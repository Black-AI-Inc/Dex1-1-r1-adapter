#!/usr/bin/env python3
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import vtk
from vtk.util.numpy_support import vtk_to_numpy,numpy_to_vtk,numpy_to_vtkIdTypeArray
from build_v2 import OUT,REF,P
from cpu_render import render
plt.rcParams['font.family']='Noto Sans CJK JP'

def read(path,scale=1,reduce=0):
    r=vtk.vtkSTLReader();r.SetFileName(str(path));r.MergingOn();r.Update();m=r.GetOutput()
    if reduce:
        dec=vtk.vtkQuadricDecimation();dec.SetInputData(m);dec.SetTargetReduction(reduce);dec.Update();m=dec.GetOutput()
    return vtk_to_numpy(m.GetPoints().GetData()).astype(float)*scale,vtk_to_numpy(m.GetPolys().GetData()).reshape(-1,4)[:,1:]
def move(m,d):return m[0]+d,m[1]
def poly(m):
    p,f=m;v=vtk.vtkPolyData();pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(p,deep=True));v.SetPoints(pts)
    cells=vtk.vtkCellArray();cells.SetCells(len(f),numpy_to_vtkIdTypeArray(np.column_stack([np.full(len(f),3),f]).astype(np.int64).ravel(),deep=True));v.SetPolys(cells);return v

def dex(q=22.5,reduce=.65):
    out=[]
    for name in ['Dex1_base_link','Dex1_finger_link_1','Dex1_finger_link_2']:
        p,f=read(REF/'g1_dex_meshes'/(name+'.STL'),1000,reduce)
        if name.endswith('_1'):p[:,1]-=q
        if name.endswith('_2'):p[:,1]+=q
        p=p[:,[2,1,0]]*[-1,1,1];p[:,2]+=P['face_z']+P['nominal_anchor_pullup']
        out.append((name,(p,f)))
    return out

def main():
    colors={'anchor':'#238693','preload_collar':'#ce9730','thrust_plate':'#667482'}
    parts=[(name,read(OUT/'docs'/(name+'_assembled.stl')),col) for name,col in colors.items()]
    arm=read(REF/'r1_arm_normalized.stl',reduce=.85);wrist=read(REF/'r1_wrist_normalized.stl',reduce=.4);grip=dex()
    frame=json.loads((REF/'arm_transform.json').read_text());r=np.array(frame['normalized_to_world_R']);t=np.array(frame['translation']);disp=np.array([[1,0,0],[0,0,-1],[0,1,0]])
    def world(m):return (m[0]@r.T+t)@disp.T,m[1]
    full=[(world(arm),'#aab3ba')]+[(world(m),'#34393f') for _,m,_ in parts]+[(world(m),'#292f35') for _,m in grip]
    fig=plt.figure(figsize=(16,9),facecolor='#f6f8f9');fig.text(.04,.94,'R1-7A × DEX1-1  /  V2 可调压紧转接环',fontsize=23,weight='bold',color='#20323c')
    ax=fig.add_axes([.0,.11,.66,.76]);ax.imshow(render(full,1550,1200,25,120));ax.axis('off')
    local=[(wrist,'#aab3ba')]+[(m,c) for _,m,c in parts]+[(m,'#343b42') for _,m in grip]
    ax=fig.add_axes([.65,.25,.34,.55]);ax.imshow(render(local,900,1100,22,-65));ax.axis('off')
    fig.text(.66,.83,'局部按零件着色',fontsize=14,color='#20323c')
    fig.text(.66,.14,'蓝：转接主体  /  金：压紧环  /  灰：承压垫环\n夹爪安装面：腕壳前方约 14.5 mm\n主体 + 垫环 + 一只压紧环，共 3 个打印件',fontsize=11,color='#20323c',linespacing=1.7)
    fig.text(.04,.045,'左图按黑色 ABS 示意；与官方图同轴布置。新增压紧环与局部锁紧耳，外形不等同原厂连接件。',fontsize=11,color='#906414')
    fig.savefig(OUT/'docs/complete_assembly.png',dpi=155);plt.close(fig)
    # Exploded components are in assembly orientation, not print orientation.
    fig=plt.figure(figsize=(15,7),facecolor='#f6f8f9');fig.text(.04,.93,'装配顺序：先套垫环和压紧环，再拧夹爪螺钉',fontsize=21,weight='bold',color='#20323c')
    exploded=[(wrist,'#aab3ba')]
    for name,m,c in parts:exploded.append((move(m,np.array([0,0,{'thrust_plate':12,'anchor':35,'preload_collar':65}[name]])),c))
    ax=fig.add_axes([.0,.07,.65,.78]);ax.imshow(render(exploded,1400,900,15,-65));ax.axis('off')
    fig.text(.67,.77,'1  垫环从主体后侧穿过卡耳\n2  压紧环从主体前侧旋入\n3  台面拧紧 4 颗夹爪螺钉\n4  按官方维修要求合拢腕壳\n5  手旋压紧环消除轴向自由间隙\n6  拧锁紧耳上的 M3 螺钉并做标记',fontsize=12,linespacing=2,color='#20323c')
    fig.text(.67,.14,'5 × M3×20 圆柱头内六角螺钉\n5 × M3 平垫片（Ø8 × 0.5）\n1 × 普通 M3 六角螺母（AF5.5 × 2.4）\n工具：2.5 mm 内六角',fontsize=11,linespacing=1.65,color='#906414')
    fig.savefig(OUT/'docs/exploded_assembly.png',dpi=155);plt.close(fig)
    traces=[]
    for name,m,col in [('R1 官方参考',arm,'#aab3ba')]+parts+[(n,m,'#343b42') for n,m in grip]:
        p,f=m;traces.append(go.Mesh3d(x=p[:,0],y=p[:,1],z=p[:,2],i=f[:,0],j=f[:,1],k=f[:,2],color=col,name=name,showlegend=True,flatshading=False))
    f=go.Figure(traces);f.update_layout(title='V2 近就位装配预览 / 点击图例隐藏零件；参考姿态，不是运动仿真',scene=dict(aspectmode='data'),margin=dict(l=0,r=0,t=60,b=0))
    f.write_html(str(OUT/'docs/assembly_interactive.html'),include_plotlyjs=True)
    # Official fixed arm pose and independent gripper finger displacement samples.
    ap=poly(read(REF/'r1_arm_normalized.stl'));checks=[]
    for q in np.linspace(-20,24.5,10):
        for name,m in dex(q,reduce=0):
            if name=='Dex1_base_link' and q!=-20:continue
            filt=vtk.vtkCollisionDetectionFilter();filt.SetInputData(0,ap);filt.SetInputData(1,poly(m));tr=vtk.vtkTransform();filt.SetTransform(0,tr);filt.SetTransform(1,tr);filt.SetCollisionModeToFirstContact();filt.SetBoxTolerance(.01);filt.SetCellTolerance(.001);filt.Update()
            count=int(filt.GetNumberOfContacts());assert count==0,(name,q,count)
            checks.append({'part':name,'prismatic_displacement_mm':float(q),'surface_contacts':count})
    base=dex(0,reduce=0)[0][1][0]
    gap=float(base[:,2].min()-(P['thrust_plate_thickness']+P['collar_height']))
    assert gap>.8
    (OUT/'docs/gripper_envelope_validation.json').write_text(json.dumps({'cases':checks,'collar_to_gripper_axial_gap_mm':gap,'scope':'Undecimated official meshes, fixed arm reference pose, 10 sampled finger positions; no full-arm joint sweep, cables or physical qualification.'},indent=2))
    print('Views generated, 21 official-mesh contact checks passed; collar/gripper axial gap',gap,flush=True)
if __name__=='__main__':main()
