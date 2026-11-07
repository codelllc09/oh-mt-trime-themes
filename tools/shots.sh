#!/bin/bash
# shots.sh —— 一鍵刷新 tmp/overview：當前版本「全套界面截圖」（整批覆蓋）
#
# 用法：  TRIME_ADB_SERIAL=localhost:5555 ./android/tools/shots.sh
# 產物：  tmp/overview/NN-<界面>-<light|dark>.png
#
# 前置：容器 1080x2280@420、同文為當前輸入法、app 內已部署最新主題。
# 說明：tmp/ 不入庫（.gitignore）；此腳本入庫，保證「全套截圖」可一鍵復現。
#
# 頁別**不靠圖像判定**（淺色主題下空格鍵與背景色差小，判定不可靠）：
# 流程全程確定性——重啓 IME 歸位 → 主鍵盤，其後每一步都是固定按鍵導航，
# 因此檔名由流程決定，改版時只要同步本腳本的座標即可。
#
# 導航模型（Hub，見 KEYBOARD_MAP.md）：
#   主鍵盤 123# → number（數字鍵盤）→ ASC → number_ascii ／ CJK → number_zh
#   符號頁 123 → 回 number；各頁 ABC → 回主鍵盤
# 每一步都由**已知狀態**出發（起點用重啓 IME 歸位），拍完再用 page_kind.py
# 反查一次頁別，檔名與畫面不符就報錯（歷史上錯過三次）。
set -e
SER="${TRIME_ADB_SERIAL:-localhost:5555}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/tmp/overview"
ADB=(adb -s "$SER")

SEARCH_X=376; SEARCH_Y=605
# 主鍵盤 4 行：1577/1742/1907/2072；符號頁與數字鍵盤 5 行：底行 2088
ROW1_Y=1577; ROW2_Y=1742; ROW3_Y=1907; BOTTOM_Y=2072; SYM_BOTTOM_Y=2088
GLOBE_X=162; KEY12_X=54; SHIFT_X=81; B_X=648    # 底行：123#(0-10) 地球(10-20)，各 10 單位等寬
# 各頁底行座標
NUM_ABC_X=76; NUM_ASC_X=227; NUM_CJK_X=378    # 數字頁底行 14/14/14/10/29/19
SYM_123_X=81

ime_up() { "${ADB[@]}" shell dumpsys input_method 2>/dev/null | grep -q 'mInputShown=true'; }
ensure_kb() {
  for _ in 1 2 3 4; do
    ime_up && return 0
    "${ADB[@]}" shell input tap $SEARCH_X $SEARCH_Y; sleep 3
  done
  echo "  ✗ 鍵盤未彈出" >&2; return 1
}
assert_theme() {   # 主題必須是 V1（configId=v1），否則整批截圖都是內建「預設」
  if "${ADB[@]}" shell dumpsys window 2>/dev/null | grep -q 'Themes'; then sleep 1; fi
  local hit
  hit=$("${ADB[@]}" shell "ls /storage/emulated/0/Android/data/com.osfans.trime/files/rime/v1.trime.yaml" 2>/dev/null | tr -d '\r')
  if [ -z "$hit" ]; then
    echo "  ✗ 裝置上沒有 v1.trime.yaml，先跑 deploy.sh push" >&2; return 1
  fi
  return 0
}

reset_ime() {   # 確定性歸位：重啓 IME → 主鍵盤、中文態
  "${ADB[@]}" shell am force-stop com.osfans.trime
  sleep 2
  "${ADB[@]}" shell ime set com.osfans.trime/.ime.core.TrimeInputMethodService >/dev/null 2>&1
  sleep 3
  "${ADB[@]}" shell input tap $SEARCH_X $SEARCH_Y; sleep 4
}
tap()  { "${ADB[@]}" shell input tap "$1" "$2"; sleep "${3:-2}"; }
hold() { "${ADB[@]}" shell input swipe "$1" "$2" "$1" "$2" 1300; sleep "${3:-3}"; }
bs()   { for _ in $(seq "$1"); do "${ADB[@]}" shell input keyevent 67; done; sleep 1; }

mkdir -p "$OUT"; rm -f "$OUT"/*.png
kind_of() { python3 "$ROOT/tools/page_kind.py" "$1" | awk '{print $1}'; }
shot() {      # shot <檔名>
  ensure_kb
  "${ADB[@]}" exec-out screencap -p > "$OUT/$1.png"
  echo "  ✓ $1"
}

assert_theme || exit 1

echo "── 淺色（雲白）──"
"${ADB[@]}" shell cmd uimode night no >/dev/null; sleep 3
"${ADB[@]}" shell am start -a android.settings.SETTINGS >/dev/null; sleep 4
reset_ime
shot 01-主鍵盤-light
"${ADB[@]}" shell input text "tigu"; sleep 3
shot 02-組稿候選-light
bs 6
hold $SHIFT_X $ROW3_Y 2; shot 03-Shift鎖定-light
tap $SHIFT_X $ROW3_Y 2

tap $KEY12_X $BOTTOM_Y 3;  shot 10-數字鍵盤-light
tap $NUM_ASC_X $SYM_BOTTOM_Y 3; shot 04-符號頁-ASCII-light
tap $SYM_123_X $SYM_BOTTOM_Y 3
tap $NUM_CJK_X $SYM_BOTTOM_Y 3; shot 05-中文標點頁-light
tap $NUM_ABC_X $SYM_BOTTOM_Y 3

hold $B_X $ROW3_Y 6; shot 06-剪貼板面板-light

echo "── 深色（墨空）──"
"${ADB[@]}" shell cmd uimode night yes >/dev/null; sleep 5
"${ADB[@]}" shell am start -a android.settings.SETTINGS >/dev/null; sleep 4
reset_ime
shot 07-主鍵盤-dark
tap $KEY12_X $BOTTOM_Y 3;  shot 11-數字鍵盤-dark
tap $NUM_ASC_X $SYM_BOTTOM_Y 3; shot 08-符號頁-ASCII-dark
tap $SYM_123_X $SYM_BOTTOM_Y 3
tap $NUM_CJK_X $SYM_BOTTOM_Y 3; shot 09-中文標點頁-dark

echo "── 完成：$(ls "$OUT"/*.png | wc -l) 張 → $OUT"
