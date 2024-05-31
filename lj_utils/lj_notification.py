# Based on app_components/notifications.py from emf-badge-2024/badge-2024-software
# tweaks and improvements by Lucas Jones

from app_components.tokens import label_font_size, set_color, colors

class Notification:
    _half_hex_rotation = (2 * 3.141593) / 12

    def __init__(self, message, port=0, open=True, font_size=None, animate_duration=500, bg_color=(82, 131, 41), display_time=3000):
        self.message = message
        self._open = open
        self._port = port

        self._animation_state = 0
        self._animation_target = 1 if open else 0
        self._open_time = 0
        self._close_after = display_time
        self.width_limits = [120, 180, 220, 240, 240, 240, 180, 120]
        if font_size:
            self.font_size = font_size
        else:
            self.font_size = label_font_size
        self._animate_duration = animate_duration
        self._max_delta_time = 500
        self.bg_color = bg_color
        # if bg_color is string, use value of color from tokens
        if type(bg_color) == str:
            self.bg_color = colors[bg_color]

    def __repr__(self):
        return f"<Notification '{self.message}' on port {self._port} ({self._open} - {self._open_time})>"

    def _is_closed(self):
        return self._animation_state < 0.01

    def open(self):
        self._animation_target = 1
        self._open = True

    def close(self):
        self._open_time = 0
        self._animation_target = 0
        self._open = False

    def update(self, delta):
        # if delta is too high, i.e. resuming paused app, don't update the animation
        if delta > self._max_delta_time:
            return
        # delta_s = min((delta / 1000) * 5, 1)
        delta_s = min((delta / self._animate_duration), 1)
        animation_delta = self._animation_target - self._animation_state
        animation_step = animation_delta * delta_s
        self._animation_state += animation_step

        if self._open:
            self._open_time += delta

        if self._open and self._open_time > self._close_after:
            self.close()

    def get_text_for_line(self, ctx, text, line):
        width_for_line = 240
        if line < len(self.width_limits):
            width_for_line = self.width_limits[line]

        words = text.split()
        line_text = ""
        extra_text = ""

        for word in words:
            if ctx.text_width(line_text + word) <= width_for_line:
                line_text += word + " "
            else:
                extra_text = ' '.join(words[words.index(word):])
                line_text = line_text.strip()
                break

        if not extra_text:
            line_text = line_text.strip()

        return line_text, extra_text

    def draw(self, ctx):
        if not self._is_closed():
            ctx.save()

            ctx.font_size = self.font_size
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE

            if self._port != 0:
                ctx.rotate(self._half_hex_rotation * (self._port * 2 - 1))

            lines = self.message.split('\n')
            final_lines = []
            extra_text = ""
            line = 0
            for line_text in lines:
                while line_text:
                    text_that_fits, line_text = self.get_text_for_line(ctx, line_text, line)
                    final_lines.append(text_that_fits)
                    line += 1

            if len(self.bg_color) == 3:
                ctx.rgb(*self.bg_color)
            elif len(self.bg_color) == 4:
                ctx.rgba(*self.bg_color)
            ctx.rectangle(-120, -150 - 30 * (len(final_lines) - 1) - (self._animation_state * -30 * len(final_lines)), 240, 30 * len(final_lines)).fill()

            if self._port != 0:
                ctx.rotate(3.14)
                set_color(ctx, "label")
                for i in range(len(final_lines)):
                    ctx.move_to(0, 135 - 30 * (len(final_lines) - 1) - (self._animation_state * -30 * len(final_lines)) + 30 * i).text(final_lines[i])
            else:
                set_color(ctx, "label")
                for i in range(len(final_lines)):
                    ctx.move_to(0, -130 - 30 * (len(final_lines) - 1) - (self._animation_state * -30 * len(final_lines)) + 30 * i).text(final_lines[i])

            ctx.restore()
