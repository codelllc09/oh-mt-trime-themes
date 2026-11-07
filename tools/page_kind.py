#!/usr/bin/env python3
"""判定截圖是哪一頁鍵盤：main／num／ascii／cjk（供 shots.sh 命名與自檢）。

判據＝底行鍵數及第一條鍵縫的位置，與字符無關：

    主鍵盤   123#│地球│,│空格│.│/│Enter         7 鍵
    number（數字鍵盤 Hub） ABC│ASC│CJK│,│空格│Enter  6 鍵
    number_ascii（ASCII 符號頁） 123│,│空格│.│/│Enter  6 鍵
    number_zh（中文標點頁）  123│［│］│空格│※│〃│Enter  7 鍵

數字頁與 ASCII 頁都有六鍵，第一條縫分別約在 x=129／162（1080p）。
主鍵盤與中文標點頁都有七鍵，中文頁底行上方的行縫在 y=2020。

用法：page_kind.py <截圖>  → main｜num｜ascii｜cjk（退出碼 0；認不出回 unknown）
"""
import sys

from PIL import Image

W = 1080
ROW_Y = 2088                 # 底行中線（1080×2280@420 實測，四頁一致）
SCAN_X = (16, 1064)
DIFF = 3                     # 同一行的背景採樣；須分得開墨空的鍵面和底色
MIN_RUN = 8                  # 一段鍵面至少這麼寬（px），濾掉圓角雜訊

KEYS_BY_COUNT = {7: 'main', 3: 'cjk'}


def classify(path):
    img = Image.open(path).convert('RGB')
    s = img.width / W
    y = img.height - round((2280 - ROW_Y) * s)
    bg = img.getpixel((0, y))

    # 數「鍵間縫」比數「鍵面」穩：鍵面上有字符（與底色差異大）會把鍵面切成幾段，
    # 而縫隙是純底色，寬度 10–16px，數它不會被字符干擾。
    gutters, run = [], 0
    for x in range(SCAN_X[0], SCAN_X[1]):
        p = img.getpixel((int(x * s), y))
        is_gap = max(abs(p[i] - bg[i]) for i in range(3)) <= DIFF
        if is_gap:
            run += 1
        else:
            if run >= MIN_RUN:
                gutters.append(x - run / 2)
            run = 0
    keys = len(gutters) + 1
    if keys == 6:
        return ('num' if gutters[0] < 145 else 'ascii'), keys
    if keys == 7 and gutters[0] >= 145:
        gap_y = img.height - round((2280 - 2020) * s)
        gap_bg = img.getpixel((0, gap_y))
        if all(max(abs(a - b) for a, b in zip(img.getpixel((round(x * s), gap_y)), gap_bg)) <= DIFF
               for x in (80, 540, 1000)):
            return 'cjk', keys
    return KEYS_BY_COUNT.get(keys, 'unknown'), keys


def main():
    kind, runs = classify(sys.argv[1])
    print(kind, f'(底行 {runs} 鍵)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
