# Lucas Jones 2024
from app_components import display_x, display_y

colors = {
    "pale_green": (175, 201, 68),
    "mid_green": (82, 131, 41),
    "dark_green": (33, 48, 24),
    "yellow": (294, 226, 0),
    "orange": (246, 127, 2),
    "pink": (245, 80, 137),
    "blue": (46, 173, 217),
}

def clear_background(ctx, color=None):
    if color is None:
        color = colors["pale_green"]
    ctx.rgb(*color).rectangle(-display_x / 2, -display_y / 2, display_x, display_y).fill()
