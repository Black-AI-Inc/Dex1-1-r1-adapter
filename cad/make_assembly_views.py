#!/usr/bin/env python3
"""Official mesh appearance + new adapter; includes an offline rotatable viewer.
DEX mesh is for envelope/appearance only. Interface dimensions use the drawing.
"""
import json
from pathlib import Path

import cadquery as cq
import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

from build_adapter import ROOT,P,hole_centers
from make_documentation import load_stl,add_mesh,setup3d,INK,TEAL,ORANGE
from cpu_render import render

OUT=ROOT/"docs"


def read(path,scale=1,reduce=0):
    reader=vtk.vtkSTLReader();reader.SetFileName(str(path));reader.MergingOn();reader.Update()
    mesh=reader.GetOutput()
    if reduce:
        dec=vtk.vtkQuadricDecimation();dec.SetInputData(mesh);dec.SetTargetReduction(reduce);dec.Update();mesh=dec.GetOutput()
    vertices=vtk_to_numpy(mesh.GetPoints().GetData()).astype(float)*scale
    faces=vtk_to_numpy(mesh.GetPolys().GetData()).reshape(-1,4)[:,1:]
    return vertices,faces


def triangles(mesh):
    p,f=mesh;v=p[f]
    n=np.cross(v[:,1]-v[:,0],v[:,2]-v[:,0]);norm=np.linalg.norm(n,axis=1)
    n/=np.maximum(norm[:,None],1e-15)
    return v,n


def gripper(q=22.5):
    data=[]
    for name in ['Dex1_base_link','Dex1_finger_link_1','Dex1_finger_link_2']:
        p,f=read(ROOT/'references/g1_dex_meshes'/(name+'.STL'),1000,.65)
        if name.endswith('_1'):p[:,1]-=q
        if name.endswith('_2'):p[:,1]+=q
        # Drawing horizontal=mesh Y, vertical=mesh Z. Rotate drawing 90 degrees.
        p=p[:,[2,1,0]]*[-1,1,1];p[:,2]+=P['face_thickness']
        data.append((name,(p,f)))
    return data


def plot_mesh(ax,mesh,color):add_mesh(ax,*triangles(mesh),color)


def write_poly(path,mesh):
    p,f=mesh;poly=vtk.vtkPolyData();points=vtk.vtkPoints();points.SetData(numpy_to_vtk(p,deep=True));poly.SetPoints(points)
    cells=vtk.vtkCellArray()
    arr=np.column_stack([np.full(len(f),3),f]).astype(np.int64).ravel()
    from vtk.util.numpy_support import numpy_to_vtkIdTypeArray
    cells.SetCells(len(f),numpy_to_vtkIdTypeArray(arr,deep=True));poly.SetPolys(cells)
    writer=vtk.vtkSTLWriter();writer.SetFileName(str(path));writer.SetInputData(poly);writer.SetFileTypeToBinary();writer.Write()
    return poly


def collision_sweep():
    # Undecimated triangle contact detection in the fixed official arm pose.
    arm=read(ROOT/'references/r1_arm_normalized.stl')
    apoly=write_poly(ROOT/'references/review_arm_mesh.stl',arm)
    rows=[]
    for q in np.linspace(-20,24.5,10):
        for name in ['Dex1_base_link','Dex1_finger_link_1','Dex1_finger_link_2']:
            if name=='Dex1_base_link' and q!=-20:continue
            p,f=read(ROOT/'references/g1_dex_meshes'/(name+'.STL'),1000)
            if name.endswith('_1'):p[:,1]-=q
            if name.endswith('_2'):p[:,1]+=q
            p=p[:,[2,1,0]]*[-1,1,1];p[:,2]+=P['face_thickness']
            poly=write_poly(ROOT/'references/review_gripper_sweep.stl',(p,f))
            cf=vtk.vtkCollisionDetectionFilter();cf.SetInputData(0,apoly);cf.SetInputData(1,poly)
            t=vtk.vtkTransform();cf.SetTransform(0,t);cf.SetTransform(1,t)
            cf.SetCollisionModeToFirstContact();cf.SetBoxTolerance(.01);cf.SetCellTolerance(.001);cf.Update()
            contacts=int(cf.GetNumberOfContacts())
            rows.append({'part':name,'joint_position_mm':float(q),'triangle_contacts':contacts})
    result={'reference_pose':'fixed pose in official R1 STEP; NOT a robot joint sweep',
            'method':'VTK triangle surface intersection, undeformed mesh; no wiring. No physical clearance guarantee.',
            'cases':rows,'all_surface_contact_checks_passed':all(x['triangle_contacts']==0 for x in rows)}
    (OUT/'gripper_envelope_validation.json').write_text(json.dumps(result,indent=2))
    return result


def run(skip_checks=False):
    adapter=read(ROOT/'references/review_adapter.stl')
    wrist=read(ROOT/'references/r1_wrist_normalized.stl',reduce=.5)
    arm=read(ROOT/'references/r1_arm_normalized.stl',reduce=.85)
    dex=gripper()
    pieces=[('R1-7A 官方参考模型',arm,'#a7b2ba'),('ABS 转接件',adapter,TEAL)]+[(n,m,'#343b42') for n,m in dex]
    for i in range(1,5):
        pieces.append((f'M3×16 螺钉 {i}',read(ROOT/f'references/review_bolt_{i}.stl'),'#c19650'))
        pieces.append((f'M3 平垫片 {i}',read(ROOT/f'references/review_washer_{i}.stl'),'#9ca9b5'))
    for name,m in dex:write_poly(ROOT/'references'/(name+'_assembled.stl'),m)
    # Full-arm illustration in the manufacturer's world pose.
    frame=json.loads((ROOT/'references/arm_transform.json').read_text())
    r=np.array(frame['normalized_to_world_R']);t=np.array(frame['translation'])
    # Original world Y is vertical. Display as Z, preserving handedness.
    display=np.array([[1,0,0],[0,0,-1],[0,1,0]])
    def world(m):
        p,f=m;return ((p@r.T+t)@display.T,f)
    wp=[(n,world(m),c) for n,m,c in pieces]
    bounds=np.concatenate([m[0] for _,m,_ in wp]);lo=bounds.min(0);hi=bounds.max(0)
    fig=plt.figure(figsize=(16,9),facecolor='#f6f8f9')
    fig.text(.04,.94,'R1-7A × DEX1-1  /  装配比例预览',fontsize=24,color=INK,weight='bold')
    fig.text(.04,.893,'v0.2 · 官方臂 / 夹爪外形 + 独立设计的 ABS 转接件',fontsize=12,color=TEAL)
    ax=fig.add_axes([.01,.10,.64,.76])
    ax.imshow(render([(m,c) for _,m,c in wp],1700,1250,25,120));ax.axis('off')
    ax=fig.add_axes([.63,.24,.35,.55])
    local=[(wrist,'#a7b2ba'),(adapter,TEAL)]+[(m,'#343b42') for _,m in dex]
    motor_path=ROOT/'references/review_last_motor.stl'
    if not motor_path.exists():
        motor=cq.importers.importBrep(str(ROOT/'references/r1_arm_normalized.brep')).val().Solids()[14]
        cq.exporters.export(motor,str(motor_path),tolerance=.15,angularTolerance=.2)
    local.append((read(motor_path,reduce=.3),'#78858e'))
    ax.imshow(render(local,850,1050,22,-65));ax.axis('off')
    fig.text(.66,.81,'腕部局部',fontsize=16,color=INK)
    fig.text(.66,.15,'蓝色：Ø52 × 13 mm 转接件\n夹爪安装面：腕壳前端面前方 8 mm\n爪尖约在前方 151 mm（随实物 TCP 标定）',fontsize=11,color=INK,linespacing=1.65)
    fig.text(.04,.045,'同轴安装形式与产品图相近；原厂连接件尺寸未公开，不能认定长度和结构完全一致。',fontsize=11,color=ORANGE)
    fig.savefig(OUT/'complete_assembly.png',dpi=155);plt.close(fig)

    # Bench assembly: the driver approaches from the exposed rear, before wrist assembly.
    fig=plt.figure(figsize=(16,8),facecolor='#f6f8f9')
    fig.text(.04,.93,'先在台面拧夹爪螺钉，再装入腕壳',fontsize=25,color=INK,weight='bold')
    fig.text(.04,.875,'4 × M3×16 + 4 × M3 平垫片（外径 8，厚 0.5）',fontsize=14,color=TEAL)
    ax=fig.add_axes([.02,.12,.47,.70],projection='3d')
    plot_mesh(ax,adapter,TEAL)
    for _,m in dex:plot_mesh(ax,m,'#343b42')
    for i in range(1,5):
        for name,c in [('bolt','#c19650'),('washer','#a7b2ba')]:
            p,f=read(ROOT/f'references/review_{name}_{i}.stl');p[:,2]-=24 if name=='bolt' else 12
            plot_mesh(ax,(p,f),c)
    setup3d(ax,[(-35,35),(-65,65),(-40,158)],-20,-55)
    fig.text(.04,.10,'1  垫片放进背面沉孔，螺钉穿过 ABS 通孔，拧入 DEX 金属螺纹。',fontsize=10.5,color=INK)
    ax=fig.add_axes([.52,.30,.44,.44])
    from matplotlib.patches import Rectangle
    ax.add_patch(Rectangle((-5,-4.3),3.8,8.6,facecolor='white',edgecolor=TEAL))
    ax.add_patch(Rectangle((-1.2,-4.3),9.2,8.6,facecolor='#d5eef0',edgecolor=TEAL))
    ax.add_patch(Rectangle((-1.2,-1.7),9.2,3.4,facecolor='white',edgecolor='none'))
    ax.add_patch(Rectangle((8,-5),10,10,facecolor='#d4d8dc',edgecolor=INK))
    ax.add_patch(Rectangle((8,-1.525),8,3.05,facecolor='white',edgecolor='none'))
    ax.add_patch(Rectangle((-1.7,-1.5),16,3,facecolor='#c19650',edgecolor=INK))
    ax.add_patch(Rectangle((-4.7,-2.75),3,5.5,facecolor='#c19650',edgecolor=INK))
    for y in [-4,1.6]:ax.add_patch(Rectangle((-1.7,y),.5,2.4,facecolor='#8597a6',edgecolor=INK))
    ax.text(-4.8,6,'螺钉头',fontsize=10);ax.text(2.5,6,'ABS 9.2',ha='center',fontsize=10)
    ax.text(12,6,'DEX 金属底座',ha='center',fontsize=10)
    ax.annotate('工具从背面进入',(-4.7,0),(-11,-8),fontsize=10,color=INK,arrowprops={'arrowstyle':'->','color':INK})
    ax.annotate('平垫片 0.5',(-1.45,3.4),(-5,10),fontsize=10,color=INK,arrowprops={'arrowstyle':'->','color':INK})
    ax.annotate('名义露出 / 旋入 6.3',(11,0),(8,-8),fontsize=10,color=INK,arrowprops={'arrowstyle':'->','color':INK})
    ax.set(xlim=(-12,20),ylim=(-11,13));ax.set_aspect('equal');ax.axis('off')
    fig.text(.54,.22,'2  四颗先手动入牙，再按对角顺序逐步贴合。\n    内六角用 2.5 mm；备用十字盘头用匹配的 #2 螺丝刀。\n3  支撑夹爪，按厂家复装方法合拢腕壳。',fontsize=11,color=INK,linespacing=1.75)
    fig.text(.54,.095,'合拢后不具备已验证的原位补拧路径。\n安装盘与腕壳有间隙时，不能靠加大螺钉扭矩补偿。',fontsize=11,color=ORANGE,linespacing=1.6)
    fig.savefig(OUT/'fastener_assembly.png',dpi=155);plt.close(fig)

    # Offline interactive appearance viewer; all JS and meshes are embedded.
    traces=[]
    for n,(p,f),c in wp:
        traces.append(go.Mesh3d(x=p[:,0],y=p[:,1],z=p[:,2],i=f[:,0],j=f[:,1],k=f[:,2],
            color=c,name=n,flatshading=False,hovertemplate=n+'<extra></extra>',showlegend=True,
            lighting=dict(ambient=.55,diffuse=.7,specular=.18,roughness=.8)))
    fig=go.Figure(traces)
    fig.update_layout(title='R1-7A + DEX1-1 / ABS v0.2（外形参考，未实物验收）',
        scene=dict(aspectmode='data',xaxis_title='mm',yaxis_title='mm',zaxis_title='mm',
                   camera=dict(eye=dict(x=1.5,y=-1.8,z=1.1))),
        margin=dict(l=0,r=0,t=65,b=0),legend=dict(x=0,y=1),paper_bgcolor='#f6f8f9')
    fig.write_html(str(OUT/'assembly_interactive.html'),include_plotlyjs=True,full_html=True)
    print('Created complete assembly preview, fastener diagram and offline viewer.',flush=True)
    if not skip_checks:print(json.dumps(collision_sweep(),indent=2),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--views-only',action='store_true')
    run(parser.parse_args().views_only)
