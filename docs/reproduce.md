# Reproduce the models and checks

The reference environment used Python 3.12 and the pinned packages in `cad/requirements.txt`. CAD is generated with CadQuery; no proprietary CAD application is required. All dimensions are millimetres.

```sh
python -m pip install -r cad/requirements.txt
python cad/build_v2.py
python cad/package_geometry.py
python cad/check_v2.py
python cad/check_variants.py
python cad/views_v2.py
```

`build_v2.py` writes all STEP and print-oriented STL models. `package_geometry.py` wraps the STL meshes in millimetre, geometry-only 3MF files. `check_v2.py` verifies the main assembly and writes the reference STEP assembly and visualization meshes. `check_variants.py` checks the alternate thread fits. `views_v2.py` renders previews and checks sampled finger travel in the fixed official arm pose. `--views-only` skips the unchanged envelope check when adjusting image presentation.

The printable collar uses overlapping short helical cutter segments. A single periodic multi-turn cut, and automatic unification of those periodic faces, produced incorrect geometry in the reference CAD kernel. The build therefore preserves the boolean faces and independently checks exported meshes with Manifold. Do not remove those checks when refactoring the thread.

For slicing, install **PrusaSlicer 2.5.2** and put its CLI executable on your path. Geometry checks used the conservative configuration in `docs/slicing_geometry_check.ini`:

```sh
python cad/slice_models.py --slicer prusa-slicer --output /tmp/r1-adapter-slices
python cad/check_slicing_v2.py /tmp/r1-adapter-slices
```

Only the anchor and wrist-fit coupon enable support. Other models explicitly disable it. This is validation G-code; do not send it to a printer. Re-slice with the actual machine and ABS profile. Different slicer versions can change paths and should be reviewed.

For publication artifacts:

```sh
python cad/make_documents.py
python cad/check_delivery.py
python cad/package_release.py --output /tmp/r1-adapter-release
```

Preview generation uses the included upstream reference files. On Linux, install Noto CJK fonts for Chinese preview text and the Chinese PDF. PDF text uses ReportLab's STSong-Light CJK font. The release package contains reference licenses and a SHA-256 manifest; it does not contain validation G-code or a preconfigured machine profile.

All physical rows in `docs/physical_acceptance.csv` are initially `PENDING`. CAD checks do not change their status.
