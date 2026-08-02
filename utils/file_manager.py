# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 14:48:08 2025

@author: gregoires
"""

import json
import numpy as np
import os
import scipy.io as spio
import sys




# this one is used to load the configuration files
class FileManager:
    # Configuration Files
    locFile = os.path.join(os.path.abspath('.'), 'configuration', 'locations_list.json')
    cntFile = os.path.join(os.path.abspath('.'), 'configuration', 'countries_list.json')
    styleFile = os.path.join(os.path.abspath('.'), 'configuration', 'paragraph_styles.json')
    glossaryFile = os.path.join(os.path.abspath('.'), 'configuration', 'glossary_terms.json')
    contentFile = os.path.join(os.path.abspath('.'), 'configuration', 'text_content_v2.json')
    captionFile = os.path.join(os.path.abspath('.'), 'configuration', 'figures_captions.json')
    tablesFile = os.path.join(os.path.abspath('.'), 'configuration', 'table_content.json')
    
    # Ancillary files
    logoDir = os.path.join(os.path.abspath('.'), 'ancillary', 'Logos')
    logoFiles = {
        'logo_COSPPAC' : os.path.join(logoDir, 'logo_COSPPAC.jpg'),
        'logo_SPC' : os.path.join(logoDir, 'logo_SPC.png'),
        # 'logo_BoM' : os.path.join(logoDir, 'logo_BoM.png'),
        'logo_BoM' : os.path.join(logoDir, 'aus_gov_BoM_new.jpg'),
        'logo_AUS_Aid' : os.path.join(logoDir, 'logo_AUS_Aid.jpg'),
        'logo_NZ' : os.path.join(logoDir, 'logo_NZ_MOFAT.png') 
        }
              
    coastlinesFile = os.path.join(os.path.abspath('.'), 'ancillary', 'coastline_pacific_countries', 'Pacific_Coastlines_0_360.shp')
    
    # Other files names / formats
    outputDir = os.path.join(os.path.abspath('.'), 'output')
    hindcast_data_fmt = '{locName}_hindcast_data.csv'
    wave_report_fmt = 'wave_report_{locName}_{countryName}.pdf'
    
    def __init__(self, locName, **kwargs):
        self.locations = self.load_json(self.locFile)
        self.countries = self.load_json(self.cntFile)
        self.content = self.load_json(self.contentFile)
        self.tables = self.load_json(self.tablesFile)
        self.captions = self.load_json(self.captionFile)
        
        # Storing the information regarding said location
        self.locName = locName
        self.countryDef = self.from_location_get_countryDef(locName)
        

    def from_location_get_countryDef(self, locName):
        country = [ tmp for tmp in self.countries if locName in tmp['locations'] ]
        
        if not country:
            err = '{} was not found in the locations list. Find bellow a list of available locations:\n  - '.format(locName)
            locList = '\n  - '.join([ v['location'] + ', ' + v['country_code'] for v in self.locations ])
            err = err + locList
            raise ValueError(err)
        return country[0]

    def get_txt_content(self, key):
        out = [ v for v in self.content if key == v['name']]
        return out[0]['content']
    
    @staticmethod
    def load_json(fpath):
        with open(fpath, 'r') as file:
            fcontent = json.load(file)
        return fcontent




# -- Other functions
def load_matfiles(filename):
    '''
    this function should be called instead of direct spio.loadmat
    as it cures the problem of not properly recovering python dictionaries
    from mat files. It calls the function check keys to cure all entries
    which are still mat-objects
    '''
    def _check_keys(d):
        '''
        checks if entries in dictionary are mat-objects. If yes
        todict is called to change them to nested dictionaries
        '''
        for key in d:
            if isinstance(d[key], spio.matlab.mio5_params.mat_struct):
                d[key] = _todict(d[key])
        return d

    def _todict(matobj):
        '''
        A recursive function which constructs from matobjects nested dictionaries
        '''
        d = {}
        for strg in matobj._fieldnames:
            elem = matobj.__dict__[strg]
            if isinstance(elem, spio.matlab.mio5_params.mat_struct):
                d[strg] = _todict(elem)
            elif isinstance(elem, np.ndarray):
                d[strg] = _tolist(elem)
            else:
                d[strg] = elem
        return d

    def _tolist(ndarray):
        '''
        A recursive function which constructs lists from cellarrays
        (which are loaded as numpy ndarrays), recursing into the elements
        if they contain matobjects.
        '''
        elem_list = []
        for sub_elem in ndarray:
            if isinstance(sub_elem, spio.matlab.mio5_params.mat_struct):
                elem_list.append(_todict(sub_elem))
            elif isinstance(sub_elem, np.ndarray):
                elem_list.append(_tolist(sub_elem))
            else:
                elem_list.append(sub_elem)
        return elem_list
    try:
        data = spio.loadmat(filename, struct_as_record=False, squeeze_me=True)
    except:
        raise
    return _check_keys(data)


























