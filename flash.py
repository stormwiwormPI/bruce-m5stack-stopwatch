#!/usr/bin/env python3
"""
Bruce Firmware flasher for the M5Stack StopWatch Dev Kit (ESP32-S3).

Works on Windows, Linux and macOS.  Everything is driven from this one file;
``flash.bat`` and ``flash.sh`` are thin wrappers around it.

Examples
--------
    python flash.py                 # interactive menu
    python flash.py --flash         # update the app (keeps settings and NVS)
    python flash.py --flash --full  # write the merged image at 0x0
    python flash.py --erase         # erase the chip, then flash everything
    python flash.py --flash --port COM4
    python flash.py --build         # build from source with PlatformIO
    python flash.py --monitor       # open a 115200 baud serial monitor
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

ROOT = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(ROOT, "binaries")
MERGED_BIN = os.path.join(BIN_DIR, "Bruce-m5stack-stopwatch.bin")
BOOTLOADER_BIN = os.path.join(BIN_DIR, "bootloader.bin")
PARTITIONS_BIN = os.path.join(BIN_DIR, "partitions.bin")
APP_BIN = os.path.join(BIN_DIR, "firmware.bin")

FIRMWARE_DIR = os.path.join(ROOT, "firmware")
BUILD_DIR = os.path.join(FIRMWARE_DIR, ".pio", "build", "m5stack-stopwatch")

BAUD = 921600
CHIP = "esp32s3"
FLASH_OPTS = ["--flash_mode", "dio", "--flash_freq", "80m", "--flash_size", "16MB"]

# USB IDs that commonly show up on an ESP32-S3 / dev board serial port.
KNOWN_VIDS = {0x303A, 0x10C4, 0x1A86, 0x0403, 0x067B}

# --------------------------------------------------------------------------- #
# Pretty output
# --------------------------------------------------------------------------- #

_COLOR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def title(text: str) -> None:
    line = "=" * 71
    print()
    print(_c("36", line))
    print(_c("1;36", text.center(71)))
    print(_c("36", line))


def info(text: str) -> None:
    print(f"  {text}")


def ok(text: str) -> None:
    print(_c("32", f"  [OK] {text}"))


def warn(text: str) -> None:
    print(_c("33", f"  [!!] {text}"))


def error(text: str) -> None:
    print(_c("31", f"  [XX] {text}"))


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        value = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(130)
    return value or default


# --------------------------------------------------------------------------- #
# Tool discovery
# --------------------------------------------------------------------------- #


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def esptool_cmd() -> list[str] | None:
    """Return the command prefix that invokes esptool, or None."""
    if _module_available("esptool"):
        return [sys.executable, "-m", "esptool"]
    if _module_available("esptool_py"):
        return [sys.executable, "-m", "esptool"]
    for name in ("esptool.py", "esptool"):
        if shutil.which(name):
            return [name]
    return None


def pio_cmd() -> list[str] | None:
    for name in ("pio", "platformio"):
        if shutil.which(name):
            return [name]
    if _module_available("platformio"):
        return [sys.executable, "-m", "platformio"]
    return None


# --------------------------------------------------------------------------- #
# Serial ports
# --------------------------------------------------------------------------- #


_pyserial_install_tried = False


def _ensure_pyserial() -> bool:
    """Try to install pyserial once; returns True if it becomes importable."""
    global _pyserial_install_tried
    if _pyserial_install_tried:
        return _module_available("serial")
    _pyserial_install_tried = True
    warn("pyserial is not installed yet - installing it with pip...")
    try:
        subprocess.call(
            [sys.executable, "-m", "pip", "install", "--user", "pyserial"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return False
    import importlib

    importlib.invalidate_caches()
    return _module_available("serial")


def list_ports() -> list[tuple[str, str, str]]:
    try:
        from serial.tools import list_ports as lp
    except ImportError:
        if not _ensure_pyserial():
            return []
        try:
            from serial.tools import list_ports as lp
        except ImportError:
            return []

    ports = []
    for p in sorted(lp.comports(), key=lambda x: x.device):
        ports.append((p.device, p.description or "", p.hwid or ""))
    return ports


def _score_port(port: tuple[str, str, str]) -> int:
    """Prefer ESP32-S3 USB-CDC ports over generic UART bridges."""
    device, description, hwid = port
    text = f"{device} {description} {hwid}".lower()
    score = 0
    if "303a" in text or "espressif" in text:
        score += 100
    if "usb jtag" in text or "usb serial" in text or "cdc" in text:
        score += 20
    for vid in KNOWN_VIDS:
        if f"{vid:04x}" in text:
            score += 10
            break
    if sys.platform.startswith("linux") and "ttyacm" in device.lower():
        score += 15
    if sys.platform == "darwin" and "usbmodem" in device.lower():
        score += 15
    return score


def pick_port(interactive: bool, requested: str | None = None) -> str | None:
    if requested:
        return requested

    ports = list_ports()
    if not ports:
        if interactive:
            warn("No serial ports detected.")
            info("Connect the StopWatch with a USB-C data cable and try again.")
            manual = ask("Enter port manually (e.g. COM4 or /dev/ttyACM0)")
            return manual or None
        return None

    ports.sort(key=_score_port, reverse=True)

    print()
    info("Detected serial ports:")
    for idx, (device, description, _hwid) in enumerate(ports, start=1):
        marker = _c("32", " <- likely the StopWatch") if idx == 1 and _score_port(ports[0]) >= 100 else ""
        print(f"      [{idx}] {device:<16} {description}{marker}")

    if not interactive:
        return ports[0][0]

    default = ports[0][0]
    choice = ask(f"Select port [1-{len(ports)}] or type one", default)
    if choice.isdigit() and 1 <= int(choice) <= len(ports):
        return ports[int(choice) - 1][0]
    # Allow "4" -> "COM4" on Windows
    if choice.isdigit() and sys.platform == "win32":
        return f"COM{choice}"
    return choice


# --------------------------------------------------------------------------- #
# Shell helpers
# --------------------------------------------------------------------------- #


def run(cmd: list[str], cwd: str | None = None) -> int:
    printable = " ".join(f'"{c}"' if " " in c else c for c in cmd)
    print(_c("90", f"  $ {printable}"))
    try:
        return subprocess.call(cmd, cwd=cwd)
    except FileNotFoundError:
        error(f"Command not found: {cmd[0]}")
        return 127
    except KeyboardInterrupt:
        print()
        return 130


def require_esptool() -> list[str] | None:
    cmd = esptool_cmd()
    if cmd:
        return cmd

    warn("esptool is not installed yet - installing it with pip...")
    try:
        rc = subprocess.call(
            [sys.executable, "-m", "pip", "install", "--user", "esptool", "pyserial"]
        )
    except Exception:
        rc = 1
    if rc == 0:
        import importlib

        importlib.invalidate_caches()
        cmd = esptool_cmd()
        if cmd:
            ok("esptool installed.")
            return cmd

    error("esptool is not installed.")
    info("Install it with:  python -m pip install esptool pyserial")
    return None


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #


def flash(port: str, erase_first: bool = False, baud: int = BAUD, full: bool = False) -> bool:
    tool = require_esptool()
    if not tool:
        return False

    have_split = all(os.path.isfile(p) for p in (BOOTLOADER_BIN, PARTITIONS_BIN, APP_BIN))
    have_merged = os.path.isfile(MERGED_BIN)

    if not have_split and not have_merged:
        # Fall back to a local PlatformIO build directory.
        built = os.path.join(BUILD_DIR, "firmware.bin")
        if os.path.isfile(built):
            warn("Using binaries from firmware/.pio/build/m5stack-stopwatch")
            return _flash_split(tool, port, baud, BUILD_DIR, erase_first)
        error("No firmware binaries found.")
        info("Expected binaries/Bruce-m5stack-stopwatch.bin")
        info("Build them first with:  python flash.py --build")
        return False

    base = [*tool, "--chip", CHIP, "--port", port]

    if erase_first:
        title("Erasing flash")
        rc = run([*base, "--baud", str(baud), "erase_flash"])
        if rc != 0:
            warn("Erase failed at high speed, retrying at 115200...")
            rc = run([*base, "--baud", "115200", "erase_flash"])
        if rc != 0:
            error("Could not erase the flash. Is another program using the port?")
            return False

    # Erasing the chip wipes the bootloader and partition table as well, so a
    # clean flash always has to write the merged image.
    full = full or erase_first

    # The app image at 0x10000 keeps the partition table, NVS and Wi-Fi
    # settings intact.  The merged image at 0x0 is only needed on a blank
    # chip or when the partition table has to be rewritten.
    if full or not have_split:
        if not have_merged:
            error("binaries/Bruce-m5stack-stopwatch.bin is missing.")
            info("Build it with:  python flash.py --build")
            return False
        image = MERGED_BIN
        target = ["0x0", MERGED_BIN]
        detail = "merged image at 0x0 (bootloader + partitions + app)"
    else:
        image = APP_BIN
        target = ["0x10000", APP_BIN]
        detail = "app only at 0x10000 (keeps partitions, NVS and settings)"

    title("Flashing Bruce Firmware")
    info(f"Image : {os.path.basename(image)}")
    info(f"Mode  : {detail}")
    args = [*base, "--baud", str(baud), "--before", "default_reset", "--after", "hard_reset",
            "write_flash", "-z", *FLASH_OPTS, *target]

    rc = run(args)
    if rc != 0:
        warn("Flash failed at 921600 baud - retrying at 460800...")
        args = [a if a != str(baud) else "460800" for a in args]
        rc = run(args)

    if rc == 0:
        reset_device(port)
        ok("Firmware flashed successfully.")
        print()
        info(_c("1", "Controls"))
        info("  Left button   : 1 click = previous, 2 clicks = down, hold = back")
        info("  Right button  : 1 click = next,     2 clicks = up,   hold = select")
        info("  Touch         : centre = select, top / swipe down = back")
        return True

    error("Flashing failed.")
    info("1. Unplug the device, hold the top button, plug the USB cable back in.")
    info("2. Make sure the cable supports data (not charge-only).")
    info("3. Close any serial monitor / Arduino IDE that is using the port.")
    return False


def reset_device(port: str) -> bool:
    """Kick the ESP32-S3 out of USB download mode after flashing.

    esptool's RTS reset is a no-op on the native USB-Serial/JTAG peripheral, so
    the board can stay in download mode (silent, dark screen) until the cable is
    replugged. Toggling DTR/RTS through the CDC port resets it reliably.
    """
    try:
        import serial
    except ImportError:
        return False
    try:
        p = serial.Serial(port, 115200, timeout=0.2)
        p.setDTR(False)
        p.setRTS(True)
        time.sleep(0.2)
        p.setRTS(False)
        time.sleep(0.3)
        p.setDTR(True)
        time.sleep(0.2)
        p.close()
        return True
    except Exception:
        return False


def _flash_split(tool: list[str], port: str, baud: int, build_dir: str, erase_first: bool) -> bool:
    base = [*tool, "--chip", CHIP, "--port", port, "--baud", str(baud)]
    if erase_first:
        run([*base, "erase_flash"])
    rc = run([*base, "--before", "default_reset", "--after", "hard_reset",
              "write_flash", "-z", *FLASH_OPTS,
              "0x0", os.path.join(build_dir, "bootloader.bin"),
              "0x8000", os.path.join(build_dir, "partitions.bin"),
              "0x10000", os.path.join(build_dir, "firmware.bin")])
    if rc == 0:
        reset_device(port)
        ok("Firmware flashed successfully.")
    return rc == 0


def erase(port: str) -> bool:
    tool = require_esptool()
    if not tool:
        return False
    title("Erasing flash")
    rc = run([*tool, "--chip", CHIP, "--port", port, "--baud", str(BAUD), "erase_flash"])
    if rc != 0:
        rc = run([*tool, "--chip", CHIP, "--port", port, "--baud", "115200", "erase_flash"])
    if rc == 0:
        ok("Flash erased. The device is now blank.")
    return rc == 0


def build() -> bool:
    tool = pio_cmd()
    if not tool:
        error("PlatformIO is not installed.")
        info("Install it with:  python -m pip install platformio")
        return False
    title("Building from source")
    info("Environment: m5stack-stopwatch")
    rc = run([*tool, "run", "-e", "m5stack-stopwatch"], cwd=FIRMWARE_DIR)
    if rc != 0:
        error("Build failed.")
        return False

    built_merged = os.path.join(FIRMWARE_DIR, "Bruce-m5stack-stopwatch.bin")
    if os.path.isfile(built_merged):
        os.makedirs(BIN_DIR, exist_ok=True)
        for src_name, dst_name in (
            ("Bruce-m5stack-stopwatch.bin", "Bruce-m5stack-stopwatch.bin"),
            (os.path.join(".pio", "build", "m5stack-stopwatch", "bootloader.bin"), "bootloader.bin"),
            (os.path.join(".pio", "build", "m5stack-stopwatch", "partitions.bin"), "partitions.bin"),
            (os.path.join(".pio", "build", "m5stack-stopwatch", "firmware.bin"), "firmware.bin"),
        ):
            src = os.path.join(FIRMWARE_DIR, src_name)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(BIN_DIR, dst_name))
        ok("Build finished and binaries/ was refreshed.")
    else:
        warn(f"Build finished but {built_merged} was not found.")
    return True


def monitor(port: str, baud: int = 115200) -> None:
    title(f"Serial monitor - {port} @ {baud}")
    info("Press Ctrl+C to exit.")
    try:
        import serial  # noqa: F401
    except ImportError:
        error("pyserial is not installed.  python -m pip install pyserial")
        return
    try:
        subprocess.call([sys.executable, "-m", "serial.tools.miniterm", port, str(baud)])
    except KeyboardInterrupt:
        pass


# --------------------------------------------------------------------------- #
# Interactive menu
# --------------------------------------------------------------------------- #


BANNER = r"""
  ____  ____  _   _ _____ _____    ______ _____  _____ __  __ _____ _____
 | __ )|  _ \| | | | ____| ____|  |  ___|  _ \|  ___|  \/  | ____|_   _|
 |  _ \| |_) | | | |  _| |  _|    | |_  | |_) | |_  | |\/| |  _|   | |
 | |_) |  _ <| |_| | |___| |___   |  _| |  _ <|  _| | |  | | |___  | |
 |____/|_| \_\\___/|_____|_____|  |_|   |_| \_|_|   |_|  |_|_____| |_|
"""


def menu() -> int:
    print(_c("36", BANNER))
    info(_c("1", "M5Stack StopWatch Dev Kit  -  ESP32-S3R8  -  16 MB flash"))
    print()

    port = pick_port(interactive=True)
    if not port:
        error("No port selected.")
        return 1

    while True:
        print()
        print(_c("36", "-" * 71))
        print(f"  Port: {_c('1', port)}")
        print(_c("36", "-" * 71))
        info("[1] Flash / update firmware  (keeps settings and NVS)")
        info("[2] Clean flash               (erase everything, then full image)")
        info("[3] Erase flash only          (factory reset)")
        info("[4] Build from source (PlatformIO)")
        info("[5] Serial monitor (115200 baud)")
        info("[6] Change port")
        info("[7] Exit")
        print()
        choice = ask("Choice", "1")

        if choice == "1":
            flash(port)
        elif choice == "2":
            flash(port, erase_first=True)
        elif choice == "3":
            if ask("Really erase the whole chip? type 'yes'") == "yes":
                erase(port)
        elif choice == "4":
            build()
        elif choice == "5":
            monitor(port)
        elif choice == "6":
            port = pick_port(interactive=True) or port
        elif choice == "7":
            return 0
        else:
            warn("Invalid choice.")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bruce Firmware flasher for the M5Stack StopWatch (ESP32-S3).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--port", help="serial port, e.g. COM4 or /dev/ttyACM0")
    parser.add_argument("--flash", action="store_true", help="flash the app image (keeps settings)")
    parser.add_argument("--full", action="store_true",
                        help="write the merged image at 0x0 (bootloader + partitions + app)")
    parser.add_argument("--erase", action="store_true", help="erase the whole flash, then flash everything")
    parser.add_argument("--erase-only", action="store_true", help="erase the flash and exit")
    parser.add_argument("--build", action="store_true", help="build the firmware from source")
    parser.add_argument("--monitor", action="store_true", help="open a serial monitor")
    parser.add_argument("--baud", type=int, default=BAUD, help=f"flash baud rate (default {BAUD})")
    args = parser.parse_args()

    if args.build:
        return 0 if build() else 1

    if not any((args.flash, args.full, args.erase, args.erase_only, args.monitor)):
        try:
            return menu()
        except KeyboardInterrupt:
            print()
            return 130

    port = pick_port(interactive=False, requested=args.port)
    if not port:
        error("No serial port found. Use --port to specify one.")
        return 1

    if args.erase_only:
        return 0 if erase(port) else 1

    if args.monitor:
        monitor(port)
        return 0

    return 0 if flash(port, erase_first=args.erase, baud=args.baud, full=args.full) else 1


if __name__ == "__main__":
    sys.exit(main())
