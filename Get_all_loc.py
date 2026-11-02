# -*- coding: utf-8 -*-
"""
Extract the hindcast time series for all locations of configuration/locations_list.json,
without generating the reports.

The WW3 files store each variable as one compressed chunk per hourly time step covering
the whole grid, so any read of one cell decompresses the full grid anyway. Here each
monthly file is therefore read ONCE, in blocks of time steps, and every location on that
grid is picked from it. The grids, variable names, nearest-cell rule, Tp = 1/fp and output
format are the ones of HindcastReader.

Usage (run from the WaveAltasReports directory):
    python Get_all_loc.py                                   # all locations, full record
    python Get_all_loc.py --locations "Betio,Pago Pago"     # a subset
    python Get_all_loc.py --countries FJ,TO                 # locations of some countries
    python Get_all_loc.py --start 1979-01 --end 1979-02     # trial on a few months

The hindcast root can also be given with the HINDCAST_ROOT environment variable.

Full record (1979-01 to 2025-12) is written to
    output/2025/<Location>/<Location>_hindcast_data.csv
Locations that already have that file are skipped unless --overwrite is given.
A trial range is written to
    output/extract/<Location>_<start>_<end>_hindcast_data.csv

Each finished month is cached in output/extract/cache/, so an interrupted run can be
restarted with the same command and continues where it stopped.
"""

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta

import numpy as np
from netCDF4 import Dataset

from utils.hindcast_reader import HindcastReader
from utils.utilitaries import FileManager


# Default full record
# NB: Location.load_data (utils/utilitaries.py) builds its time vector up to 2025-01-01
full_start = '1979-01'
full_end = '2025-12'

# Same grid assignment as HindcastReader.load_hindcast
code_to_grid = {'FJ': 'P4', 'TO': 'P4', 'FT': 'P4', 'CK': 'P4', 'WS': 'P4', 'PV': 'A4'}
grid_to_dir = {'GL': 'GLOB', 'A4': 'AUS', 'P4': 'PAC', 'P10': 'PAC'}

keys = [ key for key in HindcastReader.varMapping[0].keys() if not key == 'validity' ]

# Number of time steps decompressed at once (24 x full grid x float32, a few hundred MB at most)
block = 24


def next_month(month):
    return datetime(month.year + month.month // 12, month.month % 12 + 1, 1)


def get_mapping(month):
    for mapping in HindcastReader.varMapping:
        if mapping['validity'][0] <= month <= mapping['validity'][1]:
            return mapping
    return HindcastReader.varMapping[-1]


def extract_month(fpath, month, ind_lon, ind_lat):
    # Returns a (time, location, variable) float32 array for all the given cells
    mapping = get_mapping(month)
    ind_lon = np.asarray(ind_lon)
    ind_lat = np.asarray(ind_lat)

    with Dataset(fpath) as nc:
        nt = len(nc.dimensions['time'])
        out = np.full((nt, len(ind_lon), len(keys)), np.nan, dtype=np.float32)

        for kk, key in enumerate(keys):
            var = nc[mapping[key]]
            for t0 in range(0, nt, block):
                arr = var[t0:t0 + block]                     # (time, lat, lon), decoded and masked
                pts = arr[:, ind_lat, ind_lon]               # (time, location)
                out[t0:t0 + block, :, kk] = np.ma.filled(pts.astype(np.float32), np.nan)

    ip = keys.index('Tp')
    out[:, :, ip] = 1 / out[:, :, ip]
    return out


def run():
    parser = argparse.ArgumentParser(description='Extract the hindcast time series for all locations.')
    parser.add_argument('--locations', default=None, help='Comma-separated location names (default: all)')
    parser.add_argument('--countries', default=None, help='Comma-separated country codes, e.g. FJ,TO')
    parser.add_argument('--start', default=None, help='First month of a trial range, YYYY-MM')
    parser.add_argument('--end', default=None, help='Last month of a trial range, YYYY-MM (default: same as --start)')
    parser.add_argument('--hroot', default=os.environ.get('HINDCAST_ROOT', HindcastReader.hroot), help='Hindcast GRIDDED directory')
    parser.add_argument('--workers', type=int, default=4, help='Number of monthly files processed in parallel (default 4)')
    parser.add_argument('--overwrite', action='store_true', help='Re-extract locations that already have a hindcast_data.csv')
    args = parser.parse_args()

    if not os.path.isdir(args.hroot):
        raise SystemExit('Hindcast directory not found: {}\nMount the share and pass --hroot or set HINDCAST_ROOT.'.format(args.hroot))

    trial = args.start is not None
    start = datetime.strptime(args.start or full_start, '%Y-%m')
    end = datetime.strptime(args.end or args.start or full_end, '%Y-%m')

    # Locations to process
    with open(FileManager.locFile, 'r') as file:
        locations = json.load(file)

    if args.locations:
        names = [ v.strip() for v in args.locations.split(',') ]
        unknown = [ v for v in names if v not in [ loc['location'] for loc in locations ] ]
        if unknown:
            raise SystemExit('Unknown location(s): {}'.format(', '.join(unknown)))
        locations = [ loc for loc in locations if loc['location'] in names ]
    if args.countries:
        codes = [ v.strip() for v in args.countries.split(',') ]
        locations = [ loc for loc in locations if loc['country_code'] in codes ]

    def out_path(locName):
        if trial:
            return os.path.join(os.path.abspath('.'), 'output', 'extract',
                                '{}_{}_{}_hindcast_data.csv'.format(locName, start.strftime('%Y%m'), end.strftime('%Y%m')))
        return os.path.join(FileManager.rootOut, locName, FileManager.hindcast_data_fmt.format(locName=locName))

    if not trial and not args.overwrite:
        skipped = [ loc['location'] for loc in locations if os.path.isfile(out_path(loc['location'])) ]
        if skipped:
            print('Skipping (already extracted, use --overwrite to redo): {}\n'.format(', '.join(skipped)))
        locations = [ loc for loc in locations if loc['location'] not in skipped ]

    if not locations:
        raise SystemExit('Nothing to extract.')

    # Hourly time vector and list of months
    t0 = np.datetime64(start, 'h')
    nTstep = int((np.datetime64(next_month(end), 'h') - t0) / np.timedelta64(1, 'h'))

    months = []
    month = start
    while month <= end:
        months.append(month)
        month = next_month(month)

    # Group the locations per grid
    grids = {}
    for loc in locations:
        grids.setdefault(code_to_grid.get(loc['code'], loc['code']), []).append(loc)

    print('{} locations, {} months: {}\n'.format(len(locations), len(months),
          ', '.join('{} {}'.format(len(v), k) for k, v in grids.items())))

    tstart = time.time()
    for grid, locs in grids.items():
        fdir = os.path.join(args.hroot, grid_to_dir[grid])
        fname = HindcastReader.fnames[grid]
        locNames = [ loc['location'] for loc in locs ]
        print('=== Grid {} ({}): {}'.format(grid, fdir, ', '.join(locNames)))

        files = { m : os.path.join(fdir, fname.format(year_month=m.strftime('%Y%m'))) for m in months }
        present = [ m for m in months if os.path.isfile(files[m]) ]
        for m in months:
            if m not in present:
                print('--> missing file ', os.path.basename(files[m]), '(filled with NaN)')
        if not present:
            print('--> no file found for grid {}, skipped\n'.format(grid))
            continue

        # Nearest grid cell of each location, same rule as HindcastReader
        with Dataset(files[present[0]]) as nc:
            lon = nc['longitude'][:]
            lat = nc['latitude'][:]
        ind_lon = [ int(np.argmin(abs(float(loc['longitude']) - lon))) for loc in locs ]
        ind_lat = [ int(np.argmin(abs(float(loc['latitude']) - lat))) for loc in locs ]

        # Cache of finished months for this set of cells
        cacheDir = os.path.join(os.path.abspath('.'), 'output', 'extract', 'cache', grid)
        os.makedirs(cacheDir, exist_ok=True)
        cells = np.array([ind_lon, ind_lat])

        def cache_path(m):
            return os.path.join(cacheDir, '{}.npz'.format(m.strftime('%Y%m')))

        def load_cache(m):
            if not os.path.isfile(cache_path(m)):
                return None
            # Reuse it only if every requested cell is in it
            with np.load(cache_path(m)) as npz:
                cached = [ tuple(v) for v in npz['cells'].T ]
                wanted = [ tuple(v) for v in cells.T ]
                if not all(v in cached for v in wanted):
                    return None
                return npz['data'][:, [ cached.index(v) for v in wanted ], :]

        data = np.full((nTstep, len(locs), len(keys)), np.nan, dtype=np.float32)

        def store(m, values):
            i0 = int((np.datetime64(m, 'h') - t0) / np.timedelta64(1, 'h'))
            nexp = int((np.datetime64(next_month(m), 'h') - np.datetime64(m, 'h')) / np.timedelta64(1, 'h'))
            if len(values) != nexp:
                print('--> {} has {} time steps instead of {}'.format(os.path.basename(files[m]), len(values), nexp))
            n = min(len(values), nexp)
            data[i0:i0 + n] = values[:n]

        todo = []
        for m in present:
            values = load_cache(m)
            if values is None:
                todo.append(m)
            else:
                store(m, values)
        if len(present) - len(todo):
            print('{} months loaded from cache'.format(len(present) - len(todo)))

        tgrid = time.time()
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            jobs = { m : pool.submit(extract_month, files[m], m, ind_lon, ind_lat) for m in todo }
            for ii, m in enumerate(todo):
                values = jobs[m].result()
                np.savez(cache_path(m), data=values, cells=cells)
                store(m, values)

                elapsed = time.time() - tgrid
                remaining = elapsed / (ii + 1) * (len(todo) - ii - 1)
                print('{} done ({} / {}) - elapsed {} - remaining for this grid ~{}'.format(
                      os.path.basename(files[m]), ii + 1, len(todo),
                      timedelta(seconds=round(elapsed)), timedelta(seconds=round(remaining))), flush=True)

        # Same format as HindcastReader.export_hindcast (the file read by Location.load_data)
        for ll, locName in enumerate(locNames):
            fout = out_path(locName)
            os.makedirs(os.path.dirname(fout), exist_ok=True)
            np.savetxt(fout, data[:, ll, :], fmt='%.5f', delimiter=',', header=','.join(keys))
            print(fout, ' was saved')
        print()

    print('All done in {}'.format(timedelta(seconds=round(time.time() - tstart))))


if __name__ == '__main__':
    run()
