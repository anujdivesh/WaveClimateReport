# -*- coding: utf-8 -*-
"""
Extract the hindcast time series for one location, without generating the report.

Reads only the nearest grid cell of each monthly WW3 file with xarray (lazy isel, the
fastest method in benchmark_extract.py) instead of loading whole grids like HindcastReader,
with several months processed in parallel. The grids, variable names, nearest-cell rule,
Tp = 1/fp and output format are the ones of HindcastReader.

Usage (run from the WaveAltasReports directory):
    python Get_one_loc.py "Pago Pago" --hroot /Volumes/Shared/.../PACCSAP_WAVE_HINDCAST_DATA/GRIDDED
    python Get_one_loc.py "Pago Pago" --start 2013-05 --end 2013-06      # trial on a few months

The hindcast root can also be given with the HINDCAST_ROOT environment variable.

Without --start/--end the full record (1979-01 to 2025-12)
is written to
    output/2025/<Location>/<Location>_hindcast_data.csv
which is the file main.py reads. A trial range is written to
    output/extract/<Location>_<start>_<end>_hindcast_data.csv
so it never overwrites the report input.
"""

import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta

import numpy as np
import xarray as xr

from utils.hindcast_reader import HindcastReader
from utils.utilitaries import Location


# Default full record
# NB: Location.load_data (utils/utilitaries.py) builds its time vector up to 2025-01-01
full_start = '1979-01'
full_end = '2025-12'

# Same grid assignment as HindcastReader.load_hindcast
code_to_grid = {'FJ': 'P4', 'TO': 'P4', 'FT': 'P4', 'CK': 'P4', 'WS': 'P4', 'PV': 'A4'}
grid_to_dir = {'GL': 'GLOB', 'A4': 'AUS', 'P4': 'PAC', 'P10': 'PAC'}

keys = [ key for key in HindcastReader.varMapping[0].keys() if not key == 'validity' ]


def next_month(month):
    return datetime(month.year + month.month // 12, month.month % 12 + 1, 1)


def get_mapping(month):
    for mapping in HindcastReader.varMapping:
        if mapping['validity'][0] <= month <= mapping['validity'][1]:
            return mapping
    return HindcastReader.varMapping[-1]


def nearest_cell(fpath, xlon, ylat):
    # Nearest grid cell, same rule as HindcastReader (0-based indices)
    with xr.open_dataset(fpath) as fncdf:
        lon = fncdf['longitude'].values
        lat = fncdf['latitude'].values
    ind_lon = int(np.argmin(abs(xlon - lon)))
    ind_lat = int(np.argmin(abs(ylat - lat)))
    print('Nearest cell: lon {:.4f}, lat {:.4f}'.format(lon[ind_lon], lat[ind_lat]))
    return ind_lon, ind_lat


def extract_month(fpath, month, ind_lon, ind_lat):
    mapping = get_mapping(month)
    names = [ mapping[key] for key in keys ]

    # Read only the single grid cell (lazy isel, then load)
    with xr.open_dataset(fpath) as fncdf:
        point = fncdf[names].isel(longitude=ind_lon, latitude=ind_lat).load()

    cols = []
    for key, name in zip(keys, names):
        values = point[name].values.astype(np.float32).ravel()
        cols.append(1 / values if key == 'Tp' else values)

    return np.column_stack(cols)


def run():
    parser = argparse.ArgumentParser(description='Extract the hindcast time series for one location.')
    parser.add_argument('location', help='Location name as in configuration/locations_list.json')
    parser.add_argument('--start', default=None, help='First month of a trial range, YYYY-MM')
    parser.add_argument('--end', default=None, help='Last month of a trial range, YYYY-MM (default: same as --start)')
    parser.add_argument('--hroot', default=os.environ.get('HINDCAST_ROOT', HindcastReader.hroot), help='Hindcast GRIDDED directory')
    parser.add_argument('--workers', type=int, default=4, help='Number of months processed in parallel (default 4)')
    args = parser.parse_args()

    if not os.path.isdir(args.hroot):
        raise SystemExit('Hindcast directory not found: {}\nMount the share and pass --hroot or set HINDCAST_ROOT.'.format(args.hroot))

    trial = args.start is not None
    start = datetime.strptime(args.start or full_start, '%Y-%m')
    end = datetime.strptime(args.end or args.start or full_end, '%Y-%m')

    Loc = Location(args.location)
    grid = code_to_grid.get(Loc.code, Loc.code)
    fdir = os.path.join(args.hroot, grid_to_dir[grid])
    fname = HindcastReader.fnames[grid]
    print('Working on {} ({}, {}) code {} -> {}'.format(Loc.locName, Loc.xlon, Loc.ylat, Loc.code, fdir))

    # Hourly time vector and one row index per month
    t0 = np.datetime64(start, 'h')
    t1 = np.datetime64(next_month(end), 'h')
    nTstep = int((t1 - t0) / np.timedelta64(1, 'h'))
    data = np.full((nTstep, len(keys)), np.nan, dtype=np.float32)

    months = []
    month = start
    while month <= end:
        months.append(month)
        month = next_month(month)

    files = { m : os.path.join(fdir, fname.format(year_month=m.strftime('%Y%m'))) for m in months }
    present = [ m for m in months if os.path.isfile(files[m]) ]
    for m in months:
        if m not in present:
            print('--> missing file ', os.path.basename(files[m]), '(filled with NaN)')
    if not present:
        raise SystemExit('No hindcast file found in {}'.format(fdir))

    ind_lon, ind_lat = nearest_cell(files[present[0]], Loc.xlon, Loc.ylat)

    ti = time.time()
    # Processes, not threads: netCDF/HDF5 reads are serialised within one process
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs = { m : pool.submit(extract_month, files[m], m, ind_lon, ind_lat) for m in present }
        for ii, m in enumerate(present):
            values = jobs[m].result()

            # Place the month at its own hours
            i0 = int((np.datetime64(m, 'h') - t0) / np.timedelta64(1, 'h'))
            nexp = int((np.datetime64(next_month(m), 'h') - np.datetime64(m, 'h')) / np.timedelta64(1, 'h'))
            if len(values) != nexp:
                print('--> {} has {} time steps instead of {}'.format(os.path.basename(files[m]), len(values), nexp))
            n = min(len(values), nexp)
            data[i0:i0 + n] = values[:n]

            print('{} done ({} / {}) - elapsed {}'.format(os.path.basename(files[m]), ii + 1, len(present), timedelta(seconds=round(time.time() - ti))))

    # Same format as HindcastReader.export_hindcast (the file read by Location.load_data)
    if trial:
        outDir = os.path.join(os.path.abspath('.'), 'output', 'extract')
        os.makedirs(outDir, exist_ok=True)
        fout = os.path.join(outDir, '{}_{}_{}_hindcast_data.csv'.format(Loc.locName, start.strftime('%Y%m'), end.strftime('%Y%m')))
    else:
        fout = os.path.join(Loc.root, Loc.hindcast_data_fmt.format(locName=Loc.locName))

    np.savetxt(fout, data, fmt='%.5f', delimiter=',', header=','.join(keys))
    print(fout, ' was saved ({} rows, starting {})'.format(nTstep, start.strftime('%Y-%m-%d %H:00')))


if __name__ == '__main__':
    run()
