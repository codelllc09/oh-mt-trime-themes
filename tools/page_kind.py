#!/usr/bin/env python3
"""判定截圖是哪一頁鍵盤：main／num／ascii／cjk（供 shots.sh 命名與自檢）。

判據＝**底行的鍵數**，與字符無關（字符判據已栽過多次）：

    主鍵盤   地球│12#│,│空格│.│/│Enter          7 鍵
    number（數字鍵盤 Hub） ABC│ASC│CJK│空格│Enter  5 鍵
    number_ascii（ASCII 符號頁） 123│,│空格│.│/│Enter  6 鍵
    number_zh（中文標點頁）  123│空格│Enter        3 鍵

做法：底行中線固定落在 y=2088（四個頁面底行同高，Enter 都用強調藍、位置一致）；
鍵與鍵之間是鍵盤底色，所以沿線數「非底色連續段」就是鍵數。

用法：page_kind.py <截圖>  → main｜num｜ascii｜cjk（退出碼 0；認不出回 unknown）
"""
import sys
from collections import Counter

from PIL import Image

W = 1080
ROW_Y = 2088                 # 底行中線（1080×2280@420 實測，四頁一致）
GAP_PROBE_Y = 2175           # 底行下方＝鍵盤底色
SCAN_X = (16, 1064)
DIFF = 20                    # 與底色的差值門檻
MIN_RUN = 8                  # 一段鍵面至少這麼寬（px），濾掉圓角雜訊

KEYS_BY_COUNT = {7: 'main', 5: 'num', 6: 'ascii', 3: 'cjk'}


def classify(path):
    img = Image.open(path).convert('RGB')
    s = img.width / W
    bg = img.getpixel((int(500 * s), int(GAP_PROBE_Y * s)))

    # 數「鍵間縫」比數「鍵面」穩：鍵面上有字符（與底色差異大）會把鍵面切成幾段，
    # 而縫隙是純底色，寬度 10–16px，數它不會被字符干擾。
    gutters, run = 0, 0
    for x in range(SCAN_X[0], SCAN_X[1]):
        p = img.getpixel((int(x * s), int(ROW_Y * s)))
        is_gap = max(abs(p[i] - bg[i]) for i in range(3)) <= DIFF
        if is_gap:
            run += 1
        else:
            if run >= MIN_RUN:
                gutters += 1
            run = 0
    if run >= MIN_RUN:
        gutters += 1
    keys = gutters + 1
    return KEYS_BY_COUNT.get(keys, 'unknown'), keys


def main():
    kind, runs = classify(sys.argv[1])
    print(kind, f'(底行 {runs} 鍵)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
