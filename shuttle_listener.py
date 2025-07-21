import hid
import time
import signal
import sys
import threading
from Quartz import CGEventCreateKeyboardEvent, CGEventPost, kCGHIDEventTap
import json

with open("mappings.json") as f:
    mappings = json.load(f)

# ShuttlePRO v2 vendor/product IDs
VENDOR_ID = 0x0b33
PRODUCT_ID = 0x0030

device = None
running = True
prev_jog = None
last_jog_time = 0
last_buttons_low = 0  # data[3] = buttons 1–8
last_buttons_high = 0 # data[4] = buttons 9–15
shuttle_thread = None
shuttle_active = False
shuttle_direction = None  # 'left' or 'right'
shuttle_displacement = 0  # 1-7 or -1 to -7
# Shuttle debounce settings
last_shuttle_pos = 0
last_shuttle_change = 0
shuttle_pending_direction = None
shuttle_pending_displacement = 0
DEBOUNCE_HOLD_TIME = 0.05  # in seconds


# macOS virtual keycodes
KEYCODES = {
    "left": 0x7B,
    "right": 0x7C
}

def signal_handler(sig, frame):
    global running, shuttle_active
    print("\nCTRL+C received. Exiting...")
    running = False
    shuttle_active = False

def send_keystroke(key):
    keycode = KEYCODES.get(key)
    if keycode is None:
        print(f"Unknown key: {key}")
        return
    CGEventPost(kCGHIDEventTap, CGEventCreateKeyboardEvent(None, keycode, True))
    CGEventPost(kCGHIDEventTap, CGEventCreateKeyboardEvent(None, keycode, False))
    print(f"Sent keystroke: {key}")

def list_devices():
    print("Connected HID Devices:")
    for d in hid.enumerate():
        print(f"{d['product_string']} - VID:PID = {hex(d['vendor_id'])}:{hex(d['product_id'])}")

def shuttle_loop():
    global shuttle_active, shuttle_direction, shuttle_displacement
    print("Shuttle thread started.")
    while running:
        if shuttle_active and shuttle_direction and shuttle_displacement != 0:
            # Calculate delay: greater displacement = faster keystrokes
            delay = max(0.01, 0.25 - (abs(shuttle_displacement) * 0.03))  # 0.22s down to ~0.01s
            send_keystroke(shuttle_direction)
            time.sleep(delay)
        else:
            time.sleep(0.05)
    print("Shuttle thread exited.")
    
def send_mapped_keystroke(key_string):
    from Quartz import (
        CGEventCreateKeyboardEvent, CGEventPost,
        kCGHIDEventTap, CGEventSetFlags
    )
    from AppKit import NSEventModifierFlagCommand, NSEventModifierFlagShift, NSEventModifierFlagOption, NSEventModifierFlagControl

    # Split modifiers
    parts = key_string.lower().split('+')
    key = parts[-1]
    modifiers = parts[:-1]

    # Keycode map (expandable)
    special_keys = {
        "left": 0x7B,
        "→": 0x7C,
        "right": 0x7C,
        "↓": 0x7D,
        "up": 0x7E,
        "space": 0x31,
        "return": 0x24,
        "tab": 0x30,
        "escape": 0x35
    }

    # Get keycode
    if key in special_keys:
        keycode = special_keys[key]
    elif len(key) == 1:
        keycode = ord(key)
    else:
        print(f"Unknown key: {key_string}")
        return

    # Modifier flags
    flags = 0
    if "⌘" in modifiers or "cmd" in modifiers:
        flags |= NSEventModifierFlagCommand
    if "shift" in modifiers:
        flags |= NSEventModifierFlagShift
    if "ctrl" in modifiers:
        flags |= NSEventModifierFlagControl
    if "opt" in modifiers or "alt" in modifiers:
        flags |= NSEventModifierFlagOption

    # Create and post events
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventSetFlags(down, flags)
    CGEventSetFlags(up, flags)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def interpret_input(data):
    global prev_jog, last_jog_time, last_buttons_low, last_buttons_high
    global shuttle_active, shuttle_direction, shuttle_displacement
    global last_shuttle_pos, last_shuttle_change

    jog_value = data[1]
    btn_low = data[3]
    btn_high = data[4]
    shuttle_pos = data[0]
    now = time.time()

    # --- Jog Ring Handling ---
    if prev_jog is not None:
        delta = jog_value - prev_jog
        if delta > 128:
            delta -= 256
        elif delta < -128:
            delta += 256

        if delta != 0 and time.time() - last_jog_time > 0.01:
            if delta > 0:
                send_keystroke("right")
            else:
                send_keystroke("left")
            last_jog_time = time.time()
    prev_jog = jog_value

        # --- Buttons 1–8 (data[3]) ---
    if btn_low != last_buttons_low:
        for i in range(8):
            mask = 1 << i
            if (btn_low & mask) and not (last_buttons_low & mask):
                btn_name = f"button_{i+1}"
                key = mappings.get(btn_name)
                if key:
                    send_mapped_keystroke(key)
                    print(f"{btn_name} pressed → {key}")
                else:
                    print(f"{btn_name} pressed (no mapping)")
        last_buttons_low = btn_low

    # --- Buttons 9–15 (data[4]) ---
    if btn_high != last_buttons_high:
        for i in range(7):
            mask = 1 << i
            if (btn_high & mask) and not (last_buttons_high & mask):
                btn_name = f"button_{i+9}"
                key = mappings.get(btn_name)
                if key:
                    send_mapped_keystroke(key)
                    print(f"{btn_name} pressed → {key}")
                else:
                    print(f"{btn_name} pressed (no mapping)")
        last_buttons_high = btn_high


    # --- Shuttle Ring Handling ---
    if shuttle_pos == 0:
        if shuttle_active:
            print("Shuttle ring released (centered)")
        shuttle_active = False
        shuttle_direction = None
        shuttle_displacement = 0
    elif 1 <= shuttle_pos <= 7:
        if not shuttle_active or shuttle_direction != "right":
            print(f"Shuttle ring → right (pos: {shuttle_pos})")
        shuttle_active = True
        shuttle_direction = "right"
        shuttle_displacement = shuttle_pos
    elif 249 <= shuttle_pos <= 255:
        left_disp = 256 - shuttle_pos
        if not shuttle_active or shuttle_direction != "left":
            print(f"Shuttle ring ← left (pos: {shuttle_pos})")
        shuttle_active = True
        shuttle_direction = "left"
        shuttle_displacement = left_disp
    # # --- Shuttle Ring Handling (debounced) ---
    # now = time.time()
    # if shuttle_pos == 0:
    #     # Reset all state when released
    #     if shuttle_active:
    #         print("Shuttle ring released (centered)")
    #     shuttle_active = False
    #     shuttle_direction = None
    #     shuttle_displacement = 0
    #     shuttle_pending_direction = None
    #     shuttle_pending_displacement = 0
    #     last_shuttle_pos = 0
    #     last_shuttle_change = 0
    # else:
    #     if shuttle_pos != last_shuttle_pos:
    #         # Displacement changed — reset timer
    #         last_shuttle_pos = shuttle_pos
    #         last_shuttle_change = now

    #         if 1 <= shuttle_pos <= 7:
    #             shuttle_pending_direction = "right"
    #             shuttle_pending_displacement = shuttle_pos
    #         elif 249 <= shuttle_pos <= 255:
    #             shuttle_pending_direction = "left"
    #             shuttle_pending_displacement = 256 - shuttle_pos
    #     elif not shuttle_active and now - last_shuttle_change >= DEBOUNCE_HOLD_TIME:
    #         # Held steady — now activate repeat
    #         shuttle_direction = shuttle_pending_direction
    #         shuttle_displacement = shuttle_pending_displacement
    #         shuttle_active = True
    #         print(f"Shuttle activated → {shuttle_direction} (disp: {shuttle_displacement})")
            
            
def read_input():
    global device, shuttle_thread
    print("Listening for ShuttlePRO v2 input. Press CTRL+C to stop.")

    # Start shuttle ring thread
    shuttle_thread = threading.Thread(target=shuttle_loop, daemon=True)
    shuttle_thread.start()

    while running:
        try:
            data = device.read(32)
            if data:
                interpret_input(data)
            time.sleep(0.005)
        except Exception as e:
            print(f"Error reading device: {e}")
            break

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    list_devices()

    try:
        device = hid.device()
        device.open(VENDOR_ID, PRODUCT_ID)
        device.set_nonblocking(True)
        read_input()
    except Exception as e:
        print(f"Failed to open device: {e}")
    finally:
        if device:
            device.close()
        print("Device closed. Goodbye.")
