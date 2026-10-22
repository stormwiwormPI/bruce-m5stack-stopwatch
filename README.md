# Bruce Firmware for the M5Stack StopWatch Dev Kit

A complete port of **[Bruce Firmware](https://github.com/BruceDevices/firmware)** to the
[M5Stack StopWatch Dev Kit](https://shop.m5stack.com/products/m5stack-stopwatch-dev-kit-esp32-s3)
(Model C152, ESP32-S3R8, 16 MB flash / 8 MB PSRAM).

Everything Bruce normally does — Wi-Fi scanning, deauth, packet capture, BLE, IR, RFID/NFC,
BadUSB, the web UI, the SD-card browser — is wired up for the StopWatch's 466×466 round AMOLED
and its two top buttons. Pre-built firmware is included, plus a single cross-platform flasher
that works on Windows, Linux and macOS.

> **Legal notice** — this firmware is intended for testing and auditing networks **you own or
> are explicitly authorised to test**. Running deauth or capture attacks against networks
> without permission is illegal in most jurisdictions.

---

## Quick start

### Requirements

- Python 3.8+ on your PATH.
- `esptool` — installed automatically on first run if missing (`pip install esptool`).
- A **USB-C data cable** (not a charge-only cable).

### Windows

```
Double-click flash.bat
```

### Linux / macOS

```bash
chmod +x flash.sh     # once
./flash.sh
```

Both wrappers run `flash.py`, which detects the StopWatch port, shows a menu, and flashes.
You can also call it directly on any OS:

```bash
python flash.py                    # interactive menu
python flash.py --flash            # update the app (keeps settings and NVS)
python flash.py --flash --full     # write the merged image at 0x0
python flash.py --erase            # erase the chip, then flash everything
python flash.py --flash --port COM4
python flash.py --build            # rebuild from source, then copy binaries/
python flash.py --monitor          # 115200 baud serial monitor
```

Menu option **1** updates the application at `0x10000` and keeps your settings, saved
networks and NVS. Use option **2** (clean flash) only on a blank or previously stock device —
it erases the whole chip and writes the merged image at `0x0`.

### If the port is not detected

1. Hold the **left (top) button** while plugging the USB-C cable in to force download mode.
2. On Linux, add yourself to the `dialout` group (`sudo usermod -aG dialout $USER`, then log out
   and back in) or your user cannot open `/dev/ttyACM*`.
3. On macOS the port is usually `/dev/cu.usbmodem*`. The flasher filters out unrelated
   USB-serial adapters automatically.

---

## Controls

The StopWatch has two buttons, so Bruce's five inputs (Prev / Next / Down / Up / Select / Back)
are mapped onto clicks and holds. Multi-click state is resolved 260 ms after the last release.

| Input | Action |
| :--- | :--- |
| **Left button** — 1 click | Previous / move left |
| **Left button** — 2 clicks | Move down |
| **Left button** — hold > 500 ms | **Back / Esc** |
| **Right button** — 1 click | Next / move right |
| **Right button** — 2 clicks | Move up |
| **Right button** — hold > 500 ms | **Select** |
| **Touch** — tap centre | Select |
| **Touch** — tap left / right edge | Previous / next |
| **Touch** — tap top edge or swipe down | Back |
| **Touch** — virtual keyboard | Full QWERTY, inset for the round screen |

Single taps on the touchscreen are edge-latched, so one tap never types a character twice.
Any button or tap wakes the display.

---

## What's in the image

Bruce's full feature set, compiled for this board:

- **Wi-Fi** — AP scan, station connect, deauth / disassoc attacks, beacon spam, packet monitor,
  evil portal, web UI, ARP/TCP tools.
- **BLE** — BLE scan, spam, GATT explorer, HID keyboard.
- **RF / IR** — 433 MHz receive/send, IR receive/send with the built-in database.
- **RFID / NFC** — PN532 and MFRC522 readers (external modules via the Grove port).
- **BadUSB / USB HID**, **SD-card file browser**, **clock / NTP**, **settings**, **serial CLI**.

### Port-specific work

- **Round-screen UI fixes.** LovyanGFX's antialiased `drawWideLine` relies on `readRect`, which
  the CO5300 QSPI panel cannot do — icons came out black. They are now drawn with solid vector
  geometry (`fillTriangle` + rounded `fillCircle` caps) and normalised arc angles, so every
  Bruce menu icon renders correctly.
- **Keyboard rebuilt for the circle.** All four key rows and the action bar are inset inside the
  466 px circle ($R = 233$) and driven by physical buttons as well as touch.
- **Full-screen icon clearing** extended to 250 × 205 px so navigating with the large Wi-Fi icons
  no longer leaves ghosting.
- **Radio tuning.** Modem sleep is disabled (`WIFI_PS_NONE`), transmit power is raised to the
  chip maximum, and the worldwide 1–14 channel plan is applied to scan, AP, deauth and sniffer
  paths.
- **Raw-frame TX robustness.** The ESP-IDF driver only keeps a small pool of dynamic TX buffers;
  bursts of deauth frames used to exhaust it and return `ESP_ERR_NO_MEM` permanently. Raw sends are
  now paced and back off progressively until the radio has drained the queue, and the channel is
  only changed when it actually differs, so no frame burst starts with a stale channel.
- **Brightness scaling** from Bruce's 0–100 range onto the AMOLED's PWM range, with a floor so
  the screen never goes fully dark.
- **350 ms boot grace period** so PMIC/I²C start-up noise cannot trigger a phantom selection.

---

## Manual flashing

The flasher wraps these commands; use them directly if you prefer.

**Whole image at `0x0`** (bootloader + partition table + app; erases NVS and settings):

```bash
python -m esptool --chip esp32s3 --port COM4 --baud 921600 \
  --before default_reset --after hard_reset \
  write_flash -z --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x0 binaries/Bruce-m5stack-stopwatch.bin
```

**App only at `0x10000`** (keeps partitions, NVS, Wi-Fi settings and SD data):

```bash
python -m esptool --chip esp32s3 --port COM4 --baud 921600 \
  write_flash -z --flash_mode dio --flash_freq 80m --flash_size 16MB \
  0x10000 binaries/firmware.bin
```

Replace `COM4` with your port (`/dev/ttyACM0`, `/dev/cu.usbmodem…`, …).

---

## Building from source

```bash
python -m pip install platformio
cd firmware
pio run -e m5stack-stopwatch
```

The build takes roughly 7 minutes on a modern machine and produces:

| File | Offset | Purpose |
| :--- | :--- | :--- |
| `firmware/Bruce-m5stack-stopwatch.bin` | `0x0` | Merged image (bootloader + partitions + app) |
| `.pio/build/m5stack-stopwatch/bootloader.bin` | `0x0` | Bootloader |
| `.pio/build/m5stack-stopwatch/partitions.bin` | `0x8000` | Partition table |
| `.pio/build/m5stack-stopwatch/firmware.bin` | `0x10000` | Application |

`python flash.py --build` does the same and copies all four into `binaries/`.

The board definition lives in `firmware/boards/m5stack-stopwatch/`:

```
m5stack-stopwatch.ini   PlatformIO environment (ESP32-S3, 16 MB, OPI PSRAM, QSPI AMOLED)
pins_arduino.h          pin map, display and touch configuration
interface.cpp           display/touch/button driver and input mapping
```

---

## Repository layout

```
.
├── flash.bat / flash.sh          one-click wrappers
├── flash.py                      cross-platform flasher, builder, monitor
├── binaries/                     pre-built images (merged, bootloader, partitions, app)
├── firmware/                     Bruce source tree, ported to this board
│   ├── boards/m5stack-stopwatch/ board support package
│   ├── src/                      Bruce modules
│   └── platformio.ini            build environments
├── LICENSE                       AGPL-3.0 (inherited from Bruce)
└── README.md
```

Media (photos, PCB renders) and the upstream git history are not included; the source tree is a
snapshot of upstream Bruce with this board added.

---

## Hardware

| | |
| :--- | :--- |
| **SoC** | ESP32-S3R8 — dual-core LX7 @ 240 MHz, Wi-Fi 2.4 GHz + BLE 5 |
| **Memory** | 16 MB quad-SPI flash, 8 MB octal PSRAM |
| **Display** | 1.75" round AMOLED, 466 × 466 (CO5300 over QSPI) |
| **Touch** | CST820 capacitive |
| **PMIC** | M5PM1 + 450 mAh LiPo |
| **I/O expander** | M5IOE1 |
| **IMU** | BMI270 |
| **Grove port** | GPIO 48 (SDA/TX), GPIO 47 (SCL/RX) |
| **Internal I²C** | GPIO 11 (SDA), GPIO 10 (SCL) |

---

## Troubleshooting

| Symptom | Fix |
| :--- | :--- |
| `Could not open port` | Close other serial monitors; try `--port`; reinstall the USB-C cable. |
| `Failed to connect to ESP32-S3` | Hold the left button while plugging in, then retry. |
| No serial output after flashing | Use a data cable and check the port list; the StopWatch exposes USB CDC (`303A:1001`). |
| Blank / dark screen | The image is for the **16 MB** StopWatch; check you flashed the merged image at `0x0` at least once. |
| Screen flickers at boot | Harmless PMIC start-up noise; the 350 ms grace period suppresses input, not output. |
| Wi-Fi attacks do nothing | The target must be within range and on a channel the radio can reach; deauth requires the AP to be on 2.4 GHz. |

---

## Credits & licence

- **Bruce Firmware** — [BruceDevices/firmware](https://github.com/BruceDevices/firmware), the
  upstream project this port is based on. If you find this useful, support the upstream authors.
- **M5Stack** — StopWatch Dev Kit hardware, M5GFX / M5Unified.
- **LovyanGFX**, **ESP-IDF**, **Arduino-ESP32** and the libraries listed in
  [`firmware/THIRD_PARTY.md`](firmware/THIRD_PARTY.md).

This port keeps Bruce's licence: **GNU Affero General Public License v3.0** — see
[`LICENSE`](LICENSE). Any modified version distributed or exposed over a network must also be
released under the AGPL-3.0 with its source available.
