#!/usr/bin/env python3
"""rebuild_key_font.py —— 重建 rime/fonts/xuma_key.otf（鍵盤用 CJK 子集字體）

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
OUT = ROOT / 'rime' / 'fonts' / 'xuma_key.otf'

# 系統字體（Arch: google-noto-sans-cjk-vf-fonts）
SRC_CANDIDATES = [
    '/usr/share/fonts/google-noto-sans-cjk-vf-fonts/NotoSansCJK-VF.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
]

# 2026-11-07：
#   ㄓ —— 曾用作空格鍵的 RIME 標記（後來改成 SUIGEM，字形留着備用）；
#   ◀ ▶ ▲ ▼ —— **實心三角**。原本方向鍵提示用 ← ↑ → ↓，在 11sp（29px）下細到看不見，
#   且主題裏那幾個 preset 的 label 還寫成空白（等於沒有提示）。實心三角同字號可讀，
#   三角與箭頭的字形對照見 design/references/arrow-glyphs.png。
#   ′ ″ —— 數字頁的角分／角秒；不要用 ASCII 單／雙引號冒充。
#   ∪ ∩ ∈ ∉ ∧ ∨ ∀ ∃ —— 數字頁的集合與邏輯欄。
#   ASCII 符號頁的新增字形；CJK 上游不收的字形由 Android 系統字體回退。
#   ※ 〃 —— 中文標點頁底行的註記與同上符號。
EXTRA_CHARS = 'ㄓ◀▶▲▼′″∪∩∈∉∧∨∀∃«»‖№‰±≈¡⋯•⇐⇒€£¥₩¢¿‚‹›„–−®™©※〃'
FAMILY = 'Xuma Key CJK'


def find_src() -> Path:
    for p in SRC_CANDIDATES:
        if Path(p).exists():
            return Path(p)
    sys.exit(f'[✗] 找不到上游 CJK 字體，試過：{SRC_CANDIDATES}')


def load_sc_font(src: Path):
    """從 TTC 取出 SC 子字體；先子集化，再固定字重，避免實例化整套 32MB CJK。"""
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
    return f


def main():
    src = find_src()
    base = TTFont(str(OUT))
    chars = {chr(c) for c in base.getBestCmap()} | set(EXTRA_CHARS)
    base.close()
    print(f'  字符集：{len(chars)} 個（含新增 {EXTRA_CHARS!r}）')

    font = load_sc_font(src)
    opts = subset.Options()
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    sub = subset.Subsetter(options=opts)
    sub.populate(text=''.join(sorted(chars)))
    sub.subset(font)

    # 先縮到鍵盤所需的百餘字形，再把可變字重固定在 Regular；若反過來處理整套
    # CJK CFF2，fontTools 需逐字形展開變體，會慢數分鐘且耗用大量記憶體。
    if 'fvar' in font:
        from fontTools.varLib.instancer import instantiateVariableFont
        instantiateVariableFont(font, {'wght': 400}, inplace=True)

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
