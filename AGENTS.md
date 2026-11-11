# 倉庫協作規則

- 本倉維護通用 Trime 主題、字體、背景、鍵音及配套工具。徐碼·L 手機補丁和配置範例見 [徐碼·L 選裝](extras/xuma-l/README.md)。方案、詞典、Lua 和加詞流程由桌面 Rime 主倉維護。
- 設計、生成、打包與驗證使用 [`trime-theme` 技能](.agents/skills/trime-theme/SKILL.md)。
- [簡體 README](README.md) 為 GitHub 預設版本，[繁體 README](README.zh-Hant.md) 供切換閱讀。更新任一版時同步另一版。
- 版面、鍵位或配色改動先用單檔互動 HTML 並排展示現狀與提案，兩側都呈現短按及長按。按用戶定案實作。
- 依改動選最小驗證，失敗時先查該項。文檔、註釋和行為不變的整理只做靜態檢查。全量測試須由用戶明確要求，包括 `tools/verify.sh` 完整流程、`tools/shots.sh` 全套截圖、全量部署或字典編譯、跨解析度全頁回歸和長時間穩定性測試。
- 保留用戶已有的未提交改動。撤回局部變更時只反向修改對應片段。Python 環境和命令使用 `uv`。
