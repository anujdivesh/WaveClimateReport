# -*- coding: utf-8 -*-
"""
Created on Fri Mar 21 09:12:27 2025

@author: gregoires
"""


import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from shapely import get_coordinates


def get_map_grid_definition(bbox):
    coord = get_coordinates(bbox)
    x_extent = coord[:,0].max() - coord[:,0].min()
    y_extent = coord[:,1].max() - coord[:,1].min()
    
    if x_extent <= 0.75:
        dx = 0.25
    elif x_extent > 3:
        dx = 1
    else:
        dx = 0.5
        
    if y_extent <= 0.75:
        dy = 0.25
    elif y_extent > 3:
        dy = 1
    else:
        dy = 0.5
    
    # +0.1 to keep the end point in the values
    xticks = np.arange(np.floor(coord[:,0].min()), np.ceil(coord[:,0].max()) + 0.1, dx)
    yticks = np.arange(np.floor(coord[:,1].min()), np.ceil(coord[:,1].max()) + 0.1, dy)
    return xticks, yticks


def get_waverose_settings(axs, dtheta, dradius):
    
    if not isinstance(axs, np.ndarray):
        axs = np.array(axs)
    
    # Estimating the maximum radius (i.e., the maximum % of waves for a given direction)
    tmp_rmax = []
    tmp_dir = []
    for ax in axs.flatten():
        v = np.sum(ax._info['table'], axis=0)
        tmp_dir.append(ax._info['dir'][np.argmax(v)] + dtheta / 2)
        tmp_rmax.append(v.max())
        
    idx = np.argmax(tmp_rmax)
    rmax = tmp_rmax[idx]
    mainDir = tmp_dir[idx]
    
    if rmax > 30:
        dradius = 10
    
    rmax = (rmax - rmax % dradius)  + dradius
    
    locs = np.arange(dradius, rmax, dradius)
    yticks_labels = [ '{} %'.format(int(v)) for v in locs ]
    rticks = 180 + mainDir + dtheta + 3
    
    # Generate the grid lines (one line per direction)
    thetagrids = np.arange(0, 360+dtheta/2, dtheta)
    thetagrids[thetagrids < 0] += 360
    thetagrids[thetagrids > 360] -= 360
    thetagrids = np.unique(thetagrids)
    
    return rmax, locs, rticks, yticks_labels, thetagrids


def get_custom_colormap(nColors=None, vmin=None, vmax=None):
    
    colors = [
        '#ffffff',
        '#d0d8fb',
        '#b9c5f7',
        '#8ea0f1',
        '#6079ec',
        '#0027e0',
        '#1864f0',
        '#0c80f8',
        '#17aeff',
        '#30bdff',
        '#43caff',
        '#5fe1f0',
        '#69ebe1',
        '#7aebc7',
        '#7aebc7',
        '#acf5a7',
        '#befaa4',
        '#cdffa1',
        '#dff58c',
        '#f0ec78',
        '#f7d767',
        '#ffbc55',
        '#ff9f44',
        '#f47449',
        '#ee4f4d'
    ]
    
    cmap = mpl.colors.LinearSegmentedColormap.from_list('my cmap', colors)
    
    if nColors is not None:
        bounds = np.linspace(vmin, vmax, nColors+1)
        norm = mpl.colors.BoundaryNorm(bounds, cmap.N)
        return cmap, norm, bounds
    return cmap

def remove_spines(ax, locs):
    for loc, spine in ax.spines.items():
        if loc in locs:
                spine.set_visible(False)
    return