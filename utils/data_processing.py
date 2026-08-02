# -*- coding: utf-8 -*-
"""
Created on Thu Feb 20 13:05:54 2025

@author: gregoires
"""

from datetime import timedelta, datetime
import numpy as np
import os
from scipy.signal import detrend, find_peaks
from scipy.stats import pearsonr
import sys


def get_msk_in_range(arr, vmin, vmax):
    msk = ((arr >= vmin) & (arr < vmax))
    return msk


class DataProcessing:
    
    masks = { 'seasonal' : None,                                                
              'monthly_avg' : None,                                             # Monthly climatology (or monthly average)
              'yearly_avg' : None,                                              # Yearly average values, all months merged
            }
    
    fpath_sam_index = os.path.join('.', 'ancillary', 'seasonal_SAM_index_NERC_1967_2024.txt')
    fpath_soi_index = os.path.join('.', 'ancillary', 'monthly_SOI_NOAA_1951_2024.txt')
    
    EVA = None

    @staticmethod
    def cart2pol(x, y, unit='degree'):
        
        vector = np.sqrt(x**2 + y**2)
        theta = np.rad2deg(np.arctan2(y, x))
        
        if not unit == 'degree':
            theta = np.deg2rad(theta)
        
        if isinstance(theta, np.ndarray) and unit == 'degree':
            theta[theta < 0] += 360
        elif isinstance(theta, (int, float)) and unit == 'degree' and theta < 0:
            theta += 360
        return vector, theta
    
    
    @staticmethod
    def pol2cart(vector, theta, unit='degree'):
        if unit == 'degree':
            theta = np.deg2rad(theta)
        
        x = vector * np.cos(theta)
        y = vector * np.sin(theta)
        return x, y
    
    
    def generate_masks(self):
        
        # 2D array with one column for the years, the other for the month
        nTstep = len(self.time)
        time = np.array([ [v.year, v.month] for v in self.time.astype(datetime) ])
        
        # Generating the seasonal mask -> Summer, Autumn, Winter, Spring
        seasons = [[12, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]]
        seasonal_msk = np.full((nTstep, 4), False)
        
        for ii, season in enumerate(seasons):
            for month in season:
                seasonal_msk[time[:,1] == month, ii] = True
        
        
        # Generating the monthly mask
        months = np.arange(1, 13)
        monthly_msk = np.full((nTstep, 12), False)
        
        for ii, month in enumerate(months):
            monthly_msk[time[:,1] == month, ii] = True
        
        
        # Generating the yearly mask
        years = np.unique(time[:,0])
        yearly_msk = np.full((nTstep, len(years)), False)
        
        for ii, year in enumerate(years):
            yearly_msk[time[:,0] == year, ii] = True#
        
        return seasonal_msk, yearly_msk, monthly_msk

    def get_correlation_to_climate(self, arr, yearly_msk):
        
        def generate_time_vector(t0, t1):
            time = []
            y0 = t0.astype(datetime).year
            y1 = t1.astype(datetime).year
            
            for year in np.arange(y0, y1+1):
                for month in np.arange(1, 13):
                    time.append(datetime(year=year, month=month, day=1))
            time = np.array(time, dtype=np.datetime64)
            return time
        
        def get_masks_common_time(time0, time1):
            tmin = max(time0.min(), time1.min())
            tmax = min(time0.max(), time1.max())
            
            msk0 = ((time0 >= tmin) & (time0 <= tmax))
            msk1 = ((time1 >= tmin) & (time1 <= tmax))
            return msk0, msk1
        
        def estimate_correlation(data, time, indicator, fpath):
            DATUM = np.datetime64(datetime(year=1950, month=1, day=1))
            arrInd = np.loadtxt(fpath, delimiter=',', skiprows=1)
            
            if indicator == 'SAM':
                timeInd = np.array([ np.datetime64(datetime(year=int(year), month=1, day=1)) for year in arrInd[:,0] ])
                timeInd = arrInd[:,0].astype(float)
                arrInd = arrInd[:,1].astype(float)
            else:
                # Create a time vector for SAM
                # t0 = np.datetime64(datetime(year=int(arrInd[0,0]), month=1, day=1))
                # t1 = np.datetime64(datetime(year=int(arrInd[-1,0]), month=12, day=1))
                # timeInd = generate_time_vector(t0, t1)
                # arrInd = arrInd[:,1:].copy().flatten()    # 1st column is the year
                
                timeInd = arrInd[:,0].astype(float)
                arrInd = np.nanmean(arrInd[:,1:].astype(float), axis=1)
                
            # Average wave heights to obtain annual values
            _, nIters = yearly_msk.shape
            dataYearly = np.zeros(nIters, dtype=float)
            
            for ii in range(nIters):
                tmp = data[yearly_msk[:, ii]].copy()
                dataYearly[ii] = np.nanmean(tmp)
                
            
            # Create mask to get the common time period
            timeYear = np.unique([ v.year for v in time.astype(datetime) ])
            msk, mskInd = get_masks_common_time(timeYear, timeInd)
            
            # Remove out of bound data
            time = timeYear[msk].copy()
            data = dataYearly[msk].copy()
            
            timeInd = timeInd[mskInd].copy()
            arrInd = arrInd[mskInd].copy()
            
            # Interpolate the time serie onto the indicator time serie and estimate 
            # the correlation between both
            dataInterp = np.interp(timeInd, time, data)
            Res = pearsonr(dataInterp, arrInd)
            
            r2 = Res.statistic
            p = Res.pvalue            
            return r2, p
        
        # Estimate the correlation and p-values
        SAM_r2, SAM_p = estimate_correlation(arr, self.time, indicator='SAM', fpath=self.fpath_sam_index)
        SOI_r2, SOI_p = estimate_correlation(arr, self.time, indicator='SOI', fpath=self.fpath_soi_index)
        
        if SAM_p <= 0.05 and SOI_p <= 0.05:
            txt = 'correlated with the Southern Annular Mode (r={SAM_r2:.2f}, p<0.05),' + \
                ' which is the dominant of the mode of atmospheric variation over' + \
                ' the souther Ocean Storm belt. The wave climate is also correlated'+ \
                ' with the Southern Oscillation Index (r={SOI_r2:.2f}, p<0.05), which is a' + \
                ' measure of the development and intensity of El Nino or La Nina events in the Pacific'
        
        elif SAM_p <= 0.05 and SOI_p > 0.05:
            txt = 'correlated with the Southern Annular Mode (r={SAM_r2:.2f}, p<0.05),' + \
                ' which is the dominant of the mode of atmospheric variation over' + \
                ' the southern Ocean Storm belt'
        
        elif SAM_p > 0.05 and SOI_p <= 0.05:
            txt = 'correlated with the Southern Oscillation Index (r={SOI_r2:.2f},' + \
                ' p<0.05), which is a measure of the development and intensity' + \
                ' of El Nino or La Nina events in the Pacific'
        
        else:
            txt = 'not significantly correlated with the main climate indicators of the region'
        
        txt = txt.format(SAM_r2=SAM_r2, SOI_r2=SOI_r2)
        return txt


    def get_trend(self, arr, msk):
        
        if msk is None:
            msk = np.full((len(arr), 1), True)
        
        tmp = np.zeros(msk.shape[1], dtype=float)
        for ii in range(msk.shape[1]):
            tmp[ii] = np.nanmean(arr[msk[:,ii]])
        
        # Estimate the coefficients of the trend
        trend = tmp - detrend(tmp, type='linear')
        
        x = np.arange(0, len(tmp), 1)
        coeffs = np.polyfit(x=x, y=trend, deg=1)
        
        if abs(coeffs[0]) < 0.05:
            txt = 'remained relatively unchanged'
        elif coeffs[0] > 0:
            txt = 'increased at an average of {:.2f} meters'
        elif coeffs[0] < 0:
            txt = 'decreased at an average of {:.2f} meters'
        
        txt = txt.format(abs(coeffs[0]))
        return txt

    def get_detailed_sea_state(self, Hs, season=None):
        
        calm = len(Hs[Hs < 0.1]) / len(Hs) * 100
        smooth = len(Hs[get_msk_in_range(Hs, 0.1, 0.5)]) / len(Hs) * 100
        slight = len(Hs[get_msk_in_range(Hs, 0.5, 1.25)]) / len(Hs) * 100
        moderate = len(Hs[get_msk_in_range(Hs, 1.5, 2.5)]) / len(Hs) * 100 
        rough = len(Hs[get_msk_in_range(Hs, 2.5, 4)]) / len(Hs) * 100
        Vrough = len(Hs[get_msk_in_range(Hs, 4, 6)]) / len(Hs) * 100
        high = len(Hs[get_msk_in_range(Hs, 6, 9)]) / len(Hs) * 100
        
        seaState = np.array([calm, smooth, slight, moderate, rough, Vrough, high])
        seaState_word = np.array(['calm', 'smooth', 'slight', 'moderate', 'rough', 'very rough', 'high'], dtype=str)
        
        
        
        frequencies = np.array([5,10,40,60,80,90,100])
        freqWord = np.array(['almost never', 'seldom', 'occasionally', 'sometimes', 'often', 'frequently', 'usually'], dtype=str)
        
        # Look for the most frequent sea states
        seaState_mostFreq = np.nanmax(seaState)
        msk = seaState_mostFreq < frequencies
        mostFreqWord = str(freqWord[msk][0])
        mostFreqSeaState = seaState_word[np.argmax(seaState)]
        
        # Look for the frequency of the calm sea state
        msk = calm < frequencies
        mostFreqCalm = str(freqWord[msk][0])
        
        # Look for the frequency of the rough sea state
        msk = rough < frequencies
        mostFreqRough = str(freqWord[msk][0])
        
        # Packing everything into a dictionary
        tmp = {
            'mostFreqWord' : mostFreqWord,
            'mostFreqSeaState' : mostFreqSeaState,
            'mostFreqCalm' : mostFreqCalm,
            'mostFreqRough' : mostFreqRough
        }
        
        if season is None:
            txt = 'The conditions are {mostFreqWord} {mostFreqSeaState}, {mostFreqCalm} calm, and {mostFreqRough} rough.'
        else:
            txt = 'In {season}, the dominant wave condition (occuring {mostFreqWord}) is {mostFreqSeaState}, the '  + \
                'wave are {mostFreqCalm} calm, and {mostFreqRough} rough.'
            tmp['season'] = season
                
        txt = txt.format(**tmp)
        return txt
        

    def get_wave_history(self, avgTp, avgDp):
        
        if avgTp > 11 and avgDp < 202.5 and avgDp >= 157.5:
            txt = 'The waves reaching {locName} are generally swell produced by Southern Ocean storm that propagate across long distances to reach {locName}.'
        elif avgTp > 11 and (avgDp < 22.5 or avgDp > 337.5):
            txt = 'The waves reaching {locName} are generally swell produced by the Northern Pacific Ocean storms that propagate across long distances to reach {locName}.'
        elif avgTp < 11 and avgDp > 22.5 and avgDp < 157.5:
            txt = 'The wave reaching {locName} are generally produced by the trade winds blowing the wave accross hundreds of kilometers.'
        elif avgTp < 7:
            txt = 'The wave in {locName} are generally produced by the local winds that typically blow accross short distances of tens of kilometers.'
        else:
            txt = 'In {locName} the wave come from many sources.'
        
        txt = txt.format(locName=self.locName)
        return txt

    def get_sea_state(self, avgHs):
        
        if avgHs < 0.1:
            seaState = 'calm'
        elif avgHs < 0.5:
            seaState = 'smooth'
        elif avgHs < 1.25:
            seaState = 'slight'
        elif avgHs < 2.5:
            seaState = 'moderate'
        elif avgHs < 4:
            seaState = 'rough'
        elif avgHs < 6:
            seaState = 'very rough'
        elif avgHs < 9:
            seaState = 'high'
        else:
            seaState = 'very high'
        return seaState
    
    def get_wave_type(self, avgTp):
        
        if avgTp < 11:
            waveType = 'wind seas'
        elif avgTp < 15:
            waveType = 'swell'
        else:
            waveType = 'long swell'
        return waveType
    
    def get_main_direction(self, Dp, dtheta=20):
        
        # Generate the masks for each bin and pop the last one (360-dtheta/2, 360+dtheta/2 -> the value is bigger than 360)
        binCenters = [ np.mean([dtheta/2 + ii*dtheta, dtheta/2 + (ii+1)*dtheta]) for ii in np.arange(0, 360//dtheta) ]
        msks = [ get_msk_in_range(Dp, vmin=dtheta/2 + ii*dtheta, vmax=dtheta/2 + (ii+1)*dtheta) for ii in np.arange(0, 360//dtheta) ]
        _ = msks.pop(-1)
        
        # Create the last mask (i.e., the one crossing the 0/360 values)
        msk_p1 = get_msk_in_range(Dp, vmin=0, vmax=dtheta/2)
        msk_p2 = get_msk_in_range(Dp, vmin=360-dtheta/2, vmax=360)
        msks.append(np.any([msk_p1, msk_p2], axis=0))
        
        # Estimate the directional bins with the most values
        counter = []
        for msk in msks:
            counter.append(len(msk[msk]))
        
        principalDir = binCenters[np.argmax(counter)]
        return principalDir
    
    def get_direction(self, Dp, dtheta=20):
        principalDir = self.get_main_direction(Dp, dtheta=dtheta)
        
        if principalDir < 22.5 or principalDir > 337.5:
            txt = 'North'
        elif principalDir < 67.5:
            txt = 'NorthEast'
        elif principalDir < 112.5:
            txt = 'East'
        elif principalDir < 157.5:
            txt = 'SouthEast'
        elif principalDir < 202.5:
            txt = 'South'
        elif principalDir < 247.5:
            txt = 'SouthWest'
        elif principalDir < 292.5:
            txt = 'West'
        elif principalDir < 337.5:
            txt = 'NorthWest'
            
        txt = txt + ' ({:.0f}°)'.format(principalDir)
        return txt, principalDir
    
    def get_variability(self, arr, msk, avg=False):
        
        # nIters can be the number of years, months or seasons depending on what 
        # variability scale we are looking for (e.g., monthly variability -> nIters = 12)
        _, nIters = msk.shape
        arrIter_avg = np.zeros(nIters, dtype=float)
        arrIter_std = np.zeros(nIters, dtype=float)
        
        for ii in range(nIters):
            tmp = arr[msk[:, ii]].copy()
            arrIter_avg[ii] = np.nanmean(tmp)
            arrIter_std[ii] = np.nanstd(tmp)
        
        if avg:
            arr_std = np.nanmean(arrIter_std)
            arr_mean = np.nanmean(arrIter_avg)
        else:
            arr_std = np.nanstd(arrIter_avg)
            arr_mean = np.nanmean(arrIter_avg)
        
        variability = arr_std
        variabilityPerC = 100 * arr_std / arr_mean
        
        return variability, variabilityPerC


    def get_threshold_variability(self, arr, msk, percentile):
        
        # nIters can be the number of years, months or seasons depending on what 
        # variability scale we are looking for (e.g., monthly variability -> nIters = 12)
        _, nIters = msk.shape
        threshold = np.zeros(nIters, dtype=float)
        
        for ii in range(nIters):
            tmp = arr[msk[:, ii]].copy()
            threshold[ii] = np.nanpercentile(tmp, percentile)
            
        variability = np.std(threshold)
        variabilityPerC = 100 * variability / np.mean(threshold)
        
        return variability, variabilityPerC
    
    
    def mean_stats(self, key, isdir=False, msk=None):
        arr = self.data[key].copy()
        
        if msk is None:
            msk = np.full(arr.shape, True)
            
        if isdir:
            u, v = self.pol2cart(vector=np.ones(arr.shape), theta=arr)
            um = np.nanmean(u[msk])
            vm = np.nanmean(v[msk])
            _, theta = self.cart2pol(um, vm)
            return theta
        else:
            return np.nanmean(arr[msk])
    
    def get_local_maxima(self, arr, x, dx_min, N=None):
        
        dx = x[1] - x[0]
        distance = (dx_min / dx).astype(int)
        
        pos, *_ = find_peaks(arr, distance=distance)
        
        xpeaks = x[pos].copy()
        ypeaks = arr[pos].copy()
        
        if N is not None:
            idx = np.argsort(ypeaks)
            xpeaks = xpeaks[idx][::-1][:N]
            ypeaks = ypeaks[idx][::-1][:N]
        
        return ypeaks, xpeaks
    
    def generate_text_values(self):
        
        self.generate_avg_wave_condition()
        self.generate_mean_wave_rose()
        self.generate_wave_variability()
        self.generate_large_severe_waves()
        self.generate_extreme_waves()
        self.generate_wave_energy()
        self.generate_wind()
        
        # Manually adding some other parameters
        self.dataOut['yearStart'] = min(self.time).astype(datetime).year
        self.dataOut['yearEnd'] = max(self.time).astype(datetime).year
        self.dataOut['hindcastDuration'] = self.dataOut['yearEnd'] - self.dataOut['yearStart']

        # Dupplicating the values into the second dictionary used for the tables
        self.dataTable['yearStart'] = self.dataOut['yearStart']
        self.dataTable['yearEnd'] = self.dataOut['yearEnd']
        return self.dataOut, self.dataTable
    
    
    def generate_avg_wave_condition(self):
        self.dataOut['avgWave_meanHs'] = self.mean_stats(key='Hm0')
        self.dataOut['avgWave_meanDp'] = self.mean_stats(key='Dp', isdir=True)
        self.dataOut['avgWave_meanTp'] = self.mean_stats(key='Tp')
        self.dataOut['avgWave_nComponents'] = self.mean_stats(key='nw')
        
        self.dataOut['avgWave_seaState'] = self.get_sea_state(self.dataOut['avgWave_meanHs'])
        self.dataOut['avgWave_waveType'] = self.get_wave_type(self.dataOut['avgWave_meanTp'])
        
        # Add the necessary data into the dict used to fill the tables
        self.dataTable['avgWave_meanHs'] = self.dataOut['avgWave_meanHs']
        self.dataTable['avgWave_meanTp'] = self.dataOut['avgWave_meanTp']
        self.dataTable['avgWave_meanDp'] = self.dataOut['avgWave_meanDp']
        self.dataTable['avgWave_nComponents'] = self.dataOut['avgWave_nComponents']
        
        # Estimate the variability (dont't ask me about the avg=True or avg=False
        # I have no idea how the original is working nor which formula is used for
        # this table
        seasonal_msk, yearly_msk, _ = self.generate_masks()
        var, varPerC = self.get_variability(self.data['Hm0'], yearly_msk, avg=False)
        self.dataTable['avgWave_meanAnnualVar'] = var
        self.dataTable['avgWave_meanAnnualVarPerC'] = varPerC
        
        var, varPerC = self.get_variability(self.data['Hm0'], seasonal_msk, avg=True)
        self.dataTable['avgWave_meanSeasonalVar'] = var
        self.dataTable['avgWave_meanSeasonalVarPerC'] = varPerC
        
        return
    
    def generate_mean_wave_rose(self):
        txt, meanDp = self.get_direction(self.data['Dp'])
        self.dataOut['meanWaRose_waveHistory'] = self.get_wave_history(self.dataOut['avgWave_meanTp'], meanDp)
        self.dataOut['meanWaRose_seaState'] = self.get_detailed_sea_state(self.data['Hm0'])
        self.dataOut['meanWaRose_Dirp'] = txt
        return
    
    def generate_wave_variability(self):
        
        # Generate the masks per season (hemisphere dependent, given as DJF, MAM, JJA, SON)
        seasonal_msk, yearly_msk, monthly_msk = self.generate_masks()
        
        if self.ylat > 0:
            mskWinter = seasonal_msk[:,0].copy()
            mskSpring = seasonal_msk[:,1].copy()
            mskSummer = seasonal_msk[:,2].copy()
            mskAutumn = seasonal_msk[:,3].copy()
        else:
            mskSummer = seasonal_msk[:,0].copy()
            mskAutumn = seasonal_msk[:,1].copy()
            mskWinter = seasonal_msk[:,2].copy()
            mskSpring = seasonal_msk[:,3].copy()
        
        # Estimate peak direction per season
        winterDp = self.data['Dp'][mskWinter].copy()
        springDp = self.data['Dp'][mskSpring].copy()
        summerDp = self.data['Dp'][mskSummer].copy()
        autumnDp = self.data['Dp'][mskAutumn].copy()
        
        self.dataOut['waveVar_winterSeaState'] = self.get_detailed_sea_state(self.data['Hm0'][mskWinter], season='Winter')
        self.dataOut['waveVar_winterDirp'], _ = self.get_direction(winterDp)
        
        self.dataOut['waveVar_springSeaState'] = self.get_detailed_sea_state(self.data['Hm0'][mskSpring], season='Spring')
        self.dataOut['waveVar_springDirp'], _ = self.get_direction(springDp)
        
        self.dataOut['waveVar_summerSeaState'] = self.get_detailed_sea_state(self.data['Hm0'][mskSummer], season='Summer')
        self.dataOut['waveVar_summerDirp'], _ = self.get_direction(summerDp)
        
        self.dataOut['waveVar_autumnSeaState'] = self.get_detailed_sea_state(self.data['Hm0'][mskAutumn], season='Autumn')
        self.dataOut['waveVar_autumnDirp'], _ = self.get_direction(autumnDp)
        
        # Estimate the Hs variability
        var, varPerC = self.get_variability(self.data['Hm0'], msk=monthly_msk, avg=True)
        self.dataOut['waveVar_HsVar'] = var #May not be used
        self.dataOut['waveVar_HsVarCoeff'] = varPerC
        
        # Inter-annual
        _, varPerC = self.get_variability(self.data['Hm0'], msk=yearly_msk, avg=False)
        self.dataOut['waveVar_HsVarCoeff_InterAnnual'] = varPerC
        
        # Estimate the trend
        self.dataOut['waveVar_HsTrend'] = self.get_trend(self.data['Hm0'], msk=yearly_msk)
        
        # Estimate the correlation with climatic events`
        self.dataOut['waveVar_CorrClimate'] = self.get_correlation_to_climate(arr=self.data['Hm0'], yearly_msk=yearly_msk) #TODO: debugger le bordel
        return
    
    
    def generate_large_severe_waves(self):
        # Generate the masks per season (hemisphere dependent, given as DJF, MAM, JJA, SON)
        seasonal_msk, yearly_msk, monthly_msk = self.generate_masks()
        
        self.dataOut['severeWave_thresholdLarge'] = np.nanpercentile(self.data['Hm0'], 90)
        self.dataOut['severeWave_thresholdSevere'] = np.nanpercentile(self.data['Hm0'], 99)
        
        msk = self.data['Hm0'] >= self.dataOut['severeWave_thresholdSevere']
        severeWaves_Dp = self.data['Dp'][msk].copy()
        self.dataOut['severeWave_Dirp'], _ = self.get_direction(severeWaves_Dp)
        
        # Estimate the monthly / yearly variability
        msk = self.data['Hm0'] >= self.dataOut['severeWave_thresholdLarge']
        HsLarge = self.data['Hm0'][msk].copy()
        monthly_msk_large = monthly_msk[msk, :]
        yearly_msk_large = yearly_msk[msk, :]
        
        # Estimate the threshold monthly / yearly variability
        _, self.dataOut['severeWave_monthlyVarCoeff'] = self.get_threshold_variability(self.data['Hm0'], monthly_msk, percentile=90)
        _, self.dataOut['severeWave_yearlyVarCoeff'] = self.get_threshold_variability(self.data['Hm0'], yearly_msk, percentile=90)
        
        
        # Estimate the month with the most variability
        _, nIters = monthly_msk_large.shape
        arrIter_avg = np.zeros(nIters, dtype=float)
        arrIter_std = np.zeros(nIters, dtype=float)
        
        for ii in range(nIters):
            tmp = HsLarge[monthly_msk_large[:, ii]].copy()
            arrIter_avg[ii] = np.nanmean(tmp)
            arrIter_std[ii] = np.nanstd(tmp)
            
        variability = 100 * arrIter_std / arrIter_avg
        months = ['January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
        
        self.dataOut['severeWave_mainSeason'] = months[np.argmax(variability)]
        return
    
    
    def generate_extreme_waves(self):
        
        ypeaks, xpeaks = self.get_local_maxima(self.data['Hm0'], self.time, dx_min=np.timedelta64(60, 'h'), N=30)
        #TODO: sauver les valeurs dans un dict. pour les tables
        self.dataOut['extremeWave_largestDate'] = xpeaks[0].astype(datetime).strftime('%B %dth %Y')
        self.dataOut['extremeWave_largestHs'] = ypeaks[0]
        self.dataOut['extremeWave_largestCondition'] = self.get_sea_state(ypeaks[0])
        
        self.dataOut['extremeWave_smallestHs'] = ypeaks[-1]
        self.dataOut['extremeWave_smallestCondition'] = self.get_sea_state(ypeaks[-1])
        
        # Use the values from the pyextremes package
        self.dataOut['extremeWave_EVA_nEvents'] = len(self.EVA_model.extremes.values)
        self.dataOut['extremeWave_EVA_threshold'] = self.EVA_model.extremes_kwargs["threshold"]
        
        # Generate the data for the table containing the 30 largest wave events
        self.dataTable['extremeWave_largestEvents'] = []
        for ii in range(30):
            msk = xpeaks[ii] == self.time
            
            if len(msk[msk]) > 1:
                print('More than one dates were found when looking for a unique value. Fix me')
                raise ValueError
            elif len(msk[msk]) == 0:
                print('No date was found when looking for a unique value. Fix me')
                raise ValueError
            
            # Retrieving the values corresponding to this extrema
            date = self.time[msk][0].astype(datetime).strftime('%d/%m/%Y')
            hs = np.around(self.data['Hm0'][msk][0], 2)
            tp = np.around(self.data['Tp'][msk][0], 2)
            dp, _ = self.get_direction(self.data['Dp'][msk][0])
            
            self.dataTable['extremeWave_largestEvents'].append([ii+1, date, hs, tp, dp])
        
        # Generate the values to be put into the table
        self.dataTable['extremeWave_thresholdLarge'] = self.dataOut['severeWave_thresholdLarge']
        self.dataTable['extremeWave_thresholdSevere'] = self.dataOut['severeWave_thresholdSevere']
        
        # Estimating the wave heights at different ARI
        ARIs = np.array([1, 10, 20, 50, 100])
        extreme_values, *_ = self.EVA_model.get_return_value(return_period=ARIs, return_period_size='365.2425D')

        for ii, ARI in enumerate(ARIs):
            key = 'extremeWave_waveHeight_ARI_{}'.format(ARI)
            self.dataTable[key] = extreme_values[ii]
        return
    
    def generate_wave_energy(self):
        # Generate the masks per season (hemisphere dependent, given as DJF, MAM, JJA, SON)
        seasonal_msk, yearly_msk, monthly_msk = self.generate_masks()
        
        # Estimating the mean annual energy flux
        _, nIters = yearly_msk.shape
        arr = np.zeros(nIters, dtype=float)
        for ii in range(nIters):
            arr[ii] = np.nanmean(self.data['Ecg'][yearly_msk[:, ii]])
        
        self.dataOut['waveEnergy_meanAnnualEnergyFlux'] = np.nanmean(arr)
        
        return
    
    def generate_wind(self):
        
        # Mean wind speed / wind direction
        wspeed, directions = self.cart2pol(self.data['U10'], self.data['V10'])
        directions = 270 - directions 
        directions[directions < 0] += 360
        directions[directions > 360] -= 360
        
        self.dataOut['wind_wSpeed'] = np.nanmean(wspeed)
        self.dataOut['wind_wSpeedKnots'] = np.nanmean(wspeed) * 1.9438
        self.dataOut['wind_Dirp'], _ = self.get_direction(Dp=directions)
        
        # Estimate the mean direction (and convert it to nautical convention)
        um = np.nanmean(self.data['U10'])
        vm = np.nanmean(self.data['V10'])
        _, direction = self.cart2pol(um, vm)
        direction = 270 - direction
        
        if direction < 0:
            direction += 360
            
        if direction > 360:
            direction -= 360
            
        if direction > 90:
            self.dataOut['wind_tradeWinds'] = 'Southern Easterly trade winds'
        else:
            self.dataOut['wind_tradeWinds'] = 'Northern Easterly trade winds'
        return
    
        
        
    

