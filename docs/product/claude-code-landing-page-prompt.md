# Claude Code Prompt — Aquarela Landing Page

Build a single-page landing site for Aquarela, a plug-and-play NMEA 2000 sailing instrument system. Deploy to Vercel. The page should feel like a premium but accessible hardware product — think Teenage Engineering meets marine electronics.

## What the product is

Aquarela is a small waterproof box that connects to any sailing boat's NMEA 2000 instrument network. It creates a WiFi hotspot and serves a full racing dashboard to any phone browser — VMG, true wind, wind rose, performance data, 13 pages total. It also logs session data to clean CSV files compatible with Njord Analytics. No app to install, no configuration, no subscription. Price: €179.

The box contains a Raspberry Pi Zero 2W, a USB CAN adapter, and a 12V→5V power supply, inside a 3D-printed ASA enclosure with a proper NMEA 2000 Micro-C panel-mount connector.

## Target audience

European club racing sailors with existing NMEA 2000 instrument networks (Garmin, B&G, Raymarine, Airmar) who want performance data without investing in a €2,000+ professional system. These people understand sailing terminology — don't dumb it down, but don't use software engineering jargon either.

## Brand identity

- **Colors:** Deep ocean navy (#1B3A5C) primary, signal yellow (#F5C518) accent, white background, dark gray (#333333) text
- **Font:** Inter or similar clean sans-serif
- **Logo:** The word "Aquarela" in navy, clean and simple. Generate an SVG logo with a subtle wave or compass element.
- **Tone:** Confident, direct, no-nonsense. Not corporate. Not startup-y. Think "built by a racer who got fed up with expensive, unreliable gear."
- **No emojis in body copy.** Minimal icons (use Lucide or similar).

## Page structure

### 1. Hero section
- Large headline: "Every number you need. On your phone. €179."
- Subheadline: "Aquarela is a plug-and-play instrument system for racing sailors. Connect it to your NMEA 2000 network, power it up, and get a full racing dashboard on any phone. No apps, no configuration, no subscription."
- Primary CTA: "Join the Waitlist" → email capture form
- Hero image: placeholder for a phone showing the dashboard in a cockpit (use a clean mockup layout for now — I'll replace with real photos later)

### 2. How it works — 3 steps
- **Plug in** — Connect to your NMEA 2000 backbone with a standard Micro-C cable. Power from 12V.
- **Sail** — Aquarela creates a WiFi hotspot. Open any phone browser. See everything: VMG, true wind, wind rose, heading, boat speed, depth, performance %.
- **Analyze** — After sailing, download clean CSV session files. Upload directly to Njord Analytics for polars, maneuvers, and fleet comparison.

### 3. Feature grid (2×3 or 3×2)
- **13-page racing dashboard** — Upwind, downwind, wind rose, regatta, navigation, performance, polar, sensors, and more.
- **Derived data on-device** — VMG, true wind (TWA/TWS/TWD), current set/drift, target speed — computed in real-time, not just raw sensor relay.
- **Clean session logging** — Every sail is recorded to CSV. No proprietary formats, no corrupt files, no conversion headaches.
- **Njord Analytics ready** — Session files match Njord's spec exactly. Upload and get instant post-race reports.
- **Any phone, any browser** — No app to download. Works on iPhone, Android, even a tablet. Just connect to WiFi and open the browser.
- **Plug and play** — One cable to your N2K backbone, one power connection. No software to install, no configuration menus, no setup wizard.

### 4. Competitive comparison (simple, not a full table)
- "A WiFi gateway costs €220. A data logger costs €250. A phone app costs €30. That's €500 for three separate products that still can't compute VMG. Aquarela does it all for €179."
- Maybe a minimal visual showing: Gateway (€220) + Logger (€250) + App (€30) = €500 vs. Aquarela (€179)

### 5. Specs section (collapsible or small-print)
- Connections: NMEA 2000 Micro-C (standard drop cable)
- Power: 12V DC from boat battery (draws <1W)
- WiFi: 2.4GHz hotspot, 3+ simultaneous clients
- Logging: CSV to onboard storage, downloadable via WiFi
- Decoded PGNs: Wind, speed, depth, heading, position, COG/SOG, temperature, attitude, distance log
- Dimensions: ~120×80×45mm
- Enclosure: UV-resistant ASA, IP65 rated, panel-mount Micro-C connector
- Weight: ~120g

### 6. About / Origin story (brief)
- "Aquarela was born on a racing sailboat on Lake Lugano. After too many corrupted log files and unreliable WiFi gateways, we built what we actually needed: a simple box that captures everything, shows it on your phone, and gives you clean data after the race. Now we're making it available to other club racers."

### 7. Waitlist CTA (repeated)
- "Join the Waitlist" email capture
- "Be first to know when Aquarela ships. No spam — just one email when it's ready."

### 8. Footer
- © 2026 Aquarela
- Contact email link
- "Made in Switzerland" (if you want)

## Technical requirements

- **Framework:** Single HTML file with Tailwind CSS (CDN), or a minimal Next.js/Astro site if you prefer — whatever deploys cleanest to Vercel.
- **Email capture:** Use a simple Formspree or Buttondown form endpoint for the waitlist. Don't build a backend. Just POST the email to a form service.
- **Responsive:** Must look great on mobile (sailors will check this on their phones).
- **Performance:** Lighthouse score 95+. No heavy images for now — use CSS gradients, SVGs, and placeholder mockup frames where photos will go later.
- **SEO basics:** Proper meta tags, og:image (generate a simple social card), page title "Aquarela — Racing Instrument System for Sailors"
- **Deploy to Vercel.**

## Placeholder images

Since I don't have product photos yet, create attractive placeholder layouts:
- A phone frame mockup showing a sailing dashboard UI (you can create a simple SVG/CSS mockup of an instrument display with numbers like "BSP 6.2 kt", "TWA 42°", "VMG 5.1 kt")
- A minimal product box illustration (rounded rectangle representing the enclosure with a connector on one side)

## What NOT to do

- No cookie banners
- No analytics scripts
- No popup modals
- No "built with [framework]" badges
- No stock photography of sailboats — use clean geometric/abstract visuals until I have real photos
- Don't make it look like a Silicon Valley SaaS landing page. Make it look like a well-designed tool made by people who sail.
