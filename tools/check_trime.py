#!/usr/bin/env python3
# check_trime.py —— 同文（Trime）端資產校驗與生成
#
# 職責：
#   1. 本倉 *.yaml 語法與結構校驗（主題鍵盤/配色/補丁路徑/方案表）；
#   2. 主題字根 hint 與方案 speller/preedit_format 的 xlit 映射逐鍵對賬；
#   3. 輸出部署清單（manifest 子命令，deploy.sh 的唯一來源）。
#   4. 將 rime/theme/ 內的 Trime 預設與 V1 源檔深合併，展開 __include，生成手機主題。
#
# 依賴：PyYAML。
# 用法：
#   uv run --with pyyaml python tools/check_trime.py            # 靜態校驗
#   uv run --with pyyaml python tools/check_trime.py manifest   # 純主題 TSV，可加 --theme v1 或 --xuma
#   uv run --with pyyaml python tools/check_trime.py gen-theme  # 生成 rime/theme/v1.trime.yaml

import argparse
import os
import re
import string
import sys
from dataclasses import dataclass
from hashlib import md5
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

import yaml

ROOT = Path(__file__).resolve().parents[1]
RIME_DIR = ROOT / 'rime'
XUMA_DIR = ROOT / 'extras' / 'xuma-l'
XUMA_PATCH = XUMA_DIR / 'xuma_L.custom.yaml'
XUMA_EXAMPLE = XUMA_DIR / 'config.example.yaml'
XUMA_LOCAL = XUMA_DIR / 'config.local.yaml'
XUMA_SPOOL_README = 'lua/codelllc09/tools/dict_pipeline/README.txt'
THEME_DIR = RIME_DIR / 'theme'
THEME_SOURCE_DIR = THEME_DIR / 'sources'
THEME_SOURCE = THEME_SOURCE_DIR / 'v1.theme-source.yaml'
THEME_BUILD = THEME_DIR / 'v1.trime.yaml'
TYPEWRITER_ID = 'v2-typewriter'
TYPEWRITER_BUILD = THEME_DIR / f'{TYPEWRITER_ID}.trime.yaml'
CALCULATOR_ID = 'v2-calculator'
LABELMAKER_ID = 'v2-labelmaker'
HALFTONE_ID = 'v2-halftone'
CONTOUR_ID = 'v2-contour'
CYANOTYPE_ID = 'v2-cyanotype'
PATCHWORK_ID = 'v2-patchwork'
STAINEDGLASS_ID = 'v2-stainedglass'
OSCILLOSCOPE_ID = 'v2-oscilloscope'
PIXELBLOCK_ID = 'v2-pixelblock'
CASSETTE_ID = 'v2-cassette'
TERRAZZO_ID = 'v2-terrazzo'
BAUHAUS_ID = 'v2-bauhaus'
PERFORATION_ID = 'v2-perforation'
INTERLOCK_ID = 'v2-interlock'
BACKPLANE_ID = 'v2-backplane'
VACUUM_ID = 'v2-vacuum'
THERMOGRAM_ID = 'v2-thermogram'
MATERIAL_THEME_IDS = (CYANOTYPE_ID, PATCHWORK_ID, STAINEDGLASS_ID)
CONTRAST_THEME_IDS = (CASSETTE_ID, TERRAZZO_ID, BAUHAUS_ID)
INDUSTRIAL_THEME_IDS = (PERFORATION_ID, INTERLOCK_ID, BACKPLANE_ID, VACUUM_ID, THERMOGRAM_ID)
FACTORY_THEME_IDS = ('v2-foundry', 'v2-wafer', 'v2-pneumatic')
SKINNED_THEME_IDS = (TYPEWRITER_ID, CALCULATOR_ID, LABELMAKER_ID, HALFTONE_ID, CONTOUR_ID,
                     *MATERIAL_THEME_IDS, OSCILLOSCOPE_ID, PIXELBLOCK_ID, *CONTRAST_THEME_IDS,
                     *INDUSTRIAL_THEME_IDS, *FACTORY_THEME_IDS)
THEME_IDS = ('v1', *SKINNED_THEME_IDS)
SHARED_KEY_FONTS = ('fonts/xuma_key.otf', 'fonts/xuma_latin.ttf',
                    'fonts/Apache-2.0.txt', 'fonts/OFL-1.1.txt')
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
    print('主題 v1.theme-source.yaml：')
    item(theme.get('config_version') == '3.0', 'config_version 爲 "3.0"（Trime ≥3.3 格式）')
    source_keyboards = theme.get('preset_keyboards') or {}
    item('qwerty' in source_keyboards, '主題定義通用 qwerty 版面')
    item('xuma_L' in source_keyboards, '主題保留徐碼同名鍵盤')
    base = load_yaml(THEME_DIR / 'vendor' / 'trime-3.3.13.yaml')
    keyboards = resolve_theme(theme, base)['preset_keyboards']
    common = keyboards['qwerty']
    common_keys = common['keys']
    default_w = common.get('width', 10)
    # 行寬合計：keys 順序累積，寬滿 100 換行（Trime 佈局算法）
    row, rows = 0.0, []
    for k in common_keys:
        w = float(k.get('width', default_w))
        row += w
        if row >= 100 - 1e-6:
            rows.append(round(row, 4))
            row = 0.0
    if row > 0:
        rows.append(round(row, 4))
    item(len(rows) == 4 and all(abs(r - 100) < 0.6 for r in rows),
         f'通用鍵盤共四行，每行寬度合計≈100（實際 {rows}）')

    # 功能鍵引用閉合
    custom_keys = set((theme.get('preset_keys') or {})) - {'__include'}
    known = TRIME_PRESET_KEYS | custom_keys
    bad = []
    for k in common_keys:
        for attr in KEYREF_ATTRS:
            v = k.get(attr)
            if isinstance(v, str) and re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', v):
                if v not in known and len(v) > 1:
                    bad.append(f'{attr}={v}')
    item(not bad, f'功能鍵引用全部存在（自定義 {sorted(custom_keys)}）' +
         ('' if not bad else f'；未知引用 {bad}'))

    # 只有徐碼版面實際顯示字根提示時才需要對賬。
    hints = {
        key['click']: str(key['hint'])
        for key in keyboards.get('xuma_L', {}).get('keys', [])
        if key.get('hint') and re.fullmatch(r'[a-z]', str(key.get('click')))
    }
    if schema and hints:
        xlit = parse_schema_xlit(schema)
        item(xlit is not None, '方案 translator/preedit_format 解析出 xlit 字根映射')
        if xlit is not None:
            wrong = [f'{letter}:{hint}≠{xlit.get(letter)}' for letter, hint in hints.items()
                     if hint != xlit.get(letter)]
            item(not wrong, f'字根 hint 與方案一致（{len(hints)}/26 鍵）'
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


def check_custom(custom: dict, schema):
    print('補丁 xuma_L.custom.yaml：')
    item(isinstance(custom.get('patch'), dict) and custom['patch'],
         'patch 節點存在且非空')
    if schema is None:
        item(True, f'SKIP：補丁路徑校驗需方案檔（{len(custom.get("patch") or {})} 條未驗）')
        return
    for path in (custom.get('patch') or {}):
        item(resolve_schema_path(schema, path), f'補丁路徑存在：{path}')


def check_default(desktop_dir):
    print('生成配置（GEN_CUSTOM，部署時產出）：')
    d = yaml.safe_load(GEN_CUSTOM['default.custom.yaml'])
    item(isinstance(d.get('patch'), dict) and d['patch'], 'default.custom.yaml 語法與 patch ✓')
    l = yaml.safe_load(GEN_CUSTOM['luna_pinyin.custom.yaml'])
    item((l.get('patch') or {}).get('translator/dictionary') == 'luna_pinyin.extended',
         'luna_pinyin.custom.yaml 指向 extended ✓')
    if desktop_dir is None:
        item(True, 'SKIP：未指定桌面 Rime 目錄，跳過方案清單校驗')
    else:
        missing = [entry['schema'] for entry in d['patch']['schema_list']
                   if not (desktop_dir / f"{entry['schema']}.schema.yaml").is_file()]
        item(not missing, '方案檔案齊備' + (f'；缺 {missing}' if missing else ''))
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
    """產出個人配置二件到指定目錄，供推送與模擬測試使用。"""
    dst = Path(dst_dir)
    for name, text in GEN_CUSTOM.items():
        (dst / name).write_text(text, encoding='utf-8')
        print(f'generated {name}', file=sys.stderr)


@dataclass(frozen=True)
class XumaConfig:
    desktop_dir: Path
    files: tuple[str, ...]
    lua_dirs: tuple[str, ...]


def xuma_relative_paths(values, field):
    if not isinstance(values, list):
        raise SystemExit(f'[✗] 徐碼配置的 {field} 須為路徑清單')
    paths = []
    for value in values:
        if not isinstance(value, str) or any(char in value for char in '\\\r\n\t\0'):
            raise SystemExit(f'[✗] 徐碼配置的 {field} 須使用有效路徑：{value!r}')
        path = Path(value)
        if not path.parts or path.is_absolute() or '..' in path.parts:
            raise SystemExit(f'[✗] 徐碼配置的 {field} 須使用桌面目錄內的相對路徑：{value!r}')
        paths.append(path.as_posix())
    return tuple(paths)


def load_xuma_config(*, required=True):
    override = os.environ.get('RIME_DESKTOP_DIR')
    has_local_config = XUMA_LOCAL.exists()
    if not (has_local_config or override):
        if required:
            raise SystemExit('[✗] 請複製 extras/xuma-l/config.example.yaml 為 config.local.yaml，'
                             '設定 desktop_dir，或指定 RIME_DESKTOP_DIR')
        return None

    try:
        local = load_yaml(XUMA_LOCAL) if has_local_config else {}
        defaults = load_yaml(XUMA_EXAMPLE)
    except (OSError, yaml.YAMLError) as error:
        raise SystemExit(f'[✗] 無法讀取徐碼配置：{error}') from None
    if not isinstance(local, dict):
        raise SystemExit(f'[✗] 徐碼配置須為 YAML 鍵值表：{XUMA_LOCAL}')
    unknown = local.keys() - {'desktop_dir', 'files', 'lua_dirs'}
    if unknown:
        raise SystemExit(f'[✗] 未知的徐碼配置欄位：{", ".join(sorted(map(str, unknown)))}')

    value = override or local.get('desktop_dir')
    if not isinstance(value, str) or not value.strip() or any(char in value for char in '\r\n\t\0'):
        raise SystemExit('[✗] 請設定有效的徐碼 desktop_dir 或 RIME_DESKTOP_DIR')
    try:
        desktop = Path(value).expanduser()
    except RuntimeError as error:
        raise SystemExit(f'[✗] 無法展開徐碼 desktop_dir：{error}') from None
    if not override:
        desktop = XUMA_LOCAL.parent / desktop
    desktop = desktop.resolve()
    if not desktop.is_dir():
        raise SystemExit(f'[✗] 桌面 Rime 目錄不存在：{desktop}')

    files = xuma_relative_paths(local.get('files', defaults['files']), 'files')
    if 'xuma_L.schema.yaml' not in files:
        raise SystemExit('[✗] 徐碼配置的 files 須包含 xuma_L.schema.yaml')
    lua_dirs = xuma_relative_paths(local.get('lua_dirs', defaults['lua_dirs']), 'lua_dirs')
    return XumaConfig(desktop, files, lua_dirs)


def xuma_files(config):
    """只讀列入配置的檔案與 Lua 目錄直接包含的模組。"""
    desktop = config.desktop_dir
    yield XUMA_PATCH, XUMA_PATCH.name
    for name in config.files:
        yield desktop / name, name
    directories = [desktop / name for name in config.lua_dirs if (desktop / name).is_dir()]
    if config.lua_dirs and not directories:
        raise SystemExit(f'[✗] 桌面 Rime 未找到設定的 Lua 目錄：{desktop}')
    for directory in directories:
        for path in sorted(directory.glob('*.lua')):
            if path.is_file():
                yield path, path.relative_to(desktop).as_posix()


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
    鍵盤可用本地生成指令 __key_overrides 依 click 覆寫單鍵，避免複製整個 keys 序列。
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
    siblings = {
        k: _resolve_includes(v, base, root)
        for k, v in node.items() if k not in ('__include', '__key_overrides')
    }
    merged = _deep_merge(_resolve_includes(anchor, base, sub_root), siblings)
    for click, patch in node.get('__key_overrides', {}).items():
        keys = merged.get('keys', [])
        matches = [i for i, key in enumerate(keys) if isinstance(key, dict) and key.get('click') == click]
        if len(matches) != 1:
            raise SystemExit(f'[✗] {ref} 的 {click!r} 鍵應恰好匹配一次，實際 {len(matches)} 次')
        index = matches[0]
        keys[index] = _deep_merge(keys[index], _resolve_includes(patch, base, root))
    return merged


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


def resolve_theme(ours, base):
    """展開主題繼承，供部署和文件預覽共用。"""
    resolved = _resolve_includes(ours, base, ours)
    merged = _deep_merge(base, resolved)
    # 配色清單只有在顯式引用時才繼承，以免套用缺少自訂鍵色的內建配色。
    schemes = resolved.get('preset_color_schemes', merged['preset_color_schemes'])
    # 只對配色區做字符串化：尺寸/座標等數值鍵必須保持數值（38 變成 '#000026' 曾踩過）
    merged['preset_color_schemes'] = _stringify_colors(schemes)
    return merged


def gen_theme(target: Path = THEME_BUILD, check: bool = False) -> bool:
    """合併 Trime 預設與 v1.theme-source.yaml，生成自包含的手機主題。"""
    base = load_yaml(THEME_DIR / 'vendor' / 'trime-3.3.13.yaml')
    merged = resolve_theme(load_yaml(THEME_SOURCE), base)
    text = yaml.safe_dump(merged, allow_unicode=True, sort_keys=True, width=4096)

    if check:
        cur = target.read_text(encoding='utf-8') if target.exists() else ''
        if cur != text:
            print(f'[✗] {target.name} 與生成結果不一致（陳舊）：請跑 gen-theme', file=sys.stderr)
            return False
        print(f'  [✓] {target.name} 與 v1.theme-source.yaml 同步（無漂移）')
        return True

    target.write_text(text, encoding='utf-8')
    print(f'  [✓] 已生成 {target.name}（{len(text)} 字節）')
    return True


def theme_assets(theme_id):
    """依生成主題的全部配色列出安裝資產。"""
    build = THEME_DIR / f'{theme_id}.trime.yaml'
    yield build, build.name
    theme = load_yaml(build)
    folder = Path('backgrounds') / theme['style'].get('background_folder', '')
    images = {value for scheme in theme['preset_color_schemes'].values()
              for value in scheme.values()
              if isinstance(value, str) and value.endswith(('.png', '.webp', '.jpg'))}
    for name in sorted(images):
        asset = folder / name
        yield RIME_DIR / asset, asset.as_posix()
    fonts = SHARED_KEY_FONTS
    if theme_id == TYPEWRITER_ID:
        fonts += ('fonts/typewriter_latin.ttf', 'fonts/CourierPrime-OFL.txt')
    if theme_id in (LABELMAKER_ID, CYANOTYPE_ID, OSCILLOSCOPE_ID, PIXELBLOCK_ID):
        fonts += ('fonts/labelmaker_mono.otf', 'fonts/SourceCodePro-OFL.txt')
    if theme_id in (HALFTONE_ID, PATCHWORK_ID):
        fonts += ('fonts/halftone_latin.ttf',)
    for asset in fonts:
        yield RIME_DIR / asset, asset
    if theme_id != 'v1':
        yield from sound_asset_paths(theme_id)


def sound_asset_paths(theme_id):
    descriptor = f'soundeffect/{theme_id}.sound.yaml'
    yield RIME_DIR / descriptor, descriptor
    sound = load_yaml(RIME_DIR / descriptor)
    for name in sound['sound']:
        asset = f"soundeffect/{sound['folder']}/{name}"
        yield RIME_DIR / asset, asset


def packaged_sound_files(theme_id):
    """讀取已收錄的音效描述及 WAV，供沒有本機原型時重建。"""
    return {name: source.read_bytes() for source, name in sound_asset_paths(theme_id)}


def deployment_files(theme_id=None, *, xuma=None):
    """列出倉庫或桌面來源與手機目標，供清單與部署包共用。"""
    theme_ids = (theme_id,) if theme_id else THEME_IDS
    pairs = [pair for name in theme_ids for pair in theme_assets(name)]
    if xuma is not None:
        pairs.extend(xuma_files(xuma))

    files = list(dict.fromkeys(pairs))
    destinations = [dst for _, dst in files]
    if xuma is not None:
        destinations.extend((*GEN_CUSTOM, XUMA_SPOOL_README))
    paths = {Path(dst) for dst in destinations}
    if len(paths) != len(destinations) or any(paths.intersection(path.parents) for path in paths):
        raise SystemExit('[✗] 部署清單有重複或互相衝突的手機路徑')

    out = []
    for source, dst in files:
        src = source.relative_to(ROOT) if source.is_relative_to(ROOT) else source
        if not source.is_file():
            raise SystemExit(f'[✗] 部署來源缺失：{src}')
        if any(char in str(src) for char in '\t\r\n'):
            raise SystemExit(f'[✗] 部署來源路徑含定位字元或換行：{str(src)!r}')
        out.append((src, dst))
    return out


def manifest(theme_id=None, *, xuma=None):
    """輸出 TSV：倉庫內相對或桌面絕對來源 <TAB> 手機目標。"""
    for src, dst in deployment_files(theme_id, xuma=xuma):
        print(f'{src}\t{dst}')


def package(target, theme_id=None, *, xuma=None):
    """生成可解壓到手機使用者資料夾的 ZIP。"""
    if target.exists():
        raise SystemExit(f'[✗] 部署包已存在：{target}')
    files = deployment_files(theme_id, xuma=xuma)
    extras = {}
    if xuma is not None:
        extras = {
            **GEN_CUSTOM,
            XUMA_SPOOL_README:
                '# 同文端 /add 攢詞暫存（deploy.sh pull-spool 回收入庫；桌面勿編）\n',
        }
    destinations = {dst for _, dst in files}
    if theme_id is None:
        missing = {path.name for path in THEME_DIR.glob('*.trime.yaml')} - destinations
        if missing:
            raise SystemExit(f'[✗] 主題未納入部署清單：{", ".join(sorted(missing))}')

    with TemporaryDirectory(prefix='.tongwen-pkg-', dir=target.parent) as stage:
        temporary = Path(stage) / target.name
        with ZipFile(temporary, 'x', ZIP_DEFLATED, strict_timestamps=False) as archive:
            for src, dst in files:
                archive.write(ROOT / src, dst)
            for dst, contents in extras.items():
                archive.writestr(dst, contents)
        with ZipFile(temporary) as archive:
            damaged = archive.testzip()
            if damaged is not None:
                raise SystemExit(f'[✗] ZIP 校驗失敗：{damaged}')
        # 在同一檔案系統發佈完整檔案，並防止同時打包時覆蓋已有的 ZIP。
        try:
            os.link(temporary, target)
        except FileExistsError:
            raise SystemExit(f'[✗] 部署包已存在：{target}') from None

    listing = ''.join(f'{src}\t{dst}\n' for src, dst in files)
    return len(files) + len(extras), md5(listing.encode(), usedforsecurity=False).hexdigest()[:8]


def package_release(target: Path):
    """在新目錄生成完整包及每款主題的 Release 安裝包。"""
    if target.exists():
        raise SystemExit(f'[✗] Release 安裝包目錄已存在：{target}')
    if not gen_theme(check=True):
        raise SystemExit(1)

    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='.trime-release-', dir=target.parent) as stage:
        packages = Path(stage) / 'packages'
        packages.mkdir()
        package(packages / 'trime-themes.zip')
        for theme_id in THEME_IDS:
            package(packages / f'trime-{theme_id}.zip', theme_id)
        packages.rename(target)

    print(f'已打包並校驗：{target}（{len(THEME_IDS) + 1} 個 ZIP）')


def deployment_options(command):
    parser = argparse.ArgumentParser(prog=f'check_trime.py {command}', allow_abbrev=False)
    if command == 'package':
        parser.add_argument('target', type=Path)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--theme', choices=THEME_IDS, help='只選一款主題')
    selection.add_argument('--xuma', action='store_true', help='另含徐碼·L 方案與補丁')
    if command == 'manifest':
        for name in SKINNED_THEME_IDS:
            selection.add_argument(f'--{name.removeprefix("v2-")}', dest='theme',
                                   action='store_const', const=name, help=argparse.SUPPRESS)
    return parser.parse_args(sys.argv[2:])


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else None
    if command in ('package', 'manifest'):
        args = deployment_options(command)
        xuma = load_xuma_config() if args.xuma else None
        if command == 'package':
            count, fingerprint = package(args.target, args.theme, xuma=xuma)
            print(f'{count}\t{fingerprint}')
        else:
            manifest(args.theme, xuma=xuma)
        return
    if command == 'package-release':
        parser = argparse.ArgumentParser(prog='check_trime.py package-release')
        parser.add_argument('target', type=Path, help='輸出目錄（須尚未存在）')
        package_release(parser.parse_args(sys.argv[2:]).target)
        return
    if command == 'gen-custom' and len(sys.argv) == 3:
        gen_custom(sys.argv[2])
        return
    if command == 'gen-theme':
        ok = gen_theme(check='--check' in sys.argv)
        sys.exit(0 if ok else 1)
    if command == 'xuma-desktop-dir' and len(sys.argv) == 2:
        print(load_xuma_config().desktop_dir)
        return
    if command:
        raise SystemExit(f'[✗] 不支援的參數：{" ".join(sys.argv[1:])}')

    print('── 本倉資產校驗 ──')
    custom_path = XUMA_PATCH
    theme = load_yaml(THEME_SOURCE)
    custom = load_yaml(custom_path)
    xuma = load_xuma_config(required=False)
    desktop_dir = xuma.desktop_dir if xuma else None
    schema = None
    if desktop_dir is not None:
        schema_path = desktop_dir / 'xuma_L.schema.yaml'
        if schema_path.is_file():
            schema = load_yaml(schema_path)
    else:
        print('  [·] 未指定桌面 Rime 目錄，略過方案校驗')

    for path in (THEME_SOURCE, custom_path):
        relative_path = path.relative_to(ROOT)
        try:
            load_yaml(path)
            print(f'  [✓] YAML 語法：{relative_path}')
        except yaml.YAMLError as e:
            item(False, f'YAML 語法：{relative_path}（{e}）')

    # 圖片型配色值（key_back_color: xxx.png）必須有對應檔案，否則鍵變透明/回退
    for sid, sch in theme.get('preset_color_schemes', {}).items():
        if not isinstance(sch, dict):
            continue
        for k, v in sch.items():
            if isinstance(v, str) and v.endswith(('.png', '.webp', '.jpg')) and not v.startswith('trime:'):
                f = RIME_DIR / 'backgrounds' / v
                item(f.exists(), f'圖片資源存在：{sid}.{k} → {f.relative_to(ROOT)}')

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
    raw_lines = THEME_SOURCE.read_text(encoding='utf-8').splitlines()
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

    # ⑨ 三頁「回字母」鍵一致（2026-11-07 兩次教訓：改了數字頁漏掉另兩頁；
    #    `git checkout --` 把未提交改動整批洗掉，實機仍是舊樣）。
    # 現行定案：**不畫角標**（label_symbol 為一個空白）。
    # 配色：數字頁 nav 淡染（該頁無 123 可參照）；ASCII／標點頁 fn 灰，與同頁 123 一致。
    want_by_page = {
        'number': {'click': 'back_to_kb', 'label_symbol': ' ',
                   'key_back_color': 'nav_back_color', 'key_text_color': 'nav_text_color'},
        'number_ascii': {'click': 'back_to_kb', 'label_symbol': ' ',
                         'key_back_color': 'fn_back_color', 'key_text_color': 'fn_text_color'},
        'number_zh': {'click': 'back_to_kb', 'label_symbol': ' ',
                      'key_back_color': 'fn_back_color', 'key_text_color': 'fn_text_color'},
    }
    bad_back = []
    for page, want in want_by_page.items():
        kb = theme['preset_keyboards'].get(page) or {}
        hits = [k for k in kb.get('keys', [])
                if isinstance(k, dict) and k.get('click') == 'back_to_kb']
        if len(hits) != 1:
            bad_back.append(f'{page}：{len(hits)} 顆 back_to_kb（應爲 1）')
            continue
        diff = {k: (hits[0].get(k), v) for k, v in want.items() if hits[0].get(k) != v}
        if diff:
            bad_back.append(f'{page}：{diff}')
    item(not bad_back, '三頁「回字母」鍵一致（back_to_kb、無角標；數字頁 nav、另兩頁 fn 同 123）'
         + ('' if not bad_back else f'；{bad_back}'))

    ascii_keys = theme['preset_keyboards']['number_ascii']['keys']
    symbols = [key.get('click') for key in ascii_keys]
    ascii_punctuation = set(string.punctuation)
    punctuation = [ch for ch in symbols if isinstance(ch, str) and ch in ascii_punctuation]
    item(sorted(punctuation) == sorted(string.punctuation)
         and not any(isinstance(ch, str) and ch.isdecimal() for ch in symbols),
         'ASCII 頁短按涵蓋 32 個標點，無數字列')
    popup_keys = [key for key in ascii_keys if key.get('popup')]
    popup_style = theme['style']
    item(len(popup_keys) == 6
         and all(popup_style.get(name, 0) > 0 for name in
             ('popup_width', 'popup_height', 'popup_key_height', 'popup_text_size'))
         and all(key.get('label_symbol') and not key.get('long_click') for key in popup_keys),
         '彈出選單有可見尺寸與角標，且不和長按直出衝突')

    check_theme(theme, schema)
    check_custom(custom, schema)
    check_default(desktop_dir)
    item(gen_theme(check=True), '自包含 v1.trime.yaml 無漂移（gen-theme 生成）')
    print(f'── 結果：{"敗 " + str(len(FAIL)) + " 項" if FAIL else "全綠"}'
          f'（警告 {len(WARN)}）──')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
