"""讀取倉庫鍵音，或從指定的定案原型匯入。"""

from base64 import b64decode
from io import BytesIO
import json
import re
import wave
from zipfile import ZIP_DEFLATED, ZipFile

import yaml

from check_trime import (
    CONTRAST_THEME_IDS, FACTORY_THEME_IDS, INDUSTRIAL_THEME_IDS, LABELMAKER_ID,
    OSCILLOSCOPE_ID, PIXELBLOCK_ID, RIME_DIR, TYPEWRITER_ID, packaged_sound_files,
)

SCOPE_BANKS = {OSCILLOSCOPE_ID: 'scope', PIXELBLOCK_ID: 'pixel'}
FACTORY_BANKS = dict(zip(FACTORY_THEME_IDS, ('cast', 'wafer', 'air'), strict=True))
CONTRAST_ROLES = ('glyph-1', 'glyph-2', 'glyph-3', 'space', 'glyph-4', 'glyph-5', 'erase', 'return')
SAMPLE_RATE = 24000
SAMPLE_FRAMES = 2544  # 定稿試聽的每次按鍵均為 106 ms。


def prototype_data(prototype, script_id):
    pattern = rf'<script id="{re.escape(script_id)}" type="application/json">(.*?)</script>'
    match = re.search(pattern, prototype.read_text(encoding='utf-8'), re.S)
    if match is None:
        raise ValueError(f'{prototype.name} 缺少定案樣音 {script_id}')
    return json.loads(match[1])


def pcm_to_wave(pcm, rate):
    output = BytesIO()
    with wave.open(output, 'wb') as wav:
        wav.setparams((1, 2, rate, 0, 'NONE', 'not compressed'))
        wav.writeframes(pcm)
    return output.getvalue()


def validate_wave(stream, name):
    params = (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getcomptype())
    if params != (1, 2, SAMPLE_RATE, 'NONE'):
        raise ValueError(f'{name} 須為 24 kHz、16 位元、單聲道 PCM')


def decode_wave(encoded, name):
    data = b64decode(encoded, validate=True)
    with wave.open(BytesIO(data)) as sample:
        validate_wave(sample, name)
    return data


def numbered_clips(approved, counts):
    files = {}
    for kind, count in counts.items():
        if len(approved[kind]) != count:
            raise ValueError(f'{kind} 需要 {count} 個定案樣音')
        for index, encoded in enumerate(approved[kind], 1):
            name = f'{kind}-{index}.wav'
            files[name] = decode_wave(encoded, name)
    return files


def wav_paths(theme_id, files):
    return {f'soundeffect/{theme_id}/{name}': data for name, data in files.items()}


def sound_files(descriptor, files, comment):
    theme_id = descriptor['folder']
    content = (f'# {comment}\n' + yaml.safe_dump(descriptor, sort_keys=False)).encode()
    return {f'soundeffect/{theme_id}.sound.yaml': content, **wav_paths(theme_id, files)}


def typewriter_sound(theme_id, name, prototype):
    data = prototype_data(prototype, "sound-data")
    effects = {}
    indices = {}
    for kind in ('glyph', 'space', 'erase', 'control', 'return'):
        indices[kind] = []
        for index, encoded in enumerate(data['clips'][kind], 1):
            filename = f'{kind}-{index}.wav'
            indices[kind].append(len(effects))
            effects[filename] = pcm_to_wave(b64decode(encoded, validate=True), data['rate'])

    # 同文 3.3.13 的音效 YAML 禁用錨點。重複的音序用各自的 list。
    config = {
        'name': name,
        'folder': theme_id,
        'sound': list(effects),
        'keyset': [
            {'keys': ['KEYCODE_ENTER', 'KEYCODE_NUMPAD_ENTER'], 'inOrder': True, 'sounds': indices['return']},
            {'keys': ['KEYCODE_SPACE'], 'inOrder': False, 'sounds': indices['space']},
            {'keys': ['KEYCODE_DEL', 'KEYCODE_FORWARD_DEL'], 'inOrder': False, 'sounds': indices['erase']},
            {'keys': ['KEYCODE_SHIFT_LEFT', 'KEYCODE_SHIFT_RIGHT', 'KEYCODE_LANGUAGE_SWITCH',
                      'KEYCODE_TAB', 'KEYCODE_ESCAPE'], 'inOrder': True, 'sounds': indices['control']},
            {'min': 'KEYCODE_A', 'max': 'KEYCODE_Z', 'inOrder': False, 'sounds': indices['glyph'].copy()},
            {'min': 'KEYCODE_0', 'max': 'KEYCODE_9', 'inOrder': False, 'sounds': indices['glyph'].copy()},
            {'keys': ['KEYCODE_COMMA', 'KEYCODE_PERIOD', 'KEYCODE_SLASH', 'KEYCODE_SEMICOLON',
                      'KEYCODE_APOSTROPHE', 'KEYCODE_MINUS', 'KEYCODE_EQUALS', 'KEYCODE_GRAVE',
                      'KEYCODE_LEFT_BRACKET', 'KEYCODE_RIGHT_BRACKET', 'KEYCODE_BACKSLASH'],
             'inOrder': False, 'sounds': indices['glyph'].copy()},
        ],
    }
    return sound_files(config, effects, 'CC0 實錄剪輯：nvmbky · https://freesound.org/people/nvmbky/sounds/801118/')


def scope_sound(theme_id, name, prototype):
    bank = SCOPE_BANKS.get(theme_id, theme_id.removeprefix('v2-'))
    approved = prototype_data(prototype, 'sample-data')[bank]
    files = numbered_clips(approved, {'glyph': 3, 'space': 1, 'return': 1})
    descriptor = {
        'name': name, 'folder': theme_id, 'sound': list(files),
        'keyset': [
            {'keys': ['KEYCODE_ENTER', 'KEYCODE_NUMPAD_ENTER'], 'inOrder': True, 'sounds': [4]},
            {'keys': ['KEYCODE_SPACE'], 'inOrder': True, 'sounds': [3]},
            {'keys': ['KEYCODE_DEL', 'KEYCODE_FORWARD_DEL'], 'inOrder': True, 'sounds': [2]},
            {'keys': ['KEYCODE_SHIFT_LEFT', 'KEYCODE_SHIFT_RIGHT', 'KEYCODE_SWITCH_CHARSET', 'KEYCODE_EISU',
                      'KEYCODE_LANGUAGE_SWITCH', 'KEYCODE_TAB', 'KEYCODE_ESCAPE'], 'inOrder': True, 'sounds': [1]},
            {'min': 'KEYCODE_A', 'max': 'KEYCODE_Z', 'inOrder': False, 'sounds': [0, 1, 2]},
            {'min': 'KEYCODE_0', 'max': 'KEYCODE_9', 'inOrder': False, 'sounds': [0, 1, 2]},
            {'keys': ['KEYCODE_COMMA', 'KEYCODE_PERIOD', 'KEYCODE_SLASH', 'KEYCODE_SEMICOLON',
                      'KEYCODE_APOSTROPHE', 'KEYCODE_PLUS', 'KEYCODE_MINUS', 'KEYCODE_EQUALS'],
             'inOrder': False, 'sounds': [0, 1, 2]},
        ],
    }
    return sound_files(descriptor, files, '樣音取自定案 HTML。退格和切換各用一個短鍵音變體。')


def factory_sound(theme_id, name, prototype):
    approved = prototype_data(prototype, 'sample-data')[FACTORY_BANKS[theme_id]]
    paths = {f'{kind}.wav': decode_wave(approved[kind], f'{name} {kind}')
             for kind in ('key', 'space', 'delete', 'return')}
    keys = [
        {'keys': ['KEYCODE_ENTER', 'KEYCODE_NUMPAD_ENTER'], 'inOrder': True, 'sounds': [3]},
        {'keys': ['KEYCODE_DEL', 'KEYCODE_FORWARD_DEL'], 'inOrder': True, 'sounds': [2]},
        {'keys': ['KEYCODE_SPACE'], 'inOrder': True, 'sounds': [1]},
        {'min': 'KEYCODE_A', 'max': 'KEYCODE_Z', 'inOrder': True, 'sounds': [0]},
        {'min': 'KEYCODE_0', 'max': 'KEYCODE_9', 'inOrder': True, 'sounds': [0]},
    ]
    descriptor = {'name': name, 'folder': theme_id, 'sound': list(paths), 'keyset': keys}
    return sound_files(descriptor, paths, '合成樣音取自定案互動原型。')


def contrast_sound(theme_id, name, prototype):
    data = prototype_data(prototype, 'tongwen-contrast-data')
    url = data['sounds'][theme_id.removeprefix('v2-')]
    clips = {}
    with wave.open(BytesIO(b64decode(url.split(',', 1)[1], validate=True))) as demo:
        validate_wave(demo, name)
        for role, beat in zip(CONTRAST_ROLES, data['beats'], strict=True):
            demo.setpos(round(beat * SAMPLE_RATE))
            pcm = demo.readframes(SAMPLE_FRAMES)
            if len(pcm) != SAMPLE_FRAMES * 2:
                raise ValueError(f'{theme_id} 的 {role} 樣音不完整')
            clips[f'{role}.wav'] = pcm_to_wave(pcm, SAMPLE_RATE)

    glyphs = [i for i, role in enumerate(CONTRAST_ROLES) if role.startswith('glyph')]
    descriptor = {
        'name': name, 'folder': theme_id, 'sound': list(clips),
        'keyset': [
            {'keys': ['KEYCODE_ENTER', 'KEYCODE_NUMPAD_ENTER'], 'inOrder': True, 'sounds': [CONTRAST_ROLES.index('return')]},
            {'keys': ['KEYCODE_SPACE'], 'inOrder': True, 'sounds': [CONTRAST_ROLES.index('space')]},
            {'keys': ['KEYCODE_DEL', 'KEYCODE_FORWARD_DEL'], 'inOrder': True, 'sounds': [CONTRAST_ROLES.index('erase')]},
            {'keys': ['KEYCODE_SHIFT_LEFT', 'KEYCODE_SHIFT_RIGHT', 'KEYCODE_EISU', 'KEYCODE_LANGUAGE_SWITCH',
                      'KEYCODE_TAB', 'KEYCODE_ESCAPE'], 'inOrder': True, 'sounds': [glyphs[0]]},
            {'min': 'KEYCODE_A', 'max': 'KEYCODE_Z', 'inOrder': False, 'sounds': glyphs.copy()},
            {'min': 'KEYCODE_0', 'max': 'KEYCODE_9', 'inOrder': False, 'sounds': glyphs.copy()},
            {'keys': ['KEYCODE_COMMA', 'KEYCODE_PERIOD', 'KEYCODE_SLASH', 'KEYCODE_SEMICOLON',
                      'KEYCODE_APOSTROPHE', 'KEYCODE_PLUS', 'KEYCODE_MINUS', 'KEYCODE_EQUALS', 'KEYCODE_GRAVE',
                      'KEYCODE_LEFT_BRACKET', 'KEYCODE_RIGHT_BRACKET', 'KEYCODE_BACKSLASH'],
             'inOrder': False, 'sounds': glyphs.copy()},
        ],
    }
    return sound_files(descriptor, clips, '由定稿合成試聽逐鍵截取。')


def labelmaker_sound(theme_id, _name, prototype):
    approved = prototype_data(prototype, 'labelmaker-sound-data')
    files = numbered_clips(approved, {'glyph': 3, 'space': 1, 'erase': 1, 'control': 1, 'return': 1})
    relative = f'soundeffect/{theme_id}.sound.yaml'
    content = (RIME_DIR / relative).read_bytes()
    descriptor = yaml.safe_load(content)
    if descriptor['folder'] != theme_id or descriptor['sound'] != list(files):
        raise ValueError('音效清單與定案樣音不一致')
    return {relative: content, **wav_paths(theme_id, files)}


SOUND_IMPORTERS = {
    TYPEWRITER_ID: typewriter_sound,
    LABELMAKER_ID: labelmaker_sound,
    **dict.fromkeys((*SCOPE_BANKS, *INDUSTRIAL_THEME_IDS), scope_sound),
    **dict.fromkeys(FACTORY_THEME_IDS, factory_sound),
    **dict.fromkeys(CONTRAST_THEME_IDS, contrast_sound),
}


def collect_sound(theme_id, name, prototype):
    if prototype is None:
        return packaged_sound_files(theme_id)
    importer = SOUND_IMPORTERS.get(theme_id)
    if importer is None:
        raise ValueError(f'{theme_id} 沒有原型鍵音匯入流程')
    return importer(theme_id, name, prototype)


def write_sound_zip(directory, name, files):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f'{name}-sound.zip'
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as archive:
        for asset, data in files.items():
            archive.writestr(asset, data)
    print(f'→ {path}')
