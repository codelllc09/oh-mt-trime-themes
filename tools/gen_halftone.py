#!/usr/bin/env python3
"""生成 V2-halftone 主題、套色鍵帽和專用粗體英數。"""

import argparse
from io import BytesIO

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from PIL import Image, ImageDraw

from check_trime import HALFTONE_ID, RIME_DIR
from gen_calculator import inherit_skin, skin_keys, write_theme_assets
from render_keyboard import DP, SCREEN_W


PAPER = '#FFF4DB'
INK = '#252025'
CAPS = {
    'glyph': ('#FFF6DF', '#F2DBAA'),
    'control': ('#D3E1E0', '#B9CFCF'),
    'number': ('#FFE1A0', '#EEC57C'),
    'return': ('#BB332D', '#982621'),
}


def case_texture(height):
    image = Image.new('RGB', (SCREEN_W, height), '#E4CFA5')
    draw = ImageDraw.Draw(image)
    for row, y in enumerate(range(4, height, 15)):
        for x in range(4 + row % 2 * 7, SCREEN_W, 15):
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill='#BEA77E')
    return image


def bubble_texture():
    height = 136
    image = case_texture(height)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((11, 10, SCREEN_W - 7, 123), 14, fill='#A4332D')
    draw.rounded_rectangle((6, 5, SCREEN_W - 13, 116), 14, fill=PAPER, outline=INK, width=4)
    draw.polygon(((74, 112), (92, 112), (81, 130)), fill=PAPER)
    draw.line(((74, 116), (81, 130), (92, 116)), fill=INK, width=4, joint='curve')
    return image


def cap_texture(kind, width, height, pressed):
    w, h = width * 2, height * 2
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 10, w - 1, h - 1), 15, fill='#292027')
    shift = 7 if pressed else 0
    colors = CAPS['control' if kind == 'globe' else kind]
    draw.rounded_rectangle((shift, shift, w - 9 + shift, h - 11 + shift),
                           15, fill=colors[int(pressed)], outline=INK, width=8)
    if kind == 'globe':
        x, y = (w - 8) / 2 + shift, h * .56 + shift
        radius = min(w, h) * .21
        color = '#27333E'
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=4)
        draw.ellipse((x - radius * .44, y - radius, x + radius * .44, y + radius), outline=color, width=2)
        draw.line((x - radius, y, x + radius, y), fill=color, width=2)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def latin_font():
    source = RIME_DIR / 'fonts' / 'xuma_latin.ttf'
    with TTFont(source, recalcTimestamp=False) as font:
        options = subset.Options()
        options.name_IDs = [0, 1, 2, 3, 4, 5, 6, 10, 13, 14, 16, 17]
        sub = subset.Subsetter(options=options)
        sub.populate(unicodes=range(0x20, 0x7F))
        sub.subset(font)
        axes = {axis.axisTag: axis.defaultValue for axis in font['fvar'].axes}
        axes['wght'] = 700
        instantiateVariableFont(font, axes, inplace=True)
        family = 'Halftone Key Latin'
        renamed = {1: family, 2: 'Bold', 3: f'{family} Bold', 4: f'{family} Bold',
                   6: 'HalftoneKeyLatin-Bold', 16: family, 17: 'Bold'}
        for record in font['name'].names:
            if record.nameID in renamed:
                record.string = renamed[record.nameID]
        font['name'].setName('Modified from Xuma Key Latin (Roboto), ASCII subset at weight 700.', 10, 3, 1, 0x409)
        font['OS/2'].fsSelection = (font['OS/2'].fsSelection & ~(1 << 6)) | (1 << 5)
        font['head'].macStyle |= 1
        buffer = BytesIO()
        font.save(buffer)
        return buffer.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='檢查生成物是否同步')
    args = parser.parse_args()
    theme = inherit_skin(HALFTONE_ID)
    images = {
        'case.png': case_texture(round(theme['style']['keyboard_height'] * DP)),
        'bubble.png': bubble_texture(),
    }
    skin_keys(theme, images, cap_texture, 'halftone')
    font_path = RIME_DIR / 'fonts' / 'halftone_latin.ttf'
    font = latin_font()
    if args.check:
        if not font_path.is_file() or font_path.read_bytes() != font:
            parser.exit(1, f'{font_path.name} 未同步\n')
    else:
        font_path.write_bytes(font)
    write_theme_assets(HALFTONE_ID, theme, images, check=args.check)


if __name__ == '__main__':
    main()
