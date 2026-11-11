#!/usr/bin/env python3
"""由 V1 鍵位和定案樣音生成五款工業同文主題。"""

import argparse
from functools import partial
import json
from math import exp
from pathlib import Path
import re
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageColor, ImageDraw, ImageEnhance

from check_trime import (
    BACKPLANE_ID, INDUSTRIAL_THEME_IDS, INTERLOCK_ID, PERFORATION_ID,
    RIME_DIR, ROOT, THERMOGRAM_ID, VACUUM_ID,
    packaged_sound_files,
)
from gen_calculator import SCALE, draw_globe, inherit_skin, skin_keys, write_theme_assets
from gen_scope_pixel import sound_files
from gen_typewriter import PAGES, gradient, rounded_layer
from render_keyboard import DP, SCREEN_W, build, key_geometry


EMPHASIZED = {BACKPLANE_ID, VACUUM_ID, THERMOGRAM_ID}
COLORS = {
    'glyph': ('key_text_color', 'key_symbol_color'),
    'modifier': ('modifier_text_color', 'modifier_text_color'),
    'nav': ('nav_text_color', 'nav_symbol_color'),
    'globe': ('nav_text_color', 'nav_symbol_color'),
    'space': ('space_text_color', 'key_symbol_color'),
    'operator': ('fn_text_color', 'key_symbol_color'),
    'number': ('number_text_color', 'number_symbol_color'),
    'return': ('accent_text', 'accent_text'),
}


def key_role(theme_id, page, click, action):
    if click == 'Mode_switch':
        return 'globe'
    if click == 'space' or action.get('send') == 'space':
        return 'space'
    if action.get('send') == 'Return':
        return 'return'
    if click in ('Shift_L', 'BackSpace'):
        return 'modifier'
    if action.get('select') or click == 'sym':
        return 'nav'
    if page == 'number' and isinstance(click, str) and len(click) == 1:
        if theme_id in EMPHASIZED and click in '0123456789':
            return 'number'
        if click in '/*+':
            return 'operator'
    return 'glyph'


def chamfer(box, size):
    x0, y0, x1, y1 = box
    return [(x0 + size, y0), (x1 - size, y0), (x1, y0 + size),
            (x1, y1 - size), (x1 - size, y1), (x0 + size, y1),
            (x0, y1 - size), (x0, y0 + size)]


def inset(box, pixels):
    x0, y0, x1, y1 = box
    return x0 + pixels, y0 + pixels, x1 - pixels, y1 - pixels


def perforation_cap(image, role):
    w, h = image.size
    circle = role == 'glyph'
    diameter = min(w - 14, round(h * .81))
    half_w, half_h = (diameter // 2,) * 2 if circle else (w // 2 - 8, round(h * .37))
    box = (w // 2 - half_w, h // 2 - half_h, w // 2 + half_w, h // 2 + half_h)
    top, bottom = {
        'nav': ('#223A49', '#476575'), 'modifier': ('#303E48', '#526775'),
        'space': ('#18242B', '#303D44'), 'return': ('#123C50', '#285C72'),
        'operator': ('#263A46', '#3E5663'),
    }.get(role, ('#161F26', '#3E515E'))
    rim = '#6EC6E1' if role == 'return' else '#E5EDEF'
    rounded_layer(image, box, half_h, '#7D9099', rim)
    rounded_layer(image, inset(box, 5), half_h - 5, top, bottom)
    if role == 'space':
        ImageDraw.Draw(image).line((w * .27, h * .72, w * .73, h * .72), '#82949C', width=3)


def interlock_cap(image, role):
    w, h = image.size
    box = (8, 12, w - 9, h - 14)
    cut = min(26, w // 6)
    draw = ImageDraw.Draw(image)
    draw.polygon(chamfer(box, cut), fill='#171A1B')
    rim, face = {
        'nav': ('#D1A33F', '#353734'), 'modifier': ('#FFF3D6', '#E0D6BD'),
        'space': ('#766540', '#272A2A'), 'return': ('#604B26', '#1F2020'),
    }.get(role, ('#585950', '#353634'))
    draw.polygon(chamfer(inset(box, 3), cut - 1), fill=rim)
    draw.polygon(chamfer(inset(box, 7), cut - 3), fill=face)
    if role == 'return':
        draw.polygon(chamfer((round(w * .14), 14, round(w * .86), h - 15), 12), fill='#E75121')
        for x in (w * .09, w * .91):
            draw.line((x, 25, x, h - 26), '#100F0D', width=8)
    elif role == 'space':
        draw.line((w * .26, h * .70, w * .74, h * .70), '#B6A061', width=3)


def backplane_cap(image, role):
    w, h = image.size
    draw = ImageDraw.Draw(image)
    box = (9, 10, w - 10, h - 12)
    copper = '#DEAF70'
    if role == 'glyph':
        for x in (w * .37, w * .63):
            draw.rounded_rectangle((x - 8, h * .81, x + 8, h * .89), 2, fill=copper)
        return
    if role == 'number':
        rounded_layer(image, box, 7, '#F9DEA1', '#D7A660')
        draw.rounded_rectangle(inset(box, 4), 4, outline='#FFF0B8', width=2)
        return
    if role == 'return':
        draw.polygon(chamfer(box, 22), fill='#D49A52', outline='#FBE2A0', width=4)
        return
    face, rim = {
        'space': ('#124437', '#B17C49'), 'modifier': ('#296052', '#BCD3C7'),
        'operator': ('#184B41', '#62877A'),
    }.get(role, ('#154C3F', copper))
    draw.rounded_rectangle(box, 8, fill=face, outline=rim, width=3)
    if role == 'space':
        draw.line((w * .22, h * .71, w * .78, h * .71), copper, width=3)
        for x in (w * .22, w * .78):
            draw.ellipse((x - 5, h * .71 - 5, x + 5, h * .71 + 5), fill=copper)


def vacuum_cap(image, role):
    w, h = image.size
    side = 9 if role in ('space', 'return') else max(8, w // 10)
    box = (side, 9, w - side, h - 11)
    radius = min(w // 3, h // 3)
    rim, top, bottom = {
        'number': ('#FFCE8F', '#FFF4DF', '#EEAF78'),
        'nav': ('#C1B3B0', '#41383A', '#36252B'),
        'modifier': ('#876D69', '#4D393A', '#33252C'),
        'space': ('#855E48', '#513528', '#301F23'),
        'return': ('#F0A34B', '#824025', '#4E281E'),
    }.get(role, ('#845848', '#503238', '#332229'))
    rounded_layer(image, box, radius, rim, '#4C3335')
    rounded_layer(image, inset(box, 4), radius - 3, top, bottom)
    draw = ImageDraw.Draw(image)
    draw.arc(inset(box, 8), 205, 330, fill=rim, width=2)
    y = round(h * .79)
    left, right = w * .26, w * .74
    filament = '#FFE6B1' if role == 'return' else '#F3A057'
    if role == 'number':
        filament = '#AF593A'
    draw.rounded_rectangle((left, y - 3, right, y + 3), 3, fill=filament)


def thermogram_cap(image, role):
    w, h = image.size
    x0, y0, x1, y1 = (8, 12, w - 9, h - 14)
    draw = ImageDraw.Draw(image)
    if role == 'number':
        outer, core = (189, 81, 117), (255, 249, 226)
        for step in range(24, 0, -1):
            ratio = step / 24
            rx, ry = (w / 2 - 5) * ratio, (h / 2 - 10) * ratio
            warmth = min(1, (1 - ratio) * 2.8)
            ink = tuple(round(a + (b - a) * warmth) for a, b in zip(outer, core))
            alpha = round(min(1, (1 - ratio) * 7) * 255)
            draw.ellipse((w / 2 - rx, h / 2 - ry, w / 2 + rx, h / 2 + ry), fill=(*ink, alpha))
    elif role == 'glyph':
        for x, dx in ((x0, 1), (x1, -1)):
            for y, dy in ((y0, 1), (y1, -1)):
                draw.line((x + 13 * dx, y, x, y, x, y + 13 * dy), fill='#EBAEC5', width=2)
    elif role == 'space':
        for x in range(x0, x1, 17):
            for y in (y0, y1):
                draw.line((x, y, min(x + 10, x1), y), '#FFDBD7', width=3)
        for x in (x0, x1):
            draw.line((x, y0, x, y1), '#FFDBD7', width=2)
    else:
        face, rim = {
            'return': ('#FFDE8D', '#FFF2B6'), 'nav': ('#242447', '#9B9BD9'),
            'modifier': ('#633656', '#E3A5C4'), 'operator': ('#613044', '#DF9DAC'),
            'globe': ('#242447', '#9B9BD9'),
        }[role]
        draw.rounded_rectangle((x0, y0, x1, y1), 9, fill=face, outline=rim, width=3)


CAPS = {
    PERFORATION_ID: perforation_cap, INTERLOCK_ID: interlock_cap,
    BACKPLANE_ID: backplane_cap, VACUUM_ID: vacuum_cap, THERMOGRAM_ID: thermogram_cap,
}


def cap_texture(theme_id, scheme, role, width, height, pressed):
    w, h = width * SCALE, height * SCALE
    image = Image.new('RGBA', (w, h))
    CAPS[theme_id](image, role)
    if pressed:
        image = ImageEnhance.Brightness(image).enhance(.77)
    if role == 'globe':
        draw_globe(ImageDraw.Draw(image), (w / 2, h * .54), min(w, h) * .20,
                   '#' + scheme['nav_text_color'][-6:])
    return image.resize((width, height), Image.Resampling.LANCZOS)


def heat_field(size):
    palette = [ImageColor.getrgb(color) for color in
               ('#241938', '#481F56', '#782756', '#A33D52', '#BB6644')]
    w, h = 270, 192
    field = Image.new('RGB', (w, h))
    pixels = []
    for j in range(h):
        y = j / h
        for i in range(w):
            x = i / w
            hot = 2.7 * exp(-((x - .84) / .44) ** 2 - ((y - .89) / .34) ** 2)
            warm = 1.8 * exp(-((x - .58) / .34) ** 2 - ((y - .12) / .40) ** 2)
            level = min(3.99, .35 + hot + warm)
            index = int(level)
            pixels.append(tuple(round(a + (b - a) * (level - index))
                                for a, b in zip(palette[index], palette[index + 1])))
    field.putdata(pixels)
    return field.resize(size, Image.Resampling.BICUBIC)


def case_textures(theme_id, height, bar):
    size = SCREEN_W, height
    plate, strip = {
        PERFORATION_ID: (('#BECBD0', '#A2B0B7'), ('#BECBD0', '#BECBD0')),
        INTERLOCK_ID: (('#D6A43D', '#AA7521'), ('#282720', '#211F1B')),
        BACKPLANE_ID: (('#1A6754', '#0D473D'), ('#174A3E', '#123D32')),
        VACUUM_ID: (('#382B32', '#201D24'), ('#372831', '#2A222B')),
        THERMOGRAM_ID: (('#241938', '#BB6644'), ('#2E203D', '#37213D')),
    }[theme_id]
    case = (heat_field(size) if theme_id == THERMOGRAM_ID
            else gradient(size, *plate).convert('RGB'))
    candidate = gradient((SCREEN_W, bar), *strip)
    draw = ImageDraw.Draw(case, 'RGBA')
    if theme_id == PERFORATION_ID:
        rounded_layer(candidate, (12, 7, SCREEN_W - 12, bar - 7), bar // 2 - 7, '#3F535E', '#25353E')
        for y in range(0, height, 3):
            draw.line((0, y, SCREEN_W, y), fill=(255, 255, 255, 25 + (y * 19) % 30))
    elif theme_id == INTERLOCK_ID:
        draw.rectangle((0, height - 14, SCREEN_W, height), '#211F1B')
        for x in range(-20, SCREEN_W, 42):
            draw.polygon([(x, height), (x + 16, height), (x + 30, height - 14),
                          (x + 14, height - 14)], fill='#D6A43D')
        ImageDraw.Draw(candidate).line((0, bar - 2, SCREEN_W, bar - 2), '#D6A43D', width=3)
    elif theme_id == BACKPLANE_ID:
        for i in range(16):
            x, y = 31 + i * 67, 105 + (i % 4) * 159
            draw.line(((x, 0), (x, y - 32), (x + 31, y), (x + 31, height)),
                      (214, 163, 105, 55), width=2)
            for via_y in (y, y + 119):
                draw.ellipse((x + 26, via_y - 5, x + 36, via_y + 5),
                             outline=(224, 179, 110, 127), width=2)
    elif theme_id == VACUUM_ID:
        for x in range(22, SCREEN_W, 108):
            draw.line((x, 0, x, height), fill=(164, 109, 78, 31), width=2)
        for y in range(bar + 48, height, 161):
            draw.line((0, y, SCREEN_W, y), fill=(214, 135, 80, 41), width=2)
    else:
        for y in range(1, height, 5):
            draw.line((0, y, SCREEN_W, y), fill=(247, 179, 225, 22))
        scale = ImageDraw.Draw(candidate)
        for i, color in enumerate(('#6753A2', '#A74483', '#E0656A', '#FFA56E', '#FFE4A1')):
            x = SCREEN_W - 115 + 21 * i
            scale.rectangle((x, bar - 5, x + 20, bar - 2), fill=color)
    return {'case.png': case, 'strip.png': candidate.convert('RGB')}


def make_theme(theme_id):
    theme = inherit_skin(theme_id)
    style = theme['style']
    scheme = theme['preset_color_schemes'][style['color_scheme']]
    bar = round(style['candidate_view_height'] * DP)
    images = case_textures(theme_id, bar + round(style['keyboard_height'] * DP), bar)
    skin_keys(theme, images, partial(cap_texture, theme_id, scheme), theme_id[3:],
              separate_space=True, classify=partial(key_role, theme_id), color_keys=COLORS)
    if theme_id == PERFORATION_ID:
        # 把淺色長按字樣移入暗孔，與銀色面板分開。
        for page in PAGES:
            offset = 4 if page.startswith('number') else 7
            for cell, _ in key_geometry(build(theme, page, {})):
                cell['key']['key_symbol_offset_y'] = offset
    if theme_id in EMPHASIZED:
        cells = list(key_geometry(build(theme, 'number', {})))
        footer = max(y for _, (_, y, _, _) in cells)
        for cell, (_, y, _, _) in cells:
            if y < footer:
                cell['key']['key_text_offset_y'] = 3
    return theme, images


def samples(filename):
    path = ROOT / 'design' / 'prototypes' / filename
    if not path.is_file():
        return None
    source = path.read_text(encoding='utf-8')
    match = re.search(r'<script id="sample-data" type="application/json">(.*?)</script>', source, re.S)
    if match is None:
        raise ValueError(f'{filename} 缺少定案樣音')
    return json.loads(match[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='檢查生成物是否同步')
    parser.add_argument('--sound-zips', type=Path, help='獨立音效包的輸出目錄')
    args = parser.parse_args()
    approved = samples('interlock-docking.html')
    perforation = samples('perforation-wayfinding-terrace.html')
    for theme_id in INDUSTRIAL_THEME_IDS:
        theme, images = make_theme(theme_id)
        bank = perforation if theme_id == PERFORATION_ID else approved
        files = (packaged_sound_files(theme_id) if bank is None
                 else sound_files(theme_id, theme['name'], bank[theme_id.removeprefix('v2-')]))
        write_theme_assets(theme_id, theme, images, check=args.check)
        for asset, content in files.items():
            path = RIME_DIR / asset
            if args.check:
                if not path.is_file() or path.read_bytes() != content:
                    parser.exit(1, f'{asset} 缺失或未同步\n')
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        if args.sound_zips and not args.check:
            args.sound_zips.mkdir(parents=True, exist_ok=True)
            output = args.sound_zips / f'{theme["name"]}-sound.zip'
            with ZipFile(output, 'w', compression=ZIP_DEFLATED) as archive:
                for asset, content in files.items():
                    archive.writestr(asset, content)
            print(f'→ {output}')


if __name__ == '__main__':
    main()
