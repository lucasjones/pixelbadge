# Lucas Jones 2024
import random
import math

# from sys_colors import hsv_to_rgb, rgb_to_hsv
from app_components import display_x, display_y

from .lj_utils.lj_display_utils import colors, clear_background
from .lj_utils.base_types import Utility
from .lj_utils.color import hsv_to_rgb

class RandomGrid(Utility):
    def __init__(self, app, grid_size=20):
        super().__init__(app)
        self.grid_size = grid_size
        self.grid = self.generate_grid()
    
    def generate_grid(self):
        rows = display_y // self.grid_size
        cols = display_x // self.grid_size
        return [
            [self.random_color() for _ in range(cols)] for _ in range(rows)
        ]
    
    def random_color(self):
        # return (random.random(), random.random(), random.random())
        # only fully saturated colors (generate random hue then convert to RGB)
        hue = random.random()
        return hsv_to_rgb(hue * math.tau, 0.8, 0.4)
    
    def draw(self, ctx):
        for row_index, row in enumerate(self.grid):
            for col_index, color in enumerate(row):
                if color is None:
                    continue
                x = col_index * self.grid_size - display_x / 2
                y = row_index * self.grid_size - display_y / 2
                ctx.rgb(*color).rectangle(x, y, self.grid_size, self.grid_size).fill()
