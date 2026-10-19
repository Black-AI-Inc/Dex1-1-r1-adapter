#!/usr/bin/env python3
"""Generate validation-only G-code using an installed PrusaSlicer CLI."""
import argparse,subprocess
from pathlib import Path
from build_v2 import OUT
p=argparse.ArgumentParser();p.add_argument('--slicer',required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
for stl in sorted((OUT/'print').glob('*.stl')):
    cmd=[args.slicer,'--export-gcode','--load',str(OUT/'docs/slicing_geometry_check.ini'),'--output',str(args.output/(stl.stem+'.gcode'))]
    if stl.stem not in ['anchor','wrist_fit_coupon']:cmd.append('--no-support-material')
    r=subprocess.run(cmd+[str(stl)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    (args.output/(stl.stem+'.log')).write_text(r.stdout)
    if r.returncode:raise RuntimeError(r.stdout)
    print(stl.stem,'sliced for geometry inspection only',flush=True)
