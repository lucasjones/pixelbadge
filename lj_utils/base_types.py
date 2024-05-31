# Lucas Jones 2024
from app import App
from events.input import ButtonDownEvent, BUTTON_TYPES, ButtonUpEvent
from system.eventbus import eventbus

class Utility:
    def __init__(self, app):
        self.app = app

    def on_start(self):
        pass
    
    def on_exit(self):
        pass

    def draw(self, ctx):
        pass

    def update(self, delta):
        pass

    def update_leds(self):
        pass

    # returns True if this app handles the CANCEL button press
    def handle_buttondown(self, event: ButtonDownEvent):
        return False
    
    def handle_buttonup(self, event: ButtonUpEvent):
        pass


class ImprovedAppBase(App):
    def __init__(self):
        super().__init__()
        self.__focused = False
        eventbus.on(ButtonDownEvent, self.__handle_buttondown, self)
        eventbus.on(ButtonUpEvent, self.__handle_buttonup, self)
        self.__held_buttons = {}
        self.__held_button_durations = {}
    
    @property
    def _focused(self):
        return self.__focused
    
    @_focused.setter
    def _focused(self, value):
        last_value = self.__focused
        self.__focused = value
        if value and not last_value:
            self.__held_buttons = {}
            self.__held_button_durations = {}
            self.on_app_focused()
        elif not value and last_value:
            self.__held_buttons = {}
            self.__held_button_durations = {}
            self.on_app_unfocused()
    
    def on_app_focused(self):
        print("App focused")
    
    def on_app_unfocused(self):
        print("App unfocused")
    
    def is_focused(self):
        return self._focused
    
    def __handle_buttondown(self, event: ButtonDownEvent):
        if self._focused:
            for button_type in BUTTON_TYPES.values():
                if button_type in event.button:
                    self.__held_buttons[button_type] = True
                    self.__held_button_durations[button_type] = 0
            self.handle_buttondown(event)
    
    def __handle_buttonup(self, event: ButtonUpEvent):
        if self._focused:
            for button_type in BUTTON_TYPES.values():
                if button_type in event.button:
                    self.__held_buttons[button_type] = False
                    self.__held_button_durations[button_type] = 0
            self.handle_buttonup(event)
    
    def button_held(self, button_type):
        return self.__held_buttons.get(button_type, False)
    
    def button_hold_duration(self, button_type):
        return self.__held_button_durations.get(button_type, 0)
    
    def update(self, delta):
        if self._focused:
            for button_type in BUTTON_TYPES.values():
                if self.__held_buttons.get(button_type):
                    self.__held_button_durations[button_type] += delta
    
    def handle_buttondown(self, event: ButtonDownEvent):
        pass
    
    def handle_buttonup(self, event: ButtonUpEvent):
        pass
    
    def exit(self):
        print("Stopping app...")
        self.minimise()
        # eventbus.emit(RequestStopAppEvent(self))
    
    def print_error(self, message):
        print(f"Error: {message}")

# You need to call update(delta) and handle_buttondown(event) yourself
class RepeatingButtonManager:
    def __init__(self, app, button_type, callback, time_before_first_repeat=500, repeat_interval=200):
        self.app = app
        self.button_type = button_type
        self.callback = callback
        self.time_before_first_repeat = time_before_first_repeat
        self.repeat_interval = repeat_interval
        self._start_hold_time = 0
        self._last_trigger_time = 0
        self._button_held = False
    
    def update(self, delta):
        if not self.app.is_focused():
            return
        
        if not self._button_held:
            return
        
        # check that button is still held
        if not self.app.button_held(self.button_type):
            self._button_held = False
            return
        hold_time = self.app.button_hold_duration(self.button_type)
        if self._start_hold_time > hold_time or self._last_trigger_time > hold_time:
            self.app.print_error(f"Button hold time is less than start hold time, or last trigger time. hold_time: {hold_time}, start_hold_time: {self._start_hold_time}, last_trigger_time: {self._last_trigger_time}")
            self.button_held = False
            return
        
        time_since_press = hold_time - self._start_hold_time
        time_since_last_trigger = hold_time - self._last_trigger_time
        if time_since_press >= self.time_before_first_repeat:
            if time_since_last_trigger >= self.repeat_interval:
                self._last_trigger_time = hold_time
                self.callback()
    
    def handle_buttondown(self, event):
        if self.button_type in event.button:
            self.duration = 0
            self.triggered = False
            hold_time = self.app.button_hold_duration(self.button_type)
            self._start_hold_time = hold_time
            self._last_trigger_time = hold_time
            self._button_held = True
            self.callback()