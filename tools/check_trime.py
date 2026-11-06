#!/usr/bin/env python3
# check_trime.py —— 同文（Trime）端適配資產校驗器（只讀，不寫盤）
#
# 職責：
#   1. 本倉 *.yaml 語法與結構校驗（主題鍵盤/配色/補丁路徑/方案表）；
#   2. 主題字根 hint 與方案 speller/preedit_format 的 xlit 映射逐鍵對賬；
#   3. 輸出部署清單（manifest 子命令，deploy.sh 的唯一來源）。
#   4. 生成自包含主題 v1.trime.yaml（gen-theme 子命令；源＝vendor/trime-3.3.13.yaml
#      ＋ xuma_L.trime.yaml 深合併，__include 全部展開——避免手工產物過期）。
#
# 設計：零依賴（標準庫 yaml 除外——本倉 pyproject 已依賴 PyYAML）；
#       gen-theme 寫盤僅寫 v1.trime.yaml（生成物，不須人讀台賬）。
# 用法：
#   python3 tools/check_trime.py            # 全部校驗，非零退出即敗
#   python3 tools/check_trime.py manifest   # 輸出 TSV：源路徑<TAB>手機目標路徑
#   python3 tools/check_trime.py gen-theme  # 重生成 android/v1.trime.yaml
#                                                   # （--check 只比對漂移，不寫盤）

import re
import os
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent          # tools/
ANDROID = HERE.parent                            # 本倉根（安卓資產；原 android/）
# 共享件根（schema/詞典/lua/台賬）＝桌面主倉；獨立成倉後經 RIME_DESKTOP_DIR 指引（2026-11-07）
REPO = Path(os.environ.get('RIME_DESKTOP_DIR', str(Path.home() / '.config/ibus/rime'))).expanduser()

# ── Trime v3.3.13 默認主題（assets/shared/trime.yaml）preset_keys 名單 ──
# 來源：https://github.com/osfans/trime/blob/v3.3.13/app/src/main/assets/shared/trime.yaml
# 用途：主題鍵盤引用的功能鍵必須在此 ∪ 主題自定義 preset_keys 內。
TRIME_PRESET_KEYS = {
    'BRIGHTNESS_DOWN', 'BRIGHTNESS_UP', 'BackSpace', 'BackToPreviousSyllable',
    'Baidu', 'CALCULATOR', 'CALENDAR', 'CONTACTS', 'Candidate_switch',
    'Charset_switch', 'ChineseDate', 'Clear', 'Color_settings', 'Color_switch',
    'Comment_switch', 'CommitComment', 'CommitHomepage', 'CommitRawInput',
    'CommitScriptText', 'Date', 'Delete', 'DeleteCandidate', 'Deploy', 'Down',
    'ENVELOPE', 'EXPLORER', 'End', 'Escape', 'F4', 'Google', 'Help', 'Henkan',
    'Hide', 'Hint_switch', 'Home', 'Homepage', 'IME_last', 'IME_next',
    'IME_switch', 'Info', 'Insert', 'Keyboard_default', 'Keyboard_letter',
    'Keyboard_mini', 'Keyboard_number', 'Keyboard_switch', 'Keyboard_symbols',
    'Left', 'MUSIC', 'Menu', 'Mode_switch', 'MoeDict', 'POWER', 'Page_Down',
    'Page_Up', 'Punct_switch', 'RepeatCommit', 'Return', 'Return1', 'Return2',
    'Right', 'SEARCH', 'SLEEP', 'Schema_settings', 'Schema_switch', 'Search',
    'Settings', 'Share', 'Shift_L', 'Sync', 'Theme_settings', 'Time',
    'TrimeApp', 'TrimeCmp', 'Up', 'VOICE_ASSIST', 'VOLUME_DOWN', 'VOLUME_MUTE',
    'VOLUME_UP', 'WebSearch', 'Wiki', 'Zdic', 'Zdic2', 'Zenkaku_Hankaku',
    'clipboard_window', 'copy', 'copy_all', 'cut', 'cut_all',
    'liquid_keyboard_emoji', 'liquid_keyboard_exit', 'liquid_keyboard_switch',
    'one_hand_switch_1', 'one_hand_switch_2', 'one_hand_switch_3', 'paste',
    'paste_text', 'redo', 'select_all', 'set_color_ink', 'set_theme_ink',
    'share_text', 'space', 'space1', 'undo', 'updateConfig',
}

# 主題按鍵裏引用其他鍵的屬性（值爲功能鍵名而非字符）
KEYREF_ATTRS = ('click', 'long_click', 'composing', 'has_menu', 'paging',
                'swipe_up', 'swipe_down', 'swipe_left', 'swipe_right', 'ascii')

NAMED_COLORS = {'red', 'green', 'blue', 'black', 'white', 'gray', 'grey',
                'cyan', 'magenta', 'yellow', 'lightgray', 'darkgray',
                'transparent'}

FAIL, WARN = [], []


def item(ok, msg):
    tag = '[✓]' if ok else '[✗]'
    print(f'  {tag} {msg}')
    if not ok:
        FAIL.append(msg)


def warn(msg):
    print(f'  [!] {msg}')
    WARN.append(msg)


def load_yaml(p: Path):
    with open(p, encoding='utf-8') as f:
        return yaml.safe_load(f)


# ── 解析方案 xlit 字根映射（A→糸 …），與主題 hint 對賬 ──
def parse_schema_xlit(schema: dict):
    """返回 {小寫字母: 字根}；取 translator/preedit_format 裏的 xlit 行。"""
    fmts = (schema.get('translator') or {}).get('preedit_format') or []
    for rule in fmts:
        m = re.match(r'\s*xlit\|([^|]+)\|([^|]+)\|?\s*$', str(rule))
        if m:
            src, dst = m.group(1), m.group(2)
            if len(src) == len(dst):
                return {src[i].lower(): dst[i] for i in range(len(src))}
    return None


def resolve_schema_path(schema: dict, path: str):
    """按 rime patch 路徑語法（a/b/@0/c）在 schema 樹中定位；返回是否存在。"""
    node = schema
    for part in path.split('/'):
        if not part:
            continue
        m = re.fullmatch(r'@(\d+)', part)
        if m:
            if not isinstance(node, list) or int(m.group(1)) >= len(node):
                return False
            node = node[int(m.group(1))]
        else:
            if not isinstance(node, dict) or part not in node:
                return False
            node = node[part]
    return True


def check_theme(theme: dict, schema: dict):
    print('主題 xuma_L.trime.yaml：')
    item(theme.get('config_version') == '3.0', 'config_version 爲 "3.0"（Trime ≥3.3 格式）')
    kb = (theme.get('preset_keyboards') or {})
    item('xuma_L' in kb, "preset_keyboards 含 xuma_L（schema_id 同名自動匹配）")

    xk = kb.get('xuma_L') or {}
    default_w = xk.get('width', 10)
    # 行寬合計：keys 順序累積，寬滿 100 換行（Trime 佈局算法）
    row, rows = 0.0, []
    for k in xk.get('keys') or []:
        w = float(k.get('width', default_w))
        row += w
        if row >= 100 - 1e-6:
            rows.append(round(row, 4))
            row = 0.0
    if row > 0:
        rows.append(round(row, 4))
    item(all(abs(r - 100) < 0.6 for r in rows),
         f'鍵盤每行寬度合計≈100（實際 {rows}）')

    # 功能鍵引用閉合
    custom_keys = set((theme.get('preset_keys') or {})) - {'__include'}
    known = TRIME_PRESET_KEYS | custom_keys
    bad = []
    for k in xk.get('keys') or []:
        for attr in KEYREF_ATTRS:
            v = k.get(attr)
            if isinstance(v, str) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', v):
                if v not in known and len(v) > 1:
                    bad.append(f'{attr}={v}')
    item(not bad, f'功能鍵引用全部存在（自定義 {sorted(custom_keys)}）' +
         ('' if not bad else f'；未知引用 {bad}'))

    # 字根 hint 對賬（v2 主題已去字根——僅當設有 hint 時才校驗一致性）
    xlit = parse_schema_xlit(schema)
    item(xlit is not None, '方案 translator/preedit_format 解析出 xlit 字根映射')
    if xlit:
        hints = {}
        for k in xk.get('keys') or []:
            c = k.get('click')
            if isinstance(c, str) and re.fullmatch(r'[a-z]', c):
                hints[c] = str(k.get('hint', ''))
        have = {l: v for l, v in hints.items() if v}
        wrong = [f'{l}:{have[l]}≠{xlit[l]}' for l in have
                 if have[l] != xlit[l]]
        item(not wrong,
             f'字根 hint：{len(have)}/26 鍵設有' + ('（全部與方案 xlit 一致）' if have else '（無字根主題，跳過對賬）')
             + (f'；錯 {wrong}' if wrong else ''))

    # 配色
    # PreeditDelegate 必須鍵：缺 text_color 鍵盤彈出即崩（實錄 2026-11-06）
    for sid in ('xuma_cloud', 'xuma_night'):
        s0 = (theme.get('preset_color_schemes') or {}).get(sid) or {}
        item('text_color' in s0, f'配色 {sid} 含 text_color（PreeditDelegate 必須）')
        item('text_back_color' in s0, f'配色 {sid} 含 text_back_color')

    schemes = (theme.get('preset_color_schemes') or {})
    local = {k: v for k, v in schemes.items() if k != '__include'}
    cs = (theme.get('style') or {}).get('color_scheme')
    if cs and cs.startswith('xuma_'):
        item(cs in local, f'style/color_scheme={cs} 已定義')
    for sid, sc in local.items():
        for ref in ('dark_scheme', 'light_scheme'):
            if ref in (sc or {}):
                item(sc[ref] in local, f'配色 {sid} 的 {ref}→{sc[ref]} 已定義')
    color_bad = []
    for sid, sc in local.items():
        for key, val in (sc or {}).items():
            if key in ('name', 'author', 'dark_scheme', 'light_scheme', 'sound'):
                continue
            v = str(val)
            ok = (re.fullmatch(r'0x[0-9A-Fa-f]{2,8}', v)
                  or re.fullmatch(r'#[0-9A-Fa-f]{6,8}', v)
                  or v in NAMED_COLORS
                  or re.fullmatch(r'[a-z_]+', v)   # 顏色標籤引用（fallback_colors 鍵名）
                  or re.fullmatch(r'[A-Za-z0-9_.-]+\.(png|webp|jpg|gif)', v)  # 圖片值（image-valued color）
                  or (isinstance(val, int) and 0 <= val <= 0xFFFFFFFF))  # YAML 1.1 十六進制 int（Trime 支持）
            if not ok:
                color_bad.append(f'{sid}/{key}={v}')
    item(not color_bad, '配色值格式合法（0xAARRGGBB/#RRGGBB/命名色/標籤引用）'
         + (f'；非法 {color_bad}' if color_bad else ''))


def check_custom(custom: dict, schema: dict):
    print('補丁 xuma_L.custom.yaml：')
    item(isinstance(custom.get('patch'), dict) and custom['patch'],
         'patch 節點存在且非空')
    for path in (custom.get('patch') or {}):
        item(resolve_schema_path(schema, path), f'補丁路徑存在：{path}')


def check_default():
    print('生成配置（GEN_CUSTOM，部署時產出）：')
    d = yaml.safe_load(GEN_CUSTOM['default.custom.yaml'])
    item(isinstance(d.get('patch'), dict) and d['patch'], 'default.custom.yaml 語法與 patch ✓')
    l = yaml.safe_load(GEN_CUSTOM['luna_pinyin.custom.yaml'])
    item((l.get('patch') or {}).get('translator/dictionary') == 'luna_pinyin.extended',
         'luna_pinyin.custom.yaml 指向 extended ✓')
    for ent in d['patch']['schema_list']:
        sid = ent.get('schema')
        item((REPO / f'{sid}.schema.yaml').exists(), f'方案檔案存在：{sid}.schema.yaml')
    item(d['patch']['menu/page_size'] == 7,
         'menu/page_size=7（/add /menu 二級菜單防翻頁錯位）')


# 個人配置二件（2026-11-05 用戶裁定「個人數據不入庫」，3f5db09 退庫）：
# 內容由本檔 GEN_CUSTOM 單一來源持有，gen-custom 子命令產出檔案——
# 倉庫不存在 custom.yaml 形態，部署鏈不斷。
GEN_CUSTOM = {
    # 同文端方案表：僅徐碼；page_size 7 防 /add /menu 二級菜單翻頁選鍵錯位
    'default.custom.yaml': '''\
# default.custom.yaml —— 同文（Trime）端方案表（gen-custom 生成）
# encoding: utf-8
patch:
  schema_list:
    - schema: xuma_L
  menu/page_size: 7
''',
    # 觸發 luna_pinyin.extended 詞典編譯：librime 只編被方案引用的詞典，
    # 缺它則混輸與 `p 反查 / `li/hs 組合反查靜默無候選（sim_test 實測復現）
    'luna_pinyin.custom.yaml': '''\
# luna_pinyin.custom.yaml —— 同文（Trime）端朙月拼音補丁（gen-custom 生成）
# encoding: utf-8
patch:
  translator/dictionary: luna_pinyin.extended
''',
}


def gen_custom(dst_dir):
    """產出個人配置二件到指定目錄（deploy.sh pkg/push 與 sim_test 沙箱消費）。"""
    dst = Path(dst_dir)
    for name, text in GEN_CUSTOM.items():
        (dst / name).write_text(text, encoding='utf-8')
        print(f'generated {name}', file=sys.stderr)


# ── 部署清單（deploy.sh 的唯一來源）──
def lua_runtime_files():
    files = []
    for p in sorted((REPO / 'lua' / 'codelllc09').glob('*.lua')):
        files.append(p)
    for sub in ('', 'lib'):
        d = REPO / 'lua' / 'ace' / sub
        if d.is_dir():
            files += sorted(d.glob('*.lua'))
    return files


def _deep_merge(base, over):
    """Rime 風格的 map 深合併：over 的純量/序列覆蓋 base，map 逐鍵遞歸。"""
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _deep_merge(base[k], v) if k in base else v
        return out
    return over


def _resolve_includes(node, base, root=None):
    """展開 __include：`trime:/path` 指 vendor 主題，`/path` 指本文檔根（Rime 語義）。

    以目標節點為底，同層其餘鍵覆蓋其上（Rime 的 map 語義）。
    """
    root = base if root is None else root
    if isinstance(node, list):
        return [_resolve_includes(x, base, root) for x in node]
    if not isinstance(node, dict):
        return node
    if '__include' not in node:
        return {k: _resolve_includes(v, base, root) for k, v in node.items()}

    ref = node['__include']
    if not isinstance(ref, str) or not (ref.startswith('trime:/') or ref.startswith('/')):
        raise SystemExit(f'[✗] 不支持的 __include：{ref!r}（僅支持 trime:/path 與 /path）')
    if ref.startswith('trime:/'):
        anchor, path, sub_root = base, ref[len('trime:/'):].split('/'), base
    else:
        anchor, path, sub_root = root, ref[1:].split('/'), root
    for seg in path:
        if not isinstance(anchor, dict) or seg not in anchor:
            raise SystemExit(f'[✗] __include 目標不存在：{ref}')
        anchor = anchor[seg]
    siblings = {k: _resolve_includes(v, base, root) for k, v in node.items() if k != '__include'}
    return _deep_merge(_resolve_includes(anchor, base, sub_root), siblings)


def _stringify_colors(node):
    """把所有數值形態的顏色轉成字符串（Trime parseColor 只認 #/0x 前綴）。

    vendor 官方主題的配色全是 0xAARRGGBB 整數；Trime 構建 schemeColors 時只收
    字符串條目，整數值被丟棄 → parseColor 得到 Value.None → PreeditDelegate
    構造即崩（2026-11-05 實測：'text_color' is not a color）。故生成時全量字符串化。
    """
    if isinstance(node, dict):
        return {k: _stringify_colors(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_stringify_colors(x) for x in node]
    if isinstance(node, int) and not isinstance(node, bool):
        return f'#{node:08X}' if node > 0xFFFFFF else f'#{node:06X}'
    return node


def gen_theme(target: Path = ANDROID / 'v1.trime.yaml', check: bool = False) -> bool:
    """生成自包含主題：vendor 官方主題 ← xuma_L.trime.yaml 深合併（__include 展開）。

    pm clear 後空 prefs 默認加載的就是這份檔案；它必須跟隨 xuma_L.trime.yaml 更新，
    否則主題改動只在「手動選徐碼主題」時生效（2026-11-06 實測坑）。
    """
    base = load_yaml(ANDROID / 'vendor' / 'trime-3.3.13.yaml')
    ours = load_yaml(ANDROID / 'xuma_L.trime.yaml')
    merged = _deep_merge(base, _resolve_includes(ours, base, ours))
    # 只對配色區做字符串化：尺寸/座標等數值鍵必須保持數值（38 變成 '#000026' 曾踩過）
    merged['preset_color_schemes'] = _stringify_colors(merged['preset_color_schemes'])
    text = yaml.safe_dump(merged, allow_unicode=True, sort_keys=True, width=4096)

    if check:
        cur = target.read_text(encoding='utf-8') if target.exists() else ''
        if cur != text:
            print(f'[✗] {target.name} 與生成結果不一致（陳舊）：請跑 gen-theme', file=sys.stderr)
            return False
        print(f'  [✓] {target.name} 與 xuma_L.trime.yaml 同步（無漂移）')
        return True

    target.write_text(text, encoding='utf-8')
    print(f'  [✓] 已生成 {target.name}（{len(text)} 字節）')
    return True


def manifest():
    """輸出 TSV：倉庫相對源路徑 <TAB> 手機用戶目錄相對目標路徑。"""
    pairs = [
        ('xuma_L.schema.yaml', 'xuma_L.schema.yaml'),
        ('xuma_L.dict.yaml', 'xuma_L.dict.yaml'),
        ('xuma_spelling_pseudo.schema.yaml', 'xuma_spelling_pseudo.schema.yaml'),
        ('xuma_spelling_pseudo.dict.yaml', 'xuma_spelling_pseudo.dict.yaml'),
        ('luna_pinyin.extended.dict.yaml', 'luna_pinyin.extended.dict.yaml'),
        ('luna_pinyin.hanyu.dict.yaml', 'luna_pinyin.hanyu.dict.yaml'),
        ('symbols.yaml', 'symbols.yaml'),
        ('xuma_L.custom.yaml', 'xuma_L.custom.yaml'),
        ('backgrounds/globe_light.png', 'backgrounds/globe_light.png'),
        ('backgrounds/globe_dark.png', 'backgrounds/globe_dark.png'),
        ('fonts/xuma_key.otf', 'fonts/xuma_key.otf'),
        ('fonts/xuma_latin.ttf', 'fonts/xuma_latin.ttf'),
        ('v1.trime.yaml', 'v1.trime.yaml'),   # 自包含主題（獨立 configId，不與內建「預設」撞名）
                                                #  補齊 text_color 等必須鍵，修 PreeditDelegate 崩潰）
    ]
    for p in lua_runtime_files():
        pairs.append((str(p.relative_to(REPO)), str(p.relative_to(REPO))))
    out = []
    for src, dst in pairs:
        if not (REPO / src).exists() and not (ANDROID / src).exists():
            print(f'[✗] 清單源缺失（主倉與本倉皆無）：{src}', file=sys.stderr)
            sys.exit(1)
        out.append(f'{src}\t{dst}')
    print('\n'.join(out))


def main():
    if len(sys.argv) > 2 and sys.argv[1] == 'gen-custom':
        gen_custom(sys.argv[2])
        return
    if len(sys.argv) > 1 and sys.argv[1] == 'gen-theme':
        ok = gen_theme(check='--check' in sys.argv)
        sys.exit(0 if ok else 1)
    if len(sys.argv) > 1 and sys.argv[1] == 'manifest':
        manifest()
        return
    print('── android 資產校驗 ──')
    theme = load_yaml(ANDROID / 'xuma_L.trime.yaml')
    custom = load_yaml(ANDROID / 'xuma_L.custom.yaml')
    schema = load_yaml(REPO / 'xuma_L.schema.yaml')

    for p in ('xuma_L.trime.yaml', 'xuma_L.custom.yaml'):
        try:
            load_yaml(ANDROID / p)
            print(f'  [✓] YAML 語法：{p}')
        except yaml.YAMLError as e:
            item(False, f'YAML 語法：{p}（{e}）')

    # 圖片型配色值（key_back_color: xxx.png）必須有對應檔案，否則鍵變透明/回退
    for sid, sch in theme.get('preset_color_schemes', {}).items():
        if not isinstance(sch, dict):
            continue
        for k, v in sch.items():
            if isinstance(v, str) and v.endswith(('.png', '.webp', '.jpg')) and not v.startswith('trime:'):
                f = ANDROID / 'backgrounds' / v
                item(f.exists(), f'圖片資源存在：{sid}.{k} → backgrounds/{v}')

    # ⑥ 鍵盤內不得有重複字符（含長按；基礎鍵與長按目標也不得相同）
    #    2026-11-06 實例：中文符號頁 ，。 在行 1 與底行各一份
    for kb_name, kb in (theme.get('preset_keyboards') or {}).items():
        if kb_name.startswith('__') or not isinstance(kb, dict):
            continue
        keys = kb.get('keys') or []
        base = [k['click'] for k in keys if isinstance(k.get('click'), str) and len(k['click']) == 1]
        longs = [k['long_click'] for k in keys if isinstance(k.get('long_click'), str) and len(k['long_click']) == 1]
        dup_b = sorted({c for c in base if base.count(c) > 1})
        dup_l = sorted({c for c in longs if longs.count(c) > 1})
        clash = sorted(set(base) & set(longs))
        item(not (dup_b or dup_l or clash),
             f'鍵盤 {kb_name} 無重複字符'
             + (f'（基礎重複 {dup_b} 長按重複 {dup_l} 衝突 {clash}）' if (dup_b or dup_l or clash) else ''))

    # ⑦ 符號頁必須顯式聲明語言態：ascii_mode: -1 會被 Trime 解析成 false（中文），
    #    Rime 的 punctuator 隨即在中文態把 , . " ' : ; ? ! 換成全角形——
    #    頁面自稱 ASCII 卻出中文標點。實測事故 2026-11-06。
    for kb_name, kb in (theme.get('preset_keyboards') or {}).items():
        if kb_name.startswith('__') or not isinstance(kb, dict):
            continue
        keys = kb.get('keys') or []
        ascii_chars = [k['click'] for k in keys
                       if isinstance(k.get('click'), str) and len(k['click']) == 1
                       and k['click'].isascii() and k['click'].isprintable()]
        if not ascii_chars:
            continue
        declared = kb.get('ascii_mode') in (0, 1) and kb.get('reset_ascii_mode') is not None
        item(declared,
             f'鍵盤 {kb_name} 顯式聲明語言態（ascii_mode∈{{0,1}} + 明寫 reset_ascii_mode）'
             + ('' if declared else
                f'（現爲 ascii_mode={kb.get("ascii_mode")!r} '
                f'reset_ascii_mode={kb.get("reset_ascii_mode")!r}；'
                '-1 會被當成 false，標點將被引擎轉換）'))

    # ⑧ 重複鍵檢測（YAML 靜默取最後一個 → 前一份定義等於白寫，改版時極易踩）
    #    2026-11-06 實例：number_zh 被定義兩次，改動全被後一份蓋掉，頁面「怎麼改都沒生效」。
    raw_lines = (ANDROID / 'xuma_L.trime.yaml').read_text(encoding='utf-8').splitlines()
    section, seen, dup = None, {}, []
    for ln in raw_lines:
        m_sec = re.match(r'^([a-z_]+):\s*$', ln)
        if m_sec:
            section = m_sec.group(1)
            continue
        m_key = re.match(r'^  ([a-zA-Z_0-9\-]+):', ln)
        if m_key and section:
            key = (section, m_key.group(1))
            if key in seen:
                dup.append(f'{section}/{m_key.group(1)}（第 {seen[key]} 行與本行）')
            else:
                seen[key] = raw_lines.index(ln) + 1
    item(not dup, '主題內無重複鍵定義' + (f'（重複：{dup}）' if dup else ''))

    check_theme(theme, schema)
    check_custom(custom, schema)
    check_default()
    item(gen_theme(check=True), '自包含 v1.trime.yaml 無漂移（gen-theme 生成）')
    print(f'── 結果：{"敗 " + str(len(FAIL)) + " 項" if FAIL else "全綠"}'
          f'（警告 {len(WARN)}）──')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
