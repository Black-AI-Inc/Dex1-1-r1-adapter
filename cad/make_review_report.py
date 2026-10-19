#!/usr/bin/env python3
"""Chinese assembly review and a reproducible physical acceptance worksheet."""
import csv
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Image,PageBreak,Spacer

from build_adapter import ROOT,P

OUT=ROOT/'docs'
INK=colors.HexColor('#203a4c');TEAL=colors.HexColor('#27879b')
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
body=ParagraphStyle('b',fontName='STSong-Light',fontSize=10.5,leading=16,spaceAfter=7,wordWrap='CJK',textColor=INK)
small=ParagraphStyle('s',parent=body,fontSize=9,leading=13)
title=ParagraphStyle('t',parent=body,fontSize=21,leading=28,spaceAfter=13)
sub=ParagraphStyle('h',parent=body,fontSize=13,leading=19,spaceBefore=9,spaceAfter=6,textColor=TEAL)

def p(s,style=body):return Paragraph(s.replace('Ø','直径 ').replace('³','3').replace('·',' '),style)
def table(rows,widths):
    t=Table([[p(str(x),small) for x in r] for r in rows],colWidths=[x*mm for x in widths])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e7f1f3')),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LINEBELOW',(0,0),(-1,-1),.35,colors.HexColor('#d0dbe1')),('TOPPADDING',(0,0),(-1,-1),6),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),('LEFTPADDING',(0,0),(-1,-1),6)]))
    return t

def run():
    val=json.loads((OUT/'assembly_validation.json').read_text())
    story=[p('装配复核与实测清单',title),p('R1-7A × DEX1-1 / ABS v0.2 / 2026-10-18',sub),
        p('结论：已解决常见硬件兼容和台面拧紧路径；腕壳配合、压紧工艺及承载能力仍须首件实测。本版是可打印的试配设计，不是已验收的运行件。'),
        Image(str(OUT/'complete_assembly.png'),width=175*mm,height=98.44*mm),
        p('与官方照片的装配效果',sub),
        p('整体形式相近：夹爪与腕部轴线重合，电机筒体接在腕部前端。蓝色环最大直径 52、总高 13，其中 5 插入腕壳，夹爪贴合面位于腕壳端面前方 8。黑色 ABS 会比图中的蓝色更接近产品配色。'),
        p('这里的 8 mm 是相对腕壳基准面的尺寸，不能解释成“比原厂多 8 mm”。原厂转接件的实际外伸、包覆关系和线束布置未得到尺寸依据。夹爪开合平面由本方案的 90° 孔位转换确定，最终还需按实际腕部零位核对。'),
        p('本次修订',sub),
        table([['项目','v0.2'],['垫片兼容','背面沉孔由 7.4 扩至 8.6；主选日本常见 M3、外径 8、厚 0.5 的平垫片。'],
               ['工具与图纸','加入 4 颗螺钉、4 个垫片、整臂与夹爪外形、离线可旋转装配图。'],
               ['首件检查','新增约 3.1 g 的螺钉夹持试片，量化 B 档间隙，并给出逐级实测记录。']],[33,142]),PageBreak()]
    story += [p('1　日本常见紧固件',title),
        p('新增安装硬件只需 4 颗普通 M3×16 螺钉和 4 片平垫片。螺钉进入 DEX 金属内螺纹，ABS 不攻丝；本设计不依赖热熔铜螺母、定制套筒或微型止付螺钉。'),
        table([['数量','规格 / 日文采购词','核对尺寸'],
            ['4','M3×16 六角穴付ボルト / キャップスクリュー','M3×0.5；头径 5.5、头高 3；扳手对边 2.5。头下长度 16。'],
            ['4','M3 平ワッシャー / 丸ワッシャー<br/>3×8×0.5','外径 8、厚 0.5，内孔可自由通过 M3。只放 1 片。'],
            ['可替换','M3×16 十字穴付なべ小ねじ','本次核对款头径 5.5、头高 2，十字穴编号 2；选匹配的 #2 工具，杆径不大于 6。'],
            ['原装','R1-7A 腕壳紧固件','沿用原规格与厂家复装要求；简化模型不能确定其完整料号与拧紧扭矩。'],
            ['试配用','M3×8 普通小ねじ','薄的 A/B/C 孔位试配件才使用；本体和夹持试片仍用 M3×16。']],[18,78,79]),
        p('可直接查找的日本采购例子',sub),
        p('<link href="https://www.monotaro.com/p/4150/4863/">MonotaRO 41504863：M3×16 内六角圆柱头</link>；商品页列有 2.5 mm 内六角、5.5 mm 头径和 3 mm 头高。',small),
        p('<link href="https://www.monotaro.com/p/1651/2241/">MonotaRO 16512241：大里 515-201，3×8×0.5 平垫片</link>，10 片装。',small),
        p('<link href="https://www.monotaro.com/p/7976/9535/">MonotaRO 79769535：八幡ねじ 3×16 十字盘头</link>，6 颗装，可作为相同长度的备选。',small),
        p('以上在 2026-10-18 查到对应目录项；库存、价格和发货按下单页面核对。其他品牌同尺寸也可以。'),
        p('买错规格会改变安装结果',sub),
        p('M3×16 是头下长度。不要把圆柱头替换为沉头、自攻螺丝，或把带弹簧垫圈的组合螺钉直接代入。外径 7 的 ISO 平垫片也能放入，但主验收应统一使用外径 8、厚 0.5；混用厚垫片会减少旋入量。'),
        p('压紧不是越紧越好',sub),
        p('8 mm 垫片相对 7 mm 垫片的名义 ABS 承压面积增加约 40%；仍不能消除 ABS 的压痕和长期蠕变。估算 T=KFd、K=0.15～0.30 时，0.1 N·m 已对应约 2.7～5.4 MPa 平均面压；0.5 N·m 对应约 13.5～27 MPa。这些只是敏感性计算，不是推荐扭矩或材料许用应力。必须用实际 ABS、打印参数和夹持试片确定可重复的拧紧工艺。',small),PageBreak()]
    story += [p('2　螺钉怎么装、怎么拧',title),
        Image(str(OUT/'fastener_assembly.png'),width=175*mm,height=87.5*mm),
        p('按以下顺序操作',sub),
        p('① 先打印 fastener_stack_coupon.stl。它保留本体 13 mm 总厚、3.8 mm 沉孔深和真实孔径。检查所购 8 mm 垫片能平放，工具可直入，螺钉头不高出后表面。这个试片不装入腕壳，也不能用于承载。'),
        p('② 在试片里放 1 片 0.5 垫片和 M3×16，量螺钉露出量：名义 16 − (13 − 3.8) − 0.5 = 6.3 mm。再核对 DEX 实物的可用螺纹、孔口倒角和盲孔尖端余量，目标至少保留 1 mm 不顶底余量。尺寸图“深 8”不保证全部都是完整有效牙长。'),
        p('③ 支撑夹爪，先将四颗螺钉全部手动入牙，再用 2.5 mm 直头内六角按对角顺序逐步贴合。备用十字盘头用匹配的 #2 螺丝刀。最终紧固前确认安装面贴平；不能用螺钉把翘曲打印件强行拉平。不要用电动工具直接打紧。'),
        p('④ 台面上完成夹爪与法兰连接，记录拧紧过程和面压试片结果。然后按厂家允许的方式打开并复装两半腕壳，让卡耳进入内槽、平边对正。实体检查证明卡耳不能从闭合腕壳前端直接压入。'),
        p('⑤ 合拢后四条直线工具路径均被末端电机遮挡，因此维护流程按“取出夹爪组件后在台面复检”安排。另对 17 mm 短边的 L 形扳手作了 28 个静态姿态探查，均有碰撞；未证明可插入并连续转动，不能承诺原位补拧。'),
        p('⑥ 完成实物间隙、线束和静载验收后，才进入低速测试。中心 12 mm 孔只是预留通道；没有连接器尺寸和实际走线，不能保证插头能穿过或腕部全行程不拉线。'),
        p('维修便利性的边界',sub),
        p('本方案优先保持官方照片那样紧凑的外形，代价是夹爪固定螺钉藏在腕壳内部。若必须不打开腕壳即可换夹爪，需要另做外露快拆/分体连接机构，尺寸会更大。',small),PageBreak()]
    story += [p('3　数字校核的结果与边界',title),
        table([['检查','本次结果'],
            ['实体与网格','本体、A/B/C 试配件及夹持试片为有效单实体；STL 封闭、方向一致、体积为正。'],
            ['硬件 / 工具 / 放置路径',str(val['passed_interference_checks'])+' 项 CAD 相交检查通过：两种头型、垫片、台面工具、穿入路径、半壳相对法兰放置和法兰对官方整臂各实体。'],
            ['装好后的工具路径','4 个直工具通道均被末端电机遮挡；这是装配顺序约束，不是通过项。'],
            ['夹爪开合外形','固定官方臂姿态下，检查 URDF 行程内 10 个开度、两片手指和本体，共 21 个三角网格表面接触检查，未检出与臂接触。不是整臂关节运动仿真。'],
            ['孔与螺纹','10×30、M3 深 8 取自官方图。DEX 外形 STL 只辅助外观和外形包络；螺纹采用图纸代理，未把网格当成加工检验依据。'],
            ['物理试验','没有远程实物打印、装配、载荷、疲劳或热蠕变结果；没有用未标定材料参数做有限元并据此给额定载荷。']],[42,133]),
        p('需要真正解决的腕壳间隙',sub),
        p('B 档在固定、刚性的官方腕壳模型中，向前移动约 0.077 mm 或绕安装轴单向旋转约 0.462° 后才首次出现微小实体相交（阈值 0.001 mm3）。这些数字不包含摩擦、表面涂层、壳体变形或打印误差，也不等于装好后的实测晃动。'),
        p('若实际保留此间隙，反向定位会受影响。以本模型爪尖约 151 mm 距离估算，0.462° 对应约 1.2 mm 单侧横移；必须通过实测选档/调尺寸消除可感死区。四颗 DEX 螺钉只夹紧 DEX 与法兰，不会主动消除法兰与腕壳之间的间隙。'),
        p('如何按实测收敛尺寸',sub),
        p('先用 B 试配确认结构和孔位。测量打印后的定位直径、平边、卡耳直径/厚度，记录合拢后的轴向与转动间隙。A 比 B 紧，C 更松；若三档仍有死区，就按实测分别改 profiles 中相关尺寸及 retaining_center_z，重新打印试配件。不能仅对整件统一缩放，也不能靠加大原装腕壳螺钉扭矩来消间隙。'),
        p('本版未默认三档之一必然能锁紧。实物无晃动且复装不撑开壳体，是进入承载测试前的硬条件。',sub),PageBreak()]
    story += [p('4　首件实测与逐级验收',title),
        p('以下是项目首件筛查流程，验收目标可随实际任务提高；它不能替代寿命认证。抓取物质量、重心、加速度和打印设备尚未确定，因此不预设“可承载 2 kg”。'),
        table([['阶段','做什么 / 记录什么','通过条件'],
            ['打印与试片','校准条 → 夹持试片 → B 配合试片；记录打印机、ABS 批次、层高、温度、打印方向、实测尺寸和照片。','无翘曲、裂纹、卡耳白化、支撑残留；孔和垫片无需强压。'],
            ['紧固工艺','在夹持试片上用实际螺钉、垫片和可记录的扭矩方法试装；装后即刻、1 h、24 h 检查压痕、松弛和露出量。','安装面贴合；无顶底；无持续压陷/松弛。扭矩由首件结果确定，不能套金属 M3 表。'],
            ['本体与腕壳','先支撑住夹爪。按厂家方法复装，轻微反向推拉测死区，并记录原装壳体接缝是否被撑开。','无可感晃动。初步精度筛查可用轴向死区 ≤0.05 mm；距安装面 100 mm 测点的反向横移 ≤0.2 mm，需量具确认。这是本项目目标，非厂家标准。'],
            ['夹爪自重','在接近支撑台面的工装状态，承受夹爪+法兰+紧固件自重；检查最不利的静态弯矩方向，保持 30 min，再保持 24 h。','无裂纹、白化、永久位移、间隙增长或壳体异常；保留前后照片与读数。'],
            ['任务载荷','自重检查合格后，用目标抓取物的 25%、50%、100% 分级静载；每级记录重心位置，先保持 30 min，目标工况再做持续保持。','前一级合格才升级；超出接触面允许变形或间隙增长就停止，不能继续补拧当作通过。'],
            ['运动与温度','先空载低速 100 次；再分级加载。目标速度/加速度下先做 100 次筛查，再做至少 1000 次任务循环和实际最高使用温度下的保持检查。','线束无拉扯/夹伤；重新测量无增长。次数仅为首件筛查，不能据此推断长期疲劳寿命。']],[24,91,60]),
        p('载荷要看弯矩',sub),
        p('静态近似 M = Σ(m × g × L)，L 是各重心到腕壳接口的垂直力臂。例：只算 0.55 kg 夹爪、假设力臂 80 mm，已产生约 0.43 N·m；抓取物还会增加弯矩，运动加速度也会增加载荷。80 mm 是示例，不是已测得的 DEX 重心。'),
        p('把空载工具总质量、实际重心和 TCP 输入控制器。测试中出现变化，先卸载并检查；保留失效件与参数，便于区分尺寸、层间结合、压紧和结构问题。',small),PageBreak()]
    story += [p('5　打印、文件与依据',title),
        p('ABS 打印设置',sub),
        p('先以 0.4 mm 喷嘴、0.16 mm 层高、6～8 道壁、100% 填充、顶底至少 8 层作为起点，采用封闭腔体，温度按耗材规格。print/ 中的本体已按夹爪平面朝下摆放；两侧卡耳悬挑需要支撑，支撑必须允许落在模型安装盘背面，不能只勾选“仅接触热床”。'),
        p('薄配合试片面厚修订为 1.28 mm，与本体 8 mm 相差 42 个 0.16 mm 层；使用同样的首层厚度，才能让试片与本体的卡耳分层位置一致。卡耳厚 1.7 mm，约跨 11 个 0.16 mm 层。支撑拆除可能伤到卡耳，必须放大检查。8.6 mm 沉孔之间只剩 1.4 mm 料宽，要在实际切片器中确认保留连续壁线。3MF 仅包含毫米制几何，不包含你们打印机的设备和耗材配置。'),
        p('切片验证记录',sub)]
    slicer=OUT/'slicer_validation.json'
    if slicer.exists():
        s=json.loads(slicer.read_text())
        story += [p(s['summary']),p('此为通用几何切片检查，不是指定打印机的可执行打印任务。生产前仍需检查自己的切片预览，尤其卡耳支撑、沉孔、1.4 mm 孔间薄壁和首层补偿。',small)]
    else:story += [p('已检查打印姿态与网格；尚未完成目标设备的切片路径审查。请在实际切片器中逐层检查上述关键区域。')]
    story += [p('新增文件',sub),table([['文件','用途'],
        ['print/fastener_stack_coupon.stl','3.1 g 单孔夹持试片，使用本体同款 M3×16。'],
        ['docs/complete_assembly.png','整臂与夹爪的比例效果。'],
        ['docs/fastener_assembly.png','台面装配顺序和螺钉夹持厚度。'],
        ['docs/assembly_interactive.html','离线打开即可旋转；参考臂与夹爪不可打印。'],
        ['cad/assembly_with_hardware.step','硬件装配 CAD；DEX 仅有明确命名的图纸接口代理。'],
        ['docs/assembly_validation.json','171 项通过检查、被遮挡的工具路径及名义间隙。'],
        ['docs/physical_acceptance.csv','可填写的首件验收记录；当前全为待测。']],[85,90]),
        p('官方来源与模型范围',sub),
        p('<link href="https://github.com/unitreerobotics/r1-7a_sdk">R1-7A 官方 SDK / STEP</link>，固定提交 2c89fe4f60f0c98f1bc06795cb2477cc73d0c92c。<br/><link href="https://www.unitree.com/Dex1-1/">DEX1-1 官方尺寸图</link>：M3 深 8 孔组为 10×30。<br/><link href="https://github.com/unitreerobotics/unitree_ros/tree/5994d4faef0a9cadd3287f8de0199a67eeb2a259/robots/g1_description">unitree_ros 的 G1 DEX 外形与 URDF</link>：本次使用与外观尺寸相符的 Dex1_base_link 和两片手指。另一个 dexterous_hand_description/dex1_1 模型尺寸不同，未混用为本次外形基准。',small),
        p('数值验证不包含实际线束、未公开紧固件、控制器限制或制造批次偏差。官方几何与许可归 Unitree；独立 ABS 适配器为本项目设计，未获厂家认证。',small)]
    def footer(c,d):
        c.setFont('STSong-Light',8);c.setFillColor(INK)
        c.drawString(18*mm,10*mm,'R1-7A / DEX1-1 / ABS v0.2 / 实物验收前')
        c.drawRightString(192*mm,10*mm,str(d.page))
    SimpleDocTemplate(str(OUT/'装配复核与实测清单.pdf'),pagesize=A4,leftMargin=18*mm,rightMargin=17*mm,
        topMargin=16*mm,bottomMargin=20*mm,title='R1-7A DEX1-1 ABS v0.2 装配复核与实测清单').build(story,onFirstPage=footer,onLaterPages=footer)
    rows=[]
    for test in ['50 mm 与孔径校准','单孔夹持试片 / 螺钉露出量','有效牙长及不顶底余量','1 h 压紧松弛','24 h 压紧松弛','腕壳试配 / 轴向死区','腕壳试配 / 100 mm 处反向横移','自重 30 min','自重 24 h','25% 任务载荷','50% 任务载荷','100% 任务载荷','空载低速 100 次','任务循环 1000 次','实际使用温度保持','线束全程检查 / TCP 标定']:
        rows.append([test,'待测']+['']*14)
    # Regenerating drawings must never overwrite a user's completed test log.
    if not (OUT/'physical_acceptance.csv').exists():
        with (OUT/'physical_acceptance.csv').open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.writer(f);w.writerow(['项目','状态','日期','打印机/喷嘴','ABS牌号/批次','层高/壁数/温度','档位/实测尺寸','扭矩Nm/方法','抓取物kg','重心力臂mm','速度/加速度','环境温度C','测试时间/次数','前后间隙mm','照片/备注','操作者']);w.writerows(rows)
    print('Saved assembly review PDF and pending physical acceptance worksheet.')

if __name__=='__main__':run()
