#!/usr/bin/env python3
"""從 V1 和液晶計算機外觀源檔生成同文主題及背景。"""

import argparse
from functools import cache

from PIL import Image, ImageDraw
import yaml

from check_trime import (
    CALCULATOR_ID, RIME_DIR, THEME_DIR, THEME_SOURCE, THEME_SOURCE_DIR,
    _deep_merge, load_yaml, resolve_theme,
)
from gen_typewriter import PAGES, cap_kind, gradient, rounded_layer
from render_keyboard import DP, SCREEN_W, build, hint_of, key_geometry


CAPS = {
    'glyph': (('#535C56', '#3E4945'), ('#46504A', '#353F3B'), 'key_text_color', 'key_symbol_color'),
    'control': (('#39443E', '#29322E'), ('#313B35', '#232D28'), 'fn_text_color', 'off_key_symbol_color'),
    'number': (('#EBE6D7', '#C9C8B7'), ('#DAD5C4', '#B5B5A4'), 'number_text_color', 'number_symbol_color'),
    'return': (('#EAB16B', '#CE8E3E'), ('#D69B53', '#B87C34'), 'accent_text', 'accent_text'),
}
SCALE = 2


def lcd_texture():
    size = SCREEN_W, 136
    image = gradient(size, '#454943', '#3C423D')
    rounded_layer(image, (10, 5, SCREEN_W - 10, 131), 11, '#202820', '#505C4C')
    rounded_layer(image, (16, 10, SCREEN_W - 16, 126), 7, '#A5BB85', '#C2CF9E')
    image = image.convert('RGB')
    lines = ImageDraw.Draw(image, 'RGBA')
    for y in range(16, 122, 7):
        lines.line((20, y, SCREEN_W - 21, y), fill=(47, 76, 39, 18))
    return image


def draw_globe(draw, center, radius, color):
    x, y = center
    inner = radius * .45
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2 * SCALE)
    draw.ellipse((x - inner, y - radius, x + inner, y + radius), outline=color, width=SCALE)
    draw.line((x - radius, y, x + radius, y), fill=color, width=SCALE)


@cache
def cap_texture(kind, width, height, pressed):
    normal, down, _, _ = CAPS['control' if kind == 'globe' else kind]
    w, h = width * SCALE, height * SCALE
    image = Image.new('RGBA', (w, h))
    depth = (2 if pressed else 6) * SCALE
    top = (5 if pressed else 1) * SCALE
    radius = 10 * SCALE
    rounded_layer(image, (0, top, w, h), radius, '#202823', '#1C231E')
    rounded_layer(image, (2, top + 2, w - 2, h - depth), radius - 2, *(down if pressed else normal))
    draw = ImageDraw.Draw(image)
    edge = image.getpixel((radius, top + 3))[:3]
    shine = tuple(round((value * 4 + 255) / 5) for value in edge)
    draw.line((radius, top + 3, w - radius, top + 3), fill=shine, width=SCALE)
    if kind == 'globe':
        x, y = w / 2, h * .56 + (3 * SCALE if pressed else 0)
        draw_globe(draw, (x, y), min(w, h) * .225, '#F0E2BE')
    return image.resize((width, height), Image.Resampling.LANCZOS)


def inherit_skin(theme_id):
    base = load_yaml(THEME_DIR / 'vendor' / 'trime-3.3.13.yaml')
    inherited = resolve_theme(load_yaml(THEME_SOURCE), base)
    source = load_yaml(THEME_SOURCE_DIR / f'{theme_id}.theme-source.yaml')
    theme = _deep_merge(inherited, source)
    theme['preset_color_schemes'] = source['preset_color_schemes']
    return theme


def skin_keys(theme, images, draw_cap, prefix, *, separate_space=False, classify=None, color_keys=None):
    """替沿用 V1 的鍵位掛上背景、按下態和對應字色。"""
    scheme = theme['preset_color_schemes'][theme['style']['color_scheme']]
    presets = theme['preset_keys']
    for page in PAGES:
        for cell, (_, _, width, height) in key_geometry(build(theme, page, {})):
            key = cell['key']
            click = key['click']
            action = click if isinstance(click, dict) else presets.get(click, {})
            if classify is None:
                kind = cap_kind(click, action)
                if page == 'number' and isinstance(click, str) and len(click) == 1 and click in '0123456789.-':
                    kind = 'number'
                    key['key_text_size'] = 22
            else:
                kind = classify(page, click, action)
            if kind == 'space' and not separate_space:
                kind = 'control'
            w, h = round(width), round(height)
            for pressed, field in ((False, 'key_back_color'), (True, 'hilited_key_back_color')):
                alias = f'{prefix}_{kind}_{w}x{h}' + ('_down' if pressed else '')
                name = alias + '.png'
                scheme[alias] = name
                if name not in images:
                    images[name] = draw_cap(kind, w, h, pressed)
                key[field] = alias

            if color_keys is not None:
                text, symbol = color_keys[kind]
            elif kind == 'space':
                text = symbol = 'space_text_color'
            else:
                _, _, text, symbol = CAPS['control' if kind == 'globe' else kind]
            if key.get('popup'):
                symbol = 'nav_text_color'
            key.update(key_text_color=text, hilited_key_text_color=text,
                       key_symbol_color=symbol, hilited_key_symbol_color=symbol)
            if kind == 'globe':
                key['label'] = ' '
                if key.get('long_click'):
                    key['label_symbol'] = '◑'
            elif kind == 'return' and key.get('long_click'):
                key['label_symbol'] = 'CODE'
            key['key_text_offset_y'] = 3 if hint_of(key, presets) else 0


def make_theme():
    theme = inherit_skin(CALCULATOR_ID)
    case_size = SCREEN_W, round(theme['style']['keyboard_height'] * DP)
    images = {
        'case.png': gradient(case_size, '#454943', '#303731').convert('RGB'),
        'lcd.png': lcd_texture(),
    }
    skin_keys(theme, images, cap_texture, 'calc')
    return theme, images


def write_theme_assets(theme_id, theme, images, *, check):
    build_path = THEME_DIR / f'{theme_id}.trime.yaml'
    assets = RIME_DIR / 'backgrounds' / theme_id
    output = yaml.safe_dump(theme, allow_unicode=True, sort_keys=True, width=4096)
    if check:
        if not build_path.is_file() or build_path.read_text(encoding='utf-8') != output:
            raise SystemExit(f'{build_path.name} 未同步')
        for name, expected in images.items():
            path = assets / name
            if not path.is_file():
                raise SystemExit(f'缺少 {path.name}')
            with Image.open(path) as current:
                if (current.mode, current.size, current.tobytes()) != (expected.mode, expected.size, expected.tobytes()):
                    raise SystemExit(f'{path.name} 未同步')
        print(f'✓ {build_path.name} 和 {len(images)} 張背景同步')
        return

    assets.mkdir(parents=True, exist_ok=True)
    for name, image in images.items():
        image.save(assets / name, optimize=True)
    build_path.write_text(output, encoding='utf-8')
    print(f'✓ {build_path.name}，{len(images)} 張背景')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='檢查生成物是否同步')
    args = parser.parse_args()
    theme, images = make_theme()
    write_theme_assets(CALCULATOR_ID, theme, images, check=args.check)


if __name__ == '__main__':
    main()
