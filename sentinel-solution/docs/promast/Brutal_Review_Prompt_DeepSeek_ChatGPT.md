# Brutal Review Prompt — for DeepSeek / ChatGPT

Use this along with the proposal document `Gujarat_Police_Innovation_Challenge_2026_Technical_Proposal.md` (paste its content below the prompt, or upload it if the platform supports file upload).

---

## Prompt

Act as a **skeptical, senior technical judge** for a competitive government hackathon — the kind of reviewer who has seen hundreds of "AI + CCTV" pitches, is tired of buzzwords, and rejects submissions that sound impressive but don't survive scrutiny. Do not be encouraging. Do not soften criticism. Your job is to find every weakness before a real jury does.

This is a proposal for the **Gujarat Police Innovation Challenge 2026** — unifying 80,000+ CCTV cameras across multiple vendors/VMS platforms, with real-time detection of suspicious people/vehicles, ANPR, and cross-camera tracking. I'm applying as an independent researcher/innovator.

Tear this proposal apart. Specifically:

1. **Call out every vague or unsubstantiated claim.** Anywhere the proposal says something will "work," "scale," or "detect" without evidence, a benchmark, or a citation — flag it as unproven.

2. **Attack the architecture.** Where does this break at scale? Where is the bottleneck no one wants to admit — bandwidth, GPU cost, latency, storage, integration friction with 80,000 legacy cameras across incompatible VMS systems? Don't let vague "edge normalization" or "adapter layer" language pass without asking how, concretely.

3. **Attack the AI claims.** Is Re-ID across non-overlapping cameras actually reliable in real Indian urban/road conditions (poor lighting, camera resolution, weather, crowd density)? What's the realistic false-positive/false-negative rate this system would actually produce, and is that acceptable for a law-enforcement tool where false accusations have real consequences?

4. **Attack the occlusion/tracking-loss section.** Is "confidence scoring" and "human in the loop" a genuine technical safeguard, or is it a hand-wave that avoids admitting the system frequently fails? Where would an operator ignore or over-trust the confidence score in practice?

5. **Attack the feasibility.** What in this proposal is realistically buildable as a hackathon PoC in the given timeframe, and what is clearly aspirational fluff meant to sound ambitious? Call out anything that reads like a roadmap slide rather than a working prototype plan.

6. **Attack the compliance/ethics framing.** Is the DPDP Act / privacy section substantive, or is it a token paragraph? What would a genuinely adversarial privacy advocate or RTI activist say about this system if deployed at scale?

7. **Attack the competitive positioning.** Assume 50 other teams are also pitching "YOLO + Re-ID + ANPR." What in this proposal is actually differentiated, versus what's just competent-but-generic computer vision plumbing that every other team will also propose?

8. **Give a blunt verdict.** If you were scoring this out of 10 against other serious submissions, what score would it get, and what are the 3 things that would most likely sink it in front of a jury?

Do not pad the response with balanced praise. I want the flaws, not a summary of strengths. Be as harsh as the technical substance actually warrants.

**[Paste or attach the proposal document here]**

---

## Notes on using this

- This prompt is deliberately adversarial — it's meant to surface weak points before a jury does, not to be a fair or balanced review. Use the earlier, more neutral review prompt separately if you also want constructive, non-adversarial feedback.
- Run it through both DeepSeek and ChatGPT independently — an adversarial framing tends to surface different blind spots depending on the model's training and tendencies.
- If you get pushback or the criticism feels unfairly harsh in places, that's expected — treat it as a stress test, not a final verdict. Weigh which criticisms are substantive versus which are just the model performing harshness because you asked for it.
