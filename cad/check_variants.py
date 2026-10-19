#!/usr/bin/env python3
"""Check alternate collars and thread coupons using their exported STL meshes."""
import json
from build_v2 import OUT,P
from check_v2 import mesh_from_stl
rows=[]
a=mesh_from_stl(OUT/'print/anchor.stl',True)
male=mesh_from_stl(OUT/'print/thread_male_coupon.stl',True).translate((0,0,-(P['face_z']-4.8)))
for code in ['C020','C030','C040']:
    nut=mesh_from_stl(OUT/'print'/('thread_nut_coupon_'+code+'.stl'))
    for z in [0,.6,1.2,2.4,3.6,4.8,6]:
        v=(male^nut.rotate((0,0,z/4.8*360)).translate((0,0,z))).volume()
        assert v<.05,(code,z,v)
        rows.append({'test':'coupon_'+code,'z_mm':z,'overlap_mm3':v,'passed':True})
    if code=='C030':continue
    full=mesh_from_stl(OUT/'print'/('preload_collar_'+code+'.stl'))
    for z in [0,4.8,9.6,14.4]:
        at=z+P['thrust_plate_thickness']
        v=(a^full.rotate((0,0,at/4.8*360)).translate((0,0,at))).volume()
        assert v<.05,(code,z,v)
        rows.append({'test':'full_'+code,'z_mm':z,'overlap_mm3':v,'passed':True})
(OUT/'docs/variant_validation.json').write_text(json.dumps({'method':'Manifold intersection of exported STL','passed_checks':len(rows),'checks':rows},indent=2));print(len(rows),'variant checks passed')
