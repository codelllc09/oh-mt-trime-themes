#!/usr/bin/env python3
"""gen_icons.py —— 生成鍵位圖標 PNG（Trime 的 image-valued color 通道）

背景：Gboard 的地球鍵是 APK 內的矢量圖檔，不是字庫字形，故用系統字體模仿不了
（🌐 是彩色 emoji，VS15 文字變體在本機字庫無效；手繪幾何又總差一口氣）。
Trime 支持把「鍵背景」設成圖片值（`key_back_color` 以 .png 結尾 → 從
<userDataDir>/backgrounds/ 加載），於是自繪 PNG 復刻。

圖標來源：**Material Symbols Outlined**（Google，Apache-2.0）的 `language` 字形，
FILL=0 描邊版——與 Gboard 的地球同源同風格。字體按需下載到本地緩存（不入庫，
10 MB 太大），可用 MATERIAL_SYMBOLS_SHA256 校驗。

顏色直接讀自 android/xuma_L.trime.yaml 的配色，避免圖標與主題不同步。
幾何：圖檔會**被拉伸填滿鍵位**，所以圖檔長寬比必須等於鍵位長寬比，
      否則圓形會被拉成橢圓（實測：ASPECT 設 1.27 時地球顯示為 86% 寬的扁圓）。
      1080p@420 逐像素量得鍵位 150×146px → 長寬比 ≈1.03（並非按 15 單位×108 推算的 162）。

      ⚠ **改地球鍵寬度或 vertical_gap 就要同步改 ASPECT**（圖檔是被拉伸填滿鍵位的）：
        · 2026-11-07 第一次：底部地球鍵 15→10 單位 → 96×150px → ASPECT=0.64
        · 2026-11-07 第二次：vertical_gap 6→13 使鍵變矮 → 96×130px → ASPECT=0.74
        圖標佔比同樣跟着調（由鍵高算，鍵一矮就要略減），否則會頂滿或顯小。
"""
import hashlib
import os
import urllib.request
from pathlib import Path

import yaml
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ANDROID = HERE.parent
THEME = ANDROID / 'xuma_L.trime.yaml'
OUT = ANDROID / 'backgrounds'

FONT_URL = ('https://raw.githubusercontent.com/google/material-design-icons/master/'
            'variablefont/MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D.ttf')
FONT_SHA256 = os.environ.get('MATERIAL_SYMBOLS_SHA256', '')
FONT_CACHE = Path(os.environ.get('XDG_CACHE_HOME', Path.home() / '.cache')) / 'xuma-trime-icons'
FONT_FILE = FONT_CACHE / 'MaterialSymbolsOutlined.ttf'
GLYPH_LANGUAGE = 0xE894          # Material Symbols: language

ASPECT = 0.74                    # 鍵位長寬比（逐像素實測 96×130，1080p@420，10 單位寬＋vgap 13）
H = 300                          # 圖檔高（留 3x 餘量，2K 屏也不虛）
W = int(H * ASPECT)
ICON_RATIO = 0.40                # 圖標字號 / 鍵高：鍵窄且矮時要跟着調，否則橫向頂滿鍵面
SUPERSAMPLE = 4                  # 超採樣，邊緣抗鋸齒


def hex2rgb(v: str):
    v = v.lstrip('#')
    if len(v) == 8:              # AARRGGBB
        v = v[2:]
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def ensure_font() -> Path:
    if FONT_FILE.exists():
        return FONT_FILE
    FONT_CACHE.mkdir(parents=True, exist_ok=True)
    print('  下載 Material Symbols（一次性，約 10 MB）…')
    urllib.request.urlretrieve(FONT_URL, FONT_FILE)
    digest = hashlib.sha256(FONT_FILE.read_bytes()).hexdigest()
    print(f'  sha256 {digest}')
    if FONT_SHA256 and digest != FONT_SHA256:
        raise SystemExit(f'[✗] 字體 sha256 不符：{digest}')
    return FONT_FILE


def key_image(font_path: Path, bg, fg, glyph: int, icon_ratio=ICON_RATIO):
    """畫一張鍵位圖：圓角矩形底 + 居中圖標（Material Symbols 描邊字形）。"""
    img = Image.new('RGBA', (W * SUPERSAMPLE, H * SUPERSAMPLE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    W_, H_ = img.size
    d.rounded_rectangle([0, 0, W_ - 1, H_ - 1], radius=H_ * 0.20, fill=bg + (255,))

    f = ImageFont.truetype(str(font_path), int(H_ * icon_ratio))
    try:
        f.set_variation_by_axes([0, 0, 48, 400])     # FILL=0 描邊, GRAD=0, opsz=48, wght=400
    except Exception:
        pass
    box = d.textbbox((0, 0), chr(glyph), font=f)
    gw, gh = box[2] - box[0], box[3] - box[1]
    d.text(((W_ - gw) / 2 - box[0], (H_ - gh) / 2 - box[1]),
           chr(glyph), font=f, fill=fg + (255,))
    return img.resize((W, H), Image.LANCZOS)


def main():
    theme = yaml.safe_load(THEME.read_text(encoding='utf-8'))
    schemes = theme['preset_color_schemes']
    OUT.mkdir(exist_ok=True)
    font = ensure_font()

    for sid, fname in (('xuma_cloud', 'globe_light.png'),
                       ('xuma_night', 'globe_dark.png')):
        s = schemes[sid]
        bg = hex2rgb(s['fn_back_color'])
        fg = hex2rgb(s['fn_text_color'])
        key_image(font, bg, fg, GLYPH_LANGUAGE).save(OUT / fname)
        print(f'  [✓] {fname}  ({s["name"]}  底 {s["fn_back_color"]}  線 {s["fn_text_color"]})')
    print(f'→ {OUT}')


if __name__ == '__main__':
    main()
