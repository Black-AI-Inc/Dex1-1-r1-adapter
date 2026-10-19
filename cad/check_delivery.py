#!/usr/bin/env python3
"""Check that exported design, slicer evidence and user-facing files agree."""
import csv
import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as E
import cadquery as cq
import ezdxf
from pypdf import PdfReader
from build_adapter import P,ROOT,hole_centers

def run():
    s=cq.importers.importStep(str(ROOT/'cad/adapter_B.step')).val()
    v=json.loads((ROOT/'docs/validation.json').read_text())
    assert s.isValid() and len(s.Solids())==1
    error=abs(s.Volume()-v['parts']['adapter_B']['volume_mm3']);assert error<.01
    slicer=json.loads((ROOT/'docs/slicer_validation.json').read_text())
    for n,record in slicer['parts'].items():
        assert hashlib.sha256((ROOT/'print'/(n+'.stl')).read_bytes()).hexdigest()==record['STL_SHA256'],n
    for path in (ROOT/'print').glob('*.3mf'):
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            m=E.fromstring(z.read('3D/3dmodel.model'));assert m.get('unit')=='millimeter'
            ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
            objects=m.findall('.//m:object',ns);assert objects
            for ob in objects:
                vs=ob.findall('.//m:vertex',ns);ts=ob.findall('.//m:triangle',ns);assert vs and ts
                assert all(max(int(t.get(k)) for k in ['v1','v2','v3'])<len(vs) for t in ts)
    d=ezdxf.readfile(ROOT/'docs/DEX_mount_hole_pattern_mm.dxf');assert d.units==4
    xy=sorted((round(c.dxf.center.x,5),round(c.dxf.center.y,5)) for c in d.modelspace().query('CIRCLE') if abs(c.dxf.radius-1.7)<1e-5)
    assert xy==sorted(hole_centers())
    for file in ['日本采购清单.csv','physical_acceptance.csv']:
        with (ROOT/'docs'/file).open(encoding='utf-8-sig') as f:rows=list(csv.reader(f))
        assert len(set(len(r) for r in rows))==1,file
    pages={}
    for path in (ROOT/'docs').glob('*.pdf'):
        reader=PdfReader(path);counts=[len(x.extract_text()) for x in reader.pages]
        assert min(counts)>150
        pages[path.name]={'pages':len(counts),'text_characters':counts}
    assert (ROOT/'docs/assembly_interactive.html').stat().st_size>1_000_000
    report={'revision':P['revision'],'STEP_roundtrip_volume_error_mm3':error,
            'sliced_STLs_match_current_files':True,'3MF_units_and_indices':True,
            'DXF_hole_positions_match':True,'CSV_columns_consistent':True,'PDFs':pages}
    (ROOT/'docs/delivery_checks.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print(json.dumps(report,indent=2,ensure_ascii=False))

if __name__=='__main__':run()
