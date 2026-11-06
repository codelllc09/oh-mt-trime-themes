# android/fonts —— 鍵盤字體（開源授權）

本目錄只有兩個**子集字體**，都是免費、可商用、可再分發的開源授權；
本倉庫以開源方式發布，這兩個字體的授權允許這樣做，但**必須**隨字體保留授權文本
（已放在本目錄）。

| 檔 | 用途 | 上游 | 授權 | 體積 |
|---|---|---|---|---|
| `xuma_key.otf` | 中文標點、引號、缺字回退 | Noto Sans CJK SC Regular 2.004（© 2014-2021 Adobe） | **SIL OFL 1.1**（`OFL-1.1.txt`） | 70 KB |
| `xuma_latin.ttf` | 拉丁字母、數字、ASCII 符號 | Roboto 3.002（© 2011 Google Inc.） | **Apache License 2.0**（`Apache-2.0.txt`） | 188 KB |

## 為什麼用這兩支

- **Trime 不自帶文字字體**：APK 內只有 `res/9B.ttf`（Material Design Icons 圖標字體）。
  主題裏寫的 `symbol.ttf` / `han.ttf` 只是文件名約定，`userDataDir/fonts/` 找不到就用系統字體。
- 用系統字體時，`“”‘’` 由 Roboto 提供 → 畫成**拉丁字形**（小、貼上緣），
  中文使用者會認爲「這不是引號」。要讓引號是中文寬字形，只能自帶 CJK 字體。
- 拉丁部分保留 Roboto 是為了與改造前的觀感一致（Noto Sans CJK 的拉丁偏細）。

## 商標與改名（重要）

兩個上游字體都是 Google／Adobe 的**註冊商標字體**（Noto 的 nameID 7 明文寫着
"Noto is a trademark of Google Inc."）。OFL 要求修改版不得使用原保留字體名，
Apache 2.0 也不得用原商標背書。因此子集的 `nameID 1/3/4/6/16/17` 已改為：

- `Xuma Key CJK`
- `Xuma Key Latin`

而 `nameID 0`（版權）與 `nameID 13/14`（授權聲明與連結）**保持原樣未改**——這是
OFL/Apache 對修改版的硬性要求。

## 重建方式

```sh
# 1) 字符集：主題裏所有 click/long_click/label ＋ ASCII 全表（見 tools/gen_icons.py 同款做法）
#    本倉用 /tmp/kbchars.txt 臨時存放，腳本化時應改為由主題自動收集。

# 2) CJK 子集（去掉 ASCII，讓拉丁走 xuma_latin.ttf）
uv run --with fonttools python - <<'PY'
from fontTools import subset
src  = '<NotoSansCJKsc-Regular.otf>'
chars = open('/tmp/kbchars.txt', encoding='utf-8').read()
cjk  = ''.join(c for c in chars if not 0x20 < ord(c) < 0x7f)
o = subset.Options(); o.layout_features = ['*']; o.name_IDs = ['*']
f = subset.load_font(src, o); s = subset.Subsetter(options=o)
s.populate(text=cjk); s.subset(f); subset.save_font(f, 'android/fonts/xuma_key.otf', o)
PY

# 3) 拉丁子集（ASCII；**刻意剔除 “”‘’**，讓引號落到 CJK 字體）
uv run --with fonttools python - <<'PY'
from fontTools import subset
src  = '<Roboto-Regular.ttf>'
chars = open('/tmp/kbchars.txt', encoding='utf-8').read()
lat  = ''.join(c for c in chars if 0x20 < ord(c) < 0x7f and c not in '‘’“”')
o = subset.Options(); o.layout_features = ['*']; o.name_IDs = ['*']
f = subset.load_font(src, o); s = subset.Subsetter(options=o)
s.populate(text=lat); s.subset(f); subset.save_font(f, 'android/fonts/xuma_latin.ttf', o)
PY

# 4) 改家族名（見上「商標與改名」）
```

⚠ **字重陷阱**：不要直接子集可變字體 `NotoSansCJK-VF.ttc`——它的默認實例是
`wght=100`（Thin），整把鍵盤會偏細。要用靜態 Regular，或先 `varLib.instancer` 固定 400。

## 若想整套都用 OFL（可選）

目前是 OFL 1.1（CJK）＋ Apache 2.0（拉丁）混用，兩者都允許商用與再分發，
只是分發時要**同時**附上兩份授權（已隨倉庫提供）。
若希望授權單一化，可把拉丁換成同爲 OFL 的 **Noto Sans** 或 **Inter**——
代價是字形觀感會變（Noto 的拉丁比 Roboto 細，Inter 比 Roboto 略寬）。
