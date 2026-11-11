"""套色印刷與等高線外觀。"""

from io import BytesIO
from math import cos, sin, tau

from PIL import Image, ImageDraw

from check_trime import RIME_DIR
from render_keyboard import DP, SCREEN_W
from .core import draw_globe, skin_keys


PAPER = '#FFF4DB'
INK = '#252025'
HALFTONE_CAPS = {
    'glyph': ('#FFF6DF', '#F2DBAA'),
    'control': ('#D3E1E0', '#B9CFCF'),
    'number': ('#FFE1A0', '#EEC57C'),
    'return': ('#BB332D', '#982621'),
}


def halftone_case(height):
    image = Image.new('RGB', (SCREEN_W, height), '#E4CFA5')
    draw = ImageDraw.Draw(image)
    for row, y in enumerate(range(4, height, 15)):
        for x in range(4 + row % 2 * 7, SCREEN_W, 15):
            draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill='#BEA77E')
    return image


def bubble_texture():
    height = 136
    image = halftone_case(height)
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((11, 10, SCREEN_W - 7, 123), 14, fill='#A4332D')
    draw.rounded_rectangle((6, 5, SCREEN_W - 13, 116), 14, fill=PAPER, outline=INK, width=4)
    draw.polygon(((74, 112), (92, 112), (81, 130)), fill=PAPER)
    draw.line(((74, 116), (81, 130), (92, 116)), fill=INK, width=4, joint='curve')
    return image


def halftone_cap(kind, width, height, pressed):
    w, h = width * 2, height * 2
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 10, w - 1, h - 1), 15, fill='#292027')
    shift = 7 if pressed else 0
    colors = HALFTONE_CAPS['control' if kind == 'globe' else kind]
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


def halftone(theme_id, theme):
    images = {
        'case.png': halftone_case(round(theme['style']['keyboard_height'] * DP)),
        'bubble.png': bubble_texture(),
    }
    skin_keys(theme, images, halftone_cap, 'halftone')
    return images


def latin_font():
    from fontTools import subset
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

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


MAP_PAPER = '#D9C6A1'
CONTOUR_CAPS = {
    'glyph': ('#F5EBD0', '#E7D9B2', '#867751'),
    'control': ('#456457', '#365146', '#344D43'),
    'number': ('#E6EAD0', '#D6DFC0', '#78806A'),
    'return': ('#A84530', '#8F3827', '#783C2F'),
}


def contour_case(height):
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


def contour_cap(kind, width, height, pressed):
    w, h = width * 2, height * 2
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    up, down, border = CONTOUR_CAPS['control' if kind == 'globe' else kind]
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


def contour(theme_id, theme):
    height = round(theme['style']['keyboard_height'] * DP) + 136
    images = {'case.png': contour_case(height), 'legend.png': legend_texture()}
    skin_keys(theme, images, contour_cap, 'contour')
    return images
