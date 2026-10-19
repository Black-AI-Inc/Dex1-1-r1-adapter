#!/usr/bin/env python3
"""Validate actual toolpaths; G-code is never a printer-ready deliverable."""
import hashlib,json,re,sys
from collections import Counter
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from build_v2 import OUT,P
from package_geometry import read_stl

def parse(path):
    x=y=None;z=e=0.;rel=False;kind='Custom';width=.45;data=[];types=[]
    for raw in path.read_text().splitlines():
        if raw.startswith(';TYPE:'):kind=raw[6:];continue
        if raw.startswith(';WIDTH:'):width=float(raw[7:]);continue
        line=raw.split(';')[0].strip()
        if not line:continue
        code=line.split()[0];vs={k:float(v) for k,v in re.findall(r'([XYZE])([-+0-9.]+)',line)}
        if code=='M82':rel=False
        if code=='M83':rel=True
        if code=='G92':e=vs.get('E',e);continue
        if code not in ['G0','G1']:continue
        nx=vs.get('X',x);ny=vs.get('Y',y);nz=vs.get('Z',z);ne=e+vs.get('E',0) if rel else vs.get('E',e)
        if None not in (x,y,nx,ny) and ne-e>1e-6 and np.hypot(nx-x,ny-y)>1e-6:data.append([x-100,y-100,nx-100,ny-100,nz,width]);types.append(kind)
        x,y,z,e=nx,ny,nz,ne
    return np.array(data),np.array(types)
def dist(seg,p):
    a=seg[:,:2];d=seg[:,2:4]-a;u=np.clip(((p-a)*d).sum(1)/np.maximum((d*d).sum(1),1e-12),0,1)
    return np.linalg.norm(a+u[:,None]*d-p,axis=1)-seg[:,5]/2

def run(folder):
    parts={};data={}
    for stl in sorted((OUT/'print').glob('*.stl')):
        f=folder/(stl.stem+'.gcode');v,k=parse(f)
        verts,_=read_stl(stl);center=(verts.min(0)+verts.max(0))/2
        v[:,[0,2]]+=center[0];v[:,[1,3]]+=center[1]
        sup=np.char.startswith(k,'Support');obj=~sup&(k!='Skirt/Brim')&(k!='Custom')
        assert obj.any() and v[:,4].min()>0
        if stl.stem not in ['anchor','wrist_fit_coupon']:assert not sup.any(),stl.stem
        else:assert sup.any(),stl.stem
        raw=f.read_text();stats={}
        for key in ['filament used [g]','estimated printing time (normal mode)']:
            m=re.search(r'^; '+re.escape(key)+r' = (.+)$',raw,re.M)
            if m:stats[key]=m.group(1)
        parts[stl.stem]={'layers':len(np.unique(v[obj,4])),'object_z_range':v[obj,4][[np.argmin(v[obj,4]),np.argmax(v[obj,4])]].tolist(),'path_counts':dict(Counter(k.tolist())),'STL_SHA256':hashlib.sha256(stl.read_bytes()).hexdigest(),'gcode_SHA256':hashlib.sha256(f.read_bytes()).hexdigest(),'generic_estimates':stats}
        data[stl.stem]=(v,k,obj,sup)
    av,ak,ao,ass=data['anchor'];zs=np.unique(av[ao,4]);detail=[]
    for target in [1,12,14,18.8]:
        z=zs[abs(zs-target).argmin()];seg=av[ao&np.isclose(av[:,4],z)];rad=1.7 if z<13 else 4.3
        margins=[float(dist(seg,np.array(xy)).min()) for xy in P['hole_centers']]
        assert min(margins)>rad-.08,(z,margins)
        detail.append({'layer':z,'hole_radius':rad,'minimum_extrusion_clearance':margins})
    mid=(av[:,:2]+av[:,2:4])/2;ears=[]
    for sign in [-1,1]:
        mask=ass&(sign*mid[:,0]>22.1)&(abs(mid[:,1])<10)&(av[:,4]>11)&(av[:,4]<15.5)
        assert mask.any();ears.append({'side':sign,'support_segments':int(mask.sum()),'zrange':[float(av[mask,4].min()),float(av[mask,4].max())]})
    webs=[]
    for x in [-15,15]:
        counts=[]
        for z in zs[(zs>13.2)&(zs<19.2)]:
            ss=av[ao&np.isclose(av[:,4],z)];dx=ss[:,2]-ss[:,0];valid=(abs(dx)>1e-8)&((ss[:,0]-x)*(ss[:,2]-x)<=0);ss=ss[valid]
            ys=ss[:,1]+(x-ss[:,0])/(ss[:,2]-ss[:,0])*(ss[:,3]-ss[:,1]);counts.append(int((abs(ys)<.7).sum()))
        assert min(counts)>=2;webs.append({'x':x,'layers':len(counts),'min_crossings':min(counts)})
    cv,ck,co,cs=data['preload_collar'];cz=np.unique(cv[co,4]);z=cz[abs(cz-P['pinch_axis_z']).argmin()];seg=cv[co&np.isclose(cv[:,4],z)]
    checks=[]
    for pt,limit in [([-4,-32],1.55),([7,-32],1.3),([0,-28],.4),([0,-34],.4)]:
        d=float(dist(seg,np.array(pt)).min());assert d>limit,(pt,d);checks.append({'point_xy':pt,'clearance':d,'required':limit,'z':z})
    # Same layer phase for the wrist-fit ear profile, excluding the coupon's top disk.
    wv,wk,wo,ws=data['wrist_fit_coupon'];align=[]
    for z in np.unique(wv[wo,4]):
        if z<1.5:continue
        main_z=z+P['face_z']-1.28
        assert abs(zs-main_z).min()<1e-5
        wp=wv[wo&np.isclose(wv[:,4],z),:4].reshape(-1,2);mp=av[ao&np.isclose(av[:,4],main_z),:4].reshape(-1,2)
        err=float(max(abs(wp.min(0)-mp.min(0)).max(),abs(wp.max(0)-mp.max(0)).max()))
        assert err<.025,(z,err);align.append({'coupon_layer':z,'main_layer':main_z,'bound_error':err})
    plt.rcParams['font.family']='Noto Sans CJK JP'
    fig,axs=plt.subplots(2,2,figsize=(12,10),facecolor='#f6f8f9')
    for ax,(name,target) in zip(axs.ravel(),[('anchor',15.16),('anchor',17.64),('preload_collar',5.64),('preload_collar',8.68)]):
        v,k,obj,sup=data[name];zz=np.unique(v[:,4]);z=zz[abs(zz-target).argmin()];mask=np.isclose(v[:,4],z)
        if sup[mask].any() and not obj[mask].any():
            below=np.max(v[obj&(v[:,4]<z),4]);bm=obj&np.isclose(v[:,4],below)
            ax.add_collection(LineCollection(v[bm,:4].reshape(-1,2,2),colors='#c7cdd2',linewidths=.5))
        ax.add_collection(LineCollection(v[mask,:4].reshape(-1,2,2),colors=np.where(sup[mask],'#d18b25','#20808b'),linewidths=.6))
        ax.set(xlim=(-34,34),ylim=(-40,33),title=f'{name} / Z={z:.2f} mm');ax.set_aspect('equal');ax.grid(alpha=.2)
    fig.suptitle('V2 toolpaths / Teal: model, amber: support\nGeometry checks only. Re-slice using your actual printer and ABS profile.',fontsize=14)
    fig.tight_layout(rect=[0,0,1,.92]);fig.savefig(OUT/'docs/slicing_paths.png',dpi=160);plt.close(fig)
    report={'engine':'PrusaSlicer 2.5.2','scope':'Toolpath geometry only, no physical printer validation','parts':parts,'ear_support':ears,'main_holes':detail,'counterbore_webs':webs,'collar_hole_and_split_checks':checks,'wrist_coupon_layer_alignment':align,'supports':'Only anchor and wrist fit coupon use automatic support at 40 degrees. All remaining parts sliced without support.','gcode_delivery':'Excluded; these are not machine-ready programs.'}
    (OUT/'docs/slicer_validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({'parts':len(parts),'ears':ears,'webs':webs,'collar':checks},indent=2))
if __name__=='__main__':run(Path(sys.argv[1]))
