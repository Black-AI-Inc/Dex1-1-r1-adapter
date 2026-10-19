#!/usr/bin/env python3
"""Independent assembly/access checks, not physical load qualification.

Uses exact ABS and official wrist solids. Gripper threads are a drawing-based
interface proxy: the visual mesh is NOT taken as threaded-hole metrology.
All distances mm. The moving joint and electrical harness are not simulated.
"""
import json
import math
from pathlib import Path

import cadquery as cq
import numpy as np

from build_adapter import ROOT, P, build, hole_centers, validate_mesh


def cyl(d,z,h,x=0,y=0):
    return cq.Solid.makeCylinder(d/2,h,cq.Vector(x,y,z))


def overlap(a,b):
    c=a.intersect(b)
    return float(c.Volume()) if c.Solids() else 0.0


def fastener(kind="socket",x=0,y=0):
    seat=-P["insert_depth"]+P["head_pocket_depth"]
    washer=cyl(P["washer_outer_diameter"],seat-P["washer_thickness"],P["washer_thickness"],x,y).cut(
        cyl(P["washer_inner_diameter"],seat-P["washer_thickness"]-.1,P["washer_thickness"]+.2,x,y))
    bearing=seat-P["washer_thickness"]
    ht=3.0 if kind=="socket" else 2.0
    head=cyl(5.5,bearing-ht,ht,x,y)
    if kind=="socket":
        # 2.5 mm across flats. Socket depth from the selected Japanese listing.
        socket=(cq.Workplane("XY").workplane(offset=bearing-ht-.01)
                .center(x,y).polygon(6,2.5/math.cos(math.pi/6)).extrude(1.31).val())
        head=head.cut(socket)
    # Pan head is conservatively represented by its bounding cylinder.
    screw=head.fuse(cyl(3,bearing,P["screw_nominal_length"],x,y))
    return screw,washer,bearing-ht


def export_hardware():
    adapter,_=build(P["fit_profile"])
    wrist=cq.importers.importBrep(str(ROOT/"references/r1_wrist_normalized.brep")).val()
    # Only a mounting-face proxy, NOT a purported complete DEX solid model.
    dexproxy=cyl(49,P["face_thickness"],10)
    for x,y in hole_centers():
        dexproxy=dexproxy.cut(cyl(3.05,P["face_thickness"]-.01,8.01,x,y))
    asm=cq.Assembly(name="Hardware_access_review_v02")
    asm.add(adapter,name="ABS_adapter",color=cq.Color(.12,.53,.64))
    asm.add(wrist,name="OFFICIAL_wrist_reference",color=cq.Color(.68,.71,.75))
    asm.add(dexproxy,name="DRAWING_ONLY_Dex_mount_proxy_NOT_full_gripper",color=cq.Color(.25,.27,.29,.35))
    components={"adapter":adapter,"wrist":wrist,"dexproxy":dexproxy}
    for i,(x,y) in enumerate(hole_centers()):
        bolt,washer,_=fastener("socket",x,y)
        asm.add(bolt,name=f"M3x16_socket_{i+1}",color=cq.Color(.68,.53,.26))
        asm.add(washer,name=f"M3_washer_OD8_T05_{i+1}",color=cq.Color(.75,.78,.8))
        components[f"bolt_{i+1}"]=bolt;components[f"washer_{i+1}"]=washer
    asm.export(str(ROOT/"cad/assembly_with_hardware.step"))
    for name,s in components.items():
        cq.exporters.export(s,str(ROOT/"references"/("review_"+name+".stl")),tolerance=.08,angularTolerance=.15)
    return adapter,wrist,dexproxy


def make_stack_coupon():
    # Matches actual main-part plastic grip and counterbore; one screw suffices.
    h=P["face_thickness"]+P["insert_depth"]
    s=cq.Workplane("XY").rect(16,16).extrude(h).edges("|Z").fillet(2).val()
    s=s.cut(cyl(P["bolt_clearance_diameter"],-.1,h+.2))
    s=s.cut(cyl(P["head_pocket_diameter"],h-P["head_pocket_depth"],P["head_pocket_depth"]+.1))
    cq.exporters.export(s,str(ROOT/"cad/fastener_stack_coupon.step"))
    out=ROOT/"print/fastener_stack_coupon.stl"
    cq.exporters.export(s,str(out),tolerance=.025,angularTolerance=.08)
    return {"mass_g":s.Volume()/1000*P["abs_density_g_cm3"],"mesh":validate_mesh(out),
            "purpose":"Single screw/washer/driver and M3x16 tip-projection check; never operate arm with this coupon."}


def first_contact(adapter,wrist,mode):
    def collision(t):
        moved=adapter.translate((0,0,t)) if mode=="axial" else adapter.rotate((0,0,0),(0,0,1),t)
        return overlap(moved,wrist)>.001
    lo=0.;hi=.4 if mode=="axial" else 2.
    assert collision(hi)
    for _ in range(12):
        mid=(lo+hi)/2
        if collision(mid):hi=mid
        else:lo=mid
    return {"last_noninterfering":lo,"first_interfering":hi,
            "units":"mm" if mode=="axial" else "degrees",
            "overlap_threshold_mm3":.001}


def run():
    adapter,wrist,dexproxy=export_hardware()
    checks=[]
    def check(name,value,limit=.01,scope="exact CAD"):
        passed=value<=limit
        checks.append({"test":name,"value_mm3":value,"limit_mm3":limit,"passed":passed,"scope":scope})
        assert passed,(name,value)
    seat=-P["insert_depth"]+P["head_pocket_depth"]
    for kind in ["socket","pan"]:
        fasteners=[]
        for i,(x,y) in enumerate(hole_centers()):
            screw,washer,headback=fastener(kind,x,y)
            fasteners.extend([screw,washer])
            check(f"{kind}_{i+1}_screw_vs_ABS",overlap(screw,adapter))
            check(f"{kind}_{i+1}_washer_vs_ABS",overlap(washer,adapter))
            check(f"{kind}_{i+1}_screw_vs_wrist",overlap(screw,wrist))
            check(f"{kind}_{i+1}_washer_vs_wrist",overlap(washer,wrist))
            check(f"{kind}_{i+1}_screw_tip_vs_proxy_bottom",overlap(screw,dexproxy),scope="nominal drawing proxy, excludes threads")
            sweep=cyl(8,-45,45+seat,x,y).fuse(cyl(3,-45,45+seat-.5+16,x,y))
            check(f"{kind}_{i+1}_screw_and_washer_axial_insertion",overlap(sweep,adapter))
            # Full diameter envelopes include manufacturing/tool tip allowance.
            shaft=cyl(3.0 if kind=="socket" else 6.0,-65,65+headback,x,y)
            handle=cyl(24,-100,35,x,y)
            check(f"{kind}_{i+1}_bench_driver_vs_ABS",overlap(shaft.fuse(handle),adapter))
            for j,(ox,oy) in enumerate(hole_centers()):
                if i!=j:
                    ob,ow,_=fastener(kind,ox,oy)
                    check(f"{kind}_{i+1}_driver_vs_adjacent_{j+1}",overlap(shaft,ob.fuse(ow)))
        for i in range(len(fasteners)):
            for j in range(i):
                check(f"{kind}_hardware_pair_{j}_{i}",overlap(fasteners[i],fasteners[j]))
    # A translation check for the reference shell halves relative to the insert.
    # This does NOT validate opening the actual joint, which includes omitted parts.
    for side,s in enumerate(wrist.Solids()):
        sign=-1 if s.Center().x<0 else 1
        for d in [0,.25,.5,1,2,4,8,16,35]:
            check(f"shell_{side}_radial_placement_{d}",overlap(s.translate((sign*d,0,0)),adapter))
    # A closed wrist cannot accept the ears by simply pushing from the front.
    forward_interference=overlap(adapter.translate((0,0,1.0)),wrist)
    assert forward_interference>1
    tool_closed=[]
    if (ROOT/"references/r1_arm_normalized.brep").exists():
        arm=cq.importers.importBrep(str(ROOT/"references/r1_arm_normalized.brep")).val()
        # Check each solid separately; the manufacturer's simplified assembly
        # contains pre-existing overlaps, which must not be attributed to us.
        for j,s in enumerate(arm.Solids()):check(f"adapter_vs_official_arm_solid_{j}",overlap(adapter,s))
        for i,(x,y) in enumerate(hole_centers()):
            shaft=cyl(3,-80,75.3,x,y)
            values=[overlap(shaft,s) for s in arm.Solids()]
            tool_closed.append({"hole":i+1,"collision_sum_mm3":sum(values),"interfering_solid_indices":[j for j,v in enumerate(values) if v>.01],"serviceable_with_straight_driver":sum(values)<.01})
    # Explicitly quantify free travel without assuming shell deformation/friction.
    backlash={"axial_forward":first_contact(adapter,wrist,"axial"),
              "rotation_about_mount_axis":first_contact(adapter,wrist,"rotation"),
              "interpretation":"Ideal rigid nominal geometry only. No clamp friction, coating, print error or elastic deformation. A fit test must establish negligible actual lost motion; do not increase wrist torque to compensate."}
    od=P["washer_outer_diameter"];hole=P["bolt_clearance_diameter"]
    area=math.pi/4*(od*od-hole*hole)
    pressure=[]
    for torque in [.1,.2,.5,1.0]:
        loads=[torque/(k*.003) for k in [.3,.15]]
        pressure.append({"example_torque_Nm":torque,"preload_estimate_N":loads,"average_ABS_pressure_MPa":[v/area for v in loads]})
    report={"revision":P["revision"],"status":"DIGITAL_ASSEMBLY_REVIEW_PHYSICAL_ACCEPTANCE_PENDING",
            "passed_interference_checks":len(checks),"checks":checks,
            "closed_wrist_forward_push_interference_mm3":forward_interference,
            "driver_access_after_arm_assembly":tool_closed,"nominal_free_travel":backlash,
            "fastener_stack_coupon":make_stack_coupon(),
            "hardware_dimensions":{"socket_head_diameter":5.5,"socket_head_height":3,"hex_key_AF":2.5,"pan_head_envelope_height":2,"pan_driver_shaft_diameter_max":6,"washer_OD":od,"washer_thickness":.5,"pocket_OD":P["head_pocket_diameter"],"minimum_between_pocket_web":10-P["head_pocket_diameter"]},
            "clamp_pressure_sensitivity":{"washer_bearing_area_mm2":area,"friction_factor_assumption_K":[.15,.3],"examples":pressure,"warning":"Illustrative sensitivity only, NOT validated tightening torques or allowable ABS stresses. Washer bending and print anisotropy omitted."},
            "not_tested":["physical printing and fit","real joint disassembly and reassembly","actual screw bottoming and thread engagement","cable and connector clearance","backlash after tightening","load, fatigue, heat and creep","whole robot motion and TCP"]}
    (ROOT/"docs/assembly_validation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps({k:report[k] for k in ["passed_interference_checks","driver_access_after_arm_assembly","nominal_free_travel","hardware_dimensions"]},indent=2),flush=True)


if __name__=="__main__":run()
