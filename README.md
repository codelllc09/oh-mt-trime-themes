# Oh My Trime Themes

[同文（Trime）](https://github.com/osfans/trime) 的通用 26 鍵主題集，包含鍵盤版面、
配色、字體與鍵音，以同文 3.3.13 為驗證基準。

提供部署與驗證工具，另附[徐碼·L 選裝整合](extras/xuma-l/README.md)。
現行鍵位見[鍵位表](docs/KEYBOARD_MAP.md)。

[查看 V1 的雲白與墨空預覽](design/README.md#通用鍵盤預覽)，包含通用主鍵盤、共用頁和回車鍵帽。
[開啓 V1 鍵位指南](design/guides/v1/index.html)可按圖上編號查看特殊按鍵的動作。
[V2-typewriter 配色圖](design/guides/v2-typewriter/typewriter_ink.png)。
[V2-calculator 配色圖](design/guides/v2-calculator/calculator_lcd.png)。
[V2-halftone 配色圖](design/guides/v2-halftone/halftone_print.png)。
[V2-contour 配色圖](design/guides/v2-contour/contour_atlas.png)。

## 文件與入口

| 位置 | 內容 |
|---|---|
| [`rime/`](rime/) | 背景、鍵音與[字體及授權](rime/fonts/README.md) |
| [`rime/theme/`](rime/theme/) | 可安裝的 `*.trime.yaml` 與生成用的 Trime 預設 `vendor/` |
| [`rime/theme/sources/`](rime/theme/sources/) | [V1 源檔](rime/theme/sources/v1.theme-source.yaml)、[打字機源檔](rime/theme/sources/v2-typewriter.theme-source.yaml)、[計算機源檔](rime/theme/sources/v2-calculator.theme-source.yaml) |
| [`extras/xuma-l/`](extras/xuma-l/) | 選裝的徐碼·L 補丁與部署說明 |
| [`docs/`](docs/) | [鍵位表](docs/KEYBOARD_MAP.md)、[測試手冊](docs/TESTING.md)、[故障經驗](docs/LESSONS.md) |
| [`design/`](design/README.md) | 互動原型、鍵位指南、參考圖與實拍 |
| [`tools/`](tools/) | 主題生成、預覽、校驗及截圖工具 |
| [`deploy.sh`](deploy.sh) | 推送、打包與回收手機加詞 |

`dist/` 存放部署與音效包，`tmp/` 存放臨時產物，`third-party-skins/` 存放本機收集的外部皮膚。
這三處和 `design/recordings/` 皆由 Git 忽略。

## 安裝

公開發佈時，將純主題 ZIP 上傳為 Release 附件。使用者下載後可直接解壓安裝。

在倉庫根目錄打包全部主題。

```sh
uv run --with pyyaml ./deploy.sh pkg
```

將 `dist/` 內生成的 ZIP 解壓到同文設定所示的「使用者資料夾」，在同文點「部署」，再選所需主題與配色。ZIP 只包含主題與配套資產，沿用手機現有方案。

加上 `--theme v1` 或 `--theme v2-typewriter` 可只打包一款。同文會為字母型 26 鍵方案選用共用佈局，徐碼·L 和朙月拼音各有少量鍵位覆寫。需要方案與詞典時，見[徐碼·L 選裝](extras/xuma-l/README.md)。

### USB 推送

```sh
adb devices
TRIME_NO_DEPLOY=1 uv run --with pyyaml ./deploy.sh push --theme v1
```

推送後在同文點「部署」。多台裝置同時在線時，用 `TRIME_ADB_SERIAL` 指定目標。

### V2-typewriter

V2 沿用 V1 的鍵位與手勢。已有同文方案時，把 V2 壓縮包的內容合併到同文設定中顯示的
「使用者資料夾」，再於主題選單選 **V2-typewriter**。同文 3.3.13 的預設資料夾為
`/storage/emulated/0/Android/data/com.osfans.trime/files/rime`。全部主題的安裝包也包含 V2。

在同文「虛擬鍵盤」設定打開「按鍵聲音」與「使用自訂按鍵音」，並在「自訂按鍵音效」選
**V2-typewriter**，將按鍵音量設為大於 0 的值。音效包是同文的全局設定，切回 V1 時可在同處換回原本的音效。
字鍵、空格、退格和回車取自 [nvmbky 的 CC0 打字機實錄](https://freesound.org/people/nvmbky/sounds/801118/)。
回車是滑架回位聲。

修改 V2 外觀後，用下列命令生成手機主題、鍵帽圖及實錄鍵音。

```sh
uv run --with pyyaml --with pillow python tools/gen_typewriter.py
uv run --with pyyaml --with pillow python tools/gen_typewriter.py --check
uv run --with pyyaml python tools/check_trime.py manifest --typewriter
```

### V2-calculator

沿用 V1 鍵位，採用灰綠液晶候選欄、塑膠方鍵及琥珀色回車。整套部署包包含主題和音效。
主題選 **V2-calculator**，再於「虛擬鍵盤」的「自訂按鍵音效」另選同名音效包。
字鍵是塑膠按鍵聲，回車多一聲短促電子音。

```sh
uv run --with pyyaml --with pillow python tools/gen_calculator.py
uv run --with pyyaml --with pillow python tools/gen_calculator.py --check
uv run --with pyyaml python tools/check_trime.py manifest --calculator
```

### V2-labelmaker

熱感標籤機沿用 V1 鍵位，使用奶白候選紙帶、石墨灰鍵帽與琥珀色回車。主題選 **V2-labelmaker**，
再於「虛擬鍵盤」的「自訂按鍵音效」另選同名音效包。回車是短促的走紙切刀聲。
[配色圖](design/guides/v2-labelmaker/labelmaker_tape.png)

```sh
uv run --with pyyaml --with pillow python tools/gen_labelmaker.py
uv run --with pyyaml --with pillow python tools/gen_labelmaker.py --check
uv run --with pyyaml python tools/check_trime.py manifest --labelmaker
```

### V2-halftone

套色漫畫沿用 V1 鍵位，採用對白框候選欄、網點底板和朱紅回車。主題選 **V2-halftone**，
再於「虛擬鍵盤」的「自訂按鍵音效」選同名音效包。字鍵是紙角輕彈，回車是短促翻頁聲。

```sh
uv run --with pyyaml --with pillow --with fonttools python tools/gen_halftone.py
uv run --with pyyaml python tools/check_trime.py manifest --halftone
```

### V2-contour

等高線地圖沿用 V1 鍵位，採用砂色等高線底板、墨綠功能鍵和橘紅回車。主題選 **V2-contour**，
再於「虛擬鍵盤」的「自訂按鍵音效」選同名音效包。字鍵是鉛筆輕敲圖板，回車是兩下落筆聲。

```sh
uv run --with pyyaml --with pillow python tools/gen_contour.py
uv run --with pyyaml python tools/check_trime.py manifest --contour
```

### 藍曬植物標本、刺繡布章、彩繪玻璃窗

三款均沿用 V1 鍵位。在同文選主題，再於「虛擬鍵盤」的「自訂按鍵音效」選同名音效包。

| 主題 | 鍵音 | 配色圖 |
|---|---|---|
| V2-cyanotype | 紙面輕按，回車壓籤 | [藍曬植物標本](design/guides/v2-cyanotype/cyanotype_fern.png) |
| V2-patchwork | 布面悶敲，回車稍沉 | [刺繡布章](design/guides/v2-patchwork/patchwork_denim.png) |
| V2-stainedglass | 玻璃輕碰，回車短鳴 | [彩繪玻璃窗](design/guides/v2-stainedglass/stainedglass_amber.png) |

```sh
uv run --with pyyaml --with pillow python tools/gen_materials.py
uv run --with pyyaml --with pillow python tools/gen_materials.py --check
```

用 `manifest --cyanotype`、`--patchwork` 或 `--stainedglass` 列出各款的獨立安裝檔。

### 示波器與像素積木

**V2-oscilloscope** 使用整面冷光刻度和靜態波形，回車為短掃頻。**V2-pixelblock** 用跨鍵色塊和階梯邊，回車為雙音。
在同文選主題後，到「虛擬鍵盤」另選同名音效包。

```sh
uv run --with pyyaml --with pillow python tools/gen_scope_pixel.py --sound-zips dist
uv run --with pyyaml --with pillow python tools/gen_scope_pixel.py --check
```

用 `manifest --oscilloscope` 或 `manifest --pixelblock` 列出各款的獨立安裝檔。

### 卡帶隨身聽、水磨石、包浩斯幾何

三款沿用 V1 鍵位。在同文選主題後，到「虛擬鍵盤」選同名鍵音。

| 主題 | 鍵音 | 配色圖 |
|---|---|---|
| V2-cassette | 磁帶機卡扣，回車落鎖 | [卡帶隨身聽](design/guides/v2-cassette/cassette_tape.png) |
| V2-terrazzo | 石粒輕碰，回車雙叩 | [水磨石](design/guides/v2-terrazzo/terrazzo_stone.png) |
| V2-bauhaus | 木塊短敲，回車低音 | [包浩斯幾何](design/guides/v2-bauhaus/bauhaus_primary.png) |

```sh
uv run --with pyyaml --with pillow python tools/gen_contrast.py --sound-zips dist
uv run --with pyyaml --with pillow python tools/gen_contrast.py --check
```

用 `manifest --cassette`、`--terrazzo` 或 `--bauhaus` 列出各款的獨立安裝檔。

### 五款工業主題

五款沿用 V1 鍵位。在同文選主題後，到「虛擬鍵盤」選同名鍵音。

| 主題 | 配色圖 |
|---|---|
| V2-perforation | [沖孔鋁板](design/guides/v2-perforation/perforation_industrial.png) |
| V2-interlock | [重工聯鎖面板](design/guides/v2-interlock/interlock_industrial.png) |
| V2-backplane | [接線背板](design/guides/v2-backplane/backplane_industrial.png) |
| V2-vacuum | [真空管陣列](design/guides/v2-vacuum/vacuum_industrial.png) |
| V2-thermogram | [工業熱像儀](design/guides/v2-thermogram/thermogram_industrial.png) |

```sh
uv run --with pyyaml --with pillow python tools/gen_industrial.py --sound-zips dist
uv run --with pyyaml --with pillow python tools/gen_industrial.py --check
```

用 `manifest --perforation`、`--interlock`、`--backplane`、`--vacuum` 或 `--thermogram` 列出各款的獨立安裝檔。

### 砂型鑄造、晶圓步進機、氣動分揀台

三款沿用 V1 鍵位。在同文選主題，再於「虛擬鍵盤」選同名音效。

| 主題 | 配色圖 |
|---|---|
| V2-foundry | [砂型鑄造](design/guides/v2-foundry/foundry.png) |
| V2-wafer | [晶圓步進機](design/guides/v2-wafer/wafer.png) |
| V2-pneumatic | [氣動分揀台](design/guides/v2-pneumatic/pneumatic.png) |

```sh
uv run --with pyyaml --with pillow python tools/gen_factory.py --sound-zips dist
```

用 `manifest --foundry`、`--wafer` 或 `--pneumatic` 列出獨立安裝檔。

### 離線語音（可選）

Trime 繼續作為預設鍵盤，使用原有方案與主題。「Fcitx5 SenseVoice」是可單獨安裝的
Android 語音輸入法（`com.fcitx5sensevoice`），無須小企鵝主程式或其 Rime 插件。
語音 APK 與模型需另行準備。

| 元件 | 實測版本與來源 |
|---|---|
| Trime | 3.3.8 起支援 `VOICE_ASSIST`，本倉以 3.3.13 驗證。 [Trime 發行頁](https://github.com/osfans/trime/releases/tag/v3.3.13) |
| 獨立語音輸入法 | Fcitx5 SenseVoice 0.1.7，原始碼提交 `6119808`，Android 9 以上。 [原始碼與建置說明](https://github.com/stormrise/fcitx5-sensevoice) |
| 語音 APK 內含 | sherpa-onnx 1.13.8、Silero VAD、SenseVoice Small INT8（2024-07-17）。 [sherpa-onnx 發行頁](https://github.com/k2-fsa/sherpa-onnx/releases/tag/v1.13.8) · [模型檔](https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/tree/main) |

上游該提交預設使用 2025-09-09 粵語微調版。要重現本倉實測的版本，請在建置語音 APK 時
改用表中的 2024-07-17 模型，並同步 `ModelManager.kt` 內的模型 SHA-256。
ARM64 手機使用 `arm64-v8a`，本倉的 Waydroid 測試版另打包了 `x86_64`。

安裝語音 APK 後，在 Android 的「管理螢幕鍵盤」啓用它並授予麥克風權限，再到
Trime「一般」→「首選語音輸入」選 **Fcitx5 SenseVoice**。依
[主鍵盤長按規則](docs/KEYBOARD_MAP.md#長按表) 開啓語音面板，點麥克風開始錄音。
辨識在手機本機完成，文字直接送回原輸入框，點面板上的鍵盤圖示即可切回 Trime。
Sayboard 可保留作備用。

## 修改流程

1. 版面、鍵位或配色先做現狀／建議並排的互動 HTML，放入 `design/prototypes/`；
2. 定案後修改 `rime/theme/sources/v1.theme-source.yaml`，並同步 `docs/KEYBOARD_MAP.md`；
3. 生成並靜態校驗自包含主題：

   ```sh
   uv run --with pyyaml python tools/check_trime.py gen-theme
   uv run --with pyyaml python tools/check_trime.py
   ```

   V2 繼承 V1，改動 V1 後也按上方命令重生成 V2。

4. 按[指南生成步驟](design/README.md#由配置生成的鍵位指南)更新受影響的配色 PNG。V1 同步更新互動鍵位指南。
5. 只有需要看實機效果時才推送，按[測試手冊](docs/TESTING.md)驗證受影響部分。

全量測試只能在用戶明確要求時執行，具體約束見 `AGENTS.md`。

## CI

`.github/workflows/gate.yml` 檢查主題結構、生成物漂移和基本配色對比。
需要 Android／Waydroid 的渲染與交互驗證不在 CI 中執行。
