---
title: "Aquarela Performance System — Shopping List & BOM"
created: 2026-02-24
updated: 2026-02-24
type: project
status: active
domain: aquarela
tags:
  - type/project
  - domain/sailing
  - domain/electronics
  - project/aquarela
  - raspberry-pi
  - nmea2000
  - hardware
related:
  - "[[Aquarela Performance System]]"
  - "[[Aquarela Njord CSV Spec]]"
summary: "Bill of materials with Amazon.it/de purchase links for the Raspberry Pi 4 + CAN HAT NMEA 2000 data logger replacing the Actisense W2K-1 on Aquarela. Includes energy upgrade: LiFePO4 battery + walkable ETFE solar panel + charge controller. Data logger ~€157-185 (net ~€0 after W2K-1 sale). Energy upgrade ~€195-245."
---

## Summary

Complete shopping list for the [[Aquarela Performance System]]. All links verified on Amazon.it and Amazon.de as of February 2026. Estimated total: **~€155-160**. The removed Actisense W2K-1 sells for ~€150-200 second-hand, so the system essentially pays for itself.

## Components

### 1. Raspberry Pi 4 Model B (4GB RAM) — ~€55-78

| Option | Store | Link |
|--------|-------|------|
| Bare board (B07TC2BK1X) | Amazon.it | [Link](https://www.amazon.it/RASPBERRY-ARM-Cortex-A72-WLAN-AC-Bluetooth-Micro-HDMI/dp/B07TC2BK1X) |
| Bare board (B0C7KXMP7W) | Amazon.it | [Link](https://www.amazon.it/Raspberry-modello-4GB-ARM-Linux/dp/B0C7KXMP7W) |
| Bare board (B07TC2BK1X) | Amazon.de | [Link](https://www.amazon.de/Raspberry-Pi-ARM-Cortex-A72-Bluetooth-Micro-HDMI/dp/B07TC2BK1X) |
| Bare board (B09TTNF8BT) | Amazon.de | [Link](https://www.amazon.de/Raspberry-Pi-4595-Modell-GB/dp/B09TTNF8BT) |

> **Note**: Buy the bare board only — the starter kits include cases, SD cards, and PSUs you don't need for this marine build.

### 2. Waveshare 2-CH CAN HAT — ~€25

Standard CAN 2.0 with MCP2515 + SN65HVD230 transceivers. NMEA 2000 runs at 250 kbps on CAN 2.0 — this is the correct HAT.

| Option | Store | Link |
|--------|-------|------|
| Waveshare 2-CH CAN HAT (B087RJ6XGG) | Amazon.it | [Link](https://www.amazon.it/Waveshare-CAN-HAT-SN65HVD230-Protection/dp/B087RJ6XGG) |
| Coolwell/Waveshare variant (B087PWNMM8) | Amazon.it | [Link](https://www.amazon.it/Coolwell-Waveshare-SN65HVD230-2-CH-Communication/dp/B087PWNMM8) |
| Waveshare 2-CH CAN HAT (B087RJ6XGG) | Amazon.de | [Link](https://www.amazon.de/Waveshare-CAN-HAT-SN65HVD230-Protection/dp/B087RJ6XGG) |

> **Alternative**: PiCAN2 with DB9 connector — useful if you prefer the Delock M12-to-DB9 cable (see #5 below).

### 3. MicroSD Card (64GB, Class A2) — ~€12

| Option | Store | Link |
|--------|-------|------|
| SanDisk Extreme 64GB A2 170MB/s (B09X7C7LL1) | Amazon.it | [Link](https://www.amazon.it/SanDisk-microSDXC-adattatore-RescuePRO-prestazioni/dp/B09X7C7LL1) |
| SanDisk Extreme Pro 64GB (B07G3GMRYF) | Amazon.it | [Link](https://www.amazon.it/SanDisk-Extreme-microSDXC-Adattatore-Performance/dp/B07G3GMRYF) |
| SanDisk Extreme 64GB (B07FCMBLV6) | Amazon.it | [Link](https://www.amazon.it/SanDisk-Extreme-microSDXC-Adattatore-Performance/dp/B07FCMBLV6) |

> **Recommendation**: The standard SanDisk Extreme (not Pro) is plenty for CSV logging. A2 class matters for faster boot and random writes.

### 4. 12V→5V Step-Down Converter (USB-C, 3A+, Waterproof) — ~€15

| Option | Store | Link |
|--------|-------|------|
| Tiardey 8-32V→5V 3A epoxy-sealed (B09PFV3SWN) | Amazon.it | [Link](https://www.amazon.it/Tiardey-Convertitore-impermeabile-alimentazione-compatibile/dp/B09PFV3SWN) |
| Greluma 12V→5V 3A USB-C (B0BX3MQ18D) | Amazon.it | [Link](https://www.amazon.it/Greluma-Convertitore-impermeabile-alimentazione-compatibile/dp/B0BX3MQ18D) |
| DewinLVD 12/24V→5V 3A 95% eff. (B0FG827QKB) | Amazon.it | [Link](https://www.amazon.it/DewinLVD-Convertitore-Impermeabile-Adattatore-Alimentazione/dp/B0FG827QKB) |

> **Important**: Must output 5V/3A via USB-C. The Pi 4 is power-hungry — underpowered PSUs cause the lightning bolt icon and instability. Epoxy-sealed units are best for marine use.

### 5. NMEA 2000 Connector (M12 5-Pin to Bare Wire) — ~€15

| Option | Store | Link |
|--------|-------|------|
| HangTon M12 5-Pin Male A-Coded to Bare Wire 1m (B0CHW79832) | Amazon.de | [Link](https://www.amazon.de/HangTon-Sensorkabel-industrielle-Automatisierung-Ger%C3%A4te-Netzwerk/dp/B0CHW79832) |
| Eonvic M12 5-Pin Female Sensor Cable (B0875MW2QV) | Amazon.de | [Link](https://www.amazon.de/Industrial-Aviation-Connector-Elektrisches-Sensorkabel/dp/B0875MW2QV) |
| M12 5-Pin A-Coded Field-Installable Connector (B0C8BK14XB) | Amazon.de | [Link](https://www.amazon.de/M12-Rundsteckverbinder-Installierbarer-Schraubanschluss-Steckverbinder/dp/B0C8BK14XB) |
| Delock M12 5-Pin to D-Sub 9 CAN Bus Cable (B0CGYY5HVK) | Amazon.de | [Link](https://www.amazon.de/-/en/66745-Cable-coded-D-Sub-Female/dp/B0CGYY5HVK) |
| CSS Electronics M12-to-DB9 Adapter | Direct | [Link](https://www.csselectronics.com/products/m12-db9-cable-5-pin) |

> **Gender note**: NMEA 2000 drop cables use **male** Micro-C to connect to a T-connector on the backbone. Get the **male** HangTon pigtail. Wire CAN-H, CAN-L, Shield/GND to the Waveshare HAT screw terminals. Leave 12V/GND pins unconnected (Pi powered separately via step-down).

### 6. IP67 Waterproof Enclosure — ~€15-20

| Option | Store | Link |
|--------|-------|------|
| ABS IP67 project box 65×50×55mm (B085NPD89P) | Amazon.it | [Link](https://www.amazon.it/copertura-giunzione-elettronica-impermeabile-strumenti/dp/B085NPD89P) |
| IP67 with transparent lid (B0CBP6HBLN) | Amazon.it | [Link](https://www.amazon.it/Derivazione-Elettrica-Impermeabile-Coperchio-Trasparente/dp/B0CBP6HBLN) |
| VONVOFF IP65 158×90×60mm (B08VGGY4VC) | Amazon.it | [Link](https://www.amazon.it/impermeabile-universale-resistente-elettronica-100x68x50mm/dp/B08VGGY4VC) |
| Sixfab IP65 for Pi/Arduino (B09TRZ5BTB) | Amazon.it | [Link](https://www.amazon.it/-/en/Outdoor-Project-Enclosure-Raspberry-Development/dp/B09TRZ5BTB) |

> **Recommendation**: The **VONVOFF** (158×90×60mm) or **Sixfab** enclosures fit a Pi 4 + CAN HAT stacked. The small 65×50×55mm ABS box is too tight for the full assembly. Replace screws with stainless steel for marine use.

### 7. 12V Power Cable + Inline Fuse — ~€10

The step-down converters have bare wire inputs. Add an inline 3A fuse between the boat's 12V and the converter.

- Search Amazon.it for [portafusibile inline 3A](https://www.amazon.it/s?k=portafusibile+inline+3A)
- Or Amazon.de for [Sicherungshalter inline 3A](https://www.amazon.de/s?k=Sicherungshalter+inline+3A)

### 8. Status LED (Panel Mount, Waterproof) — ~€5

| Option | Store | Link |
|--------|-------|------|
| 12V 8mm panel mount LED 4-pack (B07H97N3F9) | Amazon.it | [Link](https://www.amazon.it/controllo-cruscotto-pannello-pilota-furgone/dp/B07H97N3F9) |
| Fydun 12V 8mm waterproof LED (B07ZHC13B2) | Amazon.it | [Link](https://www.amazon.it/Lampadine-indicatore-Fydun-impermeabile-energetico/dp/B07ZHC13B2) |

> **Wiring**: 12V LEDs need a GPIO-controlled transistor/MOSFET from the boat's 12V, OR use a 3mm/5mm 3.3V LED with resistor directly on a GPIO pin.

### 9. Cable Glands (PG7 or PG9) — ~€5

NOT in the original parts list but essential for waterproofing the enclosure. You need 2-3 glands: one for 12V in, one for the N2K cable, optionally one for the LED wires.

- Search Amazon.it for [pressacavo PG7 IP68](https://www.amazon.it/s?k=pressacavo+PG7+IP68)
- Search Amazon.de for [Kabelverschraubung PG7 IP68](https://www.amazon.de/s?k=Kabelverschraubung+PG7+IP68)

## Tools Required

You likely already own most of these:

| Tool | Purpose | Required? |
|------|---------|-----------|
| Wire strippers | Prep bare ends from M12 pigtail and 12V cable | Yes |
| Small Phillips screwdriver | HAT screw terminals, Pi standoffs, enclosure screws | Yes |
| Drill + step drill bit (~8mm, ~16mm) | Holes in enclosure for cable glands and LED | Yes |
| Multimeter | Verify 12V input, 5V output, CAN-H/CAN-L continuity | Yes |
| Heat shrink tubing + lighter/heat gun | Insulate spliced connections (fuse to step-down) | Yes |
| Soldering iron | Only if tinning wire ends or soldering LED resistor | Optional |
| Hot glue gun | Secure Pi/HAT inside enclosure if not using standoffs | Optional |
| Zip ties / cable clips | Cable management inside enclosure | Optional |

## Budget Summary

| Item | Est. Price |
|------|-----------|
| Raspberry Pi 4 (4GB) | ~€55-78 |
| Waveshare 2-CH CAN HAT | ~€25 |
| 64GB MicroSD A2 | ~€12 |
| 12V→5V USB-C Step-Down | ~€15 |
| NMEA 2000 M12 Connector | ~€15 |
| IP67 Enclosure | ~€15-20 |
| 12V Cable + Fuse | ~€10 |
| Status LED | ~€5 |
| Cable Glands | ~€5 |
| **Total** | **~€157-185** |
| **Minus W2K-1 sale** | **-€150-200** |
| **Net cost** | **~€0** |

## Energy Upgrade — Pannello Solare + Batteria LiFePO4

### Contesto

La barca ha 2× Bosch LTX14-BS (12V, 48Wh ciascuna = **96Wh totale, 8Ah**). Con l'impianto N2K + Pi il consumo totale è ~0.9A → autonomia ~7 ore utili. Sufficiente per una giornata di regate, ma al limite. L'upgrade energia dà autonomia praticamente illimitata di giorno e ~22 ore di notte.

### 10. Pannello Solare Calpestabile (ETFE, Marino) — ~€120-150

Il pannello deve essere calpestabile, ETFE (resistente al sale), semiflessibile, antiscivolo.

| Option | Store | Link |
|--------|-------|------|
| Offgridtec ETFE 160W calpestabile antiscivolo (B0786NTKVM) | Amazon.it | [Link](https://www.amazon.it/Offgridtec-Pannelli-marittimo-flessibile-calpestabili/dp/B0786NTKVM) |
| Aysolar 100W ETFE flessibile IP67 (B0DJ591XYR) | Amazon.it | [Link](https://www.amazon.it/Aysolar-Pannello-Flessibile-Monocristallino-Roulotte/dp/B0DJ591XYR) |
| BougeRV CIGS 100W ETFE IP68 — 1.7kg (B0BPC8V2FB) | Amazon.de | [Link](https://www.amazon.de/BougeRV-Photovoltaik-Solarladeger%C3%A4t-Solaranlage-D%C3%BCnnschichtsolarmodul/dp/B0BPC8V2FB) |
| enjoy solar ETFE Marine 150W (B09QMSCN75) | Amazon.de | [Link](https://www.amazon.de/enjoy-Semiflexible-Monokristallin-Solarmodul-Gartenh%C3%A4use/dp/B09QMSCN75) |
| enjoy solar ETFE Marine 200W (B09QQRQ3Z7) | Amazon.de | [Link](https://www.amazon.de/enjoy-Semiflexible-Monokristallin-Solarmodul-Gartenh%C3%A4use/dp/B09QQRQ3Z7) |
| doitBau 200W walkable con occhielli (B0D7ZPVR4L) | Amazon.de | [Link](https://www.amazon.de/doitBau-Befestigung-Anschlussbox-Balkonkraftwerk-Wirkungsgrad/dp/B0D7ZPVR4L) |

> **Raccomandazione per il Nitro 80**: Il **BougeRV CIGS 100W** (1.7kg, IP68, ETFE) è il miglior compromesso peso/potenza per una barca da regata. Un pannello da 100W in Mediterraneo genera ~5-7A a 12V nelle ore di luce — 10× quello che serve al Pi. L'Offgridtec 160W è il top per calpestabilità (unico con superficie antiscivolo scanalata) ma misura 146×54cm — verificare se sta sulla tuga.

### 11. Batteria LiFePO4 12V — ~€60-80

Sostituisce le 2× Bosch LTX14-BS (piombo, 2×2.5kg = 5kg per 8Ah). Una LiFePO4 da 20Ah pesa meno e dà 2.5× la capacità.

| Option | Store | Link |
|--------|-------|------|
| WattCycle 12V 20Ah LiFePO4 — 3kg, 256Wh, 15.000 cicli (B0GCK78W52) | Amazon.it | [Link](https://www.amazon.it/WattCycle-12V-giocattoli-protezione-temperature/dp/B0GCK78W52) |
| WSDAV LiFePO4 12.8V 30Ah (B0FK4ZKGF9) | Amazon.it | [Link](https://www.amazon.it/WSDAV-Batteria-Ricambio-Alimentazione-Emergenza/dp/B0FK4ZKGF9) |
| 12V 20Ah LiFePO4 Deep Cycle (B0BX6RPS72) | Amazon.it | [Link](https://www.amazon.it/batteria-profonda-batterie-trollmotor-elettrico/dp/B0BX6RPS72) |
| Redodo 12V 50Ah Bluetooth — 5kg (B0DFLTN2TP) | Amazon.it | [Link](https://www.amazon.it/Redodo-12V-50Ah-Protezione-Temperatura/dp/B0DFLTN2TP) |

> **Raccomandazione**: La **WattCycle 20Ah** (3kg, 256Wh) è il giusto compromesso. Con 20Ah a 0.9A di consumo hai ~22 ore di autonomia. La Redodo 50Ah con Bluetooth è overkill per il Nitro 80 ma comoda per monitorare lo stato dal telefono. Vendendo le 2 Bosch (~€20-30 l'una) recuperi parte del costo.

### 12. Regolatore di Carica Solare — ~€15

Collega il pannello alla batteria LiFePO4 senza danneggiarla. Per un pannello fino a 100W basta un 10A PWM. **Deve supportare batterie LiFePO4** (profilo di carica diverso dal piombo).

| Option | Store | Link |
|--------|-------|------|
| EIEVEY PWM 10A 12V/24V — compatibile LiFePO4 (B0BNPGBPWQ) | Amazon.it | [Link](https://www.amazon.it/EIEVEY-Regolatore-Intelligente-Controller-10A/dp/B0BNPGBPWQ) |
| SolaMr 10A Duo-Battery per 2 batterie (B0BBLWG9V5) | Amazon.it | [Link](https://www.amazon.it/EPEVER-Duo-Battery-Regolatore-Carica-Indicatore/dp/B0BBLWG9V5) |
| Duokon 10A ultracompatto 5.2×6.8cm (B07LCMJTV1) | Amazon.it | [Link](https://www.amazon.it/Duokon-Regolatore-Intelligente-regolatore-Batteria/dp/B07LCMJTV1) |

> **Attenzione**: non tutti i regolatori PWM economici supportano LiFePO4. L'EIEVEY lo supporta esplicitamente. Il Duokon è ultracompatto ma verificare compatibilità litio. Regolatori solo piombo con batteria LiFePO4 = ricarica incompleta o danni.

### Energy Upgrade — Budget Summary

| Item | Peso | Est. Price |
|------|------|-----------|
| Pannello solare ETFE 100W | ~1.7kg | ~€120-150 |
| Batteria LiFePO4 12V 20Ah | ~3kg | ~€60-80 |
| Regolatore di carica 10A PWM | ~0.1kg | ~€15 |
| **Totale energy upgrade** | **~4.8kg** | **~€195-245** |
| Vendita 2× Bosch LTX14-BS | -5kg | -€40-60 |
| **Delta peso netto** | **-0.2kg** | |
| **Costo netto** | | **~€135-205** |

> **Nota**: Con 100W di pannello e sole mediterraneo, nelle ore di luce generi ~5-7A. La batteria da 20Ah si ricarica completamente in 3-4 ore di sole. Il Pi consuma 0.5A — il pannello produce 10× tanto. Autonomia praticamente illimitata di giorno, ~22 ore di notte.

### Autonomia a confronto

| Setup | Capacità | Consumo totale | Autonomia | Peso batterie |
|-------|----------|----------------|-----------|---------------|
| 2× Bosch LTX14-BS (attuale) | 8Ah / 96Wh | 0.9A | ~7h utili | 5kg |
| 1× LiFePO4 20Ah + solare | 20Ah / 256Wh + ricarica | 0.9A | ~22h notte / illimitata giorno | 3kg |

## Connections

- This is the bill of materials for [[Aquarela Performance System]]
- The data output format is defined in [[Aquarela Njord CSV Spec]]
- Phase 3 of the project (Pi Hardware Setup & Installation) uses this parts list
