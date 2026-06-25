# SARTHI — Round 1 PPT · Slide-by-Slide Copy

> **Use:** Each slide has a title, on-slide text, speaker note, and visual hint. Copy titles/bullets directly into your deck.
> **Deck length target:** 10 slides · ~5-minute pitch · 20–60s per slide.
> **Visual system (consistent across all slides):** deep indigo primary · saffron accent · Inter/Manrope font · one illustration style for Priya throughout · ≤6-word title · ≤3 bullets per slide.

---

## SLIDE 1 — COVER

**Title:** `SARTHI`

**On-slide:**
- Tagline: *Your AI Sarthi — from dream to degree.*
- Round 1 · Problem Statement 2
- CRP TenzorX 2026 · Poonawalla Fincorp National AI Hackathon
- Team: [Your Name] · AI-augmented build

**Speaker note (15s):** "We're SARTHI — an agentic AI platform that guides Tier-2/3 Indian students from the first dream of studying abroad all the way to loan disbursement. In their language. With memory. Zero human intervention."

**Visual hint:** Large `सारथी` Devanagari watermark (low opacity) · SARTHI wordmark centered · deep indigo background · saffron accent line.

---

## SLIDE 2 — THE PROBLEM

**Title:** `Meet Priya. India Has 10 Million Priyas.`

**On-slide (left column — Priya profile):**
- Priya Sharma, 21
- Final-year Mech Eng, VNIT Nagpur · CGPA 7.8
- Dreams: MS Robotics, US/Canada · ₹40–60L budget
- First-in-family abroad

**On-slide (right column — 7-icon pains grid, 2 cols × 4 rows):**
- 🤯 *Which test? IELTS, GRE, TOEFL?*
- 🧭 *500 US unis — which 10 fit me?*
- 😰 *Will I get in? Worth ₹50L?*
- 🏠 *Family can't guide me.*
- 🗣️ *Thinks in Marathi. Internet in English.*
- 🏦 *Messy papers — any NBFC say yes?*
- 💸 *Counselors ₹1L — push their favorites.*

**Speaker note (45s):** "Priya isn't one student — she represents 10 million Indian students every year who face a broken study-abroad journey. These are the 7 pains no platform solves together today."

**Visual hint:** Priya's illustrated portrait left-half · 7-icon grid right-half · icons in saffron on indigo cards.

---

## SLIDE 3 — OUR INSIGHT

**Title:** `Relationship > Transaction.`

**On-slide (two-timeline split):**
- **Today's NBFC:** shows up on Day-330, fights a commodity price war on loan rates.
- **SARTHI:** shows up on Day-1, becomes the 12-month AI mentor, the loan is the natural outcome.
- **The reframe:** *We don't sell loans. We build 12-month relationships that end in loans.*

**Speaker note (30s):** "Every NBFC is fighting for the last 30 days of a student's 12-month journey. SARTHI shows up on Day 1. We become the mentor. The loan becomes the natural outcome, not a price war."

**Visual hint:** Horizontal split timeline — top bar gray/muted (old world, loan icon only at the end) · bottom bar vibrant indigo with SARTHI agent avatar walking alongside Priya from Day 1 to loan disbursement.

---

## SLIDE 4 — MEET SARTHI

**Title:** `Not a Chatbot. An Agent.`

**On-slide (top):**
- **SARTHI** (सारथी) — *the charioteer*
- *Your AI Sarthi — from dream to degree.*
- One-liner: *Agentic AI platform guiding Tier-2/3 Indian students end-to-end — in their language, with memory, with action.*

**On-slide (3×3 competitive matrix):**

| Category | Who | Their Gap | SARTHI's Answer |
|---|---|---|---|
| **Counselors** | Leverage Edu · Yocket · Shiksha | ₹50k–₹2L · biased · English-only | Free · consistent AI · vernacular · unbiased |
| **Loan NBFCs** | Credila · Avanse · Auxilo · Prodigy | Arrive too late · commodity price war | 12-month pre-loan relationship · propensity data |
| **Generic AI** | ChatGPT · Gemini · other LLMs | No memory · no action · no India · no loan | Memory · tools · Bharat · loan-native |

**Tag line below matrix:** *"Counselors charge too much. Loan NBFCs show up too late. Generic AI doesn't know India. SARTHI solves all three."*

**Speaker note (45s):** "SARTHI sits at the intersection of three broken categories. Counselors overcharge and bias students. Loan NBFCs arrive too late and commoditize. Generic AI has no memory, no India context, no loan funnel. SARTHI is the only agent that covers all three gaps."

**Visual hint:** Product name + tagline top-left · clean 3×3 table dominating 70% of slide · closing tag line at bottom.

---

## SLIDE 5 — THE HERO SLIDE (THE MONEY SLIDE)

**Title:** `Priya's Journey. 7 Features. One Agent.`

**On-slide (5 horizontal phase cards left-to-right, arrows between):**

| Phase 1 · DISCOVER | Phase 2 · DECIDE | Phase 3 · APPLY | Phase 4 · FUND | AMPLIFY ↻ |
|---|---|---|---|---|
| IG reel → voice chat in Hinglish → agent builds profile + personalized timeline (IELTS→GRE→Apps→Visa) | Shortlist 10 universities · admission probability · per-uni ROI (cost vs salary vs EMI) | Socratic SOP Co-Pilot references her actual Bajaj internship — because it remembers | *"You qualify for ₹45L at 10.2%."* Auto-fills 90% of loan app from past conversations | Shareable "Study Abroad Passport" → posted on IG → 3 friends enter the funnel |
| `F1` | `F2 + F3` | `F4` | `F5 + F6` | `F7` |

**Big banner below:** ***"4 phases. One agent. Zero human intervention. One ₹45L loan disbursed."***

**Speaker note (60s):** "This is the heart of the pitch. Four phases — Discover, Decide, Apply, Fund — each one powered by AI features, each one seamlessly handing off to the next. The loop closes when Priya shares her Study Abroad Passport and three friends join. This is what zero human intervention actually looks like."

**Visual hint:** 5 horizontal connected cards with arrows between · Priya avatar progresses left-to-right · Amplify card has a curved arrow looping back to Phase 1 (closing the loop visually) · each card a different shade of indigo.

---

## SLIDE 6 — AI ARCHITECTURE

**Title:** `AI Architecture — Agent, Not Chatbot.`

**On-slide (layered diagram, top-to-bottom):**

```
Frontend (Next.js · shadcn/ui · Tailwind · PWA)
       ↓
Agent Orchestrator — LLM-agnostic · memory · tool-calling · multi-model fallback
       ↓ ↓ ↓ ↓ ↓
[University Shortlister] [ROI Predictor] [SOP Co-Pilot] [Loan Eligibility + Offer] [Passport Generator]
       ↓
Data & Integration Layer — Vector DB · Postgres · Whisper + Bhashini · Poonawalla Loan API
```

**Side callout box — "Chatbot vs. SARTHI":**
| Chatbot | SARTHI Agent |
|---|---|
| Stateless | Memory per user |
| Answers | Takes actions |
| English-only | Vernacular voice |

**Footer strip:** *Consent-first · DPDP-compliant · RBI digital-lending-aligned · Explainable by default.*

**Speaker note (45s):** "We built SARTHI as a true agent. It remembers every conversation. It calls specific tools — ML shortlister, ROI calculator, SOP co-pilot, loan offer engine. It's LLM-agnostic so we can optimize for cost and latency. And we've engineered DPDP and RBI compliance from day one — not as an afterthought."

**Visual hint:** Clean 4-tier architecture diagram center-stage · small 2×3 "chatbot vs SARTHI" comparison in top-right corner · compliance strip as a saffron footer bar.

---

## SLIDE 7 — THE ZERO-HUMAN-INTERVENTION GROWTH LOOP

**Title:** `The AI Growth Loop (Bonus Challenge).`

**On-slide (circular diagram, 5 nodes):**

```
        ACQUIRE
       ↗        ↘
   AMPLIFY    ENGAGE
      ↑          ↓
    CONVERT ← NURTURE
```

**Per-node labels:**
- **Acquire** — AI-generated IG reels + SEO blogs (1/day/city × course)
- **Engage** — Free shortlister/ROI hook · profile built in 5 minutes
- **Nurture** — Proactive WhatsApp nudges · streaks · milestones
- **Convert** — Personalized loan offer · auto-filled application
- **Amplify** — Study Abroad Passport → 3 friends join → loop closes

**Callout:** *"Target K-factor of 1.5 — every 2 converted students bring 3 friends into the top of the funnel."*

**Speaker note (30s):** "This is exactly the bonus challenge — an AI growth loop where acquisition, engagement, nurturing, conversion, and amplification all happen with zero human intervention. Every Priya who gets a loan brings three friends into the funnel. Our acquisition cost approaches zero over time."

**Visual hint:** Big circular loop diagram dominating slide · 5 node circles with icons · "3 friend avatars" sprouting from Amplify node · subtle animation hint arrow from Amplify back to Acquire.

---

## SLIDE 8 — BUSINESS IMPACT

**Title:** `From ₹5,000 CAC to a 30-Year Relationship.`

**On-slide (killer quote, top):**
> ***"SARTHI converts a ₹5,000 CAC into a ₹500 CAC · a one-time loan into a 30-year relationship."***

**On-slide (4 revenue streams, 2×2 tiles):**

| 1. Loan Origination (Primary) | 2. University Lead-Gen |
|---|---|
| Revenue share on every Poonawalla-disbursed loan · ~1–2% of loan value | Universities pay per qualified applicant · ₹500–₹2,000 per lead |

| 3. Premium Student Tier | 4. White-label Agent (Phase 2) |
|---|---|
| Power-user subscription · ₹299–₹499 / mo · unlimited SOPs · mock-interview coach | License agent to other NBFCs / BFSI after Poonawalla exclusivity period |

**Footer:** *Go-to-market: Launch exclusively with Poonawalla Fincorp · 24-month exclusivity · Multi-lender expansion in Phase 2.*

**Speaker note (45s):** "SARTHI isn't a loan origination tool — it's a platform with four revenue streams and a 30-year customer LTV. Loan rev-share is primary, but lead-gen fees, premium subscriptions, and Phase 2 white-label multiply our upside. Poonawalla is our launch partner, not our product."

**Visual hint:** Big quote at top (60% width) · 2×2 revenue tiles below · GTM line as footer strip · CAC/LTV visualized as before/after bar chart on the right.

---

## SLIDE 9 — ROADMAP & PROTOTYPE

**Title:** `Prototype May 3. Scale-ready by Month 12.`

**On-slide (3-column timeline):**

**Column 1 — The 14-Day Build (Apr 19 → May 3):**
- W1: Agent core + memory · Shortlister · ROI Predictor
- W2: SOP Co-Pilot · Loan Offer · Auto-fill · Passport · Voice
- Deploy: Vercel + GitHub · scripted Priya demo

**Column 2 — Phase 2 (6 months):**
- Domestic PG market (CAT/GATE · IIMs · NITs · private MBAs)
- 5 additional Indian languages (Tamil, Telugu, Marathi, Bengali, Kannada)
- Real university data partnerships

**Column 3 — Phase 3 (12 months):**
- White-label agent licensed to other NBFCs / BFSI
- International corridors: Nepal · Bangladesh · Sri Lanka → abroad
- Cross-sell pipeline: personal loan · home loan

**Speaker note (30s):** "A working prototype with scripted Priya flow lands on GitHub by May 3. Phase 1 launches with study-abroad only. By month 12, we're white-labeling the agent to the entire Indian BFSI sector and expanding to South Asian corridors."

**Visual hint:** 3-column timeline · each column with a heading, 3 bullets, and a small icon · progressive color deepening left-to-right (light indigo → deep indigo).

---

## SLIDE 10 — CLOSING

**Title:** `Every Student Deserves a Sarthi.`

**On-slide (centered layout):**
- Large quote: ***"Every student deserves a Sarthi."***
- Below: *Your AI Sarthi — from dream to degree.*
- **Team:** [Your Name] · Human product owner + Claude-powered AI co-developer (*our build process is itself a proof of 'zero-human-intervention' feasibility*)
- **Contact:** [Your email] · [GitHub handle] · [LinkedIn]
- **QR code:** to SARTHI prototype on Vercel (live by May 3)

**Speaker note (20s):** "SARTHI isn't just another hackathon submission. It's the mentor 10 million Indian students have been waiting for. Thank you."

**Visual hint:** Giant low-opacity `सारथी` Devanagari watermark in background · centered quote and tagline · team + contact strip at bottom · QR code in bottom-right corner · clean, emotional, memorable.

---

# Pitch Delivery Cheat-Sheet

**Total time target:** 4:30–5:00 min
**Slide timing:**
- Slides 1, 3, 10 → 15–30s (short)
- Slides 2, 6, 7, 9 → 30–45s (medium)
- Slides 4, 8 → 45–60s (denser)
- Slide 5 (HERO) → 60s (the money slide — don't rush)

**Three lines to memorize and deliver verbatim:**
1. *"Not a chatbot. An agent."* (Slide 4)
2. *"4 phases. One agent. Zero human intervention. One ₹45L loan disbursed."* (Slide 5)
3. *"SARTHI converts a ₹5,000 CAC into a ₹500 CAC — a one-time loan into a 30-year relationship."* (Slide 8)

**If judges ask you one tough question, prep answers for these:**
- *"What about domestic students?"* → Phase 2 roadmap; same agent, different rulebook.
- *"How does your SOP tool avoid university AI-detection?"* → It's a Socratic co-pilot, not a generator; the student writes, we guide.
- *"Why not just use ChatGPT?"* → No memory, no tools, no India context, no loan funnel. Comparison on Slide 4.
- *"How will you comply with DPDP / RBI?"* → Consent-first, explainable, loan decisions remain with the NBFC. Compliance strip on Slide 6.
- *"Is your CAC of ₹800 realistic?"* → Target with viral K-factor of 1.5; benchmark against education-tech referral norms.

---

*Generated from locked design on 2026-04-19. Ready to drop into deck.*
