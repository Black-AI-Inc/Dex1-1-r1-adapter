# R1-7A × DEX1-1 ABS Adapter

**English** · [简体中文](README.zh-CN.md)

A printable adapter for the **standalone Unitree R1-7A arm** and **DEX1-1 gripper**. A threaded collar takes up axial clearance after the wrist is assembled; a standard M3 screw locks the collar. Three printed parts, no heat-set inserts.

![Assembly preview](docs/complete_assembly.png)

**Status: V2 release candidate.** CAD, assembly clearances and reference toolpaths have been checked. Physical fit, load capacity and long-term ABS creep have **not** been validated.

## Get started

1. [Download the latest release](https://github.com/Black-AI-Inc/Dex1-1-r1-adapter/releases) for STL, 3MF, STEP and source files.
2. Print the thread, wrist-fit and hardware coupons first. Choose the collar clearance that fits your printer.
3. Print the three parts below in ABS, then follow the [assembly guide](docs/assembly_guide.md).

| Part | Print file | Quantity |
|---|---|---|
| Anchor | [anchor.stl](print/anchor.stl) | 1 |
| Thrust plate | [thrust_plate.stl](print/thrust_plate.stl) | 1 |
| Preload collar, default C030 | [preload_collar.stl](print/preload_collar.stl) | 1 |

C020 and C040 collars provide tighter and looser thread fits. Print **one** selected collar. All models use millimetres; STL/3MF files are already oriented for printing.

**Hardware:** 5 × M3×20 socket-head screws, 5 × M3 flat washers (8 mm OD × 0.5 mm), and 1 × ordinary M3 hex nut (5.5 mm AF × 2.4 mm). Reuse the original wrist screws. [BOM and Japanese supplier examples](docs/bom.csv).

**Reference print setup:** 0.4 mm nozzle, 0.16 mm layers, 8 walls and 100% infill. Only the anchor and wrist-fit coupon need local support. Use your printer's ABS profile; no machine-ready G-code is supplied.

## Documentation

- [Assembly, fit selection and physical acceptance](docs/assembly_guide.md)
- [Validation scope and results](docs/validation.md)
- [Offline interactive assembly](docs/assembly_interactive.html) — download and open locally
- [Source models and attribution](NOTICE.md) · [Changes](CHANGELOG.md)

The coaxial layout follows the official product illustration. The collar adds a small locking tab; the gripper mounting face is about **14.5 mm ahead of the wrist datum**. This is an independent design, not an official Unitree part.

## Modify the design

Edit [cad/parameters.json](cad/parameters.json), then run:

```sh
python -m pip install -r cad/requirements.txt
python cad/build_v2.py
python cad/check_v2.py
```

See [reproduction instructions](docs/reproduce.md) for slicing, previews and packaging. Original project files use the [MIT license](LICENSE); official reference assets retain their upstream licenses. Fit reports and improvements are welcome—see [contributing](CONTRIBUTING.md).
