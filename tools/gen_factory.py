#!/usr/bin/env python3
"""由定案原型生成砂型鑄造、晶圓步進機與氣動分揀台。"""

import argparse
from base64 import b64decode
from functools import partial
from io import BytesIO
from pathlib import Path
from random import Random
import wave
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageColor, ImageDraw, ImageEnhance
import yaml

from check_trime import FACTORY_THEME_IDS, RIME_DIR, packaged_sound_files
from gen_calculator import SCALE, draw_globe, inherit_skin, skin_keys, write_theme_assets
from gen_industrial import samples
from gen_typewriter import PAGES, gradient, rounded_layer
from render_keyboard import DP, SCREEN_W, build, key_geometry


DRAFT = 'cast-wafer-pneumatic.html'
SAMPLE_NAMES = ('key', 'space', 'delete', 'return')
SKINS = dict(zip(FACTORY_THEME_IDS, ('cast', 'wafer', 'air')))
COLOR_KEYS = {
    'glyph': ('key_text_color', 'key_symbol_color'),
    'symbol': ('key_text_color', 'key_symbol_color'),
    'digit': ('key_text_color', 'key_symbol_color'),
    'tool': ('fn_text_color', 'fn_symbol_color'),
    'globe': ('fn_text_color', 'fn_symbol_color'),
    'space': ('fn_text_color', 'fn_symbol_color'),
    'return': ('accent_text', 'accent_symbol'),
}

FOUNDRY = {
    'glyph': ('#CBB187', '#AD8C65', '#654A33'),
    'light': ('#DEC096', '#AD8C65', '#654A33'),
    'digit': ('#F0D9AA', '#D2AC7E', '#806444'),
    'symbol': ('#AC9478', '#90755A', '#57422C'),
    'tool': ('#65513F', '#483524', '#241710'),
    'return': ('#FFC477', '#EF8847', '#813D21'),
}
WAFER = {
    'teal': ('#E0F4EE', '#ABCFC8', '#8DAAAE'),
    'ice': ('#E5F1FF', '#B2C4EA', '#8A99BC'),
    'violet': ('#EFECFF', '#BDBAE9', '#918FB5'),
    'lilac': ('#F7EAFF', '#D1B9E5', '#A38EB2'),
    'digit': ('#E8FFFF', '#B7CAFF', '#7D93BD'),
    'symbol': ('#D6E0E9', '#B1BED4', '#8491AD'),
    'tool': ('#F5F8FC', '#BCC4DA', '#8791A8'),
    'return': ('#5E498A', '#322756', '#282045'),
}
PNEUMATIC = {
    'glyph': ('#608DE2', '#2C5799', '#142C55'),
    'dark': ('#487AC8', '#254A84', '#142C55'),
    'digit': ('#628FFF', '#2D5FD0', '#163B7C'),
    'symbol': ('#597696', '#25455F', '#142C55'),
    'tool': ('#DFEBFA', '#9AB1CE', '#7188AD'),
    'return': ('#E6FF88', '#B3DC52', '#2A4930'),
}
CAPS = {'cast': FOUNDRY, 'wafer': WAFER, 'air': PNEUMATIC}
CAP_ALIASES = {'space': 'tool', 'globe': 'tool'}
for kind in ('light', 'teal', 'ice', 'violet', 'lilac', 'dark'):
    COLOR_KEYS[kind] = COLOR_KEYS['glyph']


def cell_role(page, click, action):
    if click == 'Mode_switch':
        return 'globe'
    if click == 'space' or action.get('send') == 'space':
        return 'space'
    if action.get('send') == 'Return':
        return 'return'
    if action.get('select') or click in ('Shift_L', 'BackSpace'):
        return 'tool'
    if page == 'number' and isinstance(click, str) and len(click) == 1 and click.isascii() and click.isdigit():
        return 'digit'
    return 'symbol' if page == 'number' else 'glyph'


def key_identity(click):
    return click.get('text') if isinstance(click, dict) else click


def key_appearances(theme, skin):
    presets = theme['preset_keys']
    appearances = {}
    for page in PAGES:
        model = build(theme, page, {})
        for cell, (x, y, w, _) in key_geometry(model):
            click = cell['key']['click']
            action = click if isinstance(click, dict) else presets.get(click, {})
            role = cell_role(page, click, action)
            row = round((y - model['vgap'] * DP / 2) / model['cell_h'])
            if role == 'glyph':
                if skin == 'wafer':
                    position = min(3, int((x + w / 2 + 43 * row) / SCREEN_W * 4))
                    role = ('teal', 'ice', 'violet', 'lilac')[position]
                elif skin == 'cast' and row == 1:
                    role = 'light'
                elif skin == 'air' and row % 2:
                    role = 'dark'
            appearances[page, key_identity(click)] = role
    return appearances


def sand_grain(image, box, color):
    draw = ImageDraw.Draw(image)
    light = ImageColor.getrgb(color)
    dark = tuple(round(channel * .69) for channel in light)
    left, top, right, bottom = box
    rng = Random(71 + right + bottom)
    for _ in range((right - left) * (bottom - top) // 27):
        x = rng.randrange(left + 4, right - 4)
        y = rng.randrange(top + 5, bottom - 6)
        draw.point((x, y), fill=rng.choice((light, dark)))
        if rng.randrange(4) == 0:
            draw.point((x + 1, y), fill=dark)


def die_grid(draw, box, role):
    left, top, right, bottom = box
    if role == 'return':
        x, y = round(right * .78), round(bottom * .79)
        draw.line((x - 9, y, x + 9, y), '#E3F9C2', width=2)
        draw.line((x, y - 9, x, y + 9), '#E3F9C2', width=2)
        return
    for x in range(left + 9, right - 4, 23):
        draw.line((x, round(top + (bottom - top) * .58), x, bottom - 5), '#FFFFFF65', width=2)
    for y in range(round(bottom * .68), bottom - 4, 21):
        draw.line((left + 6, y, right - 6, y), '#FFFFFF65', width=2)


def roller_trim(draw, box, role):
    left, top, right, bottom = box
    if role == 'return':
        for x in range(left + 3, right - 12, 18):
            draw.polygon([(x, bottom), (x + 7, bottom), (x + 17, bottom - 9), (x + 10, bottom - 9)],
                         '#29422A')
        return
    if role not in ('tool', 'globe', 'space'):
        for x in (left + 3, right - 8):
            draw.rounded_rectangle((x, top + 7, x + 5, bottom - 3), 2, fill='#182B52')
        y = round(bottom * .85)
        draw.line((left + 16, y, right - 16, y), '#9FC5FF', width=2)


def cap_texture(skin, globe_color, role, width, height, pressed):
    w, h = width * SCALE, height * SCALE
    canvas = Image.new('RGBA', (w, h))
    cap = Image.new('RGBA', canvas.size)
    face, base, heel = CAPS[skin][CAP_ALIASES.get(role, role)]
    radius = {'cast': 22, 'wafer': 7, 'air': 17}[skin]
    box = (2, 2, w - 2, h - (9 if pressed else 3))
    rounded_layer(cap, box, radius, face, heel)
    left, top, right, bottom = face_box = (4, 4, w - 4, box[3] - (4 if skin == 'wafer' else 11))
    rounded_layer(cap, face_box, radius - 2, face, base)
    if skin == 'cast':
        sand_grain(cap, face_box, face)
        y = round(bottom * .87)
        ImageDraw.Draw(cap).line((left + w * .14, y, right - w * .14, y), heel, width=2)
    elif skin == 'wafer':
        overlay = Image.new('RGBA', cap.size)
        die_grid(ImageDraw.Draw(overlay), face_box, role)
        cap.alpha_composite(overlay)
    else:
        roller_trim(ImageDraw.Draw(cap), face_box, role)
    if pressed:
        cap = ImageEnhance.Brightness(cap).enhance(.82)
    if role == 'globe':
        draw_globe(ImageDraw.Draw(cap), (w / 2, h * .54), min(w, h) * .20, globe_color)
    canvas.alpha_composite(cap, (0, 5 if pressed else 0))
    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def case_textures(skin, height, bar):
    size = (SCREEN_W, height)
    deck, strip, seam = {
        'cast': (('#382B1D', '#241D17'), ('#27211A', '#2F241B'), '#95663F'),
        'wafer': (('#8795AC', '#9293B4'), ('#E8EBF8', '#D7DAEF'), '#BBC3E2'),
        'air': (('#273F65', '#14223B'), ('#13294D', '#102444'), '#4A76BA'),
    }[skin]
    case = gradient(size, *deck).convert('RGB')
    candidate = gradient((SCREEN_W, bar), *strip).convert('RGB')
    draw = ImageDraw.Draw(case, 'RGBA')
    if skin == 'cast':
        y = bar + (height - bar) // 2
        draw.rectangle((0, y - 4, SCREEN_W, y + 4), '#1E1711')
        draw.line((0, y, SCREEN_W, y), seam, width=2)
    elif skin == 'wafer':
        cx, cy = SCREEN_W // 2, bar + (height - bar) // 2
        for index, color in enumerate(('#B7D7DD', '#BFC9EB', '#D2C1E9', '#DFCEE8')):
            r = 469 - index * 65
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color, outline='#F2F4FE', width=2)
        for r in range(28, 470, 35):
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 85), width=2)
        draw.line((cx - 38, cy, cx + 38, cy), '#FFFFFF', width=2)
        draw.line((cx, cy - 38, cx, cy + 38), '#FFFFFF', width=2)
    else:
        for x in range(0, SCREEN_W, 17):
            draw.rectangle((x, 0, x + 4, height), (132, 170, 219, 42))
        for y in range(bar + 4, height, round((height - bar) / 4)):
            draw.line((0, y, SCREEN_W, y), (134, 184, 249, 90), width=3)
    ImageDraw.Draw(candidate).line((0, bar - 2, SCREEN_W, bar - 2), seam, width=3)
    return {'case.png': case, 'strip.png': candidate}


def make_theme(theme_id):
    skin = SKINS[theme_id]
    theme = inherit_skin(theme_id)
    style = theme['style']
    scheme = theme['preset_color_schemes'][style['color_scheme']]
    bar = round(style['candidate_view_height'] * DP)
    images = case_textures(skin, bar + round(style['keyboard_height'] * DP), bar)
    appearances = key_appearances(theme, skin)

    def classify(page, click, _action):
        return appearances[page, key_identity(click)]

    draw_cap = partial(cap_texture, skin, '#' + scheme['fn_text_color'][-6:])
    skin_keys(theme, images, draw_cap, theme_id[3:], separate_space=True,
              classify=classify, color_keys=COLOR_KEYS)
    return theme, images


def sound_assets(theme_id, name, approved):
    paths = {f'{kind}.wav': b64decode(approved[kind], validate=True) for kind in SAMPLE_NAMES}
    for data in paths.values():
        with wave.open(BytesIO(data)) as track:
            if (track.getnchannels(), track.getsampwidth(), track.getframerate()) != (1, 2, 24000):
                raise ValueError(f'{name} 的樣音須為 24 kHz、16 bit、單聲道')
    keys = [
        {'keys': ['KEYCODE_ENTER', 'KEYCODE_NUMPAD_ENTER'], 'inOrder': True, 'sounds': [3]},
        {'keys': ['KEYCODE_DEL', 'KEYCODE_FORWARD_DEL'], 'inOrder': True, 'sounds': [2]},
        {'keys': ['KEYCODE_SPACE'], 'inOrder': True, 'sounds': [1]},
        {'min': 'KEYCODE_A', 'max': 'KEYCODE_Z', 'inOrder': True, 'sounds': [0]},
        {'min': 'KEYCODE_0', 'max': 'KEYCODE_9', 'inOrder': True, 'sounds': [0]},
    ]
    config = {'name': name, 'folder': theme_id, 'sound': list(paths), 'keyset': keys}
    descriptor = '# 合成樣音取自定案互動原型。\n' + yaml.safe_dump(config, sort_keys=False)
    return {f'soundeffect/{theme_id}.sound.yaml': descriptor.encode(),
            **{f'soundeffect/{theme_id}/{file}': data for file, data in paths.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='只檢查生成物是否同步')
    parser.add_argument('--sound-zips', type=Path, help='獨立音效包的輸出目錄')
    args = parser.parse_args()
    approved = samples(DRAFT)
    for theme_id, skin in SKINS.items():
        theme, images = make_theme(theme_id)
        files = (packaged_sound_files(theme_id) if approved is None
                 else sound_assets(theme_id, theme['name'], approved[skin]))
        write_theme_assets(theme_id, theme, images, check=args.check)
        for relative, content in files.items():
            path = RIME_DIR / relative
            if args.check:
                if not path.is_file() or path.read_bytes() != content:
                    parser.exit(1, f'{relative} 缺失或未同步\n')
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        if args.sound_zips and not args.check:
            args.sound_zips.mkdir(parents=True, exist_ok=True)
            archive_path = args.sound_zips / f"{theme['name']}-sound.zip"
            with ZipFile(archive_path, 'w', compression=ZIP_DEFLATED) as archive:
                for relative, content in files.items():
                    archive.writestr(relative, content)
            print(f'→ {archive_path}')


if __name__ == '__main__':
    main()
