#!/usr/bin/env python3
"""Pair a HomeKit accessory over BLE (optionally provision it onto a Thread
network), from any Linux box with Bluetooth. NO Apple device needed.

Prereqs: a venv with `aiohomekit` patched via patch_aiohomekit_bleak3.py.
For Thread: pass --dataset (your OTBR's active operational dataset TLV, hex).
That dataset is a SECRET (it contains the Thread network master key) -- never
commit it or paste it anywhere public.

Usage:
  python pair_ble.py --name 5AAA --code 123-45-678 --out plug.json
  python pair_ble.py --name 5AAA --code 12345678 --dataset 0e08... --out plug.json

Gotcha: the HomeKit device advertised while unpaired rotates its id on every
pairing trigger, so this matches by NAME substring (stable) instead of id.
"""
import os
import re
import sys
import json
import asyncio
import argparse

os.environ["AIOHOMEKIT_TRANSPORT_BLE"] = "1"
import bleak  # noqa: E402,F401  (must be imported before aiohomekit.const to enable BLE)
from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf  # noqa: E402
from aiohomekit import Controller  # noqa: E402
from aiohomekit.characteristic_cache import CharacteristicCacheMemory  # noqa: E402
from aiohomekit.zeroconf import ZeroconfServiceListener  # noqa: E402


def fmt_pin(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    return f"{d[0:3]}-{d[3:5]}-{d[5:8]}"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="substring of the accessory's advertised name")
    ap.add_argument("--code", required=True, help="8-digit HomeKit setup code (dashes optional)")
    ap.add_argument("--dataset", default="", help="Thread operational dataset TLV (hex) to provision")
    ap.add_argument("--adapter", default="hci0")
    ap.add_argument("--out", required=True, help="where to write pairing_data JSON")
    args = ap.parse_args()
    pin = fmt_pin(args.code)

    zc = AsyncZeroconf()
    c = Controller(async_zeroconf_instance=zc, char_cache=CharacteristicCacheMemory())
    async with zc:
        AsyncServiceBrowser(
            zc.zeroconf, ["_hap._tcp.local.", "_hap._udp.local."],
            listener=ZeroconfServiceListener(),
        )
        async with c:
            ble = next((t for t in c.transports.values()
                        if type(t).__name__ == "BleController"), None)
            if ble is None:
                print("BLE transport not loaded -- is aiohomekit patched and bleak installed?")
                return 1
            target = None
            for i in range(30):
                for d in list(getattr(ble, "discoveries", {}).values()):
                    if args.name in (getattr(d.description, "name", "") or ""):
                        target = d
                if target:
                    break
                print(f"t+{i * 2}s waiting for '{args.name}' in pairing mode...")
                await asyncio.sleep(2)
            if not target:
                print(f"'{args.name}' not found -- reset it into pairing mode, keep it close")
                return 1
            print("found:", target.description.name)
            finish = await target.async_start_pairing("acc")
            pairing = await finish(pin)
            print(">>> PAIRED <<<")
            json.dump(dict(pairing.pairing_data), open(args.out, "w"), default=str)
            print("saved pairing_data ->", args.out)
            if args.dataset:
                await pairing.thread_provision(args.dataset)
                print(">>> THREAD PROVISIONED <<<")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
