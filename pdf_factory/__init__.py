# -*- coding: utf-8 -*-
"""
Spyder Editor

Init file used to set up the default values for the plot.
"""

import matplotlib.pyplot as plt

# =============================================================================
# Defining the plots parameters
# =============================================================================
SMALL_SIZE              =       8
MEDIUM_SIZE             =       9
BIGGER_SIZE             =       11


# --
# Generic - Font
plt.rc('font', size=SMALL_SIZE)          # controls default text sizes

# --
# Axes
plt.rc('axes', titlesize=MEDIUM_SIZE)    # fontsize of the axes title
plt.rc('axes', titleweight='bold')       # Weight of the x and y titles
plt.rc('axes', labelsize=MEDIUM_SIZE)    # fontsize of the x and y labels
plt.rc('axes', labelweight='normal')       # Weight of the x and y labels

# Axes - Ticks Labels
plt.rc('xtick', labelsize=SMALL_SIZE)    # fontsize of the tick labels
plt.rc('ytick', labelsize=SMALL_SIZE)    # fontsize of the tick labels


# --
# Figure
plt.rc('figure', titlesize=BIGGER_SIZE)  # fontsize of the figure title
plt.rc('figure', titleweight='bold')     # Weight of the figure title


# --
# Legend
plt.rc('legend', fontsize=MEDIUM_SIZE)   # legend fontsize