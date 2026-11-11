"""從主題源檔生成同文 V2 主題。"""

from check_trime import (
    CALCULATOR_ID, CONTOUR_ID, CONTRAST_THEME_IDS, FACTORY_THEME_IDS, HALFTONE_ID,
    INDUSTRIAL_THEME_IDS, LABELMAKER_ID, MATERIAL_THEME_IDS, OSCILLOSCOPE_ID,
    PIXELBLOCK_ID, RIME_DIR, THEME_DIR, TYPEWRITER_ID, dump_theme,
)

from . import contrast, factory, industrial, materials, mechanical, print_skins, screen
from .core import inherit_skin, write_assets
from .sound import collect_sound, write_sound_zip

RENDERERS = {
    TYPEWRITER_ID: mechanical.typewriter,
    CALCULATOR_ID: mechanical.calculator,
    LABELMAKER_ID: mechanical.labelmaker,
    HALFTONE_ID: print_skins.halftone,
    CONTOUR_ID: print_skins.contour,
    **dict.fromkeys(MATERIAL_THEME_IDS, materials.render),
    **dict.fromkeys((OSCILLOSCOPE_ID, PIXELBLOCK_ID), screen.render),
    **dict.fromkeys(CONTRAST_THEME_IDS, contrast.render),
    **dict.fromkeys(INDUSTRIAL_THEME_IDS, industrial.render),
    **dict.fromkeys(FACTORY_THEME_IDS, factory.render),
}


def build_theme(theme_id, *, check, prototype, sound_zips):
    theme = inherit_skin(theme_id)
    images = RENDERERS[theme_id](theme_id, theme)
    sound = collect_sound(theme_id, theme['name'], prototype)
    backgrounds = RIME_DIR / 'backgrounds' / theme['style']['background_folder']
    target = THEME_DIR / f'{theme_id}.trime.yaml'
    files = {target: dump_theme(theme).encode(), **{RIME_DIR / path: data for path, data in sound.items()}}
    if theme_id == HALFTONE_ID:
        files[RIME_DIR / 'fonts' / 'halftone_latin.ttf'] = print_skins.latin_font()
    write_assets({backgrounds / name: image for name, image in images.items()}, files, check=check)
    print(f'✓ {target.name}，{len(images)} 張背景' + ('同步' if check else ''))
    if sound_zips is not None and not check:
        write_sound_zip(sound_zips, theme['name'], sound)
