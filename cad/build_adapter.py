#!/usr/bin/env python3
"""Parametric ABS captured flange for the Unitree R1-7A and DEX1-1.

Requires CadQuery 2.7.x. All lengths are mm. Coordinate system:
  wrist front plane Z=0; wrist Z<0; DEX mounting face Z=+8.
  X is the long direction of the wrist opening. DEX is rotated 90 deg:
  the 10 x 30 M3 pattern becomes X=+/-15, Y=+/-5.

Run from anywhere: python cad/build_adapter.py [--validate-reference]
Files in print/ are rotated with the DEX mating face on the build plate.
STEP files retain assembly coordinates. STL has no intrinsic unit metadata.
This is an untested fit prototype, not a qualified structural component.
"""
import argparse
import json
import math
import struct
from collections import Counter
from pathlib import Path

import cadquery as cq
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
P = json.loads((ROOT / "cad/parameters.json").read_text())


def hole_centers():
    theta = math.radians(P["dex_rotation_degrees"])
    c, s = math.cos(theta), math.sin(theta)
    return [
        (round(x*c-y*s, 8), round(x*s+y*c, 8))
        for x in (-P["dex_thread_spacing_x"]/2, P["dex_thread_spacing_x"]/2)
        for y in (-P["dex_thread_spacing_y"]/2, P["dex_thread_spacing_y"]/2)
    ]


def slab(diameter, z0, height, flats=None, chamfer=0):
    w = cq.Workplane("XY").workplane(offset=z0).circle(diameter/2).extrude(height)
    if flats is not None:
        clip = (cq.Workplane("XY").workplane(offset=z0-1)
                .rect(diameter+4, flats).extrude(height+2))
        w = w.intersect(clip)
    if chamfer:
        # Horizontal perimeter edges, including the two antirotation flats.
        w = w.faces(">Z or <Z").edges().chamfer(chamfer)
    return w


def build(profile="B", coupon=False):
    f = P["profiles"][profile]
    face_t = P["coupon_face_thickness"] if coupon else P["face_thickness"]
    depth = P["insert_depth"]
    neck = slab(f["neck_diameter"], -depth, depth, f["across_flats"])
    # The real opening has four R4 transitions between its cylindrical sides
    # and planar flats. A circle merely clipped by a rectangle interferes here.
    neck = neck.edges("|Z").fillet(P["neck_corner_fillet"])
    # Lead-in at the back; do not reduce the locating land at Z=0.
    neck = neck.faces("<Z").edges().chamfer(P["rear_edge_chamfer"])
    lip_t = f["retaining_thickness"]
    # The groove only opens across a 20 mm wide window, not the full 28 mm
    # flat-to-flat opening. Use two captured ears in that window.
    window = (P["reference_wrist"]["groove_window_width"]
              - (P["reference_wrist"]["across_flats"]-f["across_flats"]))
    lip = slab(f["retaining_diameter"], P["retaining_center_z"]-lip_t/2,
               lip_t, window, P["retaining_edge_chamfer"])
    face = slab(P["face_diameter"], 0, face_t,
                chamfer=min(P["face_edge_chamfer"], face_t/4))
    w = neck.union(lip).union(face)
    holes = hole_centers()
    # Check screw head pockets remain within the rear locating section.
    for x,y in holes:
        assert abs(y)+P["head_pocket_diameter"]/2 < f["across_flats"]/2
        assert math.hypot(x,y)+P["head_pocket_diameter"]/2 < f["neck_diameter"]/2
    cut = (cq.Workplane("XY").workplane(offset=-depth-1)
           .circle(P["center_hole_diameter"]/2).extrude(depth+face_t+2))
    w = w.cut(cut)
    through = (cq.Workplane("XY").workplane(offset=-depth-1).pushPoints(holes)
               .circle(P["bolt_clearance_diameter"]/2).extrude(depth+face_t+2))
    pockets = (cq.Workplane("XY").workplane(offset=-depth-.01).pushPoints(holes)
               .circle(P["head_pocket_diameter"]/2).extrude(P["head_pocket_depth"]+.01))
    w = w.cut(through).cut(pockets).clean()
    if coupon:
        # Identification is recessed, so the mating planes stay flat.
        marking = (cq.Workplane("XY").workplane(offset=face_t-.3)
                   .center(0,23).text(profile, 2.8, .5, font="Liberation Sans",
                                     kind="bold", combine=False))
        w = w.cut(marking).clean()
    shape = w.val()
    assert shape.isValid() and len(shape.Solids()) == 1
    return shape, face_t


def print_orientation(shape, face_t):
    return shape.rotate((0,0,0), (1,0,0), 180).translate((0,0,face_t))


def validate_mesh(path):
    raw = path.read_bytes()
    n, = struct.unpack_from("<I", raw, 80)
    assert len(raw) == 84+50*n, "STL is not expected binary format"
    dtype=np.dtype([("normal", "<f4", 3), ("vertices", "<f4", (3,3)), ("attr", "<u2")])
    v = np.frombuffer(raw, dtype=dtype, count=n, offset=84)["vertices"].astype(float)
    # Weld STL's per-triangle vertices at one micrometre.
    verts, inverse = np.unique(np.round(v.reshape(-1,3), 5), axis=0, return_inverse=True)
    faces = inverse.reshape(-1,3)
    directed=Counter()
    edges=Counter()
    for a,b,c in faces:
        for i,j in [(a,b),(b,c),(c,a)]:
            edges[tuple(sorted((int(i),int(j))))] += 1
            directed[(int(i),int(j))] += 1
    assert all(c==2 for c in edges.values()), "Non-manifold or open STL"
    assert all(directed[(j,i)]==c for (i,j),c in directed.items()), "Inconsistent winding"
    signed_volume = np.einsum("ij,ij->i", v[:,0], np.cross(v[:,1],v[:,2])).sum()/6
    assert signed_volume > 0
    assert np.min(v[:,:,2]) > -1e-4
    return {"triangles": n, "watertight": True, "consistent_winding": True,
            "signed_volume_mm3": float(signed_volume),
            "bounds_mm": [verts.min(0).tolist(), verts.max(0).tolist()]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--validate-reference", action="store_true")
    args=parser.parse_args()
    for d in ("print", "cad", "docs"):
        (ROOT/d).mkdir(exist_ok=True)
    wrist = None
    ref=ROOT/"references/r1_wrist_normalized.step"
    if args.validate_reference:
        if not ref.exists(): raise FileNotFoundError(ref)
        wrist = cq.importers.importStep(str(ref)).val()
    profile=P["fit_profile"]
    main_shape,face_t=build(profile)
    report={"revision": P["revision"], "units": "mm", "profile":profile,
            "status":"FIT_PROTOTYPE_UNTESTED", "cadquery_version":cq.__version__,
            "dex_holes_xy_mm": hole_centers(), "parts":{}, "reference_checks":{}}
    layer_offset=(P["face_thickness"]-P["coupon_face_thickness"])/P["print_reference_layer_height"]
    assert abs(layer_offset-round(layer_offset))<1e-6, "Set coupon face thickness to preserve the main part's layer phase at the reference layer height."
    report["coupon_layer_alignment"]={"reference_layer_height_mm":P["print_reference_layer_height"],
        "coupon_face_mm":P["coupon_face_thickness"],"main_to_coupon_layer_offset":round(layer_offset),
        "same_reference_first_layer_required":True}
    for name,shape,ft in [("adapter_"+profile,main_shape,face_t)] + [
            ("fit_coupon_"+f,*build(f,True)) for f in P["profiles"]]:
        cq.exporters.export(shape, str(ROOT/"cad"/(name+".step")))
        printshape=print_orientation(shape,ft)
        target=ROOT/"print"/(name+".stl")
        cq.exporters.export(printshape, str(target), tolerance=.025, angularTolerance=.08)
        record={"solid_valid":shape.isValid(),"solid_count":len(shape.Solids()),
                "volume_mm3":shape.Volume(),
                "solid_ABS_mass_g":shape.Volume()/1000*P["abs_density_g_cm3"],
                "mesh":validate_mesh(target)}
        report["parts"][name]=record
        if wrist is not None:
            common=shape.intersect(wrist)
            interference=common.Volume() if common.Solids() else 0.
            report["reference_checks"][name]={"wrist_interference_mm3":interference}
            assert abs(interference)<.01, (name,interference)
        print(name, "valid", round(record["volume_mm3"],1), "mm3", flush=True)
    # Explicit bolt stack calculation for a 0.5 mm plain washer under the head.
    seat_z=-P["insert_depth"]+P["head_pocket_depth"]
    grip=P["face_thickness"]-seat_z+P["washer_thickness"]
    engagement=P["screw_nominal_length"]-grip
    assert 4 <= engagement <= P["dex_thread_depth_drawing"]-1
    report["bolt_stack"]={"counterbore_seat_z_mm":seat_z,
        "plastic_grip_mm":P["face_thickness"]-seat_z,"washer_mm":P["washer_thickness"],
        "screw_length_mm":P["screw_nominal_length"],"predicted_engagement_mm":engagement,
        "nominal_remaining_thread_depth_mm":P["dex_thread_depth_drawing"]-engagement,
        "note":"Confirm actual usable thread and screw tip clearance; drawing depth is not guaranteed effective engagement."}
    (ROOT/"docs/validation.json").write_text(json.dumps(report,indent=2,ensure_ascii=False))
    # Portable native STEP assembly for visual fit checking. Reference wrist is not printable.
    if wrist is not None:
        a=cq.Assembly(name="R1_7A_DEX1_1_fit_check")
        a.add(wrist,name="official_R1_wrist_REFERENCE_ONLY",color=cq.Color(.64,.69,.73,.45))
        a.add(main_shape,name="ABS_adapter_profile_"+profile,color=cq.Color(.12,.53,.64))
        a.export(str(ROOT/"cad/assembly_fit_check.step"))
        # Sectioned wrist makes the captured lip visible without transparent rendering.
        cutbox=cq.Workplane("XY").box(200,100,200).translate((0,-50,0)).val()
        section=wrist.intersect(cutbox)
        b=cq.Assembly(name="Sectioned_fit_check")
        b.add(section,name="official_wrist_section_REFERENCE_ONLY",color=cq.Color(.64,.69,.73))
        b.add(main_shape,name="ABS_adapter_profile_"+profile,color=cq.Color(.12,.53,.64))
        b.export(str(ROOT/"cad/assembly_section.step"))
    print("Saved outputs and validation.json",flush=True)


if __name__=="__main__":
    main()
