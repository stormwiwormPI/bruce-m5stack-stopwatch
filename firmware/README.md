# Bruce Firmware — source tree

This directory is a snapshot of [BruceDevices/firmware](https://github.com/BruceDevices/firmware)
with the **M5Stack StopWatch Dev Kit** board added under `boards/m5stack-stopwatch/`.

For flashing, controls and build instructions for this port, see the repository root
[`README.md`](../README.md).

Upstream documentation (other boards, modules, CLI reference) lives at
<https://github.com/BruceDevices/firmware>. Some upstream docs reference images that are not
shipped with this repository.

## Building this board

```bash
python -m pip install platformio
pio run -e m5stack-stopwatch
```

## Licence

GNU Affero General Public License v3.0 — see [`LICENSE`](LICENSE).
Bruce Firmware is © the BruceDevices contributors.
