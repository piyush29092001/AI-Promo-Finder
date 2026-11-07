# Kuku AI Generalist Assignment — Solution Document
**Problem 1: Find the Promos (Ads)**  
**Project:** AI Promo Finder & Ranking System  
**Author:** AI Generalist Candidate  

---

## 1. Executive Summary & Problem Framing

Short-form promotional video ads (20 to 60 seconds) across TikTok, Instagram Reels, and YouTube Shorts drive user acquisition for vertical microdrama platforms like Kuku, ReelShort, and DramaBox. Manual human scanning of hours of footage is unsustainable as production scales to multiple 50-episode shows weekly.

We framed this challenge not as synthetic video generation, but as an **explainable narrative discovery, duration optimization, and multi-criteria ranking problem**. The system processes authentic screenplay text to identify precise source episodes, scenes, timestamps, opening hooks, and closing cliffhangers—delivering actionable edit decision lists (EDLs) with zero hallucinated lines or timestamps.

---

## 2. System Architecture & Discovery Pipeline

The application is architected into 7 decoupled modules:

```
[50 Screenplays (PDF/TXT)]
            │
            ▼
  [1. Screenplay Parser]     ──► Case-insensitive regex, timestamp validation (MM:SS.SS), 100 scenes extracted
            │
            ▼
  [2. Screenplay Analyzer]   ──► Gemini 2.5 Flash batch analysis (5 scenes/batch), dramatic conflict extraction
            │
            ▼
  [3. Promo Discovery]       ──► Sliding-window & multi-episode segment generator (20s - 60s bounds)
            │
            ▼
  [4. Dual Evaluators]       ──► Four Hook Mistakes Framework (100 pts) & Segment Cliffhanger Engine (100 pts)
            │
            ▼
  [5. Ranking & Clustering]  ──► 5-factor weighted scoring, diversity clustering, 6-tier tie-breaking
            │
            ▼
  [6. Quality Assurance]     ──► Method 1: Strict rule validation | Method 2: Adversarial audit & review
            │
            ▼
  [7. Multi-Format Exporter] ──► Interactive Streamlit UI, structured JSON, CSV, and ReportLab PDF
```

---

## 3. Core Assumptions & Boundary Conditions

Where the assignment brief was silent, we adopted verified industry standards:
1. **Duration Boundaries:** All promos must strictly measure between **20.0 and 60.0 seconds**, matching short-form social video limits. Single-episode cuts and multi-episode combinations both enforce this constraint.
2. **Hook Timing:** The opening hook must deliver dramatic friction within the first **0 to 3 seconds**. Establishing shots without dialogue incur delay penalties.
3. **Screenplay Variations:** Across the 50 episodes, screenplay formatting varies (e.g., uppercase `SCENE HEADING:` in Episode 6 vs standard casing). Parser uses case-insensitive regex without hardcoded scene counts.
4. **Multi-Episode Coherence:** Combined segments require character continuity (e.g., Juliana, Gerald, Alexander) and close episode proximity (within 1–3 episodes) to prevent jarring narrative jumps.
5. **Separation of Concerns:** Python handles arithmetic, timestamp verification, deduplication, and diversity clustering; Gemini provides semantic tension extraction and narrative evaluation.

---

## 4. Evaluation Rubrics & Ranking Formulation

### A. The Four Hook Mistakes Framework (100 Points)
Every candidate's opening dialogue is evaluated against 4 failure modes (0–25 points each):
1. **Delay (0–25):** Does it grab attention instantly? High-conflict dialogue earns 25/25; scenic scene setups are penalized.
2. **Confusion (0–25):** Can a cold scroller immediately grasp character dynamic and stakes without prior context?
3. **Irrelevance (0–25):** Does it present relatable emotional stakes (betrayal, humiliation, forced marriage) rather than dry exposition?
4. **Disinterest (0–25):** Does it spark an immediate curiosity gap or urgent unanswered question?

### B. Segment-Level Cliffhanger Evaluation (100 Points)
A cliffhanger must cut cleanly on an **urgent unresolved question** (e.g., *"What if I die here?"*), penalizing resolved endings or flat closures.

### C. Multi-Criteria Composite Ranking Formula
$$\text{Promo Score} = 0.40 \times \text{Hook} + 0.25 \times \text{Cliffhanger} + 0.15 \times \text{Clarity} + 0.10 \times \text{Emotion} + 0.10 \times \text{Continuity}$$

**Tie-Breaking Hierarchy:** 1. Overall Score $\rightarrow$ 2. Hook Score $\rightarrow$ 3. Cliffhanger Score $\rightarrow$ 4. Story Clarity $\rightarrow$ 5. Emotional Impact $\rightarrow$ 6. Scene Continuity.

### D. Diversity Clustering
With 11,961 candidates discovered, adjacent cuts differ by fractions of a second. The system groups candidates by shared hook dialogue and scene into **5,127 distinct narrative clusters**, selecting the single highest-scoring variant as the **Cluster Primary** for editorial recommendations while preserving all variants in raw exports for creative A/B testing.

---

## 5. Dual Quality Assurance: Rules vs Adversarial Audit

| Verification Layer | Method | Scope & Targets | Full Pack Result |
| :--- | :--- | :--- | :--- |
| **Method 1: Structural Integrity** | Deterministic Python Rules | Validates episode/scene existence, timestamp ordering ($start < end$), duration $\in [20s, 60s]$, scene containment, and unique promo IDs. | **0 Violations** across 11,961 candidates |
| **Method 2: Semantic Integrity** | Adversarial Audit | Flags soft hooks ($<80$), resolved cliffhangers ($<80$), cross-episode character mismatches, and records human review statuses. | **0 Structural Flags** on Top Recommendations |

---

## 6. Corrected Top 3 Promotional Recommendations to Publish First

From **11,961 discovered candidates** across 50 episodes, the top 3 recommendations represent distinct episodes, scenes, and dramatic concepts:

### Recommendation #1: `PROMO_EP38_SC01_001600_004750_315`
- **Episode:** Episode 38 (Dungeon Cell) | **Timestamps:** 00:16.00 – 00:47.50 | **Duration:** 31.5s
- **Composite Score:** **94.60/100** (Hook: 97.0, Cliffhanger: 90.0, Clarity: 90.0, Emotion: 100.0, Continuity: 98.0)
- **Opening Hook:** `JULIANA: "Why?"` [00:16.00 – 00:20.00] (Delay: 25/25, Confusion: 25/25, Irrelevance: 22/25, Disinterest: 25/25)
- **Closing Cliffhanger:** `JULIANA: "What if I die here?"` [00:42.50 – 00:47.50]
- **Unresolved Question:** *"Will JULIANA's urgent question be answered: 'What if I die here?'?"*
- **Why Publish First:** Delivers instantaneous curiosity, life-or-death stakes, and an urgent mortal question. Primary cut selected from 16 cluster duration variants (`EP38_EP38_SCENE_01_T4`).

### Recommendation #2: `PROMO_EP01_SC01_011500_013820_232`
- **Episode:** Episode 1 (Grand Cathedral) | **Timestamps:** 01:15.00 – 01:38.20 | **Duration:** 23.2s
- **Composite Score:** **93.55/100** (Hook: **100.0/100**, Cliffhanger: 85.0, Clarity: 90.0, Emotion: 90.0, Continuity: 98.0)
- **Opening Hook:** `LADY IN GOLD GOWN: "Long enough to know he was never going to marry you."` [01:15.00 – 01:19.00]
- **Closing Cliffhanger:** `LADY JULIANA: "Embarrassed you?"` [01:33.20 – 01:38.20]
- **Unresolved Question:** *"Will LADY JULIANA's urgent question be answered: 'Embarrassed you?'?"*
- **Why Publish First:** Flawless 100/100 Hook score under Four Hook Mistakes Framework. Immediately establishes the central wedding betrayal without backstory delay. Primary cut selected from 33 cluster variants (`EP01_EP01_SCENE_01_T18`).

### Recommendation #3: `PROMO_EP32_SC01_015690_022810_312`
- **Episode:** Episode 32 (Manor Drawing Room) | **Timestamps:** 01:56.90 – 02:28.10 | **Duration:** 31.2s
- **Composite Score:** **93.55/100** (Hook: **100.0/100**, Cliffhanger: 85.0, Clarity: 90.0, Emotion: 90.0, Continuity: 98.0)
- **Opening Hook:** `JULIANA: "...but you have never learned how to make anyone love you."` [01:56.90 – 02:00.90]
- **Closing Cliffhanger:** `CATHERINE: "You think you can lecture me?!"` [02:23.10 – 02:28.10]
- **Unresolved Question:** *"Will CATHERINE's urgent question be answered: 'You think you can lecture me?!'?"*
- **Why Publish First:** High-tension confrontation with a predatory matriarch; cuts cleanly at the emotional peak of defiance. Primary cut selected from 15 cluster variants (`EP32_EP32_SCENE_01_T29`).

---

## 7. AI Tool Usage, Verification Findings & Genuine Limitations

### AI Tool Implementation
- **Google Gen AI Python SDK (`google-genai`):** Model `gemini-2.5-flash` analyzes 5-scene batches with structured JSON schemas, extracting conflicts, betrayals, secrets, and suspense levels. Scene analyses are cached locally to ensure idempotency and zero duplicate API charges.
- **Offline Heuristic Engine:** Serves as a resilient fallback when running without an API key, extracting dialogue hooks and cliffhanger questions deterministically.

### Verification Finding: The Segment-Level Question Inheritance Defect
During independent verification of the initial 11,961 candidates, we audited promo cuts against original screenplay dialogue and discovered a **critical discrepancy**:
- **Defect:** Candidate promos cutting at mid-scene timestamps (e.g., 00:47.50) were blindly inheriting the *full scene's final cliffhanger question* (occurring at 01:20.00). This caused candidates to claim suspense regarding lines not present in the proposed cut.
- **Root Cause:** The discovery engine mapped scene-level analysis objects directly to sub-scene segment cuts.
- **Correction:** Implemented `_derive_segment_unresolved_question()`, dynamically analyzing the candidate's actual terminal dialogue line and timestamp. Terminal lines without suspense are penalized as `"Weak / Resolved ending"`.
- **Near-Duplicate Suppression:** Introduced diversity clustering (`cluster_id`, `is_cluster_primary`) so that minor duration variations (e.g., 31.5s vs 34.5s) are grouped together, ensuring top recommendations showcase genuinely diverse narrative concepts.
- **Unique ID Collision Fix:** Appended scene numbers and tenth-of-a-second durations to `promo_id`, resolving 126 ID collisions and ensuring 100% unique IDs across all 11,961 records.

---

## 8. Real-World Economics & Enterprise Reusability

- **Cost Efficiency:** Analyzing 50 episodes (100 scenes) consumes $\approx 120,000$ input tokens and $\approx 25,000$ output tokens on `gemini-2.5-flash`, totaling **under \$0.04 per 50-episode show**.
- **Model Agnostic Abstraction:** The LLM client is fully abstracted; switching to `gemini-1.5-pro` or Claude requires only updating the configuration parameter.
- **Predictive Scope:** AI scores quantify narrative and structural adherence to proven screenwriting principles. Final CTR and ROAS require iterative live A/B testing on ad networks using the provided cluster variants.
