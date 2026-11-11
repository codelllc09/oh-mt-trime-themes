# 徐碼·L 選裝整合

本節命令從倉庫根目錄執行。複製[配置範例](config.example.yaml)為同目錄的 `config.local.yaml`，填寫 `desktop_dir`、要安裝的 `files` 和 `lua_dirs`。這份本機配置由 Git 忽略。

檔案與 Lua 目錄相對於 `desktop_dir`，沿用其手機端相對路徑。Lua 目錄只收錄直接包含的 `*.lua`。`desktop_dir` 可用絕對路徑、`~` 開頭的路徑，或相對於配置檔的路徑。

`RIME_DESKTOP_DIR` 可覆寫 `desktop_dir`。未填寫的檔案和 Lua 清單沿用範例。

```sh
uv run --with pyyaml ./deploy.sh pkg --xuma
```

將 `dist/tongwen-pkg-*.zip` 整合包解壓到同文的使用者資料夾，再點「部署」並選擇徐碼·L 和所需主題。包內包含[手機方案補丁](xuma_L.custom.yaml)，以及預設只啟用徐碼·L 的 `default.custom.yaml`。如果要保留原有方案清單，保留自己的 `default.custom.yaml`，再把 `xuma_L` 加入 `patch/schema_list`。

USB 推送整套整合會寫入手機的方案清單及朙月拼音補丁。

```sh
TRIME_NO_DEPLOY=1 uv run --with pyyaml ./deploy.sh push --xuma
```

## 手機加詞回桌面

手機 `/add` 收集的詞可用 `uv run --with pyyaml ./deploy.sh pull-spool` 去重並合併到桌面待處理清單。正式入庫仍由桌面 Rime 完成。
