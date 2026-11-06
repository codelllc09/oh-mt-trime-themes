# 安卓端測試手冊（Waydroid 模擬器＋真機通用）

2026-11-06 首輪容器實測（Android 13／Trime 3.3.13 x86_64／徐碼 36 鍵）沉澱。
以後每次改動主題／lua／部署鏈，按本手冊復跑即可；真機驗收清單見 README.md。

## 一、環境一次性搭建（Waydroid，需 sudo）

```sh
sudo dnf install waydroid scrcpy            # Fedora 官方倉庫
sudo waydroid init -c https://ota.waydro.id/system -v https://ota.waydro.id/vendor
sudo semodule -B && /sbin/load_policy -i    # 修 SELinux：waydroid-selinux 模組
                                            # rpm 腳本環境常裝載失敗（load_policy
                                            # 被 PKG 環境卡死），手動重建即通
sudo systemctl enable --now waydroid-container
```

已知環境坑（各一次性處理）：

| 坑 | 現象 | 對策 |
| --- | --- | --- |
| SELinux 策略未載 | `mount -o context=…` 報 wrong fs type／`security_context_str_to_sid … errno=-22` | `semodule -B`＋`load_policy -i`（見上） |
| 窗口失焦即凍結 | 部署跑到一半停滯、容器內存歸零 | `/var/lib/waydroid/waydroid.cfg` 改 `suspend_action = ignore` 後 restart |
| init 缺 OTA 源 | `You must provide 'System OTA' and 'Vendor OTA' URLs` | 顯式帶 `-c/-v`（見上；Fedora 打包要求） |
| 內存超限 | 編譯進程靜默死（無 oom_kill 記錄） | systemd drop-in `MemoryMax=3G`（本機裁定值；15G 主機守則：<3G 可用時先收縮再測） |

容器內 root 隨時可得：`sudo waydroid shell`（測試一般用不到；adb＋外部存儲＋
Android/data 三條路已夠）。

## 二、每輪測試流程

```sh
# 1. 連容器（會話啓動後 IP 固定 localhost；真機插 USB 免此步）
adb connect localhost:5555
# 2. 推部署清單（主題/補丁同步內部副本——外部存儲模式的 import 不主動拉改動）
TRIME_ADB_SERIAL=localhost:5555 ./deploy.sh push
# 3. app 內部署（MainActivity 工具欄 Deploy；座標用 uiautomator dump 抓）
adb -s <SER> shell am start -n com.osfans.trime/.ui.main.MainActivity
# 4. 等「N tasks ran: N success」（logcat rime.trime）；改詞典時全量編譯數分鐘
# 5. 測試輸入：工具欄 Test input → Type text 聚焦 → 以下矩陣
```

注意：`force-stop` 後 IME 會回落 AOSP 鍵盤——
`adb shell ime set com.osfans.trime/.ime.core.TrimeInputMethodService` 切回
（**服務實名含 ime.core**，舊文檔的 `.TrimeImeService` 已失效）。

## 三、輸入工具 kbmap.py（勿手拼座標）

實測教訓：憑記憶點座標連錯四次（rmmir/umip/tyti/tsye），腳本化後零失誤。

```sh
python3 tools/kbmap.py --serial <SER> --keys            # 列全部映射
python3 tools/kbmap.py --serial <SER> --backspace 6     # 清稿（連點退格）
python3 tools/kbmap.py --serial <SER> --type tigu       # 打碼
python3 tools/kbmap.py --serial <SER> --tap slash       # 功能鍵
python3 tools/kbmap.py --serial <SER> --longpress z     # 長按（≥1200ms 才穩）
```

驗證一律 `adb exec-out screencap -p > x.png` 截圖後讀圖；uiautomator 對
Trime 鍵盤（自繪 View）無效，只對 app 設置頁有效。

**截圖落盤約定**：全部存 `tmp/img/`（倉庫內，忽略區），文件名帶形態與版本：
`豎屏1080p-圓角9-當前最新.png` 式；量化的美学指標報告（aesthetics 輸出）
同步貼進對應 commit 說明。

## 四、功能矩陣 checklist（首輪實測值）

| # | 項 | 操作 | 預期（首輪實錘） |
| --- | --- | --- | --- |
| 1 | 部署 | Deploy | `4 success`；方案列表唯一「徐碼·L」 |
| 2 | 打字 | `--type fbic`＋space | preedit `fbic(亻扌…) 字根映射；上屏∈該碼活條目 |
| 3 | 詞長檔 | /menu→2→1(全詞) | jbyu：12 檔「教諭」→全詞「教書育人」躥首位 |
| 4 | 簡繁檔 | /menu→1→2(汉字) | fdwg：漢字「堅定」→汉字「坚定」上屏對比 |
| 5 | 字符集檔 | /menu→3→2(全部) | sxvs：通用無生僻→全部「㔨(bèi)」+擴展區字躥前 |
| 6 | 非簡檔 | /menu→4 | 單字俗形（们/体）放行＝設計；簡形**詞**已被管道剔除無對比 |
| 7 | 打字註解檔 | /menu→5→2(拼音) | 候選帶「( hè bān )」形拼音注 |
| 8 | 反查註解檔 | /menu→6→選檔 | \`li 註釋檔位變化（機制同 7，未單獨截圖） |
| 9 | 標點檔 | /menu→7→選檔 | ，/．形態（機制同源，未單獨截圖） |
| 10 | 反查 | --longpress z→li | 裏(_wkey) 里(_keej)…16 候選帶徐碼碼注 |
| 11 | 組合反查 | 長按z→li→--tap slash→hs | 李(_ibz) 麗(_gmww)…橫豎過濾 |
| 12 | 全拼反查 | 長按z→pge | 個(_tnjg) 各(_vov)…（小寫 \`p 手機補丁） |
| 13 | 碼位反查 | --longpress u→6c5f | 「江 U+6C5F」＋preedit `U6C5F碼位反查` |
| 14 | /time | /time | 16:44:23／申時(15-17時)／申正二刻 |
| 15 | /date | /date | 七格式＋農曆丙午年(馬)九月廿七 |
| 16 | 金額大寫 | /dx1212 | 壹仟貳佰壹拾貳 |
| 17 | /add 收詞 | 上屏兩字→/add→**數字1** | 橫幅「✓ …已入暫存」計數 0→1；spool 落**內部**目錄 |
| 18 | /add 回採 | adb cat 內部 spool | 內容與收錄一致（pull-spool 時注意路徑在內部） |
| 19 | help | help/ | 功能速查表整排 |
| 20 | 主題/配色 | Themes→徐碼；Colors→徐碼·雲白 | 白鍵大圓角；U 上「碼」；空格自動顯示「徐碼·L」 |
| 21 | 中英分頁 | 中文態 123 / 英文態 123 | 中文→標點頁（，。「」）、英文→數字/符號頁；空格顯示「徐碼·L」／「En」 |
| 22 | 標點頁 | 123 → 標點頁 | 4 行鍵盤式錯開；長按 `[`→`{`、`「`→`『`、`…`→`——`；底行 方案｜#+｜，｜空格｜。｜／｜Enter |
| 23 | 數字/符號頁 | 標點頁 `#+`、長按 `n`、或英文態 123 | 仿 Gboard ?123；32 個 ASCII 標點全在（9 個長按）；底行「標點」回中文標點頁 |
| 26 | 剪貼板 | 長按 `v` | Clipboard 面板，點條目粘貼；長按 `b` 為收藏頁 |

回歸判定：改動後復跑相關行，與首輪實錘值不符即回歸。

## 四之二、2K 驗收（2026-11-06 首輪）

容器切 `wm size 1440x3200; wm density 560` 後跑全流程（截圖 10 張、錄屏 30s）。
錄屏與截圖爲個人產物，存 `tmp/img/`（不入庫）。

| # | 項 | 2K 結果 |
| --- | --- | --- |
| 1 | 主鍵盤（雲白／墨空） | ✅ 佈局完整，無裁切；鍵盤佔屏高 ≈50%（與 1080p 一致） |
| 2 | 打字候選 | ✅ 候選 24sp 清晰，preedit 與候選對齊 |
| 3 | 標點頁 | ✅ 錯開佈局、ABC/⌫ 位置、底行全對齊 |
| 4 | 符號頁（英文態 123 進） | ✅ 32 個 ASCII 標點全在，空格顯示 `En` |
| 5 | 數字頁 | ✅ 5 列加減乘除 + 數學入口 |
| 6 | 數學頁 | ✅ 40 符全部正常渲染 |
| 7 | 剪貼板面板 | ✅ 面板與標題（24sp）比例正常；歷史爲空（見下） |
| 8 | 長按功能鍵 | ✅ 長按 `n`→數字頁、長按 `#+`→符號頁 |
| 9 | 地球圖標 | ✅ 鍵位 2K 下 200×153（比例 1.31）vs 1080p 149×118（1.26），4% 差異肉眼無變形 |

### 2K 輪暴露的兩點

1. **複製快捷鍵在 Android 無效**：用長按 `a`（Ctrl+A）→ 長按 `c`（Ctrl+C）在
   Settings 搜索框不生效，剪貼板因此爲空。屬**測試方法**問題（Android 文本控件
   普遍不認 IME 發的 Ctrl+A/C），非 UI 缺陷。要造剪貼板內容，改用界面長按選中→複製。
2. **`command: clipboard`（v 長按快速粘貼）未能驗證**：剪貼板空，無從判定；
   真機待驗。

## 五、避坑實錄（每坑：現象→根因→對策）

1. **esc 不清組稿**：keyevent 111 對 Trime 組稿無效，後續擊鍵拼接成亂碼
   （「。，\`li」實錄）→ 一律連點退格清稿（--backspace N）。
2. **點擊候選＝上屏**：Trime 走 SelectCandidate API 旁路 lua 按鍵處理器——
   /add、/menu 的選項點了就把菜單文字上屏（實錄：輸入框「成功成功」）→
   **數字行是唯一正確選鍵路徑**（36 鍵保留數字行的根本原因）。
3. **long_click 直寫字符不被 recognizer 認**：主題裏 z 的 long_click 直寫
   '`' 進組稿，pattern `^\`([a-z]…)` 不匹配 → \`li 無候選 → 對策：preset_keys
   `grave_lead: {send: '`'}` 走 keysym 通路（已固化進主題 v2）。
4. **長按模擬時長**：input swipe 同點 <1000ms 常退化爲點擊 → ≥1200ms 穩定
   （kbmap --longpress 默認 1200）。
5. **內部副本滯後**：外部存儲模式的 import 不主動拉主題/補丁改動 →
   deploy.sh push 已對 Android/data 內部副本 best-effort 同步；改主題後
   仍需 app 內 Deploy 一次纔生效。
6. **/add 的「入庫重跑」手機端是降級項**：管道只在桌面倉庫；手機 /add 只
   攢 spool，回桌面 `deploy.sh pull-spool`（注意：spool 在**內部**目錄
   Android/data/com.osfans.trime/files/rime/…，外部目錄那個不增長）。
7. **IME 回落**：force-stop Trime 後鍵盤變 AOSP → `ime set` 切回（見二）。
8. **座標系**：input tap 與 screencap 同座標系（容器 1920x1160 實測一致）；
   換設備/橫豎屏後先 `--keys` 對照實圖重校。

8. **座標系**：input tap 與 screencap 同座標系（同設備同形態下實測一致）；
   換設備/橫豎屏/改 wm size 後**座標全變**，先 `--keys` 對照實圖重校，
   並更新 kbmap.py 座標表（本輪 1080x2280@420 的表已內建）。

## 六、疑難排解（2026-11-06 崩潰調查輪沉澱）

### 環境層（宿主/容器）

| # | 現象 | 根因 | 對策 |
| --- | --- | --- | --- |
| E1 | 宿主 waydroid 進程 CPU 100%、journald 日誌風暴（820 萬條/天）、`Failed to add service … -2147483647`、系統服務時好時壞 | 宿主 SELinux 缺 waydroid 策略，binder IPC 被硬攔無限重試（**半殘環境**） | 宿主裝自定義 SELinux 模組（`~/selinux-custom/waydroid-binder.te/.pp` v1.3）；**半殘期間的測試結論需在新環境復驗** |
| E2 | 容器重啓後 adb 不通、Session STOPPED | session 需重新拉起 | `nohup waydroid show-full-ui &` → 等_SESSION RUNNING_ → `adb connect` |
| E3 | IME 服務反覆崩潰後「鍵盤拉不起來」，`ime set` 報已選但無反應 | Android 對崩潰服務的**懲罰性退避**（第二次崩潰調度延遲可達 200 天量級），force-stop/ime set 都無法重置 | **重啓容器**（`pkexec systemctl restart waydroid-container`）才能清退避計時器 |

### 應用層（Trime 3.3.13）

| # | 現象 | 根因 | 對策 |
| --- | --- | --- | --- |
| A1 | 鍵盤彈出即崩 `IllegalArgumentException: 'text_color' is not a color`（PreeditDelegate <init>） | `ThemeColors.color(key)` 要求 ColorTable.Value.Color；顏色值以 **YAML 不帶引號 int 形態**存在時（0xFF...／十進制，**含官方默認主題自身全部顏色**）被 schemeColors 字符串 map 構建過濾 → parseColor（僅認 #/0x 前綴）失敗 → Value.None → 崩 | **全部顏色值寫帶引號字符串 `'#RRGGBB'/'#AARRGGBB'`**；自包含主題已全量字符串化（394 值）並入部署清單（現為 `v1.trime.yaml`） |
| A2 | 配色缺 `text_color` 鍵也觸發 A1 | PreeditDelegate 讀 TEXT_COLOR 是**必須鍵**；fallback 鏈覆蓋不到它 | 兩套配色均已補 text_color/text_back_color；check_trime.py 已加必須鍵檢查 |
| A3 | `pm clear` 後連鎖清空：SAF 目錄授權、launcher alias 開關、Setup 完成標記、內部 rime 目錄、IME 選擇全滅 | Android pm clear 語義（含 prefs/授權/內部數據） | clear 後必須重走：Setup 嚮導（SKIP 可）→ 存儲模式＋SAF（或改 app-specific 模式繞開 SAF）→ deploy push（重建內部目錄）→ ime set；**或改用 app-specific 模式（內部路徑 adb 可直寫，無 SAF 依賴——推薦測試環境）** |
| A4 | `Rime.startRime: Permission denied` → `System.exit called, status: 10` 循環 | SAF 授權丟失後 Trime 讀 /rime 失敗，daemon 啓動失敗主動 exit(10) 要求重啓 | 重授 SAF；或按 A3 改 app-specific 模式 |
| A5 | launcher 圖標消失、monkey LAUNCHER 無法啓動 app | pm clear 重置「Show app icon in launcher」開關 | `am start -n com.osfans.trime/.ui.main.MainActivity` 直啓不受影響 |
| A6 | `ime set` 報成功但鍵盤不彈 | 服務處於崩潰退避期（E3）或 showSoftInput 未觸發 | 先重啓容器清退避；再點輸入框觸發 showSoftInput |
| A7 | 系統 night 模式開、App UI 也變暗，**鍵盤始終不切深色** | 兩個條件缺一：①Keyboard Style →「Follow system day/night color」須開（預設關）；② Colors 須選**徐碼·雲白**（新建/clear 後預設是「預設／default」，與本主題無關，自然不聯動） | 兩者都設好即生效，且已驗證**再彈鍵盤即切**（不需重啓）。選配色：Keyboard Style → Colors → 列表底部「徐碼·雲白」 |
| A8 | 改了 `xuma_L.trime.yaml`、部署也成功，但鍵盤毫無變化 | 真機激活的是**自包含生成物**（現為 `v1.trime.yaml`）；它曾是手工生成的，不會跟隨 xuma_L 更新 | 已收斂：`python3 tools/check_trime.py gen-theme` 生成；校驗器已加漂移檢查（改主題不重生成即敗） |
| A9 | 鍵位顏色寫死 → 切配色時底行仍舊淺（墨空下空格白底、「徐碼·L」看不清） | 鍵盤定義裏 `key_back_color: '#FFF1F3F6'` 這類**硬編碼色值不隨配色變** | 鍵位顏色引用**配色語義色名**（`space_back_color`/`fn_back_color`/`lang_back_color`/`accent_fill`），兩套配色各自定義；驗證方法：截圖取像素點比對配色定義值 |
| A10 | `gen-theme` 生成的自包含主題一用就崩（尺寸全錯） | 顏色字符串化步驟誤對**全文**整數生效（`key_height: 38` → `'#000026'`） | 只對 `preset_color_schemes` 子樹做字符串化；生成後宜用舊檔做語義 diff，確認差異僅限預期項 |

### 導航層（UI 自動化）

| # | 現象 | 對策 |
| --- | --- | --- |
| N1 | 豎屏下 Test input 面板位置不穩定（主頁滾動區／工具欄 ⋮ 菜單兩處漂移） | dump 抓 `text="Type text"` 座標；找不到時 tap ⋮ 從菜單進；**⚠ ⋮ 菜單第一項是 Crash logs，座標勿落錯** |
| N2 | Settings 搜索頁殘留前臺，am start 被蓋 | keyevent 3（HOME）回桌面再 am start |
| N3 | MainActivity 啓動即跳 Setup 3 | 默認 IME 非 Trime 時的強制攔截；**選 Trime 前先確保存儲/主題就緒**，否則觸發 A4 崩循環——正確順序：SKIP 完成 → 存儲/SAF → 部署 → 最後 ime set Trime |
| N4 | dark 聯動驗證卡服務退避 | 容器重啓後（退避清零）直接在窗口點輸入框觀察；night 模式下墨空應自動生效 |
| N5 | Crash logs 頁截圖會裁掉異常消息行尾 | 完整棄棄用 `adb logcat -d -s AndroidRuntime:E`；r8 混淆行號不可信，以類名+方法名對源碼；ThemeDiagnostics 頁只報 unknown key，**不報 color 解析失敗**（A1 需 logcat） |
| N6 | 逐頁 dump 導航坐標會漂（同一項在滾動後 y 變） | 每步先 `uiautomator dump` 取 `text="…"` 座標再 tap；**切勿憑上次截圖的像素位坐** |
| A11 | 換了鍵位圖標 PNG，部署成功但鍵上還是舊圖 | ①內部副本缺 `backgrounds/`（import 只同步 yaml）；②Trime 對鍵背景圖有 **bitmap 緩存**，同進程不重載 | ①`deploy.sh push` 已補 backgrounds 同步；②換圖後 `am force-stop com.osfans.trime` → `ime set …` 再拉起 |
| A12 | 圖片型鍵背景顯示成橢圓/變形 | 圖檔長寬比 ≠ 鍵位實際長寬比（拉伸繪製）。1080p@420 實測鍵位 149×118 px（1.27），2K 同比例 | 按實測長寬比出圖；改鍵高/寬後須重算（`gen_icons.py` 的 ASPECT） |
| N7 | `sudo waydroid shell` 提示需密碼、`adb root` 不可用、`run-as` 報 `setegid failed` | Waydroid 不提供 adb root；sudo 需 TTY | 不依賴 root：數據走 `/sdcard` 外部目錄（adb 可寫）；確需 root 用 `pkexec`（會彈宿主圖形密碼框） |

### 主題 token 的隱性耦合（改值前先查）

| token | 除了鍵盤還影響什麼 | 源碼 |
| --- | --- | --- |
| `candidate_text_size` | **剪貼板/收藏頁的標籤標題字號** | `ClipboardWindow.kt:221` `textSize = theme.style.candidateTextSize` |
| `candidate_view_height` + `comment_height` | 剪貼板標題欄高度 | `ClipboardTitleUi.kt` `size = candidateViewHeight + commentHeight` |
| `round_corner` / `key_border` | 剪貼板卡片圓角與邊框 | `ClipboardBeanUi.kt` `decorDrawable(...)` |

2026-11-06 實例：候選字放大到 30sp 時，剪貼板標題「Clipboard Collection」
被同步放大到撐滿屏寬；調回 24sp 後標題正常、候選仍夠大。

### 剪貼板（F3）驗收流程

1. `Settings → Applications → Trime → Clipboard` 確認 **Clipboard listening** 開（默認開，
   歷史上限 10、「Return after pasting」開）；
2. 在輸入框打一段文字 → 長按 `a`（全選）→ 長按 `c`（複製）；
3. 長按 `b` → 彈出 `Clipboard Collection`，條目應含剛複製的文字；
4. 點條目 → 粘貼並自動返回鍵盤；
5. `am force-stop com.osfans.trime` → 重新拉起鍵盤 → 再開面板，**歷史應仍在**
   （2026-11-06 實測通過）。

### 崩潰調查方法論（本輪有效手段）

1. `adb logcat -d -s AndroidRuntime:E`——完整 FATAL 棧（Crash logs 頁截圖會裁行）；
2. r8 混淆行號不可信（`r8-map-id` 假行號），以**類名+方法名**對源碼；
3. 容器 root：`sudo waydroid shell` 可讀 /data/data（Trime prefs），adb shell 不行；
4. 崩潰對話框會反覆攔截 UI 自動化——先 `input tap` OK 座標關掉再導航；
5. 每輪改動後：check_trime（含 text_color 必須鍵）→ deploy push → Deploy →
   logcat 判據 → 截圖落 tmp/img/。

## 七、未覆蓋（真機剩餘項）

`b 筆畫反查（機制與 `p 同源已證）、標點檔位截圖、夜墨配色目驗、
長時間穩定性、ARM 真機性能、藍牙實體鍵盤場景。

## 附：標點「到底是不是真的」——碼位驗證法（2026-11-06）

用戶質疑「鍵盤打不出中文引號」。眼睛看字形不能下結論（`“` 與 `"` 在不同字體下差別細微），必須讀碼位。可複現流程：

1. `adb shell am start -a android.settings.SETTINGS`，點搜索框取得焦點；
2. 切到要驗的鍵盤頁，依次點鍵；
3. `adb shell uiautomator dump /sdcard/ui.xml`，`adb exec-out cat` 取回；
4. 解析出 `android:id/search_src_text` 節點的 `text`，逐字印 `U+XXXX` 與 Unicode 名稱。

要點（踩過的坑）：

- Settings 搜索框的輸入控件是 **`AutoCompleteTextView`**，不是 `EditText`；按 `class=EditText` 找會落空。
- 內容含 `"` 時該 `text` 屬性會改成**單引號包裹**，`'` 變成 `&apos;` 實體——
  必須用 XML 解析（或 `html.unescape`），不能用正則硬切。
- 按鍵座標會因頁面而異（CJK 頁只有四行，ABC 在行 3），點錯位置會得到「什麼都沒發生」的假象。

### 2026-11-06 實測結果

| 來源 | 上屏 | 碼位 |
|---|---|---|
| 中文符號頁 `「」『』` | 直角引號 | U+300C U+300D U+300E U+300F |
| 中文符號頁 `“”` | 彎引號 | **U+201C U+201D** |
| `“`／`”` 長按 | 單引號 | **U+2018 U+2019** |
| ASCII 頁 `"` `'` | 直引號 | **U+0022 U+0027** |

結論：中文引號打得出來，且雙通道——`「」『』`（直角）與 `“”`（彎的，即 GB/T 15834 的雙引號，
與英文 curly quote 同碼位，差別在字體寬窄）。

### 兩個靜默陷阱（已機化爲校驗）

1. **`ascii_mode: -1` 等於中文態。** `Keyboard.kt:83` 是 `ascii_mode == 1` 取布爾，
   `-1` 得到 `false`＝中文。於是符號頁一邊自稱 ASCII，一邊讓 Rime 的 punctuator
   把 `, . " ' : ; ? !` 全換成全角形（實測 `,`→`，`、`"`→`“`）。
   修法：頁面顯式寫 `ascii_mode` + `reset_ascii_mode`；`check_trime.py` ⑦ 強制。
2. **行內 `commit:` 無效。** `KeyAction.kt:181-192`：Plain 鍵（`click: 'x'`）的 `commit`
   只從 `preset_keys` 取，寫在鍵上會被忽略。要字面上屏須用嵌套形式
   `{click: {commit: 'x', label: 'x'}}` 或定義 preset。
   **所以「ASCII 頁仍出中文標點」不是 commit 沒寫對，而是語言態被拉成中文**——
   別再往 commit 方向修。

最終形態：ASCII 頁 `ascii_mode: 1` + `reset_ascii_mode: true`（進頁即英文，標點必爲字面 ASCII）；
中文頁 `ascii_mode: 0` + `reset_ascii_mode: true`；主鍵盤 `reset_ascii_mode: false`（記住上次語言）。

### 標點翻譯邊界（2026-11-06 實測）

主鍵盤標點鍵 = ASCII 字面 → 經 Rime `punctuator` 換形；符號頁 = 字符即輸出。

| 按鍵 | 中文態 | 英文態 |
|---|---|---|
| 主鍵盤 `\` | 、（列表型：出候選，空格確認）U+3001 | `\` U+005C |
| 主鍵盤 `;` `:` `?` `!` | ；U+FF1B ：U+FF1A ？U+FF1F ！U+FF01 | 原樣 U+003B/003A/003F/0021 |
| 主鍵盤 `'` `"` | ‘’U+2018/2019（配對交替）、”“U+201C/201D | 原樣 U+0027/0022 |
| 主鍵盤 `(` `)` | （U+FF08 ）U+FF09 | 原樣 |
| 主鍵盤底行 `,` `.` `/` | ，U+FF0C 。U+3002 、（列表型） | 原樣 |
| ASCII 頁 `,` `.` `"` `'` | 不翻譯，U+002C/002E/0022/0027 | 同左 |
| 中文頁 `，` `。` `“”` `「」` | 原樣 U+FF0C/U+3002/U+201C…/U+300C… | 同左 |

語言態往返實測：中文主鍵盤 → `12#`（CJK 頁）→ 地球（ASCII 頁）→ 地球（CJK 頁）→ `ABC` 回主鍵盤，
空格仍顯示 `徐碼·L`＝語言未被符號頁帶偏。

### 主鍵盤 4 行長按表實測（2026-11-06）

| 按鍵 | 中文態 | 英文態 |
|---|---|---|
| `,` 點／長按 | ，U+FF0C ／ ；U+FF1B | , ／ ; |
| `.` 點／長按 | 。U+3002 ／ ！U+FF01 | . ／ ! |
| `/` 點／長按 | 、U+3001 ／ ？U+FF1F | / U+002F ／ ? |
| `n` 長按 | ：U+FF1A | : |
| `m` 長按（連按） | “ U+201C → ” U+201D | " |
| `l` 長按（連按） | ‘ U+2018 → ’ U+2019 | ' |
| `o`／`p` 長按 | （U+FF08 ／ ）U+FF09 | ( ／ ) |
| `w`／`e` 長按 | ——U+2014×2 ／ ……U+2026×2 | _ ／ ^ |

注意：**Shift 鎖定時底行顯示上檔字符**（`,→<` `.→>` `/~?`），這是 Trime 的正常行爲，
不是標籤錯誤；按一下 Shift 解鎖即恢復。

### 數字鍵盤頁（2026-11-06）

| 按鍵 | 點 | 長按 |
|---|---|---|
| `()` `[]` `{}` | 一次出一對且光標在內（打 `x` 得 `(x)`） | `(` → `<` U+003C、`[` → `>` U+003E |
| `7 9` / `5` / `1 3` / `0` | 字符本身 | — |
| `8` `2` `4` `6` | 8 ／ 2 ／ 4 ／ 6 | 方向鍵 ↑ ↓ ← →（移動光標，非字符）|
| `.` / `=` | . ／ = | `,` U+002C ／ `≠` U+2260 |
| `*` / `+` | * ／ + | `#` U+0023 ／ `@` U+0040 |
| `/` `*` `+` `-` `⌫` | 字符本身 | — |
| 底行 | ABC 回主鍵盤 ／ ASC → ASCII 符號頁 ／ CJK → 中文標點頁 ／ 空格 ／ Enter | — |

本頁 `ascii_mode: 1`，所有字符原樣輸出，不受中英狀態影響。

### 教訓：主題內重複鍵 = 改動被靜默吞掉（2026-11-06）

`number_zh` 曾在 `xuma_L.trime.yaml` 裏定義兩次。YAML 的規則是最後一份生效，
於是所有對第一份的修改（頁面重排、引號上移）都**看似改完、實際無效**，
連續幾輪「改了卻沒變化」都源於此。

`check_trime.py` 已加第 ⑧ 項校驗：掃描原始行文，同一 section 下同名鍵出現兩次即敗。
（本項上線即抓到 `preset_keys/Return1` 也是重複定義，已合併。）

另：鍵盤字體 `symbol.ttf` 的 `“”‘’` 是拉丁字形（小、靠上）。CJK 字體才有大方引號，
但 Trime 每頁只用一套 key_font，故只能靠 `key_text_size: 40` 放大緩解。

### 鍵盤字體（2026-11-06）

vendor 默認 `key_font: symbol.ttf`。它把 `“”‘’` 畫成**拉丁字形**（小、貼字身上緣），
中文使用者會認爲「這不是引號」或「看不到引號」——這正是本輪反覆的根源。

處置：改用自帶 CJK 子集字體 `fonts/xuma_key.otf`
（Noto Sans CJK SC 抽取 182 個鍵盤用字，111KB；缺的 8 個功能符號由系統回退）。
部署路徑：`rime/fonts/xuma_key.otf`（Trime 的 `ThemeFonts.fontDir` 讀 `userDataDir/fonts`）。

驗收要點：換字體後必須逐頁看一遍——字母、數字、CJK 標點、功能鍵符號
（`⌫ ⬚ ✂ ⧉ ⤒ ▤ ☰ ◑ ↑↓←→`）都要能正常顯示，缺字會變豆腐塊。

### 鍵盤字體子集：字重陷阱（2026-11-06）

第一版子集取自 `NotoSansCJK-VF.ttc`（可變字體），整把鍵盤卻是**細體**——
可變字體的默認實例是 `wght=100`（Thin）。一條命令自查：

    uv run --with fonttools python -c "from fontTools.ttLib import TTFont; print(TTFont('fonts/xuma_key.otf')['OS/2'].usWeightClass)"

改取靜態 `NotoSansCJKsc-Regular.otf`（400）後恢復正常，體積由 111KB 降到 70KB。
中文一致性：與換字體前的截圖逐像素比對，CJK 標點區域亮度差 ≤12 的像素佔 95.7%
（差異來自抗鋸齒），可視爲同一字形。

### 長按提示的可見性控制（2026-11-06）

Trime 把 `long_click` 指向的 preset 的 `label` 畫成鍵面提示。要「保留功能但不要提示」，
把該 preset 的 `label` 設成 `' '`（渲染空白，`hint.isNotEmpty()` 仍成立，不會報錯）：

- `unicode_lead`（u 長按＝碼位反查）→ `label: ' '`，u 鍵不再顯示 `U`
- `arrow_up/down/left/right`（數字鍵盤 2/4/6/8）→ `label: ' '`，鍵面不再顯示箭頭
- `tab_key`（t 長按）→ `label: Tab`，操作類提示保留

`send: Tab` 的有效性：`codegen/GenKeyMapping.kt:181` 有 `"Tab" to 0xff09 to "KEYCODE_TAB"`，
故能解析到 KEYCODE_TAB。容器內沒有可觀察 Tab 效果的編輯器/多行輸入框，
**真機上用多行文本框或表單焦點移動複驗**（本輪未驗證）。

### undo／redo（q／r 長按，2026-11-06）

- 綁定：`q → undo`（`undo: {label: 撤, send: Control+z}`）、`r → redo`
  （`redo: {label: 復, send: Control+y}`），均爲 Trime 官方 preset。
- 容器內驗證受限：Waydroid 的 Settings 搜索框（`AutoCompleteTextView`）不響應
  `Ctrl+Z`（多數 Android 文本控件只認 IME 的 undo 通道或實體鍵盤），故**無法自動斷言**。
- 已觀察到的事實：長按發送後 IME 無崩潰、logcat 無錯誤、組稿與上屏流程不受影響。
- **真機複驗方法**：在任意多行輸入框（短信、備忘錄）打幾個字 → 長按 `q` 應逐字回退；
  撤銷後長按 `r` 應恢復。
- 歷史包袱：Ctrl+A／Ctrl+C 在 Waydroid 同樣無效（見前文 E 節），同一原因。

## 全流程自動驗證：`tools/verify.sh`

```sh
TRIME_ADB_SERIAL=localhost:5555 ./tools/verify.sh
```

逐項打勾、失敗即非零退出。覆蓋：

| 段 | 內容 |
|---|---|
| 0 | 前置：搜索框聚焦、鍵盤彈出、歸位主鍵盤 |
| 1 | 頁面導航：12# → 數字 → ASC/CJK → 123/ABC |
| 2 | 翻譯邊界：中文態 `,` `.` `/` 分別出 `，` `。` `、` |
| 3 | 主鍵盤長按全表（第一排 1–0、g/h ( )、j/k …… ——、l ‘、n ：、m “、底行 ；！？）|
| 4 | 功能鍵長按後 IME 存活（a Tab／s 全選／d 撤銷／f 恢復／z/x/c/v）|
| 5 | 數字鍵盤：數字、括號成對且光標在內、長按 `< > # ≠` |
| 6 | ASCII 符號頁不翻譯（`"` 與長按 `＂`、`,`）|
| 7 | 中文標點頁不翻譯（`，`、`”`）|
| 8 | 剪貼板面板可喚出 |

**判據一律為碼位**（`uiautomator` 讀 `search_src_text` 的 text），不看字形。
**未涵蓋**：undo/redo 的實際效果（容器 Settings 搜索框不響應 IME 的 Ctrl+Z）、
Tab 的可見效果（無多行輸入框）、Ctrl+A/C/V（同類限制）——需真機複驗。

### 2026-11-06 全流程驗證結果（容器 1080×2280@420）

```
PASS 55 ／ FAIL 2
失敗 2 項經複驗確認是**腳本座標寫錯**，鍵盤本身正確：
  · ASCII 頁 `,`：腳本點到 x=324（落在空格鍵）→ 改點 x=216，實測 `,` U+002C ✓
  · 中文頁 `”`：腳本點到 x=756（那是 `“`）→ 改點 x=918，實測 `”` U+201D ✓
兩處已在 verify.sh 修正，並單項複跑通過。
```

**未涵蓋（需真機）**：undo/redo 的實際效果、Tab 的可見效果、Ctrl+A/C/V。
容器 Settings 搜索框不響應 IME 送出的這些組合鍵，只驗證了「發送後 IME 存活、無崩潰」。

### 主題 configId 改為 `v1`（2026-11-06）

內建默認主題的檔名/ configId 是 `trime`（顯示名「預設」），而主題**按 configId 加載、
用戶目錄優先**。此前我們把自包含主題也命名 `trime.yaml`，導致菜單裏「預設」與
「徐碼·L」指向同一份檔案、長得一模一樣。

現改為獨立檔名 `v1.trime.yaml`（`name: V1`），三支主題各歸各：

| 清單項 | configId | 來源 |
|---|---|---|
| 标准 | tongwenfeng | APK 內建 |
| 預設 | trime | APK 內建（默認） |
| V1 | v1 | 本倉 `v1.trime.yaml` |

**代價**：`pm clear`／首裝後默認是「預設」，需手動「地球長按 → 主題選單 → V1」切一次。
`shots.sh` 已加前置檢查：裝置上沒有 `v1.trime.yaml` 就拒拍，避免整批截圖拍成內建主題。

## verify.sh 的效能取捨（2026-11-07 重寫，實測 9 分鐘 → 117 秒）

先量再改，本機實測各操作成本：

| 操作 | 耗時 | 備註 |
|---|---|---|
| `uiautomator dump` | **1928 ms** | 唯一的大頭，一次 dump 就是 2 秒 |
| `exec-out screencap` | 179 ms | |
| `page_kind.py`（本機解析） | 81 ms | |
| `dumpsys input_method` | 12 ms | 查 IME 存活／鍵盤是否彈出用它，別用截圖 |
| `input tap` | 15 ms | |

優化手段（覆蓋不變）：

1. **連打 → 讀一次**：長按全表 20 項原本逐項 `wipe + dump`，
   改成連打一串再一次讀（`1234567890`、`（）……——‘：“；！？`），dump 次數 20 → 2；
2. **wipe 不再 dump 確認**：盲發 DEL；但**必須先 `keyevent 123`（MOVE_END）再 DEL**——
   上一步若輸出成對括號 `()`，光標停在括號內，DEL 只刪左側，殘留會黏在後面（實測得到 `(7))`）；
3. **固定 sleep 減半**：tap 1.2 s → 0.5 s、hold 1.8 s → 1.3 s（長按手勢本身已 1200 ms）；
4. **刪重複**：第 0 段原本把第 1 段的導航又跑一遍；第 5 段那次 `reset_ime + focus` 也無必要。

代價與注意：

- `dumpsys input_method` 的 `mInputShown=true` **可能是陳舊的**（實測鍵盤已隱藏它仍報 true），
  所以「鍵盤是否真的在」這種判斷仍以截圖為準；
- 失敗訊息給的是**合併字串**（例如期望 `(7)` 實測 `(7))`），定位時看尾巴即可；
- `/` 鍵在中文態送 ASCII `/` → 出候選 `、/／÷`，**要再按一次空格**才上屏 `、`，
  腳本第 2 段已把這一步算進去（用戶裁定的「老樣子兩步」）。

用法：

```sh
./tools/verify.sh                # 全程（約 2 分鐘）
./tools/verify.sh --section 3    # 只跑長按全表
./tools/verify.sh --no-clip      # 跳過剪貼板段
```

