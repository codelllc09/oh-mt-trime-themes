#!/usr/bin/env bash
# 供截圖和驗證工具解析 ADB 目標。

trime_adb_serial() {
    if [[ -n ${TRIME_ADB_SERIAL:-} ]]; then
        printf '%s\n' "$TRIME_ADB_SERIAL"
        return
    fi

    local status address
    if status=$(LC_ALL=C waydroid status 2>/dev/null); then
        address=$(awk '$1 == "IP" && $2 == "address:" && $3 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/ {
            print $3
            exit
        }' <<< "$status")
        if [[ -n $address ]]; then
            printf '%s:5555\n' "$address"
            return
        fi
    fi

    printf '%s\n' '找不到 Waydroid 位址。請啟動 Waydroid 或以 TRIME_ADB_SERIAL 指定 ADB 裝置。' >&2
    return 1
}
