"""
svgkit —— 生成统一风格的架构图 / 时序图 / 资金流转图（纯 SVG，无依赖）

风格约定（参考 docs 里的示例图）：
  - 白底；圆角框 = 浅色填充 + 同色系描边；虚线框 = 分组 / 异步区域
  - 每条箭头都带文字标签；实线 = 调用 / 资金移动，虚线 = 返回 / 事件 / 读取
  - 时序图：参与者头部 + 虚线生命线 + 带圈编号消息 + alt/par 框 + 底部要点卡片

用法：见 gen.py。所有坐标都是 SVG 用户坐标（viewBox），输出时按宽度自适应缩放。
"""
import html
import os
import sys

FONT = "PingFang SC, Hiragino Sans GB, Noto Sans SC, Microsoft YaHei, Source Han Sans SC, sans-serif"
INK = "#1f2937"     # 主文字
SUB = "#4b5563"     # 副文字
MUTED = "#6b7280"   # 弱化文字 / 灰色线条

# 调色板：name -> (填充, 描边, 分组底色)
PAL = {
    "gray":   ("#f3f4f6", "#6b7280", "#fafafa"),
    "yellow": ("#fdf3d7", "#b7791f", "#fffcf2"),
    "purple": ("#efeafd", "#6d28d9", "#fbf9ff"),
    "orange": ("#fde8dc", "#c2410c", "#fffaf6"),
    "teal":   ("#dcf5ef", "#0f766e", "#f6fcfa"),
    "green":  ("#e3f5dc", "#2f7d32", "#f7fcf5"),
    "red":    ("#fde7e7", "#b91c1c", "#fff8f8"),
    "blue":   ("#e8effc", "#1d4ed8", "#f6f9ff"),
}


def tw(s, size):
    """粗略估算文字宽度（像素），用于检查文字是否溢出框。"""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o >= 0x2E80 or ch in "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯，。：；（）、！？“”":
            w += size
        elif ch in "→←⇄≈−×·…✅":
            w += size * 0.9
        elif ch.isupper():
            w += size * 0.66
        elif ch == " ":
            w += size * 0.3
        else:
            w += size * 0.56
    return w


class B:
    """一个已绘制矩形的几何信息，方便取边缘坐标连箭头。"""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h

    l = property(lambda s: s.x)
    r = property(lambda s: s.x + s.w)
    t = property(lambda s: s.y)
    b = property(lambda s: s.y + s.h)
    cx = property(lambda s: s.x + s.w / 2)
    cy = property(lambda s: s.y + s.h / 2)


class Fig:
    def __init__(self, name, w, h, title, subtitle=""):
        self.name, self.W, self.H = name, w, h
        self.bg, self.mid, self.els = [], [], []
        self.warnings = []
        self.text(40, 46, title, size=22, weight="700", anchor="start")
        if subtitle:
            self.text(40, 74, subtitle, size=13, fill=SUB, anchor="start")

    # ---------- 基础元素 ----------
    def text(self, x, y, s, size=13, fill=INK, weight="normal", anchor="middle",
             halo=None, rotate=None, layer=None):
        attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
        if weight != "normal":
            attrs += f' font-weight="{weight}"'
        if halo:
            attrs += f' stroke="{halo}" stroke-width="4" stroke-linejoin="round" paint-order="stroke"'
        if rotate is not None:
            attrs += f' transform="rotate({rotate} {x:.1f} {y:.1f})"'
        (layer if layer is not None else self.els).append(f"<text {attrs}>{html.escape(s)}</text>")

    def box(self, x, y, w, h, title, sub=(), c="gray", tsize=14.5, ssize=12,
            ghost=False, layer=None, weight="700"):
        """圆角框：粗体标题 + 若干行副标题。ghost=True 画成虚线空框（表示“这一步不存在”）。"""
        fill, stroke, _ = PAL[c]
        if isinstance(sub, str):
            sub = [sub]
        lay = layer if layer is not None else self.els
        if ghost:
            lay.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="#ffffff" '
                       f'stroke="{stroke}" stroke-width="1.6" stroke-dasharray="6 4"/>')
        else:
            lay.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
                       f'stroke="{stroke}" stroke-width="2"/>')
        lines = [(title, tsize, weight, MUTED if ghost else INK)] + [(s, ssize, "normal", SUB) for s in sub]
        heights = [sz * 1.45 for _, sz, _, _ in lines]
        cur = y + (h - sum(heights)) / 2
        for (s, sz, wt, col), lh in zip(lines, heights):
            self.text(x + w / 2, cur + lh * 0.72, s, size=sz, fill=col, weight=wt, layer=lay)
            cur += lh
            if tw(s, sz) > w - 12:
                self.warnings.append(f"[{self.name}] 文字可能溢出框（框宽 {w}）：{s}")
        if sum(heights) > h - 6:
            self.warnings.append(f"[{self.name}] 框高度不够（{h}）：{title}")
        return B(x, y, w, h)

    def group(self, x, y, w, h, label, c="blue", lsize=13.5, lpos="tl"):
        """虚线分组框，写组名。lpos：tl 左上 / tr 右上 / bl 左下。"""
        _, stroke, gfill = PAL[c]
        self.bg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{gfill}" '
                       f'stroke="{stroke}" stroke-width="1.8" stroke-dasharray="8 5"/>')
        lx, ly, anc = {"tl": (x + 16, y + 24, "start"), "tr": (x + w - 16, y + 24, "end"),
                       "bl": (x + 16, y + h - 14, "start")}[lpos]
        self.text(lx, ly, label, size=lsize, fill=stroke, weight="700", anchor=anc, layer=self.bg)
        return B(x, y, w, h)

    def arrow(self, pts, c="gray", label=None, at=None, anchor="middle", dash=False,
              lsize=12, both=False, width=1.8, lcolor=None, head=True):
        """折线箭头。pts = [(x,y), ...]；label 放在 at=(x,y)。"""
        stroke = MUTED if c == "gray" else PAL[c][1]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        extra = ' stroke-dasharray="6 4"' if dash else ""
        mk = f' marker-end="url(#ah-{c})"' if head else ""
        if both:
            mk += f' marker-start="url(#ah-{c})"'
        self.els.insert(0, f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{width}"'
                           f' stroke-linejoin="round"{extra}{mk}/>')
        if label:
            if at is None:
                (x1, y1), (x2, y2) = pts[0], pts[-1]
                at = ((x1 + x2) / 2, (y1 + y2) / 2 - 7)
            self.text(at[0], at[1], label, size=lsize, fill=lcolor or (SUB if c == "gray" else stroke),
                      anchor=anchor, halo="#ffffff")

    def diamond(self, cx, cy, w, h, s, c="yellow", size=13.5):
        fill, stroke, _ = PAL[c]
        pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
        self.els.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.text(cx, cy + size * 0.35, s, size=size, weight="700")
        if tw(s, size) > w * 0.62:
            self.warnings.append(f"[{self.name}] 菱形文字可能溢出：{s}")
        return B(cx - w / 2, cy - h / 2, w, h)

    def cards(self, items, y, h=64, x0=40, x1=None, gap=24):
        """底部一排要点卡片：items = [(标题, 副标题, 颜色), ...]"""
        x1 = x1 or self.W - 40
        n = len(items)
        w = (x1 - x0 - gap * (n - 1)) / n
        for i, (t, s, c) in enumerate(items):
            self.box(x0 + i * (w + gap), y, w, h, t, [s] if s else [], c=c, tsize=14, ssize=12)

    # ---------- 输出 ----------
    def svg(self):
        markers = []
        for name, (_, stroke, _) in PAL.items():
            col = MUTED if name == "gray" else stroke
            markers.append(
                f'<marker id="ah-{name}" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="10" '
                f'markerHeight="10" markerUnits="userSpaceOnUse" orient="auto-start-reverse">'
                f'<path d="M0,0.8 L10,5 L0,9.2 z" fill="{col}"/></marker>')
        body = "\n".join(self.bg + self.mid + self.els)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.W} {self.H}" '
                f'width="{self.W}" height="{self.H}" font-family="{FONT}" role="img">\n'
                f'<defs>{"".join(markers)}</defs>\n'
                f'<rect width="{self.W}" height="{self.H}" fill="#ffffff"/>\n{body}\n</svg>\n')

    def save(self, outdir):
        path = os.path.join(outdir, self.name + ".svg")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.svg())
        for w in self.warnings:
            print("WARN", w, file=sys.stderr)
        return path


class Seq(Fig):
    """时序图：参与者等分宽度，消息按 self.y 游标自上而下排列。"""

    def __init__(self, name, w, h, title, subtitle, parts, top=104, life_end=None, head_h=54):
        super().__init__(name, w, h, title, subtitle)
        self.keys = [p[0] for p in parts]
        n = len(parts)
        self.slot = (w - 80) / n
        self.X = {k: 40 + self.slot * (i + 0.5) for i, k in enumerate(self.keys)}
        self.top, self.head_h = top, head_h
        self.life_end = life_end or h - 40
        for k, label, sub, c in parts:
            bw = self.slot - 18
            self.box(self.X[k] - bw / 2, top, bw, head_h, label, [sub] if sub else [], c=c, tsize=14, ssize=11.5)
            self.mid.append(f'<line x1="{self.X[k]:.1f}" y1="{top + head_h}" x2="{self.X[k]:.1f}" '
                            f'y2="{self.life_end}" stroke="#c4c8cf" stroke-width="1.4" stroke-dasharray="5 5"/>')
        self.y = top + head_h + 44
        self.frames = []

    def m(self, a, b, label, c="gray", dash=False, dy=40):
        """一条消息 a -> b。"""
        xa, xb = self.X[a], self.X[b]
        off = 3 if xb > xa else -3
        self.arrow([(xa + off, self.y), (xb - off, self.y)], c=c, dash=dash, label=label,
                   at=((xa + xb) / 2, self.y - 8), lsize=12)
        if tw(label, 12) > abs(xb - xa) + self.slot * 0.6:
            self.warnings.append(f"[{self.name}] 消息文字偏长：{label}")
        self.y += dy

    def note(self, a, b, title, sub=(), c="gray", h=34, pad=0.42):
        """跨越参与者 a..b 的说明框。"""
        x1 = min(self.X[a], self.X[b]) - self.slot * pad
        x2 = max(self.X[a], self.X[b]) + self.slot * pad
        self.y -= 12
        self.box(x1, self.y, x2 - x1, h, title, sub, c=c, tsize=12.5, ssize=11.5, weight="600")
        self.y += h + 34

    def begin(self, label, c="blue", a=None, b=None):
        self.bg.append("")  # 占位：外层框先画，内层框后画，避免被盖住
        self.frames.append((label, c, a, b, self.y - 26, len(self.bg) - 1))
        self.y += 30

    def end(self):
        label, c, a, b, y0, idx = self.frames.pop()
        inset = 0.46 if self.frames else 0.48
        x1 = (self.X[a] - self.slot * inset) if a else 52
        x2 = (self.X[b] + self.slot * inset) if b else self.W - 52
        y1 = self.y - 22
        _, stroke, gfill = PAL[c]
        self.bg[idx] = (f'<rect x="{x1:.1f}" y="{y0:.1f}" width="{x2 - x1:.1f}" height="{y1 - y0:.1f}" rx="10" '
                        f'fill="{gfill}" stroke="{stroke}" stroke-width="1.8" stroke-dasharray="8 5"/>')
        self.text(x1 + 14, y0 + 20, label, size=13, fill=stroke, weight="700", anchor="start")
        self.y += 18
