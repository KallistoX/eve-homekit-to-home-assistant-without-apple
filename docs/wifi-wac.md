# Guide B: Wi-Fi Eve -> Home Assistant via WAC (no Apple)

For **Wi-Fi-only** Eve HomeKit accessories, e.g. the Eve Energy Strip (2019,
`10EAZ8301` / `20EAZ8301`). These have no Thread and are not Matter. They join
Wi-Fi through Apple's **WAC** (Wireless Accessory Configuration) -- an
MFi-restricted, undocumented protocol normally driven only by an iPhone. We
drive it ourselves with an open-source WAC client, so **no Apple device** is
needed. The accessory has the MFi chip; the client does not.

> How to tell a Wi-Fi Eve from a Thread one: when factory-reset, a Wi-Fi Eve
> broadcasts its **own open Wi-Fi network** (a SoftAP, e.g. "Eve Energy Strip
> XXXX") and advertises `_hap._tcp` on it. A Thread Eve advertises over BLE for
> setup instead -- use [Guide A](thread.md) for those.

## What you need

- A **Linux box with Wi-Fi** (`wlan0`). If it normally uses Ethernet, enable the
  Wi-Fi radio: `nmcli radio wifi on` (and `rfkill unblock wifi`). Ethernet stays
  primary, so SSH does not drop while `wlan0` roams.
- A **Go toolchain** (to build the WAC client).
- Python 3 + aiohomekit (for the pairing step -- see [Guide A](thread.md) step 1
  for the venv; the bleak patch is not needed for the IP pairing but does no
  harm).
- Your **target Wi-Fi SSID + PSK**, and the accessory's **8-digit setup code**.

## 1. Reset the accessory and find its SoftAP

Factory-reset it (Eve Energy Strip: unplug, wait for the boot LED to settle,
then hold outlets 1 + 3 for ~10 s until all LEDs blink). It now broadcasts an
open SoftAP:

```bash
nmcli dev wifi list | grep -i eve   # note the SSID; SECURITY should be "--" (open)
```

## 2. Build the WAC client

```bash
git clone https://github.com/BertoldVdb/WACResearch
mkdir -p WACResearch/waclib/examples/wac_cc
cp scripts/wac_configure_commit.go WACResearch/waclib/examples/wac_cc/main.go
( cd WACResearch/waclib/examples/wac_cc && GOFLAGS=-mod=mod go build -o /tmp/wac_cc . )
```

(WACResearch is MIT-licensed by Bertold Van den Bergh. `wac_configure_commit.go`
is a thin wrapper around its `waclib`.)

## 3. Send the Wi-Fi config (on the SoftAP)

Join the accessory's SoftAP, then send it your target credentials. The SoftAP
gateway is the accessory (typically `192.168.x.1`):

```bash
nmcli dev wifi connect "<EVE_SOFTAP_SSID>"
STRIP=$(ip -4 route show dev wlan0 | awk '/default/{print $3}')   # the accessory IP
/tmp/wac_cc -mode configure -dest "$STRIP" -ssid "<YOUR_SSID>" -password "<YOUR_PSK>"
# -> "CONFIGURE OK". The accessory tears down its SoftAP and joins YOUR Wi-Fi.
```

## 4. Commit within ~60 seconds

The accessory **rolls back to its SoftAP after ~60 s** unless you confirm the
config with a `/configured` call *on the target network*. So immediately switch
your box to the target Wi-Fi and commit to the accessory's new IP:

```bash
nmcli dev wifi connect "<YOUR_SSID>" password "<YOUR_PSK>"
sleep 8   # let the accessory associate + get its DHCP lease
/tmp/wac_cc -mode commit -dest <ACCESSORY_IP_ON_TARGET_NET>
```

> **Gotcha -- the commit "fails" but works.** The `commit` request usually times
> out *reading the response* (the accessory does not answer) yet commits
> server-side. Confirm success by the accessory **staying** on the target
> network past the ~60 s window:
>
> ```bash
> for i in $(seq 1 12); do nc -z -w2 <ACCESSORY_IP> 80 && echo up || echo gone; sleep 6; done
> ```

Reserve the accessory's IP in your DHCP server now, so it does not move.

## 5. Pair fresh over IP

> **Gotcha -- WAC wipes any pairing.** The WAC config resets HomeKit pairings, so
> any pairing you had before is gone; the accessory re-advertises `_hap._tcp`
> with a **new id** and `sf=1` (unpaired). Read the current id from mDNS and pair
> fresh (from a box that can reach the accessory -- e.g. join `wlan0` to the same
> Wi-Fi):

```bash
avahi-browse -rpt _hap._tcp | grep -i eve   # note address, port, id=..., sf=...
python scripts/pair_ip.py \
  --address <ACCESSORY_IP> --port 80 \
  --id <ID_FROM_MDNS> --code <SETUP_CODE> \
  --out strip.json
```

## 6. Networking + import

If the accessory is on an **isolated VLAN**, HA cannot reach it or rediscover it
by default. Add a firewall rule allowing HA's IP to the accessory's IP on the
HAP port (plain TCP, e.g. 80); no source-NAT is needed. mDNS often is not
reflected across VLANs, which is why the reserved IP matters.

Then continue with **[ha-import.md](ha-import.md)** using `--connection IP` and
`--ip <ACCESSORY_IP>`.
