#!/usr/bin/env bash
# android/deploy.sh —— 徐碼·L 同文（Trime）端部署與回採
#
# 用法：
#   android/deploy.sh pkg          # 打包部署 zip → tmp/tongwen-pkg-<時間>.zip
#   android/deploy.sh push         # adb 逐檔推送到 /storage/emulated/0/rime
#   android/deploy.sh pull-spool   # 回收手機 /add 攢詞 spool → 桌面主工作樹（去重合併）
#
# 設計：
#   · 清單唯一來源＝android/tools/check_trime.py manifest（改清單只改一處）；
#   · 寫盤動作（zip 產物、spool 合併）一律經 _ledger 留痕（AGENTS 留痕規定）；
#   · 推送不刪手機端其他檔案（userdb、其他方案不受影響）。
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
TOOLS="$ROOT/lua/codelllc09/tools"
PHONE_DIR="${TRIME_PHONE_DIR:-/storage/emulated/0/rime}"
DESKTOP_RIME="${RIME_DESKTOP_DIR:-$HOME/.config/ibus/rime}"   # 桌面主工作樹（部署源）
# 多目標支持（2026-11-05）：USB 真機默認；設 TRIME_ADB_SERIAL 指向 Waydroid 容器
# （如 localhost:5555）或網絡 adb 設備，例：
#   TRIME_ADB_SERIAL=localhost:5555 android/deploy.sh push
SER="${TRIME_ADB_SERIAL:-}"
adbx() { if [ -n "$SER" ]; then adb -s "$SER" "$@"; else adb "$@"; fi; }

note() {  # _ledger 台賬（寫盤留痕；失敗不阻塞但會打印）
  python3 "$TOOLS/_ledger.py" "$1" "$2" "$3" || echo "[!] 台賬寫入失敗（不阻塞）" >&2
}

manifest() { python3 "$ROOT/android/tools/check_trime.py" manifest; }

case "${1:-}" in
pkg)
  mkdir -p "$ROOT/tmp"
  ZIP="$ROOT/tmp/tongwen-pkg-$(date +%Y%m%d-%H%M).zip"
  STAGE="$(mktemp -d)"
  trap 'rm -rf "$STAGE"' EXIT
  python3 "$ROOT/android/tools/check_trime.py" gen-custom "$STAGE" 2>/dev/null   # 個人配置二件（不入庫，gen-custom 生成）
  manifest | while IFS=$'\t' read -r src dst; do
    mkdir -p "$STAGE/$(dirname "$dst")"
    cp "$ROOT/$src" "$STAGE/$dst"
  done
  # /add spool 佔位（手機端 io.open 追加寫需要目錄已存在）
  mkdir -p "$STAGE/lua/codelllc09/tools/dict_pipeline"
  printf '# 同文端 /add 攢詞暫存（deploy.sh pull-spool 回收入庫；桌面勿編）\n' \
    > "$STAGE/lua/codelllc09/tools/dict_pipeline/README.txt"
  python3 -m zipfile -c "$ZIP" "$STAGE/."
  echo "已打包：$ZIP（$(manifest | wc -l)+1 件）"
  note "$ZIP" 生成 "同文部署包：manifest $(manifest | md5sum | cut -c1-8) 共 $(manifest | wc -l) 件"
  ;;

push)
  command -v adb >/dev/null || { echo '✗ 缺 adb（android-tools 或 scrcpy 附帶）'; exit 1; }
  adbx get-state >/dev/null 2>&1 || { echo '✗ adb 設備不在线（或 TRIME_ADB_SERIAL 設錯）'; exit 1; }
  GENDIR="$(mktemp -d)"; trap 'rm -rf "$GENDIR"' EXIT
  python3 "$ROOT/android/tools/check_trime.py" gen-custom "$GENDIR" 2>/dev/null
  for f in default.custom.yaml luna_pinyin.custom.yaml; do
    adbx push "$GENDIR/$f" "$PHONE_DIR/$f" >/dev/null && echo "  pushed $f (gen)"
  done
  adbx shell "mkdir -p $PHONE_DIR/lua/codelllc09/tools/dict_pipeline"
  manifest | while IFS=$'\t' read -r src dst; do
    adbx push "$ROOT/$src" "$PHONE_DIR/$dst" >/dev/null
    echo "  pushed $dst"
  done
  echo '✓ 推送完成。手機端操作：同文 → 部署 → 主題選「徐碼」→ 配色選「徐碼·宣紙/夜墨」'
  # 內部副本即時同步（2026-11-05 Waydroid 實測：外部存儲模式的 import 不會主動
  # 拉取主題/補丁改動，直接覆寫內部副本可免手動同步；失敗不阻塞，
  # 部署時 Trime 仍會走正常 import 鏈）
  INTERNAL_DIR="${TRIME_INTERNAL_DIR:-/storage/emulated/0/Android/data/com.osfans.trime/files/rime}"
  for f in xuma_L.custom.yaml v1.trime.yaml; do
    adbx push "$ROOT/android/$f" "$INTERNAL_DIR/$f" >/dev/null 2>&1 \
      && echo "  synced → 內部副本 $f" || true
  done
  # 鍵盤字體（key_font 從內部 userDataDir/fonts 讀；與 themes 同批推送）
  adbx shell "mkdir -p $INTERNAL_DIR/fonts" >/dev/null 2>&1
  if [ -d "$ROOT/android/fonts" ]; then
    for f in "$ROOT"/android/fonts/*; do
      [ -f "$f" ] || continue
      adbx push "$f" "$INTERNAL_DIR/fonts/$(basename "$f")" >/dev/null 2>&1 \
        && echo "  synced → 內部副本 fonts/$(basename "$f")" || true
    done
  fi
  # 鍵位圖標（Trime 的 image-valued color 通道從內部 userDataDir 讀 backgrounds/）
  adbx shell "mkdir -p $INTERNAL_DIR/backgrounds" >/dev/null 2>&1
  for f in "$ROOT"/android/backgrounds/*.png; do
    adbx push "$f" "$INTERNAL_DIR/backgrounds/$(basename "$f")" >/dev/null 2>&1 \
      && echo "  synced → 內部副本 backgrounds/$(basename "$f")" || true
  done
  # Trime 會把主題編譯進 build/<theme>.trime.yaml，鍵盤讀的是那份 ——（本主題 configId = v1）
  # 只推文件不生效，必須在 app 內按一次 Deploy（TRIME_NO_DEPLOY=1 可跳過）
  if [ "${TRIME_NO_DEPLOY:-0}" != "1" ]; then
    adbx shell am start -n com.osfans.trime/.ui.main.MainActivity >/dev/null 2>&1 || true
    sleep 4
    # 用 uiautomator 找 Deploy 按鈕的真實座標（版面會隨語言/滾動變化，勿寫死）
    DXY=$(adbx shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; \
           adbx shell cat /sdcard/ui.xml 2>/dev/null \
             | grep -oE 'content-desc="Deploy"[^>]*bounds="\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]"' \
             | grep -oE '\[[0-9]+,[0-9]+\]\[[0-9]+,[0-9]+\]' | head -1)
    if [ -n "$DXY" ]; then
      CX=$(echo "$DXY" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\1 \3/' | awk '{printf "%d", ($1+$2)/2}')
      CY=$(echo "$DXY" | sed -E 's/\[([0-9]+),([0-9]+)\]\[([0-9]+),([0-9]+)\]/\2 \4/' | awk '{printf "%d", ($1+$2)/2}')
      adbx logcat -c >/dev/null 2>&1 || true
      adbx shell input tap "$CX" "$CY" >/dev/null 2>&1 || true
      for _i in $(seq 1 12); do
        sleep 3
        if adbx logcat -d 2>/dev/null | grep -q "tasks ran"; then
          echo "  ✓ 已觸發 app 內部署：$(adbx logcat -d 2>/dev/null | grep -oE '[0-9]+ tasks ran[^\"]*' | tail -1)"
          break
        fi
      done
    else
      echo "  ⚠ 找不到 Deploy 按鈕（請手動部署，或先讓同文主界面在前臺）"
    fi
  fi
  note "$PHONE_DIR" 推送 "同文端部署：manifest $(manifest | md5sum | cut -c1-8)${SER:+ → $SER}"
  ;;

pull-spool)
  command -v adb >/dev/null || { echo '✗ 缺 adb'; exit 1; }
  adbx get-state >/dev/null 2>&1 || { echo '✗ adb 設備不在线（或 TRIME_ADB_SERIAL 設錯）'; exit 1; }
  SPOOL="$DESKTOP_RIME/lua/codelllc09/tools/dict_pipeline/spool_pending.txt"
  TMP="$(mktemp)"
  trap 'rm -f "$TMP"' EXIT
  adbx pull "$PHONE_DIR/lua/codelllc09/tools/dict_pipeline/spool_pending.txt" "$TMP" >/dev/null \
    || { echo '✗ 設備端暫無 spool（先在設備上用 /add 攒詞）'; exit 1; }
  NEW=$(grep -c . "$TMP" || true)
  mkdir -p "$(dirname "$SPOOL")"
  touch "$SPOOL"
  ADDED=$(python3 - "$TMP" "$SPOOL" <<'PY'
import sys
phone, desk = sys.argv[1], sys.argv[2]
seen = {l.strip() for l in open(desk, encoding='utf-8') if l.strip()}
add = []
for l in open(phone, encoding='utf-8'):
    w = l.strip()
    if w and not w.startswith('#') and w not in seen:
        seen.add(w); add.append(w)
with open(desk, 'a', encoding='utf-8') as f:
    for w in add:
        f.write(w + '\n')
print(len(add))
PY
)
  echo "手機暫存 $NEW 詞，新併入 $ADDED 詞（其餘已存在）。"
  echo "後續：桌面 /add 菜單「入庫重跑」，或 wishd.py apply --yes"
  note "$SPOOL" 合併 "同文端 spool 回收：手機 $NEW 詞新併 $ADDED"
  ;;

*)
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
  ;;
esac
