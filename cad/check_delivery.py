#!/usr/bin/env python3
"""Check release links, file formats, validation hashes and pending physical status."""
import csv,hashlib,json,re,zipfile,py_compile
from pathlib import Path
from xml.etree.ElementTree import fromstring
from urllib.parse import unquote
from pypdf import PdfReader
from build_v2 import OUT,P
from mesh_tools import validate_mesh

def main():
    checks=[]
    def ok(label,condition):
        assert condition,label
        checks.append(label)
    for p in (OUT/'cad').glob('*.py'):py_compile.compile(str(p),doraise=True)
    ok('all Python sources compile',True)
    for file in [OUT/'README.md',OUT/'README.zh-CN.md',OUT/'NOTICE.md',OUT/'CONTRIBUTING.md']+list((OUT/'docs').glob('*.md')):
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            if link.startswith(('http:','https:','#','mailto:')):continue
            target=unquote(link.split('#')[0])
            if target:ok(f'link: {file.name} -> {target}',(file.parent/target).exists())
    slice_report=json.loads((OUT/'docs/slicer_validation.json').read_text());asm=json.loads((OUT/'docs/assembly_validation.json').read_text())
    for stl in (OUT/'print').glob('*.stl'):
        sha=hashlib.sha256(stl.read_bytes()).hexdigest()
        ok('slice hash '+stl.name,sha==slice_report['parts'][stl.stem]['STL_SHA256'])
        ok('assembly hash '+stl.name,sha==asm['stl_sha256'][stl.name])
        validate_mesh(stl)
        with zipfile.ZipFile(stl.with_suffix('.3mf')) as z:
            ok('3MF archive '+stl.name,z.testzip() is None)
            model=fromstring(z.read('3D/3dmodel.model'));ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
            ok('3MF units '+stl.name,model.attrib['unit']=='millimeter')
            vs=model.findall('.//m:vertex',ns);ts=model.findall('.//m:triangle',ns)
            ok('3MF indices '+stl.name,len(vs)>0 and len(ts)>0 and all(0<=int(t.attrib[k])<len(vs) for t in ts for k in ['v1','v2','v3']))
    for p in ['assembly_guide.pdf','assembly_guide.zh-CN.pdf','dimensions.pdf']:
        reader=PdfReader(str(OUT/'docs'/p));text='\n'.join(x.extract_text() for x in reader.pages)
        ok('PDF text '+p,len(reader.pages)>0 and 'M3' in text and '6.5' in text)
    with (OUT/'docs/physical_acceptance.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    ok('physical tests remain pending',len(rows)==17 and all(r['status']=='PENDING' and None not in r for r in rows))
    ok('offline interactive viewer',(OUT/'docs/assembly_interactive.html').stat().st_size>1_000_000)
    ok('English and Chinese README switch','README.zh-CN.md' in (OUT/'README.md').read_text() and 'README.md' in (OUT/'README.zh-CN.md').read_text())
    ok('main check count',asm['passed_checks']==270 and all(x['passed'] for x in asm['checks']))
    variants=json.loads((OUT/'docs/variant_validation.json').read_text());ok('variant checks',variants['passed_checks']==29 and all(x['passed'] for x in variants['checks']))
    env=json.loads((OUT/'docs/gripper_envelope_validation.json').read_text());ok('gripper envelopes',len(env['cases'])==21 and all(x['surface_contacts']==0 for x in env['cases']))
    result={'revision':P['revision'],'passed_delivery_checks':len(checks),'checks':checks,'physical_status':'PENDING'}
    (OUT/'docs/delivery_checks.json').write_text(json.dumps(result,indent=2));print(len(checks),'delivery checks passed')
if __name__=='__main__':main()
