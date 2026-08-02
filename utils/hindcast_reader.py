# -*- coding: utf-8 -*-
"""
Created on Tue Feb  4 16:06:06 2025

@author: gregoires
"""

from datetime import time as dtime_time
from datetime import datetime, timedelta

import numpy as np
import os
import sys
import time
import xarray as xr

from . utilitaries import FileManager



class HindcastReader(FileManager):
    # Directory containing the hindcasts
    hroot = os.path.join('S:\\', 'GEM', 'FJ_NAB', 'O_M', 'Oceans', 'Original_Sources', 'PACCSAP_WAVE_HINDCAST_DATA', 'GRIDDED')
    
    # Template formats for the hindcast files
    fnames = {
        'GL' : 'ww3.glob_24m.{year_month}.nc',          # Global - 24 arcminutes resolution
        'A4' : 'ww3.aus_4m.{year_month}.nc',            # Australia - 4 arcminutes resolution
        'P4' : 'ww3.pac_4m.{year_month}.nc',            # Pacific - 4 arcminutes resolution
        'P10' : 'ww3.pac_10m.{year_month}.nc'           # Pacific - 10 arcminutes resolution
    }        
    
    # Variables mapping (there was a naming change in June, 2013)
    varMapping = [
        {
            'validity' : (
                datetime(year=1979, month=1, day=1, hour=0), \
                datetime(year=2013, month=5, day=31, hour=0)
                ),
            'Hm0': 'hs',
            'Dp': 'dp',
            'Dm': 'dir',
            'Tp': 'fp',
            'Tm': 't',
            'Dspd': 'spr',
            'Ecg': 'CgE',
            'U10': 'U10',
            'V10': 'V10',
            'nw': 'pnr'
            },
        {
            'validity' : (
                datetime(year=2013, month=6, day=1, hour=0), \
                datetime.now()
                ),
            'Hm0': 'hs',
            'Dp': 'dp',
            'Dm': 'dir',
            'Tp': 'fp',
            'Tm': 't01',
            'Dspd': 'spr',
            'Ecg': 'cge',
            'U10': 'uwnd',
            'V10': 'vwnd',
            'nw': 'pnr'
        }
    ]
    
    
    def __init__(self, Locations):
        
        self.Locations = Locations
        
        # Creating a time vector
        t0 = np.datetime64(datetime(year=1979, month=1, day=1), '[s]')
        t1 = np.datetime64(datetime(year=datetime.now().year, month=1, day=1, hour=0), '[s]')
        
        self.time = np.arange(t0, t1, dtype='datetime64[h]').astype(datetime)
        self.timeFiles = np.arange(t0, t1, dtype='datetime64[D]').astype(datetime)
        
        
        # Pre-allocating some space for the variables
        nTstep = len(self.time)
        nVar = len(self.varMapping[0].keys()) - 1
        
        keys = [ loc.locName for loc in self.Locations ]
        arr = np.zeros((nTstep, nVar), dtype=np.float32)
        self.data = { key : arr.copy() for key in keys }
        
    
    
    
    
    
    
    def load_hindcast(self):
        # Starting by sorting the locations per code
        codes = list(self.fnames.keys())
        slocs = { key : [ v for v in self.Locations if v.code == key ] for key in codes }
        
        missing_P4 = [ v for v in self.Locations if v.code in ['FJ', 'TO', 'FT', 'CK', 'WS'] ]
        missing_A4 = [ v for v in self.Locations if v.code in ['PV'] ]
        
        # Cheating a bit using python native dict. properties
        slocs['P4'] = slocs.get('P4', []) + missing_P4
        slocs['A4'] = slocs.get('A4', []) + missing_A4
        
        # Looping over each code / location to load the data from the hindcast
        self.locList = []
        for code in slocs.keys():
            if not slocs[code]:
                continue
            
            # Creating the path pointing to the correct directory
            if code == 'A4':
                fdir = os.path.join(self.hroot, 'AUS')
            elif code == 'GL':
                fdir = os.path.join(self.hroot, 'GLOB')
            else:
                fdir = os.path.join(self.hroot, 'PAC')
                
            # Getting ready to loop over each hindcast file
            fname = self.fnames[code]
            dtime = np.array([ datetime.combine(v, dtime_time(0,0,0)) for v in self.timeFiles if v.day == 1 ])
            flist = [ fname.format(year_month=v.strftime('%Y%m')) for v in self.timeFiles if v.day == 1 ]
            files = os.listdir(fdir)
            
            previous_idx = 0
            
            for ii, file in enumerate(flist):#TODO: retirer le slicing
                ti = time.time()
                
                if file not in files:
                    print('--> missing file ', file)
                    previous_idx = self.hook_missing_file(file, previous_idx, slocs, code)
                    continue
                
                print('Working on ', file)
                
                if dtime[ii] <= self.varMapping[0]['validity'][1]:
                    mapping = self.varMapping[0]
                    
                elif dtime[ii] >= self.varMapping[1]['validity'][0] and dtime[ii] < self.varMapping[1]['validity'][1]:
                    mapping = self.varMapping[1]

                else:
                    # Left empty for now, can be used for future code evolution
                    pass
                
                # Exctracting the longitude/latitude position of each location
                lon = np.array([ v.xlon for v in slocs[code] ], dtype=float)
                lat = np.array([ v.ylat for v in slocs[code] ], dtype=float)
                
                # Load reading the netcdf
                fpath = os.path.join(fdir, file)
                with xr.open_dataset(fpath) as fncdf:
                    fncdf = fncdf
                
                # Loading the data in memory
                arr_time = fncdf['time'].data
                
                vmin = previous_idx 
                vmax = vmin + len(arr_time)
                idx = slice(vmin, vmax)
                
                previous_idx = vmax             # Storing it for next iteration
                
                ind_lon = np.array([ np.argmin(abs(v - fncdf['longitude'].values)) for v in lon ])
                ind_lat = np.array([ np.argmin(abs(v - fncdf['latitude'].values)) for v in lat ])
                
                data = { key : fncdf[nc_key].values[:,ind_lat, ind_lon].copy() for key, nc_key in mapping.items() if not key == 'validity' }
                fncdf = None
                
                print('Data is loaded')
                
                # Looping over each location
                keys = [ key for key in self.varMapping[0].keys() if not key == 'validity' ]
                for jj, loc in enumerate(slocs[code]):
                    locKey = loc.locName
                    for kk, key in enumerate(keys):
                        if key == 'Tp':
                            self.data[locKey][idx, kk] = 1 / data[key][:,jj].copy().squeeze()
                        elif key == 'validity':
                            continue
                        else:
                            self.data[locKey][idx, kk] = data[key][:,jj].copy().squeeze()
                        

                print('End of iteration {} / {} - Duration: {}\n'.format(ii+1, len(flist), timedelta(seconds=time.time() - ti)))
                     
    
    def export_hindcast(self):
        
        keys = [ key for key in self.varMapping[0].keys() if not key == 'validity' ]
        for loc in self.Locations:
            fname = self.hindcast_data_fmt.format(locName=loc.locName)
            fout = os.path.join(loc.root, fname)
            
            header = ','.join(keys)
            np.savetxt(fout, self.data[loc.locName], fmt='%.5f', delimiter=',', header=header)
            print(fname, ' was saved')
    
    def hook_missing_file(self, fname, previous_idx, slocs, code):
        
        tstart = fname.split('.')[2]
        t0 = np.datetime64(datetime(year=int(tstart[:4]), month=int(tstart[4:6]), day=1), '[h]')
        
        if t0.astype(datetime).month == 12:
            t1 = np.datetime64(datetime(year=int(tstart[:4])+1, month=1, day=1), '[h]')
            
        else:
            t1 = np.datetime64(datetime(year=int(tstart[:4]), month=int(tstart[4:6])+1, day=1), '[h]')
        
        time = np.arange(t0, t1, dtype='datetime64[h]').astype(datetime)
        
        # Estimating the indeces of the empty values
        vmin = previous_idx
        vmax = len(time) + vmin
        idx = slice(vmin, vmax)
        
        fillValues = np.full((len(time), len(self.varMapping[0].keys())-1), np.nan)
        
        for loc in slocs[code]:
            self.data[loc.locName][idx, :] = fillValues.copy()
            print(loc.locName, ' was filled with NaN for ', fname)
        return vmax




