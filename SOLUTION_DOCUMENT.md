# Kuku AI Generalist Assignment — Solution Document
**Problem 1: Find the Promos (Ads)**  
**Project:** AI Promo Finder & Ranking System  
**Author:** AI Generalist Candidate  

---

## 1. Executive Summary & Problem Framing

### Why Problem 1?
Promotional video ads (20 to 60 seconds) posted on TikTok, Instagram Reels, and YouTube Shorts are the primary user acquisition engine for vertical microdrama platforms like ReelShort, DramaBox, and Kuku. Today, human video editors manually watch hours of footage to spot promotional moments. As release cadences scale to multiple new shows every week, manual selection becomes a severe bottleneck.

We framed this problem not as video generation, but as an **explainable narrative discovery, duration optimization, and multi-criteria ranking problem**. The AI system must identify exact source episodes, timestamps, hooks, cliffhangers, and narrative justifications without fabricating lines, hallucinating timestamps, or breaking story continuity.

---

## 2. System Architecture & Pipeline Design

The system is organized into modular decoupled stages:

```
[Screenplay Files (PDF/TXT)]
             │
             ▼
   [1. Ingestion & Parser] ──► Case-insensitive segmentation, timestamp validation (MM:SS.SS)
             │
             ▼
 [2. Screenplay Analyzer] ──► Gemini batch processing (5 scenes/batch), conflict & secret extraction
             │
             ▼
 [3. Promo Discovery]     ──► Single-episode & multi-episode candidate generator (20s - 60s)
             │
             ▼
 [4. Dual Evaluators]     ──► Four Hook Mistakes Framework (100 pts) & Cliffhanger Engine (100 pts)
             │
             ▼
 [5. Ranking & Ties]      ──► Weighted composite scoring with 6-level tie-breaking hierarchy
             │
             ▼
 [6. Quality Assurance]   ──► Method 1: Python rule validator | Method 2: Adversarial audit
             │
             ▼
[7. Multi-Format Export]  ──► Streamlit UI, JSON, CSV, and ReportLab Executive PDF
```

---

## 3. Core Assumptions & Boundary Conditions

Where the assignment brief was silent, we made the following documented assumptions:
1. **Duration Boundaries:** Promos must strictly measure between **20.0 and 60.0 seconds**, matching short-form video platform limits. Single-episode stretches and multi-episode combined segments must both satisfy this constraint.
2. **Hook Timing:** The opening hook must engage the viewer in the first **0 to 3 seconds**. Hooks starting with scenic establishing shots receive delay penalties.
3. **Microdrama Scene Structure:** Microdrama episodes average 1 to 2 minutes with ~2 scenes per episode (100 scenes across the 50-episode pack). Headings, timestamps, and dialogues vary in capitalization (e.g., Episode 6 uses uppercase `SCENE HEADING:`), necessitating case-insensitive regex parsing.
4. **Cross-Episode Coherence:** Multi-episode promos must share recurring characters (e.g., Juliana, Gerald, Alexander) and close episode proximity (within 1–3 episodes) to prevent jarring narrative jumps.
5. **Separation of Concerns:** Python code handles duration arithmetic, timestamp verification, deduplication, and ranking tie-breaking. Gemini provides semantic story understanding, tension extraction, and nuance evaluation.

---

## 4. Evaluation Rubrics

### A. The Four Hook Mistakes Framework (100 Points)
Every proposed promo opening is evaluated against 4 failure modes:
1. **Delay (0–25 pts):** Does it grab attention immediately? Promos opening directly on high-conflict dialogue receive 25/25; establishing scenic descriptions are penalized.
2. **Confusion (0–25 pts):** Can a cold scroller understand the relationship dynamic without prior knowledge? Dialogue explicitly mentioning betrayal, marriage, or family stakes receives top scores.
3. **Irrelevance (0–25 pts):** Does it present relatable emotional stakes (betrayal, humiliation, sacrifice) rather than dry plot mechanics?
4. **Disinterest (0–25 pts):** Does it spark curiosity gaps, sharp contrasts, or urgent unanswered questions?

### B. Cliffhanger & Suspense Evaluation (100 Points)
A shocking event is not automatically a cliffhanger. The system evaluates whether the ending creates an **urgent unresolved question** (e.g., *"Will Juliana expose Gerald's betrayal?"*), cutting cleanly on a stinging line or sound swell rather than resolving the scene.

### C. Multi-Criteria Composite Ranking Formula
$$\text{Promo Score} = 0.40 \times \text{Hook} + 0.25 \times \text{Cliffhanger} + 0.15 \times \text{Clarity} + 0.10 \times \text{Emotion} + 0.10 \times \text{Continuity}$$

**Tie-Breaking Priority:**
1. Overall Promo Score $\rightarrow$ 2. Hook Score $\rightarrow$ 3. Cliffhanger Score $\rightarrow$ 4. Story Clarity $\rightarrow$ 5. Emotional Impact $\rightarrow$ 6. Scene Continuity. True ties are preserved transparently.

---

## 5. Dual Quality Assurance: Rules vs Adversarial Audit

To guard against model overconfidence, we implemented two independent evaluation layers:

| Check Type | Method | Scope & Targets |
| :--- | :--- | :--- |
| **Method 1: Structural Integrity** | Deterministic Python Rules | Validates episode/scene existence, ensures $start < end$, verifies segment duration $\in [20, 60]$, checks scene containment, flags duplicates. |
| **Method 2: Semantic Integrity** | Adversarial Audit | Flags soft hooks ($<80$), resolved cliffhangers ($<80$), and wide cross-episode story jumps ($>3$ episodes apart). Records human review status (`PENDING`, `CONFIRMED`, `REJECTED`). |

---

## 6. Real-World Scale, Token Economics & Interview Reusability

- **Batch Scene Processing:** Scenes are batched into groups of 5 with structured JSON schemas. Rather than passing 50 full screenplays in one bloated prompt, batching keeps token context focused, eliminates truncation, and stays well within Gemini rate limits.
- **Resumability & Caching:** Completed scene analyses are serialized to `data/analyzed/episode_XXX.json`. If an API failure or network timeout occurs, execution resumes seamlessly without re-billing unchanged scenes.
- **Cost Estimate:** Analyzing a complete 50-episode show (100 scenes) consumes $\approx 120,000$ input tokens and $\approx 25,000$ output tokens. On `gemini-2.5-flash`, the total analysis cost is **under \$0.04 per 50-episode show**, making it viable for dozens of shows released weekly.
- **Model Agnostic Swapping:** The LLM client is fully abstracted behind an interface. During interviews, stronger models (e.g., `gemini-1.5-pro` or Claude/OpenAI) can be swapped via configuration without touching business logic.

---

## 7. Known Failure Modes, Disagreements & AI Limitations

1. **Visual Comedy & Physical Gags:** Dialogue-first analysis can undervalue silent slapstick or purely physical tension that lacks spoken lines.
2. **Subtle Irony & Sarcasm:** LLMs occasionally misinterpret deadpan sarcasm as genuine agreement without acoustic or video cues.
3. **Evaluator Disagreements:** On multi-episode promos spanning non-consecutive episodes (e.g., Ep 2 to Ep 7), the Discovery Engine prioritized character tension while the Quality Auditor flagged context gaps. The system logs these as explicit disagreements rather than forcing artificial consensus.
4. **Predictive Disclaimer:** AI scores represent engagement hypotheses based on screenwriting rubrics. Real-world click-through rate (CTR) and ROAS require iterative A/B testing on ad networks.

---

## 8. Top 3 Promotional Recommendations to Publish First

From **11,961 discovered candidates** across the full 50-episode input pack, the top three recommendations are:

### Rank 1: `PROMO_EP38_001600_004750`
- **Episode:** Episode 38 | **Timestamps:** 00:16.00 – 00:47.50 | **Duration:** 31.5s
- **Composite Score:** **94.60/100** (Hook: 97.0/100, Cliffhanger: 90.0/100)
- **Hook Dialogue:** `JULIANA: "Why?"` (Start: 00:16.00)
- **Cliffhanger Line:** `JULIANA: "What if I die here?"` (End: 00:47.50)
- **Unresolved Question:** Will Juliana sacrifice herself or will Alexander arrive in time to save her?
- **Why Publish First:** Combines an instantaneous curiosity hook with mortal life-or-death stakes and an unresolved cliffhanger, creating urgency for cold scrollers.

### Rank 2: `PROMO_EP38_001600_005050`
- **Episode:** Episode 38 | **Timestamps:** 00:16.00 – 00:50.50 | **Duration:** 34.5s
- **Composite Score:** **93.60/100** (Hook: 97.0/100, Cliffhanger: 90.0/100)
- **Hook Dialogue:** `JULIANA: "Why?"` (Start: 00:16.00)
- **Cliffhanger Line:** `JULIANA: "What if I never see you again?"` (End: 00:50.50)
- **Unresolved Question:** Will Juliana and Alexander's covert bond survive the impending danger?
- **Why Publish First:** Extends the scene by 3 seconds to emphasize relationship heartbreak, serving as a powerful variant for audience split-testing against Rank 1.

### Rank 3: `PROMO_EP01_011500_013820`
- **Episode:** Episode 1 | **Timestamps:** 01:15.00 – 01:38.20 | **Duration:** 23.2s
- **Composite Score:** **93.55/100** (Hook: **100.0/100**, Cliffhanger: 85.0/100)
- **Hook Dialogue:** `LADY IN GOLD GOWN: "Long enough to know he was never going to marry you."` (Start: 01:15.00)
- **Cliffhanger Line:** `LADY JULIANA: "Embarrassed you?"` (End: 01:38.20)
- **Unresolved Question:** How will Juliana retaliate against her family and fiancé after being discarded at the altar?
- **Why Publish First:** Perfect 100/100 Hook score under the Four Hook Mistakes Framework. It captures the defining inciting incident of the series with instant universal resonance and zero exposition delay.
