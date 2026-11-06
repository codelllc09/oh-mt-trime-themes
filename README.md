# 徐碼·L 安卓端（同文／Trime）適配

桌面（Linux/ibus）方案在安卓同文輸入法（[Trime](https://github.com/osfans/trime)，≥ v3.3）上的部署與適配。
適配工作在 `feat/tongwen` 分支；本目錄所有「僅手機」文件**不得**放進桌面 ibus 用戶目錄。

## 文件一覽

| 文件 | 作用 | 部署到（手機用戶目錄根部） |
| --- | --- | --- |
| `xuma_L.trime.yaml` | 主題**源檔**（節點級 `__include`，供人編輯） | 原名 |
| `v1.trime.yaml` | 主題**生成物**（`gen-theme` 把源檔與 vendor 深合併後的自包含版，`name: V1`）——手機上加載的是它 | 新 |
| `xuma_L.custom.yaml` | 方案補丁（手機端行爲差異，見文件頭註釋） | 原名 |
| `default.custom.yaml`／`luna_pinyin.custom.yaml` | 個人配置二件（不入庫，用戶裁定 3f5db09；`check_trime.py gen-custom` 在部署時生成） | 原名 |
| `deploy.sh` | 打包 `pkg`／推送 `push`／回採 `pull-spool` | 不部署 |
| `tools/check_trime.py` | 資產校驗＋部署清單唯一來源（`manifest`） | 不部署 |
| `tools/sim_test.py` | 本機安卓模擬測試座（ctypes 直連 librime+lua） | 不部署 |
| `tools/kbmap.py` | 容器/真機鍵盤座標映射輸入工具（測試用） | 不部署 |
| `TESTING.md` | 測試手冊：環境搭建＋矩陣 checklist＋避坑實錄 | 不部署 |

方案本體（schema／詞典／lua）與桌面完全同一份——分支內僅有的 lua 改動都是
「桌面守衛」性質（`mode_hint` 無 XDG 即 no-op；`add_word*` 改用
`rime_api.get_user_data_dir()` 並容錯），桌面行爲不變。

## 部署步驟

```sh
# 方式一：USB（adb）
./deploy.sh push          # 推送 35 件到 /storage/emulated/0/rime
# 方式二：打包後手動拷貝（檔案管理器／網盤）
./deploy.sh pkg           # → tmp/tongwen-pkg-<時間>.zip，解壓到 rime 目錄
```

手機端（Trime App）：
1. 「部署」（重新編譯方案與主題）；
2. 「主題」選 **V1**（即 `v1.trime.yaml`）；「配色」選 **徐碼·雲白** 或 **徐碼·墨空**（暗黑模式自動聯動）；
   ⚠ **首次安裝或 `pm clear` 後，Trime 默認主題是內建的「預設」**（因為它的 configId 是 `trime`），
   必須手動到「地球鍵長按 → 主題選單 → V1」切換一次；之後會記住。
3. 選中方案「徐碼·L」開始使用。

詞典較大（xuma_L 2.9M＋hanyu 1.7M），首次部署約需十餘秒；
stroke／luna_pinyin／essay 用 Trime 內建共享數據，無需自帶。

## 鍵位速查（徐碼鍵盤）

| 操作 | 手機鍵位 |
| --- | --- |
| 字根提示 | 每個字母鍵下方 hint（與方案 preedit 顯示同源） |
| 次選／三選 | 直接點候選；或 `,` `.` 鍵（空碼時是標點） |
| 反查（拼音＋筆畫） | 長按 **z** → `` ` ``，如 `` `li ``（聲調 `` `li, ``）`` `li/hs ``（筆畫）`` `li,/hs ``（聲調∩筆畫） |
| 全拼反查 | `` `p `` 前綴（手機補丁放行小寫；桌面仍 `` `P ``） |
| 筆畫反查 | `` `b `` 前綴（同上） |
| 碼位反查 | 長按 **u** →「碼」（發 `Shift+u` 進大寫 U 通道）；或 `u`＋數字起頭（補丁通道） |
| 符號組／金額大寫 | `/` 鍵 → `/xx`、`/dx123`；時間日期 `/time` `/date` |
| 設定菜單 | `/menu`（數字行選）——詞長/註解/簡繁/字符集/非簡/標點全在 |
| 加詞採集 | `/add`（數字行選；spool 在手機攢着） |
| 方案選單（F4 原生） | 長按 **中/EN** 鍵 |
| 中西切換 | **中/EN** 鍵（Mode_switch）或 Shift 鍵 |

> `/menu`、`/add` 的菜單**必須用數字行選**：Trime 點擊候選走 `SelectCandidate`
> API，會把菜單文字當普通詞上屏，旁路了 lua 按鍵處理器——這是數字行常駐的原因。

## 手機 → 桌面加詞閉環

手機 `/add` 的詞攢在手機 `lua/codelllc09/tools/dict_pipeline/spool_pending.txt`
（`deploy.sh pkg/push` 已建好目錄）。回桌面後：

```sh
./deploy.sh pull-spool    # 去重合併進桌面主工作樹 spool_pending.txt
# 然後桌面 /add 菜單「入庫重跑」，或 wishd.py apply --yes
```

手機端 `/add` 菜單裏的「入庫重跑」會提示無腳本（管道只在桌面倉庫），屬預期。

## 真機驗收清單（驗證通過後方可合併回主線）

真機前先跑本機模擬（見下節）：12 項裏引擎側已在沙箱驗過，真機重點收斂到
Trime 前端（渲染、鍵值轉換、點擊行爲）與整機穩定性。

| # | 項目 | 預期 |
| --- | --- | --- |
| 1 | 部署＋選主題 | 無報錯；鍵盤爲徐碼 36 鍵（數字行＋字根 hint） |
| 2 | 常規打字 | 候選＋註解正常；preedit 顯示字根；四碼上屏 |
| 3 | 中西切換 | 進方案默認中文；中/EN 鍵切換生效 |
| 4 | 詞長檔位 | `/menu` → 詞長，四檔切換即時生效 |
| 5 | 非簡模式 | `/menu` → 非簡，簡形候選消失／俗字單字放行 |
| 6 | 簡繁轉換 | `/menu` → 簡繁（simplifier 走 Trime 內建 OpenCC） |
| 7 | 反查 | 長按 z → `` `li `` 出拼音反查；`` `li,hs `` 組合反查帶徐碼全碼註釋 |
| 8 | 碼位反查 | 長按 u 打十六進制出字；若無效，改用 `u6c5f` 小寫通道並回報 |
| 9 | `/add` | 數字選鍵收錄；重啓同文後 spool 仍在 |
| 10 | `/time` `/dx123` | 動態時間／金額大寫候選正常 |
| 11 | 配色 | 宣紙/夜墨切換；系統暗黑模式自動聯動 |
| 12 | 穩定性 | 連續輸入十分鐘無崩潰（lua 全量在 Trime 的 librime-lua 上運行） |

## 本機安卓模擬測試（真機前的前置驗證）

```sh
python3 tools/sim_test.py        # 全綠即引擎側就緒（約 1 分鐘，含部署）
```

原理：Trime 引擎＝librime＋librime-lua（Fedora ibus-rime 同源同版本族），
沙箱用戶目錄＝deploy.sh 同款清單，進程剝離 HOME／XDG_* 逼出「安卓無 XDG」
路徑。覆蓋：部署零錯（含 lua 全量加載）、進方案默認中文、打字＋字根 preedit、
42 碼驗收基準動態回歸、/menu /add 數字選鍵（spool 落沙箱）、`p ` `b 反查、
`li/hs 組合反查、u6c5f 與 Shift+u 雙碼位通道、OpenCC 簡繁、
主題 `__include` 真實編譯（Trime 同款 deploy_config_file）。

不覆蓋（真機重點）：鍵盤渲染與配色、`send: "Shift+u"` 的 Trime 鍵值轉換
（沙箱已驗 librime 側接受該鍵事件）、候選點擊、性能與長時間穩定性。

本座曾抓住的真機坑：luna_pinyin.extended 不編譯（反查全滅，靠手機版
luna_pinyin.custom.yaml 解）；`u` 單字與碼位反查引導衝突（u+數字通道規避）。

## 手機端使用須知與已知限制

- `helper/`（`help/`）、`env/` 等桌面彩蛋依賴實體鍵盤習慣，手機可用但不順手；
  `mode_hint`（WezTerm 徽標）在安卓自動 no-op，零開銷；
- 碼位反查 `u`＋數字通道查不了 a–f 開頭的碼位（避讓徐碼編碼空間的代價），
  詳見 `xuma_L.custom.yaml` 頭註釋；
- `U` 大寫通道（長按 u）依賴 Trime 對 `send: Shift+u` 的鍵值轉換，
  待清單第 8 項實測；失敗不影響其他功能。
- 詞頻管道、`wishd`、鏡像備份等倉庫工具鏈不部署到手機；
  手機端僅消費詞典產物與採集 spool。

## 本倉邊界（雙根架構）

本倉**只負責同文（Trime）主題與 UI 資產**；方案、詞典、lua 全部跟隨桌面主倉：

| 根 | 內容 | 位置 |
|---|---|---|
| 本倉 | trime 主題（`xuma_L.trime.yaml` 源檔 / `v1.trime.yaml` 生成物）、補丁、字體、背景、工具、文檔 | `~/Work/rime-tongwen` |
| 桌面主倉 | `xuma_L.schema.yaml`、`xuma_L.dict.yaml`、`lua/**`、台賬、spool 管道 | `RIME_DESKTOP_DIR`（默認 `~/.config/ibus/rime`）|

**含義**：本倉不能單獨部署——沒有主倉就沒有方案與詞典。改 lua／schema 請回主倉。

## CI

`.github/workflows/gate.yml` 在 push／PR 上跑：

1. `tools/check_trime.py`（**無主倉模式**：依賴 schema 的校驗自動 SKIP）；
2. `gen-theme --check`（自包含主題與源檔無漂移）；
3. `tools/aesthetics.py`（配色對比 WCAG）。

真機側（`deploy.sh push`、`verify.sh`、`shots.sh`）需要 adb 與 Waydroid，不在 CI 跑。

## 工作方式

- **設計類改動（版面／鍵位／配色）先出可互動 HTML 示意圖**，放 `design-refs/`，
  經選定再改主題；理由與做法見 `design-refs/README.md` 的「設計流程規約」。
- 改主題後跑 `tools/check_trime.py gen-theme` 生成自包含 `v1.trime.yaml`，
  再 `./deploy.sh push`；驗證按改動風險選檔次（見 `TESTING.md`）。
