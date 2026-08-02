# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 14:47:19 2025

@author: gregoires
"""

from datetime import datetime
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import ticker
import numpy as np
import os
from shapely import box, Point
import sys

from utils.file_manager import FileManager




class ContentManager(FileManager):
    
    def __init__(self, locName):
        super().__init__(locName)
        
        # Initialize the path to the output directory
        current_year = datetime.now().year
        self.dout = os.path.join(self.outputDir, str(current_year), self.locName)
        
        # Load the hindcast for the current location
        fname = self.hindcast_data_fmt.format(locName=self.locName)
        fpath = os.path.join(self.dout, fname)
        self.data = np.loadtxt(fpath, delimiter=',')
        
    
    def get_locations_in_bbox(self, bbox):
        
        out = []
        for loc in self.locations:
            p_i = Point(loc['longitude'], loc['latitude'])
            in_bbox = bbox.contains(p_i).values[0]
            
            if loc['location'] == self.locName:
                continue
            elif in_bbox:
                out.append([p_i.x, p_i.y])
            else:
                pass
            
        out = np.array(out)
        return out    
            
            
    
    def generate_location_map(self):
        
        countryDef = self.from_location_get_countryDef(self.locName)
        Coastline = gpd.read_file(self.coastlinesFile)
        
        # Create a bounding box around the country, clip the coastline to its extent
        # and retrieve the locations of other wave reports present in the bbox
        bbox = gpd.GeoDataFrame({"geometry": [box(countryDef['bbox_xmin'], 
                                                  countryDef['bbox_ymin'], 
                                                  countryDef['bbox_xmax'], 
                                                  countryDef['bbox_ymax'])]}, 
                                crs="EPSG:4326").to_crs(Coastline.crs)
        
        locs = self.get_locations_in_bbox(bbox)
        currentLoc = [ tmp for tmp in self.locations if self.locName == tmp['location'] ][0]
        x, y = float(currentLoc['longitude']), float(currentLoc['latitude'])
        
        # Doing the same for the data in the zoomed area
        bboxZoom = gpd.GeoDataFrame({"geometry": [box(x-1, y-1, x+1, y+1)]}, 
                                    crs="EPSG:4326").to_crs(Coastline.crs)
        
        locsZoom = self.get_locations_in_bbox(bboxZoom)
        
        print('bbox: ', bbox.bounds)
        print('bboxZoom: ', bboxZoom.bounds)
        print('Lon: ', x, ' Lat: ', y)
        print('-'*20)
        
        
        
        
        # Clipping the shapefiles to keep the bounding boxes
        CoastlineZoom = Coastline.clip(bboxZoom)
        Coastline = Coastline.clip(bbox)
        
        print('SHP: ', Coastline)
        print('SHP Zoom: ', CoastlineZoom)
        # sys.exit(0)
        
        # Defining the ploting kwargs
        style_kwargs = {'linewidth': 0.5,
                        'edgecolor':'k'}
        
        grid_kwargs = {'color' : 'gray',
                       'linestyle' : '--',
                       'linewidth' : 0.85}
        
        fig, axs = plt.subplots(1,2, figsize=(10, 7.5), layout='compressed', dpi=200)
        # First subplot
        # Coastline.boundary.plot(ax=axs[0], **style_kwargs)
        axs[0].plot(x, y, 'or', markeredgecolor='k')
        
        if locs.size > 2:
            axs[0].plot(locs[:,0], locs[:,1], 'og', markeredgecolor='k')
        
        # Second subplots
        CoastlineZoom.boundary.plot(ax=axs[1], **style_kwargs)
        axs[1].plot(x, y, 'or', markeredgecolor='k')
        
        if locsZoom.size > 2:
            axs[1].plot(locsZoom[:,0], locsZoom[:,1], 'og', markeredgecolor='k')
        
        for ax in axs:
            ax.xaxis.set_major_formatter(ticker.StrMethodFormatter("{x:.2f}°E "))
            ax.yaxis.set_major_formatter(ticker.StrMethodFormatter("{x:.2f}°N "))
            
            xlabels = ax.get_xticklabels()
            xticks = ax.get_xticks()
            
            ax.set_xticks(xticks)
            ax.set_xticklabels(xlabels, rotation=30, ha='right')
            
            ax.grid(**grid_kwargs)
            
        axs[1].yaxis.tick_right()
        axs[1].yaxis.set_ticks_position('right')
            
        plt.savefig(os.path.join(self.dout, 'test_figure_1.jpeg'))
        plt.close()