#!/usr/bin/env python3
"""Build the self-contained ZIP, with all upstream notices and a hash manifest."""
import argparse,hashlib,json,zipfile
from pathlib import Path
from build_v2 import OUT
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
files=[]
for f in sorted(OUT.rglob('*')):
    rel=f.relative_to(OUT)
    if not f.is_file() or '.git' in rel.parts or '__pycache__' in rel.parts or f.suffix in ['.pyc','.gcode','.zip']:continue
    if rel.parts[0] not in ['cad','docs','print','references'] and len(rel.parts)>1:continue
    if f.name=='MANIFEST_SHA256.json':continue
    files.append(f)
manifest={str(f.relative_to(OUT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
path=args.output/'R1-7A_DEX1-1_ABS_V2_RC1.zip'
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for f in files:z.write(f,'R1-7A_DEX1-1_ABS_V2_RC1/'+str(f.relative_to(OUT)))
    z.writestr('R1-7A_DEX1-1_ABS_V2_RC1/MANIFEST_SHA256.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(path) as z:
    assert z.testzip() is None
    for name,sha in manifest.items():assert hashlib.sha256(z.read('R1-7A_DEX1-1_ABS_V2_RC1/'+name)).hexdigest()==sha
print(json.dumps({'path':str(path),'files':len(files)+1,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()},indent=2))
