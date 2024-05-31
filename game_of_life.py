import random

from events.input import ButtonDownEvent, BUTTON_TYPES, ButtonUpEvent
from app_components import display_x, display_y
# from sys_colors import hsv_to_rgb, rgb_to_hsv
from tildagonos import tildagonos

from .lj_utils.lj_display_utils import colors, clear_background
from .lj_utils.base_types import Utility
from .lj_utils.lj_button_labels import ButtonLabels
from .lj_utils.color import hsv_to_rgb

class ConwaysGameOfLife(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.grid_pixel_width = display_x
        self.grid_pixel_height = display_y
        self.cell_size = 10
        self.grid_size_x = self.grid_pixel_width // self.cell_size
        self.grid_size_y = self.grid_pixel_height // self.cell_size
        self.timer = 0
        self.interval = 150
        self.started = False
        self.grid = None
        self.new_grid = None
        self.button_labels = ButtonLabels(app,
            labels={
                "CANCEL": "Exit",
                "UP": "size+",
                "DOWN": "size-",
                "RIGHT": "Reset"
            },
            text_color=(1,1,1),
            bg_color=(0,0,0),
            bg_pressed_color=(1,1,1),
            text_pressed_color=(0,0,0),
            fade_out_time=4000,
        )
    
    def on_start(self):
        self.randomize_grid()
        self.started = True
        self.button_labels.reset()
    
    def on_exit(self):
        self.started = False
        self.grid = None
        self.new_grid = None
    
    def randomize_grid(self):
        print("Randomizing grid")
        if self.grid is None or len(self.grid) != self.grid_size_x * self.grid_size_y:
            self.grid = [random.choice([0, 1]) for _ in range(self.grid_size_x * self.grid_size_y)]
        else:
            for idx in range(len(self.grid)):
                self.grid[idx] = random.choice([0, 1])
        return self.grid

    def update(self, delta):
        self.button_labels.update(delta)
        if not self.started:
            return
        self.timer += delta
        # print(f"conway Timer: {self.timer}, Interval: {self.interval}")
        if self.timer >= self.interval:
            new_grid = self.next_generation()
            for idx in range(len(self.grid)):
                self.grid[idx] = new_grid[idx]
            self.timer = 0
    
    def update_leds(self):
        for i in range(12):
            tildagonos.leds[i + 1] = (0, 0, 0)
        tildagonos.leds.write()

    def draw(self, ctx):
        if not self.started:
            return
        for idx in range(len(self.grid)):
            x = idx % self.grid_size_x
            y = idx // self.grid_size_x
            if self.get_grid(x, y) == 1:
                ctx.rgb(1, 1, 1)
            else:
                ctx.rgb(0, 0, 0)
            ctx.rectangle(x * self.cell_size - self.grid_pixel_width // 2, y * self.cell_size - self.grid_pixel_height // 2, self.cell_size, self.cell_size).fill()
        self.button_labels.draw(ctx)
    
    def get_grid(self, x, y):
        return self.grid[y*self.grid_size_x + x]

    def next_generation(self):
        if self.new_grid is None or len(self.new_grid) != len(self.grid):
            self.new_grid = [0 for _ in range(len(self.grid))]
        else:
            for idx in range(len(self.grid)):
                self.new_grid[idx] = 0

        for idx in range(len(self.grid)):
            x = idx % self.grid_size_x
            y = idx // self.grid_size_x
            live_neighbors = self.count_live_neighbors(x, y)
            if self.get_grid(x, y) == 1:
                if live_neighbors < 2 or live_neighbors > 3:
                    self.new_grid[y*self.grid_size_x + x] = 0
                else:
                    self.new_grid[y*self.grid_size_x + x] = 1
            else:
                if live_neighbors == 3:
                    self.new_grid[y*self.grid_size_x + x] = 1
        # if grid == new_grid, then randomize the grid
        new_grid = self.new_grid
        if self.grid == new_grid:
            new_grid = self.randomize_grid()
        return new_grid

    def count_live_neighbors(self, x, y):
        live_neighbors = 0
        for i in range(-1, 2):
            for j in range(-1, 2):
                if i == 0 and j == 0:
                    continue
                if 0 <= y + i < self.grid_size_y and 0 <= x + j < self.grid_size_x:
                    live_neighbors += self.get_grid(x + j, y + i)
        return live_neighbors

    def handle_buttondown(self, event: ButtonDownEvent):
        # if BUTTON_TYPES["UP"] in event.button:
        #     self.interval = max(10, self.interval - 50)
        #     print(f"Decreased interval to: {self.interval}")
        # elif BUTTON_TYPES["DOWN"] in event.button:
        #     self.interval = min(10000, self.interval + 50)
        #     print(f"Increased interval to: {self.interval}")
        # change grid size with UP and DOWN buttons instead (minimum 2, maximum 50)
        cell_sizes = [6, 8, 10, 12, 15, 20, 24, 30, 40]
        if BUTTON_TYPES["UP"] in event.button:
            current_index = cell_sizes.index(self.cell_size)
            self.cell_size = cell_sizes[(current_index + 1) % len(cell_sizes)]
            self.grid_size_x = self.grid_pixel_width // self.cell_size
            self.grid_size_y = self.grid_pixel_height // self.cell_size
            self.grid = self.randomize_grid()
            print(f"Changed cell size to: {self.cell_size}, grid size: {self.grid_size_x}x{self.grid_size_y}")
        elif BUTTON_TYPES["DOWN"] in event.button:
            current_index = cell_sizes.index(self.cell_size)
            self.cell_size = cell_sizes[(current_index - 1) % len(cell_sizes)]
            self.grid_size_x = self.grid_pixel_width // self.cell_size
            self.grid_size_y = self.grid_pixel_height // self.cell_size
            self.grid = self.randomize_grid()
            print(f"Changed cell size to: {self.cell_size}, grid size: {self.grid_size_x}x{self.grid_size_y}")
        # right button randomizes the grid
        elif BUTTON_TYPES["RIGHT"] in event.button:
            self.randomize_grid()
        return False