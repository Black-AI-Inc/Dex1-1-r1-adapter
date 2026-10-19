#!/usr/bin/env python3
"""Render CAD previews, dimensioned drawings, DXF and Chinese instructions."""
import json
import math
import struct
from pathlib import Path
from xml.sax.saxutils import escape

import cadquery as cq
import ezdxf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (Image, PageBreak, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

from build_adapter import ROOT, P, hole_centers, slab

DOC=ROOT/"docs"
font_manager.fontManager.addfont("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc")
FONT=font_manager.FontProperties(fname="/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc").get_name()
plt.rcParams.update({"font.family":FONT,"axes.unicode_minus":False,
                     "font.size":10,"pdf.fonttype":42})
INK="#203a4c";TEAL="#27879b";ORANGE="#bb6738";GRAY="#a8b4be"
F=P["profiles"]["B"]


def load_stl(path):
    raw=path.read_bytes();n,=struct.unpack_from("<I",raw,80)
    d=np.dtype([("n","<f4",3),("v","<f4",(3,3)),("a","<u2")])
    t=np.frombuffer(raw,dtype=d,count=n,offset=84)
    return t["v"].astype(float),t["n"].astype(float)


def assembly_mesh():
    v,n=load_stl(ROOT/"print/adapter_B.stl")
    v[:,:,1]*=-1;v[:,:,2]=P["face_thickness"]-v[:,:,2]
    n[:,1:]*=-1
    return v,n


def add_mesh(ax,v,n,color):
    c=np.array(matplotlib.colors.to_rgb(color));light=np.array([-.3,-.5,.82]);light/=np.linalg.norm(light)
    shade=.58+.38*np.maximum(0,n@light)
    col=np.clip(c[None,:]*shade[:,None],0,1)
    ax.add_collection3d(Poly3DCollection(v,facecolors=col,edgecolors="none",linewidths=0,
                                       antialiased=False,zsort="average"))


def setup3d(ax,limits,elev=30,azim=-55):
    ax.set(xlim=limits[0],ylim=limits[1],zlim=limits[2])
    ax.set_box_aspect(tuple(b-a for a,b in limits));ax.view_init(elev,azim)
    ax.set_proj_type("ortho");ax.set_axis_off();ax.set_facecolor("#f6f8f9")


def previews():
    front,nfront=assembly_mesh();back,nback=load_stl(ROOT/"print/adapter_B.stl")
    wrist=cq.importers.importBrep(str(ROOT/"references/r1_wrist_normalized.brep")).val()
    # A physical section of the reference wrist; the rear is cropped for clarity.
    box=cq.Workplane("XY").box(150,90,30).translate((0,-45,-7)).val()
    section=wrist.intersect(box)
    cq.exporters.export(section,str(ROOT/"references/wrist_preview_section.stl"),tolerance=.08,angularTolerance=.12)
    vw,nw=load_stl(ROOT/"references/wrist_preview_section.stl")
    fig=plt.figure(figsize=(16,7.8),facecolor="#f6f8f9")
    fig.text(.04,.93,"R1-7A  ×  DEX1-1",fontsize=27,color=INK,weight="bold")
    fig.text(.04,.88,"ABS 转接法兰  |  v0.2 实物试配版",fontsize=15,color=TEAL)
    fig.text(.96,.925,"单位 mm\n官方腕壳几何校核通过",ha="right",fontsize=10.5,color=INK)
    for i,(title,caption) in enumerate([
            ("夹爪侧","Ø52 安装面 · 4 × Ø3.4 通孔"),
            ("机械臂侧","两侧卡耳 · 平边防转 · 螺钉头沉孔"),
            ("腕壳剖视装配","灰色为官方腕壳；蓝色为 ABS 法兰")]):
        ax=fig.add_axes([.035+i*.322,.2,.305,.62],projection="3d")
        if i==0:
            add_mesh(ax,front,nfront,TEAL);setup3d(ax,[(-29,29),(-29,29),(-6,12)],32,-52)
        elif i==1:
            add_mesh(ax,back,nback,TEAL);setup3d(ax,[(-29,29),(-29,29),(-1,18)],37,-52)
        else:
            add_mesh(ax,vw,nw,"#a8b4be");add_mesh(ax,front,nfront,TEAL)
            setup3d(ax,[(-33,33),(-26,29),(-16,12)],24,-65)
        fig.text(.04+i*.322,.17,title,color=INK,fontsize=15,weight="bold")
        fig.text(.04+i*.322,.125,caption,color=INK,fontsize=9.3)
    fig.text(.04,.055,"先打印 B 档试配件；额定承载能力仍需实测。",fontsize=11,color=ORANGE)
    fig.text(.96,.055,"本体 52 × 52 × 13 mm  /  约 21.0 g（实心 ABS）",ha="right",fontsize=10.5,color=INK)
    fig.savefig(DOC/"preview.png",dpi=150,facecolor=fig.get_facecolor());plt.close(fig)


def dimh(ax,x1,x2,y,text,from_y=None):
    if from_y is not None:
        for x in [x1,x2]:ax.plot([x,x],[from_y,y+1],lw=.55,color=INK)
    ax.annotate("",(x1,y),(x2,y),arrowprops={"arrowstyle":"<->","lw":.7,"color":INK,"shrinkA":0,"shrinkB":0})
    ax.text((x1+x2)/2,y+1.1,text,ha="center",va="bottom",fontsize=9,color=INK,
            bbox={"fc":"white","ec":"none","pad":.2})


def dimv(ax,y1,y2,x,text,from_x=None):
    if from_x is not None:
        for y in [y1,y2]:ax.plot([from_x,x+1],[y,y],lw=.55,color=INK)
    ax.annotate("",(x,y1),(x,y2),arrowprops={"arrowstyle":"<->","lw":.7,"color":INK,"shrinkA":0,"shrinkB":0})
    ax.text(x+1.1,(y1+y2)/2,text,ha="left",va="center",fontsize=9,color=INK,
            bbox={"fc":"white","ec":"none","pad":.2})


def outline(w,ax,color=INK,ls="-",lw=1.1):
    face=w.faces(">Z").val()
    for e in face.outerWire().Edges():
        a=np.array([v.toTuple() for v in e.sample(50)[0]])
        ax.plot(a[:,0],a[:,1],ls=ls,lw=lw,color=color)


def drawings():
    fig=plt.figure(figsize=(16.54,11.69),facecolor="white")
    fig.text(.045,.955,"R1-7A / DEX1-1  ABS 转接法兰",fontsize=23,color=INK)
    fig.text(.045,.918,"B 档 · 尺寸图 · v0.2  /  单位 mm  /  示意投影，不按纸图量取",fontsize=12,color=TEAL)
    ax=fig.add_axes([.04,.38,.30,.49]);ax.set_aspect("equal");ax.axis("off")
    ax.add_patch(Circle((0,0),26,fill=False,color=INK,lw=1.2));ax.add_patch(Circle((0,0),6,fill=False,color=INK))
    for x,y in hole_centers():
        ax.add_patch(Circle((x,y),1.7,fill=False,color=INK))
        ax.plot([x-3,x+3],[y,y],color=GRAY,lw=.5);ax.plot([x,x],[y-3,y+3],color=GRAY,lw=.5)
    ax.axhline(0,color=GRAY,lw=.5,ls="-.");ax.axvline(0,color=GRAY,lw=.5,ls="-.")
    dimh(ax,-26,26,-34,"Ø52",-2);dimh(ax,-15,15,17,"30",5);dimv(ax,-5,5,31,"10",15)
    ax.annotate("4 × Ø3.4 通孔",(-15,-5),(-33,35),fontsize=9,color=INK,
                arrowprops={"arrowstyle":"->","color":INK,"lw":.7})
    ax.annotate("Ø12 中心孔",(6,0),(10,-19),fontsize=9,color=INK,
                arrowprops={"arrowstyle":"->","color":INK,"lw":.7})
    ax.set(xlim=(-40,42),ylim=(-42,42));ax.set_title("夹爪侧 / Z = +8",fontsize=13,color=INK,pad=10)

    ax=fig.add_axes([.36,.38,.30,.49]);ax.set_aspect("equal");ax.axis("off")
    neck=slab(F["neck_diameter"],0,1,F["across_flats"]).edges("|Z").fillet(P["neck_corner_fillet"])
    lip=slab(F["retaining_diameter"],0,1,19.6)
    outline(lip,ax,GRAY,"--",.9);outline(neck,ax)
    ax.add_patch(Circle((0,0),26,fill=False,color=GRAY,lw=.6,ls="--"))
    ax.add_patch(Circle((0,0),6,fill=False,color=INK))
    for x,y in hole_centers():
        ax.add_patch(Circle((x,y),4.3,fill=False,color=INK));ax.add_patch(Circle((x,y),1.7,fill=False,color=INK,lw=.7))
    dimh(ax,-22.25,22.25,-26,"定位轮廓 Ø44.5",0)
    dimv(ax,-13.8,13.8,31,"27.6",12)
    ax.annotate("4 × Ø8.6 沉孔\n从背面深 3.8",(15,5),(-34,30),fontsize=9,color=INK,
                arrowprops={"arrowstyle":"->","color":INK,"lw":.7})
    ax.annotate("4 × R4 过渡",(17,13.3),(-32,-35),fontsize=9,color=INK,
                arrowprops={"arrowstyle":"->","color":INK,"lw":.7})
    ax.set(xlim=(-40,42),ylim=(-42,42));ax.set_title("机械臂侧 / 卡耳虚线表示",fontsize=13,color=INK,pad=10)

    ax=fig.add_axes([.69,.38,.27,.49]);ax.set_aspect("equal");ax.axis("off")
    # X-Z silhouette through the centre of the captured ears (chamfers simplified).
    h=F["retaining_thickness"]/2;zl=-2-h;zu=-2+h
    x=[-22.25,-22.25,-25.75,-25.75,-22.25,-22.25,-26,-26,26,26,22.25,22.25,25.75,25.75,22.25,22.25,-22.25]
    z=[-5,zl,zl,zu,zu,0,0,8,8,0,0,zu,zu,zl,zl,-5,-5]
    ax.fill(x,z,color="#d5eef0",ec=INK,lw=1.1)
    ax.fill_between([-6,6],[-5,-5],[8,8],color="white");ax.plot([-6,-6],[-5,8],color=INK,lw=.7);ax.plot([6,6],[-5,8],color=INK,lw=.7)
    ax.axhline(0,color=ORANGE,ls="-.",lw=.7)
    ax.text(-30,.8,"腕壳前端基准 Z=0",fontsize=8,color=ORANGE)
    dimv(ax,-5,8,33,"13",26);dimv(ax,0,8,-34,"8",-26)
    dimh(ax,-25.75,25.75,-12,"卡耳外径 Ø51.5",zl)
    ax.annotate("卡耳厚 1.7\nZ = −2.85 ~ −1.15",(25.75,-2),(0,23),fontsize=9,color=INK,
                arrowprops={"arrowstyle":"->","color":INK,"lw":.7})
    ax.annotate("插入深度 5",(22.25,-5),(-30,-22),fontsize=9,color=INK,
                arrowprops={"arrowstyle":"->","color":INK,"lw":.7})
    ax.set(xlim=(-42,44),ylim=(-39,38));ax.set_title("X-Z 示意剖面",fontsize=13,color=INK,pad=10)

    notes=[
        "接口：DEX 官方图 M3 深 8 孔组为 10 × 30；本模型旋转 90°，装配坐标为 (±15, ±5)。20 × 15 为 Ø4 浅孔组，未使用。",
        "卡耳仅位于腕壳两侧 20 mm 开口内；B 档卡耳宽 19.6。卡耳边缘 C0.4，安装盘外缘 C0.35，背面导入 C0.2。",
        "B 档名义间隙：定位圆 / 卡耳圆每侧 0.25；平边每侧 0.20；卡耳上下各 0.15。R4 圆角与边缘倒角以 STEP 为准。",
        "紧固：4 × M3×16 内六角圆柱头螺钉 + 4 × M3 平垫片（外径 8、内径 3.2、厚 0.5）。预计旋入 6.3，须核实实物盲孔有效深度。",
        "材料与验证：ABS；已通过官方腕壳干涉及封闭网格检查。尚未打印、试装或载荷试验，不作为 2 kg 额定承载件。"
    ]
    for i,t in enumerate(notes):fig.text(.045,.285-i*.040,t,fontsize=9.5,color=INK)
    fig.text(.045,.045,"文件：adapter_B.step / adapter_B.stl  |  坐标：腕部前端面 Z=0，夹爪安装面 Z=+8  |  2026-10-18",fontsize=8.7,color=INK)
    fig.text(.955,.045,"01 / 02",ha="right",fontsize=9,color=INK)
    fig.savefig(DOC/"dimensioned_drawing.png",dpi=150)

    fig2=plt.figure(figsize=(16.54,11.69),facecolor="white")
    fig2.text(.045,.955,"官方腕壳与转接件的截面核对",fontsize=23,color=INK)
    fig2.text(.045,.918,"灰线：官方 STEP 截面（偏置 1 mm 避开壳体分缝）  /  蓝色：B 档转接件",fontsize=12,color=TEAL)
    rows=json.loads((ROOT/"references/wrist_section_points.json").read_text())
    ax=fig2.add_axes([.06,.41,.88,.39]);ax.set_aspect("equal")
    for row in rows["xz"]:
        a=np.array(row);ax.plot(a[:,0],a[:,2],color="#7e8c96",lw=1.4)
    ax.fill(x,z,color=TEAL,alpha=.40,ec=TEAL,lw=1.2)
    ax.fill_between([-6,6],[-5,-5],[8,8],color="white")
    ax.axhline(0,color=ORANGE,ls="--",lw=.8)
    ax.set(xlim=(-33,33),ylim=(-12,12),xlabel="X / mm",ylabel="Z / mm")
    ax.grid(lw=.4,color="#dee4e8");ax.tick_params(labelsize=9)
    ax.annotate("官方卡槽：Ø52，Z = −3 ~ −1",(25.98,-2),(-31,10),fontsize=11,color=INK,
                arrowprops={"arrowstyle":"->","color":INK})
    ax.annotate("官方入口 Ø45",(-22.48,-.5),(-30,-10),fontsize=11,color=INK,
                arrowprops={"arrowstyle":"->","color":INK})
    ax.annotate("卡耳嵌入槽内",(24.3,-2),(8,10),fontsize=11,color=TEAL,
                arrowprops={"arrowstyle":"->","color":TEAL})
    items=[
        "腕壳开口平边间距：28；四角 R4；卡槽两侧窗口宽度：20。前端并非标准 ISO 圆周螺孔法兰。",
        "需要通过原装两半腕壳合拢捕获卡耳；完整卡耳不能从前端硬压过 Ø45 的入口。",
        "三档试配件均与同一官方腕壳无实体干涉；实际孔槽、表面涂层、机型修订和打印误差仍需用实物确认。",
        "A / B / C 是配合间隙档位，并非可叠装的三个零件。使用哪档，就在 parameters.json 中选择对应 fit_profile 后重建本体。",
        "装配 STEP 仅用于检查；灰色腕壳为参考件，不应作为打印任务。"
    ]
    for i,t in enumerate(items):fig2.text(.06,.31-i*.043,t,color=INK,fontsize=10.2)
    fig2.text(.045,.045,"参考模型：unitreerobotics/r1-7a_sdk · 2c89fe4f60f0c98f1bc06795cb2477cc73d0c92c · STEP 内“末端连接件”",fontsize=8.5,color=INK)
    fig2.text(.955,.045,"02 / 02",ha="right",fontsize=9,color=INK)
    fig2.savefig(DOC/"reference_section_check.png",dpi=130)
    with PdfPages(DOC/"engineering_drawings.pdf") as pdf:
        pdf.savefig(fig);pdf.savefig(fig2)
    plt.close(fig);plt.close(fig2)


def dxf():
    doc=ezdxf.new("R2010");doc.units=4;m=doc.modelspace()
    for n,c in [("DEX_FACE",4),("CENTERLINES",8),("TEXT",7)]:doc.layers.new(n,dxfattribs={"color":c})
    m.add_circle((0,0),26,dxfattribs={"layer":"DEX_FACE"});m.add_circle((0,0),6,dxfattribs={"layer":"DEX_FACE"})
    for x,y in hole_centers():
        m.add_circle((x,y),1.7,dxfattribs={"layer":"DEX_FACE"})
        m.add_line((x-3,y),(x+3,y),dxfattribs={"layer":"CENTERLINES"});m.add_line((x,y-3),(x,y+3),dxfattribs={"layer":"CENTERLINES"})
    for s,pos in [("DEX mating face / units mm / scale 1:1",(-28,33)),
        ("4 x DIA 3.4 THRU at X=+/-15, Y=+/-5",(-28,-33)),
        ("REAR: 4 x DIA 8.6 CBORE, DEPTH 3.8",(-28,-38)),
        ("DIA 52 OUTSIDE / DIA 12 CENTER / FIT PROTOTYPE",(-28,-43))]:
        m.add_text(s,dxfattribs={"height":1.7,"layer":"TEXT"}).dxf.insert=pos
    doc.saveas(DOC/"DEX_mount_hole_pattern_mm.dxf")


def manual():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles=getSampleStyleSheet()
    body=ParagraphStyle("CN",fontName="STSong-Light",fontSize=10.3,leading=15.8,
                        textColor=colors.HexColor(INK),spaceAfter=7,wordWrap="CJK")
    h1=ParagraphStyle("CNH1",parent=body,fontSize=20,leading=27,textColor=colors.HexColor(INK),spaceAfter=12)
    h2=ParagraphStyle("CNH2",parent=body,fontSize=13.5,leading=21,textColor=colors.HexColor(TEAL),spaceBefore=10,spaceAfter=7)
    small=ParagraphStyle("CNSmall",parent=body,fontSize=8.5,leading=12.5)
    def para(s,style=body):
        # STSong CID fonts do not include the engineering diameter symbol.
        return Paragraph(s.replace("Ø","直径 ").replace("³","3").replace("·"," "),style)
    def table(data,widths):
        data=[[para(str(v),small) for v in row] for row in data]
        t=Table(data,colWidths=widths,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e8f1f4")),
            ("LINEBELOW",(0,0),(-1,0),.6,colors.HexColor(TEAL)),
            ("LINEBELOW",(0,1),(-1,-1),.3,colors.HexColor("#d5dfe5")),
            ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),7),
            ("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        return t
    story=[]
    story += [para("R1-7A × DEX1-1<br/>ABS 转接法兰使用说明",h1),
              para("v0.2 · 2026-10-18 · 基于官方几何的实物试配版",h2),
              Image(str(DOC/"preview.png"),width=175*mm,height=85.3*mm),Spacer(1,6*mm),
              para("设计适用范围",h2),
              para("面向图示新发售的独立七轴 Unitree R1-7A，利用原装两半腕壳的内卡槽捕获法兰两侧卡耳，再用四颗 M3 螺钉连接 DEX1-1。采用平边防转，ABS 本体不承担打印螺纹。需能按厂家允许的装配方式打开并复原末端两半腕壳；仅凭前端孔口无法塞入完整卡耳。"),
              table([["项目","B 档本体"],["尺寸 / 质量","最大外径 52；总高 13；实心 ABS 约 21.0 g，不含支撑与紧固件"],
                  ["机械臂侧","Ø44.5 定位轮廓，平边 27.6，四角 R4；插入 5；卡耳 Ø51.5、宽 19.6、厚 1.7"],
                  ["夹爪侧","平安装面 Z=+8；4×Ø3.4 通孔，装配坐标 (±15,±5)；中心 Ø12"],
                  ["当前验证 / 限制","几何、硬件和台面工具通道通过校核；B 档保留名义间隙，须按附加复核报告实测后定尺寸。"]],[37*mm,138*mm]),
              para("R1-7A 的 2 kg 产品载荷不等于此 ABS 转接件的承载能力。先核对实物卡槽、试配，再做夹爪自重及逐级载荷验证。",small),PageBreak()]

    story += [para("1　先打印试配件",h1),
      para("首先使用 fit_coupon_B.stl。A 更紧，C 更松；这些试配件保留真实卡槽和孔位，前安装盘减薄为 1.28 mm，且刻有档位字母。每件约 7.2 g，仅用于配合检查，不可承载或运行机械臂。"),
      table([["档位","定位直径","卡耳直径 / 宽 / 厚","平边","每侧径向 / 平边余量"],
          ["A 紧","44.7","51.7 / 19.8 / 1.8","27.8","0.15 / 0.10"],
          ["B 默认","44.5","51.5 / 19.6 / 1.7","27.6","0.25 / 0.20"],
          ["C 松","44.3","51.3 / 19.4 / 1.6","27.4","0.35 / 0.30"]],
          [20*mm,27*mm,60*mm,23*mm,45*mm]),Spacer(1,3*mm),
      para("试配顺序",h2),
      para("① 断电并支撑机械臂；先测量腕壳入口、卡槽和平边。参考值：入口 Ø45，卡槽 Ø52、轴向 2（位于前端面后方 1～3），平边 28，两侧窗口宽 20。实物明显不符时先改参数。"),
      para("② 按厂家允许的装配方法松开末端两半腕壳，将 B 试配件放入槽内并复原。不得将卡耳硬压过入口，不靠过度拧紧壳体螺钉消除间隙。不要拆动关节传动、轴承或电机定位结构。"),
      para("③ 检查腕壳能正常合拢、无撑开缝隙；卡耳有正向捕获；无明显转动和轴向晃动。B 过紧再试 C，过松再试 A。若三档都不合适，实测后调整。更换档位后须重建对应本体；包内本体仅为 B 档。"),
      para("④ 用四颗短螺钉松配检查 DEX 孔位，观察接插件、线束及安装面是否受挡。试配件较薄，不能直接使用本体的 M3×16；建议试配 M3×8 配 0.5 mm 垫片，理论旋入约 5.0，仍须核对实物。"),
      para("ABS 打印起点",h2),
      table([["设置","建议"],["姿态","使用 print/ 文件，已将夹爪平安装面朝下；勿打印灰色参考腕壳"],
          ["结构","0.4 喷嘴；0.16 层高；6～8 道壁；100% 填充；顶底 ≥8 层"],
          ["温度 / 防翘","封闭腔体；喷嘴和床温按耗材规格，常见起点 250 / 105 °C；8～10 mm brim"],
          ["支撑","仅支撑两侧卡耳下方的悬挑；允许支撑落在安装盘背面；孔内不生成支撑"],
          ["尺寸","默认 100% 比例。先用 ABS_50mm_calibration.stl 验证 50 mm 长度和孔径；按设备实测补偿收缩，勿盲目统一放大。"]],[34*mm,141*mm]),
      para("清除支撑和 brim，尤其是卡耳下面、平边及贴合面；手工清理后再复测。Ø3.4 通孔可用对应钻头轻修，保留平直安装面。3MF 只含毫米制几何，没有指定打印机或 ABS 配置。",small),PageBreak()]

    story += [para("2　本体紧固与装配",h1),
      table([["数量","物料","备注"],["1","ABS 法兰本体","adapter_B.stl；其他档位先改参数重建"],
          ["4","M3×16 内六角圆柱头螺钉","ISO 4762 / DIN 912；头径约 5.5、头高约 3"],
          ["4","M3 平垫片","外径 8、内径约 3.2、厚 0.5；置于沉孔底部"],
          ["原装","R1-7A 腕壳紧固件","沿用厂家紧固和复装要求，不以加大扭矩补偿配合错误"]],[18*mm,65*mm,92*mm]),
      para("DEX 孔组不要混用",h2),
      para("官方端面图的 4×M3 深 8 螺纹孔为 10×30 矩形，原坐标 (±5,±15)。图中的 20×15 对应 4×Ø4 深 2 浅孔；外围另有 M3 深 5 孔组。本设计只使用 M3 深 8 这一组。模型将 DEX 绕轴旋转 90°，因此本体孔位为 (±15,±5)。Ø49 外观尺寸未被当作精密定位止口，未增加未经证实的夹爪套口。"),
      para("螺钉长度核算",h2),
      para("总高 13 − 背面沉孔深 3.8 = ABS 夹持厚度 9.2；加 0.5 垫片后，M3×16 预计旋入 16 − 9.2 − 0.5 = 6.3。相对图示深 8，名义余量 1.7。先量实际可用螺纹深度及螺钉尖端余量，确认没有顶底；不要自行换更长螺钉。"),
      para("装配顺序",h2),
      para("① 先用新增 fastener_stack_coupon.stl 检查所购硬件、露出长度和压痕，再在台面上完成法兰与 DEX 连接。四个垫片放入机械臂侧沉孔，从背面穿入 M3×16，进入 DEX 金属螺纹；对角均匀轻拧，确保安装面贴平且 ABS 无压溃。螺钉头与垫片均应沉入背面轮廓内。"),
      para("② 将夹爪与法兰组件置入打开的腕壳，使卡耳进入两侧槽、平边对正；按厂家要求复原腕壳。确认接插件和线束不夹伤，且腕部运动范围内不受拉扯。若厂家不允许打开此处，先取得其允许的复装方法。"),
      para("③ 断电手动检查轴向保持、抗转和螺钉贴合。先支撑夹爪进行静态自重检查，再空载低速运行，逐步增加测试载荷并记录。试配成功并不代表 ABS 卡耳已通过强度或疲劳验证。"),
      para("④ 更新负载与 TCP：本体约 21.0 g；DEX 官方质量约 550 g，另加紧固件及实际附件。本模型夹爪安装面位于腕壳前端面前方 8 mm，TCP 按实际装配重新标定。"),
      para("使用边界",h2),
      para("两侧卡耳较薄，层间结合、支撑清理、螺钉面压和 ABS 蠕变会影响保持能力。无载荷试验数据时不赋予额定载荷；出现裂纹、白化、变形或间隙增长应停用并更换。完整载荷能力需结合打印工艺、温度、夹爪重心、运动加速度和实物结构验证。",small),PageBreak()]

    val=json.loads((DOC/"validation.json").read_text())
    story += [para("3　文件、参数与依据",h1),
      table([["文件","用途"],["print/adapter_B.stl / adapter_B_mm.3mf","B 档本体；已放置打印姿态，单位 mm"],
          ["print/fit_coupon_A、B、C.stl","三个独立试配件；fit_coupons_ABC_mm.3mf 为合并摆盘"],
          ["cad/adapter_B.step","独立本体，装配坐标；多数 CAD 可直接打开"],
          ["cad/assembly_fit_check.step / assembly_section.step","含官方参考腕壳的装配及剖视；不是打印任务"],
          ["cad/build_adapter.py / parameters.json","参数化源文件；需 CadQuery 2.7.x"],
          ["docs/engineering_drawings.pdf","两页尺寸图和官方截面对比"],
          ["docs/validation.json","实体、STL、干涉与螺钉长度核算记录"]],[85*mm,90*mm]),
      para("修改与重建",h2),
      para("在 cad/parameters.json 中选择 fit_profile 为 A、B 或 C；也可按实测改 profiles、安装盘厚度、孔径等。运行 python cad/build_adapter.py --validate-reference；再运行 python cad/make_print_package.py。脚本会检查实体、网格及与附带参考腕壳的干涉；改孔距会触发螺钉沉孔边距检查。安装盘厚度变化后须重新核算螺钉长度。"),
      para("文档脚本中的展示尺寸围绕默认 B 档绘制；如果改模型参数，应同步修订图纸标注和物料长度，再执行文档脚本。重新选择 A/C 会输出对应 adapter_A / adapter_C 文件；不要把试配件当成本体。",small),
      para("已完成的检查",h2),
      para("本体与 A/B/C 试配件均为一个有效实体；STL 网格每条边由两个三角面共享，绕向一致、体积为正。四件与指定官方腕壳的相交体积均为 0 mm³（数值阈值 0.01）。新增螺钉、垫片、工具通道及夹爪外形检查见《装配复核与实测清单》。尚未实物打印、配合、有限元或载荷 / 疲劳测试。"),
      para("官方依据",h2),
      para('<link href="https://github.com/unitreerobotics/r1-7a_sdk">1. 宇树 r1-7a_sdk 官方仓库</link>：step/R1-7A机械臂_简化模型_0928.STEP；从“末端连接件”提取两半腕壳，测量截面并进行装配校核。',small),
      para("固定提交：2c89fe4f60f0c98f1bc06795cb2477cc73d0c92c。参考 STEP 为简化模型，不保证与你们手中每个生产批次完全一致。",small),
      para('<link href="https://www.unitree.com/Dex1-1/">2. DEX1-1 官方产品页与尺寸图</link>：确认 M3 深 8 的 10×30 孔组、Ø4 浅孔组和夹爪质量。尺寸图附于 references/。',small),
      para('<link href="https://www.unitree.com/R1-7a/">3. R1-7A 官方产品页</link>：确认独立七轴型号。社区检索未找到可核验的对应法兰；最终接口尺寸均取自官方资料，未套用其他机器人标准。',small),
      para("官方腕壳参考几何属于 Unitree；原仓库许可保留在 references/UNITREE_REPOSITORY_LICENSE.txt。本方案为独立设计的试配件，不代表厂家认证。原始整臂大文件未打包，可从 sources.txt 中的固定版本链接下载。",small)]
    def footer(c,doc):
        c.setStrokeColor(colors.HexColor("#d5dfe5"));c.line(18*mm,15*mm,192*mm,15*mm)
        c.setFont("STSong-Light",8);c.setFillColor(colors.HexColor(INK))
        c.drawString(18*mm,10*mm,"R1-7A / DEX1-1  |  ABS v0.2  |  实物试配与载荷验证前")
        c.drawRightString(192*mm,10*mm,str(doc.page))
    SimpleDocTemplate(str(DOC/"使用说明_中文.pdf"),pagesize=A4,
        leftMargin=18*mm,rightMargin=17*mm,topMargin=16*mm,bottomMargin=22*mm,
        title="R1-7A DEX1-1 ABS 转接法兰 v0.2",author="Independent parametric design").build(story,onFirstPage=footer,onLaterPages=footer)


if __name__=="__main__":
    previews();drawings();dxf();manual()
    print("Rendered previews, two-page engineering drawing, DXF, and Chinese manual.")
