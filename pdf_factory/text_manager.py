# -*- coding: utf-8 -*-
"""
Created on Tue Apr 15 14:35:07 2025

@author: gregoires
"""

from string import Formatter

from reportlab.lib import colors
from reportlab.lib.units import inch  # Importing inch unit
from reportlab.platypus import Table, Paragraph


from utils.file_manager import FileManager


class TextManager:    
    txt_dft_value = '<b>ERR:MISSING_VALUE</b>'
    txt_keyValues = {}
    
    def __init__(self, locName, txt_keyValues, **kwargs):
        
        self.txt_keyValues['locName'] = locName
        self.txt_keyValues['cntName'] = self.from_location_get_countryDef(locName)['country_name']
        
        self.txt_keyValues.update(txt_keyValues)
        
    def get_txt_content(self, key):
        out = [ v for v in self.content if key == v['name']]
        return out[0]['content']
        
    def generate_txt_keywords_list(self, key):
        txt = self.get_txt_content(key)
        keywords = [ v[1] for v in Formatter().parse(txt) if v[1] is not None ]
        return keywords
    
    def generate_txt_content(self, key):
        txt = self.get_txt_content(key)
        keys = self.generate_txt_keywords_list(key)
        
        vals = {}
        for key in keys:
            vals[key] = self.txt_keyValues.get(key, self.txt_dft_value)
            
        # Unpack the dictionary with the key / value pairs to fill the text
        try:
            formatted_txt = txt.format(**vals)
        except ValueError:
            formatted_txt = self.txt_dft_value
            
        return formatted_txt
    
    
    
    
    
    
class TableManager:    
    txt_dft_value = '<b>ERR:MISSING_VALUE</b>'
    table_keyValues = {}
    
    def __init__(self, locName, table_keyValues, **kwargs):
        
        self.table_keyValues = table_keyValues
        self.table_keyValues['locName'] = locName
        self.table_keyValues['cntName'] = self.from_location_get_countryDef(locName)['country_name']
        
    def get_table_params(self, key):
        out = [ v for v in self.tables if key == v['name']]
        return out[0]
    
    def generate_table_keywords_list(self, txt):
        keywords = [ v[1] for v in Formatter().parse(txt) if v[1] is not None ]
        return keywords
    
    def generate_table_content(self, key, data=None):
        tableParams = self.get_table_params(key)
        raw_content = tableParams['content']
        
        content = []
        for row in raw_content:
            # This one is an exception as we directly use the formatted data
            if data is not None and tableParams['row_format'] is not None:
                content = raw_content
                for line in data:
                    content.append(line)
                break
            
            row_ii = []
            for col in row:
                if not isinstance(col, str):
                    col = str(col)
                    
                keys = self.generate_table_keywords_list(col)
                
                vals = {}
                for key in keys:
                    vals[key] = self.table_keyValues.get(key, self.txt_dft_value)
                
                try:
                    formatted_txt = col.format(**vals)
                except ValueError:
                    formatted_txt = self.txt_dft_value
                
                row_ii.append(formatted_txt)
                    
                
            # Appending the given row to the whole table
            content.append(row_ii)
            
        style = self.generate_table_style(tableParams)
        caption = self.generate_table_caption(tableParams)
        return content, style, caption
    
    def generate_table_style(self, tableParams):
        
        bgColor = '#c8f4e7'
        lineColor = '#42647C'
        thickLine = (1, lineColor)
        
        style = [
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-2, -1), 'CENTER'),
            ('ALIGN', (-1, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('INNERGRID', (0,0), (-1,-1), 0.75, lineColor),
            # ('LINEBELOW', (0,-1), (-1, -1), *thickLine),
            ('BOX', (0,0), (-1, -1), *thickLine),
            ('FONTNAME', (0,0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 10)
        ]

        if tableParams['headers']:
            style.append(('FONTNAME', (0,0), (-1, 0), 'Helvetica-Bold'))
            style.append(('FONTSIZE', (0,0), (-1,0), 11))
            style.append(('TEXTCOLOR', (0,0), (-1, 0), colors.white))
            style.append(('ROWBACKGROUNDS', (0,0), (-1,0), ['#005D7D']))
            style.append(('ROWBACKGROUNDS', (0,1), (-1,-1), [bgColor, colors.white]))
            
        else:
            style.append(('ROWBACKGROUNDS', (0,0), (-1,-1), [bgColor, colors.white]))
            style.append(('LINEABOVE', (0,0), (-1, 0), *thickLine))
            
            
        return style
    
    def generate_table_caption(self, tableParams):
        
        caption = tableParams['caption']
        keywords = [ v[1] for v in Formatter().parse(caption) if v[1] is not None ]
        
        vals = {}
        for key in keywords:
            vals[key] = self.table_keyValues.get(key, self.txt_dft_value)
        
        caption = caption.format(**vals)
        out = '<b>{table_id}</b>: {table_caption}'.format(table_id=tableParams['id'],
                                                          table_caption=caption)
        return out
    
    def insert_table(self, key, data=None, addRuler=True, longTable=False):
        content, style, caption = self.generate_table_content(key, data=data)
        
        if addRuler:
            self.add_horizontal_ruler()
        
        if longTable:
            rowheights = 0.2*inch
        else:
            rowheights = None
        
        self.elements.append(Paragraph(caption, self.styleSheet['captions']))
        self.elements.append(Table(content, style=style, rowHeights=rowheights))
        return

