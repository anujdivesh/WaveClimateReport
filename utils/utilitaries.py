# -*- coding: utf-8 -*-
"""
Created on Mon Feb 17 15:14:11 2025

@author: gregoires
"""

from datetime import datetime
import json
import numpy as np
import os
from shapely import box, get_coordinates

from pdf_factory.plots_manager import ReportFigures


#TODO: remove this class, it also exist in file_managher.py
class FileManager:
    # Output directory
    # rootOut = os.path.join(os.path.abspath('.'), 'output', str(datetime.now().year))
    rootOut = os.path.join(os.path.abspath('.'), 'output', '2025')
    
    # Configuration Files
    locFile = os.path.join(os.path.abspath('.'), 'configuration', 'locations_list.json')
    cntFile = os.path.join(os.path.abspath('.'), 'configuration', 'countries_list.json')
    styleFile = os.path.join(os.path.abspath('.'), 'configuration', 'paragraph_styles.json')
    glossaryFile = os.path.join(os.path.abspath('.'), 'configuration', 'glossary_terms.json')
    contentFile = os.path.join(os.path.abspath('.'), 'configuration', 'text_content_v2.json')
    
    
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
    
    # Others
    hindcast_data_fmt = '{locName}_hindcast_data.csv'
    wave_report_fmt = 'wave_report_{locName}_{countryName}.pdf'
    
    def __init__(self):
        self.locations = self.load_json(self.locFile)
        self.countries = self.load_json(self.cntFile)
        self.content = self.load_json(self.contentFile)
        
    @staticmethod
    def load_json(fpath):
        with open(fpath, 'r') as file:
            fcontent = json.load(file)
        return fcontent




class Location(FileManager, ReportFigures):
    
    def __init__(self, locName):
        super().__init__()
        
        dx = 1 #TODO: faire un truc propre pour ces gars 
        dy = 1
        
        # Retrieve the country / location definitions #TODO: retirer le control sur les locations dans la definition du pays
        countryDef = [ tmp for tmp in self.countries if locName in tmp['locations'] ][0]
        locationDef = [ tmp for tmp in self.locations if locName == tmp['location'] ][0]
        
        # Store some values into memory for later use
        self.locName = locName
        self.countryName = countryDef['country_name']
        
        self.xlon = float(locationDef['longitude'])
        self.ylat = float(locationDef['latitude'])
        
        self.code = locationDef['code']
        
        self.bbox_region = box(countryDef['bbox_xmin'], countryDef['bbox_ymin'], countryDef['bbox_xmax'], countryDef['bbox_ymax'])
        self.bbox_loc = box(self.xlon-dx, self.ylat-dy, self.xlon+dx, self.ylat+dy)
        
        # Create the output directory path
        self.root = os.path.join(self.rootOut, self.locName)
        
        # Generate the directory used to store the data and the report
        self.create_directory()
        
        
        # Define some variables as place holders for later on
        keys = ['Hm0', 'Dp', 'Dm', 'Tp', 'Tm', 'Dspd', 'Ecg', 'U10', 'V10', 'nw']
        self.data = { key : None for key in keys }
        self.time = None
        
        # Create an empty dict used to store the values we will output in the report
        self.dataOut = {} #TODO: initialize it with a configuration file
        self.dataTable = {}
        
        
        
    def create_directory(self):
        if not os.path.isdir(self.rootOut):
            os.mkdir(self.rootOut)
            
        if not os.path.isdir(self.root):
            os.mkdir(self.root)
            
    def load_data(self):
        fname = self.hindcast_data_fmt.format(locName=self.locName)
        fpath = os.path.join(self.root, fname)
        data = np.loadtxt(fpath, delimiter=',')
        self.data = { key : data[:,ii] for ii, key in enumerate(self.data.keys()) }
        
        # Creating a time vector
        t0 = np.datetime64(datetime(year=1979, month=1, day=1, hour=0), '[h]')
        # t1 = np.datetime64(datetime(year=datetime.now().year, month=1, day=1, hour=0), '[h]')
        t1 = np.datetime64(datetime(year=2025, month=1, day=1, hour=0), '[h]')

        # self.time = np.arange(t0, t1, dtype='datetime64[h]').astype(datetime)
        self.time = np.arange(t0, t1, dtype='datetime64[h]')
        
        
        
        