#!/usr/bin/env python3
"""量按鍵字形的光學居中偏移，給出該寫進 YAML 的 key_text_offset_x。

用法：
    uv run python tools/glyph_offsets.py <截圖> [--kb number_zh]

原理：全形標點（，。！？：；「」（）《》）的墨跡不在字身正中——左括號偏右、
右括號偏左、句讀偏左。Trime 不做光學居中，只能逐鍵給 key_text_offset_x；
肉眼估不準，所以量：取鍵面底色，找字形墨跡的橫向包圍盒，減去鍵面中心，
換算成 sp（sp = px / (density/160)）。輸出 `建議` 欄即該鍵應有的絕對偏移值。

判讀：殘差 px 接近 0 表示已居中；量不到（無墨跡／貼窗邊）會標 (量不到)。
"""
import argparse
import sys

import yaml
from PIL import Image

from check_trime import THEME_SOURCE

DENSITY = 420                 # 容器豎屏 1080×2280@420
WIDTH_UNIT = 1080 / 100       # width:1 = 10.8px @1080
KEY_FILL_INSET = 16
INK_THRESHOLD = 40
SP = DENSITY / 160


def rows_of(kb):
    rows, cur, acc = [], [], 0.0
    for k in kb['keys']:
        w = k.get('width', 10)
        cur.append((k, w))
        acc += w
        if abs(acc - 100) < 0.001:
            rows.append(cur)
            cur, acc = [], 0.0
    return rows


def row_layout(row):
    lead, keys = 0.0, []
    seen_key = False
    for k, w in row:
        if 'click' in k:
            seen_key = True
            keys.append(k)
        elif not seen_key:
            lead += w
    return lead, keys


def ink_center(img, x0, x1, y0, y1):
    crop = img.crop((x0, y0, x1, y1))
    # 鍵面底色＝窗內出現最多的顏色（比取樣某一點穩：那一點可能落在行間縫隙）
    from collections import Counter
    small = crop.resize((max(1, crop.width // 4), max(1, crop.height // 4)))
    fill = Counter(small.getdata()).most_common(1)[0][0]
    w, h = crop.size
    px = crop.tobytes()
    minx, maxx = w, -1
    for y in range(h):
        base = y * w * 3
        for x in range(w):
            j = base + x * 3
            if (abs(px[j] - fill[0]) > INK_THRESHOLD
                    or abs(px[j + 1] - fill[1]) > INK_THRESHOLD
                    or abs(px[j + 2] - fill[2]) > INK_THRESHOLD):
                if x < minx:
                    minx = x
                if x > maxx:
                    maxx = x
    if maxx < 0 or minx <= 1 or maxx >= w - 2:
        return None
    return x0 + (minx + maxx) / 2   # 轉回截圖絕對座標


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('shot')
    ap.add_argument('--kb', default='number_zh')
    ap.add_argument('--y', default='1400-2280')
    args = ap.parse_args()

    theme = yaml.safe_load(THEME_SOURCE.read_text(encoding='utf-8'))
    kb = theme['preset_keyboards'][args.kb]
    rows = rows_of(kb)
    y0, y1 = (int(v) for v in args.y.split('-'))
    img = Image.open(args.shot).convert('RGB')
    s = img.width / 1080
    band = (y1 - y0) / len(rows)

    print(f'# {args.shot}  {args.kb}  行數 {len(rows)}  sp={SP:.3f}')
    print('行\t鍵\t字符\t現值\t殘差px\t殘差sp\t建議')
    for r, row in enumerate(rows):
        lead, keys = row_layout(row)
        ry0 = int((y0 + r * band + band * 0.22) * s)
        ry1 = int((y0 + r * band + band * 0.78) * s)
        for i, k in enumerate(keys):
            x_left = (lead + 10 * i) * WIDTH_UNIT
            x0 = int((x_left + 12) * s)
            x1 = int((x_left + 10 * WIDTH_UNIT - 12) * s)
            ch = k.get('click') if isinstance(k.get('click'), str) else '·'
            cur = k.get('key_text_offset_x', 0) or 0
            c = ink_center(img, x0, x1, ry0, ry1)
            if c is None:
                print(f'{r + 1}\t{i + 1}\t{ch}\t{cur:+.1f}\t—\t—\t(量不到)')
                continue
            dx = c - (x0 + x1) / 2
            print(f'{r + 1}\t{i + 1}\t{ch}\t{cur:+.1f}\t{dx:+.0f}\t{dx / SP:+.1f}\t{cur - dx / SP:+.1f}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
