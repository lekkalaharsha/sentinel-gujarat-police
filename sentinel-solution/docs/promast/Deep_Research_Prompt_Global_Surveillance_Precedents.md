# Deep Research Prompt — for DeepSeek / ChatGPT

Use this to research how other countries, police forces, defense agencies, and companies have solved similar problems — multi-camera surveillance integration, AI-based tracking, ANPR, and cross-vendor interoperability — so the Gujarat Police proposal can be grounded in real precedent rather than first-principles guessing.

If your platform has a "Deep Research" mode (ChatGPT's Deep Research, or DeepSeek's equivalent), enable it before running this prompt — it will search multiple sources and produce a longer, cited report instead of a single-pass answer.

---

## Prompt

I'm building a technical proposal for a government hackathon (Gujarat Police Innovation Challenge 2026, India) focused on **unifying 80,000+ CCTV cameras across multiple vendors/departments into one AI-powered surveillance network**, with real-time detection of suspicious people/vehicles, ANPR, and cross-camera tracking.

I need deep, well-sourced research — not general knowledge — on how this problem has actually been solved elsewhere. Please research and report on the following, citing real sources (company documentation, government reports, academic papers, procurement records, news investigations) wherever possible:

### 1. National/city-scale surveillance integration projects
Research how other countries and cities have unified large, multi-vendor CCTV networks into a single platform. Include, at minimum:
- **China** — Skynet / Sharp Eyes programs (technical architecture, scale, known limitations)
- **UK** — city-wide CCTV networks (e.g., London), ANPR national network (Police National Computer / ANPR camera network), how legacy multi-vendor integration was handled
- **Singapore** — Smart Nation surveillance infrastructure
- **United States** — city-level real-time crime centers (e.g., NYC Domain Awareness System, Chicago's camera network), and any known multi-vendor interoperability approaches
- **South Korea, UAE, or other relevant deployments** if you find strong documented examples

For each, extract: **what interoperability approach they used** (standardized protocol vs. central re-encoding vs. federated search), **scale achieved**, and **publicly documented failure points or criticisms** (false positives, cost overruns, privacy backlash, technical limitations).

### 2. Companies building this technology
Identify the leading commercial/vendor platforms in this space and summarize their technical approach:
- Hikvision / Dahua (VMS + AI analytics stack)
- Milestone Systems (XProtect — known for being a vendor-agnostic VMS integration layer)
- Genetec (Security Center — multi-vendor unification platform)
- BriefCam, Avigilon (AI video analytics/search specifically)
- Any Indian companies already working with Indian police forces (e.g., Staqu, Vehant, NEC India, Innefu Labs) — these are especially relevant since they may already understand Indian deployment constraints
For each: what's their core technical differentiator, and what do they claim solves the "multi-vendor interoperability" problem specifically?

### 3. Defense/military approaches to multi-sensor fusion and tracking-through-occlusion
Police CCTV tracking is a simpler version of a problem defense/ISR (intelligence, surveillance, reconnaissance) systems have worked on for longer — multi-sensor track fusion, re-acquisition after track loss, and probabilistic target handoff. Research:
- Military/defense literature on **multi-target tracking (MTT) and sensor fusion** (e.g., Kalman/particle filter-based track fusion across multiple non-overlapping sensors)
- How defense systems handle **track loss and re-acquisition** (the equivalent of our "vehicle disappears between cameras" problem) — what probabilistic/predictive methods are used
- Whether any of these techniques have documented civilian/policing adaptations

### 4. Academic research papers
Find and summarize (with citations/links) recent peer-reviewed or arXiv papers on:
- **Person/vehicle re-identification across non-overlapping cameras** (multi-camera Re-ID) — recent SOTA methods and their reported accuracy/limitations
- **Multi-camera multi-target tracking (MC-MTT)** benchmarks and open datasets (e.g., MOT Challenge, CityFlow, VeRi-776, MSMT17)
- **ANPR in non-Western/non-standardized plate environments** (papers dealing with Indian, or similarly diverse, plate formats/scripts)
- **Federated or interoperable VMS architectures** — any papers specifically addressing the "different vendors, different systems" integration problem, not just the AI model side
- Papers or reports discussing **false positive rates and real-world reliability** of surveillance AI systems when deployed at city/state scale (important for the proposal's credibility)

### 5. Documented failures and criticisms
This is important — I don't just want success stories. Research known **failures, controversies, or technical limitations** of large-scale AI surveillance deployments (e.g., accuracy problems in poor lighting/weather, bias/error rates in facial recognition across demographics, cost overruns, vendor lock-in problems, privacy/legal challenges). I want to know what NOT to repeat.

### 6. Synthesis
After researching, give me:
- A **comparison table** of the 3–4 most relevant precedents (by architecture approach, scale, and outcome)
- The **top 5 technical lessons** most applicable to a state-level Indian police CCTV integration project
- The **top 3 known failure modes** I should explicitly address in my proposal to preempt jury skepticism
- A **short list of the strongest research papers** (with links) I should cite directly in my technical proposal for credibility

Prioritize recent sources (last 5 years) where possible, but include foundational/classic papers or systems where they're still the reference standard. Be explicit about source quality — flag anything based on marketing material versus independently verified/academic sources.

---

## Notes on using this

- Run separately on DeepSeek and ChatGPT (with Deep Research mode if available) — they'll likely surface different sources given different training data and search capabilities.
- If either tool times out or truncates on a prompt this broad, split it into 2–3 smaller runs (e.g., Sections 1–2 together, Section 3–4 together, Section 5–6 together) rather than dropping detail.
- Save direct paper links and citations as you go — these are what will actually strengthen the proposal's Section on precedent/differentiation and give it credibility in front of a technical jury.
