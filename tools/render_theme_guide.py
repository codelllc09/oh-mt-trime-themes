#!/usr/bin/env python3
"""從 Trime 主題生成配色總覽，並為 V1 生成互動鍵位指南。"""

import argparse
from base64 import b64encode
from dataclasses import dataclass, field
from functools import cache
from html import escape
from io import BytesIO
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree

from fontTools.pens.basePen import BasePen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont
from PIL import Image, ImageChops, ImageColor, ImageDraw, ImageFont, ImageOps
import yaml

from aesthetics import contrast
from check_trime import THEME_DIR, THEME_SOURCE, resolve_theme
from render_keyboard import DP, ROOT, SCREEN_W, build, css_color, key_geometry, label_of, resolve_color

PAGE_NAMES = {
    'qwerty': '通用主鍵盤', 'number': '數字小鍵盤', 'number_ascii': 'ASCII 符號頁',
    'number_zh': '中文標點頁', 'symbols': '預設符號頁',
}
GESTURES = {
    'click': '點按', 'long_click': '長按', 'double_click': '雙擊', 'lazy_double_click': '雙擊',
    'swipe_left': '左滑', 'swipe_right': '右滑', 'swipe_up': '上滑', 'swipe_down': '下滑',
    'combo': '組合按鍵', 'ascii': '英文模式', 'paging': '候選翻頁時',
    'has_menu': '有候選時', 'composing': '組稿時',
}
KEY_EVENTS = {
    'Control+a': '全選', 'Control+x': '剪切', 'Control+c': '複製', 'Control+v': '粘貼',
    'Control+z': '撤銷', 'Control+y': '重做',
    'Control+Shift+Return': '觸發 CommitComment（Ctrl+Shift+Enter）',
    'Shift_L': '切換大小寫', 'Tab': '發送 Tab', 'BackSpace': '刪除光標前的內容',
    'Delete': '刪除光標後的內容', 'Escape': '發送 Esc',
    'Home': '發送 Home，通常移到行首', 'End': '發送 End，通常移到行尾',
    'Up': '發送向上方向鍵', 'Down': '發送向下方向鍵',
    'Left': '發送向左方向鍵', 'Right': '發送向右方向鍵',
    'Page_Up': '發送 Page Up', 'Page_Down': '發送 Page Down',
    'MENU': '開啓輸入方案選單', 'BACK': '收起鍵盤',
    'VOICE_ASSIST': '開啓 Android 已啓用的相容語音輸入法',
    'Return': '按輸入框指定的動作操作，例如換行、搜索或發送',
    'PROG_RED': '切換配色', 'SETTINGS': '開啓同文設定',
}
COMMANDS = {
    'clipboard': '粘貼系統剪貼板內容', 'clipboard_window': '打開剪貼板面板',
    'liquid_keyboard': '打開擴展鍵盤面板',
    'date': '輸入日期',
}
TOGGLES = {'ascii_mode': '切換中英輸入', 'full_shape': '切換半角／全角（彎月為半角，實心圓為全角）'}
ENTER_NAMES = {
    'default': '普通回車', 'send': '發送', 'search': '搜索', 'go': '前往',
    'done': '完成', 'next': '下一項', 'pre': '上一項',
}
# 以 24 × 24 的簡化線稿呈現 Trime 圖標。背景圖片直接讀主題資產。
ICONS = {
    'send': [('polygon', (2, 3, 23, 12, 2, 21, 2, 14, 15, 12, 2, 10))],
    'magnify': [('ellipse', (3, 3, 15, 15)), ('line', (14, 14, 21, 21))],
    'keyboard_return': [('line', (21, 5, 21, 13, 3, 13)), ('line', (9, 7, 3, 13, 9, 19))],
    'arrow_right': [('line', (3, 12, 21, 12)), ('line', (14, 5, 21, 12, 14, 19))],
    'check_bold': [('line', (4, 12, 9, 17, 20, 6))],
    'keyboard_tab': [('line', (2, 12, 17, 12)), ('line', (12, 7, 17, 12, 12, 17)), ('line', (21, 5, 21, 19))],
    'keyboard_tab_reverse': [('line', (7, 12, 22, 12)), ('line', (12, 7, 7, 12, 12, 17)), ('line', (3, 5, 3, 19))],
    'text_box_check_outline': [
        ('line', (10, 21, 3, 21, 3, 3, 21, 3, 21, 12)), ('line', (7, 8, 17, 8)),
        ('line', (7, 12, 14, 12)), ('line', (7, 16, 10, 16)), ('line', (13, 18, 16, 21, 22, 15)),
    ],
    'menu_down': [('polygon', (3, 8, 21, 8, 12, 18))],
    'moon_waxing_crescent': [('polygon', (6, 2, 12, 2, 17, 4, 20, 8, 21, 12, 20, 16,
                                           17, 20, 12, 22, 6, 22, 10, 19, 12, 15, 13, 12, 12, 9, 10, 5))],
    'moon_full': [('disc', (3, 3, 21, 21))],
}

CLIPBOARD_ICONS = ROOT / 'tools' / 'assets' / 'trime-clipboard-icons.svg'

MARGIN = 30
CAPTION_H = 82
CALLOUT = '#087C82'


def read_yaml(path):
    return yaml.safe_load(path.read_text(encoding='utf-8'))


def preset(value, presets):
    if isinstance(value, dict):
        return value
    return presets.get(str(value), {})


def page_name(name, keyboards):
    return PAGE_NAMES.get(name) or str(keyboards.get(name, {}).get('name') or name)


def key_routes(keyboard, presets):
    for key in keyboard['keys']:
        if isinstance(key, dict):
            for event, gesture in GESTURES.items():
                if target := preset(key.get(event), presets).get('select'):
                    yield target, f'{gesture} {label_of(key, presets)}'


def reachable_pages(starts, theme):
    keyboards = theme['preset_keyboards']
    pages = list(starts)
    presets = theme.get('preset_keys', {})
    seen = set(pages)
    for name in pages:
        keyboard = keyboards[name]
        destinations = [keyboard.get('ascii_keyboard'), keyboard.get('landscape_keyboard')]
        destinations.extend(target for target, _ in key_routes(keyboard, presets))
        for target in destinations:
            if target not in seen and keyboards.get(target, {}).get('keys'):
                pages.append(target)
                seen.add(target)
    return pages


def guide_pages(source, theme):
    keyboards = theme['preset_keyboards']
    own = source['preset_keyboards']
    if 'qwerty' in own and keyboards.get('qwerty', {}).get('keys'):
        return reachable_pages(['qwerty'], theme)
    pages = [name for name in own if keyboards.get(name, {}).get('keys')]
    return reachable_pages(pages, theme)


def describe(value, trigger, theme):
    if value is None:
        return None
    action = preset(value, theme.get('preset_keys', {}))
    send = action.get('send')
    if action.get('select'):
        target = action['select']
        if target == '.default':
            return '返回當前輸入方案的主鍵盤'
        if target in {'.next', '.prior', '.last', '.ascii'}:
            return f'切換鍵盤（{target}）'
        return f'跳轉至{page_name(target, theme["preset_keyboards"])}'
    if toggle := action.get('toggle'):
        if toggle.startswith('_one_hand_mode') and action.get('states'):
            return f'切換單手選項（{"／".join(action["states"])}）'
        return TOGGLES.get(toggle, f'切換「{toggle}」設定')
    if send == 'SETTINGS' and action.get('option') == 'theme':
        return '開啓主題選單'
    if command := action.get('command'):
        if command == 'date' and str(action.get('option', '')).startswith(('H', 'h')):
            return '輸入時間'
        return COMMANDS.get(command, f'執行「{command}」命令')
    if trigger == 'composing' and send == 'Return':
        return '點按將組稿上屏'
    if value == 'grave_lead' and send == '`':
        return '送出反引號 `'
    if send in KEY_EVENTS:
        return KEY_EVENTS[send]
    if send and send != 'space' and len(str(send)) > 1:
        return f'發送 {send}'
    if action.get('commit') and len(str(action['commit'])) > 1:
        return f'提交「{action["commit"]}」'
    content = str(action.get('text', value))
    if content.endswith('{Left}') and len(content.removesuffix('{Left}')) == 2:
        pair = content.removesuffix('{Left}')
        return f'一次輸入一對括號 {pair}，光標停在中間'
    if trigger == 'has_menu' and content == "'":
        return '點按輸入撇號'
    if trigger == 'ascii' and send == 'space' and action.get('label'):
        return f'空格鍵帽顯示 {action["label"]}'
    return None


def key_notes(key, theme):
    lines = []
    for trigger, label in GESTURES.items():
        if description := describe(key.get(trigger), trigger, theme):
            lines.append((label, description))
        if trigger == 'long_click' and (choices := key.get('popup')):
            symbols = '　'.join(label_of({'click': value}, theme['preset_keys']) for value in choices)
            lines.append((label, f'展開符號選單（{symbols}）'))
        if trigger == 'long_click' and not key.get(trigger):
            click = preset(key.get('click'), theme['preset_keys'])
            if click.get('repeatable'):
                lines.append((label, '連續執行點按動作'))
            if click.get('shift_lock') == 'ascii_long':
                lines.append((label, '在英文模式鎖定大寫'))
    return lines


@cache
def matched_font(family):
    try:
        result = subprocess.check_output(['fc-match', '-f', '%{file}\t%{index}', family], text=True)
        path, index = result.split('\t')
        return Path(path), int(index) & 0xffff
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


@cache
def characters(spec):
    with TTFont(spec[0], fontNumber=spec[1], lazy=True) as font:
        return frozenset(font.getBestCmap())


@cache
def loaded_font(spec, size):
    font = ImageFont.truetype(str(spec[0]), size, index=spec[1])
    if spec[0].suffix.lower() == '.ttc':
        try:
            font.set_variation_by_name('Regular')
        except OSError:
            pass
    return font


class Typography:
    def __init__(self, style, asset_root, ui_font):
        self.ui = (ui_font, 0) if ui_font else matched_font('Noto Sans CJK TC:lang=zh-tw')
        if not self.ui or ord('鍵') not in characters(self.ui):
            raise SystemExit('需要繁體中文字體。請安裝 Noto Sans CJK 或傳入 --font。')
        key_fonts = []
        for name in ('latin_font', 'key_font'):
            filenames = style.get(name) or []
            if isinstance(filenames, str):
                filenames = [filenames]
            key_fonts.extend((asset_root / 'fonts' / filename, 0) for filename in filenames)
        fallbacks = [self.ui, matched_font('Noto Sans Symbols 2'), matched_font('DejaVu Sans')]
        self.keys = [font for font in [*key_fonts, *fallbacks] if font and font[0].is_file()]

    def font(self, text, size, ui=False):
        fonts = [self.ui, *self.keys] if ui else self.keys
        required = {ord(ch) for ch in text}
        spec = next((font for font in fonts if required <= characters(font)), None)
        if spec is None:
            charset = ' '.join(f'{cp:x}' for cp in sorted(required))
            spec = matched_font(f'sans-serif:charset={charset}')
        return loaded_font(spec or self.ui, max(1, round(size)))

    def text(self, draw, xy, text, size, fill, *, anchor='mm', ui=False):
        draw.text(xy, text, font=self.font(text, size, ui), fill=fill, anchor=anchor)


def rgb(value, fallback):
    if value and value.startswith('rgba('):
        red, green, blue, _alpha = value[5:-1].split(',')
        return int(red), int(green), int(blue)
    try:
        return ImageColor.getrgb(value or fallback)
    except ValueError:
        return ImageColor.getrgb(fallback)


def background_file(assets, style, value):
    if not value or Path(value).suffix.lower() not in {'.png', '.webp', '.jpg', '.jpeg'}:
        return None
    folder = assets / 'backgrounds'
    return next((path for path in (folder / style.get('background_folder', '') / value, folder / value)
                 if path.is_file()), None)


@cache
def load_background(path):
    with Image.open(path) as image:
        return image.convert('RGBA')


class IconPen(BasePen):
    def __init__(self, size):
        super().__init__()
        self.scale = size / 1024
        self.mask = Image.new('1', (size, size))

    def _moveTo(self, point):
        self.points = [point]

    def _lineTo(self, point):
        self.points.append(point)

    def _qCurveToOne(self, control, end):
        start = self.points[-1]
        for i in range(1, 9):
            t = i / 8
            self.points.append(tuple((1 - t)**2 * a + 2 * (1 - t) * t * b + t**2 * c
                                     for a, b, c in zip(start, control, end)))

    def _closePath(self):
        contour = Image.new('1', self.mask.size)
        ImageDraw.Draw(contour).polygon([(x * self.scale, y * self.scale) for x, y in self.points], fill=1)
        self.mask = ImageChops.logical_xor(self.mask, contour)


@cache
def clipboard_icon_mask(name, size):
    path = ElementTree.parse(CLIPBOARD_ICONS).find(f".//{{*}}path[@id='{name}']")
    if path is None:
        raise ValueError(f'缺少同文圖標 {name}')
    pen = IconPen(4 * size)
    parse_path(path.attrib['d'], pen)
    return pen.mask.convert('L').resize((size, size), Image.Resampling.LANCZOS)


def paint_icon(draw, center, label, size, color, fonts):
    name = label.removeprefix('ic@').replace('-', '_')
    if label.startswith('ic@') and name in ('clipboard_text_outline', 'script_outline'):
        mask = clipboard_icon_mask(name, round(size))
        draw.bitmap(tuple(round(coordinate - size / 2) for coordinate in center), mask, fill=color)
        return
    shapes = ICONS.get(name) if label.startswith('ic@') else None
    if shapes is None:
        text = label.removeprefix('ic@')
        fonts.text(draw, center, text, size if text == label else size / 2, color)
        return
    x, y = center
    line_width = max(2, round(size / 9))
    for kind, coords in shapes:
        points = [(x + (dx - 12) * size / 24, y + (dy - 12) * size / 24)
                  for dx, dy in zip(coords[::2], coords[1::2])]
        if kind == 'line':
            draw.line(points, fill=color, width=line_width, joint='curve')
        elif kind == 'ellipse':
            draw.ellipse(points, outline=color, width=line_width)
        elif kind == 'disc':
            draw.ellipse(points, fill=color)
        else:
            draw.polygon(points, fill=color)


@dataclass
class Note:
    number: int
    label: str
    lines: list


@dataclass
class Panel:
    name: str
    image: Image.Image
    markers: dict = field(default_factory=dict)


def mark(draw, fonts, number, box):
    left, top, width, _ = box
    center = (left + min(13, width / 4), top + 8)
    x, y = center
    draw.line((x + 7, y + 7, x + 19, y + 19), fill='#FFFFFF', width=5)
    draw.line((x + 7, y + 7, x + 19, y + 19), fill=CALLOUT, width=3)
    draw.polygon((x + 20, y + 20, x + 17, y + 12, x + 12, y + 17), fill=CALLOUT)
    draw.ellipse((x - 14, y - 14, x + 14, y + 14), fill=CALLOUT, outline='#FFFFFF', width=2)
    fonts.text(draw, center, str(number), 16, '#FFFFFF')
    return center


def captions(draw, fonts, title, subtitle, ink, muted, width=SCREEN_W):
    fonts.text(draw, (22, 32), title, 38, ink, anchor='lm', ui=True)
    fonts.text(draw, (width - 22, 36), subtitle, 22, muted, anchor='rm', ui=True)


def draw_board(page, model, theme, scheme, fonts, assets, notes, palette, *, ascii_mode=None):
    style = theme['style']
    presets = theme['preset_keys']
    keyboard = theme['preset_keyboards'][page]
    name = page_name(page, theme['preset_keyboards'])
    is_ascii = keyboard.get('ascii_mode') == 1 if ascii_mode is None else ascii_mode
    if ascii_mode is not None:
        name += ' · 英文態' if is_ascii else ' · 中文態'
    toolbar_h = round(style.get('candidate_view_height', 40) * DP)
    keys_y = CAPTION_H + toolbar_h
    height = keys_y + round(model['cell_h'] * len(model['rows']))
    paper, ink, muted = palette
    panel = Panel(name, Image.new('RGB', (SCREEN_W, height), paper))
    draw = ImageDraw.Draw(panel.image)
    captions(draw, fonts, name, page, ink, muted)
    colors = model['scheme']
    draw.rectangle((0, keys_y, SCREEN_W, height), fill=rgb(colors['bg'], '#17191C'))
    case = background_file(assets, style, resolve_color('keyboard_background', scheme, colors['bg']))
    if case:
        texture = ImageOps.fit(load_background(case), (SCREEN_W, height - CAPTION_H),
                               Image.Resampling.LANCZOS)
        panel.image.paste(texture, (0, CAPTION_H), texture)
    bar = resolve_color('candidate_background', scheme, css_color(scheme.get('back_color')))
    if bar_file := background_file(assets, style, bar):
        display = load_background(bar_file)
        if bar_file.name.endswith('.9.png') and display.getpixel((0, 0))[3] == 0:
            # 原始 NinePatch 的一像素標記框不屬於畫面。
            display = display.crop((1, 1, display.width - 1, display.height - 1))
        display = display.resize((SCREEN_W, toolbar_h), Image.Resampling.LANCZOS)
        panel.image.paste(display, (0, CAPTION_H), display)
    else:
        draw.rectangle((0, CAPTION_H, SCREEN_W, keys_y - 1), fill=rgb(bar, '#F5F6FA'))
    tool_color = rgb(css_color(scheme.get('candidate_text_color')), '#232832')
    fonts.text(draw, (54, CAPTION_H + toolbar_h / 2), '•••', 28, tool_color)
    for i, button in enumerate(theme.get('tool_bar', {}).get('buttons', [])):
        foreground = button.get('foreground', {})
        label = foreground.get('style') or next(iter(foreground.get('option_styles', [])), '')
        center = SCREEN_W - 65 - i * 134, CAPTION_H + toolbar_h / 2
        paint_icon(draw, center, label, 55, tool_color, fonts)
        if note := notes.get(('toolbar', i)):
            panel.markers[note.number] = mark(draw, fonts, note.number, (center[0] - 60, center[1] - 24, 60, 30))

    boxes = []
    for i, (cell, box) in enumerate(key_geometry(model)):
        key = cell['key'] if isinstance(cell['key'], dict) else {'click': cell['key']}
        x, y, width, h = box
        y += keys_y
        active = key.get('ascii') if is_ascii else None
        label = label_of({'click': active}, presets) if active is not None else cell['label']
        if label == 'enter_labels':
            label = style.get('enter_labels', {}).get('default', '↵')
        if not is_ascii and keyboard.get('label_transform') == 'uppercase':
            label = label.upper() if not label.startswith('ic@') else label
        if label == 'space':
            label = '方案名稱' if page == 'qwerty' else '空格'
        click = preset(key.get('click'), presets)
        hint = cell['hint']
        if not hint and 'label_symbol' not in key:
            long = key.get('long_click')
            if isinstance(long, str) and long.endswith('{Left}'):
                hint = long.removesuffix('{Left}')
        bg = cell['bg'] or colors[cell['cls']]
        fg = cell['fg'] or colors[{'key': 'text', 'fn': 'fn_text', 'accent': 'accent_text'}[cell['cls']]]
        fg = rgb(fg, '#16191E')
        icon_file = background_file(assets, style, bg)
        if icon_file:
            overlay = load_background(icon_file).resize((round(width), round(h)), Image.Resampling.LANCZOS)
            panel.image.paste(overlay, (round(x), round(y)), overlay)
            if click.get('toggle') == 'ascii_mode' and label == str(key.get('click')):
                label = ''
        else:
            draw.rounded_rectangle((x, y, x + width, y + h), radius=model['radius'] * DP,
                                   fill=rgb(bg, '#33363B'))
            if click.get('toggle') == 'ascii_mode' and (not label.strip() or label == str(key.get('click'))):
                label = '中／英'
        ts = cell['text_size'] or (model['long_text_size'] if len(label) > 1 else model['text_size'])
        if label.startswith('ic@'):
            ts = cell['text_size'] or model['text_size']
        dx = float(key.get('key_text_offset_x', keyboard.get('key_text_offset_x', 0))) * DP
        dy = float(key.get('key_text_offset_y', model['text_offset_y'])) * DP
        sym_size = float(key.get('symbol_text_size') or model['sym_size']) * DP
        sym_dx = float(key.get('key_symbol_offset_x') or keyboard.get('key_symbol_offset_x')
                       or style.get('key_symbol_offset_x', 0)) * DP
        sym_dy = float(key.get('key_symbol_offset_y') or keyboard.get('key_symbol_offset_y')
                       or style.get('key_symbol_offset_y', 0)) * DP
        positioned = bool(key.get('symbol_text_size') or sym_dy)
        if label.strip():
            paint_icon(draw, (x + width / 2 + dx, y + h / 2 + dy + (7 if hint and not positioned else 0)),
                       label, ts * DP, fg, fonts)
        if hint:
            sym_y = y + (sym_size * (.5 if hint.startswith('ic@') else .72) + sym_dy if positioned else 16)
            paint_icon(draw, (x + width / 2 + sym_dx, sym_y), hint, sym_size,
                       rgb(cell['sy'] or colors['hint'], '#80858F'), fonts)
        if note := notes.get(i):
            boxes.append((note.number, (x, y, width, h)))
    for number, box in boxes:
        panel.markers[number] = mark(draw, fonts, number, box)
    return panel


def enter_labels(theme, pages):
    configured = theme['style'].get('enter_labels', {})
    labels = [(ENTER_NAMES.get(state, state), configured[state])
              for state in dict.fromkeys([*ENTER_NAMES, *configured]) if state in configured]
    for page in pages:
        for key in theme['preset_keyboards'][page]['keys']:
            if not isinstance(key, dict):
                continue
            composing = preset(key.get('composing'), theme['preset_keys'])
            if composing.get('send') == 'Return' and (label := composing.get('label')):
                item = ('上屏', label)
                if item not in labels:
                    labels.append(item)
    return labels


def draw_states(theme, scheme, pages, fonts, assets, palette, width=SCREEN_W):
    paper, ink, muted = palette
    labels = enter_labels(theme, pages)
    columns = width // 270
    height = CAPTION_H + 42 + 167 * ((len(labels) + columns - 1) // columns)
    panel = Panel('回車鍵帽', Image.new('RGB', (width, height), paper))
    draw = ImageDraw.Draw(panel.image)
    captions(draw, fonts, panel.name, '依 App 與組稿狀態切換', ink, muted, width)
    background = rgb(css_color(scheme.get('keyboard_back_color')), '#16181E')
    draw.rounded_rectangle((0, CAPTION_H, width, height), radius=22, fill=background)
    fill = rgb(css_color(scheme.get('accent_fill')), '#1A73E8')
    text = rgb(css_color(scheme.get('accent_text')), '#FFFFFF')
    caption = rgb(css_color(scheme.get('key_text_color')), '#F1F3F6')
    face = next((key for page in pages for key in theme['preset_keyboards'][page]['keys']
                 if isinstance(key, dict) and key.get('click') == 'Return'), {})
    filename = background_file(assets, theme['style'], resolve_color(face.get('key_back_color'), scheme, None))
    cap = ImageOps.contain(load_background(filename), (144, 116), Image.Resampling.LANCZOS) if filename else None
    if cap:
        caption = rgb(css_color(scheme.get('off_key_text_color')), '#F1F3F6')
    if contrast('#%02x%02x%02x' % caption[:3], '#%02x%02x%02x' % background[:3]) < 4.5:
        caption = ink
    for i, (label, icon) in enumerate(labels):
        x = width / columns * (i % columns + .5)
        y = CAPTION_H + 27 + 167 * (i // columns)
        if cap:
            panel.image.paste(cap, (round(x - cap.width / 2), round(y + 48 - cap.height / 2)), cap)
        else:
            draw.rounded_rectangle((x - 72, y, x + 72, y + 96), radius=21, fill=fill)
        paint_icon(draw, (x, y + 48), str(icon), 42 if cap else 54, text, fonts)
        fonts.text(draw, (x, y + 127), label, 29, caption, ui=True)
    return panel


def collect_notes(theme, models):
    next_number = 1
    sections = {}
    for page, model in models.items():
        notes = {}
        candidates = []
        for i, (cell, _) in enumerate(key_geometry(model)):
            if not isinstance(cell['key'], dict):
                continue
            key = cell['key']
            lines = key_notes(key, theme)
            if lines:
                action = preset(key.get('click'), theme['preset_keys'])
                label = {'Mode_switch': '地球／中英切換', 'Return': '回車', 'space': '空格'}.get(
                    str(key.get('click')), cell['label'])
                candidates.append((not action.get('select'), i, label, lines))
        for _, i, label, lines in sorted(candidates):
            notes[i] = Note(next_number, label, lines)
            next_number += 1
        if page == next(iter(models)):
            for i, button in enumerate(theme.get('tool_bar', {}).get('buttons', [])):
                action = button.get('action')
                if description := describe(action, 'click', theme):
                    name = {'Hide': '工具欄 · 收起', 'Zenkaku_Hankaku': '工具欄 · 全半角'}.get(action, str(action))
                    notes['toolbar', i] = Note(next_number, name, [('點按', description)])
                    next_number += 1
        sections[page] = notes
    return sections


def guide_panels(panels):
    for page, views in panels.items():
        for index, panel in enumerate(views):
            yield f'{page}-ascii' if index else page, panel


def make_sheet(panels, states, theme_name, scheme_name, fonts, palette, *, include_html):
    paper, ink, muted = palette
    width = SCREEN_W * 2 + MARGIN * 3
    views = [panel for _, panel in guide_panels(panels)]
    rows = [views[i:i + 2] for i in range(0, len(views), 2)]
    y = 148
    height = y + sum(max(panel.image.height for panel in row) + MARGIN for row in rows)
    if states:
        height += states.image.height + MARGIN
    sheet = Image.new('RGB', (width, height), paper)
    draw = ImageDraw.Draw(sheet)
    fonts.text(draw, (MARGIN, 46), f'{theme_name}  /  {scheme_name}', 56, ink, anchor='lm', ui=True)
    subtitle = '鍵盤總覽     1080p · 420 dpi'
    if include_html:
        subtitle += '     編號對照 HTML 鍵位說明'
    fonts.text(draw, (MARGIN, 108), subtitle, 26, muted, anchor='lm', ui=True)
    for row in rows:
        for column, panel in enumerate(row):
            sheet.paste(panel.image, (MARGIN + column * (SCREEN_W + MARGIN), y))
        y += max(panel.image.height for panel in row) + MARGIN
    if states:
        sheet.paste(states.image, (MARGIN, y))
    return sheet


def panel_html(panel, sid, page=None):
    buf = BytesIO()
    panel.image.save(buf, format='PNG', optimize=True)
    encoded = b64encode(buf.getvalue()).decode('ascii')
    links = ''.join(
        f'<a class="hotspot" id="mark-{sid}-{number}" href="#note-{number}" '
        f'aria-label="查看鍵位 {number} 的說明" '
        f'style="left:{x / panel.image.width:.4%};top:{y / panel.image.height:.4%}"></a>'
        for number, (x, y) in panel.markers.items()
    )
    anchor = f' id="page-{sid}-{escape(page)}"' if page else ''
    return (f'<figure class="panel"{anchor}><img src="data:image/png;base64,{encoded}" '
            f'alt="{escape(panel.name)}" width="{panel.image.width}" height="{panel.image.height}">{links}</figure>')


def notes_html(sections, rendered, keyboards):
    notes_html = []
    for page in sections:
        notes = sections[page]
        if not notes:
            continue
        items = []
        for note in notes.values():
            lines = ''.join(f'<dt>{escape(label)}</dt><dd>{escape(description)}</dd>'
                            for label, description in note.lines)
            back = ' '.join(f'<a href="#mark-palette-{i}-{note.number}">{escape(entry[0])}</a>'
                            for i, entry in enumerate(rendered))
            items.append(f'<li id="note-{note.number}"><h4><span>{note.number}</span> {escape(note.label)}</h4>'
                         f'<dl>{lines}</dl><footer>回到圖上　{back}</footer></li>')
        notes_html.append(f'<section class="notes"><h3>{escape(page_name(page, keyboards))}</h3>'
                          f'<ul>{"".join(items)}</ul></section>')
    if not notes_html:
        return ''
    count = sum(map(len, sections.values()))
    return f'<details><summary>鍵位說明 · {count} 項</summary>{"".join(notes_html)}</details>'


def write_html(path, theme_name, rendered, sections, keyboards):
    options = [f'<button type="button" data-palette="palette-{i}" aria-pressed="{str(i == 0).lower()}">'
               f'{escape(entry[0])}</button>' for i, entry in enumerate(rendered)]
    views = []
    for index, (_, panels, states) in enumerate(rendered):
        sid = f'palette-{index}'
        boards = ''.join(panel_html(panel, sid, page) for page, panel in guide_panels(panels))
        enter = f'<section class="enter-states" aria-label="回車鍵帽">{panel_html(states, sid)}</section>' if states else ''
        views.append(f'<div data-palette-view="{sid}" {"hidden" if index else ""}>'
                     f'<div class="panels">{boards}</div>{enter}</div>')
    path.write_text(HTML.format(name=escape(theme_name), options=''.join(options),
                                views=''.join(views), notes=notes_html(sections, rendered, keyboards)),
                    encoding='utf-8')


HTML = r"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{name}｜鍵位指南</title>
<style>
:root {{color-scheme:light; --ink:#17242d; --muted:#4d6170; --paper:#edf2f5; --teal:#087c82;}}
* {{box-sizing:border-box}} [hidden] {{display:none!important}}
html {{scroll-padding-top:20px}}
body {{margin:0; background:var(--paper); color:var(--ink);
  font:16px/1.6 system-ui,"Noto Sans CJK TC",sans-serif}}
main {{max-width:1180px; margin:auto; padding:clamp(14px,3vw,36px)}}
header {{padding:28px 0 20px; border-bottom:1px solid #c8d6dd; margin-bottom:18px}}
.eyebrow {{color:var(--teal); font-size:.76rem; font-weight:750; letter-spacing:.16em}}
h1 {{font-size:clamp(2.3rem,6vw,4.6rem); line-height:1.05; margin:.15em 0 .25em}}
p {{max-width:54em; color:var(--muted); margin:.5em 0}}
nav {{display:flex; flex-wrap:wrap; gap:8px; margin:16px 0}}
button {{border:1px solid #a7bbc6; border-radius:999px; background:#fff; color:var(--ink);
  padding:.45em 1em; font:inherit; cursor:pointer}}
button[aria-pressed=true] {{background:#14575e; border-color:#14575e; color:#fff}}
.keyboard-layout {{margin:26px 0; padding:clamp(10px,2vw,22px); background:#fff;
  border:1px solid #d3dfe6; border-radius:16px}}
.panels {{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,410px),1fr)); gap:14px}}
.panel {{position:relative; align-self:start; margin:0; border-radius:14px; overflow:hidden;
  outline:1px solid #c8d6dd}}
.panel img {{display:block; width:100%; height:auto}}
.panel:target {{outline:3px solid #df8a20}}
.enter-states {{max-width:590px; margin:18px 0 0}}
.hotspot {{position:absolute; width:clamp(16px,2.6%,26px); aspect-ratio:1; border-radius:50%;
  transform:translate(-50%,-50%); outline-offset:2px}}
.hotspot:focus-visible,.hotspot:hover,.hotspot:target {{outline:2px solid #df8a20}}
details {{margin-top:16px}}
summary {{padding:.45em .75em; border-radius:7px; background:#eef3f7; cursor:pointer; font-weight:650}}
.notes h3 {{margin:1.2em 0 .45em; border-bottom:1px solid #c8d6dd; padding-bottom:.25em}}
.notes ul {{display:grid; grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr));
  list-style:none; gap:10px; padding:0; margin:0}}
.notes li {{background:#fff; border:1px solid #d6e0e6; border-radius:10px; padding:12px 14px}}
.notes li:target {{outline:2px solid var(--teal); background:#f2fbfb}}
h4 {{margin:0 0 .35em; font-size:1rem}}
h4 span {{display:inline-grid; place-items:center; min-width:1.75em; height:1.75em;
  border-radius:50%; background:var(--teal); color:white; margin-right:3px}}
dl {{margin:.35em 0; display:grid; grid-template-columns:max-content 1fr; gap:.15em .7em}}
dt {{color:var(--teal); font-weight:700}}
dd {{margin:0; overflow-wrap:anywhere}}
footer {{font-size:.8rem; color:var(--muted); margin-top:.6em}}
a {{color:#095c67; text-underline-offset:.17em}}
</style></head><body><main>
<header><div class="eyebrow">TRIME KEYBOARD GUIDE</div><h1>{name} 鍵位指南</h1>
<p>每張圖都從主題配置繪製。點編號查看特殊動作，再從說明點回鍵位。直接輸出的數字和符號請看鍵帽角標。</p>
<p>主鍵盤的中文態與英文態並排展示，主鍵盤的動作編號集中在中文態圖。</p>
<p>畫面以 1080p、420 dpi 的直向鍵盤為基準。候選、剪貼板內容與語音面板由輸入狀態或 App 提供，圖中展示固定版面與回車鍵帽。</p></header>
<nav aria-label="選擇配色">{options}</nav>
<section class="keyboard-layout" aria-label="鍵盤版面">
{views}
{notes}
</section>
</main><script>
function showPalette(id) {{
  document.querySelectorAll('[data-palette-view]').forEach(el => el.hidden = el.dataset.paletteView !== id);
  document.querySelectorAll('button[data-palette]').forEach(el =>
    el.setAttribute('aria-pressed', String(el.dataset.palette === id)));
}}
function revealAnchor(hash) {{
  const id = /^#(?:mark|page)-(palette-\d+)-/.exec(hash)?.[1];
  if (id) showPalette(id);
  const details = document.getElementById(hash.slice(1))?.closest('details');
  if (details) details.open = true;
}}
document.addEventListener('click', event => {{
  const target = event.target.closest('button[data-palette],a[href^="#"]');
  if (target?.dataset.palette) showPalette(target.dataset.palette);
  if (target?.hash) revealAnchor(target.hash);
}});
window.addEventListener('hashchange', () => revealAnchor(location.hash));
revealAnchor(location.hash);
</script></body></html>
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--theme', type=Path, default=THEME_SOURCE, help='自訂主題源檔或生成的主題')
    parser.add_argument('--pages-from', type=Path, help='指定定義自訂鍵盤頁的源檔，適用於繼承版面')
    parser.add_argument('--base', type=Path, default=THEME_DIR / 'vendor' / 'trime-3.3.13.yaml',
                        help='源檔所引用的 Trime 預設')
    parser.add_argument('--assets', type=Path, default=ROOT / 'rime', help='fonts/、backgrounds/ 所在目錄')
    parser.add_argument('--font', type=Path, help='圖中文字體，默認用 fontconfig 尋找 Noto Sans CJK')
    parser.add_argument('--out', type=Path, default=ROOT / 'tmp' / 'theme-guide', help='輸出目錄')
    args = parser.parse_args()

    source = read_yaml(args.theme)
    theme = resolve_theme(source, read_yaml(args.base))
    theme_name = str(theme.get('name', args.theme.stem))
    pages = guide_pages(read_yaml(args.pages_from) if args.pages_from else source, theme)
    schemes = [sid for sid, data in source.get('preset_color_schemes', {}).items() if isinstance(data, dict)]
    if not pages or not schemes:
        parser.error('源檔須至少定義一個鍵盤頁和一種配色')
    if any(not re.fullmatch(r'[\w-]+', sid) for sid in schemes):
        parser.error('配色 ID 只能用字母、數字、底線及連字號')
    fonts = Typography(theme['style'], args.assets, args.font)
    include_html = theme_name == 'V1'
    sections = {}
    if include_html:
        models = {page: build(theme, page, {}, schemes[0]) for page in pages}
        sections = collect_notes(theme, models)
    has_enter = bool(enter_labels(theme, pages))

    args.out.mkdir(parents=True, exist_ok=True)
    rendered = []
    for sid in schemes:
        scheme = theme['preset_color_schemes'][sid]
        name = str(scheme.get('name', sid))
        dark = sum(rgb(css_color(scheme.get('keyboard_back_color')), '#DEE1E6')) < 384
        palette = ('#161D26', '#EFF3F8', '#AEBECD') if dark else ('#EDF2F7', '#192834', '#4B5E6D')
        panels = {}
        for page in pages:
            model = build(theme, page, {}, sid)
            is_main = page == 'qwerty'
            panels[page] = [draw_board(page, model, theme, scheme, fonts, args.assets, sections.get(page, {}),
                                       palette, ascii_mode=False if is_main else None)]
            if is_main:
                panels[page].append(draw_board(page, model, theme, scheme, fonts, args.assets, {},
                                               palette, ascii_mode=True))
        wide_states = None
        if has_enter:
            wide_states = draw_states(theme, scheme, pages, fonts, args.assets, palette,
                                      width=2 * SCREEN_W + MARGIN)
        out = args.out / f'{sid}.png'
        sheet = make_sheet(panels, wide_states, theme_name, name, fonts, palette,
                           include_html=include_html)
        sheet.save(out, optimize=True)
        print(f'→ {out}')
        if include_html:
            states = draw_states(theme, scheme, pages, fonts, args.assets, palette) if has_enter else None
            rendered.append((name, panels, states))
    if include_html:
        out = args.out / 'index.html'
        write_html(out, theme_name, rendered, sections, theme['preset_keyboards'])
        print(f'→ {out}（{len(pages)} 頁、{sum(map(len, sections.values()))} 項註記）')


if __name__ == '__main__':
    main()
