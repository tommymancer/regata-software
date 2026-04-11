---
title: "Aquarela Product Business Plan"
created: 2026-03-20
updated: 2026-03-20
type: project
status: active
domain: aquarela
tags:
  - type/project
  - domain/sailing
  - domain/electronics
  - domain/business
  - project/aquarela
  - product-launch
related:
  - "[[Aquarela Performance System]]"
  - "[[Aquarela Electronics Inventory]]"
  - "[[Aquarela Shopping List]]"
summary: "Business plan to productize Aquarela as a plug-and-play NMEA 2000 data logger + WiFi instrument dashboard for club racers. v1 uses Pi Zero 2W at €179 retail, ~€85-95 BOM. First batch: 5 units, ~€550-675 total investment. Demand unvalidated — beta testing with fleet before wider launch."
---

## Summary

Turn the Aquarela sailing instrument system into a sellable product: a plug-and-play NMEA 2000 data logger with built-in WiFi dashboard for club racing sailors. Priced at €179-199, it undercuts every competitor while combining features that currently require 2-3 separate products costing €465-570.

## Product Definition

A waterproof box that connects to any NMEA 2000 backbone via a standard Micro-C connector. Powers from the boat's 12V system. Creates a WiFi hotspot. Serves a 13-page racing dashboard to any phone browser. Logs session data to clean CSV files compatible with Njord Analytics. Computes derived data (VMG, true wind, current set/drift) on-device.

No app to install. No configuration. Plug in, power on, sail.

## Competitive Position

The market has a clear gap:

- **Data loggers** (Yacht Devices YDVR-04 at €250-290, Actisense W2K-1 at €270) record data but have no display, no derived calculations, and use proprietary formats.
- **WiFi gateways** (Digital Yacht NavLink 2 at €220, Yacht Devices YDWG-02 at €200-250) relay raw data to phone apps but don't log or compute anything.
- **Professional systems** (Sailmon E4 at €2,000+, Expedition at $1,295) are overkill for club racers.
- **DIY solutions** (Signal K + OpenPlotter) require hours of Linux configuration.

Aquarela combines logging + WiFi dashboard + derived data + Njord export in one device at €179 — cheaper than any single gateway alone. See [[Aquarela Market Research.docx]] for full competitive analysis.

## Hardware — v1 (Pi Zero 2W)

| Component | Est. Cost |
|-----------|-----------|
| Raspberry Pi Zero 2W | €19.90 |
| MakerBase CANable 2.0 (USB CAN) | €25-30 |
| MicroSD 32GB A2 | €8-12 |
| Actisense A2K-PMW-F (panel mount Micro-C) | €16-22 |
| 12V→5V 3A USB-C step-down | €5-8 |
| Micro-USB OTG adapter | €2-3 |
| 3D printed enclosure (ASA, outsourced) | €8-15 |
| Cable gland, gasket, wiring, LED, fasteners | €6-10 |
| **Per-unit total** | **€91-120 (midpoint ~€105)** |

Retail price: €179-199. Gross margin: ~45-60%.

## v2 Roadmap — Custom ESP32 Board

Once 50-100 units sold, migrate to custom ESP32-S3 PCB:

- BOM drops to ~€20-27/unit (80% gross margin at €179)
- Power consumption drops from ~0.5W (Pi Zero 2W) to ~0.05W average (deep sleep)
- Smaller form factor, no SD card failure risk (onboard flash)
- Requires firmware rewrite (C/ESP-IDF) — Claude Code handles this
- Requires CE/RED certification (~€3-5k) due to WiFi radio

The v1→v2 transition is justified only if market demand is confirmed.

## First Batch — 5 Units

### Phased ordering

- **Phase 1 (~€55):** 1× Pi Zero 2W + CAN adapter + SD card + OTG. Validate software runs on Zero 2W.
- **Phase 2 (~€25-40):** 1× test enclosure + 1× Actisense connector. Validate physical design.
- **Phase 3 (~€470-580):** Remaining components for 5 production units.

**Total investment: €550-675.** See [[Aquarela v1 Shopping List.docx]] for complete BOM with quantities and suppliers.

### Revenue at 5 units × €179 = €895

Break-even at ~3-4 units.

## Support Model — AI-Powered

Each unit reports diagnostics (PGN traffic, error logs, software version) to a lightweight backend when connected to internet. Customer support handled by Claude:

1. Customer reports issue (e.g., "I can't see wind speed")
2. Claude reads the unit's diagnostic data remotely
3. Claude diagnoses cause (missing PGN decoder, wiring issue, configuration)
4. For software issues: Claude writes the fix, pushes OTA update to that unit
5. Claude confirms resolution with customer

This model scales from 5 to 500 units without proportional support cost increase. Requires building: diagnostic reporting endpoint, OTA update mechanism, Claude-powered support agent.

## Go-to-Market

1. **Beta (2026 season):** 5 units distributed to racers in the Lugano fleet. Free or at cost. Collect feedback, reliability data, PGN compatibility matrix.
2. **Soft launch (winter 2026/27):** Product page with pre-orders for 2027 season. Target: Swiss/Italian lake racing community.
3. **Launch (spring 2027):** Ship first paid batch. Channels: class association forums, Njord Analytics partnership ("recommended hardware"), sailing community word of mouth.
4. **Scale:** If demand exists, expand to Mediterranean club racing scene, partner with marine electronics distributors.

## Key Risks

- **Demand is unvalidated.** No customer has been asked "would you pay €179 for this?" yet. This is the #1 risk and must be addressed before Phase 3 ordering.
- **PGN compatibility.** Currently decodes 15 PGNs from Garmin/Airmar. Every new instrument brand (B&G, Raymarine, Furuno) may need decoder additions.
- **Njord dependency.** CSV export format tied to Njord Analytics. If they change spec or fold, feature needs updating.
- **Pi supply chain.** Pi Zero 2W availability has been unreliable historically. Mitigated by v2 custom board.
- **Time allocation.** Competes for non-Syngenta hours with LIMEN. Need clear prioritization.

## Decisions Still Open

- [ ] Validate demand with 5-10 sailors in the fleet
- [ ] Test Aquarela stack on Pi Zero 2W (Phase 1)
- [ ] Design enclosure (OpenSCAD/FreeCAD, Claude can generate)
- [ ] Choose 3D printing service for outsourced enclosures
- [ ] Design OTA update mechanism
- [ ] Build diagnostic reporting endpoint
- [ ] Decide on support channel (email, chat widget, WhatsApp)
- [ ] Approach Njord Analytics about partnership

## Reference Documents

- [[Aquarela Performance System]] — Technical architecture and software stack
- [[Aquarela Electronics Inventory]] — All onboard instruments and planned additions
- [[Aquarela Shopping List]] — Original component planning
- Aquarela Market Research.docx — Full competitive landscape analysis
- Aquarela v1 Shopping List.docx — Complete BOM with suppliers and phased ordering
