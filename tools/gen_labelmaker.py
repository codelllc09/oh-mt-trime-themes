#!/usr/bin/env python3
"""從 V1、標籤機外觀源檔和定案試聽生成同文主題及音效。"""

import argparse
from base64 import b64decode
from io import BytesIO
import json
import re
import wave

from PIL import Image, ImageDraw
import yaml

from check_trime import (
    LABELMAKER_ID, RIME_DIR, ROOT, THEME_DIR, THEME_SOURCE, THEME_SOURCE_DIR,
    _deep_merge, load_yaml, resolve_theme,
)
from gen_typewriter import PAGES, cap_kind, gradient, rounded_layer
from render_keyboard import DP, SCREEN_W, build, hint_of, key_geometry


DRAFT = ROOT / 'design' / 'prototypes' / 'thermal-label-keyboard.html'
CAPS = {
    'glyph': (('#484E45', '#363B33'), ('#3D443A', '#2E342B')),
    'control': (('#32372F', '#232720'), ('#292E27', '#1F241D')),
    'space': (('#2C3029', '#232720'), ('#272B24', '#1F241D')),
    'return': (('#E9B86A', '#D99C49'), ('#D8A052', '#BC8037')),
}
SAMPLES = {'glyph': 3, 'space': 1, 'erase': 1, 'control': 1, 'return': 1}


def case_texture(size):
    width, height = size
    image = gradient(size, '#41473E', '#282C26').convert('RGB')
    grain = ImageDraw.Draw(image, 'RGBA')
    for x in range(0, width + height, 6):
        grain.line((x, 0, x - height, height), fill=(255, 255, 242, 10))
    return image


def tape_texture(height):
    width = SCREEN_W
    image = case_texture((width, height)).convert('RGBA')
    rounded_layer(image, (8, height - 23, width - 8, height - 4), 8, '#11140F', '#4C5147')
    left, top, right, bottom = 23, 8, width - 23, height - 11
    image.alpha_composite(gradient((right - left, bottom - top), '#F9F0DC', '#EEE0C4'), (left, top))
    draw = ImageDraw.Draw(image)
    for y in range(top + 4, bottom - 4, 8):
        draw.line((left, y, right - 1, y), fill='#E9DBC0')
    draw.line((left, top, right - 1, top), fill='#FFF6E2')
    draw.line((left, bottom - 1, right - 1, bottom - 1), fill='#BAAA8A')
    cut = width - round(40 * DP)
    for y in range(top + 6, bottom - 6, 9):
        draw.line((cut, y, cut, y + 4), fill='#83735A', width=2)

    # Trime 讀取上、左的黑線作伸縮區，保留紙邊、裁切線和出紙口。
    nine_patch = Image.new('RGBA', (width + 2, height + 2))
    nine_patch.paste(image, (1, 1))
    markers = ImageDraw.Draw(nine_patch)
    markers.line((64, 0, cut - 14, 0), fill='#000000')
    markers.line((0, 22, 0, height - 26), fill='#000000')
    return nine_patch


def cap_texture(kind, width, height, pressed):
    up, down = CAPS[kind]
    scale = 2
    w, h = width * scale, height * scale
    image = Image.new('RGBA', (w, h))
    y = 6 if pressed else 2
    radius = min(w, h) // 9
    edge = '#765125' if kind == 'return' else '#171B16'
    rounded_layer(image, (0, y, w, h), radius, edge, '#131712')
    rounded_layer(image, (2, y + 2, w - 2, h - (4 if pressed else 9)),
                  max(1, radius - 2), *(down if pressed else up))
    draw = ImageDraw.Draw(image, 'RGBA')
    shine = '#F5D395' if kind == 'return' else '#656C60'
    draw.line((radius, y + 3, w - radius, y + 3), fill=shine, width=2)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def make_theme():
    base = load_yaml(THEME_DIR / 'vendor' / 'trime-3.3.13.yaml')
    inherited = resolve_theme(load_yaml(THEME_SOURCE), base)
    source = load_yaml(THEME_SOURCE_DIR / f'{LABELMAKER_ID}.theme-source.yaml')
    theme = _deep_merge(inherited, source)
    theme['preset_color_schemes'] = source['preset_color_schemes']
    style = theme['style']
    scheme = theme['preset_color_schemes'][style['color_scheme']]
    presets = theme['preset_keys']
    case_height = round((style['keyboard_height'] + style['candidate_view_height']) * DP)
    images = {
        'case.png': case_texture((SCREEN_W, case_height)),
        'tape.9.png': tape_texture(round(style['candidate_view_height'] * DP)),
        'control_down.png': cap_texture('control', 95, 130, True),
    }

    for page in PAGES:
        for cell, (_, _, width, height) in key_geometry(build(theme, page, {})):
            key = cell['key']
            click = key['click']
            action = click if isinstance(click, dict) else presets.get(click, {})
            kind = cap_kind(click, action)
            if kind == 'globe' or (kind == 'glyph' and key.get('key_back_color') == 'fn_back_color'):
                kind = 'control'
            w, h = round(width), round(height)
            for pressed, field in ((False, 'key_back_color'), (True, 'hilited_key_back_color')):
                alias = f'labelmaker_{kind}_{w}x{h}' + ('_down' if pressed else '')
                name = alias + '.png'
                if name not in images:
                    images[name] = cap_texture(kind, w, h, pressed)
                    scheme[alias] = name
                key[field] = alias

            text = 'accent_text' if kind == 'return' else 'key_text_color'
            symbol = 'accent_text' if kind == 'return' else 'key_symbol_color'
            key.update(key_text_color=text, hilited_key_text_color=text,
                       key_symbol_color=symbol, hilited_key_symbol_color=symbol)
            if click == 'Mode_switch':
                key['key_text_size'] = 10
                if key.get('long_click'):
                    key['label_symbol'] = '◑'
            if kind == 'return' and key.get('long_click'):
                key['label_symbol'] = 'CODE'
            key['key_text_offset_y'] = 3 if hint_of(key, presets) else 0
    return theme, images


def sound_assets():
    html = DRAFT.read_text(encoding='utf-8')
    data = json.loads(re.search(r'<script id="labelmaker-sound-data" type="application/json">(.*?)</script>', html, re.S)[1])
    files = {}
    for kind, count in SAMPLES.items():
        if len(data[kind]) != count:
            raise ValueError(f'{kind} 需要 {count} 個定案樣音')
        for index, encoded in enumerate(data[kind], 1):
            wav = b64decode(encoded, validate=True)
            with wave.open(BytesIO(wav)) as sample:
                if (sample.getnchannels(), sample.getsampwidth(), sample.getframerate()) != (1, 2, 24000):
                    raise ValueError(f'{kind}-{index} 不是單聲道 24 kHz、16 位元 PCM')
            files[f'{kind}-{index}.wav'] = wav
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='檢查生成物是否同步')
    args = parser.parse_args()
    theme, images = make_theme()
    sound_dir = RIME_DIR / 'soundeffect'
    descriptor = load_yaml(sound_dir / f'{LABELMAKER_ID}.sound.yaml')
    if DRAFT.is_file():
        sounds = sound_assets()
    else:
        sounds = {name: (sound_dir / LABELMAKER_ID / name).read_bytes()
                  for name in descriptor['sound']}
    if descriptor['folder'] != LABELMAKER_ID or descriptor['sound'] != list(sounds):
        parser.error('音效清單與定案樣音不一致')

    build_path = THEME_DIR / f'{LABELMAKER_ID}.trime.yaml'
    files = {build_path: yaml.safe_dump(theme, allow_unicode=True, sort_keys=True, width=4096).encode()}
    files.update({sound_dir / LABELMAKER_ID / name: wav for name, wav in sounds.items()})
    backgrounds = RIME_DIR / 'backgrounds' / LABELMAKER_ID
    for name, image in images.items():
        path = backgrounds / name
        if args.check:
            if not path.is_file():
                parser.exit(1, f'缺少 {path.relative_to(ROOT)}\n')
            with Image.open(path) as current:
                if (current.mode, current.size, current.tobytes()) != (image.mode, image.size, image.tobytes()):
                    parser.exit(1, f'{path.relative_to(ROOT)} 未同步\n')
        else:
            buffer = BytesIO()
            image.save(buffer, format='PNG', optimize=True)
            files[path] = buffer.getvalue()

    for path, content in files.items():
        if path.is_file() and path.read_bytes() == content:
            continue
        if args.check:
            parser.exit(1, f'{path.relative_to(ROOT)} 缺失或未同步\n')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(f'✓ {build_path.name}，{len(images)} 張背景，{len(sounds)} 個定案音效')


if __name__ == '__main__':
    main()
