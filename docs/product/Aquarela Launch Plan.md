---
title: "Aquarela Communication & Launch Plan"
created: 2026-03-20
updated: 2026-03-20
type: project
status: active
domain: aquarela
tags:
  - type/project
  - domain/sailing
  - domain/business
  - project/aquarela
  - marketing
  - launch
related:
  - "[[Aquarela Product Business Plan]]"
  - "[[Aquarela Market Research.docx]]"
  - "[[Aquarela Performance System]]"
summary: "Minimal-effort launch plan for Aquarela as a brand-first product targeting European club racers. Three phases: beta seeding (spring 2026), soft launch (autumn 2026), open sales (spring 2027). Total marketing time budget: ~10-15 hours across 12 months. Core strategy: let the product generate its own content through real race data, and let the sailing community do the distribution."
---

## Summary

This plan is designed for a founder who has a few hours total to spend on marketing. That constraint is the strategy: build one great product page, place 3-4 posts where sailors already gather, and let the sailing community's word-of-mouth do the work. If Aquarela doesn't sell itself after those touchpoints, more marketing wouldn't have saved it — the product-market fit would be the problem.

## Brand Identity — Aquarela

### Positioning Statement

Aquarela is the racing data system that should have existed years ago. One box, one cable, every number you need on your phone — and clean session files when you're done.

### Brand Principles

- **No jargon.** Don't say "NMEA 2000 PGN decoder with WebSocket broadcast" — say "plug it into your instruments, see everything on your phone."
- **Show, don't tell.** Screenshots of real race data beat feature lists. A 30-second phone recording of the dashboard during a tack is worth more than a spec sheet.
- **Built by a racer.** The brand is Aquarela, not Tommaso — but the credibility comes from this being built on a real racing boat by someone who actually uses it every weekend. That story should be visible (About page) without being the headline.
- **Underdog positioning.** "We're not Sailmon. We're not B&G. We're the €179 box that does what you actually need." Price is a weapon — use it prominently.

### Visual Identity (Minimal)

- Logo: The word "Aquarela" in a clean sans-serif (Inter or similar), with a subtle wave or compass motif. Claude can generate SVG options.
- Colors: Deep ocean blue (#1B3A5C) + signal yellow (#F5C518) on white. Matches nautical aesthetics without looking like a generic marine product.
- Photography style: Phone screens showing the dashboard in real sailing conditions. Cockpit shots. Hands on tillers with phones mounted. Never studio — always on-water.

## Three-Phase Timeline

### Phase 0: Preparation (March–April 2026) — ~3 hours

**Goal:** Build the minimum assets needed before anything goes public.

Deliverables:

1. **Product landing page** (1-2 hours, Claude builds it)
   - Single page: hero image (phone showing dashboard on boat), one-line pitch, 3-4 feature blocks with screenshots, price, "Join the waitlist" email capture, About section.
   - Host on Vercel (free tier). Domain: aquarela.sailing or aquarela-sailing.com (check availability).
   - No e-commerce yet. Just email capture to measure interest.

2. **Screenshot library** (30 min, from existing dashboard)
   - Capture each dashboard page with realistic data (use vcan simulator).
   - 5-6 hero images: upwind page, wind rose, regatta view, sensors, performance gauge.

3. **One-paragraph product description** (15 min)
   - The copy that goes everywhere: landing page, forum posts, emails.
   - Draft: "Aquarela is a plug-and-play instrument system for racing sailors. Connect it to your NMEA 2000 network, power it from your boat's 12V, and get a full racing dashboard on your phone — VMG, true wind, wind rose, performance data, and more. After sailing, download clean session files for Njord Analytics. No apps to install, no configuration, no subscription. €179."

4. **"About" story** (15 min)
   - "Aquarela was born on a Nitro 80 racing on Lake Lugano. After too many corrupted log files and unreliable WiFi gateways, we built what we actually needed: a simple box that captures everything, shows it on your phone, and gives you clean data after the race. Now we're making it available to other club racers."

### Phase 1: Beta Seeding (May–September 2026) — ~3 hours

**Goal:** Get 5 units on 5 boats. Generate real-world content and testimonials.

Actions:

1. **Distribute beta units** (in person, at the dock or before races)
   - 2-3 units to fleet mates on Lake Lugano
   - 1-2 units to contacts in nearby fleets (Garda, Como) if you have them
   - Free or at cost (€85-95). Frame it as: "I need beta testers, you get to keep the unit."

2. **Collect content passively** (ongoing, zero effort)
   - Ask each tester: "Can you screenshot the dashboard during a race and send it to me?" One WhatsApp message per tester.
   - Ask one tester to film 30 seconds of the phone mounted in the cockpit during sailing. This becomes your hero video.

3. **One forum post** (30 min)
   - Post on Sailing Anarchy Forums → "DIY & Instrumentation" subforum
   - Title: "Built a €179 NMEA 2000 instrument box — looking for beta testers"
   - Content: What it does (one paragraph), 3-4 screenshots, "I built this for my own boat, now testing with a few club racers. If you're interested in trying one, DM me."
   - This post will either generate genuine interest or crickets. Both are useful information.

4. **Njord Analytics outreach** (15 min email)
   - Email the Njord team: "I've built an NMEA 2000 data logger that exports Njord-compatible CSV natively. Would you be interested in listing it as recommended hardware? Happy to send you a unit."
   - If they bite, this is your single highest-leverage partnership.

### Phase 2: Soft Launch (October–December 2026) — ~4 hours

**Goal:** Open the waitlist to paying customers. Convert beta feedback into social proof.

Timing: Off-season in Europe. Sailors are buying gear for next season. This is when purchasing decisions happen.

Actions:

1. **Update landing page with real content** (1 hour)
   - Replace simulator screenshots with real race data screenshots from beta testers.
   - Add a "Testimonials" or "On the water" section with quotes from beta testers and their boat photos.
   - Add a "Compatible instruments" section listing confirmed working setups (Garmin, Airmar, B&G — whatever the beta covered).
   - Switch "Join waitlist" to "Pre-order — €179" with payment (Stripe/Gumroad/Shopify).

2. **Three targeted forum/community posts** (1.5 hours total)
   - **Sailing Anarchy** — Update the beta thread with results. "6 months of testing, here's what we found. Now taking orders."
   - **Reddit r/sailing** — New post: "We built a €179 alternative to expensive instrument systems — AMA" with real race screenshots.
   - **Class association forums** — Pick 2-3 active one-design class forums (J/70, Melges 24, SB20, or whatever classes your beta testers sail). Post in their gear/electronics subforum.

3. **One email to the waitlist** (30 min)
   - If the landing page collected emails during Phase 1, send a single email: "Aquarela is ready. Here's what beta testers said. Order now for spring delivery."

4. **Product hunt for sailing** (30 min, optional)
   - Submit to Scuttlebutt Sailing News, Sailing World gear section, or YBW.com forums. These are long shots but free and take minutes.

### Phase 3: Open Sales (January–March 2027) — ~2 hours ongoing

**Goal:** Fulfill pre-orders, build a small but sustainable order pipeline.

Actions:

1. **Ship pre-orders** (logistics, not marketing)
   - Flash SD cards, assemble units, ship. Target: 2 weeks from order to delivery.

2. **Ongoing content** (15 min/month, optional)
   - If a customer sends a great screenshot or race result, post it. "Aquarela in action at Lake Garda Melges 24 regatta."
   - This is the only ongoing marketing effort. And it's optional — if the product is good, customers post their own screenshots.

3. **Njord co-marketing** (if partnership established)
   - Njord features Aquarela on their "Hardware" page.
   - Aquarela landing page links to Njord as the recommended analytics platform.
   - Mutual benefit, zero ongoing effort.

## Channel Strategy

### Where sailors actually are (ranked by impact per hour invested)

| Channel | Effort | Expected Impact | When |
|---------|--------|----------------|------|
| In-person at the dock | 0 (you're already there) | Highest. Sailors buy what they see working. | Beta phase |
| Sailing Anarchy forum | 30 min per post | High. Active DIY/instrumentation community. | Beta + soft launch |
| Njord Analytics partnership | 15 min email | Very high if they say yes. Distribution to their entire user base. | Beta phase |
| Reddit r/sailing | 30 min | Medium. Large audience but casual. AMA format works well. | Soft launch |
| Class association forums | 30 min per class | Medium-high within that class. Very targeted. | Soft launch |
| Instagram/social media | Hours per week | Low for this product. Sailors don't buy instruments on Instagram. | Skip. |
| Boat shows | Days + travel + booth cost | Low ROI at this scale. Maybe later. | Skip until v2. |
| YouTube product video | 2-4 hours | Medium. One good video has long shelf life. | Only if a tester films it naturally. |
| Paid advertising | $$$ | Very low. Niche audience, expensive CPM. | Never at this scale. |

### Channels explicitly NOT worth the time

- **Instagram/TikTok/Twitter** — The effort-to-conversion ratio for a €179 niche hardware product on social media is terrible. Skip entirely.
- **Paid ads (Google, Facebook)** — The audience is too niche and too small. You'd spend more on ads than you'd make in revenue.
- **Boat shows** — A booth at Boot Düsseldorf costs €5,000+. Not justified for 5-50 units.
- **Press releases** — No one reads marine electronics press releases. A forum post reaches more actual buyers.

## Content Assets Needed (Total)

| Asset | Who Creates | Time | Priority |
|-------|------------|------|----------|
| Landing page | Claude (code) + you (screenshots) | 1-2 hours | Critical |
| Product one-paragraph description | Claude (draft) + you (review) | 15 min | Critical |
| Dashboard screenshot library (6-8 images) | You (from simulator or boat) | 30 min | Critical |
| Brand logo (SVG) | Claude (generative) | 15 min | Nice to have |
| Sailing Anarchy beta post | Claude (draft) + you (post) | 30 min | High |
| Njord partnership email | Claude (draft) + you (send) | 15 min | High |
| Beta tester one-pager (what to test, how to report issues) | Claude | 15 min | Medium |
| Pre-order page (Stripe/Gumroad) | Claude (setup) | 30 min | Phase 2 |
| 3 forum posts for soft launch | Claude (drafts) + you (post) | 1 hour | Phase 2 |
| Waitlist email | Claude (draft) + you (send) | 15 min | Phase 2 |

**Total time investment across 12 months: ~12-15 hours.**

## Pricing Communication

The price is the headline. In every piece of communication, lead with or prominently feature €179. The competitive framing:

- "Everything a €270 Actisense W2K-1 does, plus a full racing dashboard, for €179."
- "A WiFi gateway costs €220. A data logger costs €250. Aquarela does both — plus VMG, true wind, and session export — for €179."
- "The racing data system for boats that don't have a €2,000 budget."

Don't apologize for being cheap. Don't position as "budget." Position as "smart." The implicit message: the expensive products are overpriced, not that Aquarela is low-quality.

## Success Metrics

These are deliberately modest — calibrated to a first product by a solo founder:

| Metric | Beta Phase | Soft Launch | Open Sales |
|--------|-----------|-------------|------------|
| Units deployed | 5 | 5 (same) | 15-30 |
| Waitlist signups | — | 20-50 | — |
| Pre-orders | — | 5-15 | 10-20 |
| Forum thread views | 500+ | 2,000+ | — |
| Njord partnership | Outreach sent | Response received | Listed or not |
| Customer-generated content | 2-3 screenshots | 5+ screenshots | Organic posts |

**The kill criterion:** If after the Sailing Anarchy beta post and 3 months of 5 units on the water, fewer than 5 people have expressed concrete buying interest (not "cool project" — actual "how do I order one?"), then demand is insufficient at this price point. Pivot, reprice, or shelve.

## What Claude Handles

Claude can prepare all written content — forum posts, the landing page, the Njord email, product descriptions, the beta tester one-pager. You review and post/send. This is how "a few hours total" becomes a credible launch:

- Claude drafts → You review (5 min) → You post/send (2 min)
- Claude builds landing page → You provide screenshots → Claude deploys on Vercel
- Claude monitors forum responses (if you paste them) and drafts replies

The bottleneck is never the content creation. It's you taking the screenshots, talking to testers at the dock, and clicking "send."

## Decisions Still Open

- [ ] Domain name — check availability of aquarela.sailing, aquarela-sailing.com, getaquarela.com
- [ ] Payment processor — Stripe (most flexible), Gumroad (simplest), Shopify (most features)
- [ ] Shipping — ship from Switzerland or use a fulfillment service?
- [ ] Returns policy — what if a unit doesn't work with someone's instrument setup?
- [ ] Warranty — what do you commit to for a €179 product?
