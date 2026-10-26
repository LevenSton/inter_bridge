#!/usr/bin/env python3
"""
生成 docs/pump-bridge-vs-relay.md 里用到的全部图（SVG + PNG）。

用法：
    python3 docs/diagrams/gen.py          # 生成 SVG；装了 rsvg-convert 时同时导出 2x PNG 到 png/
数据来源：Relay 文档、Relay 公开 API、两次实测的链上交易（见文档 §3.1 / §3.7）。
改数字或文案后重跑即可，所有图共用 svgkit 的样式。
"""
import os
import shutil
import subprocess

from svgkit import B, Fig, Seq, SUB, MUTED

OUT = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# 资金流转图的公共布局：两条竖向泳道，左边买入、右边卖出；费用芯片挂在右侧
# ---------------------------------------------------------------------------
LANE_W = 570
BOX_W, BOX_H, GAP = 268, 62, 64


def lane(f, x, y, items):
    """在泳道里竖着排一列框，返回 B 列表。items = [(标题, [副标题], 颜色)]"""
    out = []
    for i, (t, s, c) in enumerate(items):
        out.append(f.box(x + 22, y + i * (BOX_H + GAP), BOX_W, BOX_H, t, s, c=c, tsize=14, ssize=12))
    return out


def down(f, b1, b2, label, c="gray", dash=False, dx=44):
    """b1 底部 -> b2 顶部 的竖向箭头，标签写在箭头右侧（可用 \\n 换行）。"""
    x = b1.l + dx
    f.arrow([(x, b1.b), (x, b2.t)], c=c, dash=dash)
    lines = label.split("\n")
    mid = (b1.b + b2.t) / 2 - (len(lines) - 1) * 8 + 4
    col = MUTED if c == "gray" else None
    for i, s in enumerate(lines):
        f.text(x + 10, mid + i * 16, s, size=12, anchor="start", halo="#ffffff",
               fill=col or {"blue": "#1d4ed8", "orange": "#c2410c", "teal": "#0f766e",
                            "purple": "#6d28d9", "red": "#b91c1c", "green": "#2f7d32"}[c])


def fees(f, src, lane_x, y, items, h=46, gap=10, label=None):
    """从 src 框右侧引一条总线，挂一列费用芯片。items = [(标题, 副标题, 颜色)]"""
    cx = lane_x + 342
    bus = lane_x + 322
    chips = []
    for i, (t, s, c) in enumerate(items):
        chips.append(f.box(cx, y + i * (h + gap), 210, h, t, [s] if s else [], c=c, tsize=12.5, ssize=11))
    ys = [b.cy for b in chips] + [src.cy]
    f.arrow([(src.r, src.cy), (bus, src.cy)], head=False, width=1.4)
    f.arrow([(bus, min(ys)), (bus, max(ys))], head=False, width=1.4)
    for b in chips:
        f.arrow([(bus, b.cy), (b.l, b.cy)], width=1.4)
    if label:
        f.text(cx, chips[0].t - 8, label, size=11.5, fill=SUB, anchor="start")
    return chips


# ---------------------------------------------------------------------------
# 图 1  Relay 架构
# ---------------------------------------------------------------------------
def fig_relay_arch():
    f = Fig("01-relay-arch", 1200, 780, "图 1  Relay 协议架构（以 Solana 上的币 → BSC meme 为例）",
            "蓝色 = 执行路径（用户在等的部分）　橙色 = Solver 事后结算回款（异步，用户无感）　虚线 = 监听 / 读取")
    app = f.box(60, 102, 300, 62, "Pump.fun 前端（集成方）", ["发起下单 · 展示报价"], c="gray")
    api = f.box(480, 102, 320, 62, "Relay API / SDK", ["报价 · 执行步骤 · 状态 · appFees"], c="yellow")
    f.arrow([(app.r, 122), (api.l, 122)], label="请求报价", at=(420, 114))
    f.arrow([(api.l, 146), (app.r, 146)], dash=True, label="报价 + 待签交易", at=(420, 162))

    f.group(40, 214, 340, 256, "源链 Solana", "blue")
    f.group(430, 214, 340, 256, "Solver（第三方 · 链下 · 自有资金）", "teal")
    f.group(820, 214, 340, 256, "目标链 BSC", "blue")
    w = f.box(80, 254, 260, 58, "用户钱包", ["SOL / USDC · 需自付 SOL gas"], c="gray")
    d = f.box(80, 372, 260, 60, "Relay Depository", ["托管用户存款 · 记录 orderId"], c="blue")
    s = f.box(470, 262, 260, 160, "Solver", ["· 监听存款事件", "· 模拟填单（不行就退款）", "· 用自有资金在目标链填单",
                                            "多链库存：USDC / ETH / BNB …"], c="teal")
    x = f.box(860, 254, 260, 58, "DEX / 聚合器", ["KyberSwap 等 · USDC → BNB → meme"], c="gray")
    u = f.box(860, 372, 260, 60, "用户 BSC 地址", ["收到 meme"], c="green")
    f.arrow([(210, app.b), (210, w.t)], label="用户签名并发送", at=(220, 200), anchor="start")
    f.arrow([(210, w.b), (210, d.t)], c="blue", label="存款 + orderId", at=(220, 347), anchor="start")
    f.arrow([(d.r, 388), (s.l, 388)], c="blue", dash=True, label="存款事件", at=(405, 380))
    f.arrow([(s.r, 283), (x.l, 283)], c="blue", label="自有 USDC 买币", at=(795, 275))
    f.arrow([(990, x.b), (990, u.t)], c="blue", label="meme 到账", at=(1000, 347), anchor="start")
    f.arrow([(s.l, 414), (d.r, 414)], c="orange", label="⑧ 取回存款", at=(405, 434))

    f.group(40, 520, 1120, 210, "结算层（Relay 自有基础设施 · 异步）", "orange")
    hub = f.box(80, 582, 280, 74, "Relay Chain · Hub", ["ERC6909 账本：MINT / TRANSFER / BURN", "约 $0.005 / 单"], c="orange")
    ora = f.box(460, 582, 280, 74, "Oracle", ["读两条链，核对存款与填单", "签发 EIP-712 证明"], c="orange")
    alo = f.box(840, 582, 280, 74, "Allocator @ Aurora", ["NEAR MPC 网络", "签发提款证明"], c="orange")
    f.arrow([(600, s.b), (600, ora.t)], c="orange", label="④ 请求证明", at=(608, 552), anchor="start")
    f.arrow([(520, ora.t), (520, 492), (210, 492), (210, d.b)], c="orange", dash=True, label="读存款", at=(365, 486))
    f.arrow([(680, ora.t), (680, 492), (990, 492), (990, u.b)], c="orange", dash=True, label="读填单", at=(835, 486))
    f.arrow([(ora.l, 619), (hub.r, 619)], c="orange", label="⑤ 记账", at=(410, 611))
    f.arrow([(220, hub.b), (220, 704), (980, 704), (980, alo.b)], c="orange",
            label="⑥ 提款：Hub 余额销毁 → 申请 MPC 证明", at=(600, 698))
    f.arrow([(1060, alo.t), (1060, 514), (700, 514), (700, s.b)], c="orange", label="⑦ MPC 提款证明", at=(1068, 552), anchor="start")
    f.text(40, 758, "用户等待的只有蓝色部分；橙色部分决定 Solver 的资金被占用多久，这部分成本最终会算进报价。",
           size=12.5, fill=SUB, anchor="start")
    return f


# ---------------------------------------------------------------------------
# 图 2  Relay 时序
# ---------------------------------------------------------------------------
def fig_relay_seq():
    parts = [("u", "用户", "Solana 钱包", "gray"), ("api", "Relay API", "报价", "yellow"),
             ("dep", "Depository", "Solana", "blue"), ("sol", "Solver", "第三方", "teal"),
             ("bsc", "BSC", "DEX + 用户地址", "green"), ("ora", "Oracle", "签证明", "orange"),
             ("hub", "Relay Chain", "Hub 账本", "purple"), ("alo", "Allocator", "NEAR MPC", "red")]
    f = Seq("02-relay-seq", 1240, 1220, "图 2  Relay 跨链买单时序（Solana → BSC meme）",
            "实线 = 调用 / 资金，虚线 = 返回 / 事件；蓝框 = 用户在等的部分，橙框 = 异步结算", parts, life_end=1090)
    f.begin("用户感知部分（约 1~4 s）", "blue")
    f.m("u", "api", "① 请求报价（1 USDC → meme）")
    f.m("api", "u", "路线 + 费用 + 待签交易", dash=True)
    f.note("u", "u", "需要 SOL 付 gas", c="yellow")
    f.m("u", "dep", "② 签名并存款（带 orderId）", c="blue")
    f.m("dep", "sol", "存款事件", c="blue", dash=True)
    f.note("sol", "sol", "模拟填单", c="teal")
    f.begin("alt 模拟结果", "red", "u", "bsc")
    f.m("sol", "bsc", "[可以填] ③ 自有 USDC 买 meme 转给用户", c="blue")
    f.m("sol", "u", "[填不了] Fast Refund：源链直接退款", c="red", dash=True)
    f.end()
    f.note("u", "bsc", "用户拿到 meme，用户感知到这里结束", c="green")
    f.end()
    f.begin("异步结算（用户无感，成本算进报价）", "orange")
    f.m("sol", "ora", "④ 请求证明", c="orange")
    f.m("ora", "dep", "核对存款", c="orange", dash=True)
    f.m("ora", "bsc", "核对填单", c="orange", dash=True)
    f.m("ora", "sol", "EIP-712 证明", c="orange", dash=True)
    f.m("sol", "hub", "⑤ 提交证明：MINT + TRANSFER 给 Solver", c="orange")
    f.m("sol", "hub", "⑥ 提款：余额转入确定性地址并 BURN", c="orange")
    f.m("sol", "alo", "⑦ 申请 MPC 提款证明", c="orange")
    f.m("alo", "sol", "MPC 证明", c="orange", dash=True)
    f.m("sol", "dep", "⑧ 提交证明，取回用户存款", c="orange")
    f.end()
    f.cards([("失败点：报价过期 / meme 滑点", "Solver 模拟失败就退款（Pump 实测 11.2%）", "red"),
             ("用户要有源链 gas", "否则走 gasless，成本计入报价", "yellow"),
             ("资金占用", "Solver 垫资到 ⑧ 才回款，成本进点差", "orange")], y=1120)
    return f


# ---------------------------------------------------------------------------
# 图 3  Relay 资金流转（通用）
# ---------------------------------------------------------------------------
def fig_relay_flow():
    f = Fig("03-relay-flow", 1240, 770, "图 3  Relay 资金流转与费用（通用模型）",
            "实线 = 资金移动　虚线 = 事件 / 事后结算　红色 = 从报价里扣掉的费用　实测金额见图 7")
    L, R = 40, 650
    f.group(L, 98, LANE_W, 630, "买入：Solana 上的币 → BSC meme", "blue")
    f.group(R, 98, LANE_W, 630, "卖出：BSC meme → Solana 上的币", "orange")
    a = lane(f, L, 140, [("用户 Solana 钱包", ["付出 X（SOL / USDC）"], "gray"),
                         ("Relay Depository · Solana", ["锁定 X，等 Solver 事后来取"], "blue"),
                         ("Solver（BSC 上的库存）", ["垫付 X − 各项费用"], "teal"),
                         ("BSC DEX / 聚合器", ["USDC → BNB → meme"], "gray"),
                         ("用户 BSC 地址", ["收到 meme"], "green")])
    down(f, a[0], a[1], "存款（用户付 SOL gas，\n或 gasless 计入报价）", c="blue")
    down(f, a[1], a[2], "触发填单", c="blue", dash=True, dx=44)
    down(f, a[1], a[2], "", c="orange", dash=True, dx=230)
    f.text(a[1].l + 222, (a[1].b + a[2].t) / 2 + 4, "事后回款", size=12, fill="#c2410c", anchor="end", halo="#ffffff")
    down(f, a[2], a[3], "USDC", c="blue")
    down(f, a[3], a[4], "meme", c="blue")
    fees(f, a[1], L, 228, [("Execution", "$0.02 固定 + 目标链 gas", "red"),
                           ("Swap Cost", "DEX 费 + 冲击 + 再平衡", "red"),
                           ("Relay 平台费", "meme 属于长尾币：0.15%", "red"),
                           ("App Fee", "集成方自定 bps", "purple"),
                           ("结算 ≈ $0.005 / 单", "Solver 承担，算进报价", "orange")], label="从 X 里扣掉")

    b = lane(f, R, 140, [("用户 BSC 地址", ["持有 meme"], "green"),
                         ("BSC DEX（源链 swap）", ["meme → USDC"], "gray"),
                         ("Relay Depository · BSC", ["锁定 USDC"], "blue"),
                         ("Solver（Solana 上的库存）", ["支付 USDC − 各项费用"], "teal"),
                         ("用户 Solana 钱包", ["收到 USDC / SOL"], "gray")])
    down(f, b[0], b[1], "需要 BNB gas\n（或 7702 / permit 免 gas）", c="orange")
    down(f, b[1], b[2], "USDC 存款", c="orange")
    down(f, b[2], b[3], "存款事件 → 触发付款", c="orange", dash=True)
    down(f, b[3], b[4], "USDC", c="orange")
    fees(f, b[1], R, 266, [("Swap Cost（源链）", "DEX 费 + 价格冲击", "red")])
    fees(f, b[3], R, 470, [("Execution + 平台费", "$0.02 + gas + bps", "red"),
                           ("App Fee", "集成方自定 bps", "purple")])
    f.text(40, 754, "卖出时“任意币 → USDC”发生在源链：用户要先在 BSC 上完成一次 swap 再存款，比买入多一段链路。",
           size=12.5, fill=SUB, anchor="start")
    return f


# ---------------------------------------------------------------------------
# 图 4  Pump Bridge 架构
# ---------------------------------------------------------------------------
def fig_pump_arch():
    f = Fig("04-pump-arch", 1240, 850, "图 4  Pump Bridge 架构（根据链上交易还原）",
            "蓝色 = 买入（用 USDC）　橙色 = 卖出　所有 gas 都由 Pump 付；金库余额为 2026-10-26 链上数据")
    f.group(40, 96, 1160, 112, "客户端", "gray")
    fe = f.box(80, 134, 300, 58, "Pump.fun 前端", ["下单 · 一键卖出"], c="gray")
    ew = f.box(470, 134, 340, 58, "内嵌钱包（第三方登录）", ["同一身份：Solana 地址 + EVM 地址"], c="blue")
    f.box(900, 134, 260, 58, "插件钱包", ["不支持跨链"], c="gray", ghost=True)

    f.group(40, 236, 1160, 176, "Pump 后端（中心化 · 自己就是唯一的 Solver）", "purple", lpos="tr")
    q = f.box(70, 276, 200, 112, "报价引擎", ["0x / Jupiter 报价", "算平台费和 gas"], c="purple")
    o = f.box(295, 276, 200, 112, "订单与对账", ["orderId 贯穿两条链", "内部账本"], c="purple")
    e = f.box(520, 276, 200, 112, "执行器（热钱包）", ["Solana 付费：FHpc…", "Solana 出金：6aQt…", "BSC 代付 gas：0x6733…"], c="purple")
    r = f.box(745, 276, 200, 112, "再平衡", ["CCTP / CEX", "批量、异步"], c="teal")
    k = f.box(970, 276, 200, 112, "风控", ["限额 · 滑点", "金库水位告警"], c="red")
    f.arrow([(170, fe.b), (170, q.t)], label="下单", at=(178, 224), anchor="start")
    f.arrow([(620, ew.b), (620, e.t)], label="服务端签名（无弹窗）", at=(628, 224), anchor="start")
    f.arrow([(q.r, 332), (o.l, 332)])
    f.arrow([(o.r, 332), (e.l, 332)])

    f.group(40, 476, 580, 296, "Solana", "blue")
    f.group(640, 476, 560, 296, "BSC（同样部署在 Base / Robinhood / Ink / Arc …）", "blue", lpos="bl")
    us = f.box(70, 530, 210, 62, "用户 CS4Um…", ["Solana 地址"], c="green")
    pg = f.box(350, 530, 240, 62, "Pump Bridge 程序", ["Dsug6J…"], c="purple")
    fa = f.box(70, 660, 210, 62, "平台费账户 KfHbT5…", ["收 0.45%"], c="red")
    sv = f.box(350, 660, 240, 62, "USDC 金库 5Zs2Gi…", ["≈ 77 万 USDC"], c="purple")
    ub = f.box(670, 530, 230, 62, "用户 0x3b7d…", ["EIP-7702 已委托"], c="green")
    bv = f.box(960, 530, 210, 62, "金库 0x836b…", ["≈ 76.6 万 USDC · 仅执行器可调"], c="purple", ssize=11)
    ag = f.box(960, 660, 210, 62, "0x 聚合器", ["→ Pancake V3 池子"], c="gray")

    f.arrow([(545, e.b), (545, 450), (455, 450), (455, pg.t)], c="blue")
    f.text(447, 508, "① 入金", size=12, fill="#1d4ed8", anchor="end", halo="#ffffff")
    f.arrow([(575, e.b), (575, 466), (510, 466), (510, pg.t)], c="orange")
    f.text(518, 508, "⑥ 出金", size=12, fill="#c2410c", anchor="start", halo="#ffffff")
    f.arrow([(680, e.b), (680, 450), (1065, 450), (1065, bv.t)], c="blue", label="② buy(orderId)", at=(880, 443))
    f.arrow([(650, e.b), (650, 466), (785, 466), (785, ub.t)], c="orange")
    f.text(793, 508, "④ 7702：approve + sell", size=12, fill="#c2410c", anchor="start", halo="#ffffff")
    f.arrow([(us.r, 550), (pg.l, 550)], c="blue", label="① USDC", at=(315, 543))
    f.arrow([(pg.l, 575), (us.r, 575)], c="orange", label="⑥ 净额", at=(315, 593))
    f.arrow([(470, pg.b), (470, sv.t)], c="gray", both=True, label="入账 / 出账", at=(480, 630), anchor="start")
    f.arrow([(sv.l, 691), (fa.r, 691)], c="orange", label="0.45%", at=(315, 684))
    f.arrow([(bv.l, 550), (ub.r, 550)], c="blue", label="③ meme", at=(930, 543))
    f.arrow([(ub.r, 575), (bv.l, 575)], c="orange", label="⑤ meme", at=(930, 593))
    f.arrow([(1065, bv.b), (1065, ag.t)], both=True, label="swap", at=(1075, 630), anchor="start")
    f.arrow([(470, sv.b), (470, 804), (1185, 804), (1185, 561), (bv.r, 561)], c="teal", dash=True, both=True)
    f.text(830, 798, "链下再平衡：两边金库的净差额通过 CCTP / CEX 批量调拨", size=12, fill="#0f766e", halo="#ffffff")
    return f


# ---------------------------------------------------------------------------
# 图 5  Pump Bridge 时序（第一次实测）
# ---------------------------------------------------------------------------
def fig_pump_seq():
    parts = [("u", "用户", "内嵌钱包", "gray"), ("p", "Pump 后端", "执行器", "purple"),
             ("fee", "平台费账户", "KfHbT5…", "red"), ("sv", "Solana 金库", "Dsug6J / 5Zs2Gi", "blue"),
             ("bv", "BSC 金库", "0x836b…", "purple"), ("dex", "0x 聚合器", "Pancake V3", "gray"),
             ("ub", "用户 BSC 地址", "0x3b7d…", "green")]
    f = Seq("05-pump-seq", 1240, 1180, "图 5  Pump Bridge 买入 + 卖出时序（第一次实测：USDC 进、USDC 出）",
            "实线 = 调用 / 资金，虚线 = 返回 / 事件；金额全部来自链上交易", parts, life_end=1060)
    f.begin("买入 · 2026-10-23 05:05:06（两条链的交易在同一秒）", "blue")
    f.m("u", "p", "① 买 1 USDC 的 BSC meme")
    f.m("p", "sv", "② 入金：用户签名 + FHpc… 付费", c="blue")
    f.m("u", "sv", "1.000000 USDC", c="blue")
    f.m("sv", "p", "确认（约 0.4 s）", dash=True)
    f.m("p", "bv", "③ buy(orderId, 0.9455 USDC)", c="blue")
    f.m("bv", "dex", "④ USDC → WBNB → meme", c="blue")
    f.m("dex", "bv", "66.806 meme", dash=True)
    f.m("bv", "ub", "⑤ 66.806 meme", c="blue")
    f.note("u", "ub", "买入完成：只有一笔 Solana 交易 + 一笔 BSC 交易", c="green")
    f.end()
    f.begin("卖出 · 05:11:23（BSC）→ 05:11:24（Solana）", "orange")
    f.m("u", "p", "⑥ 一键卖出")
    f.m("p", "ub", "⑦ 7702 交易：approve + sell（0x6733… 付 gas）", c="orange")
    f.m("ub", "bv", "⑧ 66.806 meme", c="orange")
    f.m("bv", "dex", "⑨ meme → USDC", c="orange")
    f.m("dex", "bv", "0.921972 USDC（留在金库）", dash=True)
    f.m("bv", "p", "Sold 事件", dash=True)
    f.m("p", "sv", "⑩ 出金指令（6aQt… 签名）", c="orange")
    f.m("sv", "u", "⑪ 0.899372 USDC", c="orange")
    f.m("sv", "fee", "⑫ 0.004148（0.45%）", c="orange")
    f.note("sv", "sv", "0.018452 = BSC gas", ["实报实销，留在金库"], c="yellow", h=46, pad=0.5)
    f.end()
    f.cards([("要点 1：只有两笔链上交易", "没有 Oracle / 结算链 / MPC", "blue"),
             ("要点 2：两边 gas 全由 Pump 付", "Solana：FHpc… / 6aQt…　BSC：0x6733…", "purple"),
             ("要点 3：收费 = 0.45% + gas 实报实销", "卖出已逐位对上账", "red")], y=1090)
    return f


# ---------------------------------------------------------------------------
# 图 6  Pump Bridge 资金流转（第一次实测）
# ---------------------------------------------------------------------------
def fig_pump_flow():
    f = Fig("06-pump-flow", 1240, 830, "图 6  Pump Bridge 资金流转（第一次实测：1 USDC 买入，再全部卖出）",
            "实线 = 资金移动　虚线 = Pump 内部记账 / 事件　红色 = Pump 扣的钱　灰色 = Pump 代付的 gas")
    L, R = 40, 650
    f.group(L, 98, LANE_W, 640, "买入 · Solana USDC → BSC meme", "blue")
    f.group(R, 98, LANE_W, 640, "卖出 · BSC meme → Solana USDC", "orange")
    a = lane(f, L, 140, [("用户 Solana 钱包 CS4Um…", ["付出 1.000000 USDC"], "gray"),
                         ("Pump Solana 金库 5Zs2Gi…", ["+1.000000 USDC"], "purple"),
                         ("Pump BSC 金库 0x836b…", ["拿出 0.945500 USDC"], "purple"),
                         ("0x 聚合器 → Pancake V3", ["USDC → WBNB → meme"], "gray"),
                         ("用户 BSC 地址 0x3b7d…", ["收到 66.806 meme"], "green")])
    down(f, a[0], a[1], "1.000000 USDC\n（FHpc… 代付 SOL 网络费）", c="blue")
    down(f, a[1], a[2], "内部账本 orderId 0x13cd…\n（两笔交易同一秒）", c="purple", dash=True)
    down(f, a[2], a[3], "0.945500 USDC", c="blue")
    down(f, a[3], a[4], "66.806 meme", c="blue")
    fees(f, a[0], L, 150, [("Solana 网络费 $0.0016", "FHpc… 代付", "gray")])
    fees(f, a[1], L, 262, [("留在金库 0.054500", "5.45%：0.45% + 约 $0.05（推测）", "red")])
    fees(f, a[2], L, 392, [("BSC gas ≈ $0.014", "0x6733… 代付", "gray")])

    b = lane(f, R, 140, [("用户 BSC 地址 0x3b7d…", ["66.806 meme"], "green"),
                         ("0x 聚合器 → Pancake V3", ["meme → WBNB → USDC"], "gray"),
                         ("Pump BSC 金库 0x836b…", ["收回 0.921972 USDC"], "purple"),
                         ("Pump Solana 金库 5Zs2Gi…", ["拿出 0.921972 USDC"], "purple"),
                         ("用户 Solana 钱包 CS4Um…", ["收到 0.899372 USDC"], "gray")])
    down(f, b[0], b[1], "7702：approve + sell\n（0x6733… 付 gas）", c="orange")
    down(f, b[1], b[2], "0.921972 USDC", c="orange")
    down(f, b[2], b[3], "Sold 事件（约 1 s 后出金）", c="purple", dash=True)
    down(f, b[3], b[4], "0.899372 USDC（6aQt… 签名）", c="orange")
    fees(f, b[0], R, 150, [("BSC gas ≈ $0.018", "Pump 先付，卖出时扣回", "gray")])
    fees(f, b[3], R, 506, [("平台费 0.004148", "0.45% → KfHbT5…", "red"),
                           ("gas 实报实销 0.018452", "与链上 gas 完全相等", "red")])
    f.box(40, 756, 1180, 50, "来回：1.000000 → 0.899372 USDC，损耗 10.06%",
          ["Pump 收约 0.077（买入 0.0545 + 卖出 0.0226）；两次 DEX 成本 + 6 分钟行情约 0.0235；金额越小，固定费占比越高"],
          c="yellow", tsize=13.5, ssize=11.5)
    return f


# ---------------------------------------------------------------------------
# 图 7  第二次实测：SOL 买走 Relay，卖出走 Pump 并换回 SOL
# ---------------------------------------------------------------------------
def fig_second_test():
    f = Fig("07-second-test", 1240, 900, "图 7  第二次实测：用 SOL 买 → 走 Relay；卖出 → 走 Pump Bridge 并换回 SOL",
            "左：Relay 官方 API 的费用明细（橙 = Relay / Solver 拿走，紫 = Pump 拿到，绿 = 返还）　右：链上逐位对账")
    L, R = 40, 650
    f.group(L, 98, LANE_W, 712, "买入 · 0.009888 SOL → BSC meme（Relay）", "teal")
    f.group(R, 98, LANE_W, 712, "卖出 · BSC meme → SOL（Pump Bridge + Jupiter）", "orange")
    a = lane(f, L, 140, [("用户 Solana 钱包", ["0.009888 SOL ≈ $0.9999 · 自付网络费"], "gray"),
                         ("Relay Depository 99vQwt…", ["锁定 0.009888 SOL"], "blue"),
                         ("Relay Solver 0xcc4b…", ["垫付 0.924174 USDC + BSC gas $0.035"], "teal"),
                         ("Relay Router → KyberSwap", ["USDC → USDT → BNB → meme"], "gray"),
                         ("用户 BSC 地址", ["收到 1505.79 meme ≈ $0.9246"], "green")])
    down(f, a[0], a[1], "DepositNative", c="blue")
    down(f, a[1], a[2], "存款事件（约 1 s 后填单）", c="blue", dash=True)
    down(f, a[2], a[3], "0.924174 USDC", c="blue")
    down(f, a[3], a[4], "1505.79 meme", c="blue")
    fees(f, a[1], L, 182, [("gas $0.0582", "实际链上只花 $0.035", "orange"),
                           ("固定费 $0.0200", "Execution fixed", "orange"),
                           ("换币价差 $0.0042", "SOL → USDC", "orange"),
                           ("Relay 平台费 $0.0015", "15 bps", "orange"),
                           ("Pump App Fee $0.0015", "15 bps", "purple"),
                           ("返还 +$0.0074", "Pump 补贴 $0.0015 + 正滑点 $0.0058", "green")],
         h=44, gap=8, label="Relay 报价扣费")
    f.box(L + 22, 728, 520, 58, "损耗 $0.0753（7.53%）", ["Relay + Solver 拿走约 $0.072，Pump 净收入约等于 0"],
          c="red", tsize=13.5, ssize=11.5)

    b = lane(f, R, 140, [("用户 BSC 地址", ["1505.79 meme"], "green"),
                         ("Pump BSC 金库 0x836b…", ["经 0x 换得 0.923175 USDC，留在金库"], "purple"),
                         ("Pump Solana 金库 5Zs2Gi…", ["AdminDebit × 2"], "purple"),
                         ("Jupiter（经 Tessera V 池）", ["0.899776 USDC → 0.008905774 SOL"], "gray"),
                         ("用户 Solana 钱包", ["收到 0.008906913 SOL ≈ $0.8999"], "gray")])
    down(f, b[0], b[1], "Pump 代付 gas（7702 已生效，\n这次是普通 type 2 交易）", c="orange")
    down(f, b[1], b[2], "Sold 事件（约 1 s 后出金）", c="purple", dash=True)
    down(f, b[2], b[3], "0.899776 USDC（同一笔交易）", c="orange")
    down(f, b[3], b[4], "SOL（Pump 补了 1139 lamports）", c="orange")
    fees(f, b[2], R, 360, [("平台费 0.004154", "0.45% → KfHbT5…", "red"),
                           ("gas 实报实销 0.019245", "BSC 卖出 gas，留在金库", "red"),
                           ("Jupiter 换币成本", "从用户净额里出", "gray")])
    f.box(R + 22, 728, 520, 58, "卖出规则和第一次完全一样", ["0.45% + gas 实报实销；要 SOL 就在出金交易里用 Jupiter 换"],
          c="yellow", tsize=13.5, ssize=11.5)
    f.text(40, 842, "结论：Pump 现在是混合路由。用 USDC 买走 Pump Bridge，用 SOL 买仍然走 Relay，卖出一律走 Pump Bridge。",
           size=13, fill="#1f2937", anchor="start", weight="600")
    f.text(40, 868, "走 Relay 时 Pump 几乎赚不到钱，走自营时能收 0.45% + 约 $0.05，这是 Pump 把路由收回自己手里的直接原因。",
           size=12.5, fill=SUB, anchor="start")
    return f


# ---------------------------------------------------------------------------
# 图 8  用户路径对比
# ---------------------------------------------------------------------------
def fig_path_compare():
    f = Fig("08-path-compare", 1200, 470, "图 8  用户等待的路径：Relay vs Pump Bridge",
            "同一列是同一个阶段；虚线空框 = Pump 去掉的环节；红字 = 失败主要发生的位置")
    cols = [200, 362, 524, 686, 848, 1010]
    w = 146

    def row(y, items):
        out = []
        for x, it in zip(cols, items):
            t, s, c, ghost = it
            out.append(f.box(x, y, w, 66, t, s, c=c, tsize=13.5, ssize=11.5, ghost=ghost))
        for b1, b2 in zip(out, out[1:]):
            f.arrow([(b1.r, b1.cy), (b2.l, b2.cy)], dash=b2 is out[3] and items[3][3])
        return out

    f.text(40, 140, "Relay", size=18, weight="700", anchor="start")
    f.text(40, 164, "典型 3.88 s", size=12.5, fill=SUB, anchor="start")
    f.text(40, 184, "失败率 11.2%", size=12.5, fill="#b91c1c", anchor="start")
    r = row(116, [("报价 API", ["Relay 服务"], "yellow", False), ("用户签名", ["插件钱包要弹窗"], "gray", False),
                  ("源链存款确认", ["Depository"], "blue", False), ("Solver 发现 + 模拟", ["第三方决策"], "teal", False),
                  ("Solver 填单", ["目标链 swap"], "teal", False), ("到账", ["meme"], "green", False)])
    f.text(r[3].cx, r[3].b + 20, "报价过期 / 滑点 → 退款", size=12, fill="#b91c1c", weight="600")
    f.group(cols[3] - 10, 214, cols[5] + w - cols[3] + 20, 46, "", "orange")
    f.text(cols[3] + 8, 242, "事后：Oracle 证明 → Hub 记账 → MPC 提款 → Solver 回款（异步）", size=12.5,
           fill="#c2410c", anchor="start", weight="600")

    f.text(40, 320, "Pump Bridge", size=18, weight="700", anchor="start")
    f.text(40, 344, "典型 1.95 s", size=12.5, fill=SUB, anchor="start")
    f.text(40, 364, "失败率 0.9%", size=12.5, fill="#2f7d32", anchor="start")
    p = row(296, [("报价", ["Pump 后端"], "purple", False), ("服务端签名", ["内嵌钱包，无弹窗"], "gray", False),
                  ("Solana 入金确认", ["Pump 金库"], "blue", False), ("没有第三方 Solver", ["Pump 自己执行"], "gray", True),
                  ("BSC 金库执行", ["Pump 自有 USDC"], "purple", False), ("到账", ["meme"], "green", False)])
    f.group(cols[3] - 10, 380, cols[5] + w - cols[3] + 20, 46, "", "teal")
    f.text(cols[3] + 8, 408, "事后：两边金库的净差额通过 CCTP / CEX 批量再平衡（异步）", size=12.5,
           fill="#0f766e", anchor="start", weight="600")
    f.text(40, 404, "Pump 去掉的是唯一需要", size=12.5, fill=SUB, anchor="start")
    f.text(40, 424, "第三方决策的环节", size=12.5, fill=SUB, anchor="start")
    return f


# ---------------------------------------------------------------------------
# 图 9  我们的系统架构
# ---------------------------------------------------------------------------
def fig_our_arch():
    f = Fig("09-our-arch", 1260, 860, "图 9  我们的系统架构：自营库存桥为主 + Relay 兜底",
            "蓝色 = 跨链买卖（第三方登录用户）　灰色 = 插件钱包本链交易　青色 = 再平衡　黄色虚线 = 回退到 Relay")
    f.group(40, 96, 1160, 112, "客户端", "gray")
    pw = f.box(80, 134, 320, 58, "插件钱包用户", ["Phantom / MetaMask … · 只买本链代币"], c="gray")
    ew = f.box(480, 134, 340, 58, "第三方登录用户", ["邮箱 / Google / X · 可以跨链买币"], c="blue")

    f.group(40, 236, 1160, 284, "我们的后端", "purple")
    q = f.box(70, 276, 240, 70, "报价 / 路由引擎", ["0x · 1inch · OKX · Jupiter"], c="purple")
    rt = f.box(350, 276, 240, 70, "跨链路由器", ["自营库存够吗？"], c="yellow")
    od = f.box(630, 276, 240, 70, "订单服务", ["orderId 状态机 · 幂等"], c="purple")
    rk = f.box(910, 276, 240, 70, "风控", ["限额 · 滑点 · 黑名单"], c="red")
    km = f.box(70, 410, 240, 84, "托管密钥服务", ["MPC / TEE / HSM · 不可导出", "只签白名单合约"], c="red")
    ex = f.box(350, 410, 240, 84, "执行器集群", ["每条链一个 gas 热钱包", "nonce 管理 · 失败重试"], c="purple")
    lg = f.box(630, 410, 240, 84, "内部账本", ["日终对账：金库 = 账本"], c="purple")
    rb = f.box(910, 410, 240, 84, "再平衡服务", ["水位监控 · 调拨决策"], c="teal")

    f.group(40, 582, 800, 200, "各条链（Solana / BSC / Base / ETH …）", "blue")
    dx = f.box(70, 640, 220, 70, "DEX / 聚合器", ["本链 swap"], c="gray")
    ua = f.box(330, 640, 230, 70, "用户托管地址", ["EVM：7702 委托", "Solana：我们付网络费"], c="green")
    vt = f.box(600, 640, 220, 70, "Bridge 金库合约", ["USDC 库存 · 只许执行器调", "暂停开关 · 多签"], c="purple", ssize=11)
    f.group(880, 582, 320, 200, "外部通道", "gray")
    cc = f.box(910, 624, 260, 56, "CCTP / CEX", ["金库之间调拨 USDC"], c="teal")
    rl = f.box(910, 702, 260, 56, "Relay（兜底）", ["长尾链 · 库存不足 · 充值提现"], c="yellow")

    f.arrow([(pw.l, 163), (24, 163), (24, 675), (dx.l, 675)])
    f.text(18, 420, "本链买卖：自己签名、自己付 gas", size=12, fill=SUB, halo="#ffffff", rotate=-90)
    f.arrow([(560, ew.b), (560, 220), (190, 220), (190, q.t)], c="blue", label="下单", at=(198, 254), anchor="start")
    f.arrow([(q.r, 311), (rt.l, 311)], c="blue")
    f.arrow([(rt.r, 311), (od.l, 311)], c="blue", label="是", at=(610, 303))
    f.arrow([(470, rt.t), (470, 254), (1222, 254), (1222, 730), (rl.r, 730)], c="yellow", dash=True,
            )
    f.text(1232, 480, "否：走 Relay", size=12, fill="#b7791f", halo="#ffffff", rotate=90)
    f.arrow([(750, od.b), (750, 378), (470, 378), (470, ex.t)], c="blue", label="执行", at=(610, 371))
    f.arrow([(ex.l, 452), (km.r, 452)], c="red", both=True, label="签名", at=(330, 444))
    f.arrow([(420, ex.b), (420, ua.t)], c="blue", label="7702 / 代付 gas", at=(428, 560), anchor="start")
    f.arrow([(540, ex.b), (540, 540), (700, 540), (700, vt.t)], c="blue", label="buy / sell / payout", at=(620, 533))
    f.arrow([(vt.l, 675), (ua.r, 675)], c="blue", label="代币", at=(580, 668))
    f.arrow([(710, vt.b), (710, 750), (180, 750), (180, dx.b)], c="blue", both=True, label="swap", at=(445, 744))
    f.arrow([(790, vt.t), (790, lg.b)], dash=True, label="事件", at=(798, 560), anchor="start")
    f.arrow([(1040, rb.b), (1040, cc.t)], c="teal", label="调拨", at=(1048, 560), anchor="start")
    f.arrow([(cc.l, 652), (vt.r, 652)], c="teal", dash=True, both=True)
    f.text(850, 640, "USDC", size=11.5, fill="#0f766e", halo="#ffffff")
    f.text(40, 830, "对延迟敏感的跨链买卖走自营金库；长尾链、充值提现、金库调拨这些不急的事交给 Relay / CCTP / CEX。",
           size=12.5, fill=SUB, anchor="start")
    return f


# ---------------------------------------------------------------------------
# 图 10  我们的跨链买入时序
# ---------------------------------------------------------------------------
def fig_our_seq():
    parts = [("u", "用户", "第三方登录", "gray"), ("s", "后端", "报价·路由·订单", "purple"),
             ("k", "托管密钥", "MPC / TEE", "red"), ("e", "执行器", "代付 gas", "purple"),
             ("va", "Base 金库", "源链", "blue"), ("vb", "BSC 金库", "目标链", "blue"),
             ("d", "BSC 聚合器", "DEX", "gray"), ("ub", "用户 BSC 地址", "托管", "green")]
    f = Seq("10-our-seq", 1240, 1000, "图 10  我们的跨链买入时序（例：用 Base 上的 10 USDC 买 BSC meme）",
            "实线 = 调用 / 资金，虚线 = 返回 / 事件；红框 = 失败分支", parts, life_end=880)
    f.m("u", "s", "① 用 10 USDC（Base）买 BSC meme")
    f.note("s", "s", "报价 · 算费 · 查 BSC 金库水位 · 风控", c="yellow", pad=1.3)
    f.m("s", "k", "② 请求签名：approve + deposit(orderId)", c="red")
    f.m("k", "s", "签名（只签白名单合约）", c="red", dash=True)
    f.m("s", "e", "③ 提交")
    f.m("e", "va", "④ 7702 批量交易（代付 Base gas）", c="blue")
    f.m("va", "s", "Deposited(orderId, 10 USDC)", dash=True)
    f.m("s", "e", "⑤ 目标链执行")
    f.m("e", "vb", "⑥ buy(orderId, 10 − 费用)", c="blue")
    f.m("vb", "d", "⑦ USDC → meme", c="blue")
    f.m("d", "vb", "meme", dash=True)
    f.m("vb", "ub", "⑧ meme 到账", c="blue")
    f.note("u", "ub", "目标：1~2 秒完成，失败率 < 1%", c="green")
    f.begin("alt 目标链执行失败（滑点 / 流动性 / 金库余额不足）", "red", "s", "vb")
    f.m("e", "va", "⑨ refund(orderId)", c="red")
    f.m("va", "s", "Refunded：全额退回用户 Base 地址", c="red", dash=True)
    f.end()
    f.cards([("安全点 1：密钥只签白名单", "金库、聚合器、7702 合约以外一律拒签", "red"),
             ("安全点 2：金库限额 + 暂停", "单笔 / 单日上限，提款要多签 + 时间锁", "red"),
             ("安全点 3：失败必退款", "orderId 幂等，状态机兜底", "red")], y=910)
    return f


# ---------------------------------------------------------------------------
# 图 11  我们的资金流转
# ---------------------------------------------------------------------------
def fig_our_flow():
    f = Fig("11-our-flow", 1240, 960, "图 11  我们的资金流转与收费",
            "实线 = 资金移动　虚线 = 内部记账 / 事件　红色 = 我们收的钱　灰色 = 用户承担的市场成本")
    L, R = 40, 650
    f.group(L, 98, LANE_W, 640, "跨链买入 · Base USDC → BSC meme", "blue")
    f.group(R, 98, LANE_W, 640, "跨链卖出 · BSC meme → 任意已支持的链", "orange")
    a = lane(f, L, 140, [("用户 Base 地址", ["付出 10 USDC · gas 0"], "gray"),
                         ("Base 金库", ["+10 USDC"], "purple"),
                         ("BSC 金库", ["拿出 10 − 费用"], "purple"),
                         ("BSC 聚合器", ["USDC → meme"], "gray"),
                         ("用户 BSC 地址", ["收到 meme"], "green")])
    down(f, a[0], a[1], "10 USDC\n（7702：approve + deposit）", c="blue")
    down(f, a[1], a[2], "内部账本 orderId", c="purple", dash=True)
    down(f, a[2], a[3], "10 − 费用", c="blue")
    down(f, a[3], a[4], "meme", c="blue")
    fees(f, a[1], L, 252, [("平台费 x bps", "→ 费用账户", "red"),
                           ("gas 实报实销", "源链 + 目标链", "red")])
    fees(f, a[3], L, 524, [("DEX 费 + 价格冲击", "用户承担", "gray")])

    b = lane(f, R, 140, [("用户 BSC 地址", ["持有 meme"], "green"),
                         ("BSC 聚合器", ["meme → USDC"], "gray"),
                         ("BSC 金库", ["+USDC"], "purple"),
                         ("收款链金库", ["Base / Solana / …"], "purple"),
                         ("用户收款地址", ["USDC 或原生币"], "gray")])
    down(f, b[0], b[1], "7702：approve + sell\n（我们代付 gas）", c="orange")
    down(f, b[1], b[2], "USDC", c="orange")
    down(f, b[2], b[3], "Sold 事件", c="purple", dash=True)
    down(f, b[3], b[4], "净额", c="orange")
    fees(f, b[3], R, 480, [("平台费 x bps", "→ 费用账户", "red"),
                           ("gas 实报实销", "目标链卖出 gas", "red"),
                           ("要原生币就换", "同一笔交易里走 Jupiter / 0x", "gray")])

    f.group(40, 760, 1180, 120, "插件钱包 · 只买本链代币（不经过金库）", "gray")
    p1 = f.box(70, 800, 240, 56, "插件钱包", ["自己签名、自己付 gas"], c="gray")
    p2 = f.box(480, 800, 260, 56, "本链 DEX 聚合器", ["报价里带上我们的 fee 参数"], c="gray")
    p3 = f.box(930, 800, 240, 56, "我们的费用账户", ["聚合器原生的 integrator fee"], c="red")
    f.arrow([(p1.r, 818), (p2.l, 818)], label="swap 交易", at=(395, 810))
    f.arrow([(p2.l, 840), (p1.r, 840)], label="代币", at=(395, 858))
    f.arrow([(p2.r, 828), (p3.l, 828)], c="red", label="平台费", at=(835, 820))
    f.text(40, 912, "两边金库的净差额由再平衡服务通过 CCTP / CEX 批量调拨，成本算进平台费。卖出的收费方式参考 Pump：bps + gas 实报实销。",
           size=12.5, fill=SUB, anchor="start")
    f.text(40, 934, "小额订单要设最低费用或最低下单金额，否则固定成本会吃掉利润（Pump 1 USDC 订单的来回损耗约 10%）。",
           size=12.5, fill=SUB, anchor="start")
    return f


# ---------------------------------------------------------------------------
# 图 12  路由决策
# ---------------------------------------------------------------------------
def fig_routing():
    f = Fig("12-routing", 1000, 900, "图 12  跨链订单路由决策",
            "从上往下依次判断；任何一步不满足都不会出现“买不了”，只会走 Relay 或拆单")
    st = f.box(330, 100, 340, 58, "跨链订单：A 链 → B 链，金额 M", [], c="gray")
    d1 = f.diamond(500, 238, 380, 96, "A、B 都有我们的金库？")
    d2 = f.diamond(500, 378, 380, 96, "B 金库余额 ≥ M × 安全系数？", size=13)
    d3 = f.diamond(500, 518, 380, 96, "限额 / 风控通过？")
    sb = f.box(370, 610, 260, 58, "走自营库存桥", ["1~2 s · 收 bps + gas"], c="purple")
    d4 = f.diamond(500, 748, 380, 96, "目标链执行成功？")
    rl = f.box(760, 260, 210, 96, "走 Relay", ["服务端代签 · gasless", "慢一点，但一定能买"], c="yellow")
    rj = f.box(40, 488, 190, 60, "拒绝或拆单", [], c="red")
    rf = f.box(760, 718, 210, 60, "源链金库自动退款", [], c="red")
    ok = f.box(410, 830, 180, 50, "完成", [], c="green")
    f.arrow([(500, st.b), (500, d1.t)])
    f.arrow([(500, d1.b), (500, d2.t)], c="green", label="是", at=(512, 312), anchor="start")
    f.arrow([(500, d2.b), (500, d3.t)], c="green", label="是", at=(512, 452), anchor="start")
    f.arrow([(500, d3.b), (500, sb.t)], c="green", label="是", at=(512, 590), anchor="start")
    f.arrow([(500, sb.b), (500, d4.t)])
    f.arrow([(500, d4.b), (500, ok.t)], c="green", label="是", at=(512, 818), anchor="start")
    f.arrow([(d1.r, 238), (865, 238), (865, rl.t)], c="red", label="否", at=(720, 230))
    f.arrow([(d2.r, 378), (865, 378), (865, rl.b)], c="red", label="否", at=(720, 370))
    f.arrow([(d3.l, 518), (rj.r, 518)], c="red", label="否", at=(270, 510))
    f.arrow([(d4.r, 748), (rf.l, 748)], c="red", label="否", at=(725, 740))
    return f


FIGS = [fig_relay_arch, fig_relay_seq, fig_relay_flow, fig_pump_arch, fig_pump_seq, fig_pump_flow,
        fig_second_test, fig_path_compare, fig_our_arch, fig_our_seq, fig_our_flow, fig_routing]


def main():
    png_dir = os.path.join(OUT, "png")
    os.makedirs(png_dir, exist_ok=True)
    has_rsvg = shutil.which("rsvg-convert") is not None
    for fn in FIGS:
        f = fn()
        path = f.save(OUT)
        if has_rsvg:
            subprocess.run(["rsvg-convert", "-z", "2", "-o", os.path.join(png_dir, f.name + ".png"), path], check=True)
        print("ok", f.name)


if __name__ == "__main__":
    main()
