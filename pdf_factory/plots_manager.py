    # -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 14:47:19 2025

@author: gregoires
"""

from datetime import datetime
import numpy as np
import os
import pandas as pd
from pyextremes import EVA
from pyextremes.extremes import get_return_periods
from shapely import Point, get_coordinates
import sys

from utils.data_processing import DataProcessing
from utils.pyEVA import WavesExtremeValuesAnalysis

from . figures_func import plot_area_map, plot_fancy_rose, plot_seasonal_rose, plot_wave_variability, \
    plot_large_wave_variability, plot_wind_variability, plot_sea_states_occurence, plot_extreme_waves_analysis



class ReportFigures(DataProcessing):
    
    
    def generate_all_plots(self):
        
        seasonal_msk, yearly_msk, monthly_msk = self.generate_masks()
        years = np.unique([ v.year for v in self.time.astype(datetime) ])
        savedir = self.root
        
        # Ploting the map of the region
        locs = self.get_locations_in_bbox(self.bbox_region)
        plot_area_map(bbox=self.bbox_region, nearbyLocations=locs, xloc=self.xlon, yloc=self.ylat, mapType='region', savedir=savedir)
        
        print('Region map was saved')
        
        # Ploting the map of the region
        locs = self.get_locations_in_bbox(self.bbox_loc)
        plot_area_map(bbox=self.bbox_loc, nearbyLocations=locs, xloc=self.xlon, yloc=self.ylat, mapType='zoom', savedir=savedir)
        
        print('Local map was saved')
        
        # Ploting the annual wave rose
        plot_fancy_rose(data=self.data['Hm0'], direction=self.data['Dp'], var='Hm0', savedir=savedir, largeSevere=False)
        
        print('Annual wave rose was saved')
        
        # Ploting the seasonal wave roses
        plot_seasonal_rose(data=self.data['Hm0'], direction=self.data['Dp'], msk=seasonal_msk, savedir=savedir)
        
        print('Seasonal wave rose was saved')
        
        # Ploting the monthly climatological wave parameters
        plot_wave_variability(Hs=self.data['Hm0'], Tp=self.data['Tp'], Dirp=self.data['Dp'], msk=monthly_msk, savedir=savedir, monthly=True)
        
        print('Monthly wave variability was saved')
        
        # Ploting the yearly average wave parameters
        plot_wave_variability(Hs=self.data['Hm0'], Tp=self.data['Tp'], Dirp=self.data['Dp'], msk=yearly_msk, savedir=savedir, monthly=False, years=years)
        
        print('Yearly wave variability was saved')
        
        # Ploting the large / severe wave rose
        plot_fancy_rose(data=self.data['Hm0'], direction=self.data['Dp'], var='Hm0', savedir=savedir, largeSevere=True)
        
        print('Large / Severe wave rose was saved')
        
        # Ploting the large / severe wave variability (monthly)
        plot_large_wave_variability(Hs=self.data['Hm0'], msk=monthly_msk, savedir=savedir, monthly=True, years=None)
        plot_large_wave_variability(Hs=self.data['Hm0'], msk=yearly_msk, savedir=savedir, monthly=False, years=years)
        
        print('Large / Severe wave variability was saved')
        
        # Ploting the annual wind rose
        wSpeed, directions = DataProcessing.cart2pol(self.data['U10'], self.data['V10'])
        directions = 270 - directions 
        directions[directions < 0] += 360
        directions[directions > 360] -= 360
        plot_fancy_rose(data=wSpeed, direction=directions, var='wind', savedir=savedir, largeSevere=False)
        
        print('Annual wind rose was saved')
        
        # Ploting the wind variability
        plot_wind_variability(u10=self.data['U10'], v10=self.data['V10'], msk=monthly_msk, savedir=savedir)
        
        print('Monthly wind variability was saved')
        
        # Doing the Extreme Values Analysis
        # Defining some parameters for the EVA
        threshold = np.nanpercentile(self.data['Hm0'], 95)
        ARI = np.arange(1, 101, 0.5)

        # For this one we are using the pyextremes library
        data = pd.Series(self.data['Hm0'], index=self.time)
        self.EVA_model = EVA(data=data)
        self.EVA_model.get_extremes('POT', threshold=threshold, r='24h')
        self.EVA_model.fit_model(model='MLE', distribution='genpareto')
        
        # Estimate the return values for modeled ARIs
        modeled_return_values, ci_lower, ci_upper = self.EVA_model.get_return_value(return_period=ARI, return_period_size='365.2425D', alpha=0.95)
        
        # Estimate the return period for observed events
        observed_return_values = get_return_periods(
            ts=self.EVA_model.data,
            extremes=self.EVA_model.extremes,
            extremes_method=self.EVA_model.extremes_method,
            extremes_type=self.EVA_model.extremes_type,
            block_size=self.EVA_model.extremes_kwargs.get("block_size", None),
            return_period_size='365.2425D',
        )

        x_obs = observed_return_values.loc[:, 'return period']
        y_obs = observed_return_values.loc[:, 'extreme values']

        # Now we can finally plot the figure
        plot_extreme_waves_analysis(
            observed_return_values=y_obs, 
            modeled_return_values=modeled_return_values, 
            observed_return_periods=x_obs, 
            modeled_return_periods=ARI, 
            ci_lower=ci_lower, 
            ci_upper=ci_upper, 
            savedir=savedir
            )


        print('Extreme Value Analysis was saved')
        
        # Ploting the sea states occurences
        plot_sea_states_occurence(Hs=self.data['Hm0'], Tm=self.data['Tm'], dout=savedir)
        
        print('Sea States occurences was saved')
        
        return
    
    def get_locations_in_bbox(self, bbox):
        
        out = []
        for loc in self.locations:
            p_i = Point(loc['longitude'], loc['latitude'])
            # in_bbox = bbox.contains(p_i).values[0]
            in_bbox = bbox.contains(p_i)
            
            if loc['location'] == self.locName:
                continue
            elif in_bbox:
                out.append([p_i.x, p_i.y])
            else:
                pass
            
        out = np.array(out)
        return out
    
    