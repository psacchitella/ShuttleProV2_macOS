import hid
import time
import signal
import sys
import json
import os
from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGHIDEventTap

# ShuttlePRO v2 IDs
VENDOR_ID = 0x0b33
PRODUCT_ID = 0x0030

device = None
running = True
prev_jog = None
last_jog_time = 0
mappings = {}
last_mtime = None
CONFIG_PATH = os.path.expanduser("~/Users/philsacchitella/Dev/kbin/ShuttlePROv2/mappings.json")

KEYCODES = {
        "left": 0x7B,
        "→": 0x7C,
        "right": 0x7C,
        "↓": 0x7D,
        "up": 0x7E,
        "space": 0x31,
        "return": 0x24,
        "tab": 0x30,
        "escape": 0x35,
        "v": 0x09,
        "c": 0x08
    }

def signal_handler(sig, frame):
    global running
    running = False

def send_keystroke(key):
    keycode = KEYCODES.get(key)
    if keycode is None:
        return
    CGEventPost(kCGHIDEventTap, CGEventCreateKeyboardEvent(None, keycode, True))
    CGEventPost(kCGHIDEventTap, CGEventCreateKeyboardEvent(None, keycode, False))

def load_mappings():
    global mappings
    try:
        with open(CONFIG_PATH, "r") as f:
            mappings = json.load(f)
    except:
        mappings = {}

def maybe_reload_mappings():
    global last_mtime
    try:
        mtime = os.path.getmtime(CONFIG_PATH)
        if last_mtime is None or mtime != last_mtime:
            last_mtime = mtime
            load_mappings()
    except:
        pass

def handle_buttons(data):
    # data[3] and data[4] are bitmasks for buttons 1–15
    combined = (data[4] << 8) | data[3]
    for i in range(15):
        if combined & (1 << i):
            key = mappings.get(f"button_{i+1}")
            if key:
                send_keystroke(key)

def handle_jog(data):
    global prev_jog, last_jog_time
    jog_value = data[1]
    if prev_jog is not None:
        delta = jog_value - prev_jog
        if delta > 128:
            delta -= 256
        elif delta < -128:
            delta += 256
        if delta != 0:
            now = time.time()
            if now - last_jog_time > 0.01:
                send_keystroke("right" if delta > 0 else "left")
                last_jog_time = now
    prev_jog = jog_value

def handle_shuttle(data):
    # data[0] is shuttle ring: 0 = center, 1–7 right, 255–249 left
    val = data[0]
    if val == 0:
        return
    direction = "right" if 1 <= val <= 7 else "left"
    repeats = abs(val if val <= 7 else 256 - val)
    interval = max(0.005, 0.07 - (repeats * 0.01))
    send_keystroke(direction)
    time.sleep(interval)

def read_input():
    global device
    while running:
        maybe_reload_mappings()
        try:
            data = device.read(32)
            if data:
                handle_buttons(data)
                handle_jog(data)
                handle_shuttle(data)
            time.sleep(0.005)
        except:
            break

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    load_mappings()

    try:
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        device.set_nonblocking(True)
        read_input()
    except:
        pass
    finally:
        if device:
            device.close()
