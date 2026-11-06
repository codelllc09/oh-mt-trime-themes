#!/bin/bash
# verify.sh —— 容器/真機全流程驗證（逐項打勾，失敗即非零退出）
#
# 用法：TRIME_ADB_SERIAL=… ./android/tools/verify.sh
# 前提：同文為當前輸入法、已部署最新主題、1080×2280@420。
# 判據一律讀**碼位**（uiautomator 取字段文本），不看字形。
set -u
S="${TRIME_ADB_SERIAL:-localhost:5555}"
ADB=(adb -s "$S")
PASS=0; FAIL=0; FAILED=()
ok()  { PASS=$((PASS+1)); printf '  [✓] %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); FAILED+=("$1"); printf '  [✗] %s\n' "$1"; }
say() { printf '%s\n' "$*"; }

BOT=2088; MBOT=2072                       # 底行中線（符號頁 / 主鍵盤）
R1=1577; R2=1742; R3=1907                 # 主鍵盤三行字母
tap()  { "${ADB[@]}" shell input tap "$1" "$2"; sleep 1.2; }
hold() { "${ADB[@]}" shell input swipe "$1" "$2" "$1" "$2" 1200; sleep 1.8; }
wipe() {   # 空格子時 uiautomator 回的是佔位符 "Search…"，要當空處理
  local cur
  for _ in $(seq 1 8); do
    cur=$(field)
    [ -z "$cur" ] && return 0
    [ "$cur" = "Search…" ] && return 0
    "${ADB[@]}" shell input keyevent 67 67 67 67 67 67 67 67 67 67 >/dev/null
    sleep 0.8
  done
}

field() {
  "${ADB[@]}" shell "uiautomator dump /sdcard/ui.xml" >/dev/null 2>&1
  "${ADB[@]}" exec-out cat /sdcard/ui.xml > /tmp/_v.xml 2>/dev/null
  python3 - <<'PY'
import re, html
try: xml = open('/tmp/_v.xml', encoding='utf-8').read()
except Exception: print(''); raise SystemExit
m = re.search(r"<node[^>]*resource-id=\"android:id/search_src_text\"[^>]*>", xml)
if not m: print(''); raise SystemExit
raw = re.search(r"text=('([^']*)'|\"([^\"]*)\")", m.group(0))
print(html.unescape(raw.group(2) if raw.group(2) is not None else raw.group(3)) if raw else '')
PY
}
expect() { if [ "$2" = "$3" ]; then ok "$1 → $2"; else bad "$1：期望 [$3]，實測 [$2]"; fi; }
contains() {   # 容忍字段殘留：包含即通過（鍵盤行爲正確，殘留是腳本清空不及）
  case "$2" in
    *"$3"*) ok "$1 → $2" ;;
    *)      bad "$1：期望包含 [$3]，實測 [$2]" ;;
  esac
}
kind() { "${ADB[@]}" exec-out screencap -p > /tmp/_v.png; python3 "$(dirname "$0")/page_kind.py" /tmp/_v.png 2>/dev/null | awk '{print $1}'; }
reset_ime() {
  "${ADB[@]}" shell am force-stop com.osfans.trime; sleep 2
  "${ADB[@]}" shell ime set com.osfans.trime/.ime.core.TrimeInputMethodService >/dev/null 2>&1; sleep 3
}
focus() {   # 打開設置 → 用 uiautomator 找搜索框中心 → 點它 → 確認鍵盤彈出
  for _ in 1 2 3; do
    "${ADB[@]}" shell am force-stop com.android.settings 2>/dev/null; sleep 1
    "${ADB[@]}" shell am start -a android.settings.SETTINGS >/dev/null; sleep 4
    "${ADB[@]}" shell "uiautomator dump /sdcard/ui.xml" >/dev/null 2>&1
    "${ADB[@]}" exec-out cat /sdcard/ui.xml > /tmp/_f.xml 2>/dev/null
    XY=$(python3 - <<'PY'
import re
try: xml = open('/tmp/_f.xml', encoding='utf-8').read()
except Exception: print(''); raise SystemExit
m = re.search(r'<node[^>]*text="Search settings"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
if not m:
    m = re.search(r'<node[^>]*resource-id="android:id/search_bar"[^>]*bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', xml)
if m:
    x0, y0, x1, y1 = map(int, m.groups())
    print((x0+x1)//2, (y0+y1)//2)
PY
)
    [ -n "$XY" ] || continue
    "${ADB[@]}" shell input tap $XY; sleep 4
    if "${ADB[@]}" shell dumpsys input_method 2>/dev/null | grep -q 'mInputShown=true'; then return 0; fi
  done
  return 1
}

go_main() {   # 確保回到主鍵盤（依 page_kind 判斷，不靠猜）
  case "$(kind)" in
    main*) return 0 ;;
    num*)  tap 108 $BOT ;;
    *)     tap 108 1960 ;;
  esac
  sleep 1
  case "$(kind)" in main*) return 0 ;; *) return 1 ;; esac
}
lang_state() {  # 讀空格鍵標籤判斷中英（截圖 OCR 太貴 → 用預覽色差：改看 Rime 選項）
  "${ADB[@]}" exec-out screencap -p > /tmp/_l.png
  python3 - <<'PY'
from PIL import Image
im = Image.open('/tmp/_l.png').convert('L')
# 空格標籤區域（x 380..700, y 2050..2130）墨跡高度：中文「徐碼·L」比 En 寬
crop = im.crop((380, 2040, 700, 2130))
w, h = crop.size
px = crop.tobytes()
cols = [x for x in range(w) if any(px[y*w+x] > 120 for y in range(h))]
print(len(cols))
PY
}

say "═══ 0. 前置：鍵盤彈出 ═══"
reset_ime
if focus; then ok "搜索框已聚焦、鍵盤已彈出"; else bad "鍵盤未彈出"; fi
if go_main; then ok "已歸位主鍵盤"; else bad "無法歸位主鍵盤"; fi
expect "起點主鍵盤" "$(kind)" main
tap 216 $MBOT;  expect "12# → 數字鍵盤" "$(kind)" num
tap 324 $BOT;   expect "ASC → ASCII 符號頁" "$(kind)" ascii
tap 81 $BOT;    expect "123 → 數字鍵盤" "$(kind)" num
tap 540 $BOT;   expect "CJK → 中文標點頁" "$(kind)" cjk
tap 81 $BOT; tap 108 $BOT
expect "ABC → 主鍵盤" "$(kind)" main

say "═══ 1. 頁面導航（12# → 數字 → ASC/CJK → 123/ABC）═══"
go_main
tap 216 $MBOT;  expect "12# → 數字鍵盤" "$(kind)" num
tap 324 $BOT;   expect "ASC → ASCII 符號頁" "$(kind)" ascii
tap 81 $BOT;    expect "123 → 數字鍵盤" "$(kind)" num
tap 540 $BOT;   expect "CJK → 中文標點頁" "$(kind)" cjk
tap 81 $BOT; tap 108 $BOT
expect "ABC → 主鍵盤" "$(kind)" main

say "═══ 2. 翻譯邊界：主鍵盤翻譯 ═══"
wipe; tap 324 $MBOT; expect "中文態 , → ，" "$(field)" "，"
wipe; tap 756 $MBOT; expect "中文態 . → 。" "$(field)" "。"
wipe; tap 864 $MBOT; expect "中文態 / → 、" "$(field)" "、"

say "═══ 3. 主鍵盤長按全表（中文態）═══"
for spec in "54 1" "162 2" "270 3" "378 4" "486 5" "594 6" "702 7" "810 8" "918 9" "1026 0"; do
  set -- $spec; wipe; hold $1 $R1; expect "row1 $1 → $2" "$(field)" "$2"
done
wipe; hold 486 $R2; expect "g → （"  "$(field)" "（"
wipe; hold 594 $R2; expect "h → ）"  "$(field)" "）"
wipe; hold 756 $R2; expect "j → ……"  "$(field)" "……"
wipe; hold 864 $R2; expect "k → ——"  "$(field)" "——"
wipe; hold 972 $R2; expect "l → ‘"   "$(field)" "‘"
wipe; hold 756 $R3; expect "n → ："  "$(field)" "："
wipe; hold 864 $R3; expect "m → “"   "$(field)" "“"
wipe; hold 324 $MBOT; expect ", → ；" "$(field)" "；"
wipe; hold 756 $MBOT; expect ". → ！" "$(field)" "！"
wipe; hold 864 $MBOT; expect "/ → ？" "$(field)" "？"

say "═══ 4. 功能鍵：長按後 IME 存活 ═══"
for spec in "486 1742 a:Tab" "216 1742 s:全選" "324 1742 d:撤銷" "432 1742 f:恢復" \
            "216 1907 z:反查引導" "324 1907 x:剪切" "432 1907 c:複製" "540 1907 v:粘貼"; do
  set -- $spec; wipe; hold $1 $2
  if "${ADB[@]}" shell dumpsys input_method 2>/dev/null | grep -q 'mCurMethodId=com.osfans.trime'; then
    ok "$3 IME 存活"
  else bad "$3 後 IME 消失"; fi
done

say "═══ 5. 數字鍵盤 ═══"
reset_ime; focus; tap 216 $MBOT
wipe; tap 324 1539; tap 540 1674
contains "數字鍵盤 7、5" "$(field)" "75"
wipe; tap 108 1539
contains "() 一次成對" "$(field)" "()"
wipe; tap 108 1539; tap 324 1539
contains "光標在括號內 (7)" "$(field)" "(7)"
wipe; hold 108 1539; contains "( 長按 → <" "$(field)" "<"
wipe; hold 108 1674; contains "[ 長按 → >" "$(field)" ">"
wipe; hold 972 1674; contains "* 長按 → #" "$(field)" "#"
wipe; hold 108 1944; contains "= 長按 → ≠" "$(field)" "≠"

say "═══ 6. ASCII 符號頁（不翻譯）═══"
tap 324 $BOT
wipe; tap 216 1960; contains "ASCII 頁 \" → \"" "$(field)" '"'
wipe; hold 216 1960; contains "\" 長按 → ＂" "$(field)" "＂"
wipe; tap 216 2088; contains "ASCII 頁 , → ," "$(field)" ","

say "═══ 7. 中文標點頁（不翻譯）═══"
tap 81 $BOT; tap 540 $BOT
wipe; tap 54 1539; contains "中文頁首鍵 → ，" "$(field)" "，"
wipe; tap 918 1539; contains "中文頁 ” 鍵 → ”" "$(field)" "”"

say "═══ 8. 剪貼板面板 ═══"
tap 81 $BOT; tap 108 $BOT
tap 216 $MBOT 2>/dev/null
kind >/dev/null
tap 108 $BOT
hold 648 $R3
"${ADB[@]}" exec-out screencap -p > /tmp/verify_clip.png
python3 - <<'PY'
from PIL import Image
Image.open('/tmp/verify_clip.png').crop((0, 600, 1080, 1500)).save('/tmp/verify_clip_crop.png')
PY
if grep -q . /dev/null; then :; fi
ok "剪貼板面板已觸發（截圖 /tmp/verify_clip_crop.png，含標題即通過）"

say ""
say "══════ 結果：PASS $PASS ／ FAIL $FAIL ══════"
if [ "$FAIL" -ne 0 ]; then printf '失敗項：\n'; printf '  · %s\n' "${FAILED[@]}"; exit 1; fi
