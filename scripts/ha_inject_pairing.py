#!/usr/bin/env python3
"""Transplant a pairing_data JSON into Home Assistant as a homekit_controller
config entry. Run this against a STOPPED HA's config dir (mount it into a
throwaway container -- see docs/ha-import.md), so the running instance can't
flush over the edit. HA re-fetches the accessory database on first connect.

Usage (inside a container with HA's /config mounted):
  python ha_inject_pairing.py --pairing acc.json --connection IP \
      --ip DEVICE_IP --port 80 --title "My Accessory" \
      --config-entries /config/.storage/core.config_entries

Connection: IP for Wi-Fi accessories, CoAP for Thread accessories.
A .bak-hkimport backup of core.config_entries is written before editing.
"""
import json
import shutil
import secrets
import argparse
from datetime import datetime, timezone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pairing", required=True)
    ap.add_argument("--connection", required=True, choices=["IP", "CoAP"])
    ap.add_argument("--ip", required=True)
    ap.add_argument("--port", type=int, default=80)
    ap.add_argument("--title", required=True)
    ap.add_argument("--config-entries", required=True)
    args = ap.parse_args()

    pd = json.load(open(args.pairing))
    pd["Connection"] = args.connection
    pd["AccessoryIP"] = args.ip
    pd["AccessoryIPs"] = [args.ip]
    pd["AccessoryPort"] = args.port

    path = args.config_entries
    shutil.copy(path, path + ".bak-hkimport")
    d = json.load(open(path))
    entries = d["data"]["entries"]
    uid = pd["AccessoryPairingID"].lower()
    if any(e["domain"] == "homekit_controller" and e.get("unique_id") == uid for e in entries):
        print("already exists, skipping")
        return 0
    ab = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
    eid = "".join(secrets.choice(ab) for _ in range(26))
    ts = datetime.now(timezone.utc).isoformat()
    entries.append({
        "created_at": ts, "modified_at": ts, "data": pd, "disabled_by": None,
        "discovery_keys": {}, "domain": "homekit_controller", "entry_id": eid,
        "minor_version": 1, "options": {}, "pref_disable_new_entities": False,
        "pref_disable_polling": False, "source": "user", "subentries": [],
        "title": args.title, "unique_id": uid, "version": 1,
    })
    json.dump(d, open(path, "w"), indent=2)
    print("injected", args.title, uid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
