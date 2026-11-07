# 安卓端測試手冊

適用於 Waydroid 和真機。**默認只跑與改動直接相關的最小測試；只有用戶明確
要求「全量測試」時，才執行完整驗證。** 可復用的故障原因放在 `LESSONS.md`，
本文件只保留操作流程。

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

以下操作都不是默認步驟，必須由用戶明確要求「全量測試」後才能執行：

- 無參數執行完整 `tools/verify.sh`；
- `tools/shots.sh` 全套深淺色截圖；
- 全量部署／字典編譯；
- 1080p 與 2K 的全頁回歸；
- 長時間穩定性測試。

最小測試失敗時先查該項，不得自行升級為全量測試。

## 靜態校驗

只修改文檔時不需要運行。改主題配置時按需執行：

```sh
uv run python tools/check_trime.py gen-theme
uv run python tools/check_trime.py
```

`xuma_L.trime.yaml` 是源檔，`v1.trime.yaml` 是生成物，不直接手改生成物。

## 設備操作

```sh
# Waydroid；真機 USB 可省略 connect
adb connect localhost:5555

# 只有需要觀察實機效果時才推送
TRIME_ADB_SERIAL=<SER> ./deploy.sh push
```

推送後在 Trime 點「部署」，確認主題仍為 V1，再到 Test input 輸入框測試。

不要手猜鍵位座標，使用：

```sh
uv run python tools/kbmap.py --serial <SER> --keys
uv run python tools/kbmap.py --serial <SER> --type tigu
uv run python tools/kbmap.py --serial <SER> --tap slash
uv run python tools/kbmap.py --serial <SER> --longpress z
uv run python tools/kbmap.py --serial <SER> --backspace 6
```

按段驗證示例：

```sh
TRIME_ADB_SERIAL=<SER> ./tools/verify.sh --quick
TRIME_ADB_SERIAL=<SER> ./tools/verify.sh --section 3
TRIME_ADB_SERIAL=<SER> ./tools/verify.sh --no-clip
```

`verify.sh` 以輸入框中的 Unicode 碼位判定結果，不用肉眼猜字符。Waydroid
搜索框不能可靠驗證 Tab、撤銷／恢復、全選／剪切／複製／粘貼的實際效果，
這些功能需在真機多行文本框中單獨複驗。

## 主要尺寸

| 檔 | 分辨率 | density | 用途 |
|---|---|---|---|
| 1080p | 1080×2280／2340 | 420 | 主設計基準 |
| 2K | 1440×3200 | 560 | 用戶要求時抽驗縮放 |

主題尺寸使用 dp／sp，不為不同分辨率維護第二份主題。鍵位座標由
`kbmap.py --profile 1080p` 或 `--profile 2k` 換算。截圖和錄屏放在已忽略的
`tmp/`，不要加入倉庫。

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
| 長按 | 受影響鍵符合 `KEYBOARD_MAP.md` |
| 反查 | z 長按後可用拼音反查；拼音＋筆畫組合過濾正常 |
| 碼位 | 手機鍵盤使用小寫 `u`＋數字通道；需要時單獨驗證 |
| 動態命令 | 受影響時單獨驗 `/time`、`/date` 或 `/dx123` |
| `/add` | 數字選鍵可收錄；重啓後 spool 仍保留 |
| 剪貼板 | v 長按直接粘貼；b 長按打開剪貼板頁 |
| 深淺色 | 受影響頁的文字和按鍵對比正常 |

## 常見故障

| 現象 | 優先檢查 |
|---|---|
| 修改源主題後毫無變化 | 是否重新生成 `v1.trime.yaml`；手機是否仍選 V1 |
| `force-stop` 後回到 AOSP 鍵盤 | `adb shell ime set com.osfans.trime/.ime.core.TrimeInputMethodService` |
| Trime 崩潰後鍵盤不彈 | 重啓容器清除服務退避，再點輸入框喚起 |
| 深色模式不聯動 | 是否開啓跟隨系統；配色是否選徐碼·雲白 |
| 圖片更新後仍顯示舊圖 | `force-stop` Trime 後重新喚起，清除 bitmap 緩存 |
| 圖片被拉伸 | 圖片長寬比是否與實際鍵位一致 |
| ASCII 頁輸出全角 | 先確認工具欄為半角（彎月），再檢查 `ascii_mode: 1` |
| 長按有角標但選單不可見 | 檢查 `popup_width`、`popup_height`、`popup_key_height` 是否大於零 |
| 中文引號看似不對 | 讀 Unicode 碼位，再檢查字體鏈 |
| 崩潰頁信息被截斷 | `adb logcat -d -s AndroidRuntime:E` |

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
