# 🎛 ShuttlePRO v2 Listener for macOS (Python)

A native macOS listener for the Contour ShuttlePRO v2 multimedia controller, written in Python. It captures input from the jog wheel, shuttle ring, and buttons, and maps them to macOS keypresses — ideal for apps like Adobe Premiere Pro, Audition, or Final Cut.

---

## Features

- 🌀 Shuttle ring: triggers continuous left/right keypresses at variable speed
- 🎚 Jog wheel: emits one left/right keystroke per tick
- 🔘 Buttons 1–15: configurable via `mappings.json`
- 💾 JSON-based config (no code changes required)
- 🧩 Built on `hidapi`, `pyobjc`, and `Quartz` for native event posting

---

## Requirements

- macOS 11 or later
- Python 3.8+
- Install dependencies:

```bash
pip install hidapi pyobjc
```

- **Grant Accessibility Permissions**:
  - System Settings → Privacy & Security → Accessibility
  - Add your Terminal and `/usr/bin/python3`

---

## Setup

1. **Clone this repository**:

```bash
git clone https://github.com/YOUR_USERNAME/ShuttleProV2_macOS.git
cd ShuttleProV2_macOS
```

2. **Edit the key mapping config**:

Create or modify `mappings.json` in the project root:

```json
{
  "button_1": "j",
  "button_2": "k",
  "button_7": "⌘+z",
  "button_13": "⌘+s",
  "button_14": "v",
  "button_15": "c"
}
```

3. **Run the listener**:

```bash
python3 shuttle_listener.py
```

You’ll see raw data and keystroke output as input is received.

---

## Supported Key Syntax

- Regular keys: `"a"`, `"j"`, `"space"`, `"tab"`, `"return"`
- Arrow keys: `"left"`, `"right"`, `"up"`, `"down"`
- Modifiers: `⌘` / `cmd`, `ctrl`, `shift`, `alt`

### Example mappings

```json
{
  "button_1": "j",
  "button_2": "k",
  "button_3": "l",
  "button_4": "space",
  "button_5": "c",
  "button_6": "v",
  "button_7": "⌘+z",
  "button_8": "⌘+shift+z",
  "button_9": "←",
  "button_10": "→",
  "button_11": "return",
  "button_12": "tab",
  "button_13": "⌘+s",
  "button_14": "v",
  "button_15": "c"
}
```

---

## Launch on Login (Optional)

To run at login, create a `LaunchAgent`:

1. Save as `~/Library/LaunchAgents/com.shuttlepro.listener.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.shuttlepro.listener</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/YOUR_USERNAME/ShuttleProV2_macOS/shuttle_listener.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

2. Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.shuttlepro.listener.plist
```

---

## License

MIT License

---

## Author

Created by [@psacchitella](https://github.com/psacchitella)
