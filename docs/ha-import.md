# Import a pairing into Home Assistant

Both guides end here. After you have paired an accessory (with `pair_ble.py` or
`pair_ip.py`) you hold a `pairing_data` JSON file. This step gets Home Assistant
to *use* that pairing so the accessory shows up with its entities.

## Why a manual transplant?

HA's `homekit_controller` integration stores the pairing as a config entry and
has **no UI to import an externally-created pairing**. But the format is
trivial: HA saves `pairing.pairing_data` **verbatim** as the config entry's
`data` field. In `homeassistant/components/homekit_controller/config_flow.py`:

```python
pairing_data = pairing.pairing_data.copy()
return self.async_create_entry(title=name, data=pairing_data)
```

So we just write a config entry whose `data` is our `pairing_data`. That is
exactly what `scripts/ha_inject_pairing.py` does.

## 1. Find the accessory's address and port

The scripts leave `Connection`/`AccessoryIP`/`AccessoryPort` for you to set at
import time (the accessory may have moved networks since pairing).

- **Wi-Fi accessory:** its LAN IP. Reserve it in your DHCP server so it never
  changes (if it is on an isolated VLAN, HA cannot rediscover it via mDNS).
- **Thread accessory:** its Thread OMR IPv6 address, from your OTBR's mDNS /
  SRP registration, e.g. `docker exec otbr ot-ctl srp server host`.

You can also read it from the `_hap._tcp` record on the same L2:

```bash
avahi-browse -rpt _hap._tcp | grep <accessory-name>
```

The HAP port is usually `80`; use whatever the mDNS SRV record shows.

## 2. Inject the config entry (HA must be STOPPED)

Edit `core.config_entries` while HA is **not running** -- otherwise the running
instance flushes its in-memory copy over your edit on shutdown. The clean way
is a throwaway container that mounts HA's config dir:

```bash
# adjust the image tag to your HA version and the config path to your setup
docker stop home-assistant

docker run --rm --entrypoint python3 \
  -v /path/to/homeassistant/config:/config \
  -v "$PWD:/work" \
  ghcr.io/home-assistant/home-assistant:<version> \
  /work/scripts/ha_inject_pairing.py \
    --pairing /work/acc.json \
    --connection IP \
    --ip DEVICE_IP \
    --port 80 \
    --title "My Accessory" \
    --config-entries /config/.storage/core.config_entries

docker start home-assistant
```

- `--connection IP` for a **Wi-Fi** accessory, `--connection CoAP` for a
  **Thread** accessory.
- The script sets `unique_id = AccessoryPairingID.lower()` and `version 1`, and
  writes a `.bak-hkimport` backup first.

If you run HA some other way (Core/Supervised/OS), the principle is the same:
stop HA, run `ha_inject_pairing.py` against `.storage/core.config_entries`,
start HA.

## 3. Restart and verify

On start, HA loads the config entry, connects to the accessory, fetches its
accessory database, and creates entities. Check the recorder database:

```bash
# inside the HA container
python3 - <<'PY'
import sqlite3
c = sqlite3.connect("/config/home-assistant_v2.db")
q = """SELECT sm.entity_id, s.state
       FROM states s JOIN states_meta sm ON s.metadata_id = sm.metadata_id
       WHERE sm.entity_id LIKE '%my_accessory%' AND s.state NOT IN ('unavailable','unknown')
       GROUP BY sm.entity_id HAVING MAX(s.last_updated_ts)"""
for r in c.execute(q):
    print(r[0], "=", r[1])
PY
```

A switch/outlet with a live state (and, for metering plugs, `power`/`energy`
sensors that update) means it works.

## Gotchas

- **Reachability.** If HA and the accessory are on different VLANs, HA must be
  allowed to reach the accessory on its HAP port (plain TCP; no source-NAT). Add
  a firewall allow rule from HA's IP to the accessory's IP:port.
- **Port changes.** HAP-over-IP accessories can change port on reboot and
  advertise the new one via mDNS. If mDNS is not reflected to HA's VLAN, HA
  cannot follow the change -- so **reserve the IP** and keep the accessory on a
  stable port, or ensure mDNS reflection covers the VLAN.
- **Restore from backup.** If anything looks wrong, stop HA, restore
  `core.config_entries.bak-hkimport`, start HA.
