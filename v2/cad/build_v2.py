#!/usr/bin/env python3
"""V2 captured anchor + coarse printed preload collar; all dimensions mm.
The collar creates axial preload; rotational holding is friction dependent.
No printed M3 threads. All physical fit/loads remain unqualified.
"""
import json, math, sys
from pathlib import Path
import cadquery as cq
OUT=Path(__file__).resolve().parents[1]
REF=OUT/'references'
if not REF.exists():REF=OUT.parent/'references'
from mesh_tools import validate_mesh
P=json.loads((OUT/'cad/parameters.json').read_text())

def cylinder(r,z,h):return cq.Solid.makeCylinder(r,h,cq.Vector(0,0,z))
def box(x,y,z,center):return cq.Workplane('XY').box(x,y,z).translate(center).val()
def helix_rib(radial=0.,axial=0.,phase=0.,one_turn=False):
    r=P['thread_root_radius'];d=P['thread_depth'];c=P['thread_crest_width']/2
    start=-P['thread_pitch']+phase;length=P['thread_pitch']*1.04 if one_turn else P['face_z']+3*P['thread_pitch']
    # 45 degree flanks, 0.6 mm crest, 1.0 mm root land at nominal dimensions.
    lower=r+radial-.1
    pts=[(lower,start-(c+d+.1+axial)),(r+d+radial,start-c-axial),
         (r+d+radial,start+c+axial),(lower,start+(c+d+.1+axial))]
    path=cq.Wire.makeHelix(P['thread_pitch'],length,r,center=(0,0,start))
    return cq.Workplane('XZ').polyline(pts).close().sweep(path,isFrenet=True).val()

def anchor():
    n=(cq.Workplane('XY').workplane(offset=-P['neck_depth'])
       .circle(P['neck_diameter']/2).extrude(P['neck_depth']+P['shoulder_z']+.3))
    n=n.intersect(cq.Workplane('XY').box(60,P['neck_flats'],20).translate((0,0,0)))
    n=n.edges('|Z').fillet(P['neck_corner_radius'])
    n=n.faces('<Z').edges().chamfer(.2).val()
    # A true capsule in YZ follows the R1 rounded slot ends. Localized slicer support
    # is required under the two ears in the specified print orientation.
    ear=(cq.Workplane('YZ').center(0,P['ear_center_z'])
         .slot2D(P['ear_width'],P['ear_thickness'],0).extrude(60,both=True).val())
    ear=ear.intersect(cylinder(P['ear_diameter']/2,-4,4))
    z=P['shoulder_z'];h=P['face_z']-z
    core=cylinder(P['thread_root_radius'],z,h)
    rib=helix_rib().intersect(cylinder(27,z,h))
    body=n.fuse(ear).fuse(core).fuse(rib)
    # Start/end chamfer using conical envelope; threaded start remains accessible.
    envelope=cylinder(26,z+.6,h-1.2).fuse(cq.Solid.makeCone(25.2,26,.6,cq.Vector(0,0,z)))
    envelope=envelope.fuse(cq.Solid.makeCone(26,25.2,.6,cq.Vector(0,0,P['face_z']-.6)))
    # Restrict only the threaded zone; preserve the captured ears below Z=1.
    body=body.intersect(envelope.fuse(box(80,80,20,(0,0,z-10))))
    body=body.cut(cylinder(6,-6,P['face_z']+7))
    for x,y in P['hole_centers']:
        body=body.cut(cylinder(P['bolt_hole_diameter']/2,-6,P['face_z']+7).translate((x,y,0)))
        body=body.cut(cylinder(P['bolt_pocket_diameter']/2,-5.01,P['bolt_pocket_depth']+.01).translate((x,y,0)))
    return body

def collar(radial=None,phase=0.,height=None,split=True):
    if radial is None:radial=P['thread_radial_clearance']
    h=P['collar_height'] if height is None else height
    # Twelve flats are both the hand grip and a printable tool interface.
    od=P['collar_across_flats']/math.cos(math.pi/12)
    if split:
        rr=od/2
        pts=[(rr*math.cos(math.radians(a)),rr*math.sin(math.radians(a))) for a in range(0,241,30)]
        pts += [(-9,-27.5),(-9,-37),(9,-37),(9,-27.5)]
        pts += [(rr*math.cos(math.radians(a)),rr*math.sin(math.radians(a))) for a in [300,330]]
        w=cq.Workplane('XY').polyline(pts).close().extrude(h).edges('|Z').fillet(.4).val()
        w=w.cut(box(P['split_gap'],45,h+2,(0,-22.5,h/2)))
    else:
        w=cq.Workplane('XY').polygon(12,od).extrude(h).val()
    if split:
        y=P['pinch_axis_y'];z=P['pinch_axis_z']
        through=cq.Solid.makeCylinder(1.7,40,cq.Vector(-20,y,z),cq.Vector(1,0,0))
        w=w.cut(through)
        # Hex pocket opens at +X, normal nut 5.5 AF x 2.4 high.
        pocket=(cq.Workplane('YZ').workplane(offset=5.5).center(y,z)
                .polygon(6,P['nut_pocket_af']/math.cos(math.pi/6)).extrude(5).val())
        w=w.cut(pocket)
    w=w.cut(cylinder(P['thread_root_radius']+radial,-1,h+2))
    # Cut overlapping short helical segments. A single multi-turn periodic
    # surface produced an incomplete groove in this OCCT build.
    cutter=helix_rib(radial,P['thread_axial_clearance'],phase,one_turn=True)
    for i in range(math.ceil((h+2*P['thread_pitch'])/P['thread_pitch'])):
        w=w.cut(cutter.translate((0,0,i*P['thread_pitch'])))
    # 0.5 mm lead-in bore chamfers without thinning the outside contact rim.
    bore=P['thread_root_radius']+radial
    w=w.cut(cq.Solid.makeCone(bore+.5,bore,.5,cq.Vector(0,0,0)))
    w=w.cut(cq.Solid.makeCone(bore,bore+.5,.5,cq.Vector(0,0,h-.5)))
    # Unifying cylindrical/periodic faces corrupts this slit-thread BRep in the installed OCCT build.
    # Keep the valid boolean result and verify its mesh instead.
    return w

def thrust_plate():
    h=P['thrust_plate_thickness']
    w=cylinder(P['thrust_plate_od']/2,0,h)
    bore=(cq.Workplane('XY').circle(45.1/2).extrude(h+2)
          .intersect(cq.Workplane('XY').box(60,28.2,20)).edges('|Z').fillet(4).val())
    ears=cylinder(52.1/2,-1,h+2).intersect(box(60,20.2,h+2,(0,0,h/2)))
    return w.cut(bore.translate((0,0,-1))).cut(ears)


def printable(shape,name,zflip=None):
    cq.exporters.export(shape,str(OUT/'cad'/(name+'.step')))
    s=shape if zflip is None else shape.rotate((0,0,0),(1,0,0),180).translate((0,0,zflip))
    path=OUT/'print'/(name+'.stl')
    cq.exporters.export(s,str(path),tolerance=.02,angularTolerance=.06)
    mesh=validate_mesh(path)
    assert shape.isValid() and len(shape.Solids())==1,(name,shape.isValid(),len(shape.Solids()))
    return {'valid':True,'volume_mm3':shape.Volume(),'solid_ABS_g':shape.Volume()*.001*P['abs_density'],'mesh':mesh}

def run():
    report={'revision':P['revision'],'physical_validation':'PENDING','parts':{}}
    a=anchor();print('anchor built',a.isValid(),len(a.Solids()),flush=True)
    c=collar();print('collar built',c.isValid(),len(c.Solids()),flush=True)
    for name,s,flip in [('anchor',a,P['face_z']),('preload_collar',c,None),('thrust_plate',thrust_plate(),None)]:
        report['parts'][name]=printable(s,name,flip)
    # Fit coupons and complete collars for three radial fit allowances.
    male=a.intersect(box(80,80,4.8,(0,0,P['face_z']-2.4)))
    report['parts']['thread_male_coupon']=printable(male,'thread_male_coupon',P['face_z'])
    for clearance in [.2,.3,.4]:
        code=f"C{round(clearance*100):03d}"
        nut=collar(radial=clearance,height=4.8,split=False)
        name='thread_nut_coupon_'+code
        report['parts'][name]=printable(nut,name,None)
        if clearance!=.3:
            name='preload_collar_'+code
            report['parts'][name]=printable(collar(radial=clearance),name,None)
    # Same 13.0 mm plastic grip and washer/screw stack as the real anchor.
    hw=cq.Workplane('XY').rect(16,16).extrude(19.4).edges('|Z').fillet(2).val()
    hw=hw.cut(cylinder(1.7,-.1,20)).cut(cylinder(4.3,13.0,6.5))
    report['parts']['hardware_coupon']=printable(hw,'hardware_coupon',None)
    # Keep the main part's layer phase: (14.4 - 1.28) / .16 = 82 layers.
    wc=a.intersect(box(80,80,6.28,(0,0,-1.86)))
    wc=wc.fuse(cylinder(26,0,1.28)).cut(cylinder(6,-6,8))
    for x,y in P['hole_centers']:
        wc=wc.cut(cylinder(1.7,-6,8).translate((x,y,0)))
    report['parts']['wrist_fit_coupon']=printable(wc,'wrist_fit_coupon',1.28)
    (OUT/'docs/build_validation.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':run()
