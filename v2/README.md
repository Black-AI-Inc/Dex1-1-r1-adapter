# V2 可调压紧转接环 — 发布候选版

适用于新款 Unitree R1-7A 独立机械臂与 DEX1-1。由转接主体、承压垫环、打印压紧环组成；普通 M3 螺钉与螺母锁住压紧环。无 M3 打印螺纹或热熔铜螺母。

目前已通过 270 项 CAD / STL / 装配检查和 11 个打印件的通用切片检查。完整装配图与中文手册正在整理。

**尚未进行实物验证。** 可调压紧结构针对 v0.2 的轴向自由间隙；抗转保持依赖夹紧摩擦，ABS 蠕变、实际载荷和打印精度仍须台架验证。请先打印螺纹和腕口试片。

- `print/anchor.stl`：主体
- `print/thrust_plate.stl`：承压垫环
- `print/preload_collar.stl`：默认 C030 压紧环
- C020 / C040 是较紧 / 较松的压紧环，按试片选择其中一只
- `thread_*_coupon`：螺纹配合试片；`wrist_fit_coupon`：腕口试片；`hardware_coupon`：螺钉夹持试片
- `cad/parameters.json`、`cad/build_v2.py`：参数和建模源码
- `docs/*validation.json`：当前验证证据

主装配需要 5 颗 M3×20 圆柱头内六角螺钉、5 片 Ø8×0.5 M3 平垫片、1 颗普通 M3 六角螺母（AF5.5×2.4）。不包含腕壳原厂螺钉，腕壳须复用原件。
