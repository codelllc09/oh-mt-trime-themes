#!/usr/bin/env python3
"""mock_number_page.py —— 數字鍵盤「加一列」方案示意圖（設計階段用，不入主題）

用途：在真正改 xuma_L.trime.yaml 之前，把幾個候選佈局畫成與實機同尺寸的圖，
讓取捨看得見。繪製參數全部取自真實主題與實機量測值：

    畫布寬 1080px（1080p@420 的實機寬）
    行格高 131px、可視鍵高 97px、行縫 34px（vertical_gap: 13）
    水平縫 13px（horizontal_gap: 5）
    單位寬 1 unit = 1080/100 = 10.8px

配色直接讀 xuma_L.trime.yaml 的 xuma_cloud / xuma_night。
"""
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
THEME = ROOT / 'xuma_L.trime.yaml'

W = 1080
CELL_H, KEY_H = 131, 97
GAP_X = 13
RADIUS = 22

FONT_LAT = ROOT / 'fonts' / 'xuma_latin.ttf'
FONT_CJK = ROOT / 'fonts' / 'xuma_key.otf'
# 示意圖要用來寫標題與說明（任意漢字），鍵盤子集字體沒有這些字形 →
# 用系統 Noto Sans CJK SC（wght=400 靜態實例；VF 默認是 Thin，不要直接用）。
FONT_UI_CANDIDATES = [
    '/tmp/noto_sc_400.otf',
    '/usr/share/fonts/google-noto-sans-cjk-vf-fonts/NotoSansCJK-VF.ttc',
]


def ui_font(size):
    for cand in FONT_UI_CANDIDATES:
        if Path(cand).exists():
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                continue
    return ImageFont.load_default()


# 示意圖用的字形回退鏈：鍵盤子集字體只含鍵面出現過的字符，
# 畫 ⌫ ⏎ √ ° ‰ 這些必須另找字體，故按 cmap 逐字挑第一個有該字形的字體。
FALLBACK_CANDIDATES = [
    str(FONT_LAT), str(FONT_CJK), '/tmp/noto_sc_400.otf',
    '/usr/share/fonts/vazirmatn-vf-fonts/Vazirmatn[wght].ttf',
    str(Path.home() / '.local/share/fonts/JetBrainsMonoNerdFontMono-Bold.ttf'),
]


def _cmap(path):
    from fontTools.ttLib import TTFont
    try:
        return set((TTFont(path, lazy=True).getBestCmap() or {}))
    except Exception:
        return set()


_CMAPS = None
_FONT_CACHE = {}


def glyph_font(label: str, size: int):
    global _CMAPS
    if _CMAPS is None:
        _CMAPS = [(p, _cmap(p)) for p in FALLBACK_CANDIDATES if Path(p).exists()]
    need = {ord(ch) for ch in label}
    for path, cm in _CMAPS:
        if need <= cm:
            key = (path, size)
            if key not in _FONT_CACHE:
                _FONT_CACHE[key] = ImageFont.truetype(path, size)
            return _FONT_CACHE[key]
    return ui_font(size)


def rgb(v):
    v = v.lstrip('#')
    if len(v) == 8:
        v = v[2:]
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def draw_kb(scheme, rows, title, notes, out):
    """rows: [[(label, units, kind), ...], ...]；kind ∈ key/fn/accent/space"""
    c = {
        'bg': rgb(scheme['keyboard_back_color']),
        'key': rgb(scheme['key_back_color']),
        'text': rgb(scheme['key_text_color']),
        'fn': rgb(scheme['fn_back_color']),
        'fntext': rgb(scheme['fn_text_color']),
        'accent': rgb(scheme['accent_fill']),
        'accent_text': rgb(scheme['accent_text']),
        'space': rgb(scheme['space_back_color']),
        'spacetext': rgb(scheme['space_text_color']),
        'comment': rgb(scheme['comment_text_color']),
    }
    pad_top, pad_bottom = 26, 26
    head = 74
    notes_h = 26 * len(notes) + 18
    h = head + pad_top + len(rows) * CELL_H + pad_bottom + notes_h
    img = Image.new('RGB', (W, h), c['bg'])
    d = ImageDraw.Draw(img)
    f_title = ui_font(30)
    f_note = ui_font(22)
    f_key = ImageFont.truetype(str(FONT_LAT), 46)
    f_cjk = ui_font(40)
    f_glyph = ui_font(46)          # ⌫ ⏎ 這類不在鍵盤子集裏的符號

    d.text((36, 22), title, font=f_title, fill=c['text'])
    y = head + pad_top
    f_hint = ui_font(20)
    for row in rows:
        total = sum(r[1] for r in row)
        spare = W - GAP_X * (len(row) + 1)
        x = GAP_X
        for item in row:
            label, units, kind = item[0], item[1], item[2]
            lng = item[3] if len(item) > 3 else ''
            w = spare * units / total
            fill = {'key': c['key'], 'fn': c['fn'], 'accent': c['accent'],
                    'space': c['space']}.get(kind, c['key'])
            tc = {'key': c['text'], 'fn': c['fntext'], 'accent': c['accent_text'],
                  'space': c['spacetext']}.get(kind, c['text'])
            d.rounded_rectangle([x, y, x + w - 1, y + KEY_H], radius=RADIUS, fill=fill)
            if label:
                if all(ord(ch) < 0x2E80 for ch in label):
                    font = glyph_font(label, 46)
                elif label in '⌫⏎':
                    font = glyph_font(label, 42)
                else:
                    font = f_cjk
                box = d.textbbox((0, 0), label, font=font)
                d.text((x + (w - (box[2] - box[0])) / 2 - box[0],
                        y + (KEY_H + 8 - (box[3] - box[1])) / 2 - box[1]), label, font=font, fill=tc)
            if lng:      # 長按提示（畫在鍵面上方，與實機 label_symbol 同位）
                hb = d.textbbox((0, 0), lng, font=f_hint)
                d.text((x + (w - (hb[2] - hb[0])) / 2 - hb[0], y + 6), lng, font=f_hint,
                       fill=c['comment'] if 'comment' in c else c['text'])
            x += w + GAP_X
        y += CELL_H
    ny = y + 4
    for line in notes:
        d.text((36, ny), line, font=f_note, fill=c['text'])
        ny += 26
    img.save(out)
    print(f'  → {out}  ({W}×{h})')


def main():
    theme = yaml.safe_load(THEME.read_text(encoding='utf-8'))
    S = theme['preset_color_schemes']
    O = Path('/tmp')


    # ── 現狀（帶長按提示）：25 鍵、每鍵 216×97 ──
    cur = [
        [('( )', 20, 'fn', '<'), ('7', 20, 'key', ''), ('8', 20, 'key', '↑'), ('9', 20, 'key', ''), ('/', 20, 'fn', '')],
        [('[ ]', 20, 'fn', '>'), ('4', 20, 'key', '←'), ('5', 20, 'key', ''), ('6', 20, 'key', '→'), ('*', 20, 'fn', '#')],
        [('{ }', 20, 'fn', ''), ('1', 20, 'key', ''), ('2', 20, 'key', '↓'), ('3', 20, 'key', ''), ('+', 20, 'fn', '@')],
        [('=', 20, 'fn', '≠'), ('0', 20, 'key', ''), ('.', 20, 'key', ','), ('-', 20, 'fn', ''), ('⌫', 20, 'fn', '')],
        [('ABC', 20, 'fn', ''), ('ASC', 20, 'fn', ''), ('CJK', 20, 'fn', ''), ('數字', 20, 'space', ''), ('⏎', 20, 'accent', '')],
    ]

    # ── 方案 A：6 列等寬；新列四個鍵「點擊＋長按」共八個輸出 ──
    a = [
        [(',', 16.7, 'fn', '，'), ('( )', 16.7, 'fn', '<'), ('7', 16.7, 'key', ''), ('8', 16.7, 'key', '↑'), ('9', 16.7, 'key', ''), ('/', 16.7, 'fn', '÷')],
        [('%', 16.7, 'fn', '‰'), ('[ ]', 16.7, 'fn', '>'), ('4', 16.7, 'key', '←'), ('5', 16.7, 'key', ''), ('6', 16.7, 'key', '→'), ('*', 16.7, 'fn', '#')],
        [('√', 16.7, 'fn', 'π'), ('{ }', 16.7, 'fn', ''), ('1', 16.7, 'key', ''), ('2', 16.7, 'key', '↓'), ('3', 16.7, 'key', ''), ('+', 16.7, 'fn', '@')],
        [('°', 16.7, 'fn', '℃'), ('=', 16.7, 'fn', '≠'), ('0', 16.7, 'key', ''), ('.', 16.7, 'key', ','), ('-', 16.7, 'fn', '±'), ('⌫', 16.7, 'fn', '')],
        [('ABC', 20, 'fn', ''), ('ASC', 20, 'fn', ''), ('CJK', 20, 'fn', ''), ('數字', 20, 'space', ''), ('⏎', 20, 'accent', '')],
    ]

    # ── 方案 B：新列／括號收窄，數字鍵最寬 ──
    b = [
        [(',', 13, 'fn', '，'), ('( )', 14, 'fn', '<'), ('7', 18.25, 'key', ''), ('8', 18.25, 'key', '↑'), ('9', 18.25, 'key', ''), ('/', 18.25, 'fn', '÷')],
        [('%', 13, 'fn', '‰'), ('[ ]', 14, 'fn', '>'), ('4', 18.25, 'key', '←'), ('5', 18.25, 'key', ''), ('6', 18.25, 'key', '→'), ('*', 18.25, 'fn', '#')],
        [('√', 13, 'fn', 'π'), ('{ }', 14, 'fn', ''), ('1', 18.25, 'key', ''), ('2', 18.25, 'key', '↓'), ('3', 18.25, 'key', ''), ('+', 18.25, 'fn', '@')],
        [('°', 13, 'fn', '℃'), ('=', 14, 'fn', '≠'), ('0', 18.25, 'key', ''), ('.', 18.25, 'key', ','), ('-', 18.25, 'fn', '±'), ('⌫', 18.25, 'fn', '')],
        [('ABC', 20, 'fn', ''), ('ASC', 20, 'fn', ''), ('CJK', 20, 'fn', ''), ('數字', 20, 'space', ''), ('⏎', 20, 'accent', '')],
    ]

    draw_kb(S['xuma_night'], cur, '現狀：5 列 × 20 單位（鍵 216×97，2.2:1）／上排小字＝長按輸出',
            ['括號列的長按 < > 與數字鍵的方向鍵都在 —— 加列時**一個都不能丟**。'],
            O / 'num_00_now.png')
    draw_kb(S['xuma_cloud'], a, '方案 A（淺色）：6 列等寬 16.7（鍵 167×97，1.72:1）',
            ['新列四鍵「點擊／長按」＝ , ， / % ‰ / √ π / ° ℃；另把 / 長按補 ÷、- 長按補 ±。',
             '原有長按全部保留：< > ← ↑ → ↓ # @ ≠ , 。'],
            O / 'num_01_a_light.png')
    draw_kb(S['xuma_night'], a, '方案 A：6 列等寬 16.7（鍵 167×97，1.72:1）',
            ['新列四鍵「點擊／長按」＝ , ， / % ‰ / √ π / ° ℃；另把 / 長按補 ÷、- 長按補 ±。',
             '原有長按全部保留：< > ← ↑ → ↓ # @ ≠ , 。'],
            O / 'num_01_a.png')
    draw_kb(S['xuma_night'], b, '方案 B：新列 13／括號 14／數字 18.25（鍵 197×97，2.03:1）',
            ['符號分配同方案 A，只是把寬度多讓給數字鍵；仍偏長條。'],
            O / 'num_02_b.png')


if __name__ == '__main__':
    main()
