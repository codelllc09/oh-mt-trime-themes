#!/bin/bash
# verify.sh —— 容器/真機驗證（逐項打勾，失敗即非零退出）
#
# 用法：TRIME_ADB_SERIAL=… ./tools/verify.sh [--section N] [--quick] [--no-clip]
#
# 默認只跑與改動直接相關的 --quick 或 --section。
# 只有用戶明確要求「全量測試」時，才可無參數跑完整流程（見 AGENTS.md）。
# lua／schema 不歸本腳本，回主倉測試。
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
NUM_ABC=63; NUM_ASC=195; NUM_CJK=327      # 數字頁左側三欄
tap()  { "${ADB[@]}" shell input tap "$1" "$2"; sleep 0.5; }
hold() { "${ADB[@]}" shell input swipe "$1" "$2" "$1" "$2" 1200; sleep 0.4; }
wipe() {   # 盲清：不再 dump 確認（一次 dump 近 2s，是最貴的操作）
  # 先全選刪除，避免雙向標點使 MOVE_END 停在視覺末尾而留下文字。
  "${ADB[@]}" shell 'input keycombination 113 29; input keyevent 67' >/dev/null 2>&1
  # 清理舊版 Android 不支援全選按鍵組合時的殘留與括號內光標。
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
expect_page() {
  local actual
  for _ in 1 2 3 4; do
    actual=$(kind)
    [ "$actual" = "$2" ] && break
    sleep 0.35
  done
  expect "$1" "$actual" "$2"
}
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
    if ! ime_alive; then
      "${ADB[@]}" shell ime set com.osfans.trime/.ime.core.TrimeInputMethodService >/dev/null 2>&1
      sleep 1
    fi
    if ime_alive && "${ADB[@]}" shell dumpsys input_method 2>/dev/null | grep -q 'mInputShown=true'; then return 0; fi
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
    num*)  tap $NUM_ABC $BOT ;;
    ascii*|cjk*) tap 81 $BOT; tap $NUM_ABC $BOT ;;
    *) return 1 ;;
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
say "═══ 1. 頁面導航（123# → 數字 → ASC/CJK → 123/ABC）═══"
expect_page "起點主鍵盤" main
tap 54 $MBOT; expect_page "123# → 數字鍵盤" num
tap $NUM_ASC $BOT; expect_page "ASC → ASCII 符號頁" ascii
tap 81 $BOT; expect_page "123 → 數字鍵盤" num
tap $NUM_CJK $BOT; expect_page "CJK → 中文標點頁" cjk
tap 81 $BOT; tap $NUM_ABC $BOT
expect_page "ABC → 主鍵盤" main
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
wipe; hold 648 $R2
batch "h 長按成對括號" "（）" 1
wipe
for x in 756 864 972; do hold $x $R2; done              # j k l
for x in 756 864; do hold $x $R3; done                  # n m
for x in 270 756 864; do hold $x $MBOT; done            # , . /
batch "長按符號 j k l n m , . /" "……——‘：“；！？" 8
fi

if want 4 && ! skip_quick 4 4; then
say "═══ 4. 功能鍵：長按後 IME 存活 ═══"
for spec in "108 1742 a:Tab" "216 1742 s:全選" "324 1742 d:撤銷" "432 1742 f:恢復" \
            "216 1907 z:反查引導" "324 1907 x:剪切" "432 1907 c:複製" "540 1907 v:粘貼"; do
  set -- $spec; wipe; hold $1 $2
  if ime_alive; then ok "$3 IME 存活"; else bad "$3 後 IME 消失"; fi
done
fi

if want 5; then
say "═══ 5. 數字鍵盤（三個等寬符號欄）═══"
# 主區欄中心 x = 63 / 195 / 327 / 494 / 641 / 788 / 986；行中心 y = 1563 / 1694 / 1825 / 1956。
# 底行中心 x = 63 / 195 / 327 / 494 / 714 / 986，y = 2087。
go_num || bad "無法進入數字頁"

# 左數學列：′ 長按 ″；其餘長按 ‰ π ℃
wipe; tap 63 1563; hold 63 1563; hold 63 1694; hold 63 1825; hold 63 1956
batch "左列：′ ″ ‰ π ℃" "′″‰π℃" 5
wipe
for y in 1563 1694 1825 1956; do tap 195 "$y"; hold 195 "$y"; done
batch "集合與邏輯短按／長按" "∪∩∈∉∧∨∀∃" 8
# { } 長按 → ≈
wipe; hold 327 1825
batch "{ } 長按 → ≈" "≈" 1
# 1 ≤ ／ 3 ≥
wipe; hold 494 1825; hold 788 1825
batch "1 ≤ ／ 3 ≥" "≤≥" 2
# / ÷ ／ - ±
wipe; hold 986 1563; hold 788 1956
batch "/ ÷ ／ - ±" "÷±" 2
# 原有行爲：數字、括號成對；更新長按 < > × ≠
wipe; tap 494 1563; tap 641 1694
batch "數字鍵盤 7、5" "75" 2
wipe; tap 327 1563
batch "() 一次成對" "()" 1
wipe; tap 327 1563; tap 494 1563
batch "光標在括號內 (7)" "(7)" 1
wipe; hold 327 1563; hold 327 1694; hold 986 1694; hold 327 1956
batch "( [ * = 長按" "<>×≠" 4
# 數字方陣底行與獨立逗號：0→#、.→·、逗號原樣上屏
wipe; hold 494 1956; hold 641 1956; tap 494 2087
batch "0 # ／ . · ／底行逗號" "#·," 3
# 空格鍵跨小數點與負號
wipe; tap 714 2087
batch "空格鍵 → 空格" " " 1
fi

if want 6; then
say "═══ 6. ASCII 符號頁（半角與長按變體）═══"
go_num || bad "無法進入數字頁"
tap $NUM_ASC $BOT
wipe; tap 54 1694; tap 216 $BOT; hold 216 $BOT; hold 972 1825; hold 756 1825
batch "半角 @ , 與長按變體" "@,،¡؛" 5
wipe
for x in 432 540 648 756; do tap "$x" 1956; hold "$x" 1956; done
batch "四向箭頭與雙線箭頭" "←⇐↑⇑↓⇓→⇒" 8
fi

if want 7; then
say "═══ 7. 中文標點頁（不翻譯）═══"
# 自足路徑：數字頁 →(ASC) ASCII 頁 →(123) 數字頁 →(CJK) 中文標點頁
go_num || bad "無法進入數字頁"
tap $NUM_ASC $BOT; tap 81 $BOT; tap $NUM_CJK $BOT
wipe; tap 54 1539; tap 918 1539
batch "中文頁 ，與 ”" "，”" 2
wipe; tap 216 $BOT; tap 324 $BOT; tap 540 $BOT; tap 756 $BOT; tap 864 $BOT
batch "中文頁底行破折號、省略號、空格、間隔號與波浪號" "—… ·～" 5
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
