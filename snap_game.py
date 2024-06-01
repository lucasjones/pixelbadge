# Lucas Jones 2024
import asyncio
import random
import time
import math

from events.input import Buttons, BUTTON_TYPES, ButtonDownEvent, ButtonUpEvent
from app_components import display_x, display_y
from tildagonos import tildagonos

from .lj_utils.base_types import Utility
from .lj_utils.lj_display_utils import colors, clear_background

class SnapGame(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.state = "waiting"
        self.reset_game()

    def on_start(self):
        self.state = "waiting"
        self.reset_game()
    
    def reset_game(self):
        self.winner = None
        self.flash_time = 0
        self.player_1_ready = False
        self.player_2_ready = False
        self.too_early = False
        self.win_cooldown = 0

    def on_exit(self):
        pass

    def draw(self, ctx):
        if self.state == "waiting":
            clear_background(ctx)
            # draw red rectangle on top half and blue rectangle on bottom half
            ctx.rgb(1, 0, 0).rectangle(-display_x * 0.5, -display_y * 0.5, display_x, display_y * 0.5).fill()
            ctx.rgb(0, 0, 1).rectangle(-display_x * 0.5, 0, display_x, display_y * 0.5).fill()
            ctx.font_size = 20
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            ctx.rgb(0, 0, 0)
            ctx.rotate(math.pi)
            ctx.move_to(0, 50).text("- Press as soon")
            ctx.move_to(0, 70).text("as the lights flash")
            ctx.rotate(-math.pi)
            ctx.move_to(0, 50).text("- Press as soon")
            ctx.move_to(0, 70).text("as the lights flash")
            ctx.rotate(math.pi)
            if not self.player_1_ready:
                ctx.move_to(0, 10).text("- Press your button")
                ctx.move_to(0, 30).text("when ready to begin")
            ctx.rotate(-math.pi)
            if not self.player_2_ready:
                ctx.move_to(0, 10).text("- Press your button")
                ctx.move_to(0, 30).text("when ready to begin")
        elif self.state == "ready":
            clear_background(ctx)
            ctx.rgb(0, 0, 0)
            ctx.rectangle(-display_x * 0.5, -display_y * 0.5, display_x, display_y).fill()
            # ctx.rgb(1, 1, 1)
            # ctx.font_size = 20
            # ctx.text_align = ctx.CENTER
            # ctx.text_baseline = ctx.MIDDLE
            # ctx.move_to(0, 0).text("snap")
        elif self.state == "flashing":
            clear_background(ctx, (1, 1, 1))
        elif self.state == "winner":
            clear_background(ctx)
            ctx.rgb(*self.player_color(self.winner))
            ctx.rectangle(-display_x * 0.5, -display_y * 0.5, display_x, display_y).fill()
            ctx.rgb(0, 0, 0)
            ctx.font_size = 30
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            if self.winner == "red":
                ctx.move_to(0, -40).text("Red wins!")
                if self.too_early:
                    ctx.move_to(0, 0).text("Blue was too early!")
            else:
                ctx.move_to(0, -40).text("Blue wins!")
                if self.too_early:
                    ctx.move_to(0, 0).text("Red was too early!")
            if self.win_cooldown <= 0:
                ctx.move_to(0, 40).text("Click to play again")

    def update(self, delta):
        self.win_cooldown -= delta
        if self.state == "waiting":
            # set LEDS 1,2,3,10,11,12 to red, 4,5,6,7,8,9 to blue
            red_color = self.player_color_led("red")
            blue_color = self.player_color_led("blue")
            for i in range(3):
                tildagonos.leds[i+1] = red_color
                tildagonos.leds[i+10] = red_color
                tildagonos.leds[i+4] = blue_color
                tildagonos.leds[i+7] = blue_color
            tildagonos.leds.write()
        elif self.state == "ready":
            self.flash_time -= delta
            if self.flash_time <= 0:
                self.state = "flashing"
                for i in range(12):
                    tildagonos.leds[i+1] = (255, 255, 255)
            else:
                for i in range(12):
                    tildagonos.leds[i+1] = (0, 0, 0)
            tildagonos.leds.write()
        elif self.state == "winner" and self.winner:
            color = self.player_color_led(self.winner)
            for i in range(12):
                tildagonos.leds[i+1] = color
            tildagonos.leds.write()

    def update_leds(self):
        pass
    
    def player_color(self, name):
        if name == "red":
            return (1, 0, 0)
        elif name == "blue":
            return (0, 0, 1)
        else:
            return (0, 1, 0)
    
    def player_color_led(self, name):
        if name == "red":
            return (255, 0, 0)
        elif name == "blue":
            return (0, 0, 255)
        else:
            return (0, 255, 0)

    def handle_buttondown(self, event: ButtonDownEvent):
        if self.state == "waiting":
            if BUTTON_TYPES["UP"] in event.button:
                self.player_1_ready = True
            elif BUTTON_TYPES["DOWN"] in event.button:
                self.player_2_ready = True
            
            if self.player_1_ready and self.player_2_ready:
                self.start_game()
        elif self.state == "flashing" or self.state == "ready":
            if BUTTON_TYPES["UP"] in event.button:
                if self.flash_time <= 0:
                    self.winner = "red"
                else:
                    self.winner = "blue"
                    self.too_early = True
            elif BUTTON_TYPES["DOWN"] in event.button:
                if self.flash_time <= 0:
                    self.winner = "blue"
                else:
                    self.winner = "red"
                    self.too_early = True
            
            if self.winner:
                self.state = "winner"
                self.win_cooldown = 1000
        elif self.state == "winner":
            if self.win_cooldown <= 0 and (BUTTON_TYPES["UP"] in event.button or BUTTON_TYPES["DOWN"] in event.button):
                self.reset_game()
                self.start_game()
    
    def start_game(self):
        self.state = "ready"
        self.flash_time = random.randint(2000, 5000)

    def handle_buttonup(self, event: ButtonUpEvent):
        pass