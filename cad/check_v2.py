#!/usr/bin/env python3
"""Independent CAD + Manifold mesh assembly checks. No physical load rating."""
import json,math,hashlib
import numpy as np
import cadquery as cq
import manifold3d as mf
import trimesh
from build_v2 import OUT,REF,P,cylinder,box

def overlap(a,b):
    c=a.intersect(b)
    if not c.Solids():return 0.
    if not c.isValid():raise RuntimeError('Invalid OCCT intersection; do not count it as a pass')
    return max(0.,c.Volume())
def load(name):return cq.importers.importStep(str(OUT/'cad'/(name+'.step'))).val()
def mesh_from_stl(path,anchor=False):
    t=trimesh.load(path,force='mesh',process=True)
    if anchor:t.vertices[:,1]*=-1;t.vertices[:,2]=P['face_z']-t.vertices[:,2]
    m=mf.Manifold(mf.Mesh(np.array(t.vertices,dtype=np.float32),np.array(t.faces,dtype=np.uint32)))
    assert m.status()==mf.Error.NoError,(path,m.status())
    return m

def screw_z(x,y):
    seat=-P['neck_depth']+P['bolt_pocket_depth'];bearing=seat-P['washer_thickness']
    wash=cylinder(P['washer_od']/2,seat-P['washer_thickness'],P['washer_thickness']).cut(cylinder(P['washer_id']/2,seat-P['washer_thickness']-.1,P['washer_thickness']+.2))
    head=cylinder(2.75,bearing-3,3)
    socket=cq.Workplane('XY').workplane(offset=bearing-3-.01).polygon(6,2.5/math.cos(math.pi/6)).extrude(1.31).val()
    screw=head.cut(socket).fuse(cylinder(1.5,bearing,P['dex_screw_length']))
    return screw.translate((x,y,0)),wash.translate((x,y,0)),bearing-3

def pinch_hardware():
    y=P['pinch_axis_y'];z=P['pinch_axis_z'];d=cq.Vector(1,0,0)
    def cyl(r,x,h):return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z),d)
    screw=cyl(2.75,-12.5,3).fuse(cyl(1.5,-9.5,20))
    socket=cq.Workplane('YZ').workplane(offset=-12.51).center(y,z).polygon(6,2.5/math.cos(math.pi/6)).extrude(1.31).val()
    screw=screw.cut(socket)
    washer=cyl(4,-9.5,.5).cut(cyl(1.6,-9.6,.7))
    nut=cq.Workplane('YZ').workplane(offset=5.5).center(y,z).polygon(6,5.5/math.cos(math.pi/6)).extrude(2.4).val().cut(cyl(1.55,5.4,2.6))
    return screw,washer,nut

def main():
    (OUT/'cad/preview').mkdir(exist_ok=True)
    checks=[]
    def check(name,val,limit=.01,units='mm3',method='OCCT solid intersection'):
        row={'test':name,'value':float(val),'limit':limit,'units':units,'method':method,'passed':val<=limit}
        checks.append(row)
        assert row['passed'],row
    a=load('anchor');c=load('preload_collar');t=load('thrust_plate')
    dz=P['nominal_anchor_pullup'];cz=P['thrust_plate_thickness'];ang=P['assembly_collar_angle']
    aa=a.translate((0,0,dz));cc=c.rotate((0,0,0),(0,0,1),ang).translate((0,0,cz))
    wrist=cq.importers.importBrep(str(REF/'r1_wrist_normalized.brep')).val()
    build=json.loads((OUT/'docs/build_validation.json').read_text())
    for name,row in build['parts'].items():
        solid=load(name);err=abs(solid.Volume()-row['mesh']['signed_volume_mm3'])/solid.Volume()
        check(name+'_STEP_STL_volume_agreement',err,.003,'fraction','independent volume calculation')
        check(name+'_STEP_roundtrip',abs(solid.Volume()-row['volume_mm3']),.01,'mm3','STEP reimport')
    for name,shape in [('anchor',aa),('collar',cc),('thrust_plate',t)]:check(name+'_wrist',overlap(shape,wrist))
    check('anchor_thrust_plate',overlap(aa,t));check('collar_thrust_plate',overlap(cc,t))
    # Short segments in the female thread are verified against the actual exported
    # meshes, independently of the CAD kernel's periodic-surface booleans.
    am=mesh_from_stl(OUT/'print/anchor.stl',True)
    cm=mesh_from_stl(OUT/'print/preload_collar.stl')
    for z in np.linspace(0,18,19):
        moving=cm.rotate((0,0,360*(z+cz)/P['thread_pitch'])).translate((0,0,z+cz))
        check(f'collar_screw_on_{z:.1f}',(am^moving).volume(),.05,method='Manifold intersection of exported STL')
    thread=[]
    for angle in [139,140,141,142,145,160,180,200,205,210]:
        volume=(am.translate((0,0,dz))^cm.rotate((0,0,angle)).translate((0,0,cz))).volume()
        thread.append({'angle_deg':angle,'mesh_overlap_mm3':volume})
    near=(am.translate((0,0,dz))^cm.rotate((0,0,ang)).translate((0,0,cz))).volume()
    check('thread_near_seated_pose',near,.05,method='Manifold intersection of exported STL')
    assert thread[0]['mesh_overlap_mm3']>1,'No thread load flank detected'
    # Washer can go over the rear ears before mounting the arm shells.
    for z in [-12,-8,-5,-3,-1,0]:check(f'thrust_plate_rear_insertion_{z}',overlap(a,t.translate((0,0,z))))
    # Shells approach radially. Include thrust plate and collar in the check.
    for side,s in enumerate(wrist.Solids()):
        sign=-1 if s.Center().x<0 else 1
        for x in [0,.25,1,3,8,20,35]:
            shell=s.translate((sign*x,0,0))
            for name,shape in [('anchor',aa),('collar',cc),('plate',t)]:check(f'shell_{side}_{x}_{name}',overlap(shell,shape))
    hardware=[];bench=[]
    for i,(x,y) in enumerate(P['hole_centers']):
        bolt,washer,back=screw_z(x,y)
        for name,s in [('screw',bolt),('washer',washer)]:
            check(f'DEX_{i}_{name}_anchor',overlap(s,a))
            check(f'DEX_{i}_{name}_plate',overlap(s,t))
            check(f'DEX_{i}_{name}_collar',overlap(s,cc))
            hardware.append((f'DEX_{i}_{name}',s.translate((0,0,dz))))
        driver=cylinder(1.5,-65,65+back).translate((x,y,0)).fuse(cylinder(12,-105,40).translate((x,y,0)))
        check(f'DEX_{i}_bench_driver_anchor',overlap(driver,a))
        check(f'DEX_{i}_bench_driver_collar',overlap(driver,cc))
        check(f'DEX_{i}_bench_driver_plate',overlap(driver,t))
        bench.append(driver)
    pinch=pinch_hardware()
    for name,s in zip(['pinch_screw','pinch_washer','M3_nut'],pinch):
        check(name+'_collar',overlap(s,c))
        transformed=s.rotate((0,0,0),(0,0,1),ang).translate((0,0,cz))
        hardware.append((name,transformed))
        check(name+'_anchor',overlap(transformed,aa));check(name+'_plate',overlap(transformed,t));check(name+'_wrist',overlap(transformed,wrist))
    # Standard nut and screw have modeled clearance in lieu of helical M3 threads.
    for i,(ni,si) in enumerate(hardware):
        for nj,sj in hardware[:i]:check(ni+'_vs_'+nj,overlap(si,sj))
    y=P['pinch_axis_y'];z=P['pinch_axis_z']
    shaft=cq.Solid.makeCylinder(1.5,58,cq.Vector(-70,y,z),cq.Vector(1,0,0))
    handle=cq.Solid.makeCylinder(12,35,cq.Vector(-105,y,z),cq.Vector(1,0,0))
    driver=shaft.fuse(handle).rotate((0,0,0),(0,0,1),ang).translate((0,0,cz))
    for name,s in [('collar',cc),('anchor',aa),('plate',t),('wrist',wrist)]:check('pinch_driver_'+name,overlap(driver,s))
    arm=cq.importers.importBrep(str(REF/'r1_arm_normalized.brep')).val()
    for j,s in enumerate(arm.Solids()):
        for name,obj in [('anchor',aa),('collar',cc),('plate',t),('pinch_driver',driver)]:check(f'{name}_arm_solid_{j}',overlap(obj,s))
    area_w=overlap(t.translate((0,0,-.005)),wrist)/.005
    area_c=overlap(cc.translate((0,0,-.005)),t)/.005
    area_e=overlap(a.translate((0,0,dz+.005)),wrist)/.005
    assert min(area_w,area_e)>100 and area_c>400
    # Positive retention: a forward displacement must hit the groove shoulders.
    retention=overlap(a.translate((0,0,dz+.05)),wrist);assert retention>1
    seat=-5+P['bolt_pocket_depth'];engagement=P['dex_screw_length']-(P['face_z']-seat+P['washer_thickness'])
    assert 4<=engagement<=7
    rows={'revision':P['revision'],'passed_checks':len(checks),'checks':checks,
          'thread_flank_scan':thread,'assembly_illustration':{'anchor_z':dz,'collar_z':cz,'collar_angle_deg':ang,'analytical_thread_contact_angle_deg':141,'illustration_thread_axial_gap_mm':1/360*P['thread_pitch'],'note':'Illustration uses 1 degree / 0.0133 mm numerical clearance. On hardware, turn to contact; actual phase depends on print error.'},
          'thread_effective_axial_overlap_mm':cz+P['collar_height']-(P['shoulder_z']+dz),
          'thread_nominal_engaged_pitches':(cz+P['collar_height']-(P['shoulder_z']+dz))/P['thread_pitch'],
          'bearing_areas_approx_mm2':{'plate_wrist':area_w,'collar_plate':area_c,'ears_wrist':area_e},
          'bolt_stack':{'M3_length':20,'plastic_grip':P['face_z']-seat,'washer':.5,'nominal_insertion':engagement,'drawing_depth_remaining':8-engagement,'head_recess':5+(seat-.5-3)},
          'retention_forward_005mm_overlap_mm3':retention,
          'stl_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (OUT/'print').glob('*.stl')},
          'physical_status':'NOT TESTED. No payload, torque, fatigue, ABS creep or printer accuracy rating.',
          'antirotation':'Axial preload supplies frictional torsional holding; keyed neck is a backup stop. No absolute zero elastic deflection or unlimited torque claim.'}
    (OUT/'docs/assembly_validation.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
    asm=cq.Assembly(name='V2_near_seated_reference_assembly')
    parts=[('anchor',aa,(.16,.55,.60)),('preload_collar',cc,(.78,.55,.17)),('thrust_plate',t,(.33,.40,.47)),('official_wrist_REFERENCE',wrist,(.67,.71,.75))]
    for name,s,col in parts:asm.add(s,name=name,color=cq.Color(*col))
    for name,s in hardware:asm.add(s,name=name,color=cq.Color(.7,.71,.73))
    asm.export(str(OUT/'cad/assembly_reference.step'))
    for name,s,_ in parts:
        cq.exporters.export(s,str(OUT/'cad/preview'/(name+'_assembled.stl')),tolerance=.03,angularTolerance=.08)
    for name,s in hardware:cq.exporters.export(s,str(OUT/'cad/preview'/(name+'.stl')),tolerance=.03,angularTolerance=.1)
    print(json.dumps({k:rows[k] for k in ['passed_checks','bearing_areas_approx_mm2','bolt_stack','thread_flank_scan']},indent=2),flush=True)
if __name__=='__main__':main()
