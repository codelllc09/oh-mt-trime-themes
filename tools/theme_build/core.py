"""共用鍵帽、鍵盤尺寸與資產輸出。"""

from PIL import Image, ImageColor, ImageDraw

from check_trime import RIME_DIR, THEME_SOURCE_DIR, _deep_merge, load_base_theme, load_yaml
from render_keyboard import DP, build, hint_of, key_geometry

MAIN_PAGES = ('qwerty', 'xuma_L', 'luna_pinyin')
PAGES = (*MAIN_PAGES, 'number', 'number_ascii', 'number_zh', 'symbols', 'mini')
SCALE = 2
KEY_COLORS = {
    'glyph': ('key_text_color', 'key_symbol_color'),
    'control': ('fn_text_color', 'off_key_symbol_color'),
    'number': ('number_text_color', 'number_symbol_color'),
    'return': ('accent_text', 'accent_text'),
    'globe': ('fn_text_color', 'off_key_symbol_color'),
    'space': ('space_text_color', 'space_text_color'),
}


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


def draw_globe(draw, center, radius, color):
    x, y = center
    inner = radius * .45
    draw.ellipse((x - radius, y - radius, x + radius, y + radius), outline=color, width=2 * SCALE)
    draw.ellipse((x - inner, y - radius, x + inner, y + radius), outline=color, width=SCALE)
    draw.line((x - radius, y, x + radius, y), fill=color, width=SCALE)


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


def inherit_skin(theme_id):
    source = load_yaml(THEME_SOURCE_DIR / f'{theme_id}.theme-source.yaml')
    theme = _deep_merge(load_base_theme(), source)
    theme['preset_color_schemes'] = source['preset_color_schemes']
    return theme


def active_scheme(theme):
    return theme['preset_color_schemes'][theme['style']['color_scheme']]


def case_geometry(theme):
    style = theme['style']
    bar = round(style['candidate_view_height'] * DP)
    return bar + round(style['keyboard_height'] * DP), bar


def styled_keys(theme):
    presets = theme['preset_keys']
    for page in PAGES:
        for cell, (_, _, width, height) in key_geometry(build(theme, page, {})):
            key = cell['key']
            click = key['click']
            action = click if isinstance(click, dict) else presets.get(click, {})
            yield page, key, action, round(width), round(height)


def attach_key_images(scheme, key, images, alias, draw_cap, *args):
    for pressed, field in ((False, 'key_back_color'), (True, 'hilited_key_back_color')):
        ref = alias + ('_down' if pressed else '')
        name = ref + '.png'
        scheme[ref] = name
        if name not in images:
            images[name] = draw_cap(*args, pressed)
        key[field] = ref


def skin_keys(theme, images, draw_cap, prefix, *, separate_space=False, classify=None, color_keys=KEY_COLORS):
    """替沿用 V1 的鍵位掛上背景、按下態和對應字色。"""
    scheme = active_scheme(theme)
    presets = theme['preset_keys']
    for page, key, action, w, h in styled_keys(theme):
        click = key['click']
        if classify is None:
            kind = cap_kind(click, action)
            if page == 'number' and isinstance(click, str) and len(click) == 1 and click in '0123456789.-':
                kind = 'number'
                key['key_text_size'] = 22
        else:
            kind = classify(page, click, action)
        if kind == 'space' and not separate_space:
            kind = 'control'
        attach_key_images(scheme, key, images, f'{prefix}_{kind}_{w}x{h}', draw_cap, kind, w, h)

        text, symbol = color_keys[kind]
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


def write_assets(images, files, *, check):
    if check:
        for path, expected in images.items():
            if not path.is_file():
                raise SystemExit(f'[✗] 缺少 {path.relative_to(RIME_DIR)}')
            with Image.open(path) as current:
                if (current.mode, current.size, current.tobytes()) != (
                    expected.mode, expected.size, expected.tobytes()
                ):
                    raise SystemExit(f'[✗] {path.relative_to(RIME_DIR)} 未同步')
        for path, contents in files.items():
            if not path.is_file() or path.read_bytes() != contents:
                raise SystemExit(f'[✗] {path.relative_to(RIME_DIR)} 缺失或未同步')
        return

    for path, image in images.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, optimize=True)
    for path, contents in files.items():
        if not path.is_file() or path.read_bytes() != contents:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(contents)
