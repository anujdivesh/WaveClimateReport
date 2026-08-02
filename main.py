# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 12:04:09 2025

@author: gregoires
"""
import os
import ssl
import sys

# The network re-signs TLS connections, so no public CA bundle validates the
# Natural Earth downloads cartopy needs. Skip verification for them.
ssl._create_default_https_context = ssl._create_unverified_context

from pdf_factory.layout_manager import WaveReport

from utils.hindcast_reader import HindcastReader
from utils.utilitaries import Location




def run():
    
    locList = ['Betio']
    # locList = ['Pago Pago']
    
    
    # locList = ['Betio', 'Guam', 'Pago Pago', 'Yap']
    # locList = ['Penrhyn', 'Lakepa Island', 'Rotuma Island', 'Mare Island', 'Betio', 'Guam', 'Pago Pago', 'Yap']
    Locations = [ Location(locName) for locName in locList ]
    # Hindcast = HindcastReader(Locations)
    # Hindcast.load_hindcast()
    # Hindcast.export_hindcast()
    
    for Loc in Locations:
        print('Working on', Loc.locName)
        Loc.load_data()
        
        Loc.generate_all_plots()
        
        fname = Loc.wave_report_fmt.format(locName=Loc.locName, countryName=Loc.countryName)
        fpath = os.path.join(Loc.root, fname)
        
        txt_keyValues, table_keyValues = Loc.generate_text_values()

        Report = WaveReport(fpath, locName=Loc.locName, txt_keyValues=txt_keyValues, table_keyValues=table_keyValues)
    
    
    return














if __name__ == '__main__':
    run()