#!/usr/bin/env python3
"""Static 17 mm short-leg L-key envelopes, no assertion of serviceability."""
import json
import math
import cadquery as cq
from build_adapter import ROOT,hole_centers
from check_assembly import overlap

def run():
    arm=cq.importers.importBrep(str(ROOT/'references/r1_arm_normalized.brep')).val().Solids()
    data=[]
    for i,(x,y) in enumerate(hole_centers()):
        for angle in [-45,-30,-15,0,15,30,45]:
            a=math.radians(angle+(180 if x<0 else 0));z=-20.4
            leg=cq.Solid.makeCylinder(1.5,15.7,cq.Vector(x,y,z))
            cross=cq.Solid.makeCylinder(1.5,60,cq.Vector(x,y,z),cq.Vector(math.cos(a),math.sin(a),0))
            tool=leg.fuse(cross)
            data.append({'hole':i+1,'short_leg_nominal_mm':17,'angle_deg':angle,
                         'interference_mm3':sum(overlap(tool,arm[k]) for k in [14,15,16])})
    (ROOT/'docs/L_key_access_exploration.json').write_text(json.dumps({
        'scope':'Static envelopes only; no insertion path or uninterrupted 60-degree turning arc proven. Generic AF2.5 tool, 3 mm envelope, 17 mm short leg.',
        'cases':data},indent=2))
    print('Checked',len(data),'static L-key envelopes.')

if __name__=='__main__':run()
