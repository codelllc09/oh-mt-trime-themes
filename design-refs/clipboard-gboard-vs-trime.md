# 剪貼板 UI：Gboard vs Trime（2026-11-06 研究與取捨）

## Gboard 的剪貼板

| 要素 | 做法 |
| --- | --- |
| 入口 | 工具欄常駐剪貼板圖標（四宮格裏可拖到工具欄常顯） |
| 面板 | 替代鍵盤區的 bottom sheet，垂直卡片列表 |
| 單條卡片 | 文本預覽（截斷）＋右下角圖釘；長按或編輯圖標出「編輯／置頂／刪除」 |
| 過期策略 | 未置頂 **1 小時後自動刪除**，置頂永久保留 |
| 空狀態 | 引導文案「Welcome to Gboard clipboard, any text you copy will be saved here…」 |
| 頂部操作 | 一鍵全部清除 |

來源：Google Gboard 幫助頁、Android Central 教程、多篇實機測評；官方空狀態文案
「Tap on a clip to paste it… use the edit icon to pin, add or delete clips…」在多處轉載。

## Trime 的剪貼板窗口（源碼事實）

`app/src/main/java/com/osfans/trime/ime/clipboard/`（710 行**應用層代碼**，非主題配置）：

| 要素 | 實現 |
| --- | --- |
| 入口 | 按鍵命令 `clipboard_window`，`option` 爲標籤頁序號（`CommonKeyboardActionListener.kt:222`）|
| 標籤頁 | 0 = 剪貼板、1 = 收藏（`ClipboardWindow(di, initialTab)`）|
| 卡片外觀 | `decorDrawable("key_back_color", "key_border_color", dp(style.keyBorder), dp(style.roundCorner))` |
| 正文色 | `key_text_color`；圖釘 `key_symbol_color`（30% alpha）|
| 交互 | 點擊粘貼；長按彈 PopupMenu（編輯／置頂／取消置頂／刪除）；標題欄全清 |
| 過期策略 | **條數上限**（默認 10），非時間 |

## 結論：能照抄的與抄不了的

| Gboard 特性 | Trime | 說明 |
| --- | --- | --- |
| 卡片列表、點擊粘貼 | ✅ | 結構一致 |
| 置頂 / 編輯 / 刪除 / 全清 | ✅ | 藏在長按菜單裏（Gboard 是內聯圖標）|
| 空狀態（無內容時） | ⚠ | Trime 顯示 `No results`，無引導文案（字符串硬編碼）|
| 卡片內聯操作圖標 | ❌ | 佈局寫死在 adapter，主題改不了 |
| 未置頂 1 小時過期 | ❌ | Trime 只有條數上限 |
| 空狀態引導文案 | ❌ | 同上 |

主題側唯一能影響的是**顏色與圓角**——而這部分已經自動繼承（卡片底色 `key_back_color`、
邊框 `key_border_color`、圓角 `style.round_corner = 9`、正文 `key_text_color`），
所以 light/dark 下觀感與鍵盤一致。

## 本倉最終取捨

- 入口雙通道（語義貼合）：
  - 長按 **`v`**（粘貼鍵）→ 剪貼板頁（`option: 0`）
  - 長按 **`b`** → 收藏頁（`option: 1`）
- 不追求克隆 Gboard 的內聯操作圖標——那需要改 Trime 源碼，超出主題能力；
  長按菜單已覆蓋同等功能，且與鍵盤「長按出功能」的既有心智一致。
- 已知缺口（記錄備查）：無空狀態引導文案；無時間過期。
