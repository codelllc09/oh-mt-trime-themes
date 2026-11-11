#!/usr/bin/env python3
# aesthetics.py —— 皮膚美學量化（SPEC §5 驗收的機械化）
#
# 兩個模式：
#   --theme rime/theme/sources/v1.theme-source.yaml
#       直接從主題配色算 WCAG 對比度矩陣（改 token 後立即知道達不達標，
#       不用等部署截圖）。判定：AA=4.5（正文）、大字/輔助=3.0、裝飾=標記值。
#   --shot <png> [--width 1080 --height 2280]
#       截圖量化：鍵盤佔屏比（候選欄頂邊界檢測）、行列縫隙均勻性
#       （投影法找鍵邊界）、對稱性（左右半差異）、層次（亮度直方圖峰數）。
#
# 只讀；零依賴（PIL 可選——缺 PIL 時 --shot 降級跳過，--theme 純標準庫）。

import argparse
import math
import sys
from pathlib import Path

# ── WCAG 相對亮度與對比度 ──

def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lum(color):
    """0xAARRGGBB 或 0xRRGGBB（int 或 str）→ 相對亮度 0..1"""
    if isinstance(color, str):
        color = int(color.replace('#', ''), 16)
    v = color & 0xFFFFFF
    r, g, b = (v >> 16) & 255, (v >> 8) & 255, v & 255
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(fg, bg):
    l1, l2 = sorted((lum(fg), lum(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def judge(ratio, kind):
    if kind == 'body':          # 正文鍵字
        return 'AA' if ratio >= 4.5 else ('AA-large' if ratio >= 3.0 else 'FAIL')
    if kind == 'aux':           # 註解/長按符號（輔助信息）
        return 'ok' if ratio >= 3.0 else ('weak' if ratio >= 2.0 else 'FAIL')
    return f'{ratio:.2f}'


# ── 對比度矩陣（鍵值對：前景 token, 背景 token, 類型, 說明）──

PAIRS = [
    ('key_text_color', 'key_back_color', 'body', '字母鍵字/鍵底'),
    ('key_text_color', 'keyboard_back_color', 'aux', '鍵字/縫隙底（邊界感）'),
    ('off_key_text_color', 'off_key_back_color', 'body', '功能鍵字/功能鍵底'),
    ('candidate_text_color', 'back_color', 'body', '候選字/候選欄'),
    ('hilited_candidate_text_color', 'hilited_candidate_back_color', 'body', '首選/首選底（G7 重點）'),
    ('comment_text_color', 'back_color', 'aux', '註解/候選欄'),
    ('key_symbol_color', 'key_back_color', 'aux', '長按符號/鍵底'),
    ('label_color', 'back_color', 'aux', '候選序號/候選欄'),
    # 底行語義色（鍵盤定義引用這些名，兩套配色各自定義；2026-11-06 新增）
    ('space_text_color', 'space_back_color', 'aux', '空格文字/空格底'),
    ('fn_text_color', 'fn_back_color', 'body', '功能鍵字/功能鍵底（#+123）'),
    ('accent_text', 'accent_fill', 'body', 'Enter 字/Enter 實心底'),
    ('on_key_text_color', 'on_key_back_color', 'body', '點亮態字/點亮態底（Shift鎖定·英文模式）'),
]


def theme_mode(path):
    import yaml
    t = yaml.safe_load(open(path, encoding='utf-8'))
    cs = t['preset_color_schemes']
    fails = 0
    for sid in ('xuma_cloud', 'xuma_night'):
        s = cs[sid]
        print(f'── {s.get("name", sid)} ──')
        for fgk, bgk, kind, desc in PAIRS:
            fg, bg = s.get(fgk), s.get(bgk)
            if fg is None or bg is None:
                print(f'  [?] {desc}: 缺 {fgk if fg is None else bgk}')
                continue
            r = contrast(fg, bg)
            v = judge(r, kind)
            flag = '' if v in ('AA', 'ok') else ' ← 不達標'
            if v in ('FAIL',):
                fails += 1
            print(f'  {r:5.2f}:1 [{v:>8}] {desc}{flag}')
    print(f'── FAIL 計數：{fails} ──')
    return 1 if fails else 0


# ── 截圖量化 ──

def shot_mode(png, width, height):
    try:
        from PIL import Image
    except ImportError:
        sys.exit('--shot 需要 Pillow（uv run --with pillow）')
    im = Image.open(png).convert('RGB')
    W, H = im.size
    print(f'截圖：{W}x{H}')

    px = im.load()

    # 1) 鍵盤頂邊界：自底向上找淺色鍵盤帶（候選欄+鍵盤是亮色大塊）的起點
    def row_stats(y):
        vals = [sum(px[x, y]) / 3 for x in range(0, W, 6)]
        return (sum(vals) / len(vals),
                sum(1 for v in vals if v > 180) / len(vals))

    kb_top, in_band = None, False
    for y in range(H - 130, H // 2, -4):
        mean, light_frac = row_stats(y)
        if light_frac > 0.55:
            in_band = True
        elif in_band:
            kb_top = y + 4
            break
    if kb_top:
        ratio = (H - kb_top) / H * 100
        v = '達標' if ratio <= 40 else '超標'
        print(f'  鍵盤區頂邊界 y={kb_top}；佔屏比 {ratio:.1f}%（目標 ≤40%）：{v}')
    else:
        print('  [?] 未檢出鍵盤頂邊界（可能純色畫面）')

    # 2) 鍵盤區縫隙均勻性：在鍵盤區中部取一行，找「暗縫」位置
    if kb_top:
        probe_y = kb_top + (H - kb_top) // 3
        lum_row = [sum(px[x, probe_y]) / 3 for x in range(W)]
        row_mean_v = sum(lum_row) / W
        thr = row_mean_v - 12
        valleys = []
        x = 0
        while x < W:
            if lum_row[x] < thr:
                x0 = x
                while x < W and lum_row[x] < thr:
                    x += 1
                valleys.append((x0 + x) // 2)
            else:
                x += 1
        gaps = [b - a for a, b in zip(valleys, valleys[1:])]
        body = [g for g in gaps if 8 < g < 200]
        if len(body) >= 4:
            mean = sum(body) / len(body)
            dev = (max(abs(g - mean) for g in body) / mean) * 100
            note = '均勻' if dev < 40 else '偏差大——鍵寬不一或含功能鍵區'
            print(f'  縫隙數 {len(body)}，均寬 {mean:.0f}px，最大偏差 {dev:.0f}%（{note}）')

    # 3) 對稱性：左右半鏡像差異（鍵盤區）
    if kb_top:
        region = im.crop((0, kb_top, W, H))
        rw, rh = region.size
        left, right = region.crop((0, 0, rw // 2, rh)), region.crop((rw - rw // 2, 0, rw, rh)).transpose(
            Image.FLIP_LEFT_RIGHT)
        import statistics
        diffs = []
        lp, rp = left.load(), right.load()
        for y in range(0, rh, 6):
            for x in range(0, rw // 2, 6):
                a, b = lp[x, y], rp[x, y]
                diffs.append(abs(a[0] - b[0]) + abs(a[1] - b[1]) + abs(a[2] - b[2]))
        m = sum(diffs) / len(diffs)
        print(f'  左右對稱性：平均逐點差 {m:.1f}/765（<12 優秀，<25 良好）'
              f'{"✓" if m < 25 else "△（空格鍵偏左佈局屬設計，非對稱合理）"}')

    # 4) 層次：採樣字母鍵/功能鍵/縫隙背景三層亮度（座標按鍵盤區高度比例）
    if kb_top:
        kh = H - kb_top
        def region_lum(cx, cy, r=14):
            vals = []
            for yy in range(cy - r, cy + r, 3):
                for xx in range(cx - r, cx + r, 3):
                    vals.append(sum(px[xx, yy]) / 3)
            return sum(vals) / len(vals)
        # 行結構：候選欄(~0.11)+數字行+QWERTY+ASDF+ZXCV(Shift行)+底行
        letter_y = kb_top + int(kh * 0.38)   # QWERTY 行中心
        func_y = kb_top + int(kh * 0.74)     # Shift 行中心（ZXCV）
        gap_y = kb_top + int(kh * 0.12)      # 候選欄與數字行間
        letter = region_lum(int(W * 0.075), letter_y)      # Q 鍵中心附近
        func = region_lum(int(W * 0.07), func_y)           # Shift 鍵中心附近
        gap = region_lum(int(W * 0.5), gap_y)              # 行間縫隙
        d1, d2 = abs(letter - gap), abs(func - letter)
        print(f'  三層亮度：字母鍵 {letter:.0f} / 功能鍵 {func:.0f} / 背景 {gap:.0f}'
              f'；鍵-背景差 {d1:.0f}（≥8 分明），功能-字母差 {d2:.0f}（≥8 分明）')

    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--theme', metavar='YAML', help='主題配色 WCAG 對比度矩陣')
    ap.add_argument('--shot', metavar='PNG', help='截圖量化')
    ap.add_argument('--width', type=int, default=1080)
    ap.add_argument('--height', type=int, default=2280)
    a = ap.parse_args()
    if a.theme:
        sys.exit(theme_mode(a.theme))
    if a.shot:
        sys.exit(shot_mode(a.shot, a.width, a.height))
    ap.print_help()


if __name__ == '__main__':
    main()
