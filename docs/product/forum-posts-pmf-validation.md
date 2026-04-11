# Aquarela — Forum Posts for Product-Market Fit Validation

Created: 2026-03-23
Purpose: Gauge real buying interest before committing to Phase 3 ordering (~€470-580).
Success metric: 5+ people asking "how do I buy one?" within 3 months.

---

## 1. Sailing Anarchy — DIY & Instrumentation

**Title:** Built a €179 NMEA 2000 instrument box with WiFi dashboard — gauging interest

**Body:**

I race a Nitro 80 on Lake Lugano and got tired of the usual instrument headaches — expensive WiFi gateways that don't compute anything, data loggers with proprietary formats, and professional systems that cost more than my sails.

So I built what I actually needed: a small box that plugs into the NMEA 2000 backbone, creates a WiFi hotspot, and serves a full racing dashboard to any phone browser. No app to install, no configuration. Just connect to the WiFi and open the browser.

**What it does:**
- Reads wind, speed, depth, heading, position, COG/SOG, temperature, attitude from the N2K bus
- Computes derived data on-device: VMG, true wind (TWA/TWS/TWD), current set/drift, target speed, performance %
- Serves a 13-page dashboard: upwind, downwind, wind rose, regatta, navigation, performance, polar, sensors, etc.
- Logs every session to clean CSV files that upload directly to Njord Analytics — no format conversion, no corrupt files
- Works with any phone or tablet, any browser. iPhone, Android, whatever.

**What's inside:**
Raspberry Pi Zero 2W, USB CAN adapter, 12V-to-5V step-down, inside a 3D-printed ASA enclosure with a proper Actisense panel-mount Micro-C connector. Draws under 1W.

**What it costs to build:** About €100 in components. I'm considering producing a small batch at €179 retail — plug and play, pre-configured, ready to mount.

For context, a Digital Yacht NavLink 2 (WiFi gateway only, no logging, no derived data) is €220. A Yacht Devices YDVR-04 (logger only, no display) is €250-290. Combining those two with a phone app gets you to €500+ and you still don't get on-device VMG or true wind computation.

I've been running this on my boat all season. It's been reliable with Garmin and Airmar instruments. Haven't tested B&G or Raymarine yet — that's one reason I'm posting here.

**What I'm trying to figure out:** Is there actually demand for this beyond my own boat? If 10-20 club racers would genuinely pay €179 for a box like this, I'll produce a first batch. If it's just me, I'll keep sailing with my one-off and save myself the trouble.

If you race with NMEA 2000 instruments and this solves a problem you actually have, I'd like to hear from you. Not looking for "cool project" encouragement — I want to know if you'd actually buy one.

Happy to answer technical questions about the setup, PGN compatibility, or anything else.

[ATTACH: 4-5 dashboard screenshots — upwind page, wind rose, performance gauge, sensor overview]

---

## 2. Reddit r/sailing

**Title:** I built a €179 NMEA 2000 instrument system — dashboard on your phone, session logging, no app needed. Would you buy one?

**Body:**

I race on Lake Lugano (Switzerland) and built a small box that connects to the boat's NMEA 2000 instrument network. It creates a WiFi hotspot and serves a racing dashboard to any phone browser — VMG, true wind, wind rose, performance data, 13 pages total. It also logs every session to CSV files compatible with Njord Analytics.

No app to install. No configuration. Plug it into your N2K backbone, power it from 12V, and it just works.

The hardware is a Raspberry Pi Zero 2W with a USB CAN adapter in a waterproof enclosure. Total BOM is about €100. I'm considering building a small batch as a finished product at €179.

For comparison:
- WiFi gateway alone (Digital Yacht NavLink 2): €220
- Data logger alone (Yacht Devices YDVR-04): €250-290
- Neither of those computes VMG or true wind on-device

I've been using it on my own boat for a full season. Works with Garmin and Airmar instruments so far.

**My question:** Would you actually pay €179 for this? I'm trying to decide whether to produce a batch or just keep the one I built for myself.

If you race with NMEA 2000 instruments and this interests you, tell me what would make or break the purchase decision for you.

[IMAGES: 3-4 dashboard screenshots]

---

## 3. Cruisers Forum — Electronics

**Title:** Homemade NMEA 2000 WiFi dashboard + data logger — €179. Interest check.

**Body:**

Fellow sailors,

I built a small device for my racing boat that I'm considering turning into a product, and I'd like to gauge whether there's any real interest before I invest in a production batch.

**What it is:** A waterproof box (~120x80x45mm) that connects to your NMEA 2000 backbone via a standard Micro-C drop cable. It creates its own WiFi hotspot and serves a multi-page instrument dashboard to any phone or tablet browser. It also logs all session data to CSV files.

**What it computes on-device:**
- True wind (TWA, TWS, TWD) from apparent wind + boat speed
- VMG (upwind and downwind)
- Current set and drift
- Target boat speed and performance percentage
- All the raw sensor data: BSP, depth, heading, heel, water temp, position, COG/SOG

**What it replaces:** A WiFi gateway (€200-250) + a data logger (€250-290) + a phone app (€30). Those three products combined cost €480-570 and still don't compute derived data on-device.

**Target price:** €179, fully assembled, plug and play.

**Hardware:** Raspberry Pi Zero 2W, USB CAN adapter (SocketCAN), Actisense panel-mount Micro-C connector, ASA enclosure, 12V power input. Draws under 1W.

I've been using the prototype on my Nitro 80 on Lake Lugano for the current season. It's been solid with Garmin gWind and Airmar sensors. I haven't had a chance to test with B&G, Raymarine, or Furuno equipment yet.

I'm not here to sell anything — the product doesn't exist as a finished item yet. I'm genuinely trying to understand if there's a market for this beyond my own boat. If you'd buy one at €179, or if you'd want different features, I'd like to know.

Technical questions welcome.

[ATTACH: Dashboard screenshots, maybe a photo of the prototype box on the boat]

---

## 4. Class Association Forums (Template — adapt per class)

**Use for:** J/70 Class, Melges 24 Class, SB20 Class, or whichever one-design forums you have access to. Post in the gear/electronics section.

**Title:** Budget NMEA 2000 instrument system — €179 — anyone interested?

**Body:**

Hi all,

I race a Nitro 80 on Lake Lugano and built a small device that I think could be useful for [CLASS NAME] sailors who have NMEA 2000 instruments but don't want to spend €2,000 on a Sailmon or Expedition setup.

It's a small waterproof box that plugs into your N2K backbone and serves a full racing dashboard to your phone via WiFi. VMG, true wind, wind rose, performance data, heel angle, current — all computed on-device and displayed in real time. After sailing, you download clean session files for post-race analysis (Njord Analytics compatible).

No app needed. Any phone, any browser. One cable to N2K, one power connection. Done.

I'm considering producing a small batch at €179. For reference, that's less than a standalone WiFi gateway costs — and this does logging and on-device computation too.

Before I commit to building more, I'm checking whether there's actual demand. Would anyone here pay €179 for something like this?

Happy to share more details or screenshots if there's interest.

[ATTACH: 2-3 key dashboard screenshots]

---

## 5. YBW Forum (UK) — Electronics & Instruments

**Title:** DIY NMEA 2000 WiFi dashboard + logger — considering small production run at €179

**Body:**

I race on Lake Lugano and built a small box that connects to the boat's NMEA 2000 network and serves a racing dashboard to any phone via WiFi. It also logs session data to CSV. Computes VMG, true wind, current, and performance data on-device.

Hardware is a Raspberry Pi Zero 2W with a USB CAN adapter in a 3D-printed ASA enclosure. Panel-mount Micro-C NMEA 2000 connector. Draws under 1W from the boat's 12V.

I'm considering doing a small production run at €179 per unit, fully assembled and pre-configured. That undercuts standalone WiFi gateways (NavLink 2 at £190, YDWG-02 at £175-210) while adding data logging and on-board computation that neither of those offers.

Posting here to gauge whether there's actual buying interest from UK/European sailors, or whether I should just keep the one I built and call it a day.

If you sail with NMEA 2000 instruments and would genuinely consider buying one at that price, let me know. Also interested to hear what features would matter most to you.

[ATTACH: Dashboard screenshots]

---

## Posting Notes for Tommaso

**Before posting:**
- Take 4-5 good screenshots of the dashboard running with realistic data (use the vcan simulator if needed). Key pages: upwind instruments, wind rose, performance gauge, sensor overview, regatta page.
- If you have a photo of the prototype box (even the Pi 4 version), include it. Real hardware photos build credibility.
- Each forum has different rules about commercial posts. Read the subforum rules. Most allow "interest check" or "project share" posts in the DIY/electronics sections. Don't post in the classifieds/for-sale sections — this isn't a product listing yet.

**After posting:**
- Check back every 2-3 days for the first two weeks. Reply to every substantive question.
- Keep a tally of responses in three buckets: (1) "I'd buy one" — real demand signal, (2) "Cool project" — not a demand signal, (3) technical questions/feature requests — useful but not demand.
- The kill criterion from the launch plan: fewer than 5 concrete buying signals after 3 months = insufficient demand at €179.

**What NOT to do:**
- Don't bump your own threads.
- Don't create multiple accounts.
- Don't post in all forums on the same day — space them out over 1-2 weeks so you can adapt later posts based on early responses.
- Don't promise delivery dates or take money yet.

**Recommended posting order:**
1. Sailing Anarchy first (most technical, most skeptical — good calibration)
2. Reddit r/sailing a few days later
3. Cruisers Forum the following week
4. Class forums after you've refined the pitch based on initial responses
5. YBW if you want UK market signal
