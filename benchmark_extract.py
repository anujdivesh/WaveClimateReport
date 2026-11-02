# -*- coding: utf-8 -*-
"""
Compare the speed of extracting one grid cell from the WW3 hindcast with
xarray (as in HindcastReader), xarray (lazy point read), netCDF4, CDO and NCO.

Each method reads a DIFFERENT month (consecutive months from --start), so the
operating system's file cache can't make a later method look faster.
Every result is checked against the original <Location>_hindcast_data.csv.

Usage (run from the WaveAltasReports directory):
    python benchmark_extract.py "Betio" --start 1979-01
    python benchmark_extract.py "Betio" --start 1979-01 --methods netcdf4,nco
"""

import argparse
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta

import numpy as np
import xarray as xr
from netCDF4 import Dataset

from utils.hindcast_reader import HindcastReader
from utils.utilitaries import Location


code_to_grid = {'FJ': 'P4', 'TO': 'P4', 'FT': 'P4', 'CK': 'P4', 'WS': 'P4', 'PV': 'A4'}
grid_to_dir = {'GL': 'GLOB', 'A4': 'AUS', 'P4': 'PAC', 'P10': 'PAC'}

keys = [ key for key in HindcastReader.varMapping[0].keys() if not key == 'validity' ]


def next_month(month):
    return datetime(month.year + month.month // 12, month.month % 12 + 1, 1)


def get_names(month):
    for mapping in HindcastReader.varMapping:
        if mapping['validity'][0] <= month <= mapping['validity'][1]:
            return [ mapping[key] for key in keys ]
    return [ HindcastReader.varMapping[-1][key] for key in keys ]


def to_table(arrays):
    # (time, 10) float32 table with Tp = 1 / fp, as in HindcastReader
    cols = []
    for key, values in zip(keys, arrays):
        values = np.ma.filled(np.asarray(values, dtype=np.float32), np.nan).ravel() if np.ma.isMaskedArray(values) \
            else np.asarray(values, dtype=np.float32).ravel()
        cols.append(1 / values if key == 'Tp' else values)
    return np.column_stack(cols)


def read_small_file(fpath, names):
    with Dataset(fpath) as nc:
        return to_table([ nc[name][:] for name in names ])


# ---------------------------------------------------------------- methods

def m_xarray_full(fpath, names, i, j, tmpdir):
    # What HindcastReader does: load each full variable, then pick the cell
    with xr.open_dataset(fpath) as ds:
        return to_table([ ds[name].values[:, j, i] for name in names ])


def m_xarray_point(fpath, names, i, j, tmpdir):
    # xarray reading only the cell (lazy isel)
    with xr.open_dataset(fpath) as ds:
        point = ds[names].isel(longitude=i, latitude=j).load()
        return to_table([ point[name].values for name in names ])


def m_netcdf4(fpath, names, i, j, tmpdir):
    # netCDF4 hyperslab read of the cell
    with Dataset(fpath) as nc:
        return to_table([ nc[name][:, j, i] for name in names ])


def m_cdo(fpath, names, i, j, tmpdir):
    fout = os.path.join(tmpdir, 'cdo.nc')
    box = 'selindexbox,{0},{0},{1},{1}'.format(i + 1, j + 1)
    subprocess.run(['cdo', '-s', '-O', '-L', box, '-selname,' + ','.join(names), fpath, fout], check=True, capture_output=True)
    return read_small_file(fout, names)


def m_nco(fpath, names, i, j, tmpdir):
    fout = os.path.join(tmpdir, 'nco.nc')
    subprocess.run(['ncks', '-O', '-d', 'longitude,{0},{0}'.format(i), '-d', 'latitude,{0},{0}'.format(j),
                    '-v', ','.join(names), fpath, fout], check=True, capture_output=True)
    return read_small_file(fout, names)


methods = {
    'xarray_full': m_xarray_full,
    'xarray_point': m_xarray_point,
    'netcdf4': m_netcdf4,
    'cdo': m_cdo,
    'nco': m_nco,
}


def run():
    parser = argparse.ArgumentParser(description='Benchmark single-cell extraction methods on the WW3 hindcast.')
    parser.add_argument('location', help='Location name as in configuration/locations_list.json')
    parser.add_argument('--start', default='1979-01', help='First month, YYYY-MM; each method gets the next month')
    parser.add_argument('--methods', default=','.join(methods), help='Comma-separated subset of: ' + ', '.join(methods))
    parser.add_argument('--hroot', default=os.environ.get('HINDCAST_ROOT', HindcastReader.hroot), help='Hindcast GRIDDED directory')
    args = parser.parse_args()

    selected = [ m.strip() for m in args.methods.split(',') if m.strip() ]
    for m in selected:
        if m not in methods:
            raise SystemExit('Unknown method {}'.format(m))
        if m in ('cdo', 'nco') and shutil.which({'cdo': 'cdo', 'nco': 'ncks'}[m]) is None:
            raise SystemExit('{} not found on the PATH'.format(m))

    Loc = Location(args.location)
    grid = code_to_grid.get(Loc.code, Loc.code)
    fdir = os.path.join(args.hroot, grid_to_dir[grid])
    fname = HindcastReader.fnames[grid]

    # Original extraction used as the reference
    ref_path = os.path.join(Loc.root, Loc.hindcast_data_fmt.format(locName=Loc.locName))
    ref = np.loadtxt(ref_path, delimiter=',') if os.path.isfile(ref_path) else None

    month = datetime.strptime(args.start, '%Y-%m')
    first = os.path.join(fdir, fname.format(year_month=month.strftime('%Y%m')))
    with Dataset(first) as nc:
        i = int(np.argmin(abs(Loc.xlon - nc['longitude'][:])))
        j = int(np.argmin(abs(Loc.ylat - nc['latitude'][:])))
    print('{} -> cell index lon {}, lat {}\n'.format(Loc.locName, i, j))

    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        for name in selected:
            fpath = os.path.join(fdir, fname.format(year_month=month.strftime('%Y%m')))
            print('{:13s} {} ...'.format(name, os.path.basename(fpath)), flush=True)

            ti = time.time()
            try:
                table = methods[name](fpath, get_names(month), i, j, tmpdir)
                status = 'ok'
            except Exception as err:
                table, status = None, 'FAILED: {}'.format(str(err).strip().splitlines()[-1] if str(err).strip() else type(err).__name__)
            elapsed = time.time() - ti

            # Check against the original CSV rows of that month
            check = 'no reference'
            if table is not None and ref is not None:
                i0 = int((np.datetime64(month, 'h') - np.datetime64('1979-01-01T00', 'h')) / np.timedelta64(1, 'h'))
                expected = ref[i0:i0 + len(table)]
                same_nan = (np.isnan(expected) == np.isnan(table)).all()
                diff = np.nanmax(np.abs(expected - table)) if len(table) else np.nan
                check = 'matches original' if same_nan and diff < 1e-3 else 'DIFFERS (max diff {:.4f}, NaN match {})'.format(diff, same_nan)

            print('{:13s} {:>10s}  {}  {}\n'.format(name, str(timedelta(seconds=round(elapsed))), status, check), flush=True)
            results.append((name, month.strftime('%Y-%m'), elapsed, status, check))
            month = next_month(month)

    print('Summary (fastest first)')
    for name, m, elapsed, status, check in sorted(results, key=lambda r: r[2]):
        print('  {:13s} {}  {:>8.1f} s  {}  {}'.format(name, m, elapsed, status, check))


if __name__ == '__main__':
    run()
