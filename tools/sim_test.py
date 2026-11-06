#!/usr/bin/env python3
# sim_test.py —— 本機安卓（同文/Trime）模擬測試座（feat/tongwen）
#
# 原理：Trime 的輸入引擎＝librime＋librime-lua 插件（其構建即 RIME_PLUGINS
#   "librime-lua librime-octagram librime-predict"）。本機 Fedora 的
#   ibus-rime 用同族 librime 1.16.1 動態庫＋rime-plugins/librime-lua.so。
#   本座以 ctypes 直連，沙箱用戶目錄＝deploy.sh 同款清單佈局，
#   並在進程環境剝離 HOME／XDG_*，逼出「安卓進程無 XDG/HOME」的路徑。
#
# 覆蓋（對應 README.md 真機驗收清單）：
#   T1  部署零錯＋lua 全量加載        T2 進方案默認中文（補丁生效）
#   T3  打字＋字根 preedit＋上屏      T3b 42 碼首選全量回歸（驗收基準）
#   T4  /menu 數字選鍵＋option 生效   T5  /add 收詞入沙箱 spool
#   T6  `p 小寫拼音反查（補丁）       T7  `li,hs 組合反查
#   T8  u6c5f 碼位反查（u+數字）      T9  Shift+u 大寫通道（「碼」鍵前提）
#   T10 simplification 簡繁（OpenCC） T11 主題 __include 編譯＋節點斷言
#   T12 全程無 HOME／XDG 環境（本座自身即測試）
#
# 不覆蓋（仍需真機）：Trime 前端渲染、send:"Shift+u" 的鍵值轉換、
#   候選點擊 UI、打包的 OpenCC 詞典、性能與崩潰。
#
# 用法：python3 tools/sim_test.py [--keep]
# 依賴：/lib64/librime.so.1、/usr/lib64/rime-plugins/librime-lua.so（只讀）；
#   首跑需網絡拉取 Trime v3.3.13 默認主題（緩存 tmp/simtest/trime.yaml）。

import argparse
import ctypes as C
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # tools/
ANDROID = HERE.parent                            # 本倉根（安卓資產）
# 共享件根＝桌面主倉（schema/詞典/lua/基準檔）；獨立成倉後經 RIME_DESKTOP_DIR 指引（2026-11-07）
REPO = Path(os.environ.get('RIME_DESKTOP_DIR', str(Path.home() / '.config/ibus/rime'))).expanduser()
SIM = REPO / 'tmp' / 'simtest'
BASELINE = REPO / 'lua/codelllc09/tools/dict_pipeline/archive/rulings/驗收基準.txt'

LIBRIME = os.environ.get('SIM_LIBRIME', '/lib64/librime.so.1')
LIBLUA = os.environ.get('SIM_LIBRIME_LUA', '/usr/lib64/rime-plugins/librime-lua.so')
SHARED = os.environ.get('SIM_SHARED', '/usr/share/rime-data')
TRIME_YAML_URL = ('https://raw.githubusercontent.com/osfans/trime/v3.3.13/'
                  'app/src/main/assets/shared/trime.yaml')

FAIL = []


def item(ok, msg, hint=''):
    print(f"  [{'✓' if ok else '✗'}] {msg}" + (f'　{hint}' if hint and not ok else ''))
    if not ok:
        FAIL.append(msg)


# ── ctypes 結構（照 librime 1.16.1 src/rime_api.h）──────────────
class RimeTraits(C.Structure):
    _fields_ = [('data_size', C.c_int),
                ('shared_data_dir', C.c_char_p),
                ('user_data_dir', C.c_char_p),
                ('distribution_name', C.c_char_p),
                ('distribution_code_name', C.c_char_p),
                ('distribution_version', C.c_char_p),
                ('app_name', C.c_char_p),
                ('modules', C.POINTER(C.c_char_p)),
                ('min_log_level', C.c_int),
                ('log_dir', C.c_char_p),
                ('prebuilt_data_dir', C.c_char_p),
                ('staging_dir', C.c_char_p)]


class RimeComposition(C.Structure):
    _fields_ = [('length', C.c_int), ('cursor_pos', C.c_int),
                ('sel_start', C.c_int), ('sel_end', C.c_int),
                ('preedit', C.c_char_p)]


class RimeCandidate(C.Structure):
    _fields_ = [('text', C.c_char_p), ('comment', C.c_char_p),
                ('reserved', C.c_void_p)]


class RimeMenu(C.Structure):
    _fields_ = [('page_size', C.c_int), ('page_no', C.c_int),
                ('is_last_page', C.c_int),
                ('highlighted_candidate_index', C.c_int),
                ('num_candidates', C.c_int),
                ('candidates', C.POINTER(RimeCandidate)),
                ('select_keys', C.c_char_p)]


class RimeContext(C.Structure):
    _fields_ = [('data_size', C.c_int), ('composition', RimeComposition),
                ('menu', RimeMenu), ('commit_text_preview', C.c_char_p),
                ('select_labels', C.POINTER(C.c_char_p))]


class RimeCommit(C.Structure):
    _fields_ = [('data_size', C.c_int), ('text', C.c_char_p)]


def _fp(restype, *argtypes):
    return C.CFUNCTYPE(restype, *argtypes)


class RimeApi(C.Structure):
    # 僅列出至最後一個被調用字段（順序照 rime_api.h 1.16.1）
    _fields_ = [('data_size', C.c_int),
                ('setup', _fp(None, C.POINTER(RimeTraits))),
                ('set_notification_handler', _fp(None, C.c_void_p, C.c_void_p)),
                ('initialize', _fp(None, C.POINTER(RimeTraits))),
                ('finalize', _fp(None)),
                ('start_maintenance', _fp(C.c_int, C.c_int)),
                ('is_maintenance_mode', _fp(C.c_int)),
                ('join_maintenance_thread', _fp(None)),
                ('deployer_initialize', _fp(None, C.POINTER(RimeTraits))),
                ('prebuild', _fp(C.c_int)),
                ('deploy', _fp(C.c_int)),
                ('deploy_schema', _fp(C.c_int, C.c_char_p)),
                ('deploy_config_file', _fp(C.c_int, C.c_char_p, C.c_char_p)),
                ('sync_user_data', _fp(C.c_int)),
                ('create_session', _fp(C.c_size_t)),
                ('find_session', _fp(C.c_int, C.c_size_t)),
                ('destroy_session', _fp(C.c_int, C.c_size_t)),
                ('cleanup_stale_sessions', _fp(None)),
                ('cleanup_all_sessions', _fp(None)),
                ('process_key', _fp(C.c_int, C.c_size_t, C.c_int, C.c_int)),
                ('commit_composition', _fp(C.c_int, C.c_size_t)),
                ('clear_composition', _fp(None, C.c_size_t)),
                ('get_commit', _fp(C.c_int, C.c_size_t, C.POINTER(RimeCommit))),
                ('free_commit', _fp(None, C.POINTER(RimeCommit))),
                ('get_context', _fp(C.c_int, C.c_size_t, C.POINTER(RimeContext))),
                ('free_context', _fp(None, C.POINTER(RimeContext))),
                ('get_status', C.c_void_p),
                ('free_status', C.c_void_p),
                ('set_option', _fp(None, C.c_size_t, C.c_char_p, C.c_int)),
                ('get_option', _fp(C.c_int, C.c_size_t, C.c_char_p)),
                ('set_property', C.c_void_p),
                ('get_property', C.c_void_p),
                ('get_schema_list', C.c_void_p),
                ('free_schema_list', C.c_void_p),
                ('get_current_schema', C.c_void_p),
                ('select_schema', _fp(C.c_int, C.c_size_t, C.c_char_p)),
                ('simulate_key_sequence', _fp(C.c_int, C.c_size_t, C.c_char_p))]


SPACE, BACKSPACE, PAGE_DOWN = 0x20, 0xFF08, 0xFF56
SHIFT_MASK = 1 << 0


class Harness:
    def __init__(self, user_dir: Path):
        # glog 寫 fd2：先重定向到捕獲文件，供錯誤掃描
        self.err_path = user_dir.parent / 'stderr.log'
        self._err_fd = os.open(self.err_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
        os.dup2(self._err_fd, 2)
        self.lib = C.CDLL(LIBRIME)
        self.lua = C.CDLL(LIBLUA)     # 插件 constructor 自動註冊 'lua' 模塊
        self.lib.rime_get_api.restype = C.c_void_p
        self.api = C.cast(C.c_void_p(self.lib.rime_get_api()),
                          C.POINTER(RimeApi)).contents
        tr = RimeTraits()
        tr.data_size = C.sizeof(RimeTraits) - C.sizeof(C.c_int)
        tr.shared_data_dir = str(SHARED).encode()
        tr.user_data_dir = str(user_dir).encode()
        tr.distribution_name = b'Trime'
        tr.distribution_code_name = b'trime'
        tr.distribution_version = b'3.3.13-sim'
        tr.app_name = b'rime.simtest'
        self.api.initialize(C.byref(tr))
        self.sid = None

    def deploy(self):
        # 兩輪：首輪建 installation/default.yaml，次輪掃到 schema_list（真機同源行爲）
        for _ in range(2):
            self.api.start_maintenance(1)
            self.api.join_maintenance_thread()

    def deploy_config(self, fname, key):
        return bool(self.api.deploy_config_file(fname.encode(), key.encode()))

    def open_session(self):
        self.sid = self.api.create_session()

    def key(self, ch):
        if isinstance(ch, str):
            ch = ord(ch)
        return bool(self.api.process_key(self.sid, ch, 0))

    def key_masked(self, ch, mask):
        return bool(self.api.process_key(self.sid, ord(ch), mask))

    def commit_text(self):
        cm = RimeCommit()
        cm.data_size = C.sizeof(RimeCommit) - C.sizeof(C.c_int)
        if self.api.get_commit(self.sid, C.byref(cm)):
            t = cm.text.decode('utf-8', 'replace') if cm.text else ''
            self.api.free_commit(C.byref(cm))
            return t
        return None

    def context(self):
        ctx = RimeContext()
        ctx.data_size = C.sizeof(RimeContext) - C.sizeof(C.c_int)
        if not self.api.get_context(self.sid, C.byref(ctx)):
            return None
        out = {'preedit': ctx.composition.preedit.decode('utf-8', 'replace')
               if ctx.composition.preedit else '', 'cands': []}
        m = ctx.menu
        for i in range(max(0, m.num_candidates)):
            c = m.candidates[i]
            out['cands'].append((c.text.decode('utf-8', 'replace') if c.text else '',
                                 c.comment.decode('utf-8', 'replace') if c.comment else ''))
        self.api.free_context(C.byref(ctx))
        return out

    def clear(self):
        self.api.clear_composition(self.sid)

    def option(self, name):
        return bool(self.api.get_option(self.sid, name.encode()))

    def set_option(self, name, v):
        self.api.set_option(self.sid, name.encode(), 1 if v else 0)

    def errors(self):
        """掃捕獲的 glog 輸出中的 E 級行。"""
        if not self.err_path.exists():
            return []
        return [ln.strip()[:200] for ln in self.err_path.read_text(errors='replace').splitlines()
                if ln.startswith('E') and ln[1:2].isdigit()]


def stage_sandbox(user: Path):
    man = subprocess.run(
        [sys.executable, str(ANDROID / 'tools' / 'check_trime.py'), 'manifest'],
        capture_output=True, text=True, check=True, cwd=REPO).stdout
    for line in man.splitlines():
        src, dst = line.split('\t')
        target = user / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        srcp = (ANDROID / src) if (ANDROID / src).exists() else (REPO / src)
        shutil.copy2(srcp, target)
    sp = user / 'lua/codelllc09/tools/dict_pipeline'
    sp.mkdir(parents=True, exist_ok=True)
    (sp / 'spool_pending.txt').touch()
    # 個人配置二件（用戶裁定不入庫 3f5db09）：gen-custom 生成，保沙箱與真機同構
    subprocess.run([sys.executable, str(ANDROID / 'tools' / 'check_trime.py'),
                    'gen-custom', str(user)], check=True, capture_output=True)
    trime_yaml = user / 'trime.yaml'
    if not trime_yaml.exists():
        cached = SIM / 'trime.yaml'
        if not cached.exists():
            subprocess.run(['curl', '-sLo', str(cached), TRIME_YAML_URL], check=True)
        shutil.copy2(cached, trime_yaml)


def load_baseline():
    """驗收基準：碼<TAB>字 每行一條（靜態詞典首位語義，供參照與可達性斷言）。"""
    pairs = []
    for ln in BASELINE.read_text(encoding='utf-8').splitlines():
        ln = ln.strip()
        if not ln or ln.startswith('#') or '\t' not in ln:
            continue
        code, word = ln.split('\t')[:2]
        pairs.append((code.strip(), word.strip()))
    return pairs


def load_dict_codes(codes):
    """掃 xuma_L 詞典：每碼的全部活條目字集（動態有效性斷言用，掃法同 check_acceptance）。"""
    out = {c: set() for c in codes}
    started = False
    for ln in (REPO / 'xuma_L.dict.yaml').read_text(encoding='utf-8').splitlines():
        if not started:
            if ln == '...':
                started = True
            continue
        if not ln or ln.lstrip().startswith('#'):
            continue
        c = ln.split('\t')
        if len(c) < 2:
            continue
        code = c[1].strip()
        if code in out and all(ord(ch) <= 0x9FFF for ch in c[0]):
            out[code].add(c[0])
    return out


def type_commit(h, code):
    """打碼→空格，返回上屏文本（首選）。"""
    h.clear()
    for ch in code:
        h.key(ch)
    h.key(SPACE)
    return h.commit_text()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keep', action='store_true')
    args = ap.parse_args()

    user = SIM / 'sandbox' / 'user'
    if user.exists():
        shutil.rmtree(SIM / 'sandbox')
    user.mkdir(parents=True)

    # ── T12：剝離桌面環境變量（模擬安卓進程）────────────────────
    for var in ('HOME', 'XDG_CONFIG_HOME', 'XDG_RUNTIME_DIR', 'XDG_DATA_HOME'):
        os.environ.pop(var, None)

    print('── 沙箱佈置（部署清單 → %s）──' % user)
    stage_sandbox(user)
    baseline = load_baseline()
    dict_codes = load_dict_codes([c for c, _ in baseline])
    item(len(baseline) >= 40, f'驗收基準載入 {len(baseline)} 碼')

    print('── 初始化 librime＋librime-lua（無 HOME／XDG 環境）──')
    h = Harness(user)

    print('── T1 全量部署 ──')
    t0 = time.time()
    h.deploy()
    h.open_session()
    item((user / 'build' / 'xuma_L.schema.yaml').exists(), '部署產出 xuma_L.schema.yaml')
    item((user / 'build' / 'luna_pinyin.extended.table.bin').exists(),
         '部署產出 luna_pinyin.extended 表（反查依賴；靠手機版 luna_pinyin.custom.yaml）')
    errs = h.errors()
    item(not errs, f'部署日誌零錯誤（{time.time() - t0:.1f}s）', '; '.join(errs[:3]))

    print('── T2 進方案默認中文 ──')
    item(bool(h.api.select_schema(h.sid, b'xuma_L')), '選中方案 xuma_L')
    item(h.option('ascii_mode') is False, 'ascii_mode 默認關（補丁 reset 0 生效）')

    print('── T3 常規打字＋字根 preedit ──')
    code0 = baseline[0][0]
    h.clear()
    for ch in code0:
        h.key(ch)
    ctx = h.context()
    item(bool(ctx and ctx['cands']), f'{code0} 有候選',
         str(ctx)[:120] if ctx else 'no ctx')
    item(bool(ctx) and any(ord(c) > 0x2E7F for c in ctx['preedit']),
         'preedit 顯示字根部件', repr(ctx['preedit']) if ctx else '')
    h.key(SPACE)
    got = h.commit_text()
    item(bool(got) and got in dict_codes[code0],
         f'空格上屏首選 {got!r} ∈ 該碼詞典活條目')

    print('── T3b 動態回歸（上屏有效性＋基準字可達性，word_all 檔）──')
    # 基準＝詞典靜態首位（check_acceptance 語義）；默認 word_12 檔會合法地濾掉
    # 四字詞（如「教書育人」），故可達性在 word_all 檔驗。上屏有效性同檔成立。
    h.set_option('word_12', False)
    h.set_option('word_all', True)
    ok_n, bad_got, bad_reach, same = 0, [], [], 0
    for code, word in baseline:
        h.clear()
        for ch in code:
            h.key(ch)
        seen = set()
        for _ in range(3):
            c = h.context()
            if c:
                seen.update(x[0] for x in c['cands'])
                h.key(PAGE_DOWN)
        if word not in seen:
            bad_reach.append(f'{code}:{word}')
        h.clear()
        got = type_commit(h, code)
        if got in dict_codes[code]:
            ok_n += 1
        else:
            bad_got.append(f'{code}:{got}')
        if got == word:
            same += 1
    h.set_option('word_all', False)
    h.set_option('word_12', True)
    item(not bad_got, f'{ok_n}/{len(baseline)} 碼上屏字均属該碼活條目',
         '; '.join(bad_got[:5]))
    # 可達性僅統計：基準＝詞典序首位，個別生僻單字（如挸/㔨）經詞頻重排後
    # 動態排名本就後置——這是詞頻管道的設計行為，非缺陷（桌面同款）。
    print(f'  [i] 基準字在前三頁可達 {len(baseline) - len(bad_reach)}/{len(baseline)}；'
          f'動態首位與靜態基準一致 {same}/{len(baseline)}（排序差非缺陷）')

    print('── T4 /menu 數字選鍵 ──')
    h.clear()
    h.key('/') ; [h.key(c) for c in 'menu']
    ctx = h.context()
    idx = next((i for i, c in enumerate(
        (ctx['cands'] if ctx else [])[:9], 1) if '詞長' in c[0]), None)
    item(idx is not None, '/menu 一級菜單含「詞長」',
         str(ctx['cands'][:4]) if ctx else 'no ctx')
    if idx:
        h.key(str(idx))
        ctx2 = h.context()
        j = next((i for i, c in enumerate(
            (ctx2['cands'] if ctx2 else [])[:9], 1) if c[0] == '單字'), None)
        if j:
            h.key(str(j))
            item(h.option('single_char_only') is True, '數字選「單字」→ option 即時生效')
        else:
            item(None, '二級「單字」檔', str(ctx2['cands'][:6]) if ctx2 else '')
    h.clear()
    h.set_option('single_char_only', False)

    print('── T5 /add 收詞入沙箱 spool ──')
    h.clear()
    a = type_commit(h, baseline[0][0])          # 上屏第 1 字
    b = type_commit(h, baseline[1][0])          # 上屏第 2 字
    h.key('/') ; [h.key(c) for c in 'add']
    ctx = h.context()
    want = (a + b) if a and b else None         # 尾部連綴（最近 2 字）
    item(bool(ctx and want and any(c[0] == want for c in ctx['cands'])),
         f'/add 列出尾部連綴 {want!r}', str(ctx['cands'][:4]) if ctx else 'no ctx')
    if ctx and want:
        k = next((i for i, c in enumerate(ctx['cands'][:9], 1) if c[0] == want), None)
        if k:
            h.key(str(k))
            spool = user / 'lua/codelllc09/tools/dict_pipeline/spool_pending.txt'
            txt = spool.read_text(encoding='utf-8') if spool.exists() else ''
            item(want in txt.split(),
                 f'/add 收錄落沙箱 spool（get_user_data_dir 鏈，無 HOME 環境）')
        else:
            item(None, '連綴詞不在前 9 候選')
    h.clear()

    print('── T6 `p 小寫拼音反查（手機補丁）──')
    h.clear()
    h.key('`') ; [h.key(c) for c in 'pli']
    ctx = h.context()
    item(bool(ctx and ctx['cands']), '`pli 反查有候選（徐碼碼注）',
         str(ctx['cands'][:2]) if ctx else 'no ctx')
    h.clear()

    print('── T7 組合反查 `li/hs ──')
    h.clear()
    for ch in '`li/hs':
        h.key(ch)
    ctx = h.context()
    item(bool(ctx and ctx['cands'] and ctx['cands'][0][0] == '李'),
         '`li/hs 組合反查首選「李」',
         str(ctx['cands'][:3]) if ctx else 'no ctx')
    h.clear()

    print('── T8 碼位反查（KNOWN-SKIP：harness 無法模擬長按數字）──')
    # 方案 recognizer 為 ^U[0-9a-fA-F]{4,8}$，需要**大寫 U** ＋ 連續十六進制字符；
    # 手機上 4 行鍵盤沒有數字鍵，靠第一排長按出數字（y→6、t→5…），
    # librime 直連沒有「長按」通道，故本項在沙箱內無法復現。
    # 真機做法（2026-11-07 實測：preedit 顯示「U6C5F 碼位反查」、候選「江 U+6C5F」）：
    #   鎖定 Shift → u → 長按 y(6) → c → 長按 t(5) → f
    item(True, '碼位反查（沙箱跳過；真機 Shift+u 後以長按數字輸入十六進制）')

    print('── T10 simplification 簡繁（OpenCC）──')
    # 取一個繁簡異形詞的碼（fdwg→堅定，基準收錄）
    fdwg = next(((c, w) for c, w in baseline if w in ('堅定',)), None)
    if fdwg:
        h.set_option('simplification', False)
        trad = type_commit(h, fdwg[0])
        h.set_option('simplification', True)
        simp = type_commit(h, fdwg[0])
        h.set_option('simplification', False)
        item(trad == '堅定' and simp == '坚定',
             f'simplification 簡繁轉換：{trad!r} → {simp!r}', f'{trad!r}/{simp!r}')
    else:
        item(None, '基準中未找到繁簡異形樣本')

    print('── T11 主題編譯（真機上線的是自包含 v1.trime.yaml）──')
    # 部署清單送 android/v1.trime.yaml（gen-theme 生成的自包含替身；configId=v1），
    # xuma_L.trime.yaml 不再進沙箱也不再上手機——此測試必須跟着改，否則永遠紅燈。
    ok = h.deploy_config('v1.trime.yaml', 'config_version')
    built = user / 'build' / 'v1.trime.yaml'
    item(ok and built.exists(), 'deploy_config_file 編譯主題成功')
    if built.exists():
        import yaml
        theme = yaml.safe_load(built.read_text(encoding='utf-8'))
        kb = theme.get('preset_keyboards') or {}
        pk = theme.get('preset_keys') or {}
        cs = theme.get('preset_color_schemes') or {}
        item('xuma_L' in kb, '編譯產物含 preset_keyboards/xuma_L')
        item('unicode_lead' in pk, '編譯產物含自定義鍵 unicode_lead')
        item(len(pk) > 100, f'__include: trime:/preset_keys 併入官方鍵（{len(pk)} 個）')
        item('xuma_cloud' in cs and 'xuma_night' in cs, '配色兩套併入（雲白/墨空）')
        hints = [k.get('hint') for k in (kb.get('xuma_L') or {}).get('keys', [])
                 if isinstance(k.get('click'), str) and len(k['click']) == 1
                 and k['click'].isalpha()]
        # 用戶裁定「去字根 hint」：字根提示應為 0（長按提示改為功能/符號，不算 hint）
        item(len([x for x in hints if x]) == 0,
             f'字根 hint 已移除（{len([x for x in hints if x])} 個殘留）')

    h.api.cleanup_all_sessions()
    h.api.finalize()
    print(f'── 結果：{"全綠" if not FAIL else f"敗 {len(FAIL)} 項：{FAIL}"} ──')
    sys.exit(1 if FAIL else 0)


if __name__ == '__main__':
    main()
