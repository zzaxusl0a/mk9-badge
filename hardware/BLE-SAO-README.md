# MK9 Bluetooth SAO daughterboards

Two SAO (Simple Add-On) board designs that give the MK9 badge a Bluetooth radio so
it can act as a **Bluetooth keyboard**. The badge's RP2040 has no radio; these
boards provide it and connect over the SAO1 header as a UART. They pair with the
firmware in [`software/`](../software) (see the *Bluetooth keyboard* section of
[`software/README.md`](../software/README.md)).

- **Board A — Friend Carrier SAO** (`BLE-Friend-SAO.*`): hosts a genuine Adafruit
  Bluefruit LE UART Friend. **Home-buildable, no RF/certification work, and the
  badge firmware runs unchanged.** This is the recommended build.
- **Board B — nRF52 SAO** (`BLE-nRF52-SAO.*`): a self-contained board around a
  pre-certified Raytac MDBT42Q (nRF52832) module. A modern single-board reference;
  needs a one-time firmware flash.

Both are **KiCad 10**, 2-layer, and reuse the repo's SAO connector symbol
(`badgelife_shitty_addon_v169bis:Badgelife_sao_connector_v169bis`) and footprint
(`lib_fp:Badgelife-Shitty-v1.69bis`), matching the `SAO-adapter.*` conventions.

> **Plug into SAO1**, not SAO2. Only SAO1's two side pins (GP29/GP28) are
> hardware-UART-capable on the RP2040. Set `USE_BLE_SAO = True` in
> `software/setup.py` (the default).

---

## Host-side pin mapping (SAO1 → radio)

| SAO pin | Net | Badge RP2040 | Direction | Board A (Friend) | Board B (MDBT42Q) |
|--------:|-----|--------------|-----------|------------------|-------------------|
| 1 VCC   | VCC (+3.3 V) | 3.3 V rail | power | VIN | VDD |
| 2 GND   | GND | — | power | GND | GND |
| 3 SDA   | SDA0 | GP9 | unused by BLE | n/c | n/c |
| 4 SCL   | SCL0 | GP10 | unused by BLE | n/c | n/c |
| 5 GPIO1 | SAO1_1 | GP29 = UART0 **RX** | badge ◄ radio | **TXO** | module **TX** |
| 6 GPIO2 | SAO1_2 | GP28 = UART0 **TX** | badge ► radio | **RXI** | module **RX** |

The schematic net between GPIO1 and the radio's transmit pin is `FRIEND_TXO`; the
net between GPIO2 and the radio's receive pin is `FRIEND_RXI`. Both boards use the
same two net names so they are interchangeable from the badge's point of view.

---

## Board A — Friend Carrier SAO

Pure interconnect. A genuine **Bluefruit LE UART Friend (#2479)** solders onto the
carrier (via a 0.1″ header/socket); the carrier routes it to the SAO connector and
handles the two gotchas in copper.

**Netlist**
- SAO VCC → Friend **VIN**
- SAO GND → Friend **GND**
- SAO GPIO1 (pin 5) → Friend **TXO** (net `FRIEND_TXO`)
- SAO GPIO2 (pin 6) → Friend **RXI** (net `FRIEND_RXI`)
- Friend **CTS → GND** *(critical — the Friend ignores incoming data if CTS floats)*
- Friend **MOD**, **RTS**, **3Vo**, **DFU** → not connected

**Two build-time gotchas**
1. **CTS is tied to GND on the board** — already in the schematic.
2. **Set the Friend's on-board CMD/DATA slide switch to `CMD`.** The firmware talks
   to it with AT commands (Command Mode). The MODE pin is left unconnected on
   purpose, so the physical switch selects the mode.

Optional (not in the schematic, add if you like): a 100 nF + 1 µF cap across
VIN/GND, and a power LED + resistor. The Friend already has its own regulator and
decoupling, so these are truly optional.

### BOM — Board A
| Reference | Value | Footprint | Part Number | Distributor | Qty |
|-----------|-------|-----------|-------------|-------------|-----|
| U1 | Bluefruit LE UART Friend | 1×header socket | 2479 | Adafruit | 1 |
| X1 | SAO connector | lib_fp:Badgelife-Shitty-v1.69bis (2×3 THT) | — | badgelife | 1 |
| — | 0.1″ header/socket for U1 | PinHeader/PinSocket 1×N 2.54 mm | — | any | 1 |

All through-hole / hand-solderable.

---

## Board B — nRF52 SAO (Raytac MDBT42Q)

Self-contained: the module *is* the radio (integrated chip antenna, 32 MHz +
32.768 kHz crystals, RF matching, internal DC/DC on the -512KV2). The carrier only
provides DC power, a slow UART, and an SWD programming header.

**Netlist**
- SAO VCC → module **VDD** (module runs 1.7–3.6 V; the 3.3 V rail is fine)
- SAO GND → module **GND**
- module **TX** (default P0.06) → SAO GPIO1 (net `FRIEND_TXO`)
- module **RX** (default P0.08) → SAO GPIO2 (net `FRIEND_RXI`)
- **C1 100 nF + C2 4.7 µF** across VDD/GND (decoupling)
- **J1 SWD header** (5-pin): 1=VCC, 2=SWDIO, 3=SWDCLK, 4=RESET, 5=GND

**Layout must-do (RF):** mount the module at the **board edge** with **no copper or
ground plane under the chip-antenna** portion (honor Raytac's keep-out — confirm the
exact dimensions from the MDBT42Q datasheet). Keep a solid ground pour under the
non-antenna portion. 2-layer is fine because the certified module contains the
radio + antenna; you're only routing DC and a 9600-baud UART.

**Firmware (separate, one-time):** the module ships blank — flash it via SWD with
CircuitPython (`adafruit_ble` HID) or the Arduino nRF52 core. **Recommended:**
implement an AT-compatible command subset (`AT`, `AT+GAPDEVNAME`,
`AT+BLEKEYBOARDEN`, `AT+BLEKEYBOARDCODE`, `AT+BLEKEYBOARD`) so the badge's existing
RP2040 firmware (`software/typer.py`) drives it **unchanged** — making Board B a
drop-in replacement for Board A. (That firmware is a follow-up task, not included
here.)

### BOM — Board B
| Reference | Value | Footprint | Part Number | Distributor | Qty |
|-----------|-------|-----------|-------------|-------------|-----|
| U1 | MDBT42Q-512KV2 (nRF52832) | Raytac MDBT42Q land pattern | 4077 / MDBT42Q-512KV2 | Adafruit / Raytac | 1 |
| X1 | SAO connector | lib_fp:Badgelife-Shitty-v1.69bis (2×3 THT) | — | badgelife | 1 |
| C1 | 100 nF | C_0603_1608Metric | any | Mouser/Digikey | 1 |
| C2 | 4.7 µF | C_0603_1608Metric | any | Mouser/Digikey | 1 |
| J1 | SWD header 1×5 | PinHeader_1x05_P2.54mm_Vertical | — | any | 1 |

---

## Files
| File | What |
|------|------|
| `BLE-Friend-SAO.kicad_sch` / `.kicad_pro` | Board A schematic |
| `BLE-nRF52-SAO.kicad_sch` / `.kicad_pro` | Board B schematic |

The schematics embed all needed symbols (self-contained `lib_symbols`), so they open
without resolving external libraries. Custom symbols use the `mk9_ble:` prefix
(`Bluefruit_LE_UART_Friend`, `MDBT42Q`); the SAO connector, power, `Device:C`, and
`Conn_01x05` symbols are reused from the standard/repo libraries.

## Opening & finishing in KiCad
1. Open the `.kicad_sch` in **KiCad 10 Eeschema**.
2. Run **ERC**. Expect **two "Input Power pin not driven by a Power Output"**
   warnings on VCC/GND — these are normal because the board is powered *externally*
   through the SAO connector. To silence them, drop a `PWR_FLAG` on the VCC and GND
   nets. All other nets should be clean; verify they match the mapping table above.
3. Connectivity is established by labels/power symbols placed on the pin endpoints.
   If you prefer the usual look, add short wire stubs — connectivity is unchanged.
4. Assign/verify footprints, then lay out the PCB. **This deliverable is schematic +
   BOM only** — the PCB is not routed here.

## Verify before fabricating
- **Board A:** confirm the Friend's physical header pad order against the board silk,
  then pick/verify the matching 1×N socket footprint for U1 (the schematic uses named
  pins; the footprint pad-number ↔ pin-name mapping is a layout-time detail).
- **Board B:** confirm the MDBT42Q land pattern, decoupling values, and the exact
  antenna keep-out from the Raytac MDBT42Q datasheet and the Adafruit Feather
  nRF52832 reference design.
- Cross-check that `FRIEND_TXO` lands on SAO pin 5 and `FRIEND_RXI` on pin 6 so the
  board is a true drop-in for the badge firmware (green boot flash → pair "MK9 Badge").
