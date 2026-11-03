# -*- coding: utf-8 -*-
"""
Created on Fri Mar 21 09:09:36 2025

@author: gregoires
"""


import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.ticker import MultipleLocator
import numpy as np
import os
from scipy.stats import circmean
from shapely import Point, get_coordinates
import sys
from windrose import WindroseAxes


from . fig_tools import get_map_grid_definition, get_waverose_settings, get_custom_colormap, remove_spines
from utils.data_processing import DataProcessing
from utils.pyEVA import PhysicalConstants




def plot_area_map(bbox, nearbyLocations, xloc, yloc, mapType, savedir):
    
    savename =  'figure_1_{}.jpeg'.format(mapType)
    fout = os.path.join(savedir, savename)
    
    # Arguments used in the plot
    fkwargs = {
        'nrows': 1,
        'ncols': 1,
        'figsize': (3.5, 3.5),
        'dpi': 200,
        'layout': 'compressed',
        'subplot_kw': {
            # Centred on the dateline so Pacific boxes crossing 180 (Fiji, Tuvalu) are not split
            'projection': ccrs.PlateCarree(central_longitude=180)
        }
    }

    # Coordinates (bbox, locations, ticks) are plain lon/lat
    lonlat = ccrs.PlateCarree()

    # Extent of the map
    coord = get_coordinates(bbox)
    extent = (coord[:,0].min(), coord[:,0].max(), coord[:,1].min(), coord[:,1].max())

    pkwargs = {
        'markeredgecolor' : 'k',
        'markersize' : 7,
        'marker' : 'o',
        'linestyle' : '',
        'zorder' : 9999
    }
    
    # 
    xticks, yticks = get_map_grid_definition(bbox=bbox)
    xticks = (xticks + 180) % 360 - 180     # gridlines expect -180..180, so 188 -> -172 (172°W)
    
    # Basemap doesn't display these points otherwise (i.e., passing a single float sometimes doesnt work)
    x = np.array([xloc])
    y = np.array([yloc])
    
    
    fig, axs = plt.subplots(**fkwargs)
    axs.set_extent(extent, crs=lonlat)

    axs.add_feature(cfeature.LAND, facecolor='lightgrey')
    # axs.add_feature(cfeature.OCEAN)
    axs.coastlines(resolution='10m', color='k', linewidth=0.5)

    # transform: points are lon/lat (0-360 or -180..180), projected onto the map
    # The location itself is drawn last so a nearby location at the same point (e.g. Fongafale / Funafuti) doesn't hide it
    if nearbyLocations.size >= 2:
        axs.plot(nearbyLocations[:,0], nearbyLocations[:,1], color='g', transform=ccrs.Geodetic(), **pkwargs)
    axs.plot(x, y, color='r', transform=ccrs.Geodetic(), **pkwargs)

    # Manage the axis and their legends
    gl = axs.gridlines(
        crs=lonlat,
        draw_labels={'top': False, 'bottom': True, 'left': True, 'right': False},
        xlocs=xticks,
        ylocs=yticks,
        xlabel_style={'rotation': 45, 'fontsize': 6},
        ylabel_style={'fontsize': 6},
        color='grey',
        linestyle='--',
        linewidth=0.55
    )

    plt.savefig(fout)
    plt.close()
    return


def plot_fancy_rose(data, direction, var, savedir, largeSevere=False):
    
    if var == 'Hm0':
        figname = 'figure_2_annual_wave_rose.jpeg'
        dbins = 0.25
        
        # vmax = np.ceil(np.nanmax(data))
        vmax = 3
        bins = np.arange(0, vmax + dbins, dbins)
        units = '[m]'
        cb_lbl = 'Wave Height '
        
    elif var == 'wind':
        figname = 'figure_11_annual_wind_rose.jpeg'
        dbins = 1
        
        # vmax = np.ceil(np.nanmax(data))
        vmax = 12
        bins = np.arange(0, vmax + dbins, dbins)
        units = '[m/s]'
        cb_lbl = 'Wind Speed '
    
    if largeSevere:
        threshold = np.percentile(data, 99)
        msk = data > threshold
        
        data = data[msk].copy()
        direction = direction[msk].copy()
        
        # vmax = np.ceil(np.nanmax(data))
        vmax = 5
        vmin = max(0, np.floor(np.nanmin(data)))
        
        bins = np.arange(vmin, vmax + dbins, dbins)
        units = '[m]'
        figname = 'figure_6_large_severe_wave_rose.jpeg'
        
    
    # Generate the ouput path
    fout = os.path.join(savedir, figname)
    
    # Define some of the plot parameters
    nsector = 18
    dradius = 10
    dtheta = 360 / nsector
    
    # Define the labels and the angles at which the grid will be created
    minor_angles = np.arange(dtheta, 360, dtheta)
    val = (90 - minor_angles)
    val[val < 0] += 360
    
    # Dirty way to remove the dupplicate value (W and 270 degrees)
    minor_angles = minor_angles[val!=270]
    val = val[val!=270]
    minor_lbl = [ '{:.0f}°'.format(v) for v in val ]
    
    major_angles = [0, 90, 180, 270]
    major_lbl = ['E', 'N', 'W', 'S']
    
    # Arguments used in the plot
    fkwargs = {
        'nrows': 1,
        'ncols': 1,
        'figsize': (5, 4.5),
        'dpi': 200,
        'subplot_kw': {
            'projection': 'windrose'
        }
    }
    
    # Histogram and colormap kwargs
    nColors = np.ceil(vmax / dbins).astype(int)
    _, norm, bounds = get_custom_colormap(nColors=nColors, vmin=0, vmax=vmax)
    
    cmap = get_custom_colormap()
    ticks = bounds[::2] if len(bounds) > 10 else bounds.copy()
    kwargs = {
        'nsector' : nsector,
        'opening' : 1,
        'normed' : True, 
        'bins' : bins, 
        'cmap' : cmap,
        'blowto' : False, # i.e., we are ploting following the FROM convention
        'edgecolor' : 'black',
        'zorder' : 9999
    }
    
    # Colorbar kwargs
    cb_lbl = cb_lbl+units
    cbkwargs = {
        'location' : 'right',
        'pad': 0.075,
        'extend' : 'max',
        'format' : '{x:.1f}',
        'drawedges' : True,
        'norm' : norm,
        'ticks' : ticks,
        'boundaries' : bounds,
    }

    # Major ticks params
    matkwargs = {
        'axis' : 'x', 
        'labelsize' : 8,
        'labelcolor' : 'black',
        'pad' : -3
    }

    # Minor ticks params
    mitkwargs = {
        'axis' : 'x', 
        'labelsize' : 7, 
        'labelcolor' : 'gray', 
        'pad' : -3.5
    }


    # Create the figure
    fig, ax = plt.subplots(**fkwargs)
    
    ax.bar(direction, data, **kwargs)
    
    # Get the parameters to generate the grid and the ticks
    rmax, locs, rticks, yticks_labels, thetagrids = get_waverose_settings(ax, dtheta, dradius)    
    
    # Remove the automatic gridlines and generating new ones which corresponds to each sectors
    ax.grid()

    # Create the angular grid
    for angle in np.deg2rad(thetagrids):
        ax.plot([angle, angle], [0, rmax], linestyle='-', color='gray', linewidth=0.5, zorder=-10)
    
    # Create the radial grid
    theta = np.linspace(0, 2 * np.pi, 500)
    for r_val in locs:
        ax.plot(theta, [r_val] * len(theta), color='gray', linestyle='-', linewidth=0.5, zorder=-10)
    
    # Setting up the radial labels
    ax.set_rmax(rmax)
    ax.set_rticks(ticks=[locs[0]], labels=[yticks_labels[0]], color='k')
    ax.set_rlabel_position(rticks)
    
    # Setting up the angular labels
    ax.set_xticks([])   
    ax.set_xticks(np.deg2rad(major_angles))
    ax.set_xticklabels(major_lbl, fontweight='bold')
    ax.tick_params(**matkwargs)

    # Ensure the patches are above the gridlines
    for child in ax.get_children():
        if isinstance(child, Rectangle):
            child.set_zorder(2)
            child.set(linewidth=0.5)

    # Display a colorbar instead of a legend
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, **cbkwargs)
    cbar.set_label(label=cb_lbl, labelpad=15)

    # Create the secondary axis used for the minor ticks
    ax2 = ax.figure.add_axes(ax.get_position(), projection='windrose', frameon=False, anchor='C')
    ax2.set_in_layout(True)

    # Work out the radius of the plot
    ax2.set_rmax(rmax)
    ax2.set_yticklabels([])

    # Work out the minor ticks along the outer radar plot
    ax2.set_xticks(np.deg2rad(minor_angles))
    ax2.set_xticklabels(minor_lbl)
    ax2.tick_params(**mitkwargs)

    ax2.grid(False)
        

    plt.savefig(fout)
    plt.close()
    return


def plot_seasonal_rose(data, direction, msk, savedir):
    
    fname = 'figure_3_seasonal_wave_rose.jpeg'
    fout = os.path.join(savedir, fname)
    
    dbins = 0.25
    vmax = 3
    bins = np.arange(0, vmax+dbins, dbins)
    units = '[m]'
    titles = ['Dec Jan Feb', 'Mar Apr May', 'Jun Jul Aug', 'Sep Oct Nov']

    seasonal_data = []
    seasonal_direction = []
    
    # The masks are pre-generated per season
    for ii in range(4):
        tmp_msk = msk[:,ii].copy()
        seasonal_data.append(data[tmp_msk])
        seasonal_direction.append(direction[tmp_msk])
    
    # Some parameters
    nsector = 18
    dradius = 10
    dtheta = 360 / nsector
    
    # Plyaing with the colormap
    nColors = np.ceil(vmax / dbins).astype(int)
    cmap, norm, bounds = get_custom_colormap(nColors=nColors, vmin=0, vmax=vmax)

    # Define the labels and the angles at which the grid will be created
    minor_angles = np.arange(dtheta, 360, dtheta)
    val = (90 - minor_angles)
    val[val < 0] += 360
    
    # Dirty way to remove the dupplicate value (W and 270 degrees)
    minor_angles = minor_angles[val!=270]
    val = val[val!=270]
    minor_lbl = [ '{:.0f}°'.format(v) for v in val ]
    
    major_angles = [0, 90, 180, 270]
    major_lbl = ['E', 'N', 'W', 'S']
    
    # Arguments used in the plot
    fkwargs = {
        'nrows': 2,
        'ncols': 2,
        'figsize': (7, 5),
        'dpi': 200,
        'subplot_kw': {
            'projection': 'windrose'
        },
        'gridspec_kw': {
            'hspace': 0.4,  # Vertical Space between subplots
            'wspace': 0.4   # Horizontal space between subplots
        }
    }

    # Figure kwargs
    cmap = get_custom_colormap()
    ticks = bounds[::2] if len(bounds) > 10 else bounds.copy()
    kwargs = {
        'nsector' : nsector,
        'opening' : 1,
        'normed' : True, 
        'bins' : bins, 
        'cmap' : cmap,
        'blowto' : False, # i.e., we are ploting following the FROM convention
        'edgecolor' : 'black',
        'zorder' : 9999
    }
    
    # Colorbar kwargs
    cbkwargs = {
        'location' : 'right',
        'pad': 0.075,
        'extend' : 'max',
        'format' : '{x:.2f}',
        'drawedges' : True,
        'norm' : norm,
        'ticks' : ticks,
        'boundaries' : bounds
    }

    # Subplots title params
    stkwargs = {
        'pad' : 4,
        'fontsize' : 9
    }

    # Major ticks params
    matkwargs = {
        'axis' : 'x', 
        'labelsize' : 6,
        'labelcolor' : 'black',
        'pad' : -3
    }

    # Minor ticks params
    mitkwargs = {
        'axis' : 'x', 
        'labelsize' : 6,
        'labelcolor' : 'gray', 
        'pad' : -3.5
    }
    
    fig, axs = plt.subplots(**fkwargs)
    
    axs[0,0].bar(seasonal_direction[0], seasonal_data[0], **kwargs)
    axs[0,1].bar(seasonal_direction[1], seasonal_data[1], **kwargs)
    axs[1,0].bar(seasonal_direction[2], seasonal_data[2], **kwargs)
    axs[1,1].bar(seasonal_direction[3], seasonal_data[3], **kwargs)
    
    # Iterate over the subplots to estimate how to setup the grid
    rmax = []
    for ax in axs.flatten():
        tmp, *_ = get_waverose_settings(ax, dtheta, dradius)
        rmax.append(tmp)

    # Use the one maximising rmax value
    idx = np.argmax(rmax)
    rmax, locs, rticks, yticks_labels, thetagrids = get_waverose_settings(axs.flatten()[idx], dtheta, dradius)
    
    # Remove the automatic gridlines and generating new ones which corresponds to each sectors
    for ii, ax in enumerate(axs.flatten()):
        ax.grid()

        # Create the angular grid
        for angle in np.deg2rad(thetagrids):
            ax.plot([angle, angle], [0, rmax], linestyle='-', color='gray', linewidth=0.5, zorder=-10)
        
        # Create the radial grid
        theta = np.linspace(0, 2 * np.pi, 500)
        for r_val in locs:
            ax.plot(theta, [r_val] * len(theta), color='gray', linestyle='-', linewidth=0.5, zorder=-10)
        
        ax.set_rmax(rmax)
        ax.set_rticks(ticks=[locs[0]], labels=[yticks_labels[0]], color='k')
        ax.set_rlabel_position(rticks)
        
        # Setting up the angular labels
        ax.set_xticks([])   
        ax.set_xticks(np.deg2rad(major_angles))
        ax.set_xticklabels(major_lbl, fontweight='bold')
        ax.tick_params(**matkwargs)

        # Set up the title
        ax.set_title(titles[ii], **stkwargs)

        # Ensure the patches are above the gridlines
        for child in ax.get_children():
            if isinstance(child, Rectangle):
                child.set_zorder(2)
                child.set(linewidth=0.5)
    
    
    # Display a colorbar instead of a legend
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=axs, **cbkwargs)
    cbar.set_label(label='Wave Height [m]', labelpad=15)

    for ax in axs.flatten():
        ax2 = ax.figure.add_axes(ax.get_position(), projection='windrose', frameon=False, anchor='C')
        ax2.set_in_layout(True)

        # Work out the radius of the plot
        ax2.set_rmax(rmax)
        ax2.set_yticklabels([])

        # Work out the minor ticks along the outer radar plot
        ax2.set_xticks(np.deg2rad(minor_angles))
        ax2.set_xticklabels(minor_lbl)
        ax2.tick_params(**mitkwargs)

        ax2.grid(False)
        

    plt.savefig(fout)
    plt.close()
    return



#TODO: comprendre pourquoi il n'y a pas de variabilite annuelle pour les directions Betio 
def plot_wave_variability(Hs, Tp, Dirp, msk, savedir, monthly=True, years=None):
    
    if monthly:
        x = np.arange(1, 13)
        xticks = np.arange(1, 13)
        xticklbls = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        fname = 'figure_4_monthly_wave_variability.jpeg'
    else:
        dx = 5
        x = years
        xticks = np.arange(1980, years.max()+dx, dx)
        xticklbls = [ '{:.0f}'.format(v) for v in xticks ]
        fname = 'figure_5_yearly_wave_variability.jpeg'

    fout = os.path.join(savedir, fname)


    p1 = np.zeros(len(x))
    p2 = p1.copy()
    
    Hs_x = p1.copy()
    Tp_x = p1.copy()
    Dirp_x = p1.copy()
    
    u_ii = p1.copy()
    v_ii = p1.copy()
    
    for ii in range(len(x)):
        mskYear = msk[:,ii]

        # Estimating the average values
        Hs_x[ii] = np.nanmean(Hs[mskYear])
        Tp_x[ii] = np.nanmean(Tp[mskYear])
        
        # Converting the data back to a "traditional" reference (i.e., East = 0)
        angles = Dirp[mskYear].copy()
        angles = angles[np.isfinite(angles)]
        angles += 270                       # (-> 90 + 180), 90 to rotate back to East = 0 and +180 to display directions TO
        angles[angles > 360] -= 360
        angles[angles < 0] += 360
        Dirp_x[ii] = circmean(angles, high=360, low=0)
        
        # Retrieving the 10% and 90% smaller / higher values
        p1[ii] = np.nanpercentile(Hs[mskYear], 10)
        p2[ii] = np.nanpercentile(Hs[mskYear], 90)
        
    
    # Estimating the U/V components of the vector
    unitary = np.ones(x.shape)
    u_ii, v_ii = DataProcessing.pol2cart(unitary, Dirp_x)

    # Define the axis limits
    ylim = (0, np.ceil(max(p2)))
    ylim2 = (np.floor(min(Tp_x)), np.ceil(max(Tp_x)))

    # Define the ticks (y-, y2-axis)
    dy = 0.5
    yticks = np.arange(0, ylim[1] + dy, dy)
    yticklbls = [ '{:.1f}'.format(v) for v in yticks ]

    dy2 = 1
    y2ticks = np.arange(ylim2[0], ylim2[1] + dy2, dy2)
    y2ticklbls = [ '{:.0f}'.format(v) for v in y2ticks ]
    
    # --- Parameters definition
    # Define the figure params
    fkwargs = {
        'nrows' : 1,
        'ncols' : 1,
        'figsize' : (6.5, 2),
        'dpi' : 200,
        'layout' : 'compressed'
    }

    # Define quiver parameters
    qkwargs = {
        'pivot' : 'middle',      # Anchor point
        'angles' : 'uv',         # Coordinate reference to be used for the angles
        'color' : 'black',       # Arrows color
        'zorder' : 10,           # Ploting order (0 (beneath) -> 999 (above))
        'units' : 'dots',        # Units used for the arrows dimension
        'width' : 4,
        'scale' : 6,
        'scale_units' : 'inches',
        'headaxislength' : 3.5,
        'headlength' : 4,
        'headwidth' : 3
    }

    # Define the x-axis ticks
    xminorLocator = MultipleLocator(1)
    xtkwargs = {
        'ticks' : xticks,
        'labels' : xticklbls
    }


    # Define the y-axis ticks and labels
    yminorLocator = MultipleLocator(0.25)
    ytkwargs = {
        'ticks' : yticks,
        'labels' : yticklbls,
    }

    ylkwargs = {
        'ylabel' : 'Wave Height [m]',
        'color' : 'black',
        'fontweight' : 'normal'
    }

    # Define the second y-axis ticks and labels
    y2tkwargs = {
        'ticks' : y2ticks,
        'labels' : y2ticklbls,
        'color' : 'red',
    }

    y2lkwargs = {
        'ylabel' : 'Wave Period [s]',
        'color' : 'red',
        'fontweight' : 'normal'
    }

    fig, axs = plt.subplots(**fkwargs)
    # Ploting on the left y-axis
    axs.plot(x, Hs_x, 'k', linewidth=0.85)
    axs.fill_between(x, p1, p2, color='lightgray', zorder=0)
    axs.quiver(x, Hs_x, u_ii, v_ii, **qkwargs)
    
    # Second axis
    ax2 = axs.twinx()
    ax2.plot(x, Tp_x, color='r', zorder=1, linewidth=0.75)
    
    # Set the labels, legends ...
    axs.set(xlim=(min(x), max(x)), ylim=ylim)
    
    axs.set_xticks(**xtkwargs)
    axs.xaxis.set_minor_locator(xminorLocator)

    axs.set_yticks(**ytkwargs)
    axs.set_ylabel(**ylkwargs)
    axs.yaxis.set_minor_locator(yminorLocator)
    
    # Do the same for the secondary axis
    ax2.set(ylim=ylim2)
    
    ax2.set_yticks(**y2tkwargs)
    ax2.set_ylabel(**y2lkwargs)
    
    # Hide the spines
    remove_spines(axs, locs=['top', 'right'])
    remove_spines(ax2, locs=['top'])
    
    plt.savefig(fout)
    plt.close()
    return


def plot_large_wave_variability(Hs, msk, savedir, monthly=True, years=None):
    
    if monthly:
        x = np.arange(1, 13)
        xticks = np.arange(1, 13)
        xticklbls = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        fname = 'figure_7_monthly_large_wave_variability.jpeg'
    else:
        dx = 5
        x = years
        xticks = np.arange(1980, years.max()+dx, dx)
        xticklbls = [ '{:.0f}'.format(v) for v in xticks ]
        fname = 'figure_8_yearly_large_wave_variability.jpeg'

    fout = os.path.join(savedir, fname)

    Hs_90 = np.zeros(len(x))
    Hs_99 = np.zeros(len(x))
    Hs_max = np.zeros(len(x))
    
    for ii in range(len(x)):
        # Estimating the average values
        tmp = Hs[msk[:,ii]].copy()
        Hs_90[ii] = np.nanpercentile(tmp, 90)
        Hs_99[ii] = np.nanpercentile(tmp, 99)
        Hs_max[ii] = np.nanmax(tmp)
    
    # Define the axis limits
    ylim = (0, np.ceil(max(Hs_max)))

    # Define the ticks (y-, y2-axis)
    dy = 1
    yticks = np.arange(0, ylim[1] + dy, dy)
    yticklbls = [ '{:.0f}'.format(v) for v in yticks ]

    # --- Parameters definition
    # Define the figure params
    fkwargs = {
        'nrows' : 1,
        'ncols' : 1,
        'figsize' : (6.5, 3),
        'dpi' : 200,
        'layout' : 'compressed'
    }

    # Define the x-axis ticks
    xminorLocator = MultipleLocator(1)
    xtkwargs = {
        'ticks' : xticks,
        'labels' : xticklbls
    }


    # Define the y-axis ticks and labels
    yminorLocator = MultipleLocator(0.5)
    ytkwargs = {
        'ticks' : yticks,
        'labels' : yticklbls,
    }

    ylkwargs = {
        'ylabel' : 'Wave Height [m]',
        'color' : 'black',
        'fontweight' : 'normal'
    }

    fig, axs = plt.subplots(**fkwargs)
    # Ploting on the left y-axis
    axs.plot(x, Hs_90, linewidth=1, label='90th Percentile', color='#42647C')
    axs.plot(x, Hs_99, linewidth=1, label='99th Percentile', color='#53ACD3')
    axs.plot(x, Hs_max, linewidth=1, label='Largest wave', color='#AEC386')
    
    # Set the labels, legends ...
    # axs.legend()
    axs.set(xlim=(min(x), max(x)), ylim=ylim)

    axs.set_xticks(**xtkwargs)
    axs.xaxis.set_minor_locator(xminorLocator)

    axs.set_yticks(**ytkwargs)
    axs.set_ylabel(**ylkwargs)
    axs.yaxis.set_minor_locator(yminorLocator)
        
    # Hide the spines
    remove_spines(axs, locs=['top', 'right'])
        
    plt.savefig(fout)
    plt.close()    
    return


def plot_extreme_waves_analysis(observed_return_values, modeled_return_values, observed_return_periods, modeled_return_periods, ci_lower, ci_upper, savedir):

    # Figure name / output directory
    fname = 'figure_9_extreme_value_analysis.jpeg'
    fout = os.path.join(savedir, fname)

    # Define additional parameters for the plot
    ymin = np.floor(min((observed_return_values.min(), modeled_return_values.min(), ci_lower.min())))
    ymax = np.ceil(max((observed_return_values.max(), modeled_return_values.max(), ci_upper.max())))

    # Define the parameters for the plot
    fkwargs = {
        'nrows' : 1,
        'ncols' : 1,
        'layout' : 'compressed',
        'dpi' : 200,
        'figsize' : (4, 4)
    }

    cikwargs = {
        'linewidth' : 0.75,
        'linestyle' : '--',
        'color' : 'black'
    }

    # Modeled Return Values
    mrvkwargs = {
        'linewidth' : 0.9,
        'linestyle' : '-',
        'color' : 'black'
    }

    # Observed Return Values
    orvkwargs = {
        'linestyle' : '',
        'marker' : 'o',
        'markerfacecolor' : 'r',
        'markeredgecolor' : 'k',
        'markersize' : 4,
        'markeredgewidth' : 0.5
    }

    fig, axs = plt.subplots(**fkwargs)
    axs.semilogx()
    axs.grid(True, which="both")
    axs.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:,.0f} years"))

    # Plot the Modeled Return Values (and CI)
    axs.plot(modeled_return_periods, ci_lower, **cikwargs)
    axs.plot(modeled_return_periods, ci_upper, **cikwargs)
    axs.plot(modeled_return_periods, modeled_return_values, **mrvkwargs)

    # Plot the Observed Returned Values
    axs.plot(observed_return_periods, observed_return_values, **orvkwargs)

    # Fill the blank between upper and lower CI
    axs.fill_between(modeled_return_periods, ci_lower, ci_upper, alpha=0.2)

    # Play around with the ticks, axis ...
    axs.set(
        xlabel='Annual Return Interval',
        xlim=(1, np.floor(modeled_return_periods.max())),
        ylabel='Significant Wave Height [m]',
        ylim=(ymin, ymax)
    )


    plt.savefig(fout)
    plt.close()

    return




def plot_wind_variability(u10, v10, msk, savedir):
    
    # Figure name / output directory
    fname = 'figure_12_monthly_wind_variability.jpeg'
    fout = os.path.join(savedir, fname)

    # Prepare the data
    n = 12 # number of months per year
    wSpeed_x = np.zeros(n)
    direction = np.zeros(n)
    
    for ii in range(n):
        # Estimating the average values
        um = np.nanmean(u10[msk[:,ii]])
        vm = np.nanmean(v10[msk[:,ii]])
        
        vector, angle = DataProcessing.cart2pol(um, vm)
        wSpeed_x[ii] = vector
        direction[ii] = angle
        
    # Estimating the U/V components of the vector (+180 to estimate the TO direction)        
    unitary = np.ones(n)
    u, v = DataProcessing.pol2cart(unitary, direction)
    
    # Define the axis limits
    ylim = (np.floor(min(wSpeed_x)), np.ceil(max(wSpeed_x)))

    # Define the ticks (y-axis)
    dy = 1
    yticks = np.arange(ylim[0], ylim[1] + dy, dy)
    yticklbls = [ '{:.0f}'.format(v) for v in yticks ]

    # Define the ticks (y2-axis)
    dy = 2
    y2lim = (np.floor(ylim[0] * 1.94384449), np.ceil(ylim[1] * 1.94384449) )        # Conversion from m/s to knots
    y2ticks = np.arange(y2lim[0], y2lim[1] + dy, dy)
    y2ticklbls = [ '{:.0f}'.format(v) for v in y2ticks ]
    
    # --- Parameters definition
    # Define the figure params
    fkwargs = {
        'nrows' : 1,
        'ncols' : 1,
        'figsize' : (6.5, 3),
        'dpi' : 200,
        'layout' : 'compressed'
    }

    # Define quiver parameters
    qkwargs = {
        'pivot' : 'middle',      # Anchor point
        'angles' : 'uv',         # Coordinate reference to be used for the angles
        'color' : 'black',       # Arrows color
        'zorder' : 10,           # Ploting order (0 (beneath) -> 999 (above))
        'units' : 'dots',        # Units used for the arrows dimension
        'width' : 5,
        'scale' : 4,
        'scale_units' : 'inches',
        'headaxislength' : 3.5,
        'headlength' : 4,
        'headwidth' : 3
    }

    # Define the x-axis ticks
    x = np.arange(1, 13)
    xtkwargs = {
        'ticks' : x,
        'labels' : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    }

    # Define the y-axis ticks and labels
    yminorLocator = MultipleLocator(0.5)
    ytkwargs = {
        'ticks' : yticks,
        'labels' : yticklbls,
    }

    ylkwargs = {
        'ylabel' : 'Wind Speed [m/s]',
        'color' : 'black',
        'fontweight' : 'normal'
    }

    # Define the secondary y-axis ticks and labels
    y2minorLocator = MultipleLocator(1)
    y2tkwargs = {
        'ticks' : y2ticks,
        'labels' : y2ticklbls,
    }

    y2lkwargs = {
        'ylabel' : '[Knots]',
        'color' : 'black',
        'fontweight' : 'normal'
    }



    # Generate the figure
    fig, axs = plt.subplots(**fkwargs)
    axs.plot(x, wSpeed_x, 'k', linewidth=0.85)
    axs.quiver(x, wSpeed_x, u, v, **qkwargs)
    
    # Set the labels, legends ...
    axs.set(xlim=(min(x), max(x)), ylim=ylim)
    
    axs.set_xticks(**xtkwargs)

    axs.set_yticks(**ytkwargs)
    axs.set_ylabel(**ylkwargs)
    axs.yaxis.set_minor_locator(yminorLocator)
    
    # Second axis
    ax2 = axs.twinx()
    ax2.set(ylim=y2lim)
    ax2.set_yticks(**y2tkwargs)
    ax2.set_ylabel(**y2lkwargs)

    ax2.yaxis.set_minor_locator(y2minorLocator)

    # Hide the spines
    remove_spines(axs, locs=['top', 'right'])
    remove_spines(ax2, locs=['top'])
    
    plt.savefig(fout)
    plt.close()
    return




def plot_sea_states_occurence(Hs, Tm, dout):
    
    def fmt(x):
        s = '{x:.0f} kW/m'
        return s.format(x=x)
    
    fname = 'figure_10_sea_states_occurence.jpeg'
    fout = os.path.join(dout, fname)
    
    # Defining the (x,y) coordinates used in the plot + the background
    dx, dy = (0.5, 0.5)
    Tmrange = np.arange(3, 20 + dx, dx)
    Hsrange = np.arange(0, 10 + dy, dy)
    
    occurences = np.full((Hsrange.size, Tmrange.size), np.nan, dtype=float)
    
    for ii, hs in enumerate(Hsrange):
        for jj, tm in enumerate(Tmrange):
            msk = ((Hs >= hs) & (Hs < hs + dy) & (Tm >= tm) & (Tm < tm + dx))
            
            if np.any(msk):
                occurences[ii,jj] = 100 * len(msk[msk]) / msk.size
    
    # Removing the values close to 0
    occurences[occurences < 0.5] = np.nan
    
    # Estimating the colobar limit, the number of colors used and generate the colormap
    maxOcc = np.nanmax(occurences)
    vlims = np.arange(10, 105, 5)
    vmax = vlims[vlims > maxOcc][0]
    nColors = vmax * 2
    cmap, norm, bounds = get_custom_colormap(nColors=nColors, vmin=0, vmax=vmax)
    
    # Estimating the wave power (the factor 1000 is for the conversion from W to kW)
    g = PhysicalConstants.gravity_acceleration
    rho_sw = PhysicalConstants.rho_seawater
    wavePower = (rho_sw * (g**2) * np.power(Hsrange[:,None], 2) * Tmrange[None,:]) / (64*np.pi*1000)
    
    
    kwargs = {'vmin' : None,
              'vmax' : None,
              'cmap' : cmap,
              'norm' : norm}
    
    if len(bounds) > 10:
        ticks = bounds[::2]
    else:
        ticks = bounds.copy()
    
    cbkwargs = {'location' : 'right',
                'extend' : 'max',
                'format' : '{x:.2f}%',
                'drawedges' : True,
                'label' : 'Occurences [%]',
                'norm' : norm,
                'ticks' : ticks,
                'boundaries' : bounds}
    
    ckwargs = {'colors' : 'black',
               'linestyles' : '--'}
    
    # Creating the axis limits
    ylim = (0, np.ceil(np.nanmax(Hs)))
    xlim = (3, np.ceil(np.nanmax(Tm)))
    
    fig, axs = plt.subplots(dpi=200, layout='compressed', figsize=(5, 4))
    im0 = axs.pcolormesh(Tmrange, Hsrange, occurences, **kwargs)
    CS = axs.contour(Tmrange, Hsrange, wavePower, levels=[5, 25, 50, 100, 200], **ckwargs)
    
    axs.clabel(CS, CS.levels, fmt=fmt, fontsize=10)
    cbar = plt.colorbar(im0, ax=axs, **cbkwargs)
    
    axs.set(xlabel='Wave Period [s]', ylabel='Wave Height [m]', xlim=xlim, ylim=ylim)
    
    plt.savefig(fout)
    plt.close()
    
    
    
    return