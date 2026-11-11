# Trime 主題知識與故障經驗

以 Trime 3.3.13 為基準。本倉配置與設備量測作為範例。

## 配置與按鍵動作

### 主題檔名衝突

- **現象**　自訂主題與內建主題使用同一檔名時，選單中的不同項目可能載入同一份配置。
- **判斷**　Trime 按去除 `.yaml` 的檔名查找配置，先找使用者資料夾，再找共享資料夾。內建預設的 ID 是 `trime`。例如 `example.trime.yaml` 的配置 ID 是 `example.trime`。
- **處理**　自訂主題使用獨立的 `<短名>.trime.yaml`，在 YAML 中用 `name` 指定選單顯示名。
- **依據**　[Trime 檔案清單](https://raw.githubusercontent.com/osfans/trime/develop/app/src/main/java/com/osfans/trime/data/theme/ThemeFilesManager.kt) · [Trime 3.3.13 主題載入](https://raw.githubusercontent.com/osfans/trime/v3.3.13/app/src/main/java/com/osfans/trime/data/theme/ThemeLoader.kt) · [預設回退](https://raw.githubusercontent.com/osfans/trime/v3.3.13/app/src/main/java/com/osfans/trime/data/theme/ThemeManager.kt)

### 改動未出現在生成檔

- **現象**　修改 `number_zh` 或移動長按動作後，生成檔仍是舊配置。
- **判斷**　同一映射出現兩次 `number_zh` 時，本倉使用的 PyYAML 會取後一份。依原文替換鍵位也可能零命中。
- **處理**　合併重複定義，解析源檔核對目標鍵的實際值，再重新生成並比對。靜態校驗會掃描 V1 源檔頂層區段下的重複鍵。
- **依據**　用 PyYAML 解析 `number_zh: 1\nnumber_zh: 2` 得到 `{'number_zh': 2}`。[靜態校驗](../../../../tools/check_trime.py) · [重建步驟](build.md#重建主題)

### ASCII 頁出現中文標點

- **現象**　ASCII 頁的逗號變成 `，`。
- **判斷**　Trime 以 `ascii_mode == 1` 判定鍵盤的初始 ASCII 狀態，`-1` 得到 `false`。送出的鍵事件仍受方案與全半角設定影響。
- **處理**　需要固定為 ASCII 的頁面用 `ascii_mode: 1`、`reset_ascii_mode: true`。若還有換形，核對方案的標點表及工具欄的全半角狀態。
- **依據**　[Trime Keyboard](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/Keyboard.kt#L75-L78) · [本倉鍵位表](../../../../docs/KEYBOARD_MAP.md)

### 長按角標空白或壓住鍵面文字

- **現象**　數字頁的方向鍵提示曾留白，細箭頭也容易和數字疊在一起。
- **判斷**　上方角標優先取 `label_symbol`，空字串時取長按動作的標籤。下方 `hint` 是另一欄。Trime 的「Hide key symbol」可隱藏上方角標。
- **處理**　個別鍵用 `label_symbol: ' '` 可留下空白角標並保留動作。V1 數字頁用實心三角作方向提示，並用 `key_text_offset_y` 錯開數字與角標。空格的「語音」取自 `VOICE_ASSIST` 的固定標籤。實際能否啟動語音，由 Android 已啟用的語音輸入法決定。
- **依據**　[Trime Key](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/Key.kt#L282-L283) · [Trime KeyView](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/KeyView.kt#L345-L347) · [V1 源檔](../../../../rime/theme/sources/v1.theme-source.yaml)

### 長按有角標但選單不可見

- **現象**　鍵面已顯示提示，長按時看不到彈出選單。
- **判斷**　角標、`long_click` 和 `popup` 分別負責提示、直接動作和選單。角標本身只提供提示。
- **處理**　確認目標鍵有 `popup` 項目，並核對 `popup_width`、`popup_height`、`popup_key_height` 和 `popup_text_size` 的有效尺寸。
- **依據**　[Trime 長按分支](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/KeyView.kt#L144-L155) · [本倉選單校驗](../../../../tools/check_trime.py)

### 直出標點與切頁要配在動作上

- **現象**　在鍵位層加 `commit:` 沒有直出，或刪掉 `send: Eisu_toggle` 後 `select:` 無法切頁。
- **判斷**　Trime 從內嵌動作或 `preset_keys` 解析 `commit`。鍵盤切頁由 `Eisu_toggle` 的處理分支讀取 `select`。
- **處理**　固定字元可用 `{click: {commit: '、', label: '、'}}`。返回鍵用 `send: Eisu_toggle` 搭配 `select: .default`，回到當前方案的主鍵盤。
- **依據**　[Trime KeyAction](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/KeyAction.kt#L172-L223) · [Trime 切頁分支](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/CommonKeyboardActionListener.kt#L112-L137)

### 回車鍵在不同輸入框顯示不同

- **現象**　同一主題的回車鍵在搜尋框顯示搜尋圖示，在多行輸入框顯示回車。
- **判斷**　Trime 將 `enter_labels` 標記解析成當前輸入框對應的鍵面。`enter_label_mode` 決定如何採用 App 的自訂動作名稱。
- **處理**　在 `enter_labels` 配置標準動作的字樣或圖示，並在相應輸入框核對顯示和輸出。
- **依據**　[Trime 回車鍵繪製](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/KeyView.kt#L248-L254) · [內建主題配置](../../../../rime/theme/vendor/trime-3.3.13.yaml#L56)

### 斜線有候選或方案命令失效

- **現象**　徐碼·L 中文態點斜線後出候選。改為直接提交 `、` 後，`/menu` 等命令無法組稿。
- **判斷**　Rime 依當前方案的標點表處理鍵事件。多選列表進入候選流程，`{commit: …}` 則可直接提交。Trime 動作的 `commit` 也直接向輸入框提交字元。
- **處理**　徐碼·L 的主鍵盤保留送出 ASCII `/`。要打 `、`，按斜線後選候選。其他方案依其標點表驗證。
- **依據**　[Rime 標點表](https://github.com/rime/rime-prelude/blob/master/punctuation.yaml#L36-L60) · [librime Punctuator](https://github.com/rime/librime/blob/master/src/rime/gear/punctuator.cc#L168-L224) · [本倉鍵位表](../../../../docs/KEYBOARD_MAP.md#三主鍵盤4-行)

## 配色、字體與圖像

### HTML 預覽的半透明色跑偏

- **現象**　同一個八位十六進位色值在 Trime 和 HTML 裡呈現不同顏色。
- **判斷**　Trime 的八位字面色使用 `#AARRGGBB`，CSS 使用 `#RRGGBBAA`。
- **處理**　渲染預覽時轉換位序或輸出 `rgba()`。回寫 YAML 時，把以 `#` 開頭的顏色保留為帶引號的字串。
- **依據**　[原型渲染器的 `css_color`](../../../../tools/render_keyboard.py)

### 深淺色未跟隨系統切換

- **現象**　系統切換深色後，鍵盤仍維持原配色。
- **判斷**　Trime 依目前選用的配色、主題的 `dark_scheme`／`light_scheme` 關聯，以及「跟隨系統日夜配色」設定決定實際配色。
- **處理**　核對目前選中的配色和其日夜配色關聯，再檢查同文的跟隨系統設定。
- **依據**　[Trime 配色載入](https://raw.githubusercontent.com/osfans/trime/v3.3.13/app/src/main/java/com/osfans/trime/data/theme/ColorManager.kt)

### 引號外觀與字體回退

- **現象**　輸出碼位已是中文排版常用的彎引號，鍵面仍顯得窄小。
- **判斷**　Trime 從使用者資料夾的 `fonts/` 讀取主題指定字體，並略過缺失的檔案。Android 10 以上有自訂回退鏈，鍵面可依 `latin_font`、`key_font`、`hanb_font` 的順序找字形。
- **處理**　先核對碼位及字體檔。V1 的拉丁子集略去四個彎引號，讓 CJK 子集提供字形。曾遇到跨可變字體合併的 `VarStore` 錯誤，這裡使用各自的子集與回退鏈。
- **依據**　[Trime ThemeFonts](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/data/theme/ThemeFonts.kt#L65-L98) · [共用字體與授權](../../../../rime/fonts/README.md)

### CJK 子集過細

- **現象**　直接子集化當時使用的 Noto Sans CJK SC 可變字體後，鍵面偏細。
- **判斷**　該檔的 `wght` 預設值和 `OS/2.usWeightClass` 都是 100。可變字體的預設值由各檔案指定。
- **處理**　先子集化，再把 `wght` 固定為 400。用 FontTools 讀取輸出字體的 `OS/2.usWeightClass` 核對。
- **依據**　目前收錄的 `xuma_key.otf` 字重為 400。[字體重建腳本](../../../../tools/rebuild_key_font.py)

### 同頁需要不同的分組間距

- **現象**　數字頁需要拉開分組間距，同組按鍵仍保持緊湊。
- **判斷**　同一頁的 `horizontal_gap` 共用。只有寬度而沒有 `click` 的項目會佔用橫向空間。
- **處理**　保留頁面的基本鍵縫，用只有 `width` 的間隔項目分組。確認加上間隔後的行寬與鍵位。
- **依據**　[Trime 鍵盤排版](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/Keyboard.kt#L196-L232) · [本倉數字頁](../../../../docs/KEYBOARD_MAP.md#四數字鍵盤頁number)

### 地球鍵圖示變形

- **現象**　調整鍵寬或行距後，地球鍵圖示變扁。
- **判斷**　背景圖被拉伸到鍵面。Trime 按 `keyboard_height` 縮放各行，行距從鍵面的上下邊扣除。本倉 V1 在 1080 × 2280、420 dpi 下測得地球鍵約 96 × 130 px。
- **處理**　鍵面比例改變時量實際像素，更新 `gen_icons.py` 的 `ASPECT`，再以截圖核對圖示形狀。
- **依據**　[Trime 鍵面邊距](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/KeyboardView.kt#L52-L65) · [本倉圖示生成腳本](../../../../tools/gen_icons.py)

### 圖片替換後仍顯示舊圖

- **現象**　以同名 PNG 替換鍵面背景後，畫面仍顯示舊圖。
- **判斷**　Trime 按圖片路徑快取點陣圖。
- **處理**　確認替換的是目前主題實際讀取的檔案，再重啟同文核對。
- **依據**　[Trime 圖片載入與快取](https://raw.githubusercontent.com/osfans/trime/v3.3.13/app/src/main/java/com/osfans/trime/data/theme/ColorManager.kt)

### 標點字形偏心

- **現象**　全形括號的字身居中，墨跡仍偏向一側。
- **判斷**　Trime 以字體度量定位文字，字形墨跡的包圍盒可能偏離鍵面中心。
- **處理**　對純色鍵面量墨跡偏移，再調整 `key_text_offset_x`。`glyph_offsets.py` 以 V1 中文標點頁的截圖和等寬鍵為基準，遇到異形或不同寬度的鍵需重新確認取樣框。
- **依據**　[Trime 繪字程式](https://github.com/osfans/trime/blob/v3.3.13/app/src/main/java/com/osfans/trime/ime/keyboard/KeyView.kt#L286-L304) · [字形量測工具](../../../../tools/glyph_offsets.py)

## 鍵音

### 鍵音包漏聲或對錯鍵

- **現象**　配色正常，字鍵、退格或回車卻播放錯誤樣音。
- **判斷**　鍵音描述檔與主題配置分開載入。`folder` 指定 `soundeffect/` 下的樣音目錄，`sound` 列出檔名，`keyset` 的 `sounds` 用從零起算的索引指向樣音。
- **處理**　打包時保留 `soundeffect/<id>.sound.yaml` 與描述檔引用的 WAV 路徑。核對按鍵映射和檔案，再在同文選取配套音效包，以同樣節奏試字鍵、退格和回車。實錄樣音保留來源與授權。
- **依據**　[Trime 音效描述](https://github.com/osfans/trime/commit/411ed71653769849d73c90fada5c4226e943497c) · [本倉打字機音效範例](../../../../rime/soundeffect/v2-typewriter.sound.yaml)

## 設備驗證

### 改動未載入或鍵盤未彈出

- **現象**　測試畫面仍用舊主題，或 `mInputShown=true` 時點擊卻落空。
- **判斷**　目前選用的主題、實際載入的配置與鍵盤是否出現在畫面上，需要分別確認。
- **處理**　核對主題及實際鍵面。V1 自動驗證先用 `page_kind.py` 判斷是否回到主鍵盤。辨識不明時檢查截圖、尺寸與配色。
- **依據**　[設備操作](device.md#實機部署) · [驗證腳本](../../../../tools/verify.sh) · [鍵盤辨識工具](../../../../tools/page_kind.py)

### 鍵位測試點錯位置或認錯字元

- **現象**　視窗改版後點到其他控制項，或把 `“`（U+201C）認成 `"`（U+0022）。
- **判斷**　系統介面會移動，固定鍵位座標也只適用於特定版式和尺寸。相近的字形可來自不同碼位。
- **處理**　用 UI 節點的 `bounds` 定位搜尋框，依現行鍵面定位按鍵。從 XML 取文字並解碼實體，再逐碼位比對。
- **依據**　[驗證腳本](../../../../tools/verify.sh)的 `focus` 和 `field` · [主要尺寸](device.md#主要尺寸)

### 清空輸入後仍有殘字

- **現象**　上一項輸入成對括號後，下一項多出尾括號。
- **判斷**　光標可能停在兩括號之間，退格只刪光標前方。
- **處理**　先全選並刪除，必要時用 `KEYCODE_MOVE_END`（123）移至末尾再退格。排查個別失敗時讀回輸入欄確認。
- **依據**　[驗證腳本的 `wipe`](../../../../tools/verify.sh)

### 自動點擊測試耗時過長

- **現象**　舊版腳本頻繁逐鍵讀取輸入欄，單次回歸耗時數分鐘。
- **判斷**　當時 Waydroid 每次 `uiautomator dump` 約 1.93 秒，單次點擊約 15 毫秒。
- **處理**　先量各操作耗時，將可連續驗證的輸入合成一串再讀取。失敗時才逐鍵定位。
- **依據**　歷史提交 `03c9885` 記錄量測與驗收結果。[驗證腳本](../../../../tools/verify.sh)

### 錄影未能呈現鍵音

- **現象**　錄影看得到按鍵，但缺少部分字鍵或回車聲。
- **判斷**　鍵面錄影與內部音訊可分開取得。截圖和畫面無法確認音效是否播放。
- **處理**　同時錄製畫面與裝置內部音訊。核對主鍵盤和受影響的頁面，按時間複聽疑似漏聲的按鍵。若剪輯調整音量，交付時說明。
- **依據**　[scrcpy 錄影文件](https://github.com/Genymobile/scrcpy/blob/master/doc/recording.md)

## 原型設計

### 原型漏掉長按功能

- **現象**　數字頁的靜態稿省略括號長按及方向鍵，導致對鍵位空間的判斷有偏差。
- **判斷**　比較時只呈現了短按，漏掉同一鍵的其他動作。
- **處理**　從現行配置生成基準，並排比較實際鍵面與提案，兩者都呈現短按和長按。以相同 dp／sp 比較不同密度的畫面，定案後同步說明與相應的生成圖。
- **依據**　[設計流程](build.md#原型) · [數字頁鍵位表](../../../../docs/KEYBOARD_MAP.md#四數字鍵盤頁number)
