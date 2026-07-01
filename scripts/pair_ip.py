#!/usr/bin/env python3
"""Pair a HomeKit-over-IP accessory by explicit address + setup code, from any
Linux box on the same network (or joined to the accessory's SoftAP). No Apple
device, no mDNS discovery. Writes pairing_data (Connection=IP) for HA import.

Get the accessory's current id/address/port/status-flags from its _hap._tcp
mDNS record while you are on the same L2, e.g.:
    avahi-browse -rpt _hap._tcp | grep <accessory-name>
The record shows the address:port and TXT keys id=... and sf=... (sf bit0 = 1
means unpaired).

Usage:
  python pair_ip.py --address 192.168.62.1 --id AA:BB:CC:DD:EE:FF \
      --code 123-45-678 --out acc.json
"""
import re
import sys
import json
import asyncio
import argparse

from zeroconf.asyncio import AsyncServiceBrowser, AsyncZeroconf
from aiohomekit import Controller
from aiohomekit.characteristic_cache import CharacteristicCacheMemory
from aiohomekit.zeroconf import ZeroconfServiceListener, HomeKitService
from aiohomekit.controller.ip.discovery import IpDiscovery
from aiohomekit.model.feature_flags import FeatureFlags
from aiohomekit.model.status_flags import StatusFlags
from aiohomekit.model.categories import Categories


def fmt_pin(raw: str) -> str:
    d = re.sub(r"\D", "", raw)
    return f"{d[0:3]}-{d[3:5]}-{d[5:8]}"


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--address", required=True)
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--id", required=True, help="accessory HAP device id (from its _hap._tcp mDNS record)")
    ap.add_argument("--code", required=True)
    ap.add_argument("--sf", type=int, default=1, help="status flags from mDNS (1 = unpaired)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    svc = HomeKitService(
        name="accessory", id=args.id, model="", feature_flags=FeatureFlags(0),
        status_flags=StatusFlags(args.sf), config_num=1, state_num=1,
        category=Categories(1), protocol_version="1.1", type="_hap._tcp.local.",
        address=args.address, addresses=[args.address], port=args.port,
    )
    zc = AsyncZeroconf()
    c = Controller(async_zeroconf_instance=zc, char_cache=CharacteristicCacheMemory())
    async with zc:
        AsyncServiceBrowser(
            zc.zeroconf, ["_hap._tcp.local.", "_hap._udp.local."],
            listener=ZeroconfServiceListener(),
        )
        async with c:
            disc = IpDiscovery(c, svc)
            finish = await disc.async_start_pairing("acc")
            pairing = await finish(fmt_pin(args.code))
            print(">>> PAIRED <<<")
            json.dump(dict(pairing.pairing_data), open(args.out, "w"), default=str)
            print("saved pairing_data ->", args.out)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
