#!/usr/bin/env python3
"""Create a dimensional coupon and generic millimetre 3MF geometry files.

These are geometry-only 3MF files, without printer or filament settings.
"""
import json
import struct
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring

import cadquery as cq
import numpy as np

from build_adapter import ROOT, P, validate_mesh

NS="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def read_stl(path):
    raw=path.read_bytes();n,=struct.unpack_from("<I",raw,80)
    d=np.dtype([("n","<f4",3),("v","<f4",(3,3)),("a","<u2")])
    v=np.frombuffer(raw,dtype=d,count=n,offset=84)["v"]
    vertices,inv=np.unique(np.round(v.reshape(-1,3).astype(float),6),axis=0,return_inverse=True)
    return vertices,inv.reshape(-1,3)


def write_3mf(path, parts):
    model=Element("model",{"unit":"millimeter","xml:lang":"en-US","xmlns":NS})
    SubElement(model,"metadata",{"name":"Title"}).text="Unitree ABS fit prototype v0.2"
    SubElement(model,"metadata",{"name":"Description"}).text=(
        "Geometry only. Configure ABS and printer separately. Fit and load validation required.")
    resources=SubElement(model,"resources");build=SubElement(model,"build")
    for i,(name,stl,shift) in enumerate(parts,1):
        vertices,faces=read_stl(stl)
        o=SubElement(resources,"object",{"id":str(i),"type":"model","name":name})
        mesh=SubElement(o,"mesh");vs=SubElement(mesh,"vertices");ts=SubElement(mesh,"triangles")
        for x,y,z in vertices:
            SubElement(vs,"vertex",{"x":f"{x:.6f}","y":f"{y:.6f}","z":f"{z:.6f}"})
        for a,b,c in faces:
            SubElement(ts,"triangle",{"v1":str(a),"v2":str(b),"v3":str(c)})
        SubElement(build,"item",{"objectid":str(i),
                   "transform":f"1 0 0 0 1 0 0 0 1 {shift[0]} {shift[1]} {shift[2]}"})
    types=('<?xml version="1.0" encoding="UTF-8"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
      '</Types>')
    rels=('<?xml version="1.0" encoding="UTF-8"?>'
      '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
      '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
      'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
      '</Relationships>')
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",types)
        z.writestr("_rels/.rels",rels)
        z.writestr("3D/3dmodel.model",tostring(model,encoding="utf-8",xml_declaration=True))


def main():
    bar=cq.Workplane("XY").rect(50,12).extrude(3)
    for x,d in zip([-18,-6,6,18],[3.2,3.4,3.6,3.8]):
        h=cq.Workplane("XY").workplane(offset=-1).center(x,1.5).circle(d/2).extrude(5)
        bar=bar.cut(h)
        txt=(cq.Workplane("XY").workplane(offset=2.7).center(x,-3.4)
             .text(str(d),2.1,.5,font="Liberation Sans",combine=False))
        bar=bar.cut(txt)
    bar=bar.clean();assert bar.val().isValid()
    stl=ROOT/"print/ABS_50mm_calibration.stl"
    cq.exporters.export(bar,str(stl),tolerance=.025,angularTolerance=.08)
    validation=validate_mesh(stl)
    (ROOT/"docs/calibration_mesh_validation.json").write_text(json.dumps(validation,indent=2))
    b=P["fit_profile"]
    main_name="adapter_"+b+"_mm.3mf"
    write_3mf(ROOT/"print"/main_name,[("ABS_adapter_profile_"+b,ROOT/"print"/("adapter_"+b+".stl"),(0,0,0))])
    write_3mf(ROOT/"print/fit_coupons_ABC_mm.3mf",[
        ("FIT_ONLY_"+f,ROOT/"print"/("fit_coupon_"+f+".stl"),(x,0,0))
        for f,x in zip(["A","B","C"],[-58,0,58])])
    if (ROOT/"print/fastener_stack_coupon.stl").exists():
        write_3mf(ROOT/"print/fastener_stack_coupon_mm.3mf",[
            ("FASTENER_TEST_ONLY",ROOT/"print/fastener_stack_coupon.stl",(0,0,0))])
    # Re-read package structure and unit metadata; do not imply slicer verification.
    for name in [main_name,"fit_coupons_ABC_mm.3mf"]:
        from xml.etree.ElementTree import fromstring
        with zipfile.ZipFile(ROOT/"print"/name) as z:
            assert z.testzip() is None
            root=fromstring(z.read("3D/3dmodel.model"))
            assert root.attrib["unit"]=="millimeter"
    print("Calibration STL and generic millimetre 3MF packages saved.")


if __name__=="__main__":main()
