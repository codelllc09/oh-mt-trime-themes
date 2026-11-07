# 徐碼·L 安卓端（同文／Trime）

本倉提供徐碼·L 在 [Trime](https://github.com/osfans/trime) 3.3 以上版本使用的
手機主題、方案補丁、字體、部署與驗證工具。現行鍵盤規則只以
[`KEYBOARD_MAP.md`](KEYBOARD_MAP.md) 為準。

[查看 V1 的雲白與墨空實拍](design-refs/README.md#現行版本實拍)，包含四個鍵盤頁和八種回車鍵帽。

## 文件與入口

| 文件／命令 | 用途 |
|---|---|
| `xuma_L.trime.yaml` | 主題源檔，供人編輯 |
| `v1.trime.yaml` | 自包含生成物，手機實際載入 |
| `xuma_L.custom.yaml` | 手機端方案補丁 |
| `./deploy.sh push` | 推送到手機或 Waydroid |
| `./deploy.sh pkg` | 生成可手動解壓的部署包 |
| `tools/check_trime.py` | 資產校驗、部署清單與主題生成 |
| `KEYBOARD_MAP.md` | 鍵位、頁面、長按與版式規則 |
| `TESTING.md` | 最小測試選擇與設備操作 |
| `LESSONS.md` | 可復用的故障原因與避坑經驗 |
| `design-refs/README.md` | 設計流程、參考圖與定案索引 |
| `fonts/README.md` | 字體來源、授權與重建方法 |

## 倉庫邊界

本倉只維護 Trime 主題與 UI 資產；schema、詞典、Lua 和加詞管道仍由桌面
Rime 主倉提供。

| 根 | 內容 | 位置 |
|---|---|---|
| 本倉 | 主題、補丁、字體、背景、部署與驗證工具 | `~/Work/rime-tongwen` |
| 桌面主倉 | schema、詞典、Lua、台賬、spool 管道 | `RIME_DESKTOP_DIR`，默認 `~/.config/ibus/rime` |

部署清單先在本倉找 UI 資產，再到桌面主倉找共享文件。因此本倉不能脫離
桌面主倉單獨部署；修改 schema、詞典或 Lua 也應在桌面主倉完成。

## 部署

```sh
# USB／Waydroid
./deploy.sh push

# 或生成壓縮包，解壓到手機 rime 目錄
./deploy.sh pkg
```

手機端隨後：

1. 在 Trime 點「部署」；
2. 主題選 **V1**，配色選 **徐碼·雲白**或**徐碼·墨空**；
3. 選中方案「徐碼·L」。

首次安裝或清除應用資料後，Trime 會回到內建「預設」主題，需要重新選一次
V1。詞典較大，首次部署可能需要十餘秒。

### 離線語音（可選）

Trime 繼續作為預設鍵盤，負責徐碼與 V1 主題。「Fcitx5 SenseVoice」是可單獨安裝的
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
[主鍵盤長按規則](KEYBOARD_MAP.md#長按表) 開啓語音面板，點麥克風開始錄音。
辨識在手機本機完成，文字直接送回原輸入框，點面板上的鍵盤圖示即可切回 Trime。
Sayboard 可保留作備用。

## 手機加詞回桌面

手機 `/add` 收集的詞保存在部署目錄的
`lua/codelllc09/tools/dict_pipeline/spool_pending.txt`。回到桌面後執行：

```sh
./deploy.sh pull-spool
```

該命令去重並合併到桌面主倉的待處理清單；正式入庫仍在桌面管道完成。

## 修改流程

1. 版面、鍵位或配色先做現狀／建議並排的互動 HTML，放入 `design-refs/`；
2. 定案後修改 `xuma_L.trime.yaml`，並同步 `KEYBOARD_MAP.md`；
3. 生成並靜態校驗自包含主題：

   ```sh
   uv run python tools/check_trime.py gen-theme
   uv run python tools/check_trime.py
   ```

4. 只有需要看實機效果時才推送；按 `TESTING.md` 只驗證受影響部分。

全量測試只能在用戶明確要求時執行，具體約束見 `AGENTS.md`。

## CI

`.github/workflows/gate.yml` 檢查主題結構、生成物漂移和基本配色對比。
需要 Android／Waydroid 的渲染與交互驗證不在 CI 中執行。
