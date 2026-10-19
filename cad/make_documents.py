#!/usr/bin/env python3
"""Create offline English/Chinese assembly PDFs and a dimension summary."""
import re,json,html
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
import ezdxf
from build_v2 import OUT,P
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))

def inline(s):
    s=s.replace('Ø','diam. ').replace('·',' / ')
    s=re.sub(r'`([^`]+)`',r'\1',s)
    s=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',s)
    s=html.escape(s);s=re.sub(r'\*\*(.*?)\*\*',r'<b>\1</b>',s)
    return s

def pdf_guide(lang):
    file='assembly_guide'+('.zh-CN' if lang=='zh' else '')
    font='STSong-Light' if lang=='zh' else 'Helvetica'
    body=ParagraphStyle('body',fontName=font,fontSize=9.8,leading=14.5,spaceAfter=7,wordWrap='CJK' if lang=='zh' else None)
    head=ParagraphStyle('head',parent=body,fontSize=14,leading=19,spaceBefore=12,spaceAfter=8,keepWithNext=True)
    title=ParagraphStyle('title',parent=head,fontSize=21,leading=26)
    lines=(OUT/'docs'/(file+'.md')).read_text().splitlines();flow=[];i=0
    while i<len(lines):
        line=lines[i].strip();i+=1
        if not line:continue
        if line.startswith('!['):
            path=re.search(r'\(([^)]+)\)',line).group(1)
            from PIL import Image as PILImage
            with PILImage.open(OUT/'docs'/path) as im:w,h=im.size
            flow.append(Image(str(OUT/'docs'/path),width=470,height=470*h/w));flow.append(Spacer(1,8));continue
        if line.startswith('|'):
            rows=[line]
            while i<len(lines) and lines[i].strip().startswith('|'):rows.append(lines[i]);i+=1
            data=[]
            for row in rows:
                cells=[x.strip() for x in row.strip().strip('|').split('|')]
                if all(re.fullmatch(r'[-: ]+',x) for x in cells):continue
                data.append([Paragraph(inline(x),body) for x in cells])
            tab=Table(data,colWidths=[155,115,200],repeatRows=1);tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e9f1f3')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.3,colors.HexColor('#cad3d8')),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5)]));flow.append(tab);flow.append(Spacer(1,10));continue
        sty=title if line.startswith('# ') else head if line.startswith('## ') else body
        text=re.sub(r'^#{1,2} ','',line)
        if lang=='en':text=text.replace('简体中文','Simplified Chinese')
        flow.append(Paragraph(inline(text),sty))
    def footer(c,d):
        c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#687984'));c.drawString(44,24,'R1-7A / DEX1-1 | v2.0.0-rc1 | Physical validation pending');c.drawRightString(551,24,str(d.page))
    SimpleDocTemplate(str(OUT/'docs'/(file+'.pdf')),pagesize=A4,leftMargin=44,rightMargin=44,topMargin=36,bottomMargin=42,title=file,author='Black-AI-Inc contributors').build(flow,onFirstPage=footer,onLaterPages=footer)

def drawing():
    path=OUT/'docs/dimensions.pdf';c=canvas.Canvas(str(path),pagesize=A4);c.setTitle('V2 interface and screw-stack dimensions');c.setFont('Helvetica-Bold',17);c.drawString(42,800,'V2 interface dimensions / mm')
    c.setFont('Helvetica',10);c.drawString(42,778,'Nominal dimensions. Inspect STEP for the full shape; this is not a load qualification.')
    cx,cy,scale=178,590,4
    c.setStrokeColor(colors.HexColor('#247f8c'));c.circle(cx,cy,25.8*scale);c.circle(cx,cy,6*scale)
    for x,y in P['hole_centers']:c.circle(cx+x*scale,cy+y*scale,1.7*scale)
    c.setStrokeColor(colors.HexColor('#b7c5cb'));c.line(cx-120,cy,cx+120,cy);c.line(cx,cy-120,cx,cy+120)
    c.setFont('Helvetica',10)
    for i,line in enumerate(['DEX hole pattern (rotated 90 degrees)','4 x dia. 3.4 clearance holes','X = +/-15; Y = +/-5','M3 x 20 into DEX metal threads','Drawing thread depth: 8','Centre passage: dia. 12','Barrel dia. 49 is not a locating fit']):c.drawString(318,680-i*21,line)
    rows=[('Neck diameter / flats','44.5 / 27.6'),('Rounded retaining ears','dia. 51.5; width 19.6; thickness 1.8'),('Ear end radius','0.9'),('Rear insert depth','5.0'),('Anchor front face (unseated)','Z = +14.4'),('Nominal axial take-up','0.1'),('Thrust plate','OD58; thickness 2.4'),('Collar','58 across flats; 11.2 high; local tab to Y=-37'),('Custom printed thread','pitch 4.8; major dia. 51.6; minor dia. 48.4'),('Thread form','45 degree flanks; 0.6 crest; not an ISO M thread'),('Radial fit allowances','C020 = 0.2; C030 = 0.3; C040 = 0.4'),('Rear screw counterbores','4 x dia. 8.6; depth 6.4'),('Gripper screw stack','13.0 plastic + 0.5 washer; 20 screw'),('Nominal thread insertion','6.5; 1.5 remaining drawing depth'),('Ordinary captive nut','M3; AF5.5 x 2.4; pocket AF5.8')]
    y=435
    for a,b in rows:
        c.setFillColor(colors.HexColor('#20323c'));c.drawString(42,y,a);c.drawString(248,y,b);y-=22
    c.setFont('Helvetica',9);c.drawString(42,66,'Measure the real wrist and effective blind-hole depth. No manufacturing tolerance has been certified.');c.save()
    d=ezdxf.new();d.units=4;ms=d.modelspace();ms.add_circle((0,0),6)
    for xy in P['hole_centers']:ms.add_circle(xy,1.7)
    ms.add_text('DEX1-1: 4x clearance 3.4 at X=+/-15, Y=+/-5; units mm',dxfattribs={'height':2}).set_placement((-36,-24));d.saveas(OUT/'cad/dex_mount_holes.dxf')
if __name__=='__main__':
    pdf_guide('en');pdf_guide('zh');drawing();print('English/Chinese PDFs and dimensions generated')
