# Lucas Jones 2024
import json
import os
import math
import requests
import _thread
import gc
import time
import wifi
import asyncio
from tildagonos import tildagonos

from events.input import ButtonDownEvent, BUTTON_TYPES, ButtonUpEvent
from app_components import display_x, display_y

from .lj_utils.lj_display_utils import colors, clear_background
from .lj_utils.base_types import Utility, RepeatingButtonManager
from .lj_utils.lj_button_labels import ButtonLabels
from .lj_utils.lj_notification import Notification
from .lj_utils.wifi_utils import check_wifi, wifi_is_connecting
from .lj_utils.file_utils import file_exists, folder_exists

APP_BASE_PATH = "./apps/pixelbadge/"

def get_image_path(filename):
    return APP_BASE_PATH + filename


DISPLAY_THUMBNAILS_STATE = 1
PLAYING_ANIMATION_STATE = 2
VIEW_METADATA_STATE = 3
LOGIN_STATE = 4
DISPLAY_WEBSITE_STATE = 5

# api_base_url = "http://localhost:8080"
api_base_url = "https://pixelbadge.xyz"
favorites_file = get_image_path("favorite_animations.json")
auth_file = get_image_path("auth_token.json")


class ThumbnailBrowser(Utility):
    def __init__(self, app, parent):
        super().__init__(app)
        self.parent = parent
        self.sequences = []
        self.selected_thumbnail = 0
        self.render_start_index = 0
        self.visible_thumbnails = 9  # 3x3 grid
        self.scroll_target_y = 0
        self.scroll_current_y = 0
        self.icon_size = 60
        self.current_page_index = 1
        self.max_page_index = 1
        self.sort_mode_index = 1
        self.is_loading_sequences_list = False
        self.spinner_time = 0

        self.button_managers = [
            RepeatingButtonManager(self.app, BUTTON_TYPES['DOWN'], self.navigate_down),
            RepeatingButtonManager(self.app, BUTTON_TYPES['LEFT'], self.navigate_left),
            RepeatingButtonManager(self.app, BUTTON_TYPES['RIGHT'], self.navigate_right),
        ]
        self.page_identifier = ""

    def on_start(self):
        tmp_dir = get_image_path("thumbs")
        try:
            os.mkdir(tmp_dir)
        except Exception as e:
            print(f"Error creating tmp directory: {e}")
        if len(self.sequences) == 0:
            _thread.start_new_thread(self.fetch_sequences, ())

    def get_all_sort_modes(self):
        if self.parent.logged_in():
            return ["recent", "popular", "recently_liked", "random", "favorites"]
        else:
            return ["recent", "popular", "recently_liked", "random"]

    def sort_mode(self):
        all_sort_modes = self.get_all_sort_modes()
        return all_sort_modes[self.sort_mode_index % len(all_sort_modes)]

    def fetch_sequences(self):
        print("Fetching sequences... sort mode:", self.sort_mode())

        while not self.app.wifi_manager.is_connected():
            print("[fetch_sequences] Waiting for Wi-Fi connection...")
            time.sleep(1)
        
        self.sequences = []
        try:
            self.is_loading_sequences_list = True
            if self.sort_mode() == "favorites":
                favorites = self.parent.load_favorites_file()
                response = requests.get(api_base_url + '/api/sequences?page=' + str(self.current_page_index), json=favorites, headers=self.parent.get_auth_headers())
            else:
                response = requests.get(api_base_url + '/api/sequences?page=' + str(self.current_page_index) + "&sort=" + self.sort_mode(), headers=self.parent.get_auth_headers())
            if response.status_code == 200:
                result = response.json()
                if result.get('sequences') is not None:
                    self.sequences = result['sequences']
                else:
                    self.sequences = []
                if result.get('total_page_count', 0) > 0:
                    self.max_page_index = result['total_page_count']
                if result.get('next_page_exists', False):
                    if self.current_page_index + 1 > self.max_page_index:
                        self.max_page_index = self.current_page_index + 1
                else:
                    self.max_page_index = self.current_page_index
                print(f"Fetched {len(self.sequences)} sequences. Next page exists: {result['next_page_exists']}")
                self.is_loading_sequences_list = False
                self.parent.delete_all_files(get_image_path("thumbs"))
                self.page_identifier = f"{self.sort_mode()}_{self.current_page_index}"
                if len(self.sequences) > 0:
                    _thread.start_new_thread(self.download_thumbnails, (0, self.page_identifier))
            else:
                self.is_loading_sequences_list = False
                print("Failed to fetch sequences, status code:", response.status_code)
        except Exception as e:
            self.is_loading_sequences_list = False
            print(f"Error fetching sequences: {e}")

    def download_thumbnails(self, i, page_identifier):
        if self.page_identifier != page_identifier:
            # stop downloading if the page has changed
            return
        print("Downloading thumbnails...")
        while not self.app.wifi_manager.is_connected():
            print("[download_thumbnails] Waiting for Wi-Fi connection...")
            time.sleep(1)
        erased_thumbnails = False
        if i >= len(self.sequences):
            self.parent.app.print_error(f"WARNING: download_thumbnails called with invalid index: {i} (sequences len: {len(self.sequences)})")
            return
        sequence = self.sequences[i]
        try:
            thumb_url = f"{api_base_url}/api/sequence/{sequence['id']}/thumbnail"
            thumb_response = requests.get(thumb_url)
            if self.page_identifier != page_identifier:
                return
            if thumb_response.status_code == 200:
                print(f"Downloaded thumbnail for {sequence['id']}")
                thumb_path = get_image_path(f"thumbs/{sequence['id']}.png")
                if not erased_thumbnails:
                    erased_thumbnails = True
                with open(thumb_path, "wb") as f:
                    f.write(thumb_response.content)
                sequence['thumbnail_path'] = thumb_path
            else:
                print(f"Failed to download thumbnail for {sequence['id']}")
        except Exception as e:
            self.parent.app.print_error(f"Error downloading thumbnail for {sequence['id']}: {e}")
        if i < len(self.sequences) - 1:
            _thread.start_new_thread(self.download_thumbnails, (i + 1, page_identifier))
        elif i == len(self.sequences) - 1:
            print("[download_thumbnails] running gc.collect()")
            gc.collect()

    def get_thumbnail_screen_coords(self, i):
        x = (i % 3) * self.icon_size - 90
        y = (i // 3) * self.icon_size - 90 + self.scroll_current_y
        return x, y

    def draw(self, ctx):
        ctx.save()

        # sort mode will be obscured by thumbnails so don't draw it if a thumbnail is selected
        if self.selected_thumbnail <= self.visible_thumbnails:
            # draw sort mode text at top middle of screen
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            ctx.font_size = 20
            ctx.rgba(0, 0, 0, 1)
            ctx.move_to(0, -display_y * 0.5 + 15).text(self.sort_mode() + "(" + str(self.current_page_index) + "/" + str(self.max_page_index) + ")")

        ctx.image_smoothing = 0
        ctx.rgba(1, 1, 1, 1)

        start_index = max(0, self.render_start_index - 6)
        end_index = min(self.render_start_index + self.visible_thumbnails + 6, len(self.sequences))

        # draw visible thumbnails
        for i in range(start_index, end_index):
            seq = self.sequences[i]
            x, y = self.get_thumbnail_screen_coords(i)
            if 'thumbnail_path' in seq:
                ctx.image(seq['thumbnail_path'], x, y, self.icon_size - 5, self.icon_size - 5)
            else:
                # draw a small grey square if thumbnail is not loaded
                ctx.rgb(0.5, 0.5, 0.5)
                ctx.rectangle(x + self.icon_size * 0.3, y + self.icon_size * 0.3, self.icon_size * 0.4, self.icon_size * 0.4).fill()
        
        # draw outline
        outline_x, outline_y = self.get_thumbnail_screen_coords(self.selected_thumbnail)
        ctx.rgb(0, 0, 1)
        ctx.rectangle(outline_x - 2.5, outline_y - 2.5, self.icon_size, self.icon_size).stroke()

        # draw prev/next buttons
        next_button_x, next_button_y = self.get_thumbnail_screen_coords(self.next_button_index())
        ctx.rgb(0, 0, 0)
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        # ctx.font_size = 13
        # ctx.move_to(next_button_x + self.icon_size * 0.5, next_button_y + self.icon_size * 0.5).text("REFRESH")
        ctx.font_size = 20
        if self.is_loading_sequences_list:
            if self.next_button_index() < 0:
                next_button_x, next_button_y = self.get_thumbnail_screen_coords(self.login_button_index())
        #     ctx.text("...")
            self.draw_spinning_wheel(ctx, next_button_x + self.icon_size * 0.5, next_button_y + self.icon_size * 0.5, 16, self.spinner_time)
        else:
            ctx.move_to(next_button_x + self.icon_size * 0.5, next_button_y + self.icon_size * (0.5))
            ctx.text("NEXT")
        # ctx.move_to(next_button_x + self.icon_size * 0.5, next_button_y + self.icon_size * (0.5 + 0.15)).text("PAGE")

        if self.current_page_index > 1:
            prev_button_x, prev_button_y = self.get_thumbnail_screen_coords(self.prev_button_index())
            if self.is_loading_sequences_list:
                # ctx.text("...")
                pass
            else:
                ctx.move_to(prev_button_x + self.icon_size * 0.5, prev_button_y + self.icon_size * (0.5))
                ctx.text("PREV")

        # draw login button
        login_button_x, login_button_y = self.get_thumbnail_screen_coords(self.login_button_index())
        ctx.rgb(0, 0, 0)
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.font_size = 20
        if not (self.is_loading_sequences_list and self.next_button_index() < 0):
            if self.parent.logged_in():
                ctx.move_to(login_button_x + self.icon_size * 0.5, login_button_y + self.icon_size * 0.3)
                ctx.text("LOG")
                ctx.move_to(login_button_x + self.icon_size * 0.5, login_button_y + self.icon_size * 0.65)
                ctx.text("OUT")
            else:
                ctx.move_to(login_button_x + self.icon_size * 0.5, login_button_y + self.icon_size * 0.5)
                ctx.text("LOGIN")

        ctx.restore()

    def draw_spinning_wheel(self, ctx, x, y, size, time):
        ctx.save()
        ctx.translate(x, y)
        ctx.rotate(time * 0.002 % math.tau)
        ctx.rgb(0, 0, 0)
        ctx.line_width = 5
        ctx.arc(0, 0, size, 0, math.tau * 0.8, False)
        ctx.stroke()
        ctx.restore()

    def prev_button_index(self):
        if self.current_page_index > 1:
            return len(self.sequences)
        return -1

    def next_button_index(self):
        if self.current_page_index < self.max_page_index:
            index = len(self.sequences)
            if self.prev_button_index() != -1:
                index += 1
            return index
        return -1

    def login_button_index(self):
        index = len(self.sequences)
        if self.prev_button_index() != -1:
            index += 1
        if self.next_button_index() != -1:
            index += 1
        return index

    def handle_buttondown(self, event: ButtonDownEvent):
        for btn_manager in self.button_managers:
            btn_manager.handle_buttondown(event)

        if BUTTON_TYPES['CONFIRM'] in event.button:
            if self.selected_thumbnail == self.next_button_index():
                if self.current_page_index < self.max_page_index:
                    self.current_page_index += 1
                else:
                    self.current_page_index = 1
                _thread.start_new_thread(self.fetch_sequences, ())
                self.selected_thumbnail = 0
                self.scroll_target_y = 0
                self.render_start_index = 0
            elif self.selected_thumbnail == self.prev_button_index():
                if self.current_page_index > 1:
                    self.current_page_index -= 1
                _thread.start_new_thread(self.fetch_sequences, ())
                self.selected_thumbnail = 0
                self.scroll_target_y = 0
                self.render_start_index = 0
            elif self.selected_thumbnail == self.login_button_index():
                self.parent.set_state(LOGIN_STATE)
            elif self.selected_thumbnail < len(self.sequences):
                _thread.start_new_thread(self.handle_thumbnail_select, ())
        elif BUTTON_TYPES['UP'] in event.button:
            self.change_sort_mode_index((self.sort_mode_index + 1) % len(self.get_all_sort_modes()))
        return True

    def change_sort_mode_index(self, new_val):
        if self.sort_mode_index == new_val:
            return
        self.sort_mode_index = new_val
        self.current_page_index = 1
        self.max_page_index = 1
        self.selected_thumbnail = 0
        self.scroll_target_y = 0
        self.render_start_index = 0
        _thread.start_new_thread(self.fetch_sequences, ())

    def get_max_index(self):
        max_index = len(self.sequences)
        if self.prev_button_index() != -1:
            max_index += 1
        if self.next_button_index() != -1:
            max_index += 1
        if self.login_button_index() != -1:
            max_index += 1
        return max_index

    def navigate_left(self):
        self.selected_thumbnail = (self.selected_thumbnail - 1) % self.get_max_index()
        self.ensure_thumbnail_visible(self.selected_thumbnail)

    def navigate_right(self):
        self.selected_thumbnail = (self.selected_thumbnail + 1) % self.get_max_index()
        self.ensure_thumbnail_visible(self.selected_thumbnail)

    def navigate_down(self):
        self.selected_thumbnail = (self.selected_thumbnail + 3) % self.get_max_index()
        self.ensure_thumbnail_visible(self.selected_thumbnail)

    def ensure_thumbnail_visible(self, previous_selected_thumbnail):
        while self.selected_thumbnail < self.render_start_index:
            self.render_start_index -= 3
            self.scroll_target_y += self.icon_size
        while self.selected_thumbnail >= self.render_start_index + self.visible_thumbnails:
            self.render_start_index += 3
            self.scroll_target_y -= self.icon_size

    def update(self, delta):
        for btn_manager in self.button_managers:
            btn_manager.update(delta)
        self.spinner_time += delta
        if self.scroll_current_y != self.scroll_target_y:
            self.scroll_current_y += (self.scroll_target_y - self.scroll_current_y) * 4.0 * (delta * 0.001)
            if abs(self.scroll_target_y - self.scroll_current_y) < 0.1:
                self.scroll_current_y = self.scroll_target_y

    def handle_thumbnail_select(self):
        self.parent.state = PLAYING_ANIMATION_STATE
        _thread.start_new_thread(self.parent.animation_player.download_animation, (self.sequences[self.selected_thumbnail],))


class AnimationPlayer(Utility):
    def __init__(self, app, parent):
        super().__init__(app)
        self.parent = parent
        self.current_sequence = None
        self.downloading = False
        self.leds_enabled = True
        self.reset()

    def reset(self):
        self.frame_time = self.parent.default_frame_time
        self.frame_timer = 0
        self.current_frame = 0

    def draw(self, ctx):
        clear_background(ctx, (0, 0, 0))
        ctx.save()
        ctx.image_smoothing = 0
        frame_drawn = False
        if self.current_sequence and 'local_frames' in self.current_sequence:
            current_frame, frame_path = self.get_current_frame_or_last_downloaded()
            if frame_path is not None:
                ctx.move_to(0, 0)
                ctx.image(frame_path, -display_x * 0.5, -display_y * 0.5, display_x, display_y)
                frame_drawn = True
                if current_frame != self.current_frame:
                    self.current_frame = current_frame
        if not frame_drawn:
            # draw text to indicate that the animation is being downloaded
            ctx.rgb(0.4, 0.4, 0.4)
            ctx.font_size = 30
            ctx.text_align = ctx.CENTER
            ctx.text_baseline = ctx.MIDDLE
            ctx.move_to(0, 0).text("Loading...")
        ctx.restore()

    def update(self, delta):
        if self.current_sequence:
            self.frame_timer += delta
            if self.frame_timer >= self.frame_time:
                self.current_frame = (self.current_frame + 1) % len(self.current_sequence['frames'])
                self.frame_timer = 0
            if self.leds_enabled:
                try:
                    self.update_f_leds()
                except Exception as e:
                    print(f"Error updating frame leds: {e}")
    
    def get_current_frame_or_last_downloaded(self):
        if self.current_sequence and 'local_frames' in self.current_sequence:
            current_frame = self.current_frame % len(self.current_sequence['local_frames'])
            frame_path = None
            while frame_path is None and current_frame >= 0:
                frame_path = self.current_sequence['local_frames'][current_frame]
                if frame_path is None:
                    current_frame -= 1
            return current_frame, frame_path
        return None

    def update_f_leds(self):
        if self.current_sequence and 'local_frames' in self.current_sequence:
            current_frame, frame_path = self.get_current_frame_or_last_downloaded()
            if frame_path is not None and 'frame_main_colors' in self.current_sequence and self.current_sequence['frame_main_colors'] is not None:
                colors = self.current_sequence['frame_main_colors'][current_frame]
                if colors is not None and len(colors) > 0:
                    for i in range(12):
                        color = colors[i % len(colors)]
                        tildagonos.leds[i+1] = color
                    tildagonos.leds.write()

    def handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES['CANCEL'] in event.button:
            self.parent.set_state(DISPLAY_THUMBNAILS_STATE)
            self.cleanup()
        elif BUTTON_TYPES['CONFIRM'] in event.button:
            self.parent.metadata_viewer.set_sequence(self.current_sequence)
            self.parent.set_state(VIEW_METADATA_STATE)
        return True

    def download_animation(self, sequence):
        self.current_sequence = sequence
        self.downloading = True
        if 'frame_time_ms' in self.current_sequence and self.current_sequence['frame_time_ms'] > 0:
            self.frame_time = self.current_sequence['frame_time_ms']
            print("Loaded frame time from sequence:", self.frame_time)
        else:
            self.frame_time = self.parent.default_frame_time
        self.current_sequence['local_frames'] = [None] * len(self.current_sequence['frames'])
        for i, frame_id in enumerate(self.current_sequence['frames']):
            if not self.downloading or self.current_sequence is None:
                return
            print(f"Downloading frame {i} for {self.current_sequence['id']}")
            frame_url = f"{api_base_url}/images/{self.current_sequence['id']}/{frame_id}"

            while not self.app.wifi_manager.is_connected():
                print("[download_animation] Waiting for Wi-Fi connection...")
                time.sleep(1)
            frame_response = requests.get(frame_url)
            if not self.downloading or self.current_sequence is None:
                return
            if frame_response.status_code == 200:
                print(f"Downloaded frame {i} for {self.current_sequence['id']}")
                frame_path = get_image_path(f"tmp/{self.current_sequence['id']}-{i}.jpg")
                with open(frame_path, "wb") as f:
                    f.write(frame_response.content)
                print(f"Saved frame {i} for {self.current_sequence['id']} to {frame_path}")
                self.current_sequence['local_frames'][i] = frame_path
            else:
                print(f"Failed to download frame {i} for {self.current_sequence['id']}")
        self.downloading = False
        print("[download_animation] running gc.collect()")
        gc.collect()

    def cleanup(self):
        if self.current_sequence:
            for frame_path in self.current_sequence['local_frames']:
                if frame_path is not None:
                    os.remove(frame_path)
            self.current_sequence = None
            print("[AnimationPlayer.cleanup] running gc.collect()")
            gc.collect()

    def on_start(self):
        self.reset()
    
    def on_exit(self):
        self.downloading = False


class AnimationMetadataViewer(Utility):
    def __init__(self, app, parent):
        super().__init__(app)
        self.parent = parent
        self.sequence = None
        self.is_favorited = False

    def on_start(self):
        pass

    def set_sequence(self, sequence):
        self.sequence = sequence
        self.is_favorited = sequence.get('favorited_by_current_user', False) or self.check_is_local_favorite(sequence['id'])

    def draw(self, ctx):
        ctx.save()
        ctx.rgb(1, 1, 1)
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.move_to(0, -70).text(f"Uploaded by:")
        ctx.move_to(0, -45).text(f"@{self.sequence.get('username')}")
        ctx.move_to(0, -20).text(f"Title:")
        ctx.move_to(0, 5).text(f"{self.sequence.get('title')}")
        heart_x, heart_y = 0, 60
        ctx.move_to(heart_x, heart_y)
        if self.is_favorited:
            ctx.rgb(1, 0, 0).text("favorited")
        else:
            ctx.rgb(0, 0, 0).text("mark as favorite")
        ctx.restore()

    def handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES['CANCEL'] in event.button:
            self.parent.set_state(PLAYING_ANIMATION_STATE)
        elif BUTTON_TYPES['CONFIRM'] in event.button:
            _thread.start_new_thread(self.favorite_animation, ())
        return True

    def favorite_animation(self):
        current_sequence_id = self.sequence['id']
        self.is_favorited = not self.is_favorited
        print(f"Setting favorite state for {current_sequence_id} to {self.is_favorited}")
        if not self.is_favorited:
            self.save_favorite(current_sequence_id, self.is_favorited)
        try:
            while not self.app.wifi_manager.is_connected():
                print("[favorite_animation] Waiting for Wi-Fi connection...")
                time.sleep(1)
            if self.is_favorited:
                response = requests.post(f"{api_base_url}/api/sequence/{current_sequence_id}/mark_favorite", headers=self.parent.get_auth_headers())
            else:
                response = requests.post(f"{api_base_url}/api/sequence/{current_sequence_id}/remove_favorite", headers=self.parent.get_auth_headers())
            if response.status_code == 200:
                print("Successfully updated animation favorite state")
                self.sequence['favorited_by_current_user'] = self.is_favorited
            else:
                print(f"Failed to favorite animation, status code: {response.status_code}")
                self.save_favorite(current_sequence_id, self.is_favorited)
        except Exception as e:
            print(f"Error favoriting animation: {e}")
            self.save_favorite(current_sequence_id, self.is_favorited)

    def save_favorite(self, sequence_id, is_favorited):
        try:
            favorites = self.parent.load_favorites_file()
            if is_favorited:
                if sequence_id not in favorites['list']:
                    favorites['list'].append(sequence_id)
            else:
                if sequence_id in favorites['list']:
                    favorites['list'].remove(sequence_id)
            self.parent.write_favorites_file(favorites)
            print("Saved favorite animations list to local file, updated list:", favorites['list'])
        except Exception as e:
            print(f"Error saving favorite animation: {e}")

    def check_is_local_favorite(self, sequence_id):
        favorites = self.parent.load_favorites_file()
        return sequence_id in favorites['list']

    def on_exit(self):
        pass


class LoginUtility(Utility):
    def __init__(self, app, parent):
        super().__init__(app)
        self.parent = parent
        self.login_code = None
        self.polling_task = None
        self.code_expired = False
        self.button_labels = ButtonLabels(app, {},
            text_color=(1, 1, 1),
            text_pressed_color=(0, 0, 0),
            bg_pressed_color=(1, 1, 1)
        )

    def on_start(self):
        self.update_button_labels()
        self.login_code = None
        self.code_expired = False
        if not self.parent.logged_in():
            _thread.start_new_thread(self.fetch_login_code, ())

    def update_button_labels(self):
        if self.parent.logged_in():
            self.button_labels.update_labels({
                "CANCEL": "Exit",
                "RIGHT": "Logout",
                "CONFIRM": "Website",
            }, clear=True)
        else:
            self.button_labels.update_labels({
                "CANCEL": "Exit",
                "CONFIRM": "Website",
            }, clear=True)

    def fetch_login_code(self):
        while not self.app.wifi_manager.is_connected():
            print("[fetch_login_code] Waiting for Wi-Fi connection...")
            time.sleep(1)
        try:
            response = requests.post(api_base_url + '/api/get_login_code', json={"badge_uuid": self.parent.badge_uuid}, headers=self.parent.get_auth_headers())
            if response.status_code == 200:
                data = response.json()
                self.login_code = data.get('code')
                if data.get('badge_uuid') is not None:
                    self.parent.badge_uuid = data.get('badge_uuid')
                    self.parent.save_auth_info(badge_uuid=self.parent.badge_uuid)
                print(f"Received login code: {self.login_code} and badge uuid: {self.parent.badge_uuid}")
                self.polling_task = _thread.start_new_thread(self.poll_for_auth, ())
            else:
                print(f"Failed to fetch login code, status code: {response.status_code}")
        except Exception as e:
            print(f"Error fetching login code: {e}")

    def poll_for_auth(self):
        while not self.parent.auth_token:
            time.sleep_ms(5000)
            if self.parent.state != LOGIN_STATE:
                return
            try:
                while not self.app.wifi_manager.is_connected():
                    print("[poll_for_auth] Waiting for Wi-Fi connection...")
                    time.sleep(1)
                response = requests.post(api_base_url + '/api/check_login_code', json={"code": self.login_code}, headers=self.parent.get_auth_headers())
                if response.status_code == 200:
                    data = response.json()
                    self.parent.auth_token = data.get('auth_token')
                    if data.get('badge_uuid'):
                        self.parent.badge_uuid = data.get('badge_uuid')
                    if self.parent.auth_token:
                        self.parent.save_auth_info(auth_token=self.parent.auth_token, badge_uuid=self.parent.badge_uuid)
                        print(f"Received auth token: {self.parent.auth_token} uuid: {self.parent.badge_uuid}")
                        self.update_button_labels()
                        break
                elif response.status_code == 401:
                    if self.parent.state != LOGIN_STATE:
                        return
                    data = response.json()
                    if data.get('error') == "code_expired":
                        self.code_expired = True
                        print("Login code has expired")
                else:
                    print(f"Failed to check login code, status code: {response.status_code}")
            except Exception as e:
                print(f"Error checking login code: {e}")

    def draw(self, ctx):
        self.button_labels.draw(ctx)
        ctx.save()
        ctx.rgb(1, 1, 1)
        ctx.font_size = 25
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        if self.parent.logged_in():
            ctx.move_to(0, 0).text(f"You are logged in!")
        elif self.code_expired:
            ctx.move_to(0, 0).text("Code expired")
        elif self.login_code:
            ctx.move_to(0, -60).text(f"Login Code:")
            ctx.rgb(0, 0, 0)
            ctx.move_to(0, 0).text(f"{self.login_code}")
        else:
            ctx.move_to(0, 0).text("Fetching login code...")
        ctx.restore()

    def handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES['CANCEL'] in event.button:
            self.parent.set_state(DISPLAY_THUMBNAILS_STATE)
            if self.polling_task:
                self.polling_task = None
        elif BUTTON_TYPES['RIGHT'] in event.button:
            if self.parent.logged_in():
                auth_token = self.parent.auth_token
                _thread.start_new_thread(self.logout_user, (auth_token,))
                self.parent.auth_token = None
                self.parent.save_auth_info(auth_token="")
                self.parent.set_state(DISPLAY_THUMBNAILS_STATE)
        elif BUTTON_TYPES['CONFIRM'] in event.button:
            self.parent.set_state(DISPLAY_WEBSITE_STATE)
        return True

    def logout_user(self, auth_token):
        try:
            while not self.app.wifi_manager.is_connected():
                print("[logout_user] Waiting for Wi-Fi connection...")
                time.sleep(1)
            response = requests.post(api_base_url + '/api/logout_badge', json={"auth_token": auth_token}, headers=self.parent.get_auth_headers())
            if response.status_code == 200:
                print("Successfully logged out user")
            else:
                print(f"Failed to log out user, status code: {response.status_code}")
        except Exception as e:
            print(f"Error logging out user: {e}")

    def on_exit(self):
        if self.polling_task:
            self.polling_task = None


class DisplayWebsiteUtility(Utility):
    def __init__(self, app, parent):
        super().__init__(app)
        self.parent = parent
        self.qr_code_path = get_image_path("images/qrcode.png")
        self.website_url = api_base_url
        self.button_labels = ButtonLabels(app, {
            "CANCEL": "Back",
        })

    def draw(self, ctx):
        clear_background(ctx, (1, 1, 1))
        ctx.save()
        ctx.move_to(0, 0)
        ctx.image_smoothing = 0
        ctx.image(self.qr_code_path, -display_x * 0.4, -display_y * 0.4, display_x * 0.8, display_y * 0.8)

        ctx.rgb(0, 0, 0)
        ctx.font_size = 20
        ctx.text_align = ctx.CENTER
        ctx.text_baseline = ctx.MIDDLE
        ctx.move_to(0, -100).text("Website:")

        ctx.restore()
        self.button_labels.draw(ctx)

    def handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES['CANCEL'] in event.button:
            self.parent.set_state(DISPLAY_THUMBNAILS_STATE)
        return True


class AnimationApp(Utility):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.state = DISPLAY_THUMBNAILS_STATE
        self.current_frame = 0
        self.default_frame_time = 200
        self.thumbnail_browser = ThumbnailBrowser(app, self)
        self.animation_player = AnimationPlayer(app, self)
        self.metadata_viewer = AnimationMetadataViewer(app, self)
        self.login_utility = LoginUtility(app, self)
        self.display_website_utility = DisplayWebsiteUtility(app, self)
        self.states = {
            DISPLAY_THUMBNAILS_STATE: self.thumbnail_browser,
            PLAYING_ANIMATION_STATE: self.animation_player,
            VIEW_METADATA_STATE: self.metadata_viewer,
            LOGIN_STATE: self.login_utility,
            DISPLAY_WEBSITE_STATE: self.display_website_utility,
        }

        self.auth_token = None
        self.badge_uuid = None

    def on_start(self):
        self.load_auth_info()
        # if not check_wifi(on_need_to_connect=self.on_wifi_connecting):
        #     print("Wi-Fi connection failed")
        #     # Handle Wi-Fi connection failure (e.g., show an error message)
        #     notification = Notification("Wi-Fi connection failed")
        #     self.app.notifications.append(notification)
        # else:
        #     print("Wi-Fi connected")
        #     notification = Notification("Wi-Fi connected", animate_duration=200, display_time=1200)
        #     self.app.notifications.append(notification)
        self.states[self.state].on_start()
    
    def on_exit(self):
        self.delete_all_files(get_image_path("thumbs"))
        self.delete_all_files(get_image_path("tmp"))

    # def on_wifi_connecting(self):
    #     print("Connecting to Wi-Fi...")
    #     notification = Notification("Connecting to Wi-Fi...", open=True, animate_duration=200, display_time=1000)
    #     self.app.notifications.append(notification)
    
    def set_state(self, state):
        self.states[self.state].on_exit()
        self.state = state
        self.states[self.state].on_start()

    def delete_all_files(self, directory):
        try:
            print("Deleting all files in", directory)
            if directory == "":
                print("Warning: Trying to delete all files in root directory, aborting.")
                return
            for file in os.listdir(directory):
                print("Deleting", directory + "/" + file, "...")
                try:
                    os.remove(directory + "/" + file)
                except Exception as e:
                    print(f"Error deleting {directory}/{file}: {e}")
            print("Finished deleting all files in", directory)
        except Exception as e:
            self.app.print_error(f"Error deleting all files in {directory}: {e}")

    def load_favorites_file(self):
        try:
            if folder_exists(favorites_file):
                with open(favorites_file, "r") as f:
                    favorites = json.load(f)
                    return favorites
        except Exception as e:
            self.app.print_error(f"Error loading favorite animations: {e}")
        return {'list': []}

    def write_favorites_file(self, favorites):
        try:
            with open(favorites_file, "w") as f:
                json.dump(favorites, f)
        except Exception as e:
            self.app.print_error(f"Error writing favorite animations: {e}")

    def logged_in(self):
        return self.auth_token is not None and self.auth_token != ""

    def load_auth_info(self):
        try:
            if folder_exists(auth_file):
                with open(auth_file, "r") as f:
                    auth_data = json.load(f)
                    self.auth_token = auth_data.get("auth_token")
                    self.badge_uuid = auth_data.get("badge_uuid")
                    print(f"Loaded auth token: {self.auth_token}")
        except Exception as e:
            print(f"Error loading auth token: {e}")

    def save_auth_info(self, auth_token=None, badge_uuid=None):
        try:
            auth_data = {}
            if folder_exists(auth_file):
                with open(auth_file, "r") as f:
                    auth_data = json.load(f)
            if auth_token is not None:
                auth_data['auth_token'] = auth_token
            if badge_uuid is not None:
                auth_data['badge_uuid'] = badge_uuid
            with open(auth_file, "w") as f:
                json.dump(auth_data, f)
                print(f"Saved auth info. token: {auth_data.get('auth_token')} uuid: {auth_data.get('badge_uuid')}")
        except Exception as e:
            print(f"Error saving auth token: {e}")

    def get_auth_headers(self):
        return {
            "auth_token": self.auth_token,
            "badge_uuid": self.badge_uuid,
        }

    def draw(self, ctx):
        clear_background(ctx)
        self.states[self.state].draw(ctx)

    def update(self, delta):
        self.states[self.state].update(delta)

    def handle_buttondown(self, event: ButtonDownEvent):
        if BUTTON_TYPES['CANCEL'] in event.button:
            self.back_button()
        return self.states[self.state].handle_buttondown(event)

    def back_button(self):
        if self.state == DISPLAY_THUMBNAILS_STATE:
            self.app.set_screen("main")
