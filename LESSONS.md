# LESSONS —— 同文（Trime）移植過程中踩過的坑與方法論

> 本檔只收**可複用的教訓**（現象 → 根因 → 對策 → 防再犯機制）。
> 版式與鍵位規則見 `KEYBOARD_MAP.md`；實測矩陣與驗收流程見 `TESTING.md`。
> 每條都附「憑證」（命令、檔案行號或實測數據），沒有憑證的經驗不收。

## A. YAML / 主題層

### A1. 同一個鍵定義兩次＝改動被靜默吞掉
- **現象**：頁面怎麼改都沒變化，連續幾輪「改了卻無效」。
- **根因**：`number_zh` 在 `xuma_L.trime.yaml` 裏出現了兩次，YAML 取**最後一處**，
  前面的定義（我一直在改的那份）是死副本。
- **對策**：刪重複塊，保留生效的那份。
- **防再犯**：`check_trime.py` 第 ⑧ 項「主題內無重複鍵定義」——掃原始行文，
  同 section 同名鍵出現兩次即敗（上線當場又抓到 `preset_keys/Return1` 重複）。

### A2. 鍵入替換未命中＝改動悄悄丟失
- **現象**：把 q/r 的長按搬到 d/f 後，d/f 上什麼都沒有。
- **根因**：腳本用 `- {click: d, long_click: '^'}` 去匹配，但文件裏當時是
  `- {click: d}`（長按早被清掉）→ 替換零命中，`long_click` 根本沒寫進去。
- **對策**：改完**立刻解析 YAML 打印實際鍵位表**核對，不只看 grep 有沒有輸出。
- **防再犯**：`check_trime.py` 的「長按表」與頁面行寬校驗；每次改完必跑。

### A3. `ascii_mode: -1` 等於「中文」
- **現象**：符號頁自稱 ASCII，打 `,` 卻出 `，`、`"` 出 `“`。
- **根因**：Trime `Keyboard.kt:83` 是 `ascii_mode == 1` 取布爾，`-1` 得 `false`＝中文；
  Rime 的 punctuator 遂把 ASCII 標點換成全角。
- **對策**：頁面顯式寫 `ascii_mode`(0/1) + `reset_ascii_mode`。
- **防再犯**：`check_trime.py` 第 ⑦ 項強制「語言態顯式聲明」。

## B. Trime 鍵位機制

### B1. 只有 preset 的 `label` 會變成鍵面提示；`hint` 欄位被字根校驗佔用
- **現象**：想給 d/f 顯示「撤銷」「恢復」，寫 `hint:` 卻被門禁擋（`d:撤≠尸`）。
- **根因**：`long_click` 指向 preset 時，鍵面提示畫的是 **preset 的 label**；
  `hint` 欄位另有用途（歷史上是字根提示，校驗器要求與方案 xlit 一致）。
- **對策**：改 preset 的 label（`undo: {label: 撤銷, send: Control+z}`）即可，
  不必碰 `hint`。
- **憑證**：`KeyView.drawSymbol` 讀 `key.hint`；`Keyboard.kt` 解析 long_click 的 label。

### B2. Plain 鍵上的 `commit:` 無效
- **現象**：給 ASCII 頁的 `,` 加 `commit: ','` 想繞過 Rime，實測無效。
- **根因**：`KeyAction.kt:181-192`——Plain 鍵（`click: 'x'`）的 `commit` 只從
  `preset_keys` 取，寫在鍵上被忽略；要用 Inline 形式
  `{click: {commit: ',', label: ','}}` 或 preset。
- **憑證**：同檔 `KeyActionToken.Inline` 分支。

### B3. `send:` 必須存在，`select:` 才生效
- **現象**：把符號頁地球鍵的 `send: Eisu_toggle` 拿掉後，切頁徹底失效。
- **根因**：`CommonKeyboardActionListener.kt:140` 只在 `KEYCODE_EISU` 分支裏
  `switchKeyboard(action.select)`；沒有 `send: Eisu_toggle` 就不會執行 select。

### B4. Rime 的「列表型」標點會彈候選
- `punctuation.yaml` 中 `/ \ [ ] { } < >` 是列表（`[、, /, ／, ÷]` 這類），
  按一次出候選、要空格或點選確認；`,` `.` `;` `:` `?` `!` `(` `)` 是單值，直上屏。
- **對策**：需要「一鍵直出」的鍵可用 `ascii:` 分支寫死
  `{click: {commit: '、', label: '/'}, ascii: '/'}`。
- ⚠ **但別對 `/` 這麼做**：一旦 `/` 直出 `、`，中文態就打不出 `/`，而 `/menu`
  `/add` `/time` 這些 lua 命令必須靠 `/` 進組稿緩衝；英文態雖能打出 `/`，
  但 ascii 模式不走 processor，同樣進不了命令。實測後已改回送 ASCII `/`
  （代價是打 `、` 要再按一次空格／點候選）。

### B5. 鍵面提示要留空時
- 把 preset 的 `label` 設成 `' '`（不是空串）——`hint.isNotEmpty()` 仍成立，
  渲染爲空白，功能照舊。用於「u 不顯示 U」「2/4/6/8 不顯示箭頭」。

## C. 字體

### C1. Trime 不自帶文字字體
- APK 內只有 `res/9B.ttf`＝Material Design Icons（7,138 字形，純圖標）。
- 主題裏 `symbol.ttf` / `han.ttf` / `comment.ttf` 只是**文件名約定**，
  `ThemeFonts.makeFileStateList` 會 `filter { it.isFile }`——找不到就跳過，
  全缺時 `Typeface.DEFAULT`＝系統字體。
- **因此**：「引號看着像拉丁引號」的真因是**系統字體**（Roboto 提供 U+201C），
  不是 symbol.ttf。

### C2. 可變字體的默認實例是 Thin
- 直接子集 `NotoSansCJK-VF.ttc` → `usWeightClass=100`，整把鍵盤偏細。
- **對策**：用靜態 Regular（400），或先 `varLib.instancer` 固定 `wght=400`。
- **自查**：`TTFont(path)['OS/2'].usWeightClass`。

### C3. 跨字體合併會撞可變字體表
- `fontTools.merge` 在 `VarStore` 上報 `no attribute 'mergeMap'`。
- **對策**：不合并，用 Trime 的字體鏈 `latin_font + key_font + hanb_font`（前優先）：
  `latin_font`＝Roboto 子集（**剔除 `“”‘’`**）、`key_font`＝Noto Sans CJK 子集
  → 拉丁回歸 Roboto、引號仍是中文寬形、缺字走 `setSystemFallback("sans-serif")`。

## D. 圖標與量測

### D1. 圖片會被拉伸填滿鍵位
- **現象**：地球圖標發扁（實測 0.928，正圓應 1.0）。
- **根因**：`key_back_color` 的 .png 被拉伸到鍵位尺寸；
  圖檔長寬比必須等於**鍵位實測**比例。按「15 單位 × 108px = 162」推算的 1.27/1.11 都不對，
  逐像素量得鍵位 **150×146**（≈1.03）。
- **對策**：`gen_icons.py` 的 `ASPECT` 用實測值；改版式後重量。
- **驗收**：截圖裏量圖標墨跡 bbox 的寬高比，須在 1.00±0.05。

### D2. 全形標點墨跡不在字身正中
- 左括號偏右、右括號偏左、句讀偏下——Trime 不自動光學居中。
- **對策**：逐鍵 `key_text_offset_x/y`；用 `tools/glyph_offsets.py` 量測
  （按鍵面底色取眾數 → 求墨跡包圍盒 → 換算 sp），殘差 ≤1px。

## E. 驗證方法論

### E1. 一律讀碼位，不看字形
- 眼睛判斷不了 `“`（U+201C）與 `"`（U+0022）、全角 `（）` 與半角 `()`。
- **方法**：`uiautomator dump` → 讀 `resource-id="android:id/search_src_text"` 的
  `text` → `U+XXXX`。注意：控件是 `AutoCompleteTextView`（不是 `EditText`）；
  內容含 `"` 時屬性改用單引號包裹、`'` 變 `&apos;`，必須按 XML 解析。

### E2. 裝置狀態可能與倉庫脫節
- **現象**：改完主題「沒生效」——裝置的主題選單停在「預設」，倉庫改的是「徐碼·L」。
- **對策**：每輪驗證前先確認 ① 主題選中項 ② `rime/build/trime.yaml` 時間戳
  ③ `shots.sh` 重跑時間 ≥ 最後一次提交時間。
- **防再犯**：`verify.sh` 前置用 `page_kind` 斷言起點是主鍵盤；截圖腳本跑完打印張數。

### E3. 硬編碼座標會漂
- 驗證腳本直接用 `(376,605)` 點搜索框，換過佈局後就點到別處，後面全紅。
- **對策**：用 `uiautomator` 找 "Search settings" 節點算中心；
  鍵位座標一律由「行/欄 × 鍵寬」推導，並在註釋寫明推導式。

### E4. 清空字段要循環確認
- 一次發 8 個退格常常沒清乾淨，殘留字符會污染後續斷言（`<))` 這種）。
- **對策**：`wipe()` 循環「讀字段→若空則返回→否則發退格」，最多 8 輪。

## E6 · 「先量再改」：驗證腳本的 90% 時間花在一個操作上

**現象**：`verify.sh` 跑一次要 9 分鐘，沒人願意在每次改動後跑。

**根因**：腳本里有 ~90 次 `uiautomator dump`，每次 1.93 秒；而其他所有操作
（tap 15 ms、screencap 179 ms、dumpsys 12 ms）加起來不值一提。
憑直覺會去砍 `sleep`，其實砍 dump 次數才有用。

**對策**：先寫個小腳本逐項計時（`date +%s%N` 包住單個命令），再決定優化哪裏。
本例的結論是「連打一串再一次讀」＋「wipe 不再 dump 確認」，
9 分鐘 → 117 秒，覆蓋未減。

**防再犯**：任何「跑得慢所以沒人跑」的腳本，先量出熱點再動刀；別憑印象調 sleep。

## E7 · 盲清字段要先 MOVE_END

**現象**：加了「盲發 DEL 清空」後，若干斷言開始多出尾巴，如 `(7))`。

**根因**：上一步輸出成對括號 `()` 時，光標停在括號**內**；
此時 `DEL` 只刪光標左側，右側殘留 `)` 繼續黏在字段末尾。

**對策**：`wipe()` 裏先 `input keyevent 123`（MOVE_END）再發 DEL，
並分兩批發（一次發 30 個會被丟鍵）。

**防再犯**：凡是「假設光標在末尾」的批量輸入，都要顯式歸位光標。

## E8 · `dumpsys mInputShown=true` 可能是陳舊狀態

**現象**：`focus()` 用 `dumpsys input_method | grep mInputShown=true` 判斷鍵盤已彈出，
但實際截圖裏鍵盤並不在，後續點擊全部落空。

**根因**：`mInputShown` 是 IME 內部的請求狀態，窗口是否真的顯示要看合成器；
剪貼板面板關閉等時機會留下不一致。

**對策**：判斷「鍵盤在不在」用截圖＋`page_kind.py`；`dumpsys` 只用來查 `mCurMethodId`（IME 是否存活）。

**防再犯**：狀態查詢要選「反映結果」的通道，不要選「反映意圖」的通道。
