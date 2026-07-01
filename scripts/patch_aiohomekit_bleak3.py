#!/usr/bin/env python3
"""Patch aiohomekit for bleak >= 3.x (removes register_detection_callback).

aiohomekit 3.2.x builds a BleakScanner then calls
scanner.register_detection_callback(cb) -- a method bleak 3.x deleted. This
sets the callback at construction instead. Idempotent; safe to re-run.

Usage: python patch_aiohomekit_bleak3.py /path/to/site-packages/aiohomekit

Find the package dir with:
    python -c "import aiohomekit, os; print(os.path.dirname(aiohomekit.__file__))"
"""
import sys
import pathlib


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: patch_aiohomekit_bleak3.py <aiohomekit-package-dir>")
        return 2
    f = pathlib.Path(sys.argv[1]) / "controller" / "ble" / "controller.py"
    if not f.exists():
        print(f"not found: {f}")
        return 1
    s = orig = f.read_text()
    s = s.replace(
        "self._scanner = BleakScanner()",
        "self._scanner = BleakScanner(detection_callback=self._device_detected)",
    )
    s = s.replace(
        "            self._scanner.register_detection_callback(self._device_detected)\n",
        "            # patched: detection callback set at construction (bleak 3.x)\n",
    )
    s = s.replace(
        "            self._scanner.register_detection_callback(None)\n",
        "            # patched: no register_detection_callback in bleak 3.x\n",
    )
    if s == orig:
        print("no changes (already patched, or aiohomekit layout differs)")
        return 0
    f.write_text(s)
    print(f"patched {f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
