# -*- coding: utf-8 -*-
"""
Created on Mon Mar 24 09:38:25 2025

@author: gregoires
"""

import os 

from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import blue, gray, lightblue, lightsteelblue

from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, NextPageTemplate, HRFlowable

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch  # Importing inch unit
from reportlab.lib.utils import ImageReader







WIDTH, HEIGHT = A4



class ReportUtils:
    # Pre-defined for later on
    largeSpacer = Spacer(0, 35)
    smallSpacer = Spacer(0, 25)
    captionSpacer = Spacer(0, 10)
    
    
    @staticmethod
    def get_image(fpath, width=1*inch):
        img = ImageReader(fpath)
        iw, ih = img.getSize()
        aspect = ih / float(iw)
        return Image(fpath, width=width, height=(width * aspect), hAlign='CENTER')
    
    def get_figure_caption(self, name):
        content = [ v for v in self.captions if v['name'] == name ][0]
        caption = content['caption']
        
        if '{locName}' in caption and '{yearStart}' in caption:
            caption = caption.format(locName=self.locName, yearStart=self.txt_keyValues['yearStart'])
        
        elif '{locName}' in caption:
            caption = caption.format(locName=self.locName)

        else:
            pass
        
        txt = '<b>{id}</b>: {caption}'.format(id=content['id'], caption=caption)
        return txt
    
    def insert_image(self, fname, width, captionId, addRuler=True):
        # Add a ruler
        if addRuler:
            self.add_horizontal_ruler()
        else:
            self.elements.append(Spacer(height=35, width=0))
        
        # Adding the caption
        caption = self.get_figure_caption(name=captionId)
        self.elements.append(Paragraph(caption, self.styleSheet['captions']))
        
        # Add the image
        image = self.get_image(os.path.join(self.root, fname), width=width)
        self.elements.append(image)
        return
    
    
    def add_horizontal_ruler(self):
        width = 0.9*inch + self.doc.width
        ruler = HRFlowable(width=width, color='#043e73', spaceBefore=25, spaceAfter=10)
        self.elements.append(ruler)
        return