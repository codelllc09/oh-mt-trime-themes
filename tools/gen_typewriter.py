#!/usr/bin/env python3
"""從 V1、V2 外觀源檔和核准的 HTML 實錄生成同文 V2 主題及音效。"""

import argparse
import base64
from functools import lru_cache
from io import BytesIO
import json
import math
from pathlib import Path
import re
import wave

from PIL import Image, ImageColor, ImageDraw
import yaml

from check_trime import (
    RIME_DIR, ROOT, THEME_DIR, THEME_SOURCE, THEME_SOURCE_DIR, TYPEWRITER_BUILD, TYPEWRITER_ID,
    _deep_merge, load_yaml, packaged_sound_files, resolve_theme,
)
from render_keyboard import DP, build, hint_of, key_geometry, label_of


SOURCE = THEME_SOURCE_DIR / f'{TYPEWRITER_ID}.theme-source.yaml'
DRAFT = ROOT / 'design' / 'prototypes' / 'v2-typewriter.html'
MAIN_PAGES = ('qwerty', 'xuma_L', 'luna_pinyin')
PAGES = (*MAIN_PAGES, 'number', 'number_ascii', 'number_zh', 'symbols', 'mini')
CAP_PALETTES = {
    'glyph': ('#fff2d6', '#dac7a0'),
    'porcelain': ('#fffae9', '#e5dfce'),
    'control': ('#4d5d4d', '#232e24'),
    'globe': ('#4d5d4d', '#232e24'),
    'space': ('#434b3e', '#242e25'),
    'return': ('#a14c52', '#55282f'),
}
UI_HINTS = {'Shift_L': '⇪', 'BackSpace': '×…', 'Mode_switch': '◑', 'Return': 'CODE'}
SCALE = 2


def gradient(size, top, bottom):
    """在小圖做垂直漸層，再展開橫向，保留透明鍵帽以外的機身。"""
    a, b = (ImageColor.getrgb(color) for color in (top, bottom))
    strip = Image.new('RGB', (1, size[1]))
    strip.putdata([
        tuple(round(x + (y - x) * row / max(1, size[1] - 1)) for x, y in zip(a, b))
        for row in range(size[1])
    ])
    return strip.resize(size).convert('RGBA')


def rounded_layer(image, box, radius, top, bottom):
    x1, y1, x2, y2 = box
    size = (x2 - x1, y2 - y1)
    mask = Image.new('L', size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius, fill=255)
    layer = gradient(size, top, bottom)
    layer.putalpha(mask)
    image.alpha_composite(layer, (x1, y1))


def cap_dimensions(kind, width, height):
    if kind in ('glyph', 'porcelain'):
        diameter = min(90, width - 12, height - 16)
        return diameter, diameter
    return width - 12, min(height - 16, 76 if kind == 'space' else 93)


def etch_silver_ring(image, center, radius, rim, scale):
    draw = ImageDraw.Draw(image)
    x, y = center
    inner, outer = radius - rim + scale, radius - 2 * scale
    for i in range(48):
        angle = i * math.tau / 48
        dx, dy = math.cos(angle), math.sin(angle)
        draw.line((x + inner * dx, y + inner * dy, x + outer * dx, y + outer * dy),
                  fill='#697572' if i % 2 else '#f7f6ec', width=scale)


@lru_cache
def cap_texture(kind, width, height, pressed):
    cap_width, cap_height = cap_dimensions(kind, width, height)
    porcelain = kind == 'porcelain'
    scale = 3 if porcelain else SCALE
    w, h = cap_width * scale, cap_height * scale
    y_press = 3 * scale if pressed else 0
    x = (width * scale - w) // 2
    y = (height * scale - h) // 2 + y_press
    radius = h // 2 if kind in ('glyph', 'porcelain') else min(h // 4, (13 if kind == 'space' else 21) * scale)
    rim = (7 if porcelain else 4) * scale
    image = Image.new('RGBA', (width * scale, height * scale))
    rounded_layer(image, (x, y + 3 * scale, x + w, y + h + 3 * scale), radius, '#19251c', '#111a13')
    metal = ('#e3e5d7', '#848e8a') if porcelain else ('#dedac1', '#878a77')
    rounded_layer(image, (x, y, x + w, y + h), radius, *metal)
    if porcelain:
        etch_silver_ring(image, (x + radius, y + radius), radius, rim, scale)
    top, bottom = CAP_PALETTES[kind]
    if pressed:
        top, bottom = bottom, top
    rounded_layer(image, (x + rim, y + rim, x + w - rim, y + h - rim), radius - rim, top, bottom)

    draw = ImageDraw.Draw(image)
    if kind == 'space':
        for line_y in range(y + 15 * SCALE, y + h - 9 * SCALE, 5 * SCALE):
            draw.line((x + 12 * SCALE, line_y, x + w - 12 * SCALE, line_y), fill='#41483a', width=SCALE)
    if kind == 'globe':
        cx, cy = width * SCALE / 2, height * SCALE / 2 + y_press + 8 * SCALE
        size = min(w, h) * .20
        color = '#fff0cc'
        draw.ellipse((cx - size, cy - size, cx + size, cy + size), outline=color, width=2 * SCALE)
        draw.ellipse((cx - size * .43, cy - size, cx + size * .43, cy + size), outline=color, width=SCALE)
        for offset in (-.43, 0, .43):
            half = size * math.sqrt(1 - offset**2)
            draw.line((cx - half, cy + size * offset, cx + half, cy + size * offset), fill=color, width=SCALE)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def case_texture():
    width, height = 1080, 762
    image = gradient((width, height), '#375747', '#1b2c23')
    draw = ImageDraw.Draw(image)
    for x in range(0, width, 14):
        draw.line((x, 0, x, height), fill='#263b2f', width=1)
    draw.rounded_rectangle((4, 3, width - 5, height - 4), radius=27, outline='#7c8668', width=2)
    return image.convert('RGB')


def cap_kind(click, action):
    send = action.get('send')
    if click == 'Mode_switch':
        return 'globe'
    if send == 'space' or click == 'space':
        return 'space'
    if send == 'Return':
        return 'return'
    if action.get('select') or send or action.get('command'):
        return 'control'
    return 'glyph'


def skin_keys(theme, scheme):
    images = {'case.png': case_texture()}
    presets = theme['preset_keys']
    for page in PAGES:
        model = build(theme, page, {}, scheme)
        for cell, (_, _, w, h) in key_geometry(model):
            key = cell['key']
            click = key['click']
            action = click if isinstance(click, dict) else presets.get(click, {})
            kind = cap_kind(click, action)
            if page == 'number' and isinstance(click, str) and len(click) == 1 and click in '0123456789':
                kind = 'porcelain'
            w, h = round(w), round(h)
            for pressed, field in ((False, 'key_back_color'), (True, 'hilited_key_back_color')):
                alias = f'v2_{kind}_{w}x{h}' + ('_down' if pressed else '')
                filename = alias + '.png'
                theme['preset_color_schemes'][scheme][alias] = filename
                images[filename] = cap_texture(kind, w, h, pressed)
                key[field] = alias

            light = kind not in ('glyph', 'porcelain')
            text = 'off_key_text_color' if light else 'key_text_color'
            hint_color = 'nav_text_color' if key.get('popup') else (
                'off_key_symbol_color' if light else 'key_symbol_color'
            )
            if kind == 'porcelain':
                text, hint_color = 'number_text_color', 'number_symbol_color'
            key.update(key_text_color=text, hilited_key_text_color=text, key_symbol_color=hint_color)
            # V2 的提示字樣沿用草案，按鍵動作仍由 V1 決定。
            if click == 'Shift_L' or (click == 'BackSpace' and not key.get('long_click')):
                key['label_symbol'] = UI_HINTS[click]
            if page in MAIN_PAGES and click in ('Mode_switch', 'Return') and key.get('long_click'):
                key['label_symbol'] = UI_HINTS[click]
            if kind == 'globe':
                key['label'] = ' '
            hint = hint_of(key, presets)
            if not hint and 'label_symbol' not in key:
                long_click = key.get('long_click')
                if isinstance(long_click, str) and long_click.endswith('{Left}'):
                    hint = long_click.removesuffix('{Left}')
            label = label_of(key, presets)
            cap_width, cap_height = cap_dimensions(kind, w, h)
            label_size = 16 if len(label) == 1 or label.startswith('ic@') or kind == 'return' else 11
            if len(label) > 1 and kind == 'glyph' and not label.startswith('ic@'):
                label_size = 14
            key['key_text_size'] = min(label_size, round(cap_height * .53 / DP, 1))
            key['key_text_offset_y'] = round(cap_height * .13 / DP, 1) if hint else 0
            key['symbol_text_size'] = min(8, round(cap_width * .22 / DP, 1))
            symbol_center = (h - cap_height) / 2 + cap_height * .26
            key['key_symbol_offset_y'] = round((symbol_center - 15) / DP, 1)
    return images


def make_theme():
    vendor = load_yaml(THEME_DIR / 'vendor' / 'trime-3.3.13.yaml')
    inherited = resolve_theme(load_yaml(THEME_SOURCE), vendor)
    source = load_yaml(SOURCE)
    theme = _deep_merge(inherited, source)
    # V1 的配色屬於 V1。V2 的鍵帽圖片使用各自配色內的別名。
    theme['preset_color_schemes'] = source['preset_color_schemes']
    scheme = theme['style']['color_scheme']
    images = skin_keys(theme, scheme)
    return theme, images


def sound_assets():
    """從本機原型匯入 24 kHz PCM，或讀取現有鍵音。"""
    if not DRAFT.is_file():
        files = packaged_sound_files(TYPEWRITER_ID)
        descriptor = yaml.safe_load(files.pop(f'soundeffect/{TYPEWRITER_ID}.sound.yaml'))
        return descriptor, {Path(path).name: content for path, content in files.items()}

    html = DRAFT.read_text(encoding='utf-8')
    data = json.loads(re.search(r'<script id="sound-data" type="application/json">(.*?)</script>', html, re.S)[1])
    effects = {}
    indices = {}
    for kind in ('glyph', 'space', 'erase', 'control', 'return'):
        indices[kind] = []
        for index, encoded in enumerate(data['clips'][kind], 1):
            name = f'{kind}-{index}.wav'
            indices[kind].append(len(effects))
            output = BytesIO()
            with wave.open(output, 'wb') as wav:
                wav.setparams((1, 2, data['rate'], 0, 'NONE', 'not compressed'))
                wav.writeframes(base64.b64decode(encoded, validate=True))
            effects[name] = output.getvalue()

    # 同文 3.3.13 的音效 YAML 禁用錨點。重複的音序用各自的 list。
    config = {
        'name': 'V2-typewriter',
        'folder': TYPEWRITER_ID,
        'sound': list(effects),
        'keyset': [
            {'keys': ['KEYCODE_ENTER', 'KEYCODE_NUMPAD_ENTER'], 'inOrder': True, 'sounds': indices['return']},
            {'keys': ['KEYCODE_SPACE'], 'inOrder': False, 'sounds': indices['space']},
            {'keys': ['KEYCODE_DEL', 'KEYCODE_FORWARD_DEL'], 'inOrder': False, 'sounds': indices['erase']},
            {'keys': ['KEYCODE_SHIFT_LEFT', 'KEYCODE_SHIFT_RIGHT', 'KEYCODE_LANGUAGE_SWITCH',
                      'KEYCODE_TAB', 'KEYCODE_ESCAPE'], 'inOrder': True, 'sounds': indices['control']},
            {'min': 'KEYCODE_A', 'max': 'KEYCODE_Z', 'inOrder': False, 'sounds': indices['glyph'].copy()},
            {'min': 'KEYCODE_0', 'max': 'KEYCODE_9', 'inOrder': False, 'sounds': indices['glyph'].copy()},
            {'keys': ['KEYCODE_COMMA', 'KEYCODE_PERIOD', 'KEYCODE_SLASH', 'KEYCODE_SEMICOLON',
                      'KEYCODE_APOSTROPHE', 'KEYCODE_MINUS', 'KEYCODE_EQUALS', 'KEYCODE_GRAVE',
                      'KEYCODE_LEFT_BRACKET', 'KEYCODE_RIGHT_BRACKET', 'KEYCODE_BACKSLASH'],
             'inOrder': False, 'sounds': indices['glyph'].copy()},
        ],
    }
    return config, effects


def write_assets(check):
    theme, images = make_theme()
    sound, recordings = sound_assets()
    backgrounds = RIME_DIR / 'backgrounds' / TYPEWRITER_ID
    sound_dir = RIME_DIR / 'soundeffect'
    files = {
        TYPEWRITER_BUILD: yaml.safe_dump(theme, allow_unicode=True, sort_keys=True, width=4096).encode(),
        sound_dir / f'{TYPEWRITER_ID}.sound.yaml': (
            '# CC0 實錄剪輯：nvmbky · https://freesound.org/people/nvmbky/sounds/801118/\n'
            + yaml.safe_dump(sound, sort_keys=False)
        ).encode(),
    }
    for name, image in images.items():
        if check:
            # PNG 壓縮器版本可以不同，檢查圖像本身與透明通道。
            path = backgrounds / name
            if not path.is_file():
                print(f'[✗] 缺少 {path.relative_to(ROOT)}')
                return False
            with Image.open(path) as current:
                if (current.mode, current.size, current.tobytes()) != (image.mode, image.size, image.tobytes()):
                    print(f'[✗] {path.relative_to(ROOT)} 圖像陳舊')
                    return False
        else:
            output = BytesIO()
            image.save(output, format='PNG', optimize=True)
            files[backgrounds / name] = output.getvalue()
    files.update({sound_dir / TYPEWRITER_ID / name: pcm for name, pcm in recordings.items()})
    if check:
        stale = [path for path, data in files.items() if not path.is_file() or path.read_bytes() != data]
        for path in stale:
            print(f'[✗] {path.relative_to(ROOT)} 缺失或陳舊')
        return not stale

    for path, data in files.items():
        if path.is_file() and path.read_bytes() == data:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f'✓ {TYPEWRITER_BUILD.name}，{len(images)} 張鍵帽與機身圖片，{len(recordings)} 個實錄鍵音')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='比對生成物')
    args = parser.parse_args()
    raise SystemExit(0 if write_assets(args.check) else 1)
