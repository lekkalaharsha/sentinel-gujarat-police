# Review Prompt — for DeepSeek / ChatGPT

Use this prompt along with the attached proposal document `Gujarat_Police_Innovation_Challenge_2026_Technical_Proposal.md` (paste its content below the prompt, or upload it if the platform supports file upload).

---

## Prompt

I'm submitting the attached technical proposal to the **Gujarat Police Innovation Challenge 2026** — a government hackathon focused on AI-powered CCTV integration across 80,000+ cameras from different vendors, for real-time detection of suspicious people/vehicles, ANPR, and unified surveillance search. I'm applying as an independent researcher/innovator in the student/small-innovator track.

Please review this proposal critically and give me detailed feedback on:

1. **Technical soundness** — Are the proposed models and architecture (YOLOv8/RT-DETR for detection, OSNet-based Re-ID, PaddleOCR/CRNN for ANPR, ByteTrack/DeepSORT for tracking, SlowFast for anomaly detection) appropriate and current for this use case? Are there better/more recent alternatives I should consider?

2. **Feasibility gaps** — What parts of this proposal would be difficult or unrealistic to actually build within a hackathon PoC timeframe? Be specific about what to cut or simplify for Stage 1.

3. **Scalability concerns** — Does this architecture realistically scale to 80,000 cameras across multiple government departments and vendors? What would break first?

4. **Weaknesses in the occlusion/tracking-loss handling section** — Is the reasoning about Re-ID matching, travel-time plausibility, and confidence scoring technically sound? Are there failure modes or edge cases I haven't addressed?

5. **Compliance and ethics** — Are there privacy, DPDP Act 2023, or law-enforcement-specific concerns (e.g., false positive risk, misuse potential, human-in-the-loop safeguards) that a police/technical jury would likely probe, that I haven't covered?

6. **Competitive differentiation** — Given this is a hackathon judged against other submissions, what would make this proposal stand out versus a generic "we'll use YOLO + face recognition" pitch?

7. **Missing sections** — What would a strong jury-facing submission include that this draft is missing (e.g., cost estimates, deployment timeline, risk register, evaluation metrics)?

Please be direct and critical rather than just validating — I'd rather find the weak points now than in front of the jury. Give concrete, actionable suggestions, not general praise.

**[Paste or attach the proposal document here]**

---

## Tips for using this

- Run it through **both models separately** with the same prompt, then compare — they often catch different gaps (DeepSeek tends to be sharper on technical/model-choice critique, ChatGPT often stronger on structure/completeness and compliance framing).
- If either tool has a smaller context window or you're pasting instead of uploading, trim the proposal to the essentials (architecture + occlusion-handling section) rather than the full document.
