# Sources and third-party notices

The MIT license covers this project's original CAD design, generated adapter models, code and documentation. It does **not** replace licenses or rights in third-party references. Unitree names identify compatible products; this project is independent and does not imply manufacturer endorsement.

| Reference | Pinned source | Rights / use |
|---|---|---|
| R1-7A arm STEP | [unitreerobotics/r1-7a_sdk](https://github.com/unitreerobotics/r1-7a_sdk/tree/2c89fe4f60f0c98f1bc06795cb2477cc73d0c92c), `step/R1-7A机械臂_简化模型_0928.STEP` | BSD-3-Clause; [original license](references/UNITREE_REPOSITORY_LICENSE.txt) |
| DEX1-1 appearance meshes and URDF | [unitreerobotics/unitree_ros](https://github.com/unitreerobotics/unitree_ros/tree/5994d4faef0a9cadd3287f8de0199a67eeb2a259), `robots/g1_description/meshes/Dex1_*` and `g1_29dof_mode_15_with_dex1_1.urdf` | BSD-3-Clause; [original license](references/UNITREE_ROS_LICENSE.txt) |
| DEX1-1 interface drawing | [Official product page](https://www.unitree.com/Dex1-1/) and [dimension image](https://www.unitree.com/images/480c4c42e3154ec7aebb36b2b5a3b720_1525x475.png) | Unitree product material; no project license is asserted over the reference image |

`references/r1_*_normalized.*` are coordinate-transformed or tessellated derivatives of the official STEP. `references/g1_dex_meshes/` and the URDF retain their upstream rights. Adapter assembly images combine those references with this project's original parts. Generated geometry under `cad/preview/` and `cad/assembly_reference.step` may include official reference geometry and therefore retains the corresponding attribution.

The source STEP SHA-256 is `fe371fe75dd48e0c9c0779505d8b74269e367dc45facb39541459edfd79daa04`. The normalization transform is recorded in [arm_transform.json](references/arm_transform.json). The wrist datum is Z=0, the arm lies at negative Z, and the gripper mounting face is at positive Z. The official simplified assembly contains pre-existing intersections; checks evaluate each added part against individual reference solids.

DEX meshes are used for appearance and sampled envelope checks, not for precision thread metrology. The 10 × 30 mm M3 interface comes from the official dimension drawing. Reference data was retrieved on 2026-10-17; V2 was prepared on 2026-10-19.

The offline interactive viewer embeds Plotly.js, whose MIT license notice is retained in the bundled script.
