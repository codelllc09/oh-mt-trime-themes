# 主題概覽與設計流程

原型、實拍、錄屏與外部參考放在本機 `design/`，由 Git 忽略。

## 主題概覽

[V1 雲白總覽](../rime/theme/overview/v1-cloud.png) · [V1 墨空總覽](../rime/theme/overview/v1-night.png)

### V2 配色圖

- [V2-typewriter](../rime/theme/overview/v2-typewriter.png) · [V2-calculator](../rime/theme/overview/v2-calculator.png) · [V2-labelmaker](../rime/theme/overview/v2-labelmaker.png)
- [V2-halftone](../rime/theme/overview/v2-halftone.png) · [V2-contour](../rime/theme/overview/v2-contour.png) · [V2-cyanotype](../rime/theme/overview/v2-cyanotype.png)
- [V2-patchwork](../rime/theme/overview/v2-patchwork.png) · [V2-stainedglass](../rime/theme/overview/v2-stainedglass.png) · [V2-oscilloscope](../rime/theme/overview/v2-oscilloscope.png)
- [V2-pixelblock](../rime/theme/overview/v2-pixelblock.png) · [V2-cassette](../rime/theme/overview/v2-cassette.png) · [V2-terrazzo](../rime/theme/overview/v2-terrazzo.png)
- [V2-bauhaus](../rime/theme/overview/v2-bauhaus.png) · [V2-perforation](../rime/theme/overview/v2-perforation.png) · [V2-interlock](../rime/theme/overview/v2-interlock.png)
- [V2-backplane](../rime/theme/overview/v2-backplane.png) · [V2-vacuum](../rime/theme/overview/v2-vacuum.png) · [V2-thermogram](../rime/theme/overview/v2-thermogram.png)
- [V2-foundry](../rime/theme/overview/v2-foundry.png) · [V2-wafer](../rime/theme/overview/v2-wafer.png) · [V2-pneumatic](../rime/theme/overview/v2-pneumatic.png)

## 由配置生成的鍵位指南

[V1 互動鍵位指南](../keyboard-guide.html)說明所有主題共用的按鍵功能。點圖上的編號即可查看動作。
各主題的配色圖展示中英文態、數字小鍵盤和符號頁。

從倉庫根目錄生成 V1 的互動指南和配色 PNG。

```sh
uv run --with pyyaml --with pillow --with fonttools python tools/render_theme_guide.py \
  --out rime/theme/overview \
  --html-out keyboard-guide.html
```

以 V2-typewriter 為例，從手機主題和鍵帽資產生成配色 PNG。將 `$theme` 改成其他主題 ID 即可重用。

```sh
theme=v2-typewriter
uv run --with pyyaml --with pillow --with fonttools python tools/render_theme_guide.py \
  --theme "rime/theme/$theme.trime.yaml" \
  --pages-from rime/theme/sources/v1.theme-source.yaml \
  --out rime/theme/overview
```

省略 `--out` 時，產物放在 `tmp/theme-guide/`。生成圖片需要繁體中文字體，可用 `--font` 指定。

## 重建與打包

改動共用鍵位後，先重建 V1，再執行受影響的 V2 生成器。

```sh
uv run --with pyyaml python tools/check_trime.py gen-theme
uv run --with pyyaml python tools/check_trime.py
```

在倉庫根目錄執行相應的 V2 生成器，例如 `uv run --with pyyaml --with pillow python tools/gen_typewriter.py`。
V2-halftone 另加 `--with fonttools`。用 `--check` 比對生成物。

| 主題 | 生成器 |
|---|---|
| V2-typewriter | `gen_typewriter.py` |
| V2-calculator | `gen_calculator.py` |
| V2-labelmaker | `gen_labelmaker.py` |
| V2-halftone | `gen_halftone.py` |
| V2-contour | `gen_contour.py` |
| V2-cyanotype、V2-patchwork、V2-stainedglass | `gen_materials.py` |
| V2-oscilloscope、V2-pixelblock | `gen_scope_pixel.py` |
| V2-cassette、V2-terrazzo、V2-bauhaus | `gen_contrast.py` |
| V2-perforation、V2-interlock、V2-backplane、V2-vacuum、V2-thermogram | `gen_industrial.py` |
| V2-foundry、V2-wafer、V2-pneumatic | `gen_factory.py` |

`gen_scope_pixel.py`、`gen_contrast.py`、`gen_industrial.py` 和 `gen_factory.py` 支援 `--sound-zips dist`，可另存音效包。
V2-typewriter 的鍵音取自 [nvmbky 的 CC0 打字機實錄](https://freesound.org/people/nvmbky/sounds/801118/)。

打包全部純主題到 `dist/`。加 `--theme v1` 或其他主題 ID 可只打包一款。

```sh
uv run --with pyyaml ./deploy.sh pkg
```

透過 USB 推送單款後，在同文點「部署」。多台裝置同時在線時，用 `TRIME_ADB_SERIAL` 指定目標。

```sh
TRIME_NO_DEPLOY=1 uv run --with pyyaml ./deploy.sh push --theme v1
```

## 設計流程

版面、鍵位或配色改動先做**現狀／建議並排**的單檔互動 HTML，經確認後才改
[V1 源檔](../rime/theme/sources/v1.theme-source.yaml)。示意圖須遵守：

- 同屏比較原稿與修改稿，不能只給修改版；
- 短按與長按兩層都要呈現；
- 尺寸與顏色從主題讀取或按實機像素計算，不憑眼估；
- 1080p 為主稿，2K 按同一套 dp／sp 縮放；
- 定案後只把最終結果同步到[鍵位表](KEYBOARD_MAP.md)。

優先用 `tools/render_keyboard.py` 讀主題生成畫面，避免示意圖與配置分叉：

```sh
uv run --with pyyaml python tools/render_keyboard.py number --scheme xuma_night
uv run --with pyyaml python tools/render_keyboard.py number --scheme xuma_cloud
```

Trime 顏色使用 `#AARRGGBB`，CSS 使用 `#RRGGBBAA`，八位色值不能直接照搬。

## 參考圖

| 檔案 | 用途 |
|---|---|
| Gboard 拼音 | 小寫字母、功能鍵層級、地球鍵與留白 |
| 同文風格 | 文字 Shift、藍色 Enter、同文式功能鍵 |
| 中英雙字鍵 | 中英狀態鍵和大寫字母方案的比較 |
| 箭頭字形 | 對照不同字號的箭頭和實心三角 |

主鍵盤預設使用小寫字母、文字 Shift 和實心藍色 Enter。地球鍵切換語言。
各方案的空格鍵標籤見[鍵位表](KEYBOARD_MAP.md#空格鍵標籤)。

現行數字與符號頁的版面、返回鍵和剪貼板手勢統一記在[鍵位表](KEYBOARD_MAP.md)。
剪貼板卡片的操作、過期時間和空狀態文案由 Trime 管理。

## 留存原則

本機原型可保留作視覺回歸。鍵音生成器可讀取本機定案原型，也可使用倉庫收錄的 WAV。
可復用的技術原因寫入[故障經驗](LESSONS.md)。
