"""卡帶、水磨石與包浩斯外觀。"""

from functools import partial
from math import cos, sin, tau
from random import Random

from PIL import Image, ImageColor, ImageDraw

from check_trime import CASSETTE_ID, TERRAZZO_ID
from render_keyboard import SCREEN_W
from .core import SCALE, active_scheme, case_geometry, draw_globe, gradient, rounded_layer, skin_keys


CAP_COLORS = {
    'glyph': ('key_back_color', 'hilited_key_back_color'),
    'control': ('fn_back_color', 'hilited_off_key_back_color'),
    'number': ('on_key_back_color', 'hilited_on_key_back_color'),
    'return': ('accent_fill', 'accent_fill_hl'),
    'space': ('space_back_color', 'space_down_color'),
}


def rgb(scheme, name):
    return '#' + scheme[name][3:]


def shade(color, target, amount):
    channels = ImageColor.getrgb(color)
    return '#' + ''.join(f'{round(channel * (1 - amount) + target * amount):02x}' for channel in channels)


def cassette_case(height):
    image = gradient((SCREEN_W, height), '#554E44', '#302D28').convert('RGB')
    draw = ImageDraw.Draw(image, 'RGBA')
    for y in range(0, height, 3):
        draw.line((0, y, SCREEN_W, y), fill=(255, 241, 209, 8))
    return image


def cassette_strip(case, height):
    image = case.crop((0, 0, SCREEN_W, height)).convert('RGBA')
    right, bottom = SCREEN_W - 17, height - 8
    rounded_layer(image, (16, 6, right, bottom), 19, '#877355', '#5C4A38')
    rounded_layer(image, (19, 9, right - 3, bottom - 3), 16, '#191611', '#241B14')
    rounded_layer(image, (25, 14, right - 9, bottom - 8), 12, '#3B3025', '#211D19')
    draw = ImageDraw.Draw(image)
    left_hub, right_hub, center = 634, 802, (height - 2) / 2
    draw.rectangle((left_hub, center - 12, right_hub, center + 12), fill='#3E2D22')
    for y in range(round(center) - 10, round(center) + 11, 4):
        draw.line((left_hub, y, right_hub, y), fill='#6D4A33', width=2)
    for x in (left_hub, right_hub):
        draw.ellipse((x - 30, center - 30, x + 30, center + 30), fill='#4C392A', outline='#745838', width=2)
        draw.ellipse((x - 21, center - 21, x + 21, center + 21), fill='#795D40')
        draw.ellipse((x - 11, center - 11, x + 11, center + 11), fill='#33271F')
        for index in range(6):
            angle = index * tau / 6
            px, py = x + 16 * cos(angle), center + 16 * sin(angle)
            draw.ellipse((px - 2, py - 2, px + 2, py + 2), fill='#58412D')
    return image.convert('RGB')


def terrazzo_case(height):
    rng = Random(7463)
    draft_height = 792
    image = Image.new('RGB', (SCREEN_W, draft_height), '#DED3C2')
    draw = ImageDraw.Draw(image)
    colors = ('#9E604E', '#6E8279', '#CD987F', '#B28C53', '#778591', '#EAE4D8', '#A8A092', '#515F57')
    for count, minimum, maximum in ((700, 1, 5), (260, 6, 19), (62, 16, 34)):
        for _ in range(count):
            x, y = rng.randrange(SCREEN_W), rng.randrange(draft_height)
            width = rng.uniform(minimum, maximum)
            depth = width * rng.uniform(.37, 1.12)
            sides, rotation = rng.choice((4, 5, 6)), rng.uniform(0, tau)
            points = []
            for vertex in range(sides):
                angle = rotation + vertex * tau / sides + rng.uniform(-.19, .19)
                points.append((x + width * rng.uniform(.28, .65) * cos(angle),
                               y + depth * rng.uniform(.28, .65) * sin(angle)))
            draw.polygon(points, fill=rng.choice(colors))
    return image.resize((SCREEN_W, height), Image.Resampling.LANCZOS)


def terrazzo_strip(case, height):
    image = case.crop((0, 0, SCREEN_W, height)).convert('RGBA')
    rounded_layer(image, (21, 12, SCREEN_W - 20, height - 5), 7, '#B4A48C', '#8C785F')
    rounded_layer(image, (21, 8, SCREEN_W - 20, height - 9), 6, '#F9F5EC', '#F1E8DA')
    ImageDraw.Draw(image).rounded_rectangle((21, 8, SCREEN_W - 21, height - 10), 6, outline='#A79A86', width=2)
    return image.convert('RGB')


def bauhaus_strip(base, height):
    image = Image.new('RGB', (SCREEN_W, height), base)
    draw = ImageDraw.Draw(image)
    # 淺色內面讓候選字可以掃過色塊，原色保留在圖形下緣。
    draw.ellipse((426, 15, 510, height - 10), fill='#E08770')
    draw.chord((426, 15, 510, height - 10), 65, 115, fill='#C63829')
    draw.rectangle((597, 23, 757, height - 11), fill='#8DA1C2')
    draw.rectangle((597, height - 16, 757, height - 11), fill='#234489')
    draw.rectangle((758, height - 26, 833, height - 11), fill='#EFBC32')
    draw.rectangle((0, height - 5, SCREEN_W, height - 1), fill='#191919')
    return image


def cap_texture(theme_id, scheme, kind, width, height, pressed):
    w, h = width * SCALE, height * SCALE
    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    color = rgb(scheme, CAP_COLORS['control' if kind == 'globe' else kind][pressed])
    shift = 0
    if theme_id == CASSETTE_ID:
        shift = 6 if pressed else 0
        depth = 9 if pressed else 16
        rounded_layer(image, (0, 4, w, h), 15, '#29221C', '#211C18')
        rounded_layer(image, (2, shift, w - 2, h - depth), 13, shade(color, 255, .13), shade(color, 0, .13))
        draw.line((16, shift + 3, w - 17, shift + 3), fill=shade(color, 255, .28), width=2)
        if kind == 'space':
            draw.line((13, h - depth - 4, w - 14, h - depth - 4), fill='#BA895A', width=3)
    elif theme_id == TERRAZZO_ID:
        shift = 4 if pressed else 0
        bottom, cut = h - (6 if pressed else 10), 14
        points = ((cut, shift), (w - cut - 1, shift), (w - 1, cut + shift), (w - 1, bottom - cut),
                  (w - cut - 1, bottom), (cut, bottom), (0, bottom - cut), (0, cut + shift))
        draw.polygon(points, fill=color)
        draw.line([points[i] for i in (6, 7, 0, 1, 2)], fill=shade(color, 255, .38), width=4)
        draw.line([points[i] for i in (2, 3, 4, 5, 6)], fill=shade(color, 0, .21), width=4)
    elif kind == 'glyph' and not pressed:
        draw.rectangle((0, h - 7, w - 1, h - 1), fill='#191919')
    else:
        draw.rectangle((0, 0, w - 1, h - 1), fill=color)
        if pressed:
            draw.rectangle((0, 0, w - 1, h - 1), outline=shade(color, 0, .42), width=4)
    if kind == 'globe':
        draw_globe(draw, (w / 2, h * .56 + shift), min(w, h) * .19, rgb(scheme, 'fn_text_color'))
    return image.resize((width, height), Image.Resampling.LANCZOS)


def render(theme_id, theme):
    scheme = active_scheme(theme)
    height, bar = case_geometry(theme)
    if theme_id == CASSETTE_ID:
        case = cassette_case(height)
        strip = cassette_strip(case, bar)
    elif theme_id == TERRAZZO_ID:
        case = terrazzo_case(height)
        strip = terrazzo_strip(case, bar)
    else:
        base = rgb(scheme, 'keyboard_back_color')
        case = Image.new('RGB', (SCREEN_W, height), base)
        strip = bauhaus_strip(base, bar)
    images = {'case.png': case, 'strip.png': strip}
    skin_keys(theme, images, partial(cap_texture, theme_id, scheme),
              theme_id.removeprefix('v2-'), separate_space=True)
    return images
