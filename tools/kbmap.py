#!/usr/bin/env python3
# kbmap.py —— Waydroid/真機 Trime 鍵盤座標映射與輸入工具（測試用）
#
# 來歷：2026-11-06 容器功能矩陣實測中，憑記憶點座標連錯四次（rmmir/umip/
#   tyti/tsye），座標映射腳本化後零失誤——測試輸入必走本工具，勿手拼座標。
#
# 座標基準：容器/真機橫屏 1920x1160、Trime 徐碼 36 鍵主題（數字行佈局）。
#   佈局改動後以 uiautomator/screencap 重校。
#
# 用法：
#   python3 android/tools/kbmap.py --serial <adb-serial> --type tigu --backspace 6
#   python3 android/tools/kbmap.py --serial <...> --longpress z 1200   # 長按 z 發 `
#   python3 android/tools/kbmap.py --serial <...> --tap slash          # 點功能鍵
#   python3 android/tools/kbmap.py --keys                              # 列全部映射
#
# 依賴：adb 在 PATH；設備已 adb connect。

import argparse
import subprocess
import sys
import time

ROWS = {
    'qwertyuiop': 845,
    'asdfghjkl': 919,
    'zxcvbnm': 985,
    '1234567890': 771,          # 數字行
}
COLS = {
    'qwertyuiop': [96, 288, 480, 672, 864, 1056, 1248, 1440, 1632, 1824],
    'asdfghjkl': [170, 381, 573, 765, 958, 1150, 1342, 1534, 1727],
    'zxcvbnm': [381, 573, 765, 958, 1150, 1342, 1534],
    '1234567890': [96, 288, 480, 672, 864, 1056, 1248, 1440, 1632, 1824],
}
# 底行功能鍵（徐碼 36 鍵主題；1080x2280@420 實測基準座標）
FUNCS = {
    'shift': (144, 985), 'backspace': (1776, 985),
    'mode': (144, 1055), 'symbols': (381, 1055),      # 方案中文 / 数字符號
    'comma': (573, 1055), 'space': (960, 1055),
    'period': (1342, 1055), 'slash': (1534, 1055),
    'return': (1776, 1055),
}
# 尺寸檔（SPEC.md §0.5）：tap 座標按邏輯分辨率線性換算
PROFILES = {
    '1080p': (1080, 2280, 1.0, 1.0),
    '2k': (1440, 3200, 1440/1080, 3200/2280),
}


def scale(x, y, profile):
    _, _, sx, sy = PROFILES[profile]
    return round(x * sx), round(y * sy)


def xy(ch, profile):
    ch = ch.lower()
    for row, y in ROWS.items():
        if ch in row:
            return scale(COLS[row][row.index(ch)], y, profile)
    raise KeyError(f'無此字母鍵：{ch}（功能鍵用 --tap <name>）')


def adb(serial):
    return ['adb', '-s', serial] if serial else ['adb']


def tap(serial, x, y, delay=0.6):
    subprocess.run(adb(serial) + ['shell', 'input', 'tap', str(x), str(y)])
    time.sleep(delay)


def longpress(serial, x, y, ms=1200, delay=1.2):
    subprocess.run(adb(serial) + ['shell', 'input', 'swipe',
                                  str(x), str(y), str(x), str(y), str(ms)])
    time.sleep(delay)


def main():
    ap = argparse.ArgumentParser(description='Trime 鍵盤座標映射輸入工具')
    ap.add_argument('--serial', default='', help='adb serial（如 localhost:5555）')
    ap.add_argument('--type', metavar='WORD', help='逐鍵點擊字母/數字串')
    ap.add_argument('--tap', metavar='FUNC', help='點功能鍵：' + '/'.join(FUNCS))
    ap.add_argument('--longpress', metavar='CH', help='長按字母鍵（如 z 發反查引導）')
    ap.add_argument('--ms', type=int, default=1200, help='長按時長 ms（默認 1200）')
    ap.add_argument('--backspace', type=int, default=0, help='連點退格次數（清稿）')
    ap.add_argument('--delay', type=float, default=0.6, help='每鍵間隔秒')
    ap.add_argument('--profile', default='1080p', choices=list(PROFILES),
                    help='尺寸檔（SPEC §0.5）')
    ap.add_argument('--keys', action='store_true', help='列全部映射')
    a = ap.parse_args()

    if a.keys:
        for row, y in ROWS.items():
            for ch, x in zip(row, COLS[row]):
                print(f'  {ch}: ({x},{y})')
        for name, (x, y) in FUNCS.items():
            print(f'  {name}: ({x},{y})')
        return

    if not a.serial:
        sys.exit('缺 --serial（或改腳本默認值）')

    n = 0
    if a.backspace:
        for _ in range(a.backspace):
            tap(a.serial, *scale(*FUNCS['backspace'], a.profile), a.delay)
            n += 1
    if a.longpress:
        x, y = xy(a.longpress, a.profile)
        longpress(a.serial, x, y, a.ms)
        n += 1
    if a.type:
        for ch in a.type:
            x, y = xy(ch, a.profile)
            tap(a.serial, x, y, a.delay)
            n += 1
    if a.tap:
        if a.tap not in FUNCS:
            sys.exit(f'未知功能鍵 {a.tap}；可用：{"/".join(FUNCS)}')
        tap(a.serial, *scale(*FUNCS[a.tap], a.profile), a.delay)
        n += 1
    if not n:
        ap.print_help()


if __name__ == '__main__':
    main()
