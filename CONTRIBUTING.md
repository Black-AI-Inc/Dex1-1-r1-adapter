# Contributing

Fit reports, assembly photos and CAD improvements are welcome. English and Chinese reports are both useful.

For a fit report, include the arm/gripper revision, printer, nozzle, layer height, ABS brand, dimensional compensation, selected collar, measured clearances and any filing or re-tightening. For a load test, include payload, moment arm, speed/acceleration, duration and temperature. Do not describe an unmeasured setup as zero-backlash or load-rated.

For design changes, edit `cad/parameters.json` or the source rather than a generated STL. Rebuild the parts and run the checks relevant to the changed geometry. Keep English and Chinese assembly instructions consistent, preserve upstream attributions, and attach the resulting validation records. See [reproduction instructions](docs/reproduce.md).

Please do not reuse a physical pass result for a changed material, fit, print orientation or interface geometry without repeating the affected test.
