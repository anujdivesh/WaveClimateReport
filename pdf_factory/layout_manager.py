# -*- coding: utf-8 -*-
"""
Created on Wed Jan 29 09:49:12 2025

@author: gregoires
"""

from datetime import datetime
import os



from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import blue, gray, lightblue, lightsteelblue

from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, BaseDocTemplate, PageTemplate, Frame, Table, TableStyle, Paragraph, Spacer, PageBreak, Image, NextPageTemplate, HRFlowable
from reportlab.platypus.tableofcontents import TableOfContents

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch  # Importing inch unit
from reportlab.lib.utils import ImageReader

from reportlab.rl_config import defaultPageSize


from . layout_utils import ReportUtils
from . text_manager import TextManager, TableManager
from utils.file_manager import FileManager #TODO: remove this one, there is already one defined in utils.utilities.py






WIDTH, HEIGHT = A4



def get_image(fpath, width=1*inch):
    img = ImageReader(fpath)
    iw, ih = img.getSize()
    aspect = ih / float(iw)
    return Image(fpath, width=width, height=(width * aspect), hAlign='CENTER')

#TODO: passer dans une classe
def header_front_page(canvas, doc):
    cosppac_logo = os.path.join(os.path.abspath('.'), 'ancillary', 'Logos', 'COSPPac-Logo-Acronym.png')
    spc_logo = os.path.join(os.path.abspath('.'), 'ancillary', 'Logos', 'logo_SPC.png')
    canvas.saveState()
    
    # Creating the blue shapes on the Front Page
    # First, the one at the bottom
    x0 = 0
    y0 = 0
    height = doc.bottomMargin + 0.35*inch
    
    canvas.setFillColor(lightsteelblue)
    canvas.rect(x0, y0, doc.width+2*inch, height, stroke=0, fill=1)
    
    # Then the one on top
    y = doc.height - 0.25*inch
    
    x_tl = 0
    y_tl = HEIGHT
    
    x_tr = WIDTH
    y_tr = HEIGHT
    
    x1 = 0
    y1 = y
    
    x2 = WIDTH * 0.2
    y2 = y - 0.6*inch
    
    x3 = WIDTH * 0.8
    y3 = y + 0.6*inch
    
    x4 = WIDTH
    y4 = y
    
    canvas.setFillColor(lightsteelblue)
    path = canvas.beginPath()
    
    path.moveTo(x_tl, y_tl)
    path.lineTo(x1, y1)
    path.curveTo(x2, y2, x3, y3, x4, y4)
    path.lineTo(x_tr, y_tr)
    canvas.drawPath(path, fill=1, stroke=0)
    
    # COSPPac logo (top left)
    x_logo = doc.leftMargin - 0.85*inch
    y_logo = doc.height + 0.35*inch

    canvas.drawImage(
        cosppac_logo,
        x_logo,
        y_logo,
        width=3*inch,
        height=2*inch,
        preserveAspectRatio=True,
        mask='auto'
    )

    # SPC logo (top right)
    x_logo = doc.width * 0.9 - 0*inch
    y_logo = doc.height + 0.5*inch
    
    canvas.drawImage(
        spc_logo,
        x_logo,
        y_logo,
        width=2*inch,
        height=1.5*inch,
        preserveAspectRatio=True,
        mask='auto'
    )

    # Add the logo in the footer
    logo_AusAid = os.path.join(os.path.abspath('.'), 'ancillary', 'Logos', 'australian-aid-blue-and-red.png')
    logo_NZ = os.path.join(os.path.abspath('.'), 'ancillary', 'Logos', 'logo_NZ_MOFAT.png')
    logo_bom = os.path.join(os.path.abspath('.'), 'ancillary', 'Logos', 'BOM_Official_Logo_Black-Blue_RGB.png')
    
    # Australian Aid logo (Bottom left)
    x_logo = doc.leftMargin - 0.75*inch
    y_logo = doc.bottomMargin - 0.85 * inch
    
    canvas.drawImage(
        logo_AusAid,
        x_logo,
        y_logo,
        width=1.65*inch,
        height=1*inch,
        preserveAspectRatio=True,
        mask='auto'
    )

    # NZ MOFAT (Bottom middle)
    x_logo = doc.leftMargin + doc.width * 0.35
    y_logo = doc.bottomMargin - 0.95 * inch
    
    canvas.drawImage(
        logo_NZ,
        x_logo,
        y_logo,
        width=1.5*inch,
        height=1.4*inch,
        preserveAspectRatio=True,
        mask='auto'
    )

    # Bureau of Met. logo (Bottom right)
    x_logo = doc.width * 0.8
    y_logo = doc.bottomMargin - 1.70 * inch
    
    canvas.drawImage(
        logo_bom,
        x_logo,
        y_logo,
        width=3.25*inch,
        height=2.65*inch,
        preserveAspectRatio=True,
        mask='auto'
    )

    # Add some text in the header
    txtStyleHeader = ParagraphStyle(
        name='FrontPageLogoText',
        alignment=TA_JUSTIFY,
        fontSize=9,
        borderPadding=0,
        backColor=None
    )

    txtStyleFooter = ParagraphStyle(
        name='FrontPageInfoText',
        alignment=TA_JUSTIFY,
        fontSize=8,
        borderPadding=0,
        backColor=None
    )
    
    # logo_txt = 'The Climate and Oceans Support Program in the Pacific (COSPPAC)' + \
    #     ' works to enhance the accessibility of essential ocean and climate' + \
    #     ' information for Pacific Islands Nations. Through Initiatives like' + \
    #     ' the wave climate reports, sub-seasonal to seasonal forecast and ocean' + \
    #     ' data tools, COSPPAC strengthens ocean services across the region. The' + \
    #     ' updated wave climate reports, based on hindcast data spanning 1979' + \
    #     ' to {current_year}, offer insights into regional wave climatology. These reports' + \
    #     ' aims to support informed decision-making and resilience planning.'
    
    logo_txt = 'The Climate and Oceans Support Program in the Pacific (COSPPac)' + \
    ' is a long-running regional activity supporting Pacific Island countries' + \
    ' to adapt to and to mitigate the impacts of climate variability and change.' + \
    ' The Wave Climate Reports, based on statistical data of wave conditions' + \
    ' spanning 1979 to {current_year}, are designed to strengthen ocean services' + \
    ' across the region and aim to support informed decision-making and resilience planning.'

    logo_txt = logo_txt.format(current_year=datetime.now().year)
    
    P_logo = Paragraph(logo_txt, txtStyleHeader)
    _ = P_logo.wrap(doc.width+1.9*inch, doc.bottomMargin)
    P_logo.drawOn(canvas, doc.leftMargin-0.95*inch, doc.height-0.05*inch)
    

    # Creating the footer while we are at it
    footer_txt = '<b>For more information, contact:</b><br/>' + \
        "Moleni Tu\'uholoaki <br/>" + \
        'Pacific Community (SPC) <br/>' + \
        'Geoscience, Energy, and Maritime Division <br/>' + \
        'Postal Adress: Private mail bag, GPO, Suva - Fiji Islands <br/>' + \
        'Street Adress: Nabua, Suva - Fiji Islands <br/>' + \
        'Office Tel.: +679 338 1377 <br/>' + \
        'Email: molenit@spc.int'
    
    P_footer = Paragraph(footer_txt, txtStyleFooter)
    _ = P_footer.wrap(doc.width / 2, doc.bottomMargin)
    P_footer.drawOn(canvas, doc.leftMargin-0.85*inch, doc.bottomMargin+0.5*inch)
    
    # Second text in the footer
    footer_txt_2 = '<font size=12><strong>Download a copy:</strong></font><br/>' + \
        'Select Wave Climate Report under Document Type at: <br/>' + \
        'https://oceanportal.spc.int/library'
    
    # y_footer_2 = P_footer.height - 36 + 0.1*inch
    y_footer_2 = doc.bottomMargin + 1.4*inch
    
    P_footer_2 = Paragraph(footer_txt_2, txtStyleFooter)
    _ = P_footer_2.wrap(doc.width / 2, doc.bottomMargin)
    P_footer_2.drawOn(canvas, doc.width-1.15*inch, y_footer_2)
    
    
    
    
    canvas.restoreState()





class WaveReport(FileManager, TextManager, TableManager, ReportUtils):
    '''
    Look up https://stackoverflow.com/questions/21696462/how-to-assign-doc-topmargin-for-different-pages-using-reportlab-simpledoctemplat
    for a solution as to how increase / decrease the margin values
    '''
    
    # Defining the figures width (in the report)
    pfigures = {
        'fig_1' : 4*inch,       # Both maps
        'fig_2' : 6*inch,       # Annual wave rose
        'fig_3' : 6*inch,       # Seasonal Wave rose
        'fig_4' : 6*inch,     # Monthly variabilty
        'fig_5' : 6*inch,     # Yearly variabilty
        'fig_6' : 5*inch,     # Large / severe / extreme waves
        'fig_7' : 6*inch,       # Extreme Waves monthly variations
        'fig_8' : 6*inch,       # Extreme Waves annual variations
        'fig_9' : 3.2*inch,     # Extreme Values Analysis (sits beside the return periods table)
        'fig_10' : 5*inch,      # Sea states occurences (wave energy)
        'fig_11' : 5*inch,      # Wind Annual wind rose
        'fig_12' : 5*inch       # Wind Monthly variability
    }
    
    
    def __init__(self, fpath, locName, txt_keyValues, table_keyValues):
        
        FileManager.__init__(self, locName=locName)
        TextManager.__init__(self, locName=locName, txt_keyValues=txt_keyValues)
        TableManager.__init__(self, locName=locName, table_keyValues=table_keyValues)
        
        
        # Initialize the saving directory
        self.root = os.path.split(fpath)[0]
        self.start_page_number = None
        
        self.init_styleSheet()
        
        
        self.elements = []
        
        
        
        
        # creation of the BaseDocTempalte. showBoundary=0 to hide the debug borders
        self.doc = BaseDocTemplate(fpath, pagesize=A4, showBoundary=0)
        
        # Create the frames. Here you can adjust the margins
        frame_first_page = Frame(
            x1=self.doc.leftMargin - 1*inch,
            y1=self.doc.bottomMargin + 2*inch, # 0.5
            width=self.doc.width + 2*inch,
            # height=self.doc.height - 2.5*inch, # 1.75
            height=self.doc.height *0.65, # 1.75
            id='first'
        )
        
        frame_remaining_pages = Frame(
            self.doc.leftMargin - 0.5 * inch, 
            self.doc.bottomMargin, 
            self.doc.width + 1 * inch,
            self.doc.height * 0.98,
            id='remaining'
        )
        
        # add the PageTempaltes to the BaseDocTemplate. You can also modify those to adjust the margin if you need more control over the Frames.
        self.doc.addPageTemplates(
            [
                PageTemplate(id='first_page', frames=frame_first_page, onPage=header_front_page),
                PageTemplate(id='remaining_pages', frames=frame_remaining_pages, onPage=self.header_other_pages),
            ]
        )
        
        # Initialize the TOC
        toc = TableOfContents(dotsMinLevel=0)
        toc.levelStyles = [self.styleSheet['tocHeaders']]
        
        # Overwritte initial method to ensure the TOC is generated
        self.doc.afterFlowable = self.afterFlowable
        
        # Generate each element present in the report (i.e., paragraphs, tables ...)
        self.firstPage()
        
        # Add the TOC
        self.elements.append(Paragraph('Table of Contents', self.styleSheet['tocHeaders']))
        self.elements.append(toc)
        self.elements.append(PageBreak())
        
        self.generalWaveClimatePage()
        self.meanWaveRosePage()
        self.waveVariationPage()
        self.largeSevereWavesPage()
        
        self.extremeWavesPage()
        # self.waveEnergyPage()
        
        self.windPage()
        
        self.glossaryPage()
        self.acknowledgementPage()
        self.disclaimerPage()
        
        
                
        # Merge the pages into one document
        # self.doc.build(self.elements)
        self.doc.multiBuild(self.elements)
        
    def get_page_number(self):
        if self.start_page_number is None:
            self.start_page_number = self.doc.page
        page_number = self.doc.page - self.start_page_number + 1
        return page_number
    
    def afterFlowable(self, flowable):
        "Registers TOC entries."
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'bodyHeaders':
                page_number = self.get_page_number()
                self.doc.notify('TOCEntry', (0, text, page_number))
            elif style == 'bodySubHeaders':
                page_number = self.get_page_number()
                self.doc.notify('TOCEntry', (1, text, page_number))
    
            
    def init_styleSheet(self):
        self.styleSheet = getSampleStyleSheet()
        styles = self.load_json(self.styleFile)
        
        for style in styles:
            self.styleSheet.add(ParagraphStyle(**style))
        
    def header_other_pages(self, canvas, doc):
        pageWidth, pageHeight = canvas._pagesize
        
        canvas.saveState()
        # Generate the colored rectangle at the top of the page
        y0 = self.doc.height + 1*inch # previous was 0.7, too low, this one is too high
        x0 = 0
        width = pageWidth
        height = pageHeight # This one doesnt really matter, we are drawing the rectangle at the top of the page
        
        p = canvas.beginPath()
        p.rect(x0, y0, width, height)
        canvas.clipPath(p, stroke=0)
        canvas.linearGradient(x0, y0, width, height, ('#07B4DE', '#005D7D'))
        
        
        kwargs = {
            'year' : datetime.now().year,
            'loc' : self.locName,
            'country' : self.countryDef['country_name']
        }
        txtHeader = '<b>Wave Climate Report {year}</b><br/>{loc}, {country}'.format(**kwargs)
            
        header = Paragraph(txtHeader, self.styleSheet['headerFootings'])
        _ = header.wrap(doc.width, doc.bottomMargin)
        header.drawOn(canvas, doc.leftMargin - 0.5*inch, doc.height + 1.3*inch)
        
        canvas.restoreState()
        canvas.saveState()
        
        # Create the footer
        x = A4[0]-128
        y = 40
        
        if self.start_page_number is not None:
            page_number = self.get_page_number()
            if page_number < 1:
                return

            txtFooting = "Page {}".format(int(page_number))
            footing = Paragraph(txtFooting, self.styleSheet['footingText'])
            _ = footing.wrap(doc.width, doc.bottomMargin)
            footing.drawOn(canvas, x, y)
            
            canvas.restoreState()
    
    
    def firstPage(self):
        
        # Inserting the title that will be used for the report
        title = 'Wave Climate Report<br/><br/><br/>{loc} - {country}'.format(
            loc=self.locName,
            country=self.countryDef['country_name']
        )
        
        self.elements.append(Paragraph(title, self.styleSheet['headerFrontPage']))
        
        self.elements.append(self.largeSpacer)
        
        
        # Inserting the maps
        mwidth = self.pfigures['fig_1']
        region_map = get_image(os.path.join(self.root, 'figure_1_region.jpeg'), width=mwidth)
        zoom_map = get_image(os.path.join(self.root, 'figure_1_zoom.jpeg'), width=mwidth)
        
        self.elements.append(Table([[region_map, zoom_map]],
                                    colWidths=[mwidth, mwidth],
                                    rowHeights=[mwidth],
                                    style=TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                                                     ('VALIGN', (0, 0), (-1, -1), 'CENTER')])))
        
        self.elements.append(self.captionSpacer)
        
        caption = self.get_figure_caption(name='locationMap')
        self.elements.append(Paragraph(caption, self.styleSheet['captions']))
        
        self.elements.append(NextPageTemplate("remaining_pages"))
        self.elements.append(PageBreak())
        
    
    
    
    def generalWaveClimatePage(self):
                
        # Creating a header for the section
        header = 'General Wave Climate'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('introduction_1'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('introduction_2'), self.styleSheet['textBody']))
        
        # Creating the table summing up the validation
        self.insert_table(key='validationWaveHindcast')
        
        self.elements.append(PageBreak())
        
        
        # Creating a header for the sub-section
        header = 'Average Wave Conditions'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))
        
        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('averageWaveConditions_1'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('averageWaveConditions_2'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('averageWaveConditions_3'), self.styleSheet['textBody']))
        
        # Creating the table witht the average wave conditions
        self.insert_table(key='waveConditionsHindcast')
        
        self.elements.append(PageBreak())
        
        
    def meanWaveRosePage(self):
        
        # Creating a header for the section
        header = 'Annual Mean Wave Rose'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('meanWaveRose_1'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('meanWaveRose_2'), self.styleSheet['textBody']))
        
        # Inserting the waverose
        fname = 'figure_2_annual_wave_rose.jpeg'
        width = self.pfigures['fig_2']
        captionId = 'annualWaveRose'
        self.insert_image(fname, width, captionId)
        
        self.elements.append(PageBreak())


    def waveVariationPage(self):
        
        # Creating a header for the section
        header = 'Waves Variability'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('waveVariation_1'), self.styleSheet['textBody']))
        
        # Inserting the waverose
        fname = 'figure_3_seasonal_wave_rose.jpeg'
        width = self.pfigures['fig_3']
        captionId = 'seasonalWaveRose'
        self.insert_image(fname, width, captionId)

        # Creating a header for the sub-section
        header = 'Seasonal Wave Rose Summary'
        self.elements.append(Paragraph(header, self.styleSheet['bodySubHeaders']))
        self.elements.append(Paragraph(self.generate_txt_content('waveVariation_2'), self.styleSheet['textBody']))
        
        self.elements.append(PageBreak())

        # Creating a header for the sub-section
        header = 'Monthly Wave Height, Period and Direction'
        self.elements.append(Paragraph(header, self.styleSheet['bodySubHeaders']))
        self.elements.append(Paragraph(self.generate_txt_content('waveVariation_3'), self.styleSheet['textBody']))
 
        # Inserting the wave variability (monthly)
        fname = 'figure_4_monthly_wave_variability.jpeg'
        width = self.pfigures['fig_4']
        captionId = 'monthlyWaveVariation'
        self.insert_image(fname, width, captionId)
        
        # Creating a header for the sub-section
        header = 'Annual Mean Wave Height, Period and Direction'
        self.elements.append(Paragraph(header, self.styleSheet['bodySubHeaders']))
        self.elements.append(Paragraph(self.generate_txt_content('waveVariation_4'), self.styleSheet['textBody']))
 
        # Inserting the wave variability (yearly)
        fname = 'figure_5_yearly_wave_variability.jpeg'
        width = self.pfigures['fig_5']
        captionId = 'annualWaveVariation'
        self.insert_image(fname, width, captionId)
        
        self.elements.append(PageBreak())
        
        

        

        
        
        
    def largeSevereWavesPage(self):
        
        # Creating a header for the section
        header = 'Large and Severe Waves'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('largeSevereWaves_1'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('largeSevereWaves_2'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('largeSevereWaves_3'), self.styleSheet['textBody']))
        
        # Inserting the large and severe wave rose (monthly)
        fname = 'figure_6_large_severe_wave_rose.jpeg'
        width = self.pfigures['fig_6']
        captionId = 'largeWaveRose'
        self.insert_image(fname, width, captionId)
        
        
        # Creating a header for the sub-section
        self.elements.append(PageBreak())
        
        header = 'Large Wave Variability'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))
        self.elements.append(Paragraph(self.generate_txt_content('largeSevereWaves_4'), self.styleSheet['textBody']))        
        
        
        # Inserting the large and severe wave variability (monthly)
        fname = 'figure_7_monthly_large_wave_variability.jpeg'
        width = self.pfigures['fig_7']
        captionId = 'monthlyWaveVariation_large'
        self.insert_image(fname, width, captionId)
        
        # Inserting the large and severe wave variability (annual)
        fname = 'figure_8_yearly_large_wave_variability.jpeg'
        width = self.pfigures['fig_8']
        captionId = 'annualWaveVariation_large'
        self.insert_image(fname, width, captionId, addRuler=False)


        self.elements.append(PageBreak())
        
    def extremeWavesPage(self):
        # Creating a header for the section
        header = 'Extreme Waves Events'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('extremeWaves_1'), self.styleSheet['textBody']))
        
        # Creating the table with the 30 largest wave events
        self.insert_table(key='largestWaveEvents', data=self.table_keyValues['extremeWave_largestEvents'], addRuler=True, longTable=True)
        
        self.elements.append(PageBreak())
        
        # Creating a header for the sub-section
        header = 'Extreme Waves Analysis'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))
        self.elements.append(Paragraph(self.generate_txt_content('extremeWaves_2'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('extremeWaves_3'), self.styleSheet['textBody']))
        
        # Inserting the EVA figure and the return periods table side by side, in a single
        # two-column wrapper row, so that the analysis stays on one page. Both cells are
        # built inline here rather than through insert_image / insert_table because those
        # helpers stack their blocks vertically and are shared with every other figure.
        fname = 'figure_9_extreme_value_analysis.jpeg'
        width = self.pfigures['fig_9']
        captionId = 'extremeValuesAnalysis'

        figColWidth = width + 12
        tableColWidth = self.doc.width + 1*inch - 12 - figColWidth

        figCell = [
            Paragraph(self.get_figure_caption(name=captionId), self.styleSheet['captions']),
            self.get_image(os.path.join(self.root, fname), width=width),
        ]

        content, style, caption = self.generate_table_content('summaryExtremeWaves')
        tableCell = [
            Paragraph(caption, self.styleSheet['captions']),
            Table(content, style=style),
        ]

        self.add_horizontal_ruler()
        self.elements.append(
            Table(
                [[figCell, tableCell]],
                colWidths=[figColWidth, tableColWidth],
                style=[
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('LEFTPADDING', (0, 0), (0, -1), 0),
                    ('RIGHTPADDING', (-1, 0), (-1, -1), 0),
                ],
            )
        )

        self.elements.append(PageBreak())
        
        
        
    def waveEnergyPage(self):
        
        # Creating a header for the section
        header = 'Waves Energy'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('waveEnergy_1'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('waveEnergy_2'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('waveEnergy_3'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('waveEnergy_4'), self.styleSheet['textBody']))
        
        # Inserting the wave power
        fname = 'figure_10_sea_states_occurence.jpeg'
        width = self.pfigures['fig_10']
        captionId = 'waveEnergy'
        self.insert_image(fname, width, captionId)
        
        self.elements.append(PageBreak())


    def windPage(self):
        
        # Creating a header for the section
        header = 'Wind'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('wind_1'), self.styleSheet['textBody']))
        
        # Inserting the wind rose (annual). Both figures only fit on this page if the
        # gaps around them are tighter than insert_image's defaults (a 25/10 ruler and
        # a 35pt spacer), so the two blocks are built inline here instead. This keeps
        # the spacing change local to the wind page and leaves every other figure alone.
        fname = 'figure_11_annual_wind_rose.jpeg'
        width = self.pfigures['fig_11']
        captionId = 'annualWindRose'
        self.elements.append(HRFlowable(width=0.9*inch + self.doc.width, color='#043e73', spaceBefore=6, spaceAfter=6))
        self.elements.append(Paragraph(self.get_figure_caption(name=captionId), self.styleSheet['captions']))
        self.elements.append(self.get_image(os.path.join(self.root, fname), width=width))

        # Inserting the monthly wind variability, now on the same page as figure 11
        fname = 'figure_12_monthly_wind_variability.jpeg'
        width = self.pfigures['fig_12']
        captionId = 'monthlyWindVariation'
        self.elements.append(Spacer(height=12, width=0))
        self.elements.append(Paragraph(self.get_figure_caption(name=captionId), self.styleSheet['captions']))
        self.elements.append(self.get_image(os.path.join(self.root, fname), width=width))

        self.elements.append(PageBreak())

    
    def acknowledgementPage(self):
        
        self.current_section = ''
        
        # Creating a header for the section
        header = 'Acknowledgements'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('acknoledgements_1'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('acknoledgements_2'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('acknoledgements_3'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('acknoledgements_4'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('acknoledgements_5'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('acknoledgements_6'), self.styleSheet['textBody']))
        self.elements.append(Paragraph(self.generate_txt_content('acknoledgements_7'), self.styleSheet['textBody']))
        
        self.elements.append(Spacer(height=50, width=0))
        # self.elements.append(PageBreak())


    def disclaimerPage(self):
        
        # Creating a header for the section
        header = 'Disclaimer'
        self.elements.append(Paragraph(header, self.styleSheet['bodyHeaders']))

        # Adding in the text
        self.elements.append(Paragraph(self.generate_txt_content('disclaimer'), self.styleSheet['textDisclaimer']))
        
        # self.elements.append(Spacer(height=50, width=0))
        # self.elements.append(PageBreak())



    def glossaryPage(self):
        
        glossary = self.load_json(self.glossaryFile)
        
        # Creating a header for this section
        self.elements.append(Paragraph('Glossary', self.styleSheet['bodyHeaders']))
        
        for items in glossary:
            term = Paragraph(items['term'], self.styleSheet['headerGlossary'])
            definition = Paragraph(items['definition'], self.styleSheet['textBody'])
            
            self.elements.append(term)
            self.elements.append(definition)
            
        self.elements.append(PageBreak())



        
        
        
        
        
