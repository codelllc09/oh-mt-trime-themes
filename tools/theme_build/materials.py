"""藍曬、刺繡布章與彩繪玻璃外觀。"""

from functools import partial
from math import hypot, pi, sin

from PIL import Image, ImageDraw

from check_trime import CYANOTYPE_ID, PATCHWORK_ID, STAINEDGLASS_ID
from render_keyboard import DP, SCREEN_W
from .core import SCALE, active_scheme, draw_globe, gradient, skin_keys


STRIP_HEIGHT = 136
NUMBER_COLORS = {
    CYANOTYPE_ID: ('#C6DCE4', '#AACAD9'),
    PATCHWORK_ID: ('#4C6B7B', '#405D6D'),
    STAINEDGLASS_ID: ('#D9A963', '#E4B675'),
}
CAP_COLORS = {
    'glyph': ('key_back_color', 'hilited_key_back_color'),
    'control': ('off_key_back_color', 'hilited_off_key_back_color'),
    'return': ('accent_fill', 'accent_fill_hl'),
}
CAP_EDGES = {
    CYANOTYPE_ID: (7, '#6086A4', '#0D2A49'),
    PATCHWORK_ID: (14, '#2B3A47', '#5B483A'),
    STAINEDGLASS_ID: (5, '#10171E', '#0B1116'),
}


def fern(draw, base, tip, curve, spread, opacity, height):
    def axis(t):
        return tuple(a + (b - a) * t + bend * 4 * t * (1 - t)
                     for a, b, bend in zip(base, tip, curve))

    def pixel(point):
        x, y = point
        return round(x * SCALE), round(y * height / 792 * SCALE)

    ink = (222, 241, 229, opacity)
    draw.line([pixel(axis(i / 40)) for i in range(41)], fill=ink, width=9, joint='curve')
    for side in (-1, 1):
        for i in range(14):
            t = .13 + i * .057 + (.014 if side == 1 else 0)
            root = axis(t)
            previous, following = axis(t - .01), axis(t + .01)
            dx, dy = following[0] - previous[0], following[1] - previous[1]
            length = hypot(dx, dy)
            dx, dy = dx / length, dy / length
            nx, ny = -dy * side, dx * side
            span = spread * sin(pi * t) ** .76 * (1 - .44 * t)
            leaf = []
            for edge, samples in ((1, range(15)), (-1, range(14, -1, -1))):
                for j in samples:
                    u = j / 14
                    arc = sin(pi * u)
                    width = span * .115 * arc ** .80 * (1 if j % 2 else .76) * edge
                    x = root[0] + (nx + dx * .43) * span * u + dx * span * .2 * arc - dy * width
                    y = root[1] + (ny + dy * .43) * span * u + dy * span * .2 * arc + dx * width
                    leaf.append(pixel((x, y)))
            draw.polygon(leaf, fill=ink)


def linen(size):
    image = Image.new('RGB', size, '#C7AE87')
    w, h = size
    draw = ImageDraw.Draw(image, 'RGBA')
    for y in range(1, h, 8):
        draw.line((0, y, w, y), fill=(102, 72, 44, 45), width=2)
    for x in range(3, w, 8):
        draw.line((x, 0, x, h), fill=(255, 242, 211, 78), width=2)
    return image


def case_texture(theme_id, height):
    if theme_id == PATCHWORK_ID:
        return linen((SCREEN_W, height))
    if theme_id == STAINEDGLASS_ID:
        return gradient((SCREEN_W, height), '#202A33', '#121C25').convert('RGB')

    image = gradient((SCREEN_W * SCALE, height * SCALE), '#275B89', '#123154').convert('RGB')
    draw = ImageDraw.Draw(image, 'RGBA')
    fern(draw, (1103, 801), (675, 449), (17, 48), 125, 94, height)
    fern(draw, (-104, 566), (340, 186), (-49, 36), 120, 89, height)
    fern(draw, (73, 773), (1055, 170), (-112, -28), 225, 204, height)
    return image.resize((SCREEN_W, height), Image.Resampling.LANCZOS)


def stitches(draw, box, fill, scale):
    left, top, right, bottom = box
    dash, gap, corner = 5 * scale, 4 * scale, 7 * scale
    for x in range(left + corner, right - corner, dash + gap):
        end = min(x + dash, right - corner)
        draw.line((x, top, end, top), fill=fill, width=scale)
        draw.line((x, bottom, end, bottom), fill=fill, width=scale)
    for y in range(top + corner, bottom - corner, dash + gap):
        end = min(y + dash, bottom - corner)
        draw.line((left, y, left, end), fill=fill, width=scale)
        draw.line((right, y, right, end), fill=fill, width=scale)


def strip_texture(theme_id):
    w, h = SCREEN_W, STRIP_HEIGHT
    if theme_id == CYANOTYPE_ID:
        image = Image.new('RGB', (w, h), '#153F70')
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((17, 17, w - 14, h - 11), 5, fill='#0D2C4E')
        draw.rounded_rectangle((15, 11, w - 17, h - 17), 5, fill='#F3ECD5', outline='#F7F4E3', width=2)
        for x in range(33, 420, 23):
            draw.line((x, h - 24, x, h - 19), fill='#95A5A5', width=2)
        return image
    if theme_id == PATCHWORK_ID:
        image = linen((w, h))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((24, 15, w - 19, h - 9), 12, fill='#846547')
        draw.rounded_rectangle((21, 10, w - 23, h - 15), 12, fill='#F2E4CA', outline='#9A7752', width=2)
        stitches(draw, (29, 18, w - 31, h - 23), '#9B815C', 2)
        return image

    image = Image.new('RGB', (w, h), '#263748')
    draw = ImageDraw.Draw(image)
    draw.polygon(((0, 0), (w // 5, 0), (w // 9, h), (0, h)), fill='#315069')
    draw.polygon(((w * 9 // 10, 0), (w, 0), (w, h), (w * 4 // 5, h)), fill='#503B55')
    draw.rectangle((0, 0, w, 6), fill='#151B22')
    draw.rectangle((0, h - 7, w, h), fill='#151B22')
    draw.line((0, 7, w, 7), fill='#C3A56A', width=2)
    draw.line((0, h - 8, w, h - 8), fill='#8995AB', width=2)
    return image


def cap_texture(theme_id, scheme, kind, width, height, pressed):
    w, h = width * SCALE, height * SCALE
    radius, border, shadow = CAP_EDGES[theme_id]
    radius *= SCALE
    color_kind = 'control' if kind == 'globe' else kind
    if color_kind == 'number':
        fill = NUMBER_COLORS[theme_id][pressed]
    else:
        fill = '#' + scheme[CAP_COLORS[color_kind][pressed]][3:]

    image = Image.new('RGBA', (w, h))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((0, 4, w - 1, h - 1), radius, fill=shadow)
    shift = 5 if pressed else 0
    face_height = h - 8
    face = Image.new('RGB', (w, face_height), fill)
    texture = ImageDraw.Draw(face, 'RGBA')
    if theme_id == PATCHWORK_ID:
        for x in range(-face_height, w, 13):
            texture.line((x, 0, x + face_height, face_height), fill=(248, 225, 186, 20), width=2)
        stitches(texture, (13, 13, w - 14, face_height - 14), (241, 229, 199, 168), SCALE)
    elif theme_id == STAINEDGLASS_ID:
        texture.polygon(((0, 0), (w, 0), (w * .68, face_height * .19), (0, face_height * .31)),
                        fill=(249, 244, 219, 58))
        texture.polygon(((w, face_height * .68), (w, face_height), (0, face_height)), fill=(14, 12, 23, 60))
        texture.line((9, 6, w - 9, 6), fill=(255, 244, 221, 126), width=2)
    elif kind == 'number':
        for x in range(18, w - 18, 32):
            texture.line((x, 6, x, 14), fill=(45, 84, 118, 83), width=2)

    mask = Image.new('L', face.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, face_height - 1), radius, fill=255)
    image.paste(face, (0, shift), mask)
    draw.rounded_rectangle((0, shift, w - 1, face_height - 1 + shift), radius, outline=border, width=4)
    if kind == 'globe':
        color = '#' + scheme['fn_text_color'][3:]
        draw_globe(draw, (w / 2, face_height * .58 + shift), min(w, h) * .21, color)
    return image.resize((width, height), Image.Resampling.LANCZOS)


def render(theme_id, theme):
    scheme = active_scheme(theme)
    height = round(theme['style']['keyboard_height'] * DP) + STRIP_HEIGHT
    images = {'case.png': case_texture(theme_id, height), 'strip.png': strip_texture(theme_id)}
    skin_keys(theme, images, partial(cap_texture, theme_id, scheme), theme_id.removeprefix('v2-'))
    return images
