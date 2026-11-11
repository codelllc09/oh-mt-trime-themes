# 安卓端測試手冊

適用於 Waydroid 和真機。**默認只跑與改動直接相關的最小測試；只有用戶明確
要求「全量測試」時，才執行完整驗證。** 可復用的故障原因見[故障經驗](LESSONS.md)。
下列命令從倉庫根目錄執行。

## 測試選擇

| 改動 | 默認驗證 |
|---|---|
| 文檔、註釋 | 檢查連結與命令；不啓動 Waydroid、不部署 |
| 配色、文字、單一字號 | 靜態校驗；需要實機時只看相關頁 |
| 單鍵輸出或長按 | `verify.sh --section <相關段>` 或手動驗該鍵 |
| 鍵寬、行高、間距、導航 | 靜態校驗＋只看受影響頁；不自動擴大範圍 |
| 字體或背景圖片 | 只看受影響字符／圖片；必要時重啓 Trime 清緩存 |
| 驗證工具本身 | 只跑修改到的工具或段落 |
| schema、詞典、Lua | 回桌面主倉驗證，不在本倉修改 |

下列完整回歸項目只在用戶明確要求「全量測試」時執行：

- 完整執行 `tools/verify.sh`；單用 `--no-clip` 仍會跑其餘各段；
- `tools/shots.sh` 全套深淺色截圖；
- 把全量部署／字典編譯當作回歸步驟；
- 1080p 與 2K 的全頁回歸；
- 長時間穩定性測試。

最小測試失敗時先查該項，不得自行升級為全量測試。

## 靜態校驗

只修改文檔時不需要運行。改主題配置時按需執行：

```sh
uv run --with pyyaml python tools/check_trime.py gen-theme
uv run --with pyyaml python tools/check_trime.py
```

在倉庫編輯 `rime/theme/sources/v1.theme-source.yaml`，再生成 `rime/theme/v1.trime.yaml`。
驗證徐碼·L 手機補丁時，先按[選裝說明](../extras/xuma-l/README.md)指定桌面 Rime 目錄。CI 會略過依賴方案的檢查。

## 設備操作

冷啓動後先開一次同文測試框，確認徐碼底行顯示 `123#`，再切換待驗主題。
若初次出現預設鍵盤，關閉測試框，待徐碼初始化後再開。仍顯示預設鍵盤時，從方案選單重選徐碼·L。
以實際鍵面確認版式後才使用固定座標。

```sh
adb devices
# 測試徐碼·L 時，將序號換成 adb devices 顯示的裝置序號
SER='裝置序號'
TRIME_NO_DEPLOY=1 TRIME_ADB_SERIAL="$SER" ./deploy.sh push --xuma
```

推送後在 Trime 點「部署」，確認主題仍為 V1，再到測試輸入框驗證。若手機已具備相同的方案與資產，
只驗主題時可單獨同步新的 `v1.trime.yaml`，再點「部署」。

按受影響範圍選擇指令，例如：

```sh
TRIME_ADB_SERIAL="$SER" ./tools/verify.sh --section 3
TRIME_ADB_SERIAL="$SER" ./tools/verify.sh --quick
```

`verify.sh` 在 1080 × 2280 的 Android 系統設定搜尋框內自動點擊，並讀取 Unicode 碼位判定結果。
Tab、撤銷／恢復及剪貼板操作需要在真機多行文本框中單獨驗證。

## 主要尺寸

| 檔 | 分辨率 | density | 用途 |
|---|---|---|---|
| 1080p | 1080×2280 | 420 | 設計、實拍和自動點擊基準 |
| 2K | 1440×3200 | 560 | 用戶要求時抽驗縮放 |

主題使用同一套 dp／sp。V1 座標按[現行鍵位表](KEYBOARD_MAP.md)和設備畫面推導。
`kbmap.py` 的座標表屬於舊 36 鍵版，`--profile` 只會縮放那套座標。
臨時截圖和錄屏放在 `tmp/`。實拍放在 `design/screenshots/`，
留存的驗收錄屏放在 `design/recordings/`。

## 單項人工檢查表

按改動挑選相關行，不需要全部執行：

| 項目 | 預期 |
|---|---|
| 部署與主題 | 無錯誤；V1、雲白／墨空可正常選擇 |
| 常規輸入 | 候選、註解、字根 preedit 和上屏正常 |
| 詞長／簡繁／字符集／非簡 | `/menu` 中受影響檔位切換後立即生效 |
| 註解檔 | `/menu` 切換打字或反查註解後，候選註釋相應變化 |
| 中英切換 | 地球鍵切換正常，返回主鍵盤後狀態保持 |
| 頁面導航 | `123# → number → ASC/CJK → 123/ABC` 可返回 |
| 主鍵盤標點 | 中文態輸出中文形，英文態輸出 ASCII |
| 數字與符號頁 | ASCII 鍵受工具欄全半角控制；Unicode 變體原樣上屏 |
| 長按 | 受影響鍵符合[鍵位表](KEYBOARD_MAP.md) |
| 反查 | z 長按後可用拼音反查；拼音＋筆畫組合過濾正常 |
| 碼位 | 手機鍵盤使用小寫 `u`＋數字通道；需要時單獨驗證 |
| 動態命令 | 受影響時單獨驗 `/time`、`/date` 或 `/dx123` |
| `/add` | 數字選鍵可收錄；重啓後 spool 仍保留 |
| 剪貼板 | v 長按直接粘貼；b 長按打開剪貼板頁 |
| 深淺色 | 受影響頁的文字和按鍵對比正常 |

## 常見故障

| 現象 | 優先檢查 |
|---|---|
| 修改源主題後毫無變化 | 是否重新生成 `rime/theme/v1.trime.yaml`；手機是否仍選 V1 |
| `force-stop` 後回到 AOSP 鍵盤 | `adb shell ime set com.osfans.trime/.ime.core.TrimeInputMethodService` |
| Trime 崩潰後鍵盤不彈 | 重啓容器清除服務退避，再點輸入框喚起 |
| 深色模式不聯動 | 是否開啓跟隨系統；配色是否選雲白 |
| 圖片更新後仍顯示舊圖 | `force-stop` Trime 後重新喚起，清除 bitmap 緩存 |
| 圖片被拉伸 | 圖片長寬比是否與實際鍵位一致 |
| ASCII 頁輸出全角 | 先確認工具欄為半角（彎月），再檢查 `ascii_mode: 1` |
| 長按有角標但選單不可見 | 檢查 `popup_width`、`popup_height`、`popup_key_height` 是否大於零 |
| 中文引號看似不對 | 讀 Unicode 碼位，再檢查字體鏈 |
| 崩潰頁信息被截斷 | `adb logcat -d -s AndroidRuntime:E` |

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
[主鍵盤長按規則](KEYBOARD_MAP.md#長按表) 開啓語音面板，點麥克風開始錄音。
辨識在手機本機完成，文字直接送回原輸入框，點面板上的鍵盤圖示即可切回 Trime。
Sayboard 可保留作備用。

## Waydroid 一次性環境

```sh
sudo dnf install waydroid scrcpy
sudo waydroid init -c https://ota.waydro.id/system -v https://ota.waydro.id/vendor
sudo semodule -B
sudo /sbin/load_policy -i
sudo systemctl enable --now waydroid-container
```

若窗口失焦後部署停住，將 Waydroid `suspend_action` 設為 `ignore` 後重啓容器。
不為小改動啓動部署；宿主資源不足時停止設備測試，不用全量任務硬撐。
