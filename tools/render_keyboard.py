#!/usr/bin/env python3
"""render_keyboard.py —— 直接把 **主題 YAML** 渲染成 HTML（不是手畫）

背景（2026-11-07 教訓）：示意圖靠手寫 HTML 拼版面，出了三次錯——
初始狀態與按鈕不一致、鍵的比例靠估算、角標顏色與實機不符。
根因是「示意圖」與「主題」是兩份手寫的東西，必然漂移。

本工具把方向反過來：**示意圖由主題生成**。
輸入 xuma_L.trime.yaml → 輸出該頁的 HTML（1080px 寬、與實機同像素），
變體用 patch（dict）表達，例如給數字頁加 gap 與 spacer。

用法：
    python3 tools/render_keyboard.py number                 # 出 HTML 到 tmp/
    python3 tools/render_keyboard.py number --patch '{"gap":14,"spacer":3}'
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
THEME_PATH = ROOT / 'xuma_L.trime.yaml'

DP = 2.625          # 420dpi：1dp = 2.625px
SCREEN_W = 1080


def px(v):
    return v * DP


def css_color(v):
    """Trime 用 #AARRGGBB（alpha 在前）；CSS 是 #RRGGBBAA 或 rgba()。
    直接照搬 8 位 hex 會出現「顏色整個粉紅」——實測踩過（2026-11-07）。"""
    if not v:
        return None
    if v.startswith('0x'):
        v = '#' + v[2:]
    if not v.startswith('#'):
        return v
    h = v[1:]
    if len(h) == 8:
        a, r, g, b = h[0:2], h[2:4], h[4:6], h[6:8]
        return f'rgba({int(r,16)},{int(g,16)},{int(b,16)},{int(a,16)/255:.3f})'
    if len(h) == 6:
        return v
    return v


def resolve_color(name, scheme, default):
    """鍵上的顏色可以是 hex，也可以是配色名（Trime 支持按名引用）。"""
    if not name:
        return default
    if name.startswith('#') or name.startswith('0x'):
        return css_color(name)
    return css_color(scheme.get(name)) or default


def label_of(key, presets):
    if not isinstance(key, dict):
        return str(key)
    if key.get('label'):
        return key['label']
    click = key.get('click')
    if isinstance(click, dict):
        return click.get('label') or click.get('text', '')
    if isinstance(click, str):
        p = presets.get(click)
        if isinstance(p, dict) and p.get('label'):
            return p['label']
        return click
    return ''


def hint_of(key, presets):
    if not isinstance(key, dict):
        return ''
    sym = key.get('label_symbol')
    if sym is not None and sym.strip():
        return sym
    lc = key.get('long_click')
    if isinstance(lc, str) and lc in presets:
        lab = presets[lc].get('label', '')
        return lab if lab.strip() else ''
    if isinstance(lc, str) and lc and len(lc) == 1:
        return lc
    return ''


def build(theme, kb_name, patch, scheme_id=None):
    style = theme['style']
    schemes = theme['preset_color_schemes']
    scheme_id = scheme_id or style.get('color_scheme')
    scheme = schemes[scheme_id]
    presets = theme.get('preset_keys', {})
    kb = theme['preset_keyboards'][kb_name]

    gap = float(patch.get('gap', kb.get('horizontal_gap') or style.get('horizontal_gap', 5)))
    vgap = float(kb.get('vertical_gap') or style.get('vertical_gap', 13))
    spacer_units = float(patch.get('spacer', 0))
    text_size = float(style.get('key_text_size', 22))
    long_text_size = float(style.get('key_long_text_size', 11))
    sym_size = float(style.get('symbol_text_size', 10))
    text_offset_y = float(kb.get('key_text_offset_y', 0))
    radius = float(style.get('round_corner', 9))

    # 把 keys 依「累計寬度超過 100」切成行（與 Trime 的換行規則一致）
    rows, cur, total = [], [], 0.0
    for k in kb['keys']:
        w = float(k.get('width', 0)) if isinstance(k, dict) else 0.0
        if w == 0:
            w = float(kb.get('width', 10))
        cur.append((k, w))
        total += w
        if total >= 99.99:
            rows.append(cur)
            cur, total = [], 0.0
    if cur:
        rows.append(cur)

    # Variant：自訂每欄寬度（cols = 每列第 i 個鍵的單位寬；只套用到鍵數相同的前幾列）
    cols = patch.get('cols')
    if cols:
        new_rows = []
        for r in rows:
            if len(r) == len(cols):
                r = [(k, cols[i]) for i, (k, _w) in enumerate(r)]
            new_rows.append(r)
        rows = new_rows

    # Variant：在「第 2 欄之後」插入 spacer，並把所有其他鍵按比例縮小，
    # 使總寬仍為 100（等同主題裏把六欄從 16.7 改成 (100-spacer)/6）。
    if spacer_units:
        scale = (100 - spacer_units) / 100
        new_rows = []
        for r in rows:
            scaled = [(k, w * scale) for k, w in r]
            if len(scaled) >= 3:
                scaled = (scaled[:2]
                          + [({'width': spacer_units, '_spacer': True}, spacer_units)]
                          + scaled[2:])
            new_rows.append(scaled)
        rows = new_rows

    n_rows = len(rows)
    kb_h = float(style.get('keyboard_height', 250)) * DP
    cell_h = kb_h / n_rows
    key_h = cell_h - vgap * DP

    out_rows = []
    for row in rows:
        cells = []
        for k, w in row:
            is_spacer = isinstance(k, dict) and k.get('_spacer')
            if is_spacer:
                cells.append({'spacer': True, 'units': w})
                continue
            click = k.get('click') if isinstance(k, dict) else k
            cls = 'key'
            if isinstance(click, str) and click in ('BackSpace', 'Return'):
                cls = 'accent' if click == 'Return' else 'fn'
            elif isinstance(click, dict):
                cls = 'fn'
            elif isinstance(click, str) and click in presets and presets[click].get('send'):
                cls = 'fn'
            bg = resolve_color(k.get('key_back_color') if isinstance(k, dict) else None,
                               scheme, None)
            fg = resolve_color(k.get('key_text_color') if isinstance(k, dict) else None,
                               scheme, None)
            sy = resolve_color(k.get('key_symbol_color') if isinstance(k, dict) else None,
                               scheme, None)
            cells.append({
                'units': w,
                'label': label_of(k, presets),
                'hint': hint_of(k, presets),
                'cls': cls,
                'bg': bg, 'fg': fg, 'sy': sy,
                'text_size': float(k.get('key_text_size') or 0) if isinstance(k, dict) else 0,
            })
        out_rows.append(cells)

    return {
        'kb_name': kb_name, 'rows': out_rows, 'gap': gap, 'vgap': vgap,
        'key_h': key_h, 'cell_h': cell_h, 'radius': radius,
        'text_size': text_size, 'long_text_size': long_text_size,
        'sym_size': sym_size, 'text_offset_y': text_offset_y,
        'scheme': {k: css_color(scheme.get(v[0], v[1]))
                   for k, v in {
                       'key': ('key_back_color', '#2C2F33'),
                       'text': ('key_text_color', '#E6E8EB'),
                       'fn': ('fn_back_color', '#454A51'),
                       'fn_text': ('fn_text_color', '#E6E8EB'),
                       'accent': ('accent_fill', '#8AB4F8'),
                       'accent_text': ('accent_text', '#1B1C1E'),
                       'bg': ('keyboard_back_color', '#101113'),
                       'hint': ('key_symbol_color', '#8A9098')}.items()},
    }


HTML = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ margin:0; background:{page}; font-family:system-ui,"Noto Sans CJK SC",sans-serif; }}
  .board {{ position:relative; width:{W}px; height:{H}px; background:{bg}; }}
  .k {{ position:absolute; display:flex; align-items:center; justify-content:center;
        border-radius:{radius}px; overflow:hidden; }}
  .k .hint {{ position:absolute; top:4px; left:0; right:0; text-align:center;
              font-size:{sym}px; line-height:1.1; color:{hint}; }}
</style></head>
<body><div class="board">{keys}</div></body></html>
"""


def render_html(m, title):
    rows = m['rows']
    gap = m['gap'] * DP
    key_h = m['key_h']
    cell_h = m['cell_h']
    out = []
    for ri, row in enumerate(rows):
        x = 0.0
        y = ri * cell_h
        for c in row:
            units = c['units']
            wpx = units * 10.8
            if c.get('spacer'):
                x += wpx
                continue
            left = x + gap / 2
            width = wpx - gap
            bg = c['bg'] or (m['scheme']['accent'] if c['cls'] == 'accent'
                             else m['scheme']['fn'] if c['cls'] == 'fn'
                             else m['scheme']['key'])
            fg = c['fg'] or (m['scheme']['accent_text'] if c['cls'] == 'accent'
                             else m['scheme']['fn_text'] if c['cls'] == 'fn'
                             else m['scheme']['text'])
            sy = c['sy'] or m['scheme']['hint']
            ts = c['text_size'] or m['text_size']
            hint = (f'<div class="hint" style="color:{sy}">{c["hint"]}</div>'
                    if c['hint'] else '')
            if len(c['label']) > 1:
                ts = m['long_text_size']
            out.append(
                f'<div class="k" style="left:{left:.1f}px;top:{y + m["vgap"]*DP/2:.1f}px;'
                f'width:{width:.1f}px;height:{key_h:.1f}px;background:{bg};color:{fg};'
                f'font-size:{ts*DP:.0f}px;padding-top:{m["text_offset_y"]*DP:.0f}px">'
                f'{hint}{c["label"]}</div>')
            x += wpx
    H = len(rows) * cell_h
    return HTML.format(title=title, W=SCREEN_W, H=H, radius=m['radius'] * DP,
                       bg=m['scheme']['bg'], page='#0B0C0E',
                       hint=m['scheme']['hint'], sym=m['sym_size'] * DP,
                       keys='\n'.join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('keyboard')
    ap.add_argument('--patch', default='{}')
    ap.add_argument('--out', default=None)
    ap.add_argument('--scheme', default=None, help='xuma_cloud（淺）/ xuma_night（深）')
    args = ap.parse_args()
    theme = yaml.safe_load(THEME_PATH.read_text(encoding='utf-8'))
    patch = json.loads(args.patch)
    m = build(theme, args.keyboard, patch, args.scheme)
    title = f'{args.keyboard} · patch={patch or "（無）"}'
    html = render_html(m, title)
    out = Path(args.out or (ROOT / 'tmp' / f'mock-{args.keyboard}{"-variant" if patch else ""}.html'))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding='utf-8')
    print(f'→ {out}')
    print(f'   {len(m["rows"])} 行 · 鍵高 {m["key_h"]:.0f}px · 行格 {m["cell_h"]:.1f}px · '
          f'gap {m["gap"]}dp')


if __name__ == '__main__':
    main()
