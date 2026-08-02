# -*- coding: utf-8 -*-
"""
Created on Tue Jan 28 15:25:44 2025

@author: gregoires
"""


import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import windrose

from pdf_factory.fig_tools import get_custom_colormap, get_waverose_settings


nsector = 18
bins = np.arange(0, 3.25, 0.25)

kwargs = {'nsector' : nsector,
          'opening' : 1,
          'normed' : True, 
          'bins' : bins, 
          'cmap' : get_custom_colormap(),
          'blowto' : False, # i.e., we are ploting following the FROM convention,
          'edgecolor' : 'black'
          }

N = 10000
direction = np.random.rand(N) * 360
data = np.random.rand(N) * 3

dtheta = 360 / nsector
dradius = 5



fout = os.path.abspath(os.path.join('.', 'output', '2025', 'Betio', 'test_polar_plots.jpeg'))

fig, ax = plt.subplots(dpi=200, figsize=(10, 8.5), subplot_kw={'projection' : 'windrose'}, layout='compressed')

ax.bar(direction, data, **kwargs)

# Set up the legend
ax.set_legend(units='[m]', decimal_places=2, loc='lower left', bbox_to_anchor=(1, 0.025))

# Set up some nice axis
rmax, locs, rticks, yticks_labels = get_waverose_settings(ax, dtheta, dradius)
ax.set_rmax(rmax)
ax.set_rticks(ticks=locs, labels=yticks_labels, color='k')
ax.set_rlabel_position(rticks)




# xticks = np.arange(dtheta/2, 360, dtheta)
# xticks_labels = xticks.astype(str)

# ax.set_xticks(ticks=np.deg2rad(xticks), labels=xticks_labels)


plt.savefig(fout)
plt.close()



































sys.exit(0)


from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch  # Importing inch unit
from reportlab.lib.utils import ImageReader

from reportlab.rl_config import defaultPageSize


from pdf_factory import layout_manager, report_content_manager
from utils.file_manager import FileManager
from utils.hindcast_reader import HindcastReader



# locList = ['Betio', 'Tanna']

# locList = None
locList = ['Pago Pago']
# locList = ['Betio', 'Guam', 'Yap']
locList = ['Betio', 'Yap', 'Pago Pago']





#TODO: there seems to be an issue with values other than Betio (due to the bounding box)

for locName in locList:
    Content = report_content_manager.ContentManager(locName)
    Content.generate_location_map()
    # break
    
sys.exit(0)









A = HindcastReader(locList=locList)
A.load_hindcast()
A.export_hindcast()

sys.exit(0)

PAGE_HEIGHT = defaultPageSize[1]
PAGE_WIDTH = defaultPageSize[0]


countries = [ {'name' : 'Tonga', 'latitude' : -21.327, 'longitude' : 184.73} ]
current_year = 2023
country_name = countries[0]['name']

current_dir = os.path.abspath(os.path.dirname(__file__))
outdir = os.path.join(current_dir, 'output')
fout = os.path.join(outdir, 'testing_reportlab.pdf')

ancillary_dir = os.path.join(current_dir, 'ancillary')
fpath_bckgrnd = os.path.join(ancillary_dir, 'FrontPage-V2.svg')

pdir_logo = os.path.join(ancillary_dir, 'Logos')





Report = layout_manager.WaveReport(fpath=fout, locName='Betio')





sys.exit(0)












