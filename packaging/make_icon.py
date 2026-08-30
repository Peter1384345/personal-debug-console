#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成 exe 图标 packaging/app.ico —— 暖金底 + 深色终端提示符 ">_"

只在需要换图标时才跑：
    pip install pillow
    python packaging/make_icon.py
"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "app.ico"

GOLD = (232, 184, 106, 255)
INK = (26, 20, 17, 255)
S = 8  # 超采样倍数，先画大再缩，边缘才不毛


def rounded_rect(draw, box, radius, fill):
    draw.rounded_rectangle(box, radius=radius, fill=fill)


def render(size: int) -> Image.Image:
    n = size * S
    img = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # 底板：圆角金块
    pad = n * 0.04
    rounded_rect(d, [pad, pad, n - pad, n - pad], radius=int(n * 0.22), fill=GOLD)

    # 终端提示符 "> _"（viewBox 0 0 64 64 的等比映射）
    k = n / 64.0
    w = max(int(5 * k), 1)

    def pt(x, y):
        return (x * k, y * k)

    chevron = [pt(17, 23), pt(28, 34), pt(17, 45)]
    d.line(chevron, fill=INK, width=w, joint="curve")
    for p in (chevron[0], chevron[2]):
        r = w / 2
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=INK)

    under = [pt(33, 45), pt(47, 45)]
    d.line(under, fill=INK, width=w)
    for p in under:
        r = w / 2
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=INK)

    return img.resize((size, size), Image.LANCZOS)


def main():
    sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
    base = render(256)
    base.save(
        OUT,
        format="ICO",
        sizes=[(s, s) for s in sizes],
    )
    print(f"✓ {OUT}  ({OUT.stat().st_size / 1024:.1f} KB, {len(sizes)} 个尺寸)")


if __name__ == "__main__":
    main()
