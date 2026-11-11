#!/usr/bin/env bash
# deploy.sh —— 同文（Trime）端部署與回採
#
#   ./deploy.sh pkg [--theme v1 | --xuma]   # 生成 ZIP 到 dist/
#   ./deploy.sh push [--theme v1 | --xuma]  # 透過 adb 推送
#   ./deploy.sh pull-spool                 # 回收徐碼·L 的手機加詞
# pkg / push 預設包含全部主題。--theme 選單款，--xuma 另含徐碼·L 方案。

set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CHECK="$ROOT/tools/check_trime.py"
PHONE_DIR="${TRIME_PHONE_DIR:-/storage/emulated/0/rime}"
# 多目標支持（2026-11-05）：USB 真機默認；設 TRIME_ADB_SERIAL 指向 Waydroid 容器
# （如 localhost:5555）或網絡 adb 設備，例：
#   TRIME_ADB_SERIAL=localhost:5555 ./deploy.sh push
SER="${TRIME_ADB_SERIAL:-}"
adbx() { if [ -n "$SER" ]; then adb -s "$SER" "$@"; else adb "$@"; fi; }

note() {  # _ledger 台賬（寫盤留痕；失敗不阻塞但會打印）
  python3 "$RIME_DESKTOP_DIR/lua/codelllc09/tools/_ledger.py" "$1" "$2" "$3" || echo "[!] 台賬寫入失敗（不阻塞）" >&2
}

make_phone_dirs() {
  local root=$1 manifest=$2 folder quoted
  local -a dirs=("$root")
  while IFS= read -r folder; do
    dirs+=("$root/$folder")
  done < <(cut -f 2 <<< "$manifest" | sed -n 's|/[^/]*$||p' | sort -u)
  printf -v quoted " '%s'" "${dirs[@]//\'/\'\\\'\'}"
  adbx shell "mkdir -p$quoted"
}

usage() {
  sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'
}

ACTION=${1:-}
if (($#)); then shift; fi
XUMA=0
if [[ "$ACTION" == pkg || "$ACTION" == push ]]; then
  case "$#:${1:-}" in
    0:|2:--theme) ;;
    1:--xuma) XUMA=1 ;;
    1:--help|1:-h) usage; exit 0 ;;
    *) usage >&2; exit 1 ;;
  esac
fi

if ((XUMA)) || [[ "$ACTION" == pull-spool ]]; then
  RIME_DESKTOP_DIR=$(python3 "$CHECK" xuma-desktop-dir)
  export RIME_DESKTOP_DIR
fi

case "$ACTION" in
pkg)
  python3 "$CHECK" gen-theme --check
  NAME=trime-themes
  if ((XUMA)); then
    NAME=tongwen-pkg
  elif [[ $# == 2 && $1 == --theme && $2 =~ ^[a-z0-9-]+$ ]]; then
    NAME="trime-$2"
  fi
  mkdir -p "$ROOT/dist"
  ZIP="$ROOT/dist/$NAME-$(date +%Y%m%d-%H%M%S).zip"
  PACKAGE=$(python3 "$CHECK" package "$ZIP" "$@")
  IFS=$'\t' read -r count fingerprint <<< "$PACKAGE"
  echo "已打包並校驗：$ZIP（$count 件）"
  if ((XUMA)); then
    note "$ZIP" 生成 "同文端部署包：manifest $fingerprint 共 $count 件"
  fi
  ;;

push)
  command -v adb >/dev/null || { echo '✗ 缺 adb（android-tools 或 scrcpy 附帶）'; exit 1; }
  adbx get-state >/dev/null 2>&1 || { echo '✗ adb 設備不在線（或 TRIME_ADB_SERIAL 設錯）'; exit 1; }
  MANIFEST=$(python3 "$CHECK" manifest "$@")
  make_phone_dirs "$PHONE_DIR" "$MANIFEST"
  if ((XUMA)); then
    GENDIR="$(mktemp -d)"
    trap 'rm -rf "$GENDIR"' EXIT
    python3 "$CHECK" gen-custom "$GENDIR" 2>/dev/null
    for f in default.custom.yaml luna_pinyin.custom.yaml; do
      adbx push "$GENDIR/$f" "$PHONE_DIR/$f" >/dev/null && echo "  pushed $f (gen)"
    done
  fi
  while IFS=$'\t' read -r src dst; do
    if [[ "$src" != /* ]]; then src="$ROOT/$src"; fi
    source_file=$(realpath -e -- "$src")
    adbx push "$source_file" "$PHONE_DIR/$dst" >/dev/null
    echo "  pushed $dst"
  done <<< "$MANIFEST"
  echo '✓ 推送完成。手機端操作：同文 → 部署 → 選擇主題。V2 鍵音另在「虛擬鍵盤」設定選擇。'
  # 內部副本即時同步。失敗時，Trime 仍可走正常匯入流程。
  INTERNAL_DIR="${TRIME_INTERNAL_DIR:-/storage/emulated/0/Android/data/com.osfans.trime/files/rime}"
  if [[ "$INTERNAL_DIR" != "$PHONE_DIR" ]]; then
    UI_MANIFEST=$(awk -F '\t' '$2 ~ /^(fonts|backgrounds|soundeffect)\// || $2 ~ /(\.trime\.yaml|^xuma_L\.custom\.yaml)$/' <<< "$MANIFEST")
    make_phone_dirs "$INTERNAL_DIR" "$UI_MANIFEST" >/dev/null 2>&1 || true
    while IFS=$'\t' read -r src dst; do
      if [[ "$src" != /* ]]; then src="$ROOT/$src"; fi
      adbx push "$src" "$INTERNAL_DIR/$dst" >/dev/null 2>&1 \
        && echo "  synced → 內部副本 $dst" || true
    done <<< "$UI_MANIFEST"
  fi
  # Trime 也維護 build/<theme>.trime.yaml；與方案一起推送時按原流程部署。
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
  if ((XUMA)); then
    note "$PHONE_DIR" 推送 "同文端部署：manifest $(printf '%s\n' "$MANIFEST" | md5sum | cut -c1-8)${SER:+ → $SER}"
  fi
  ;;

pull-spool)
  command -v adb >/dev/null || { echo '✗ 缺 adb'; exit 1; }
  adbx get-state >/dev/null 2>&1 || { echo '✗ adb 設備不在线（或 TRIME_ADB_SERIAL 設錯）'; exit 1; }
  SPOOL="$RIME_DESKTOP_DIR/lua/codelllc09/tools/dict_pipeline/spool_pending.txt"
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
  usage >&2
  exit 1
  ;;
esac
