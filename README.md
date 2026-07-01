# eve-homekit-to-home-assistant-without-apple

Get **old Eve HomeKit accessories into Home Assistant with no Apple hardware** --
no iPhone, no HomePod, no Apple TV. Thread plugs join a Thread network your Home
Assistant already controls; Wi-Fi devices are provisioned onto your Wi-Fi via
Apple's WAC protocol. In both cases the pairing is transplanted straight into
Home Assistant.

## The problem

Older Eve devices are **HomeKit** accessories. Onboarding a HomeKit accessory
normally needs an Apple device:

- **Thread** Eve accessories expect to be commissioned onto a Thread network by
  an Apple Thread border router (HomePod mini/2, or a recent Apple TV 4K), and
  the "Upgrade to Matter" path in the Eve app requires the same.
- **Wi-Fi** Eve accessories get their Wi-Fi credentials via Apple's WAC, driven
  by an iPhone.

If you have none of that Apple hardware, the vendor path is a dead end. This
repo documents two ways around it that need **zero** Apple devices.

## Which guide do I need?

| Your Eve device | Radio | Guide |
|---|---|---|
| Thread generation of Eve Energy plugs (HomeKit, pre-Matter) | Thread + BLE | **[docs/thread.md](docs/thread.md)** |
| Eve Energy Strip (2019, `10EAZ8301` / `20EAZ8301`) and other Wi-Fi-only Eve HomeKit devices | Wi-Fi (2.4 GHz) | **[docs/wifi-wac.md](docs/wifi-wac.md)** |

How to tell them apart when factory-reset: a **Wi-Fi** Eve broadcasts its own
open Wi-Fi network (a SoftAP); a **Thread** Eve advertises over Bluetooth for
setup. (Matter-native Eve devices are out of scope -- add those through Home
Assistant's normal Matter flow.)

Both guides finish at the shared **[docs/ha-import.md](docs/ha-import.md)**.

## Prerequisites (common)

- **Home Assistant** with the `homekit_controller` integration available.
- A **Linux box** with Bluetooth (Thread guide) or Wi-Fi (Wi-Fi guide) -- your
  workstation works. HA's own host does not need Bluetooth.
- **Python 3** + [`aiohomekit`](https://github.com/Jc2k/aiohomekit).
- The accessory's **8-digit HomeKit setup code** (on its label/box).
- For the Thread guide only: a running **OpenThread Border Router** that HA
  controls, set as HA's preferred Thread network.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/patch_aiohomekit_bleak3.py` | Patches aiohomekit for bleak 3.x (which removed `register_detection_callback`). A string patcher instead of a fragile line-numbered `.patch`. |
| `scripts/pair_ble.py` | Pairs an accessory over BLE; optionally `thread_provision`s it onto your Thread network. |
| `scripts/pair_ip.py` | Pairs an accessory reachable over IP (its Wi-Fi address or SoftAP) by explicit address. |
| `scripts/wac_configure_commit.go` | Thin wrapper over BertoldVdb/WACResearch `waclib` -- `configure` (send Wi-Fi creds on the SoftAP) and `commit` (`/configured` on the target network). |
| `scripts/ha_inject_pairing.py` | Transplants a `pairing_data` JSON into HA as a `homekit_controller` config entry. |

All scripts are parameterized via CLI arguments and contain **no secrets or
site-specific values** -- you supply your SSID, PSK, IPs, setup code, and Thread
dataset. Your Thread operational dataset and any `pairing_data` files are
secrets; do not commit or share them.

## Credits

- **[BertoldVdb/WACResearch](https://github.com/BertoldVdb/WACResearch)** -- the
  WAC protocol implementation this uses for Wi-Fi provisioning. MIT, (c) 2021
  Bertold Van den Bergh.
- **[aiohomekit](https://github.com/Jc2k/aiohomekit)** -- the HomeKit controller
  library used for pairing and Thread provisioning. Apache-2.0.
- **[Home Assistant](https://www.home-assistant.io/)** `homekit_controller` --
  the integration the pairings are imported into.

## Disclaimer

These methods use reverse-engineered / undocumented Apple protocols to configure
**your own** devices. No warranty. Not affiliated with, endorsed by, or
sponsored by Apple Inc. or Eve Systems. Use at your own risk.

## License

MIT -- see [LICENSE](LICENSE).
