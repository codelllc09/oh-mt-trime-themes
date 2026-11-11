---
name: trime-theme
description: 設計、維護或排查同文（Trime）鍵盤主題與鍵音，涵蓋鍵位、配色、字體、生成、打包和實機驗證。
---

# 同文主題工作流

遵循[倉庫規則](../../../AGENTS.md)，以[現行鍵位表](../../../docs/KEYBOARD_MAP.md)和主題配置為基準。

- **原型**　由現行配置渲染受影響的頁面，並排比較短按和長按。比較鍵音時用相同節奏，保留定案畫面和樣音。[原型步驟](references/build.md#原型)
- **實作**　編輯 `rime/theme/sources/` 的源檔，共用鍵位先重建 V1，再重建受影響的 V2。安裝用的 `*.trime.yaml` 在 `rime/theme/`。只有字符集、字形來源或字重改變才重建字體。鍵面尺寸或比例有變動時，只重建受影響的圖片。[生成步驟](references/build.md#重建主題)
- **同步**　更新受影響的鍵位表條目及配色 PNG。共用鍵位變動時同步 `keyboard-guide.html`。[指南生成](references/build.md#更新鍵位指南)
- **打包**　以 `tools/check_trime.py manifest` 核對安裝檔與手機端路徑。發佈時一併產出完整包與各款安裝包。[安裝包](references/build.md#安裝包)
- **驗證**　依改動選擇靜態校驗或實機抽驗。用現行版式與尺寸定位，讀 Unicode 碼位核對輸出，用截圖檢查外觀。回報實測主題、鍵音、範圍與待驗項目。[驗證與部署](references/device.md)

遇到具體問題時查[故障經驗](references/lessons.md)的相關段落。[配置與按鍵動作](references/lessons.md#配置與按鍵動作) · [配色、字體與圖像](references/lessons.md#配色字體與圖像) · [鍵音](references/lessons.md#鍵音) · [設備驗證](references/lessons.md#設備驗證)

將可跨主題重用的故障成因與處理方式補入故障經驗。
