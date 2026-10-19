R1-7A × DEX1-1 ABS 转接法兰 v0.2
2026-10-18 | 单位 mm | 先实物试配，再做载荷验证

这是面向新发售的独立七轴 Unitree R1-7A 的参数化转接件。
基于宇树官方 STEP 的“末端连接件”两半腕壳，以及 DEX1-1 官方尺寸图设计。
通过腕壳内槽捕获两侧卡耳，用平边防转；四颗螺钉连接 DEX 的金属螺纹。

建议从这里开始
1. 先读 docs/装配复核与实测清单.pdf；原几何说明见 docs/使用说明_中文.pdf。
   先打印新增 fastener_stack_coupon.stl（约 3.1 g），试用常见 M3×16 与外径 8、厚 0.5 平垫片。
2. 先打印 print/fit_coupon_B.stl（约 7.2 g），检查腕壳与孔位。
   A 更紧，C 更松；每档独立使用，不叠装。试配件不能承载或运行机械臂。
3. B 合适后再打印 print/adapter_B.stl 或 adapter_B_mm.3mf。
   本体最大外径 52，总高 13，实心 ABS 约 21.0 g。
4. 本体用 4×M3×16 内六角圆柱头螺钉及 4×M3 垫片（8×3.2×0.5）。
   预计旋入 6.3，须核实盲孔有效深度。试配件减薄，不能用同样长的螺钉；见 PDF。
5. 先在台面上把本体与 DEX 固定好，再按厂家允许方式放入两半腕壳并复装。

关键接口
- DEX 的 M3 深 8 孔组是 10×30；20×15 对应直径 4 深 2 浅孔组，未使用。
- 本设计将 DEX 绕安装轴旋转 90°，四孔位于 (±15, ±5)。
- 腕壳参考入口直径 45，内槽直径 52、深度范围 Z=-3 到 -1，平边距 28。
- B 档定位轮廓直径 44.5、平边 27.6、R4 过渡；卡耳直径 51.5、宽 19.6、厚 1.7。
- 装配 CAD 坐标：腕壳前端平面 Z=0，夹爪安装面 Z=+8；背部插入至 Z=-5。
- print/ 内文件已旋转至夹爪平安装面朝下。STL 约定 mm，3MF 明确使用毫米单位。

ABS 起点
0.4 喷嘴、0.16 层高、6～8 道壁、100% 填充、顶底不少于 8 层、封闭腔体、8～10 mm brim。
耗材温度按其规格（常见起点：喷嘴 250°C / 热床 105°C）。
仅支撑卡耳悬挑区域，允许支撑落在安装盘背面；不要堵住孔。
默认比例为 100%。可先打印 ABS_50mm_calibration.stl 校准 50 mm 外长和孔径。
3MF 仅包含几何，不包含打印机或耗材设置；需要自行切片。

文件
print/       本体、A/B/C 试配件、毫米制 3MF、50 mm ABS 校准条
cad/         STEP、参数 JSON、CadQuery 源文件、装配及剖视参考
docs/        两页尺寸图、四页中文说明、DXF 孔位图、预览和校核记录
references/  从官方模型提取并归一化的腕壳、尺寸图、测量记录和来源许可
sources.txt  官方来源及固定版本链接

修改参数
基础环境：Python + CadQuery 2.7.x（本次使用 2.7.0）。
在 cad/parameters.json 中修改 fit_profile（A/B/C）、配合尺寸或其他参数，然后运行：
  python cad/build_adapter.py --validate-reference
  python cad/make_print_package.py
本体会按所选档位输出为 adapter_A、adapter_B 或 adapter_C。
本包预导出的本体为 B 档。保留 A/B/C 试配文件便于选择。
改安装盘厚度或沉孔深度时，必须同时检查螺钉夹持长度及盲孔余量。
python cad/make_documentation.py 可重建默认 B 档文档；需要 matplotlib、reportlab、
ezdxf 及 Noto CJK 字体。改变几何后要同步核对图纸标注；字体路径按本机调整。

新增复核与关键限制
171 项硬件/台面工具/接口相交检查通过；21 个固定臂姿态下的夹爪外形接触检查通过。
装好腕壳后，4 条直线拧紧路径被末端电机遮挡，按台面预装、取出组件后复检的流程使用。
B 档理想刚性模型约有 0.077 mm 轴向、单向 0.462° 转动自由余量；不能因此认为装上即锁紧。
必须按试片实测选档/改尺寸，确认无晃动且壳体不被撑开，再进行分级载荷和长期松弛检查。
四颗夹爪固定螺钉不会消除腕壳接口间隙。拧紧工艺与额定载荷尚未验证。
完整效果：docs/complete_assembly.png；旋转查看：docs/assembly_interactive.html（离线 HTML）。
相对腕壳端面外伸 8 mm，不代表相对原厂连接件多 8 mm。
日本采购例子见 docs/日本采购清单.csv；实物验收表 docs/physical_acceptance.csv 当前全部待测。

校核范围
本体及三个试配件均为有效单实体，STL 封闭且绕向一致；
与固定版本官方腕壳的相交体积均为 0 mm3（容许阈值 0.01）。详见 docs/validation.json。
已用通用 PrusaSlicer 2.5.2 配置完成几何切片与关键路径检查；尚未在实际打印机上打印、装配，或进行强度、疲劳、温度与蠕变试验。
通用切片参数仅用于复现路径检查；不提供可直接发送到打印机的 G-code。
因此不给 ABS 转接件指定额定载荷；机械臂的 2 kg 产品载荷不能直接沿用。
实际批次尺寸需试配；卡耳较薄，必须检查层间结合与支撑清理质量。
灰色腕壳仅为装配参考，不是打印任务。

完整重建顺序（Python 依赖见 cad/requirements.txt）
python cad/build_adapter.py --validate-reference
python cad/check_assembly.py
python cad/make_print_package.py
python cad/make_documentation.py
python cad/make_assembly_views.py
python cad/make_review_report.py
L 形扳手静态探索记录另见 docs/L_key_access_exploration.json；28 个测试姿态均有碰撞。

试片分层修订：A/B/C 试片面厚 1.28 mm，与本体 8 mm 相差 42 个 0.16 mm 层。
本体与试片使用相同首层厚度与层高；若改层高，须同步调整 coupon_face_thickness / print_reference_layer_height 并重新切片检查。
