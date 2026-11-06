#!/usr/bin/env python3
"""rebuild_key_font.py —— 重建 fonts/xuma_key.otf（鍵盤用 CJK 子集字體）

為什麼要有這支腳本：字體是**二進制生成物**，靠手上傳不可重現。
以前的做法是臨時 `uv run --with fonttools` 打一段 heredoc，字符集存在 /tmp，
換臺機器就必然走樣。現在固定成：

    字符集 = 現有 xuma_key.otf 的 cmap ∪ EXTRA_CHARS

這樣每次「往鍵盤上加一個新字符」時，只要把它放進 EXTRA_CHARS（或先確保
它在舊字體裏），重跑本腳本即可，不會丟字。

字重陷阱：**不要直接子集 NotoSansCJK-VF.ttc** —— 可變字體的默認實例是
wght=100（Thin），整把鍵盤會偏細。故先 varLib.instancer 固定到 400。

商標：OFL 要求修改版不得沿用上游保留字體名，故 nameID 1/3/4/6/16/17 改爲
「Xuma Key CJK」；nameID 0（版權）與 13/14（授權聲明與連結）保持上游原文。

用法：
    uv run --with fonttools python3 tools/rebuild_key_font.py
"""
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / 'fonts' / 'xuma_key.otf'

# 系統字體（Arch: google-noto-sans-cjk-vf-fonts）
SRC_CANDIDATES = [
    '/usr/share/fonts/google-noto-sans-cjk-vf-fonts/NotoSansCJK-VF.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]

EXTRA_CHARS = 'ㄓ'        # 2026-11-07：空格鍵的 RIME 標記（注音 ㄓ）；系統字體不會有此子集
FAMILY = 'Xuma Key CJK'


def find_src() -> Path:
    for p in SRC_CANDIDATES:
        if Path(p).exists():
            return Path(p)
    sys.exit(f'[✗] 找不到上游 CJK 字體，試過：{SRC_CANDIDATES}')


def instantiate_regular(src: Path, wght=400):
    """把可變字體的 wght 軸釘死在 400，並取出 SC 子字體。"""
    from fontTools.varLib.instancer import instantiateVariableFont
    # TTC 裏第一個通常是 JP；按 name 找 SC
    idx = 0
    for i in range(10):
        try:
            f = TTFont(str(src), fontNumber=i, lazy=True)
        except Exception:
            break
        name = f['name'].getDebugName(1) or ''
        if 'SC' in name:
            idx = i
            break
        f.close()
    f = TTFont(str(src), fontNumber=idx)
    if 'fvar' in f:
        instantiateVariableFont(f, {'wght': wght}, inplace=True)
    return f


def main():
    src = find_src()
    base = TTFont(str(OUT))
    chars = {chr(c) for c in base.getBestCmap()} | set(EXTRA_CHARS)
    base.close()
    print(f'  字符集：{len(chars)} 個（含新增 {EXTRA_CHARS!r}）')

    font = instantiate_regular(src)
    opts = subset.Options()
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    sub = subset.Subsetter(options=opts)
    sub.populate(text=''.join(sorted(chars)))
    sub.subset(font)

    # 改名（只動 1/3/4/6/16/17；nameID 0 版權、13/14 授權聲明保持上游原文）
    renames = {1: FAMILY, 3: f'{FAMILY}-Regular', 4: FAMILY,
               6: f'{FAMILY}-Regular', 16: FAMILY, 17: 'Regular'}
    for rec in font['name'].names:
        if rec.nameID in renames:
            rec.string = renames[rec.nameID]

    font['OS/2'].usWeightClass = 400
    OUT.parent.mkdir(parents=True, exist_ok=True)
    font.save(str(OUT))
    got = TTFont(str(OUT))
    cmap = got.getBestCmap()
    print(f'  [✓] {OUT.name}：{len(cmap)} 字形，含 ㄓ={0x3113 in cmap}，'
          f'{OUT.stat().st_size // 1024} KB，家族名 {got["name"].getDebugName(1)}')


if __name__ == '__main__':
    main()
