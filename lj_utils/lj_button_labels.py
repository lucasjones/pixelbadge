# Lucas Jones 2024
import math
from events.input import ButtonDownEvent, ButtonUpEvent, BUTTON_TYPES
from system.eventbus import eventbus
from app_components.tokens import label_font_size, set_color, clear_background


class ButtonLabels:
    # options:
    # highlight_button_presses=True - will highlight the label when a button is being pressed
    #
    # advanced options:
    # register_button_handlers=True - set to False if you want to pass button events to this class manually
    def __init__(self, app, labels={},
        register_button_handlers=True,
        highlight_button_presses=True,
        text_color=(0, 0, 0),
        text_pressed_color=(1, 1, 1),
        bg_pressed_color=(0, 0, 0),
        fade_out_time=6000,
        hold_time=2000,
    ):
        self.app = app

        self.labels = {}
        self.update_labels(labels)
        
        self.reset()
        self.highlight_button_presses = highlight_button_presses
        self.visible = True

        self.text_color = text_color
        self.text_pressed_color = text_pressed_color
        self.bg_pressed_color = bg_pressed_color

        self.fade_out_time = fade_out_time
        self.time_fading_out = 0
        self.hold_time = hold_time
        # if fade out time set, must be greater than hold time
        if self.fade_out_time > 0 and self.fade_out_time < self.hold_time:
            self.fade_out_time = self.hold_time
            print("WARNING: fade_out_time must be greater than hold_time, setting fade_out_time = hold_time")
    
    def update_labels(self, labels, clear=False):
        if clear:
            self.labels = {}
        for key in list(labels.keys()):
            # if key is a string
            if type(key) == str:
                # if key isn't in BUTTON_TYPES throw an error
                if key not in BUTTON_TYPES:
                    raise ValueError(f"Invalid button type: {key}. Valid types are: {BUTTON_TYPES.keys()}")
                self.labels[BUTTON_TYPES[key]] = labels[key]
            else:
                self.labels[key] = labels[key]

    def reset(self):
        self.show()
    
    def hide(self):
        self.visible = False
    
    def show(self):
        self.visible = True
        self.reset_fade_out()

    def draw_label(self, ctx, button, label, pressed):
        if self.fade_out_time > 0 and self.time_fading_out > self.fade_out_time:
            return
        
        angles = {
            BUTTON_TYPES["LEFT"]: -2 * math.pi / 3,
            BUTTON_TYPES["RIGHT"]: math.pi / 3,
            BUTTON_TYPES["UP"]: 0,
            BUTTON_TYPES["DOWN"]: math.pi,
            BUTTON_TYPES["CANCEL"]: -math.pi / 3,
            BUTTON_TYPES["CONFIRM"]: 2 * math.pi / 3,
        }

        if button in angles:
            angle = angles[button] - math.radians(90)
            ctx.save()
            text_dist = 105
            ctx.translate(math.cos(angle) * text_dist, math.sin(angle) * text_dist)
            ctx.rotate(angle + math.radians(90))

            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            ctx.font_size = label_font_size

            alpha = 1.0
            
            if self.fade_out_time > 0:
                if self.time_fading_out < self.hold_time:
                    alpha = 1.0
                else:
                    alpha = 1.0 - (self.time_fading_out - self.hold_time) / (self.fade_out_time - self.hold_time)
                # print(f"alpha: {alpha}")

            if pressed and self.highlight_button_presses:
                text_width = ctx.text_width(label) + 5
                ctx.rgba(*self.bg_pressed_color, alpha)
                # ctx.rectangle(-text_width/2, -10, text_width, 20).fill()
                ctx.round_rectangle(-text_width/2, -12, text_width, 24, 5).fill()
                ctx.rgba(*self.text_pressed_color, alpha)
            else:
                # ctx.rgb(0, 0, 0).rectangle(-20, -10, 40, 20).fill()
                ctx.rgba(*self.text_color, alpha)
            
            ctx.move_to(0, 0).text(label)
            ctx.restore()
    
    def update(self, dt):
        self.time_fading_out += dt
    
    def reset_fade_out(self):
        self.time_fading_out = 0
    
    def draw(self, ctx):
        if not self.visible:
            return
        for button, label in self.labels.items():
            pressed = self.app.button_held(button)
            self.draw_label(ctx, button, label, pressed)
