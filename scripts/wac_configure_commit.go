// wac_configure_commit: provision a Wi-Fi HomeKit accessory's WiFi with no
// Apple device, using BertoldVdb/WACResearch (MIT). The accessory (server) has
// the MFi chip; this client does not need one (uses -insecure to skip device
// validation).
//
// Build (waclib resolves inside a WACResearch checkout):
//   git clone https://github.com/BertoldVdb/WACResearch
//   mkdir -p WACResearch/waclib/examples/wac_cc
//   cp wac_configure_commit.go WACResearch/waclib/examples/wac_cc/main.go
//   cd WACResearch/waclib/examples/wac_cc && GOFLAGS=-mod=mod go build -o /tmp/wac_cc .
//
// Flow (see docs/wifi-wac.md):
//   1) join the accessory SoftAP, then:
//        wac_cc -mode configure -dest 192.168.x.1 -ssid YOUR_SSID -password YOUR_PSK
//   2) join YOUR target WiFi, then within ~60s:
//        wac_cc -mode commit -dest <accessory-ip-on-target-net>
package main

import (
	"flag"
	"log"

	"github.com/BertoldVdb/WACResearch/waclib"
)

func main() {
	mode := flag.String("mode", "", "configure|commit")
	dest := flag.String("dest", "", "accessory IP (SoftAP for configure, target-net IP for commit)")
	ssid := flag.String("ssid", "", "target WiFi SSID (configure)")
	pw := flag.String("password", "", "target WiFi PSK (configure)")
	flag.Parse()

	c := waclib.NewClient()
	c.Insecure = true // client needs no MFi chip; skip accessory validation

	switch *mode {
	case "configure":
		if _, err := c.Configure(*dest, waclib.ConfigRequest{SSID: *ssid, Password: *pw, DeviceName: "waclib"}); err != nil {
			log.Fatalln("CONFIGURE FAILED:", err)
		}
		log.Println("CONFIGURE OK (accessory joins the target WiFi; run commit within ~60s)")
	case "commit":
		// NB: this request usually times out reading the response but commits
		// server-side. Verify success by the accessory staying on the target
		// network past ~60s.
		if _, err := c.IsConfigured(*dest); err != nil {
			log.Println("commit returned:", err, "(often a read timeout; check the device persists)")
			return
		}
		log.Println("COMMIT OK")
	default:
		log.Fatalln("mode required: configure|commit")
	}
}
