"""鍵帽外觀與字樣排版。"""

from functools import cache, lru_cache
import math

from PIL import Image, ImageColor, ImageDraw

from render_keyboard import DP, SCREEN_W, hint_of, label_of
from .core import (
    MAIN_PAGES, SCALE, active_scheme, attach_key_images, cap_kind, draw_globe,
    gradient, rounded_layer, skin_keys, styled_keys,
)


CAP_PALETTES = {
    'glyph': ('#fff2d6', '#dac7a0'),
    'porcelain': ('#fffae9', '#e5dfce'),
    'control': ('#4d5d4d', '#232e24'),
    'globe': ('#4d5d4d', '#232e24'),
    'space': ('#434b3e', '#242e25'),
    'return': ('#a14c52', '#55282f'),
}
UI_HINTS = {'Shift_L': '⇪', 'BackSpace': '×…', 'Mode_switch': '◑', 'Return': 'CODE'}


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
def typewriter_cap(kind, width, height, pressed):
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


def typewriter_case():
    width, height = 1080, 762
    image = gradient((width, height), '#375747', '#1b2c23')
    draw = ImageDraw.Draw(image)
    for x in range(0, width, 14):
        draw.line((x, 0, x, height), fill='#263b2f', width=1)
    draw.rounded_rectangle((4, 3, width - 5, height - 4), radius=27, outline='#7c8668', width=2)
    return image.convert('RGB')


def typewriter(theme_id, theme):
    images = {'case.png': typewriter_case()}
    scheme = active_scheme(theme)
    presets = theme['preset_keys']
    for page, key, action, w, h in styled_keys(theme):
        click = key["click"]
        kind = cap_kind(click, action)
        if page == 'number' and isinstance(click, str) and len(click) == 1 and click in '0123456789':
            kind = 'porcelain'
        attach_key_images(scheme, key, images, f'v2_{kind}_{w}x{h}',
                          typewriter_cap, kind, w, h)

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


CALCULATOR_CAPS = {
    'glyph': (('#535C56', '#3E4945'), ('#46504A', '#353F3B')),
    'control': (('#39443E', '#29322E'), ('#313B35', '#232D28')),
    'number': (('#EBE6D7', '#C9C8B7'), ('#DAD5C4', '#B5B5A4')),
    'return': (('#EAB16B', '#CE8E3E'), ('#D69B53', '#B87C34')),
}


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


@cache
def calculator_cap(kind, width, height, pressed):
    normal, down = CALCULATOR_CAPS['control' if kind == 'globe' else kind]
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


def calculator(theme_id, theme):
    case_size = SCREEN_W, round(theme['style']['keyboard_height'] * DP)
    images = {
        'case.png': gradient(case_size, '#454943', '#303731').convert('RGB'),
        'lcd.png': lcd_texture(),
    }
    skin_keys(theme, images, calculator_cap, 'calc')
    return images


LABELMAKER_CAPS = {
    'glyph': (('#484E45', '#363B33'), ('#3D443A', '#2E342B')),
    'control': (('#32372F', '#232720'), ('#292E27', '#1F241D')),
    'space': (('#2C3029', '#232720'), ('#272B24', '#1F241D')),
    'return': (('#E9B86A', '#D99C49'), ('#D8A052', '#BC8037')),
}


def labelmaker_case(size):
    width, height = size
    image = gradient(size, '#41473E', '#282C26').convert('RGB')
    grain = ImageDraw.Draw(image, 'RGBA')
    for x in range(0, width + height, 6):
        grain.line((x, 0, x - height, height), fill=(255, 255, 242, 10))
    return image


def tape_texture(height):
    width = SCREEN_W
    image = labelmaker_case((width, height)).convert('RGBA')
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


def labelmaker_cap(kind, width, height, pressed):
    up, down = LABELMAKER_CAPS[kind]
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


def labelmaker(theme_id, theme):
    style = theme['style']
    scheme = active_scheme(theme)
    presets = theme['preset_keys']
    case_height = round((style['keyboard_height'] + style['candidate_view_height']) * DP)
    images = {
        'case.png': labelmaker_case((SCREEN_W, case_height)),
        'tape.9.png': tape_texture(round(style['candidate_view_height'] * DP)),
        'control_down.png': labelmaker_cap('control', 95, 130, True),
    }

    for _, key, action, w, h in styled_keys(theme):
        click = key["click"]
        kind = cap_kind(click, action)
        if kind == 'globe' or (kind == 'glyph' and key.get('key_back_color') == 'fn_back_color'):
            kind = 'control'
        attach_key_images(scheme, key, images, f'labelmaker_{kind}_{w}x{h}',
                          labelmaker_cap, kind, w, h)

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
    return images
