import struct,zipfile
import numpy as np
from xml.etree.ElementTree import Element,SubElement,tostring
from build_v2 import OUT

NS="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def read_stl(path):
    raw=path.read_bytes();n,=struct.unpack_from("<I",raw,80)
    d=np.dtype([("n","<f4",3),("v","<f4",(3,3)),("a","<u2")])
    v=np.frombuffer(raw,dtype=d,count=n,offset=84)["v"]
    vertices,inv=np.unique(np.round(v.reshape(-1,3).astype(float),6),axis=0,return_inverse=True)
    return vertices,inv.reshape(-1,3)


def write_3mf(path, parts):
    model=Element("model",{"unit":"millimeter","xml:lang":"en-US","xmlns":NS})
    SubElement(model,"metadata",{"name":"Title"}).text="Unitree ABS preload adapter V2"
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


if __name__=="__main__":
    for p in (OUT/"print").glob("*.stl"):
        write_3mf(p.with_suffix(".3mf"),[(p.stem,p,(0,0,0))])
