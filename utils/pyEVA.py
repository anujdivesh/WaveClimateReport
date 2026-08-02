# -*- coding: utf-8 -*-
"""
Created on Mon Mar 24 11:56:00 2025

@author: gregoires
"""

from copulas.multivariate import GaussianMultivariate
from copulas.univariate import GaussianKDE
from datetime import datetime, timedelta
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from scipy.signal import find_peaks
import scipy.stats as stats
from scipy.stats import gaussian_kde
import sys


# Declaring some constants
class PhysicalConstants:
    # General parameters
    gravity_acceleration = 9.80665          # [m/s2]
    rho_seawater = 1028.1                   # [kg/m3]
    atmospheric_pressure = 10.132501 * 1e4  # [Pa]



# --- Misc functions to be used in every scripts
def statistical_standardization(data: np.ndarray)->np.ndarray:
    '''
    Standardize a dataset so that its mean is equal to 0 and its standard deviation
    is equal to 1.

    Parameters
    ----------
    data : np.ndarray
        Data to be normalized.

    Returns
    -------
    out : np.ndarray
        Normalized dataset.
    '''
    out = (data - np.nanmean(data)) / np.nanstd(data)
    return out

def confidence_interval(data: np.ndarray, 
                        percentile:float|int, 
                        axis:int=-1) -> np.ndarray:
    '''
    Compute the X % Confidence Interval along the specified axis.

    Parameters
    ----------
    data : np.ndarray
        Input array or object that can be converted to an array.
    percentile : float|int
        Percentage or sequence of percentages for the percentiles to compute. Values must be between 0 and 100 inclusive.
    axis : int, optional
        Axis along which the percentile are computed. The default is -1.

    Returns
    -------
    out : np.ndarray
        Confidence Interval estimated for the provided percentile.

    '''
    return np.percentile(data, [(100 - percentile) / 2, 100 - (100 - percentile) / 2], axis=axis)

def datenum_to_datetime(datenum):
    """
    Convert Matlab datenum into Python datetime.
    :param datenum: Date in datenum format
    :return:        Datetime object corresponding to datenum.
    """
    days = datenum % 1
    hours = days % 1 * 24
    minutes = hours % 1 * 60
    seconds = minutes % 1 * 60
    return datetime.fromordinal(int(datenum)) \
           + timedelta(days=int(days)) \
           + timedelta(hours=int(hours)) \
           + timedelta(minutes=int(minutes)) \
           + timedelta(seconds=round(seconds)) \
           - timedelta(days=366)


def solve_linear_dispersion(k0: float|np.ndarray,
                            Tp: float|np.ndarray,
                            depth: float, eps: float=1e-4) -> float|np.ndarray:
    '''
    Newton-Raphson's iterative method applied to the dispersion relationship
    for gravity waves in the ocean to estimate the wavenumber k.
    
    The linear wave dispersion relation follows:
            
            omega^2 = gk.tanh(kh)
            
    Parameters
    ----------
    k0 : float|np.ndarray
        Initial guess as to the wave number. Can be any positive value.
    Tp : float|np.ndarray
        Peak period given in seconds.
    depth : float
        Depth at which the dispersion relation is to be applieds.
    eps : float, optional
        Threshold used to stop the iterations. The default is 1e-4.

    Returns
    -------
    x1 : float|np.ndarray
        Wavenumber value(s) solving the dispersion relation.

    '''
    
    # Retrieving the constants
    g = PhysicalConstants.gravity_acceleration
    
    # Estimating some parameters
    omega = 2*np.pi/Tp
    f = np.power(omega, 2) - g*k0 * np.tanh(k0*depth)
    fp = -g * np.tanh(k0*depth) - depth*g*k0 * (1 - np.power(np.tanh(k0*depth), 2))
    
    # Initialize some parameters
    x1 = 1e10
    x = 0
    cnt = 0
    
    while (abs(x1-x) > eps):
        x = x1
        cnt += 1
        
        f = (np.power(omega, 2) - g*x * np.tanh(x*depth))
        fp = -g * np.tanh(x*depth) - depth*g*x * (1 - np.power(np.tanh(x*depth), 2))
        x1 = x - f/fp
    
    return x1

def bootstrapping(data: np.ndarray, nSamples: int, nSteps: int=2000) -> tuple[np.ndarray, np.ndarray]:
    '''
    Re-sample the provided dataset by applying a bootstrapping scheme.

    Parameters
    ----------
    data : np.ndarray
        Input dataset.
    nSamples : int
        Number of samples to be drawn at each iteration.
    nSteps : int, optional
        Number of iterations. The default is 2000.

    Returns
    -------
    CI : np.ndarray
        95% Confidence Index.
    synthData_mean : np.ndarray
        Averaged bootstraped data.

    '''
    # Instantiate a random number generator and storage arrays
    synthData = np.zeros((nSteps, nSamples), dtype=float)
    
    rng = np.random.default_rng()
    kwargs = {'low' : 0,
              'high' : len(data) - 1,
              'size' : nSamples}
    
    for ii in range(nSteps):
        indeces = rng.integers(**kwargs)
        synthData[ii, :] = np.sort(data[indeces].copy())
        
    synthData_mean = np.nanmean(synthData, axis=0)
    
    # 3 ways of estimating it, looping over the nSamples dimension is the matlab direct implementation
    # Calling the confidence_interval function directly also works byt yields slightly different results
    # calling the test_CI_vX functions also works but doesnt return the exact same results.
    CI = []
    for ii in range(nSamples):
        tmp = confidence_interval(synthData[:,ii], percentile=95)
        CI.append(tmp)
    
    CI = np.array(CI).T
    
    # CI = confidence_interval(data=synthData, percentile=95, axis=0)
    return CI, synthData_mean



# --- Main classes used for the EVA analysis
class WavesEVA_Figures:
    '''
    Class used to keep the functions generating the plots together. 
    
    It is inherited by the WavesExtremeValuesAnalysis() class.
    '''
    
    @staticmethod
    def rotate_xticks(ax: mpl.axes.Axes, rotation: int|float) -> None:
        '''
        Wrapper function to rotate the x-ticks from the provided axe.

        Parameters
        ----------
        ax : mpl.axes.Axes
            Axe along which the x-ticks will be rotated.
        rotation : int|float
            Angle of rotation given in degrees.
        '''
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=rotation)
        return
    
    @staticmethod
    def plt_show_save(fout: str=None) -> None:
        '''
        Wrapper function used to either display or save a figure. If no argument
        is provided, the figure will displayed. Otherwise it will generated, 
        saved at the location pointed by fout and closed.        

        Parameters
        ----------
        fout : str|path-like, optional
            A path, or a Python file-like object. The default is None.
        '''
        if fout is None:
            plt.show()
        else:
            plt.savefig(fout)
            plt.close()
            
            fpath, fname = os.path.split(fout)
            txt = '\n{} was saved in {}\n'.format(fname, fpath)
            print(txt)
        return
    
    @staticmethod
    def scatter_hist(ax: mpl.axes.Axes, 
                     ax_histx: mpl.axes.Axes, 
                     ax_histy: mpl.axes.Axes, 
                     x: np.ndarray, y:np.ndarray) -> None:
        '''
        Wrapper function used to generate a scatter plot with its data distributions
        ploted on the exterior of its x and y- axis.

        Parameters
        ----------
        ax : mpl.axes.Axes
            The Matplotlib Axes object in which the scatter will ploted
        ax_histx : mpl.axes.Axes
            The Matplotlib Axes object in which the distribution of the data along
            the x-axis will be ploted
        ax_histy : mpl.axes.Axes
            The Matplotlib Axes object in which the distribution of the data along
            the y-axis will be ploted
        x : np.ndarray
            Data to be ploted along the x-axis.
        y : np.ndarray
            Data to be ploted along the y-axis.
        '''
        # no labels
        ax_histx.tick_params(axis="both", labelbottom=False, labeltop=False, labelleft=False, labelright=False)
        ax_histy.tick_params(axis="both", labelleft=False, labelright=False, labelbottom=False, labeltop=False)
        
        # I am too lazy to properly count the number of bins
        nBins_x = len(np.arange(np.floor(np.nanmin(x)), np.ceil(np.nanmax(x)), 0.5))
        nBins_y = len(np.arange(np.floor(np.nanmin(y)), np.ceil(np.nanmax(y)), 0.5))
        
        binned_x, bins_x = np.histogram(x, bins=nBins_x, density=True)
        binned_y, bins_y = np.histogram(y, bins=nBins_y, density=True)
        
        # Calculating the middle of each bin
        x_bins = np.array( [ _bin + (bins_x[ii+1] - _bin) / 2 for ii, _bin in enumerate(bins_x[:-1]) ] )
        y_bins = np.array( [ _bin + (bins_y[ii+1] - _bin) / 2 for ii, _bin in enumerate(bins_y[:-1]) ] )

        # Ploting the scatter plot:
        ax.scatter(x, y)
        
        # Ploting the histogram
        dBins = np.diff(x_bins).mean()
        ax_histy.bar(x_bins, binned_x, width=dBins, edgecolor='k', align='center')
        
        dBins = np.diff(y_bins).mean()
        ax_histx.barh(y_bins, binned_y, height=dBins, edgecolor='k', align='center')
        
        # Revert the axis to have the distribution ploted in the outward direction
        ax_histx.xaxis.set_inverted(True)
        ax_histy.yaxis.set_inverted(True)
        return

    
    def plot_record(self) -> None:
        '''
        Plot the timeseries fed to the class.

        '''
        if self.dout is not None:
            fname = 'figure_1_wave_record.jpeg'
            fout = os.path.join(self.dout, fname)
        else:
            fout = None
        
        # Defining the figure settings
        kwargs = {'figsize' : (8, 6),
                  'dpi' : 200,
                  'nrows' : 2,
                  'ncols' : 1,
                  'sharex' : True,
                  'sharey' : False,
                  'layout' : 'compressed'
                  }
        
        if fout is None:
            _ = kwargs.pop('figsize')
            _ = kwargs.pop('dpi')
        
        # Generate the figure
        fig, axs = plt.subplots(**kwargs)
        axs[0].plot(self.time, self.Hs)
        axs[1].plot(self.time, self.Tm)
        
        for ax in axs:
            ax.grid()
        
        axs[1].set(ylabel='Hs [m]')
        axs[1].set(xlabel='Time', ylabel='Tm [s]')
        
        self.rotate_xticks(ax=axs[1], rotation=45)
        self.plt_show_save(fout=fout)
        return
    
    def plot_peaks_over_threshold(self, xdata: np.ndarray, 
                                  ydata: np.ndarray, 
                                  xpeaks: np.ndarray, 
                                  ypeaks: np.ndarray) -> None:
        '''
        Plot the timeseries stored into the class object and add markers at each
        selected peaks

        Parameters
        ----------
        xdata : np.ndarray
            x-coordinates of the data (usually it should be a time vector).
        ydata : np.ndarray
            Data to be displayed.
        xpeaks : np.ndarray
            x-coordinates of the peaks.
        ypeaks : np.ndarray
            y-coordinates of the peaks.

        '''
        if self.dout is not None:
            fname = 'figure_2_maxima_selection.jpeg'
            fout = os.path.join(self.dout, fname)
        else:
            fout = None
            
        # Defining the figure settings
        kwargs = {'figsize' : (8, 6),
                  'dpi' : 200,
                  'nrows' : 1,
                  'ncols' : 1,
                  'layout' : 'compressed'
                  }
        
        if fout is None:
            _ = kwargs.pop('figsize')
            _ = kwargs.pop('dpi')
        
        nMaxima = len(ypeaks)
        
        fig, axs = plt.subplots(**kwargs)
        axs.plot(xdata, ydata)
        axs.plot(xpeaks, ypeaks, '.r', label='local maxima')
        
        axs.grid()
        axs.legend()
        axs.set(xlabel='Time', ylabel='Inital Guess - TWL [m]', title='{} events exceeding 99% percentile'.format(nMaxima))
        self.rotate_xticks(ax=axs, rotation=45)
        self.plt_show_save(fout=fout)
        return
    
    def plot_storm_waves_scatter(self) -> None:
        '''
        Create a scatter plot with both datasets' distribution displayed along
        the horizontal / vertical axis.

        '''
        
        if self.dout is not None:
            fname = 'figure_3_scatter_dist_Hs_Tm.jpeg'
            fout = os.path.join(self.dout, fname)
        else:
            fout = None
            
        # Defining the figure settings
        kwargs = {'figsize' : (8, 8),
                  'dpi' : 200,
                  'layout' : 'compressed',
                  'width_ratios' : (1,4),
                  'height_ratios' : (4, 1)
                  }

        if fout is None:
            _ = kwargs.pop('figsize')
            _ = kwargs.pop('dpi')
        
        
        fig, axs = plt.subplot_mosaic([['histx', 'scatter'],
                                       ['.', 'histy']],
                                      **kwargs)
        
        self.scatter_hist(axs['scatter'], axs['histx'], axs['histy'], self.HsPeaks, self.TmPeaks)
        
        for ax in [axs['scatter'], axs['histx'], axs['histy']]:
            ax.grid()
        
        axs['scatter'].set(xlabel='Hs [m]', ylabel='Tm [s]')
        
        self.plt_show_save(fout=fout)
        return
    
    def plot_storm_waves_scatter_pdf(self) -> None:
        '''
        Create a scatter plot with both datasets' PDF displayed along
        the horizontal / vertical axis.

        '''
        if self.dout is not None:
            fname = 'figure_4_scatter_pdf_Hs_Tm.jpeg'
            fout = os.path.join(self.dout, fname)
        else:
            fout = None
            
        # Defining the figure settings
        kwargs = {'figsize' : (8, 8),
                  'dpi' : 200,
                  'layout' : 'compressed',
                  'width_ratios' : (1,4),
                  'height_ratios' : (4, 1)
                  }

        if fout is None:
            _ = kwargs.pop('figsize')
            _ = kwargs.pop('dpi')
        
        # Estimate the PDF of each dataset
        x_Hs = np.arange(np.nanmin(self.HsPeaks), np.nanmax(self.HsPeaks), 0.1)
        kernel_Hs = gaussian_kde(self.HsPeaks)
        pdf_Hs = kernel_Hs.pdf(x_Hs)
        
        x_Tm = np.arange(np.nanmin(self.TmPeaks), np.nanmax(self.TmPeaks), 0.1)
        kernel_Tm = gaussian_kde(self.TmPeaks)
        pdf_Tm = kernel_Tm.pdf(x_Tm)
        
        
        # Solution found in https://matplotlib.org/stable/gallery/lines_bars_and_markers/scatter_hist.html
        fig, axs = plt.subplot_mosaic([['pdf_x', 'scatter'],
                                       ['.', 'pdf_y']],
                                      **kwargs)
        
        axs['scatter'].scatter(self.HsPeaks, self.TmPeaks)
        axs['pdf_x'].plot(pdf_Tm, x_Tm)
        axs['pdf_y'].plot(x_Hs, pdf_Hs)
        
        for ax in [axs['scatter'], axs['pdf_x'], axs['pdf_y']]:
            ax.grid()
        
        # no labels
        axs['pdf_x'].tick_params(axis="both", labelbottom=False, labeltop=False, labelleft=False, labelright=False)
        axs['pdf_y'].tick_params(axis="both", labelleft=False, labelright=False, labelbottom=False, labeltop=False)
        
        # Revert the axis to have the distribution ploted in the outward direction
        axs['pdf_x'].xaxis.set_inverted(True)
        axs['pdf_y'].yaxis.set_inverted(True)
        
        axs['scatter'].set(xlabel='Hs [m]', ylabel='Tm [s]')
        self.plt_show_save(fout=fout)
        return
    
    def plot_synthetic_dataset(self) -> None:
        '''
        Plot the estimated dataset of extreme values. Both historical and extreme
        wave conditions are also displayed for comparison with the synthetic
        extreme values

        '''
        if self.dout is not None:
            fname = 'figure_5_synthetic_extremes.jpeg'
            fout = os.path.join(self.dout, fname)
        else:
            fout = None
            
        # Defining the figure settings
        kwargs = {'figsize' : (8, 8),
                  'dpi' : 200,
                  'layout' : 'compressed',
                  'nrows' : 1,
                  'ncols' : 1
                  }

        if fout is None:
            _ = kwargs.pop('figsize')
            _ = kwargs.pop('dpi')
        
        
        pkwargs = {'linestyle' : '',
                   'marker' : '.',
                   'markersize' : 1.5}
        
        pkwargs2 = {'linestyle' : '',
                    'marker' : 'o',
                    'markersize' : 5}
        
        xlim = (np.floor(np.nanmin(self.Hs)), np.ceil(np.nanmax(self.Hs_synth)))
        ylim = (np.floor(np.nanmin(self.Tm)), np.ceil(np.nanmax(self.Tm_synth)))
        
        fig, axs = plt.subplots(**kwargs)
        axs.plot(self.Hs, self.Tm, color='gray', label='Historical conditions', **pkwargs)
        axs.plot(self.Hs_synth, self.Tm_synth, color='brown', label='Synthetic Extremes', **pkwargs)
        axs.plot(self.HsPeaks, self.TmPeaks, color='black', label='Historical Extremes', **pkwargs2)
        
        axs.grid()
        axs.legend()
        axs.set(xlabel='Hs [m]', ylabel='Tm [s]', xlim=xlim, ylim=ylim)
        self.plt_show_save(fout=fout)
        return
    
    def plot_average_recurence_interval(self) -> None:
        '''
        Plot the Average Recurence Interval, its 95% confidence interval and
        the historical estimation.

        Parameters
        ----------
        Hs_synth : np.ndarray
            Synthetic dataset.
        returnPeriod : np.ndarray
            Return Period, used as x-coordinates.
        returnPeriod_synth : np.ndarray
            Return Period of the synthetic dataset, used as x-coordinates.

        '''
        if self.dout is not None:
            # fname = 'figure_6_average_recurence_interval.jpeg'
            fname = 'figure_9_extreme_value_analysis.jpeg'
            fout = os.path.join(self.dout, fname)
        else:
            fout = None
            
        # Defining the figure settings
        kwargs = {'figsize' : (4, 4),
                  'dpi' : 200,
                  'layout' : 'compressed',
                  'nrows' : 1,
                  'ncols' : 1
                  }

        if fout is None:
            _ = kwargs.pop('figsize')
            _ = kwargs.pop('dpi')
        
        
        factor = len(self.HsPeaks) / self.nYears
        
        x1 = self.returnPeriod / factor
        x2 = self.returnPeriod_synth / factor
        
        y1 = np.sort(self.HsPeaks)
        y2 = np.sort(self.Hs_synth_mc)
        y3_lower = np.sort(self.CI[0,:])
        y3_upper = np.sort(self.CI[1,:])
        
        # Estimating the axis limits
        xlim = (1, 100)
        msk = x2 < xlim[1]
        ylim = (1, np.ceil(y3_upper[msk][-1]))
        
        
        fig, axs = plt.subplots(**kwargs)
        axs.semilogx(x2, y2, '-k', label='Synthetic', linewidth=0.8)
        axs.semilogx(x2, y3_lower, '--k', label='95% CI - Scipy implementation', linewidth=0.7)
        axs.semilogx(x2, y3_upper, '--k', linewidth=0.7)
        axs.semilogx(x1, y1, 'r', linestyle='', marker='.', label='historical', markersize=1)
        
        axs.grid(which='major', axis='x')
        axs.grid(which='minor', axis='x', linestyle=':')
        axs.grid(which='major', axis='y')
        
        axs.legend()
        axs.set(xlabel='Average Recurence Interval (years)', ylabel='Hs [m]', xlim=xlim, ylim=ylim)
        self.plt_show_save(fout=fout)
        return
    
    def plot_synthetic_comparison(self):
        
        # Estimate the PDF of each dataset
        # Hs peaks
        peaks_Hs = np.arange(np.nanmin(self.HsPeaks), np.nanmax(self.HsPeaks), 0.1)
        kernel_Hs_peaks = gaussian_kde(self.HsPeaks)
        pdf_Hs_peaks = kernel_Hs_peaks.pdf(peaks_Hs)
        
        # Hs synthetic
        synth_Hs = np.arange(np.nanmin(self.Hs_synth), np.nanmax(self.Hs_synth), 0.1)
        kernel_Hs = gaussian_kde(self.Hs_synth)
        pdf_Hs_synth = kernel_Hs.pdf(synth_Hs)
        
        # Tm peaks
        peaks_Tm = np.arange(np.nanmin(self.TmPeaks), np.nanmax(self.TmPeaks), 0.1)
        kernel_Tm_peaks = gaussian_kde(self.TmPeaks)
        pdf_Tm_peaks = kernel_Tm_peaks.pdf(peaks_Tm)
        
        # Tm syntethic
        synth_Tm = np.arange(np.nanmin(self.Tm_synth), np.nanmax(self.Tm_synth), 0.1)
        kernel_Tm = gaussian_kde(self.Tm_synth)
        pdf_Tm_synth = kernel_Tm.pdf(synth_Tm)
        
        
        fig, axs = plt.subplots(1,2)
        axs[0].plot(peaks_Hs, pdf_Hs_peaks, label='Hs - peaks')
        axs[0].plot(synth_Hs, pdf_Hs_synth, label='Hs - synth')
        
        axs[1].plot(peaks_Tm, pdf_Tm_peaks, label='Tm - peaks')
        axs[1].plot(synth_Tm, pdf_Tm_synth, label='Tm - synth')
        
        for ax in axs:
            ax.grid()
            ax.legend()
        
        plt.show()
        return
    
    


class WavesExtremeValuesAnalysis(WavesEVA_Figures):
    '''
    Main class used to apply the Extrenme Values Analysis.
    
    '''
    
    def __init__(self, Hs: np.ndarray, 
                 Tm: np.ndarray, 
                 Tp: np.ndarray, 
                 time: np.ndarray[np.datetime64], 
                 maxARI: int=500, 
                 synthYears: int=10000, 
                 plot_all: bool=False, 
                 dout: str=None) -> None:
        '''
        Note: Figures generation is included in the current implementation, 
        to ignore them (and avoid ploting) set plot_all=False.
        
        If the figures are to be created, the user has the choice to provide a 
        path pointing to the output directory (dout), in which case the figure
        will created, saved and closed (i.e., you will not see it).
        
        The figures can be displayed during the run by setting plot_all=True and
        dout=None.

        Parameters
        ----------
        Hs : np.ndarray
            Significant Wave Height (Hm0 or H1/3) given in meters.
        Tm : np.ndarray
            Mean period (Tm01 or Tz) given in seconds.
        Tp : np.ndarray
            Peak period (Tp or T1/3) given in seconds.
        time : np.ndarray[np.datetime64]
            Time vector.
        maxARI : int, optional
            Maximum Average Recurence Interval given in years. The default is 500.
        synthYears : int, optional
            Number of synthetic years to be generated during the analysis. The default is 10000.
        plot_all : bool, optional
            Swtich to generate the plots or ignore them. The default is False.
        dout : str, optional
            A path pointing to the directory where the plots will be saved. The default is None.

        '''
        self.time = time
        self.Hs = Hs
        self.Tm = Tm
        self.Tp = Tp
        
        # Processing parameters
        self.synthYears = synthYears
        self.nYears = len(np.arange(self.time[0].astype(datetime).year, self.time[-1].astype(datetime).year)) + 1
        self.maxARI = maxARI
        
        # Extreme values present in the dataset
        self.HsPeaks = None
        self.TmPeaks = None
        
        # Synthetic extrema values (defined as placeholder for now)
        self.Hs_synth = None
        self.Tm_synth = None
        
        # Synthetic extreme Hs generated by Monte Carlo simunation (defined as placeholder for now)
        self.Hs_synth_mc = None
        self.returnPeriod_synth = None
        
        # Confidence Interval (2, N) -> [0,:] -> lower threshold, [1,:] -> upper threshold
        self.CI = None
        
        # Ploting options
        self.plot_all = plot_all
        self.dout = dout
        
    def run(self, percentile: int=99, nSteps: int=2000) -> None:
        '''
        Wrapping function to run the Extreme Values Analysis once the class has 
        been initialized.

        Parameters
        ----------
        percentile : int, optional
            Percentile used to identify the peaks in the original record. The default is 99.
        nSteps : int, optional
            Number of iterations used during the monte carlo simulation. The default is 2000.

        '''
        if self.plot_all:
            self.plot_record()
            
        self.peak_over_threshold(percentile=percentile)
        
        if False:
            self.generalized_pareto()
        else:
            self.generate_synthetic_extremes()
        
        # Monte Carlo simulation + EVA plot
        self.monte_carlo_simulation(nSteps=nSteps)
        self.plot_average_recurence_interval()
        return
    
    
    def maxima_selection(self, data: np.ndarray,
                         threshold: float, 
                         tmin: int=1) -> tuple[list[np.ndarray], list[np.datetime64], list[np.ndarray], list[np.timedelta64]]:
        '''
        Select local maxima from the provided data. A minimum time interval is
        needed between two consecutive values for the second to be kept.

        Parameters
        ----------
        data : np.ndarray
            Dataset.
        threshold : float
            Threshold above which the data will be selected.
        tmin : int, optional
            Minimum duration between two selected consecutive values, given in 
            days. The default is 1.

        Returns
        -------
        dataEvents : list[np.ndarray]
            Maximum value during the selected event.
        timeEvents : list[np.datetime64]
            Time at which the value was observed.
        timeVectorEvents : list[np.ndarray]
            List containing the timesteps of each event.
        durationEvents : list[np.timedelta64]
            List containing the duration of each event.

        '''
        #tmin -> nombre de jours entre 2 storm events pour les considerer independants
        dt_threshold = np.timedelta64(tmin, 'D')
        
        # Find the values where the data is higher than the threshold
        msk = data > threshold
        
        data_extreme = data[msk].copy()
        time_extreme = self.time[msk].copy()
        
        # Create some objects for data storage
        timeVectorEvents = []
        dataEvents = []
        timeEvents = []
        durationEvents = []
        condition = False
        
        for ii in range(len(time_extreme)):
            t0 = time_extreme[ii]
            
            # Check if this timestep was already accounted for, if so the condition
            # keyword is set to True and we jump to the next timestep 
            for times in timeVectorEvents:
                if t0 in times:
                    condition = True
                    break
                else:
                    condition = False
            
            if condition:
                continue
            
            # Estimate all points related to an event
            dt = abs(time_extreme - t0).astype('timedelta64[D]')
            msk_event = dt <= dt_threshold
            
            timeVectorEvent = time_extreme[msk_event].copy()
            vmax_event = np.nanmax(data_extreme[msk_event])
            timeEvent = timeVectorEvent[np.nanargmax(data_extreme[msk_event])]
            duration_event = (timeVectorEvent[-1] - timeVectorEvent[0]).astype('timedelta64[D]')
            
            timeEvents.append(timeEvent)
            timeVectorEvents.append(timeVectorEvent)
            dataEvents.append(vmax_event)
            durationEvents.append(duration_event)
        return dataEvents, timeEvents, timeVectorEvents, durationEvents
    
    def check_wave_steepness(self, Hs: np.ndarray, Tm: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        '''
        Remove values from the estimated synthetic datasets that do not satisfy 
        the following conditions:
            1. Synthetic Hs has to be superior to the minimal historical Hs value
            2. Synthetic Hs has to be inferior to the maximal historical Tp value
            3. Wave steepness has to be verified

        Parameters
        ----------
        Hs : np.ndarray
            Synthetic Significant wave height.
        Tm : np.ndarray
            Synthetic Mean Period.

        Returns
        -------
        Hs : np.ndarray
            Synthetic Significant wave height.
        Tm : np.ndarray
            Synthetic Mean Period.

        '''
        # Estimating some values that will be used later on 
        tpf = np.nanmean(self.Tm / self.Tp)
        factor = Hs * np.power(tpf / Tm, 2)
        msk = ((factor < 0.07) & (Hs >= np.nanmin(self.Hs)) & (Tm <= np.nanmax(self.Tp)))
        return Hs[msk], Tm[msk]
    
    def peak_over_threshold(self, percentile: int|float=99) -> None:
        '''
        Select the values over a threshold defined based on the percentile
        of the estimated water level (used to link Tm and Hs).

        Parameters
        ----------
        percentile : int|float, optional
            Percentile used to identify the peaks in the original record. The default is 99.

        '''
        # Create a relation between H0 and Tm based on Stockdon 2006
        g = PhysicalConstants.gravity_acceleration
        L0 = g*np.power(self.Tm, 2) / (2 * np.pi)
        H0L0 = self.Hs * L0
        wave_setup = 0.043 * np.sqrt(H0L0)
        
        # Independant maxima selection
        threshold_value = np.nanpercentile(wave_setup, percentile)
        dataEvents, timeEvents, timeVectorEvents, durationEvents = self.maxima_selection(data=wave_setup, threshold=threshold_value)
        
        HsPeaks = np.zeros(len(dataEvents), dtype=float)
        TmPeaks = np.zeros(len(dataEvents), dtype=float)
        timePeaks = np.empty(len(dataEvents), dtype='datetime64[s]')
        
        for ii, t_i in enumerate(timeEvents):
            # Here the times should be the same but looking for the timestep that minimizes 
            # the time gap is more robust than looking for an exact match between
            # individual values in two numpy arrays
            idx = np.nanargmin(abs(self.time - t_i))
            HsPeaks[ii] = self.Hs[idx]
            TmPeaks[ii] = self.Tm[idx]
            timePeaks[ii] = self.time[idx]
        
        # Store the data into the object
        self.HsPeaks = HsPeaks.copy()
        self.TmPeaks = TmPeaks.copy()
        
        if self.plot_all:
            # Ploting the selected maxima
            xpeaks = np.array(timeEvents, dtype='datetime64[s]')
            ypeaks = np.array(dataEvents, dtype=float)
            self.plot_peaks_over_threshold(self.time, wave_setup, xpeaks, ypeaks)
            
            # Ploting the scatter + histogram
            self.plot_storm_waves_scatter()
            self.plot_storm_waves_scatter_pdf()
        return
    
    def generalized_pareto(self):
        nSamples = int(len(self.HsPeaks) * self.synthYears / self.nYears)
        
        b, loc, scale = stats.genpareto.fit(self.HsPeaks, floc=self.HsPeaks.mean(), fscale=self.HsPeaks.std())
        rv = stats.genpareto.rvs(c=b, size=nSamples)
        
        rv2 = statistical_standardization(rv)
        Hs_synth = np.nanmean(self.HsPeaks) + rv2 * np.nanstd(self.HsPeaks)
        
        self.Hs_synth = Hs_synth.copy()
        
        print('Hs Peaks: ', round(self.HsPeaks.mean(), 2), round(self.HsPeaks.std(), 2))
        print('Genpareto Fit: ', round(b, 2), round(loc, 2), round(scale, 2))
        print('Sample Out: ', round(self.Hs_synth.mean(), 2), round(self.Hs_synth.std(), 2))
        print('rv: ', round(rv.mean(), 2), round(rv.std(), 2))
        
        return
    
    def generate_synthetic_extremes(self) -> None:
        '''
        Generate synthetic extremas through a copula for Tm and Hs based on
        their marginal distributions. Both (marginals) distributions are estimated
        using a Gaussian Kernel Density Estimation.

        '''
        # Standardize the data
        Hsi = statistical_standardization(self.HsPeaks)
        Tmi = statistical_standardization(self.TmPeaks)
        
        # Prepare the data
        data = np.zeros((len(Hsi), 2), dtype=float)
        data = pd.DataFrame({'x' : Hsi.copy(), 'y' : Tmi.copy()}) # it needs to be a pd.DataFrame or it will use the default distribution to fit the data
        
        # Lazy but straigtforward way to estimate the number of years present in the dataset
        nSamples = int(len(Hsi) * self.synthYears / self.nYears)
        
        # Estimation of the marginals distributions + creation of artificial dataset
        # Not sure about the factor 2, here is the comment in the original code: 
        # "Simulate double of expected number of extremes to remove those that 
        # does not satisfy wave steepness condition (Dag Myrhaug, 2017)"
        copula = GaussianMultivariate(distribution={'x' : GaussianKDE,
                                                    'y' : GaussianKDE})
        copula.fit(data)
        synthetic_data = copula.sample(nSamples*2).to_numpy()
                

        # Transform the synthetic dataset back to its original distribution 
        Hs_synth = np.nanmean(self.HsPeaks) + synthetic_data[:,0] * np.nanstd(self.HsPeaks)
        Tm_synth = np.nanmean(self.TmPeaks) + synthetic_data[:,1] * np.nanstd(self.TmPeaks)
        
        # Account for wave steepness and outliers (e.g. Hs_synth < min(Hs), ...)
        Hs_synth, Tm_synth = self.check_wave_steepness(Hs=Hs_synth, Tm=Tm_synth)
        
        # Store the data in the object
        self.Hs_synth = Hs_synth.copy()
        self.Tm_synth = Tm_synth.copy()
        
        if self.plot_all:
            self.plot_synthetic_dataset()
        return
    
    def monte_carlo_simulation(self, nSteps: int=2000) -> None:
        '''
        Monte Carlo simulation.

        Parameters
        ----------
        nSteps : int, optional
            Number of iterations used for the simulation. The default is 2000.

        '''
        # Estimate the sample size used for the boostraping scheme
        nSamples = int(len(self.HsPeaks) * self.maxARI / self.nYears )
        self.CI, Hs_synth_mc = bootstrapping(data=self.Hs_synth, nSamples=nSamples, nSteps=nSteps)

        # nExcProb (Non-exceedance Propability) -> empirical probability of a value not being exceed in the dataset
        nExcProb = np.arange(1, len(self.HsPeaks)+1) / (len(self.HsPeaks) + 1)
        returnPeriod = 1 / (1 - nExcProb)
        
        nExcProb_synth = np.arange(1, len(Hs_synth_mc)+1) / (len(Hs_synth_mc) + 1)
        returnPeriod_synth = 1 / (1 - nExcProb_synth)
        
        # Store the results
        self.Hs_synth_mc = Hs_synth_mc
        self.returnPeriod_synth = returnPeriod_synth
        self.returnPeriod = returnPeriod
        return
    
    
    
    
    
    
