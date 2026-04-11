# Aquarela — Raspberry Pi Operations Guide

## Quick Reference

| What | Value |
|------|-------|
| WiFi network | **Aquarela** |
| WiFi password | **aquarela1** |
| Pi IP (on Aquarela WiFi) | **10.42.0.1** |
| Pi IP (direct ethernet to Mac) | **10.42.1.1** |
| Pi hostname (on home router via Ethernet) | **aquarela.local** |
| Aquarela UI | **http://10.42.0.1:8080** (phone) or **http://aquarela.local:8080** (Mac) |
| SSH | `ssh pi@aquarela.local` or `ssh pi@10.42.1.1` |
| User / Password | `pi` / (your password) |

---

## Network Architecture

The Pi has three network interfaces, each serving a different role:

```
┌──────────────────────────────────────────────┐
│                Raspberry Pi                   │
│                                               │
│  wlan0 (Hotspot)     eth0 (Ethernet)          │
│  SSID: Aquarela      Auto-detects:            │
│  10.42.0.1/24        - Router → DHCP          │
│  DHCP server         - Direct → 10.42.1.1/24  │
│                        (serves DHCP to Mac)   │
│                                               │
│  can0 (NMEA 2000)                             │
│  250 kbps            ← boat instruments       │
└──────────────────────────────────────────────┘
```

### Ethernet auto-detection

The Pi has two ethernet profiles in NetworkManager:

1. **"Wired connection 1"** — `ipv4.method auto`, priority 10, DHCP timeout 10s
2. **"Ethernet Direct"** — `ipv4.method shared`, priority 0, IP 10.42.1.1/24

When connected to a **router**: DHCP succeeds, Pi gets a normal IP (e.g., 192.168.1.x), reachable via `aquarela.local`.

When connected **directly to Mac** (no router): DHCP times out after 10s, Pi falls back to shared mode at 10.42.1.1 and runs a DHCP server. The Mac automatically gets an IP in the 10.42.1.x range.

---

## 1. Developing (Mac at home)

Work on your Mac as usual. The Pi config stays on `"source": "can0"` for the boat.
For local development, `data/aquarela-config.json` on your Mac has `"source": "interactive"`.

### Deploy to Pi

From the project root, run the deploy script:

```bash
./deploy.sh
```

This script:
1. Builds the Svelte frontend (`npm run build`)
2. Auto-detects the Pi (tries `aquarela.local` first, falls back to `10.42.1.1`)
3. Syncs all code via rsync (excludes config, sessions, database, Android app)
4. Restarts the Aquarela service

The script works whether the Pi is on your home router or directly connected via ethernet.

### Manual deploy (if needed)

```bash
cd frontend && npm run build && cd ..
rsync -avz --delete \
  --exclude node_modules --exclude .git --exclude __pycache__ \
  --exclude venv --exclude '*.pyc' \
  --exclude 'data/aquarela-config.json' --exclude 'data/sessions' \
  --exclude 'data/aquarela.db*' --exclude 'aquarela-android' \
  ./ pi@aquarela.local:~/aquarela/
ssh pi@aquarela.local "sudo systemctl restart aquarela"
```

---

## 2. Testing (Pi at home, no boat)

### Test with virtual CAN (simulated instruments)

SSH into the Pi:

```bash
ssh pi@aquarela.local
```

Set up virtual CAN (once per boot):

```bash
sudo modprobe vcan
sudo ip link add dev vcan0 type vcan 2>/dev/null
sudo ip link set up vcan0
```

Switch config to vcan0:

```bash
sed -i 's/"source": "can0"/"source": "vcan0"/' ~/aquarela/data/aquarela-config.json
sudo systemctl restart aquarela
```

Start the fake instrument sender:

```bash
cd ~/aquarela && source venv/bin/activate && python scripts/vcan_test.py
```

Open **http://aquarela.local:8080** — you should see live data (HDG ~140°, BSP ~5.8 kt, AWS ~12.5 kt).

When done, press Ctrl+C and switch back to real CAN:

```bash
sed -i 's/"source": "vcan0"/"source": "can0"/' ~/aquarela/data/aquarela-config.json
sudo systemctl restart aquarela
```

### Test with interactive source (no Pi needed)

On your Mac, just run the app directly:

```bash
cd ~/Documents/regata-software
python3 -m uvicorn aquarela.main:app --host 0.0.0.0 --port 8080
```

Open http://localhost:8080. The interactive source responds to REST API calls for helm, wind, and position.

### Source switching via the UI

The System page has a SIM/BOAT toggle. Switching to SIM uses the interactive source; switching to BOAT uses the CAN bus. The switch resets all sensor state, so sensors will show as disconnected until real data arrives.

---

## 3. Racing (on the boat)

### Before leaving the dock

1. Power on the Pi (USB-C, 5V/3A minimum)
2. Wait ~60 seconds for boot
3. Connect your phone to WiFi network **Aquarela** (password: **aquarela1**)
4. Open the **Aquarela Android app** (auto-discovers the Pi via mDNS/IP probing)
5. Verify: System page should show WebSocket **connected**, sensors **ok**

### Connecting the Mac on the boat

Plug an ethernet cable directly from the Mac to the Pi. The Pi will:
- Try DHCP (times out in 10s since there's no router)
- Fall back to shared mode at **10.42.1.1**
- Serve DHCP to your Mac (you'll get an IP in 10.42.1.x)

The deploy script (`./deploy.sh`) will automatically find the Pi at 10.42.1.1.

### Config must be set to CAN

If you were testing with vcan0, make sure to switch back before racing:

```bash
ssh pi@10.42.0.1
sed -i 's/"source": "vcan0"/"source": "can0"/' ~/aquarela/data/aquarela-config.json
sudo systemctl restart aquarela
```

### If sensors show "dead"

- Check CAN cable connection to NMEA 2000 backbone
- Verify instruments are powered on
- SSH in and run `candump can0` to see if frames are arriving
- If no frames: check CAN HAT is seated properly on GPIO pins

### If WiFi "Aquarela" doesn't appear

- Power cycle the Pi (unplug, wait 5s, replug)
- If still missing after 2 minutes, the hotspot may need re-setup (see Initial Setup section)

### If the UI shows "Disconnected — retrying..."

```bash
ssh pi@10.42.0.1
sudo systemctl status aquarela    # check if service is running
sudo journalctl -u aquarela -n 30 # check for errors
sudo systemctl restart aquarela   # restart if needed
```

---

## 4. Android App (Aquarela Viewer)

The Android app is a WebView wrapper that auto-discovers the Pi. Source code is in `aquarela-android/`.

### How it finds the Pi

The app tries multiple discovery methods in order:
1. Connects to WiFi (with Aquarela network suggestion)
2. Probes hotspot IP (10.42.0.1:8080)
3. Runs mDNS discovery (`_http._tcp` services matching "aquarela")
4. Fallback (after 5s): unbinds from WiFi and probes localhost, aquarela.local, 192.168.1.138, 10.42.0.1, 10.42.1.1, 10.0.2.2

### Building the APK

Open `aquarela-android/` in Android Studio and build normally, or:

```bash
cd aquarela-android
./gradlew assembleDebug
# APK at app/build/outputs/apk/debug/app-debug.apk
```

Install on phone via USB:

```bash
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

### Session log downloads

The app includes a DownloadListener that handles file downloads from the Aquarela UI (session logs). Downloaded files go to the phone's Downloads folder.

### Testing in the Android emulator

The emulator can't reach the Pi directly. Set up a tunnel:

```bash
# On Mac: forward a local port to the Pi
ssh -L 8081:localhost:8080 pi@aquarela.local
# In another terminal: map emulator localhost:8080 to Mac:8081
adb reverse tcp:8080 tcp:8081
```

The app's fallback probe will find the Pi at `localhost:8080` in the emulator.

---

## 5. NMEA 2000 PGN Decoding

The Pi decodes the following PGNs from the CAN bus:

| PGN | Data | Source | Notes |
|-----|------|--------|-------|
| 126992 | System Time | GPS 24xd | UTC time |
| 127250 | Vessel Heading | GPS 24xd | Magnetic heading |
| 127257 | Attitude | Vakaros Atlas 2 | Heel and trim angles |
| 127258 | Magnetic Variation | GPS 24xd | |
| 128259 | Speed, Water Referenced | Airmar Smart TRI | BSP (boat speed) |
| 128267 | Water Depth | Airmar Smart TRI | |
| 128275 | Distance Log | Airmar Smart TRI | Trip and total distance (fast-packet, 14 bytes) |
| 129025 | Position, Rapid Update | GPS 24xd | Lat/lon |
| 129026 | COG & SOG, Rapid Update | GPS 24xd | |
| 129029 | GNSS Position Data | GPS 24xd | High-precision lat/lon + sat count (fast-packet, 51 bytes) |
| 129540 | GNSS Sats in View | GPS 24xd | Satellite count (fast-packet) |
| 130306 | Wind Data | gWind | AWA/AWS; accepts non-standard ref byte (0xFA) |
| 130310 | Environmental Parameters | Airmar Smart TRI | Water temp (standard) |
| 130311 | Environmental Parameters 2 | Airmar Smart TRI | Water temp (alternate encoding used by our Airmar) |

### Known instrument quirks

- **gWind sends ref=250 (0xFA)** instead of standard ref=2 for apparent wind. The decoder accepts this.
- **Airmar sends PGN 130311** instead of 130310 for water temperature. Both are decoded.
- **Fast-packet PGNs** (128275, 129029, 129540) require multi-frame CAN reassembly.

---

## 6. Software Architecture

```
aquarela/                    Python backend (FastAPI + uvicorn)
├── main.py                  App entry, WebSocket broadcast, source switching, heartbeat
├── config.py                Configuration management
├── nmea/
│   ├── pgn_decoder.py       PGN decoders for all NMEA 2000 messages
│   ├── source_base.py       Abstract base class for data sources
│   ├── source_can.py        CAN bus source (SocketCAN + fast-packet reassembly)
│   ├── source_interactive.py  REST-controlled source for development
│   └── source_simulator.py  Automated simulation source
├── pipeline/
│   ├── state.py             BoatState dataclass (all sensor fields)
│   ├── calibration.py       Sensor calibration offsets
│   ├── damping.py           Signal damping/filtering
│   ├── derived.py           Computed fields (VMG, true wind, current, etc.)
│   └── true_wind.py         True wind calculation
├── api/                     REST API endpoints
├── race/                    Race timer, start line, regatta logic
├── performance/             Polar engine, performance %
├── training/                Trim book, session analysis
├── logging/                 Session CSV logging
└── static/                  Built frontend (served by FastAPI)

frontend/                    Svelte frontend
└── src/pages/
    ├── UpwindPage.svelte     Upwind instruments (TWA, BSP, VMG, targets)
    ├── DownwindPage.svelte   Downwind instruments
    ├── WindRosePage.svelte   Combined AWA/TWA wind rose
    ├── RegattaPage.svelte    Race tactical display (shift indicator)
    ├── RaceTimerPage.svelte  Countdown timer
    ├── NavPage.svelte        Navigation (HDG, COG, BTW, DTW)
    ├── PerformancePage.svelte Performance gauge and charts
    ├── PolarPage.svelte      Polar diagram
    ├── MapPage.svelte        Map view
    ├── SensorsPage.svelte    Raw sensor readings grid
    ├── SystemPage.svelte     System status, source toggle, session logs
    ├── TrimPage.svelte       Trim book entry
    └── CourseSetupPage.svelte Course mark setup

aquarela-android/            Android WebView app (Kotlin)
└── app/src/main/java/com/aquarela/viewer/
    └── MainActivity.kt      Auto-discovery, WebView, download handler

scripts/
├── test_can.py              PGN diagnostic report from CAN bus
└── vcan_test.py             Virtual CAN instrument simulator

deploy.sh                    Build + rsync + restart (auto-detects Pi)
```

### Key data flow

```
NMEA 2000 bus → CAN HAT → SocketCAN → source_can.py (PGN decode + fast-packet)
    → pipeline (calibration → damping → true wind → derived fields)
    → BoatState → WebSocket broadcast (1 Hz heartbeat + on-PGN-update)
    → Svelte frontend (reactive updates)
    → Session CSV logger
```

### WebSocket heartbeat

The backend broadcasts the current BoatState once per second via a heartbeat loop, independent of CAN data arrival. This ensures the frontend stays updated even when no PGN data is flowing (e.g., instruments off, or CAN bus quiet).

---

## Useful Commands (on the Pi)

```bash
# Service management
sudo systemctl status aquarela
sudo systemctl restart aquarela
sudo journalctl -u aquarela -f        # live logs

# CAN bus diagnostics
candump can0                           # see raw NMEA 2000 frames
python scripts/test_can.py             # PGN report (which instruments are talking)

# Check config
cat ~/aquarela/data/aquarela-config.json

# Network profiles
nmcli con show                         # list all connections
nmcli con show 'Wired connection 1'    # ethernet DHCP profile
nmcli con show 'Ethernet Direct'       # ethernet direct-connect profile
nmcli con show 'Hotspot'               # WiFi hotspot profile

# Manual run (for debugging — stop service first)
sudo systemctl stop aquarela
cd ~/aquarela && source venv/bin/activate
python -m uvicorn aquarela.main:app --host 0.0.0.0 --port 8080
```

---

## Initial Setup (from scratch)

Only needed if re-flashing the SD card.

### 1. Flash SD card

- Raspberry Pi Imager → **Raspberry Pi OS Lite (64-bit)**
- Edit Settings: hostname `aquarela`, SSH enabled, user `pi`, WiFi (home network), country `CH`

### 2. First boot + system update

```bash
ssh pi@aquarela.local
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git nodejs npm can-utils
```

### 3. Copy code + Python env

From Mac:
```bash
scp -r /Users/tommaso/Documents/regata-software/ pi@aquarela.local:~/aquarela/
```

On Pi:
```bash
cd ~/aquarela && python3 -m venv venv && source venv/bin/activate
pip install fastapi uvicorn python-can pydantic numpy aiosqlite websockets
cd frontend && npm install && npm run build
```

### 4. Systemd service

```bash
sudo tee /etc/systemd/system/aquarela.service << 'EOF'
[Unit]
Description=Aquarela Sailing Instruments
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/aquarela
ExecStart=/home/pi/aquarela/venv/bin/uvicorn aquarela.main:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable aquarela && sudo systemctl start aquarela
```

### 5. WiFi Access Point

```bash
sudo nmcli device wifi hotspot ifname wlan0 ssid Aquarela password aquarela1
sudo nmcli connection modify Hotspot connection.autoconnect yes
```

### 6. Ethernet direct-connect profile

```bash
# The default "Wired connection 1" handles DHCP (router).
# Add a shared fallback for direct Mac connections:
sudo nmcli con modify 'Wired connection 1' ipv4.dhcp-timeout 10 connection.autoconnect-priority 10
sudo nmcli con add type ethernet con-name 'Ethernet Direct' ifname eth0 \
  ipv4.method shared ipv4.addresses 10.42.1.1/24 \
  connection.autoconnect yes connection.autoconnect-priority 0
```

### 7. CAN HAT

Add to `/boot/firmware/config.txt`:
```
dtparam=spi=on
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=23
dtoverlay=mcp2515-can1,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay
```

Create `/etc/network/interfaces.d/can0`:
```
auto can0
iface can0 inet manual
    pre-up /sbin/ip link set can0 type can bitrate 250000
    up /sbin/ip link set can0 up
    post-up /sbin/ip link set can0 txqueuelen 65536
    down /sbin/ip link set can0 down
```

Same for `can1`. Reboot.
