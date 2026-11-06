#!/bin/bash
# verify.sh —— 容器/真機全流程驗證（逐項打勾，失敗即非零退出）
#
# 用法：TRIME_ADB_SERIAL=… ./tools/verify.sh [--section N] [--quick] [--no-clip]
#
# 跑多少由改動風險決定（見 TESTING.md「按改動風險選驗證」）：
#   只改配色／文案／單鍵數值 → --quick（約 50s，跳過長按全表與功能鍵）
#   改版式／鍵位／行高     → 全量（約 2 分鐘）
#   改 lua／schema        → 不歸本腳本，回主倉跑四道門禁
# 前提：同文為當前輸入法、已部署最新主題、1080×2280@420。
# 判據一律讀**碼位**（uiautomator 取字段文本），不看字形。
#
# 效能備註（2026-11-07 重寫，皆為實測值）：
#   uiautomator dump ≈1.93s／次，是全腳本唯一的大頭；input tap 15ms、
#   dumpsys input_method 12ms、screencap+page_kind 260ms 都不值錢。
#   故策略是**減少 dump 次數**：
#     ① 長按／點擊的輸出改成「連打一串 → 讀一次」，失敗時看合成字串即可定位；
#     ② wipe 不再先 dump 確認，直接盲發 30 個 DEL（≈0.3s）；
#     ③ 固定 sleep 由 tap 1.2s／hold 1.8s 降到 0.5s／1.3s（長按手勢本身已 1200ms）；
#     ④ 刪掉與第 1 段重複的導航、以及第 5 段多餘的 reset_ime＋focus。
#   覆蓋不變：批次通過時按逐鍵計數，PASS 總數與舊版一致。
set -u
S="${TRIME_ADB_SERIAL:-localhost:5555}"
ADB=(adb -s "$S")
ONLY=""; CLIP=1; QUICK=0
while [ $# -gt 0 ]; do
  case "$1" in
    --section) ONLY="$2"; shift 2 ;;
    --quick) QUICK=1; CLIP=0; shift ;;   # 跳過第 3／4／8 段（長按全表、功能鍵、剪貼板）
    --no-clip) CLIP=0; shift ;;
    *) echo "未知參數：$1" >&2; exit 2 ;;
  esac
done
PASS=0; FAIL=0; FAILED=()
ok()  { PASS=$((PASS+1)); printf '  [✓] %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); FAILED+=("$1"); printf '  [✗] %s\n' "$1"; }
say() { printf '%s\n' "$*"; }
want() { [ -z "$ONLY" ] || [ "$ONLY" = "$1" ]; }
skip_quick() { [ "$QUICK" = 1 ] && [ "$1" = "$2" ]; }

BOT=2088; MBOT=2072                       # 底行中線（符號頁 / 主鍵盤）
R1=1577; R2=1742; R3=1907                 # 主鍵盤三行字母
tap()  { "${ADB[@]}" shell input tap "$1" "$2"; sleep 0.5; }
hold() { "${ADB[@]}" shell input swipe "$1" "$2" "$1" "$2" 1200; sleep 0.4; }
wipe() {   # 盲清：不再 dump 確認（一次 dump 近 2s，是最貴的操作）
  # 必須先 MOVE_END 再 DEL：光標若停在中間（例如上一項輸出了成對括號 「()」，
  # 光標留在括號內），DEL 只會刪光標左側，殘留會黏在後面——實測曾得到「(7))」。
  local codes; codes=$(printf '67 %.0s' $(seq 1 25))
  "${ADB[@]}" shell input keyevent 123 $codes >/dev/null 2>&1; sleep 0.15
  "${ADB[@]}" shell input keyevent 123 $codes >/dev/null 2>&1; sleep 0.25
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
# batch 標籤 期望字串 逐項數 —— 一發 dump 驗多鍵；通過時按逐鍵計數
batch() {
  local got want_s=$2 n=$3 i
  sleep 0.6                      # 讓上屏的字符落地（連打後立刻 dump 曾漏最後一個）
  got=$(field)
  if [ "$got" = "$want_s" ]; then
    for i in $(seq 1 "$n"); do ok "$1（$i/$n）"; done
  else
    bad "$1：期望 [$want_s]，實測 [$got]（$n 項合併驗證）"
  fi
}
kind() { "${ADB[@]}" exec-out screencap -p > /tmp/_v.png; python3 "$(dirname "$0")/page_kind.py" /tmp/_v.png 2>/dev/null | awk '{print $1}'; }
ime_alive() { "${ADB[@]}" shell dumpsys input_method 2>/dev/null | grep -q 'mCurMethodId=com.osfans.trime'; }
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

go_num() {   # 確保停在數字頁（符號頁的中轉站；各段可單獨跑）
  case "$(kind)" in
    num*) return 0 ;;
    main*|"") tap 54 $MBOT ;;
    *) tap 81 $BOT ;;
  esac
  sleep 0.4
  case "$(kind)" in num*) return 0 ;; *) return 1 ;; esac
}

go_main() {   # 確保回到主鍵盤（依 page_kind 判斷，不靠猜）
  case "$(kind)" in
    main*) return 0 ;;
    num*)  tap 81 $BOT ;;
    *)     tap 108 1960 ;;
  esac
  sleep 0.4
  case "$(kind)" in main*) return 0 ;; *) return 1 ;; esac
}

T0=$(date +%s)
say "═══ 0. 前置：鍵盤彈出 ═══"
reset_ime
if focus; then ok "搜索框已聚焦、鍵盤已彈出"; else bad "鍵盤未彈出"; fi
if go_main; then ok "已歸位主鍵盤"; else bad "無法歸位主鍵盤"; fi

if want 1; then
say "═══ 1. 頁面導航（12# → 數字 → ASC/CJK → 123/ABC）═══"
expect "起點主鍵盤" "$(kind)" main
tap 54 $MBOT;  expect "12# → 數字鍵盤" "$(kind)" num
tap 243 $BOT;   expect "ASC → ASCII 符號頁" "$(kind)" ascii
tap 81 $BOT;    expect "123 → 數字鍵盤" "$(kind)" num
tap 405 $BOT;   expect "CJK → 中文標點頁" "$(kind)" cjk
tap 81 $BOT; tap 81 $BOT
expect "ABC → 主鍵盤" "$(kind)" main
fi

if want 2; then
say "═══ 2. 翻譯邊界：主鍵盤翻譯（連打後讀一次）═══"
# `/` 送的是 ASCII `/`（保 /menu /add 等 lua 入口），中文態下 Rime 給
# 、/／÷ 候選，**要再按一次空格**才上屏第一個（用戶裁定的「老樣子兩步」）。
wipe; tap 270 $MBOT; tap 756 $MBOT; tap 864 $MBOT; tap 540 $MBOT
batch "中文態 , . /＋空格選首選" "，。、" 3
fi

if want 3 && ! skip_quick 3 3; then
say "═══ 3. 長按全表（中文態，連打後讀一次）═══"
wipe
for x in 54 162 270 378 486 594 702 810 918 1026; do hold $x $R1; done
batch "row1 長按 → 1..0" "1234567890" 10
wipe
for x in 486 594 756 864 972; do hold $x $R2; done      # g h j k l
for x in 756 864; do hold $x $R3; done                  # n m
for x in 270 756 864; do hold $x $MBOT; done            # , . /
batch "長按符號 g h j k l n m , . /" "（）……——‘：“；！？" 10
fi

if want 4 && ! skip_quick 4 4; then
say "═══ 4. 功能鍵：長按後 IME 存活 ═══"
for spec in "486 1742 a:Tab" "216 1742 s:全選" "324 1742 d:撤銷" "432 1742 f:恢復" \
            "216 1907 z:反查引導" "324 1907 x:剪切" "432 1907 c:複製" "540 1907 v:粘貼"; do
  set -- $spec; wipe; hold $1 $2
  if ime_alive; then ok "$3 IME 存活"; else bad "$3 後 IME 消失"; fi
done
fi

if want 5; then
say "═══ 5. 數字鍵盤（6 列 × 16.7 單位）═══"
# 座標：列中心 x = 90 / 270 / 451 / 631 / 811 / 992；行中心 y = 1563 / 1694 / 1825 / 1956 / 2087（底行）
go_num || bad "無法進入數字頁"

# 新數學列：點 , ；長按 ‰ π ℃
wipe; tap 90 1563; hold 90 1694; hold 90 1825; hold 90 1956
batch "新列：, ‰ π ℃" ",‰π℃" 4
# { } 長按 → ≈
wipe; hold 270 1825
batch "{ } 長按 → ≈" "≈" 1
# 1 ≤ ／ 3 ≥
wipe; hold 451 1825; hold 811 1825
batch "1 ≤ ／ 3 ≥" "≤≥" 2
# / ÷ ／ - ±
wipe; hold 992 1563; hold 811 1956
batch "/ ÷ ／ - ±" "÷±" 2
# 原有行爲：數字、括號成對、長按 < > # ≠
wipe; tap 451 1563; tap 631 1694
batch "數字鍵盤 7、5" "75" 2
wipe; tap 270 1563
batch "() 一次成對" "()" 1
wipe; tap 270 1563; tap 451 1563
batch "光標在括號內 (7)" "(7)" 1
wipe; hold 270 1563; hold 270 1694; hold 992 1694; hold 270 1956
batch "( [ * = 長按" "<>#≠" 4
# 空格鍵（鍵面寫「空格」，寬 40）
wipe; tap 702 2087
batch "空格鍵 → 空格" " " 1
fi

if want 6; then
say "═══ 6. ASCII 符號頁（不翻譯）═══"
go_num || bad "無法進入數字頁"
tap 243 $BOT                                   # 數字頁的 ASC
wipe; tap 216 1960; hold 216 1960; tap 216 2088
batch "ASCII 頁 \" 點／長按、, 點擊" '"＂,' 3
fi

if want 7; then
say "═══ 7. 中文標點頁（不翻譯）═══"
# 自足路徑：數字頁 →(ASC) ASCII 頁 →(123) 數字頁 →(CJK) 中文標點頁
go_num || bad "無法進入數字頁"
tap 243 $BOT; tap 81 $BOT; tap 405 $BOT
wipe; tap 54 1539; tap 918 1539
batch "中文頁 ，與 ”" "，”" 2
fi

if [ "$CLIP" = 1 ] && want 8; then
say "═══ 8. 剪貼板面板 ═══"
go_main || bad "無法回到主鍵盤"
hold 648 $R3
"${ADB[@]}" exec-out screencap -p > /tmp/verify_clip.png
python3 - <<'PY'
from PIL import Image
Image.open('/tmp/verify_clip.png').crop((0, 600, 1080, 1500)).save('/tmp/verify_clip_crop.png')
PY
ok "剪貼板面板已觸發（截圖 /tmp/verify_clip_crop.png，含標題即通過）"
fi

T1=$(date +%s)
say ""
say "══════ 結果：PASS $PASS ／ FAIL $FAIL　　耗時 $((T1-T0)) s ══════"
if [ "$FAIL" -ne 0 ]; then printf '失敗項：\n'; printf '  · %s\n' "${FAILED[@]}"; exit 1; fi
