# Lucas Jones 2024
import asyncio
import math
import random
import machine
import urequests
import _thread
import uos
import json
import wifi

BLUETOOTH_ENABLED = False

APP_VERSION = "1.0.1"
APP_VERSION_IOTA = 2

if BLUETOOTH_ENABLED:
    import aioble
from app import App
# from app_components import clear_background
from app_components import display_x, display_y
from app_components.tokens import one_pt
from tildagonos import tildagonos
import display
from events.input import ButtonDownEvent, BUTTON_TYPES, ButtonUpEvent
from system.scheduler.events import RequestStopAppEvent
from system.eventbus import eventbus

from .lj_utils.lj_menu import Menu
from .lj_utils.lj_button_labels import ButtonLabels
from .lj_utils.lj_display_utils import colors, clear_background
from .lj_utils.base_types import Utility, ImprovedAppBase
from .lj_utils.lj_notification import Notification
from .lj_utils.wifi_utils import check_wifi, WiFiManager

from .animation_viewer import AnimationApp, api_base_url
from .basic_utils import Torch, Rainbow, Strobe, Spiral, CreditsScreen
from .game_of_life import ConwaysGameOfLife
from .visual_effects import RandomGrid
from .snap_game import SnapGame

class MainMenu(Utility):
    def __init__(self, app, items=None):
        super().__init__(app)
        self.menu = Menu(
            app,
            items,
            select_handler=app.select_handler,
            # back_handler=app.back_handler,
            text_color=(1, 1, 1)
        )
        self.bg = RandomGrid(app)
    
    def on_start(self):
        self.bg.grid = self.bg.generate_grid()
        # if not check_wifi(on_need_to_connect=self.on_wifi_connecting):
        #     print("Wi-Fi connection failed")
        #     # Handle Wi-Fi connection failure (e.g., show an error message)
        #     notification = Notification("Wi-Fi connection failed")
        #     self.app.notifications.append(notification)
        # else:
        #     print("Wi-Fi connected")
        _thread.start_new_thread(self.check_for_update, ())
    
    # def on_wifi_connecting(self):
    #     print("Connecting to Wi-Fi...")
    #     notification = Notification("Connecting to Wi-Fi...", open=True, animate_duration=200, display_time=1000)
    #     self.app.notifications.append(notification)

    def draw(self, ctx):
        self.bg.draw(ctx)
        self.menu.draw(ctx)

    def update(self, delta):
        self.menu.update(delta)

    def update_leds(self):
        # Turn off all LEDs
        for i in range(12):
            tildagonos.leds[i+1] = (0, 0, 0)
        tildagonos.leds.write()
    
    def handle_buttondown(self, event: ButtonDownEvent):
        self.menu._handle_buttondown(event)
        return False
    
    def check_for_update(self):
        print("Checking for updates...")
        while not wifi.status():
            print("[check_for_update] Waiting for Wi-Fi connection...")
            time.sleep(1)
        try:
            response = urequests.get(api_base_url + "/api/latest_app_version")
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("iota")
                print("Update check result:", data.get("version"), "iota:", latest_version, "local version:", APP_VERSION, "iota:", APP_VERSION_IOTA)
                if latest_version > APP_VERSION_IOTA:
                    notification = Notification(f"New update available!\nYou are on {APP_VERSION},\nlatest is {data.get('version')}", font_size=one_pt * 9, open=True)
                    self.app.notifications.append(notification)
        except Exception as e:
            print(f"Failed to check for updates: {e}")

class UtilityMenuApp(ImprovedAppBase):
    def __init__(self):
        super().__init__()
        self.current_menu = "main"
        self.utilities = {
            "Pixel Badge": AnimationApp(self),
            "torch": Torch(self),
            "rainbow": Rainbow(self),
            "strobe": Strobe(self),
            "spiral": Spiral(self),
            "Game of Life": ConwaysGameOfLife(self),
            "Snap Game": SnapGame(self),
        }
        self.utilities["main"] = MainMenu(self, items=list(self.utilities.keys()))
        self.utilities["credits"] = CreditsScreen(self)
        self.button_labels = ButtonLabels(
            self, labels={
                "LEFT": "Left",
                "RIGHT": "Right",
                "UP": "Up",
                "DOWN": "Down",
                "CANCEL": "Cancel",
                "CONFIRM": "Confirm"
            },
            bg_pressed_color=(1, 0, 0)
        )
        self.notifications = []

        # Initialize the WiFiManager
        self.wifi_manager = WiFiManager(
            on_connected=self.on_wifi_connected,
            on_fail=self.on_wifi_fail,
            on_disconnect=self.on_wifi_disconnect,
            on_wifi_connecting=self.on_first_wifi_connect
        )

    def select_handler(self, item):
        print(f"Selected item: {item}")
        self.set_screen(item)
    
    def set_screen(self, screen):
        self.utilities[self.current_menu].on_exit()
        self.current_menu = screen
        if screen != "main":
            self.button_labels.hide()
        self.utilities[screen].on_start()

    def back_handler(self):
        if self.current_menu == "main":
            self.exit()
        else:
            self.set_screen("main")

    def draw(self, ctx):
        clear_background(ctx)
        self.utilities[self.current_menu].draw(ctx)
        self.button_labels.draw(ctx)
        for notification in self.notifications:
            notification.draw(ctx)

    def update(self, delta):
        super().update(delta)
        if delta > 5000:
            print("Delta too high, skipping update. Delta:", delta)
            return
        self.utilities[self.current_menu].update(delta)
        self.update_leds()
        self.button_labels.update(delta)
        # don't update notifications for very high delta as they won't animate properly
        if delta < 500:
            for notification in self.notifications:
                notification.update(delta)
        
        # Update the WiFiManager
        self.wifi_manager.update(delta)

        if self.button_hold_duration(BUTTON_TYPES["UP"]) > 2000 and self.button_hold_duration(BUTTON_TYPES["DOWN"]) > 2000:
            self.set_screen("credits")

    def update_leds(self):
        self.utilities[self.current_menu].update_leds()
    
    def handle_buttondown(self, event: ButtonDownEvent):
        handled_cancel_button = self.utilities[self.current_menu].handle_buttondown(event)
        if not handled_cancel_button and BUTTON_TYPES["CANCEL"] in event.button:
            self.back_handler()
    
    def handle_buttonup(self, event: ButtonUpEvent):
        self.utilities[self.current_menu].handle_buttonup(event)
    
    def on_app_focused(self):
        super().on_app_focused()
        self.button_labels.reset()
        self.utilities[self.current_menu].on_start()
    
    def on_app_unfocused(self):
        super().on_app_unfocused()
        self.utilities[self.current_menu].on_exit()

    def on_first_wifi_connect(self, is_first_connection):
        if is_first_connection:
            print("First WiFi Connect Attempt")
            notification = Notification("Connecting to Wi-Fi...", open=True, animate_duration=200, display_time=1000)
            self.notifications.append(notification)
    
    # WiFiManager event handlers
    def on_wifi_connected(self):
        print("WiFi Connected")
        notification = Notification("Wi-Fi Connected", open=True, animate_duration=200, display_time=1000)
        self.notifications.append(notification)
        

    def on_wifi_fail(self):
        print("WiFi Connection Failed")
        notification = Notification("Wi-Fi Connection Failed", open=True, animate_duration=200, display_time=1000)
        self.notifications.append(notification)

    def on_wifi_disconnect(self):
        print("WiFi Disconnected")
        notification = Notification("Wi-Fi Disconnected", open=True, animate_duration=200, display_time=1000)
        self.notifications.append(notification)

