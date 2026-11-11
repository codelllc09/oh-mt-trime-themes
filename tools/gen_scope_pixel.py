#!/usr/bin/env python3
"""由 V1 與定案原型生成示波器、像素積木主題及音效。"""

import argparse
from base64 import b64decode
from io import BytesIO
from itertools import groupby
import json
from pathlib import Path
import re
import wave
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageColor, ImageDraw
import yaml

from check_trime import OSCILLOSCOPE_ID, PIXELBLOCK_ID, RIME_DIR, ROOT, packaged_sound_files
from gen_calculator import draw_globe, inherit_skin, skin_keys, write_theme_assets
from gen_typewriter import MAIN_PAGES, PAGES, gradient
from render_keyboard import DP, SCREEN_W, build, hint_of, key_geometry


DRAFT = ROOT / 'design' / 'prototypes' / 'scope-pixelblock.html'
THEMES = {OSCILLOSCOPE_ID: 'scope', PIXELBLOCK_ID: 'pixel'}
MAIN_GROUPS = (
    ((3, '#BBA9FF'), (3, '#81EED6'), (4, '#FFCE64')),
    ((3, '#FF9BD7'), (3, '#FFD878'), (3, '#9BDAFA')),
    ((1, '#AFD4FF'), (4, '#83E6D9'), (3, '#C2A8FF'), (1, '#FFC2F5')),
    ((3, '#B8BCFF'), (1, '#9DEBE2'), (2, '#FFE17B'), (1, '#FFA9DC')),
)
BLOCK_COLORS = ('#BBA9FF', '#81EED6', '#FFD878', '#9BDAFA', '#FFA9DC')


def scope_grid(height):
    screen = gradient((SCREEN_W, height), '#0E2431', '#112C37').convert('RGB')
    draw = ImageDraw.Draw(screen, 'RGBA')
    for x in range(0, SCREEN_W, SCREEN_W // 8):
        draw.line((x, 0, x, height), fill=(119, 228, 211, 25 if x == SCREEN_W // 2 else 13), width=2)
    for y in range(0, height, height // 6):
        draw.line((0, y, SCREEN_W, y), fill=(119, 228, 211, 15), width=2)
    return screen


def scope_trace(height):
    image = scope_grid(height)
    draw = ImageDraw.Draw(image)
    center = height - 18
    wave_points = ((470, 0), (548, 0), (558, -4), (570, 5), (581, -7), (593, 4),
                   (608, 0), (664, 0), (678, -5), (689, 6), (700, -12), (712, 11), (724, 0), (820, 0))
    draw.line([(x, center + y) for x, y in wave_points], fill='#70C4B4', width=3, joint='curve')
    draw.line((0, height - 1, SCREEN_W, height - 1), fill='#396762', width=2)
    return image


def scope_cap(kind, w, h, pressed):
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    if pressed or kind == 'return':
        draw.rectangle((5, 4, w - 6, h - 5), fill=(48, 122, 114, 108 if pressed else 49),
                       outline='#67CFB6', width=2)
    y = round(h * .86)
    if kind == 'control' and w > 220:
        draw.line((w * .36, y, w * .64, y), fill='#54968E', width=2)
    else:
        draw.ellipse((w / 2 - 2, y - 2, w / 2 + 2, y + 2), fill='#54968E')
    if kind == 'globe':
        draw_globe(draw, (w / 2, h * .52), min(w, h) * .19, '#9FDDD9')
    return image


def pixel_hud(height):
    image = Image.new('RGB', (SCREEN_W, height), '#343BD5')
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 4, SCREEN_W - 9, height - 5), fill='#242682', outline='#9397FF', width=2)
    draw.line((11, 8, SCREEN_W - 12, 8), fill='#1A1A64', width=3)
    return image


def pixel_groups(page, rows):
    for row_index, row in enumerate(rows):
        if page in MAIN_PAGES:
            cells = [cell for cell in row if not cell.get('spacer')]
            start = 0
            for size, color in MAIN_GROUPS[row_index]:
                yield cells[start:start + size], color
                start += size
            if start != len(cells):
                raise ValueError(f'{page} 第 {row_index + 1} 行的色塊和鍵數不同')
            continue
        column = 0
        for spacer, cells in groupby(row, key=lambda cell: bool(cell.get('spacer'))):
            if spacer:
                continue
            run = list(cells)
            for start in range(0, len(run), 3):
                group = run[start:start + 3]
                click = group[0]['key']['click']
                color = BLOCK_COLORS[(column + row_index) % len(BLOCK_COLORS)]
                if page == 'number' and str(click) in ('7', '4', '1', '0'):
                    color = '#FFD878'
                if click == 'Return':
                    color = '#FFA9DC'
                yield group, color
                column += 1


def pixel_cap(w, h, color, first, last, globe, pressed):
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    left, right = (6 if first else 0), w - (7 if last else 1)
    bottom_step, top_step = (7 if first else 0), (7 if last else 0)
    fill = tuple(round(channel * .82) for channel in ImageColor.getrgb(color)) if pressed else color
    draw.polygon(((left, 0), (right - top_step, 0), (right - top_step, 7), (right, 7),
                  (right, h - 1), (left + bottom_step, h - 1), (left + bottom_step, h - 8),
                  (left, h - 8)), fill=fill)
    draw.rectangle((left, 0, right - top_step, 4), fill='#FFFFFF4D')
    draw.rectangle((left + bottom_step, h - 8, right, h - 1), fill='#28205D48')
    if not last:
        draw.line((right, h * .31, right, h * .69), fill='#21265566', width=2)
    if globe:
        draw_globe(draw, (w / 2, h * .53), min(w, h) * .19, '#171A48')
    # 將半透明印線疊在色塊上，保留對組內相鄰鍵連續的實色底。
    alpha = image.getchannel('A')
    opaque = Image.new('RGBA', image.size, fill)
    opaque.alpha_composite(image)
    opaque.putalpha(alpha.point(lambda value: 255 if value else 0))
    return opaque


def pixel_keys(theme, images):
    scheme = theme['preset_color_schemes'][theme['style']['color_scheme']]
    presets = theme['preset_keys']
    for page in PAGES:
        model = build(theme, page, {})
        sizes = {id(cell): (round(w), round(h)) for cell, (_, _, w, h) in key_geometry(model)}
        for group, color in pixel_groups(page, model['rows']):
            for index, cell in enumerate(group):
                key = cell['key']
                w, h = sizes[id(cell)]
                first, last = index == 0, index == len(group) - 1
                globe = key['click'] == 'Mode_switch'
                edge = ('l' if first else 'm') + ('r' if last else 'm')
                tile = 'globe' if globe else 'tile'
                alias = f'block_{tile}_{color[1:].lower()}_{edge}_{w}x{h}'
                for pressed, field in ((False, 'key_back_color'), (True, 'hilited_key_back_color')):
                    ref = alias + ('_down' if pressed else '')
                    name = ref + '.png'
                    if name not in images:
                        images[name] = pixel_cap(w, h, color, first, last, globe, pressed)
                    scheme[ref] = name
                    key[field] = ref
                key.update(key_text_color='key_text_color', hilited_key_text_color='key_text_color',
                           key_symbol_color='key_symbol_color', hilited_key_symbol_color='key_symbol_color')
                if globe:
                    key['label'] = ' '
                    if key.get('long_click'):
                        key['label_symbol'] = '◑'
                elif key['click'] == 'Return' and key.get('long_click'):
                    key['label_symbol'] = 'CODE'
                key['key_text_offset_y'] = 3 if hint_of(key, presets) else 0


def make_theme(theme_id):
    theme = inherit_skin(theme_id)
    style = theme['style']
    bar = round(style['candidate_view_height'] * DP)
    if theme_id == OSCILLOSCOPE_ID:
        height = bar + round(style['keyboard_height'] * DP)
        images = {'grid.png': scope_grid(height), 'trace.png': scope_trace(bar)}
        skin_keys(theme, images, scope_cap, 'scope')
    else:
        images = {'hud.png': pixel_hud(bar)}
        pixel_keys(theme, images)
    return theme, images


def sound_files(theme_id, name, approved):
    files = {}
    for kind, count in (('glyph', 3), ('space', 1), ('return', 1)):
        if len(approved[kind]) != count:
            raise ValueError(f'{name} 的 {kind} 樣音數量不同')
        for index, encoded in enumerate(approved[kind], 1):
            data = b64decode(encoded, validate=True)
            with wave.open(BytesIO(data)) as track:
                if (track.getnchannels(), track.getsampwidth(), track.getframerate()) != (1, 2, 24000):
                    raise ValueError(f'{name} 的 {kind}-{index} 格式錯誤')
            files[f'{kind}-{index}.wav'] = data

    descriptor = {
        'name': name, 'folder': theme_id, 'sound': list(files),
        'keyset': [
            {'keys': ['KEYCODE_ENTER', 'KEYCODE_NUMPAD_ENTER'], 'inOrder': True, 'sounds': [4]},
            {'keys': ['KEYCODE_SPACE'], 'inOrder': True, 'sounds': [3]},
            {'keys': ['KEYCODE_DEL', 'KEYCODE_FORWARD_DEL'], 'inOrder': True, 'sounds': [2]},
            {'keys': ['KEYCODE_SHIFT_LEFT', 'KEYCODE_SHIFT_RIGHT', 'KEYCODE_SWITCH_CHARSET', 'KEYCODE_EISU',
                      'KEYCODE_LANGUAGE_SWITCH', 'KEYCODE_TAB', 'KEYCODE_ESCAPE'], 'inOrder': True, 'sounds': [1]},
            {'min': 'KEYCODE_A', 'max': 'KEYCODE_Z', 'inOrder': False, 'sounds': [0, 1, 2]},
            {'min': 'KEYCODE_0', 'max': 'KEYCODE_9', 'inOrder': False, 'sounds': [0, 1, 2]},
            {'keys': ['KEYCODE_COMMA', 'KEYCODE_PERIOD', 'KEYCODE_SLASH', 'KEYCODE_SEMICOLON',
                      'KEYCODE_APOSTROPHE', 'KEYCODE_PLUS', 'KEYCODE_MINUS', 'KEYCODE_EQUALS'],
             'inOrder': False, 'sounds': [0, 1, 2]},
        ],
    }
    config = '# 樣音取自定案 HTML。退格和切換各用一個短鍵音變體。\n'
    config += yaml.safe_dump(descriptor, sort_keys=False)
    return {f'soundeffect/{theme_id}.sound.yaml': config.encode(),
            **{f'soundeffect/{theme_id}/{filename}': data for filename, data in files.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='檢查生成物是否同步')
    parser.add_argument('--sound-zips', type=Path, help='獨立音效包的輸出目錄')
    args = parser.parse_args()
    approved = None
    if DRAFT.is_file():
        match = re.search(r'<script id="sample-data" type="application/json">(.*?)</script>',
                          DRAFT.read_text(encoding='utf-8'), re.S)
        if not match:
            parser.error('定案 HTML 缺少樣音')
        approved = json.loads(match[1])
    for theme_id, skin in THEMES.items():
        theme, images = make_theme(theme_id)
        files = (packaged_sound_files(theme_id) if approved is None
                 else sound_files(theme_id, theme['name'], approved[skin]))
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
