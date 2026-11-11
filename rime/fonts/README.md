# fonts —— 鍵盤字體（開源授權）

本目錄包含 V1、V2 的鍵盤字體子集與上游授權文本。

| 檔 | 用途 | 上游 | 授權 |
|---|---|---|---|
| `xuma_key.otf` | 中文標點、引號、缺字回退 | Noto Sans CJK SC Regular 2.004（© 2014-2021 Adobe） | [SIL OFL 1.1](OFL-1.1.txt) |
| `xuma_latin.ttf` | 拉丁字母、數字、ASCII 符號 | Roboto 3.002（© 2011 Google Inc.） | [Apache License 2.0](Apache-2.0.txt) |
| `typewriter_latin.ttf` | V2-typewriter 的鍵帽，覆蓋 ASCII，中文沿用 V1 字體 | [Courier Prime Bold](https://github.com/google/fonts/tree/main/ofl/courierprime) | [SIL OFL 1.1](CourierPrime-OFL.txt) |
| `labelmaker_mono.otf` | V2-labelmaker、V2-cyanotype、V2-oscilloscope、V2-pixelblock 的等寬英數，收錄 `A–Z`、`a–z`、`0–9` | Source Code Pro Semibold（Adobe） | [SIL OFL 1.1](SourceCodePro-OFL.txt) |
| `halftone_latin.ttf` | V2-halftone、V2-patchwork 的粗體 ASCII | `xuma_latin.ttf` 的 Roboto Bold 子集，由 `gen-theme --theme v2-halftone` 生成 | [Apache License 2.0](Apache-2.0.txt) |

## 共用字體

- Trime 字體載入與缺字排查見[字體回退](../../.agents/skills/trime-theme/references/lessons.md#引號外觀與字體回退)。
- V1 保留 Roboto 的拉丁字形，`“”‘’` 由 Noto Sans CJK 子集提供中文排版字形。

## 子集名稱

兩個子集使用獨立的家族名稱（`nameID 1/3/4/6/16/17`）：

- `Xuma Key CJK`
- `Xuma Key Latin`

子集保留了上游的版權（`nameID 0`）和授權聲明與連結（`nameID 13/14`）。

## 重建方式

從倉庫根目錄執行：

```sh
uv run --with fonttools python tools/rebuild_key_font.py
```

腳本只重建 `xuma_key.otf`。它合併現有字體的碼位與 `EXTRA_CHARS`，從系統 Noto Sans CJK SC
抽出所需字形，再把可變字重固定為 Regular（`wght=400`），以免量測整套 CJK。`ㄓ` 留在字體內作備用。

手動重建拉丁子集時，使用 Roboto 的 ASCII 字形和 `Xuma Key Latin` 家族名，保留上游版權與授權資料。
`“”‘’` 由 CJK 子集提供。

V2-typewriter 的拉丁子集由 Courier Prime Bold 的 `U+0020–007E` 生成。用 FontTools 子集化時保留原
字體的名稱與授權資料。

## 若想整套都用 OFL（可選）

V1 共用字體採 OFL 1.1（CJK）及 Apache 2.0（拉丁），兩者都允許商用與再分發，
只是分發時要**同時**附上兩份授權（已隨倉庫提供）。
若希望授權單一化，可把拉丁換成同爲 OFL 的 **Noto Sans** 或 **Inter**——
代價是字形觀感會變（Noto 的拉丁比 Roboto 細，Inter 比 Roboto 略寬）。
