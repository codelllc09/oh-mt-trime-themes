#!/usr/bin/env python3
"""render_keyboard.py —— 直接把 **主題 YAML** 渲染成 HTML（不是手畫）

背景（2026-11-07 教訓）：示意圖靠手寫 HTML 拼版面，出了三次錯——
初始狀態與按鈕不一致、鍵的比例靠估算、角標顏色與實機不符。
根因是「示意圖」與「主題」是兩份手寫的東西，必然漂移。

本工具把方向反過來：**示意圖由主題生成**。
輸入 rime/theme/sources/v1.theme-source.yaml → 輸出該頁的 HTML（1080px 寬、與實機同像素），
變體用 patch（dict）表達，例如給數字頁加 gap 與 spacer。

用法：
    uv run --with pyyaml python tools/render_keyboard.py number  # 出 HTML 到 tmp/
    uv run --with pyyaml python tools/render_keyboard.py number --patch '{"gap":14,"spacer":3}'
"""
import argparse
import json
import sys
from html import escape
from pathlib import Path

import yaml

from check_trime import ROOT, THEME_SOURCE

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
    if key.get('label') is not None:
        return str(key['label'])
    click = key.get('click')
    if isinstance(click, dict):
        return str(click.get('label') or click.get('text', ''))
    if isinstance(click, str):
        p = presets.get(click)
        if isinstance(p, dict) and p.get('label') is not None:
            return str(p['label'])
        return click
    return str(click) if click is not None else ''


def hint_of(key, presets):
    if not isinstance(key, dict):
        return ''
    sym = key.get('label_symbol')
    if sym is not None:
        return str(sym).strip()
    lc = key.get('long_click')
    if isinstance(lc, str) and lc in presets:
        return str(presets[lc].get('label', '')).strip()
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

    # 依 Trime 的寬度與欄數限制換行，spacer 不計入欄數。
    rows, cur, total, columns = [], [], 0.0, 0
    max_columns = kb.get('columns', -1)
    for k in kb['keys']:
        w = float(k.get('width', 0)) if isinstance(k, dict) else 0.0
        clickable = not isinstance(k, dict) or 'click' in k or 'text' in k or 'label' in k
        if w == 0 and clickable:
            w = float(kb.get('width', 10))
        if cur and (total + w > 100.001 or (max_columns > 0 and columns >= max_columns)):
            rows.append(cur)
            cur, total, columns = [], 0.0, 0
        cur.append((k, w))
        total += w
        columns += clickable
    if cur:
        rows.append(cur)

    # Variant：自訂每欄寬度（cols = 每列第 i 個鍵的單位寬；只套用到鍵數相同的前幾列）
    cols = patch.get('cols')
    if cols:
        new_rows = []
        for r in rows:
            if len(r) == len(cols) and len(r) == len(rows[0]):
                r = [(k, cols[i]) for i, (k, _w) in enumerate(r)]
            new_rows.append(r)
        rows = new_rows

    # Variant：在指定位置插入 spacer（不畫鍵），用於製造「不等寬的縫隙」
    #   patch: {"insert": [[2, 6], [5, 3]]} → 在第 3 欄前插 6 單位、第 6 欄前插 3 單位
    ins = patch.get('insert')
    if ins:
        new_rows = []
        for r in rows:
            if len(r) == len(rows[0]):      # 只動第一種（數字四列），底行不動
                for pos, units in sorted(ins, key=lambda t: -t[0]):
                    r = r[:pos] + [({'width': units, '_spacer': True}, units)] + r[pos:]
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
    kb_h = float(kb.get('keyboard_height') or style.get('keyboard_height', 250)) * DP
    default_row_h = float(kb.get('height') or style.get('key_height', 38))
    raw_heights = [float(row[0][0].get('height') or default_row_h) if isinstance(row[0][0], dict)
                   else default_row_h for row in rows]
    row_heights = [kb_h * raw / sum(raw_heights) for raw in raw_heights]
    cell_h = kb_h / n_rows
    key_h = cell_h - vgap * DP

    out_rows = []
    for row in rows:
        cells = []
        for k, w in row:
            is_spacer = isinstance(k, dict) and (
                k.get('_spacer')
                or ('click' not in k and 'text' not in k and 'label' not in k))
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
                'key': k,
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
        'key_h': key_h, 'cell_h': cell_h, 'row_heights': row_heights, 'radius': radius,
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


def key_geometry(m):
    """可見鍵面在 1080p 畫布上的 x、y、寬、高。"""
    gap = m['gap'] * DP
    vgap = m['vgap'] * DP
    top = vgap / 2
    for row, height in zip(m['rows'], m['row_heights']):
        x = 0.0
        for c in row:
            wpx = c['units'] * SCREEN_W / 100
            if not c.get('spacer'):
                yield c, (x + gap / 2, top, wpx - gap, height - vgap)
            x += wpx
        top += height


def render_html(m, title):
    out = []
    for c, (left, top, width, height) in key_geometry(m):
        bg = c['bg'] or m['scheme'][c['cls']]
        fg = c['fg'] or m['scheme'][{'accent': 'accent_text', 'fn': 'fn_text', 'key': 'text'}[c['cls']]]
        sy = c['sy'] or m['scheme']['hint']
        ts = c['text_size'] or (m['long_text_size'] if len(c['label']) > 1 else m['text_size'])
        hint = (f'<div class="hint" style="color:{sy}">{escape(c["hint"])}</div>'
                if c['hint'] else '')
        out.append(
            f'<div class="k" style="left:{left:.1f}px;top:{top:.1f}px;'
            f'width:{width:.1f}px;height:{height:.1f}px;background:{bg};color:{fg};'
            f'font-size:{ts*DP:.0f}px;padding-top:{m["text_offset_y"]*DP:.0f}px">'
            f'{hint}{escape(c["label"])}</div>')
    H = len(m['rows']) * m['cell_h']
    return HTML.format(title=escape(title), W=SCREEN_W, H=H, radius=m['radius'] * DP,
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
    theme = yaml.safe_load(THEME_SOURCE.read_text(encoding='utf-8'))
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
