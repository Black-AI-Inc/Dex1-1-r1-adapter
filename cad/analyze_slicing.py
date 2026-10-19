#!/usr/bin/env python3
"""Inspect generic validation G-code. No machine-ready G-code is delivered."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection

from build_adapter import ROOT,P,hole_centers
from make_documentation import INK,TEAL,ORANGE

def parse(path):
    x=y=None;z=0.;e=0.;relative_e=False;kind='Custom';width=.45;records=[];types=[]
    for raw in path.read_text().splitlines():
        if raw.startswith(';TYPE:'):kind=raw[6:];continue
        if raw.startswith(';WIDTH:'):width=float(raw[7:]);continue
        line=raw.split(';')[0].strip()
        if not line:continue
        code=line.split()[0]
        vals={k:float(v) for k,v in re.findall(r'([XYZE])([-+0-9.]+)',line)}
        if code=='M82':relative_e=False
        if code=='M83':relative_e=True
        if code=='G92':
            if 'E' in vals:e=vals['E']
            continue
        if code not in ['G0','G1']:continue
        nx=vals.get('X',x);ny=vals.get('Y',y);nz=vals.get('Z',z)
        ne=(e+vals.get('E',0)) if relative_e else vals.get('E',e)
        if x is not None and y is not None and nx is not None and ny is not None:
            if ne-e>1e-6 and np.hypot(nx-x,ny-y)>1e-6:
                records.append([x-100,y-100,nx-100,ny-100,nz,width]);types.append(kind)
        x,y,z,e=nx,ny,nz,ne
    return np.array(records),np.array(types)

def distance_to_segments(seg,point):
    a=seg[:,:2];b=seg[:,2:4];d=b-a
    u=np.clip(np.sum((np.array(point)-a)*d,axis=1)/np.maximum(np.sum(d*d,axis=1),1e-12),0,1)
    return np.linalg.norm(a+u[:,None]*d-np.array(point),axis=1)-seg[:,5]/2

def run(folder):
    results={};datasets={}
    names=['adapter_B','fit_coupon_A','fit_coupon_B','fit_coupon_C','fastener_stack_coupon']
    for name in names:
        path=folder/(name+'_VALIDATION_ONLY.gcode');v,k=parse(path);datasets[name]=(v,k)
        obj=~np.char.startswith(k,'Support') & (k!='Skirt/Brim') & (k!='Custom')
        supp=np.char.startswith(k,'Support')
        assert obj.any()
        if name!='fastener_stack_coupon':assert supp.any(),name+' expected ear supports'
        assert v[:,4].min()>0
        results[name]={'object_deposition_layers':len(np.unique(v[obj,4])),
            'object_z_min_max_mm':[float(v[obj,4].min()),float(v[obj,4].max())],
            'extrusion_segment_counts':dict(Counter(k.tolist())),
            'support_z_min_max_mm':[float(v[supp,4].min()),float(v[supp,4].max())] if supp.any() else None,
            'STL_SHA256':hashlib.sha256((ROOT/'print'/(name+'.stl')).read_bytes()).hexdigest(),
            'gcode_SHA256':hashlib.sha256(path.read_bytes()).hexdigest()}
    v,k=datasets['adapter_B'];support=np.char.startswith(k,'Support')
    mid=(v[:,:2]+v[:,2:4])/2
    # Actual support deposited on top of the 8 mm face plate, below each ear.
    side_support=[]
    for sign in [-1,1]:
        mask=support & (sign*mid[:,0]>22) & (np.abs(mid[:,1])<10) & (v[:,4]>8) & (v[:,4]<9.15)
        assert mask.any(),('missing below-ear support',sign)
        side_support.append({'side':sign,'segments_above_plate_below_ear':int(mask.sum())})
    obj=~support & (k!='Skirt/Brim') & (k!='Custom')
    zs=np.unique(v[obj,4]);detail=[]
    cv,ck=datasets['fit_coupon_B'];cobj=~np.char.startswith(ck,'Support') & (ck!='Skirt/Brim') & (ck!='Custom')
    dz=P['face_thickness']-P['coupon_face_thickness'];aligned=[]
    for cz in np.unique(cv[cobj,4]):
        if cz<=P['coupon_face_thickness']+.2:continue
        mz=cz+dz
        assert np.min(abs(zs-mz))<1e-6,('coupon layer phase mismatch',cz,mz)
        cmask=cobj&np.isclose(cv[:,4],cz);mmask=obj&np.isclose(v[:,4],mz)
        cp=cv[cmask,:4].reshape(-1,2);mp=v[mmask,:4].reshape(-1,2)
        err=float(max(np.max(abs(cp.min(0)-mp.min(0))),np.max(abs(cp.max(0)-mp.max(0)))))
        assert err<.02,('coupon/main outer contour bounds differ',cz,err)
        aligned.append({'coupon_z':float(cz),'main_z':float(mz),'outer_contour_bound_difference_mm':err})
    for target_z in [1.,10.5,12.0]:
        z=zs[np.argmin(abs(zs-target_z))];seg=v[obj & np.isclose(v[:,4],z)]
        radius=1.7 if z<9.2 else 4.3
        margins=[]
        for xy in hole_centers():
            smallest=float(distance_to_segments(seg,xy).min());margins.append(smallest)
            assert smallest>radius-.08,('hole crossed by extrusion',z,xy,smallest)
        detail.append({'layer_z':float(z),'nominal_hole_radius':radius,'minimum_extrusion_envelope_radius_each_hole_mm':margins})
    # Inspect the 1.4 mm web between the two counterbores in each column.
    web=[]
    for x in [-15,15]:
        counts=[]
        for z in zs[(zs>9.3)&(zs<12.8)]:
            a=v[obj & np.isclose(v[:,4],z)];dx=a[:,2]-a[:,0]
            valid=(abs(dx)>1e-8)&((a[:,0]-x)*(a[:,2]-x)<=0)
            a=a[valid];u=(x-a[:,0])/(a[:,2]-a[:,0]);ys=a[:,1]+u*(a[:,3]-a[:,1])
            counts.append(int(np.sum(abs(ys)<.7)))
        assert min(counts)>=2,('web lost',x,counts)
        web.append({'x':x,'layers_checked':len(counts),'minimum_crossings_at_web_center':min(counts)})
    fig,axs=plt.subplots(2,2,figsize=(12,11),facecolor='#f6f8f9')
    targets=[8.60,8.76,9.64,12.04]
    allzs=np.unique(v[:,4])
    for ax,target in zip(axs.ravel(),targets):
        z=allzs[np.argmin(abs(allzs-target))];mask=np.isclose(v[:,4],z)
        if support[mask].any() and not obj[mask].any():
            below=zs[zs<z].max();ref=obj & np.isclose(v[:,4],below)
            ax.add_collection(LineCollection(v[ref,:4].reshape(-1,2,2),colors='#c5cdd3',linewidths=.5))
        colors=np.where(support[mask],ORANGE,TEAL)
        ax.add_collection(LineCollection(v[mask,:4].reshape(-1,2,2),colors=colors,linewidths=.65))
        ax.set(xlim=(-29,29),ylim=(-28,28),title=f'实际挤出路径 / Z = {z:.3f} mm')
        ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_facecolor('white')
    fig.suptitle('通用切片检查 · 0.4 喷嘴 / 0.16 层高 / 100% 填充\n蓝：模型挤出；橙：支撑（不是机器打印任务）',color=INK,fontsize=16)
    fig.tight_layout(rect=[0,0,1,.93]);fig.savefig(ROOT/'docs/slicing_paths.png',dpi=150);plt.close(fig)
    summary=(f'PrusaSlicer 2.5.2 通用配置切片：本体、A/B/C 试配件和夹持试片均成功生成路径。本体 {results["adapter_B"]["object_deposition_layers"]} 个模型沉积层；确认安装盘上方两侧卡耳支撑存在，抽检通孔/沉孔路径保持开口，1.4 mm 孔间薄壁的检查层均保留至少 2 条中心线穿越。详见 slicing_paths.png 和本 JSON。')
    report={'summary':summary,'engine':'PrusaSlicer 2.5.2+linux-x64-GTK3',
        'scope':'Generic toolpath geometry only; no physical printer, extrusion quality, ABS shrink or bond validation.',
        'config_sha256':hashlib.sha256((ROOT/'docs/slicing_geometry_check.ini').read_bytes()).hexdigest(),
        'parts':results,'ear_supports':side_support,'hole_checks':detail,'web_checks':web,
        'coupon_B_to_main_layer_alignment':{'z_offset':dz,'checks':aligned},
        'gcode_delivery':'Validation G-code intentionally excluded; slice with actual printer/material profile.'}
    (ROOT/'docs/slicer_validation.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(summary,flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('gcode_dir',type=Path);run(ap.parse_args().gcode_dir)
