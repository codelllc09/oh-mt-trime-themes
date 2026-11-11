# 驗證與部署

命令從倉庫根目錄執行。實機驗證適用於 Waydroid 和真機。

## 驗證範圍

| 改動 | 驗證 |
|---|---|
| 文檔、註釋 | 核對連結與命令 |
| 主題配置或資產 | `uv run --with pyyaml python tools/check_trime.py`。按需加跑 `gen-theme --check`，校驗 V2 時加 `--theme 主題 ID` 和生成所需依賴 |
| 鍵位輸出或長按 | 手動抽驗受影響的鍵，或執行 `verify.sh --section N` |
| 鍵寬、行高、間距、導航 | 抽驗受影響頁面，按[鍵位表](../../../../docs/KEYBOARD_MAP.md)核對返回、語言態與按鍵動作 |
| 字體或圖片 | 抽查受影響的字符、鍵面及深淺色對比。舊圖仍出現時查[圖片快取](lessons.md#圖片替換後仍顯示舊圖) |
| 安裝檔案 | 核對[部署清單](build.md#安裝包)和 ZIP 內路徑 |
| 驗證工具 | 只執行修改到的工具或測試段落 |

## 實機部署

用 `adb devices` 確認裝置。多台在線時，用 `TRIME_ADB_SERIAL` 指定序號。按需更換主題 ID。

```sh
TRIME_NO_DEPLOY=1 uv run --with pyyaml ./deploy.sh push --theme v1
```

在同文點「部署」，選擇待驗主題與配色，打開輸入框確認鍵面。驗證鍵音時選同名音效包，按同樣節奏抽聽字鍵、退格和回車。

### 自動點擊

截圖與驗證預設讀取執行中的 Waydroid 位址。指定 `TRIME_ADB_SERIAL` 時使用指定裝置。

`SER` 為 `adb devices` 顯示的序號。`--section 3` 檢查長按，`--quick` 跳過長按全表、功能鍵和剪貼板，`--no-clip` 只跳過剪貼板。

```sh
TRIME_ADB_SERIAL="$SER" uv run --with pillow ./tools/verify.sh --section 3
```

腳本在 Android 系統設定搜尋框中測試 V1。開始前確認實際鍵面和尺寸。用 UI 節點定位輸入框，批次輸入後讀回碼位，失敗時再逐鍵定位。Tab、撤銷／恢復和剪貼板可在多行輸入框單獨驗證。[座標與碼位排查](lessons.md#鍵位測試點錯位置或認錯字元)

### 主要尺寸

1080 × 2280、420 dpi 為設計和自動點擊基準。2K 抽驗使用 1440 × 3200、560 dpi。V1 的座標從[鍵位表](../../../../docs/KEYBOARD_MAP.md)和現行畫面推導。座標變更時同步 `verify.sh` 和 `shots.sh` 的受影響點位。`kbmap.py --profile` 只縮放舊 36 鍵版座標。

### 徐碼·L 選裝驗證

依[選裝說明](../../../../extras/xuma-l/README.md)指定桌面 Rime 目錄並推送補丁。部署後選徐碼·L，確認底行有 `123#`。冷啟動若暫時顯示預設鍵盤，待方案載入後重開輸入框，必要時重選方案。

按改動抽驗候選上屏、註解、字根 preedit、數字與退格、`ABC` 返回。涉及方案功能時，檢查對應的 `/menu` 檔位、拼音或筆畫反查、小寫 `u` 碼位輸入、動態命令或 `/add` 暫存重啟後是否保留。

### 錄影

用 scrcpy 同時錄製畫面與內部音訊，核對受影響的鍵面和聲音。Wayland 無窗錄影遇 SDL 初始化錯誤時，可為該次行程設定 `SDL_VIDEODRIVER=dummy`。截圖及錄屏暫存於 `tmp/`，留存檔放在 `design/screenshots/` 或 `design/recordings/`。[鍵音錄影排查](lessons.md#錄影未能呈現鍵音)

## 常見故障

- 更新後仍是舊主題，先核對[生成檔](build.md#重建主題)和裝置實際選用的主題。
- `force-stop` 後回到 AOSP 鍵盤，可用 `adb shell ime set com.osfans.trime/.ime.core.TrimeInputMethodService` 恢復。
- 崩潰訊息被截斷時讀 `adb logcat -d -s AndroidRuntime:E`。Waydroid 若因服務退避無法喚起鍵盤，可重啟容器後再開輸入框。
- V1 深淺色未切換時，選雲白並核對[日夜配色設定](lessons.md#深淺色未跟隨系統切換)。

## 離線語音（可選）

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
[主鍵盤長按規則](../../../../docs/KEYBOARD_MAP.md#長按表) 開啓語音面板，點麥克風開始錄音。
辨識在手機本機完成，文字直接送回原輸入框，點面板上的鍵盤圖示即可切回 Trime。
Sayboard 可保留作備用。

## Waydroid 一次性環境

在 Fedora 新建測試環境時參考。

```sh
sudo dnf install waydroid scrcpy
sudo waydroid init -c https://ota.waydro.id/system -v https://ota.waydro.id/vendor
sudo semodule -B
sudo /sbin/load_policy -i
sudo systemctl enable --now waydroid-container
```

若窗口失焦後部署停住，將 Waydroid `suspend_action` 設為 `ignore` 後重啓容器。
宿主資源不足時暫停設備測試。
