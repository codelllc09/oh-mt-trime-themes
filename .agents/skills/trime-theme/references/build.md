# 原型、生成與打包

命令從倉庫根目錄執行。

## 原型

用 [`render_keyboard.py`](../../../../tools/render_keyboard.py) 讀取現行配置並做局部渲染。以 1080p 為基準，用相同 dp／sp 比較不同密度。八位色值需按 [Trime 與 CSS 的位序](lessons.md#html-預覽的半透明色跑偏)轉換。

```sh
uv run --with pyyaml python tools/render_keyboard.py number --scheme xuma_night --out tmp/number-night.html
```

臨時圖放在 `tmp/`。原型、實拍、錄屏與外部參考放在 Git 忽略的 `design/`。

## 重建主題

常規重建用 `gen-theme`，預設生成 V1。**共用入口無法直接處理時，新增專用腳本。** 有適用的共用函式就重用。

```sh
uv run --with pyyaml python tools/check_trime.py gen-theme
```

V2 沿用 V1 鍵位。源檔放在 `rime/theme/sources/`，顯示名用 `V2-xxx`，主題 ID 用 `v2-xxx`。使用共用入口的繪圖函式在 [`theme_build`](../../../../tools/theme_build/__init__.py) 登記。

```sh
uv run --with pyyaml --with pillow python tools/check_trime.py gen-theme --theme v2-typewriter
uv run --with pyyaml --with pillow --with fonttools python tools/check_trime.py gen-theme --all --check
```

加 `--check` 比對生成物。生成 V2-halftone 或使用 `--all` 時加 `--with fonttools`。

### 鍵音

一般生成讀取 `rime/soundeffect/` 的描述檔和 WAV。從定案 HTML 匯入時指定單款 V2 並加 `--prototype 路徑`。加 `--sound-zips dist` 可輸出獨立音效包。

V2-typewriter 採用 [nvmbky 的 CC0 打字機實錄](https://freesound.org/people/nvmbky/sounds/801118/)。

## 更新鍵位指南

生成 V1 配色圖及互動指南。

```sh
uv run --with pyyaml --with pillow --with fonttools python tools/render_theme_guide.py \
  --out rime/theme/overview \
  --html-out keyboard-guide.html
```

生成 V2 配色圖時，將 `theme` 換成目標主題 ID。

```sh
theme=v2-typewriter
uv run --with pyyaml --with pillow --with fonttools python tools/render_theme_guide.py \
  --theme "rime/theme/$theme.trime.yaml" \
  --pages-from rime/theme/sources/v1.theme-source.yaml \
  --out rime/theme/overview
```

省略 `--out` 時輸出到 `tmp/theme-guide/`。可用 `--font` 指定繁體中文字體。

## 安裝包

先核對目標主題的部署清單，將 `--theme` 改成所需主題 ID。

```sh
uv run --with pyyaml python tools/check_trime.py manifest --theme v2-typewriter
```

本機用 `uv run --with pyyaml ./deploy.sh pkg` 打包全部主題，加 `--theme v1` 等主題 ID 可只打包一款。

準備 Release 時，將完整包與單款安裝包輸出到新目錄。

```sh
uv run --with pyyaml python tools/check_trime.py package-release dist/release
```

將 `trime-themes.zip` 和所有 `trime-<主題 ID>.zip` 一併上傳到同一個 Release。[手機安裝步驟](../../../../README.md#安装)
