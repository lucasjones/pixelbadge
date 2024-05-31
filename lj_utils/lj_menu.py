# based on app_components.Menu, improvements by Lucas Jones

from typing import Any, Callable, Literal, Union

from app import App
from events.input import BUTTON_TYPES, ButtonDownEvent
from system.eventbus import eventbus

from app_components.tokens import heading_font_size, label_font_size, line_height, set_color


def ease_out_quart(x):
    return 1 - pow(1 - x, 4)


class Menu:
    def __init__(
        self,
        app: App,
        menu_items: list[str] = [],
        position=0,
        select_handler: Union[Callable[[str], Any], None] = None,
        back_handler: Union[Callable, None] = None,
        speed_ms=300,
        item_font_size=label_font_size,
        item_line_height=label_font_size * line_height,
        focused_item_font_size=heading_font_size,
        focused_item_margin=20,
        animate_movement=False,
        text_color = (1, 1, 1),
        # outline_text_color = (1, 1, 1),
        # outline_text_thickness = 2,
    ):
        self.app = app
        self.menu_items = menu_items
        self.position = position
        self.select_handler = select_handler
        self.back_handler = back_handler
        self.speed_ms = speed_ms
        self.item_font_size = item_font_size
        self.item_line_height = item_line_height
        self.focused_item_font_size = focused_item_font_size
        self.focused_item_margin = focused_item_margin
        self.animate_movement = animate_movement
        self.text_color = text_color
        # self.outline_text_color = outline_text_color
        # self.outline_text_thickness = outline_text_thickness

        self.unfocused_text_scale = 0.8

        self.animation_time_ms = 0
        # self.is_animating: Literal["up", "down", "none"] = "none"
        self.is_animating: Literal["up", "down", "none"] = "up"

        self.text_fit_sizes = {}

        # eventbus.on(ButtonDownEvent, self._handle_buttondown, app)

    def _cleanup(self):
        eventbus.remove(ButtonDownEvent, self._handle_buttondown, self.app)

    def _handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES["UP"] in event.button:
            self.up_handler()
        if BUTTON_TYPES["DOWN"] in event.button:
            self.down_handler()
        if BUTTON_TYPES["CANCEL"] in event.button:
            if self.back_handler is not None:
                self.back_handler()
        if BUTTON_TYPES["CONFIRM"] in event.button:
            if self.select_handler is not None:
                self.select_handler(
                    self.menu_items[self.position % len(self.menu_items)]
                )

    def up_handler(self):
        self.is_animating = "up"
        self.animation_time_ms = 0
        self.position = (self.position - 1) % len(self.menu_items)
        # if wrapped around, reverse the animation direction
        if self.position == len(self.menu_items) - 1:
            self.is_animating = "down"

    def down_handler(self):
        self.is_animating = "down"
        self.animation_time_ms = 0
        self.position = (self.position + 1) % len(self.menu_items)
        # if wrapped around, reverse the animation direction
        if self.position == 0:
            self.is_animating = "up"
    
    def get_target_font_size(self, ctx, text):
        target_font_size = self.focused_item_font_size
        if text in self.text_fit_sizes:
            return self.text_fit_sizes[text]
        else:
            ctx.font_size = target_font_size
            while ctx.text_width(text) > 200:
                target_font_size -= 1
                ctx.font_size = target_font_size
                self.text_fit_sizes[text] = target_font_size
        return target_font_size
    
    def get_base_font_size(self, target_font_size):
        # if the default base size is within 10% of the target font size, or it's bigger than target, return the target font size scaled down
        # otherwise return the default font size
        if self.item_font_size >= target_font_size or self.item_font_size >= target_font_size * 1.1:
            return target_font_size * self.unfocused_text_scale
        return self.item_font_size

    def draw(self, ctx):
        animation_progress = ease_out_quart(self.animation_time_ms / self.speed_ms)
        animation_direction = 1 if self.is_animating == "up" else -1

        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE

        current_item_text = self.menu_items[self.position % len(self.menu_items)]
        target_font_size = self.get_target_font_size(ctx, current_item_text)

        # Current menu item
        ctx.font_size = self.get_base_font_size(target_font_size) + animation_progress * (
            target_font_size - self.get_base_font_size(target_font_size)
        )

        ctx.rgb(*self.text_color)
        animation_movement = self.item_line_height
        if not self.animate_movement:
            animation_movement = 0
        animation_offset_y = animation_direction * -animation_movement + animation_progress * animation_direction * animation_movement
        ctx.move_to(
            0, animation_offset_y
        ).text(current_item_text)
        # if self.outline_text_color is not None:
        #     ctx.rgb(*self.outline_text_color)
        #     ctx.font_size = ctx.font_size + 2
        #     ctx.move_to(
        #         0, animation_offset_y
        #     ).text(current_item_text)

        # Previous menu items
        ctx.font_size = self.item_font_size
        for i in range(1, 4):
            if (self.position - i) >= 0:
                target_font_size = self.get_target_font_size(ctx, self.menu_items[self.position - i])
                # if self.outline_text_color is not None:
                #     ctx.rgb(*self.outline_text_color)
                #     ctx.font_size = self.get_base_font_size(target_font_size) + 2
                #     ctx.move_to(
                #         0,
                #         -self.focused_item_margin
                #         + -i * self.item_line_height
                #         + animation_offset_y,
                #     ).text(self.menu_items[self.position - i])
                ctx.font_size = self.get_base_font_size(target_font_size)
                ctx.rgb(*self.text_color)
                ctx.move_to(
                    0,
                    -self.focused_item_margin
                    + -i * self.item_line_height
                    + animation_offset_y,
                ).text(self.menu_items[self.position - i])

        # Next menu items
        for i in range(1, 4):
            if (self.position + i) < len(self.menu_items):
                target_font_size = self.get_target_font_size(ctx, self.menu_items[self.position + i])
                # if self.outline_text_color is not None:
                #     ctx.rgb(*self.outline_text_color)
                #     ctx.font_size = self.get_base_font_size(target_font_size) + 2
                #     ctx.move_to(
                #         0,
                #         self.focused_item_margin
                #         + i * self.item_line_height
                #         + animation_offset_y,
                #     ).text(self.menu_items[self.position + i])
                ctx.font_size = self.get_base_font_size(target_font_size)
                ctx.rgb(*self.text_color)
                ctx.move_to(
                    0,
                    self.focused_item_margin
                    + i * self.item_line_height
                    + animation_offset_y,
                ).text(self.menu_items[self.position + i])

    def update(self, delta):
        if self.is_animating != "none":
            self.animation_time_ms += delta
            if self.animation_time_ms > self.speed_ms:
                self.is_animating = "none"
                self.animation_time_ms = self.speed_ms