# Guide A: HomeKit-Thread Eve -> Home Assistant (no Apple, no dongle)

For Thread-capable Eve accessories that were sold as **HomeKit** devices (before
the Matter upgrade), e.g. the Thread generation of Eve Energy plugs. We pair the
accessory over Bluetooth ourselves and push **your own** Thread network onto it,
so it joins the mesh your Home Assistant controls -- no HomePod, no Apple TV, no
"Upgrade to Matter" (which needs an Apple Thread border router).

## What you need

- A **running OpenThread Border Router (OTBR)** that HA controls, with a formed
  Thread network set as HA's **preferred** network. (Setting up the OTBR +
  `matter-server` and adding the OTBR/Thread integrations to HA is out of scope
  here -- follow the Home Assistant Thread docs.)
- A **Linux box with Bluetooth** (your workstation is fine). It only does the
  one-time pairing; the accessory then runs over Thread, so this box does **not**
  need to stay near the accessory afterwards. HA's host does **not** need
  Bluetooth.
- Python 3, and the accessory's **8-digit HomeKit setup code** (on its
  label/box).

## 1. Set up aiohomekit (patched for bleak 3.x)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install aiohomekit
# aiohomekit 3.2.x calls a bleak method removed in bleak 3.x -- patch it:
python scripts/patch_aiohomekit_bleak3.py \
  "$(python -c 'import aiohomekit, os; print(os.path.dirname(aiohomekit.__file__))')"
```

`pair_ble.py` sets `AIOHOMEKIT_TRANSPORT_BLE=1` itself (aiohomekit only enables
its BLE transport when that env var is set, or bleak is pre-imported).

## 2. Put the accessory into pairing mode

Remove it from Apple Home if it is still there, then factory-reset it (Eve
plugs: hold the button ~10 s until the LED blinks). A mains-powered plug has no
battery, so keep it plugged in and within ~1 m of your Bluetooth box.

## 3. Get your OTBR's Thread dataset

You will provision the accessory with your network's **operational dataset**
(TLV hex). Get it from the OTBR REST API or from HA's stored preferred dataset:

```bash
curl -s http://127.0.0.1:8081/node/dataset/active   # from the OTBR host
```

> This dataset contains your Thread **network master key**. Treat it as a
> secret -- pass it as an argument, never commit or share it.

## 4. Pair over BLE and provision Thread

```bash
python scripts/pair_ble.py \
  --name <NAME_SUBSTRING> \
  --code <SETUP_CODE> \
  --dataset <YOUR_OTBR_DATASET> \
  --out plug.json
```

`--name` is a substring of the accessory's advertised name (stable across the
id rotation described below). On success it writes `plug.json` (the pairing) and
sends `thread_provision(dataset)`, so the accessory joins your mesh.

> **Gotcha -- the device id rotates.** While unpaired, the accessory generates a
> new HomeKit device id every time you re-trigger pairing mode. That is why we
> match by name, not id. If a run cannot find it, re-trigger pairing mode and
> keep it close.

## 5. Confirm it joined your mesh

```bash
docker exec otbr ot-ctl child table      # a new child row appears
docker exec otbr ot-ctl srp server host  # it registers its _hap._tcp service + an OMR IPv6
```

Note the accessory's **OMR IPv6 address** -- you need it for the import.

## 6. Import into Home Assistant

Continue with **[ha-import.md](ha-import.md)** using `--connection CoAP` and
`--ip <the OMR IPv6 address>`. HA reaches Thread accessories over CoAP via the
OTBR; make sure HA's host has a route to the Thread OMR prefix (the OTBR creates
a `wpan0` interface and route on its host).
