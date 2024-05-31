# Lucas Jones 2024
import wifi
import _thread
import time

_is_connecting_wifi = False

def connect_wifi(on_need_to_connect=None):
    ssid = wifi.get_ssid()
    if not ssid:
        print("No WIFI config!")
        return False

    if not wifi.status():
        _is_connecting_wifi = True
        if on_need_to_connect:
            on_need_to_connect()
        wifi.connect()
        while True:
            print(f"Connecting to {ssid}...")
            if wifi.wait():
                _is_connecting_wifi = False
                break

    return wifi.status()

def check_wifi(on_need_to_connect=None):
    connected = connect_wifi(on_need_to_connect=on_need_to_connect)
    if not connected:
        print("No Wi-Fi connection")
        return False
    return True

def wifi_is_connecting():
    return is_connecting_wifi

class WiFiManager:
    def __init__(self, on_connected=None, on_fail=None, on_disconnect=None, on_wifi_connecting=None):
        self.on_connected = on_connected
        self.on_fail = on_fail
        self.on_disconnect = on_disconnect
        self.on_wifi_connecting = on_wifi_connecting
        self._first_connect = True
        self._connecting = False
        self._last_check = time.time()
        self._connect_start_time = None
        self.wifi_connected = False
        self.timer = 0.0
        self.done_first_update = False

    def update(self, delta):
        self.timer += delta / 1000.0
        # Run this check every second
        if self.timer - self._last_check < 1 and self.done_first_update:
            return
        self._last_check = self.timer
        self.done_first_update = True

        if not wifi.status():
            # wifi not connected
            if self._connecting:
                # Check if we have exceeded the connection timeout
                if self._connect_start_time and self.timer - self._connect_start_time > wifi.get_connection_timeout():
                    self._connecting = False
                    self._connect_start_time = None
                    print("[WiFiManager] wifi connection timed out")
                    if self.on_fail:
                        self.on_fail()
            else:
                if self.wifi_connected and self.on_disconnect:
                    self.on_disconnect()
                # wifi not connected and not trying to connect
                if self.on_wifi_connecting:
                    self.on_wifi_connecting(self._first_connect)
                self._first_connect = False
                self._connecting = True
                self._connect_start_time = self.timer
                print("[WiFiManager] trying to connect to wifi...")
                try:
                    wifi.disconnect()
                    wifi.connect()
                except Exception as e:
                    print(f"[WiFiManager] error connecting to wifi: {e}")
                    self._connecting = False
                    self._connect_start_time = None
                    if self.on_fail:
                        self.on_fail()
            self.wifi_connected = False
        else:
            # wifi is connected
            if self._connecting:
                self._connecting = False
                self._connect_start_time = None
                print("[WiFiManager] wifi connected!")
                if self.on_connected:
                    self.on_connected()
            elif not self.wifi_connected:
                if self.on_connected:
                    self.on_connected()
            self.wifi_connected = True

    def stop(self):
        wifi.stop()
        self._connecting = False
        self._first_connect = True
        self._connect_start_time = None
    
    def is_connected(self):
        return self.wifi_connected