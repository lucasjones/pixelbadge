# Lucas Jones 2024
import math

from events.input import ButtonDownEvent, BUTTON_TYPES, ButtonUpEvent
# from sys_colors import hsv_to_rgb, rgb_to_hsv
from tildagonos import tildagonos

from .lj_utils.lj_display_utils import colors, clear_background
from .lj_utils.base_types import Utility
from .lj_utils.lj_button_labels import ButtonLabels
from .lj_utils.color import hsv_to_rgb

# increase speed button
INCREASE_SPEED_BUTTON = BUTTON_TYPES["UP"]
DECREASE_SPEED_BUTTON = BUTTON_TYPES["DOWN"]

class Torch(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.brightness = 255

    def draw(self, ctx):
        ctx.rgb(self.brightness / 255.0, self.brightness / 255.0, self.brightness / 255.0)
        ctx.rectangle(-120, -120, 240, 240).fill()

    def update(self, delta):
        pass

    def update_leds(self):
        for i in range(12):
            tildagonos.leds[i + 1] = (self.brightness, self.brightness, self.brightness)
        tildagonos.leds.write()

    def handle_buttondown(self, event: ButtonDownEvent):
        if INCREASE_SPEED_BUTTON in event.button:
            self.brightness = min(255, self.brightness + 25)
            print(f"Increased brightness to: {self.brightness}")
        if DECREASE_SPEED_BUTTON in event.button:
            self.brightness = max(0, self.brightness - 25)
            print(f"Decreased brightness to: {self.brightness}")
        self.update_leds()
        return False

class Rainbow(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.screen_hue = 0
        self.intervals = [100, 200, 300, 400, 500, 1000, 2000, 3000, 4000, 5000, 10000, 20000, 30000]
        self.interval_index = 10

    def draw(self, ctx):
        r, g, b = hsv_to_rgb((self.screen_hue / 360) * math.tau, 1, 1)
        ctx.rgb(r, g, b).rectangle(-120, -120, 240, 240).fill()

    def update(self, delta):
        # self.screen_hue = (self.screen_hue + 1) % 360
        self.screen_hue = (self.screen_hue + delta * 360 / self.intervals[self.interval_index]) % 360

    def update_leds(self):
        for i in range(12):
            color = hsv_to_rgb(((self.screen_hue + i * 30) % 360 / 360) * math.tau, 1, 1)
            tildagonos.leds[i+1] = color
        tildagonos.leds.write()

    def handle_buttondown(self, event: ButtonDownEvent):
        # if INCREASE_SPEED_BUTTON in event.button:
        #     self.rainbow_interval = max(100, self.rainbow_interval - 500)
        #     print(f"Decreased rainbow interval to: {self.rainbow_interval}")
        # if DECREASE_SPEED_BUTTON in event.button:
        #     self.rainbow_interval = min(30000, self.rainbow_interval + 500)
        #     print(f"Increased rainbow interval to: {self.rainbow_interval}")
        if INCREASE_SPEED_BUTTON in event.button:
            self.interval_index = max(0, self.interval_index - 1)
            print(f"Decreased interval to: {self.intervals[self.interval_index]}")
        elif DECREASE_SPEED_BUTTON in event.button:
            self.interval_index = min(len(self.intervals) - 1, self.interval_index + 1)
            print(f"Increased interval to: {self.intervals[self.interval_index]}")
        return False

class Strobe(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.strobe_state = False
        self.strobe_interval = 500
        self.strobe_timer = 0

    def draw(self, ctx):
        if self.strobe_state:
            ctx.rgb(1, 1, 1).rectangle(-120, -120, 240, 240).fill()
        else:
            ctx.rgb(0, 0, 0).rectangle(-120, -120, 240, 240).fill()

    def update(self, delta):
        self.strobe_timer += delta
        if self.strobe_timer >= self.strobe_interval:
            self.strobe_state = not self.strobe_state
            self.strobe_timer = 0

    def update_leds(self):
        color = (255, 255, 255) if self.strobe_state else (0, 0, 0)
        for i in range(12):
            tildagonos.leds[i+1] = color
        tildagonos.leds.write()

    def handle_buttondown(self, event: ButtonDownEvent):
        if INCREASE_SPEED_BUTTON in event.button:
            self.strobe_interval = max(10, self.strobe_interval - 10)
            print(f"Decreased strobe interval to: {self.strobe_interval}")
        if DECREASE_SPEED_BUTTON in event.button:
            self.strobe_interval = min(10000, self.strobe_interval + 10)
            print(f"Increased strobe interval to: {self.strobe_interval}")
        return False


class Spiral(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.led_index = 0
        self.spiral_interval = 100
        self.spiral_timer = 0

    def draw(self, ctx):
        # Calculate the start and end angles for the arc in radians
        # 0 degrees is at the right side of the screen (going clockwise), and is next to LED 4
        angle_start = math.radians(self.led_index * 30 - 30 * 3)
        angle_end = angle_start + math.radians(30)

        # print(f"Drawing arc from {math.degrees(angle_start)} to {math.degrees(angle_end)} degrees")

        ctx.save()
        ctx.rgb(1, 1, 1)

        # Draw the slice
        ctx.begin_path()
        ctx.move_to(0, 0)
        ctx.arc(0, 0, 120, angle_start, angle_end, False)
        ctx.close_path()
        ctx.fill()

        # Restore the previous drawing context
        ctx.restore()
    
    def update(self, delta):
        self.spiral_timer += delta
        if self.spiral_timer >= self.spiral_interval:
            self.led_index = (self.led_index + 1) % 12
            self.spiral_timer = 0

    def update_leds(self):
        for i in range(12):
            if i == self.led_index:
                tildagonos.leds[i+1] = (255, 255, 255)
            else:
                tildagonos.leds[i+1] = (0, 0, 0)
        tildagonos.leds.write()

    def handle_buttondown(self, event: ButtonDownEvent):
        if INCREASE_SPEED_BUTTON in event.button:
            self.spiral_interval = max(10, self.spiral_interval - 10)
            print(f"Decreased spiral interval to: {self.spiral_interval}")
        if DECREASE_SPEED_BUTTON in event.button:
            self.spiral_interval = min(10000, self.spiral_interval + 10)
            print(f"Increased spiral interval to: {self.spiral_interval}")
        return False

class CreditsScreen(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.credits = [
            "Created by Lucas Jones",
            "for EMF Camp 2024",
        ]
        self.screen_hue = 0
        self.button_labels = ButtonLabels(self.app,
            labels={
                "CANCEL": "Back",
            },
            text_color=(1,1,1),
            bg_pressed_color=(1,1,1),
            text_pressed_color=(0,0,0),
            fade_out_time=0,
        )
        
    def draw(self, ctx):
        clear_background(ctx, (0, 0, 0))
        self.button_labels.draw(ctx)
        ctx.rgb(1, 1, 1)
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        for i, credit in enumerate(self.credits):
            ctx.move_to(0, -15 + i * 30).text(credit)
    
    def update(self, delta):
        # self.screen_hue = (self.screen_hue + 1) % 360
        self.screen_hue = (self.screen_hue + delta * 360 / 4000) % 360
        self.button_labels.update(delta)

    def update_leds(self):
        for i in range(12):
            color = hsv_to_rgb(((self.screen_hue + i * 30) % 360 / 360) * math.tau, 1, 1)
            tildagonos.leds[i+1] = color
        tildagonos.leds.write()

class UserUploadedDisclaimerScreen(Utility):
    # Shows a disclaimer that pixel art content is user uploaded
    def __init__(self, app, APP_BASE_PATH):
        super().__init__(app)
        self.screen_hue = 0
        self.button_labels = ButtonLabels(self.app,
            labels={
                "CANCEL": "Back",
                "CONFIRM": "Continue",
            },
            text_color=(1,1,1),
            bg_pressed_color=(1,1,1),
            text_pressed_color=(0,0,0),
            fade_out_time=0,
        )
        self.app_base_path = APP_BASE_PATH

    def draw(self, ctx):
        clear_background(ctx, (0, 0, 0))
        self.button_labels.draw(ctx)
        ctx.rgb(1, 1, 1)
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.move_to(0, -15).text("Please be aware that")
        ctx.move_to(0, 10).text("pixel art is user uploaded")
    
    def update(self, delta):
        # self.screen_hue = (self.screen_hue + 1) % 360
        self.button_labels.update(delta)
    
    def update_leds(self):
        for i in range(12):
            tildagonos.leds[i+1] = (0, 0, 0)
        tildagonos.leds.write()
    
    def handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["CONFIRM"] in event.button:
            # write _seen_disclaimer.txt in current folder
            print("User accepted content disclaimer")
            with open(self.app_base_path + "_seen_disclaimer.txt", "w") as f:
                f.write("y")
            self.app.set_screen("Pixel Art")
            return True
        return False

class WaitingForWifiScreen(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.screen_hue = 0
        self.button_labels = ButtonLabels(self.app,
            labels={
                "CANCEL": "Back",
            },
            text_color=(1,1,1),
            bg_pressed_color=(1,1,1),
            text_pressed_color=(0,0,0),
            fade_out_time=0,
        )
        self.next_screen = self.app.animation_app_state

    def draw(self, ctx):
        clear_background(ctx, (0, 0, 0))
        self.button_labels.draw(ctx)
        ctx.rgb(0.6, 0.6, 0.6)
        ctx.font_size = 30
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.move_to(0, 0).text("Waiting for WiFi...")
    
    def update(self, delta):
        # self.screen_hue = (self.screen_hue + 1) % 360
        self.button_labels.update(delta)
        if self.app.wifi_manager.is_connected():
            self.app.set_screen(self.next_screen)
    
    def handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["CANCEL"] in event.button:
            self.app.set_screen("main")
            return True
        return False