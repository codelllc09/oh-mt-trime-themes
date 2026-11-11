#!/usr/bin/env python3
"""從 V1 生成 V2-contour 主題與等高線鍵面。"""

import argparse
from math import cos, sin, tau

from PIL import Image, ImageDraw

from check_trime import CONTOUR_ID
from gen_calculator import draw_globe, inherit_skin, skin_keys, write_theme_assets
from render_keyboard import DP, SCREEN_W


MAP_PAPER = '#D9C6A1'
CAPS = {
    'glyph': ('#F5EBD0', '#E7D9B2', '#867751'),
    'control': ('#456457', '#365146', '#344D43'),
    'number': ('#E6EAD0', '#D6DFC0', '#78806A'),
    'return': ('#A84530', '#8F3827', '#783C2F'),
}


def case_texture(height):
    scale = 2
    image = Image.new('RGB', (SCREEN_W * scale, height * scale), MAP_PAPER)
    draw = ImageDraw.Draw(image, 'RGBA')
    hills = ((-80, 395, 1.1, .73, .16), (830, 770, 1.3, .83, .36), (855, 138, 1.2, .67, .05))
    for cx, cy, sx, sy, phase in hills:
        for level in range(9):
            radius = 47 + level * 28
            line = []
            for step in range(91):
                angle = tau * step / 90
                shape = 1 + .12 * sin(3 * angle + phase * tau) + .06 * cos(5 * angle - .18 * level)
                x = cx + sx * radius * cos(angle) * shape
                y = cy + sy * radius * sin(angle) * shape
                line.append((round(x * scale), round(y * height / 792 * scale)))
            index_line = level % 4 == 0
            draw.line(line, fill=(139, 104, 62, 168 if index_line else 128),
                      width=(3 if index_line else 2) * scale, joint='curve')
    return image.resize((SCREEN_W, height), Image.Resampling.LANCZOS)


def legend_texture():
    height = 136
    image = Image.new('RGB', (SCREEN_W, height), '#E9DFC4')
    draw = ImageDraw.Draw(image)
    draw.line((0, 2, SCREEN_W, 2), fill='#52604D', width=2)
    draw.line((0, height - 3, SCREEN_W, height - 3), fill='#52604D', width=2)
    for i, x in enumerate(range(14, SCREEN_W, 36)):
        draw.line((x, height - (15 if i % 5 == 0 else 9), x, height - 3), fill='#8B8367', width=2)
    return image


def cap_texture(kind, width, height, pressed):
    w, h = width * 2, height * 2
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    up, down, border = CAPS['control' if kind == 'globe' else kind]
    draw.rounded_rectangle((0, 4, w - 1, h - 1), 15, fill='#8B7951')
    shift = 6 if pressed else 0
    draw.rounded_rectangle((0, shift, w - 1, h - 9 + shift), 15,
                           fill=down if pressed else up, outline=border, width=4)
    if kind == 'number':
        for index, x in enumerate(range(21, w - 18, 51)):
            draw.line((x, shift + 6, x, shift + (17 if index % 2 == 0 else 13)), fill='#A0A986', width=2)
    if kind == 'globe':
        draw_globe(draw, (w / 2, h * .56 + shift), min(w, h) * .21, '#FFF6DA')
    return image.resize((width, height), Image.Resampling.LANCZOS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='檢查生成物是否同步')
    args = parser.parse_args()
    theme = inherit_skin(CONTOUR_ID)
    height = round(theme['style']['keyboard_height'] * DP) + 136
    images = {'case.png': case_texture(height), 'legend.png': legend_texture()}
    skin_keys(theme, images, cap_texture, 'contour')
    write_theme_assets(CONTOUR_ID, theme, images, check=args.check)


if __name__ == '__main__':
    main()
