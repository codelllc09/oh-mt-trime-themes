---
name: trime-theme
description: 為 Oh My Trime Themes 設計、製作或更新 Trime 主題及鍵音，包括並排原型、主題 YAML、離線鍵位指南、配色 PNG，以及按要求在 Waydroid 部署、抽驗和錄影。
---

# 同文主題工作流

依當次要求進入相應階段。靈感需求交付構想，原型需求交付並排稿，已定案的提案直接進入獲授權的實作或驗收。倉庫限制以 [AGENTS.md](../../../AGENTS.md) 為準，鍵位與動作查 [鍵位表](../../../docs/KEYBOARD_MAP.md)。

## 原型

- 優先用 [鍵面渲染工具](../../../tools/render_keyboard.py) 讀取現有主題。將現況與提案放在同一份 HTML，展示主鍵盤、數字頁、短按字面與長按角標。
- 有鍵音時，用同一節奏比較樣音，讓字鍵和回車容易辨認。記住定案的畫面與音效版本，供後續生成。

## 實作

- 新外觀沿用 V1 鍵位。顯示名用 `V2-xxx`，配置 ID 用 `v2-xxx`。在 `rime/theme/sources/` 維護 `*.theme-source.yaml`，生成的 `*.trime.yaml` 放在 `rime/theme/`。優先重用 [V2 生成函式](../../../tools/gen_calculator.py) 的 `inherit_skin`、`skin_keys` 和 `write_theme_assets`。
- 音效沿用定案樣本，按鍵類別寫入 `rime/soundeffect/<id>.sound.yaml`，WAV 放在同名子目錄。獨立 ZIP 以 `soundeffect/` 為根，包含描述檔及其引用的 WAV。取用實錄時保留來源與授權。
- 在 [部署清單](../../../tools/check_trime.py) 納入主題及其資產。用獨立主題清單核對引用、鍵位與音效包，並依 [指南生成步驟](../../../design/README.md#由配置生成的鍵位指南) 更新受影響的配色 PNG。共用鍵位變動時更新 V1 互動指南。交付主題 YAML、配色圖與配套音效包。

## Waydroid 驗收

- 當次要求包含設備部署或錄影時，確認 Waydroid 裝置和現行解析度，只推目標主題清單所需的檔案。選用主題和同名獨立音效，等載入完成，再確認實際鍵面與錄到的鍵音。
- 用同文測試框抽驗徐碼主鍵盤的候選上屏、數字頁的輸入與退格、ABC 返回及回車聲。依現行版式取座標，以 Unicode 碼位核對輸出。範圍與失敗處理見 [測試手冊](../../../docs/TESTING.md)。
- 需要影片時錄製 Android 畫面和內部鍵音，抽看成片兩頁並確認回車聲。逐鍵複核音軌中的疑似漏聲。若無窗錄影在 Wayland 初始化失敗，可只為該次 scrcpy 行程設定 `SDL_VIDEODRIVER=dummy`。
- 回報實測範圍與目前啟用的主題。交付影片時說明成片的音量調整或仍待驗證的項目。
