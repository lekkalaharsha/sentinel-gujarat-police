# Technical Proposal
## Gujarat Police Innovation Challenge 2026 — AI-Powered CCTV Integration & Real-Time Intelligence

**Applicant Category:** Independent Researcher / Innovator
**Track:** Open Innovation Challenge — Category A (Students / Individual Innovators / Small & Medium Startups)

---

### 1. Problem Understanding

Gujarat operates 80,000+ CCTV cameras across multiple government departments, each using different vendors, Video Management Systems (VMS), and network architectures. This fragmentation prevents:

- Cross-camera search and tracking (e.g., following a suspect or vehicle across zones)
- Real-time correlation of alerts from disparate systems
- Centralized, low-latency access to surveillance intelligence for field officers and command centers

**Core ask:** Build a system that unifies heterogeneous CCTV feeds into a single interoperable layer, and layer real-time AI analytics on top — suspicious person/vehicle detection, unusual activity recognition, and ANPR — with alerting that works across the fragmented infrastructure.

---

### 2. Proposed Solution: "Unified Sentinel Layer" (working name)

A three-layer architecture designed to sit *on top of* existing CCTV infrastructure without requiring hardware replacement.

#### Layer 1 — Ingestion & Normalization
- **Protocol-agnostic adapters** (ONVIF, RTSP, proprietary VMS APIs) to pull feeds regardless of vendor
- **Edge normalization**: transcode/resample streams to a common format (resolution, frame rate, codec) before central processing, reducing bandwidth load
- **Metadata tagging** at ingestion: camera ID, GPS location, department owner, timestamp sync (NTP-aligned) — critical for later cross-camera correlation

#### Layer 2 — AI Analytics Core
- **Object detection & tracking**: YOLOv8/YOLOv10 or RT-DETR for person/vehicle detection, fine-tuned on Indian road/urban scene datasets
- **Re-identification (Re-ID) module**: appearance-embedding model (e.g., OSNet or a fine-tuned ResNet-based Re-ID) to match the same person/vehicle across non-overlapping camera views — this is what makes "track a suspect across the city" possible
- **ANPR**: two-stage pipeline — plate detection (YOLO-based) + OCR (CRNN or PaddleOCR fine-tuned for Indian plate formats, including regional scripts)
- **Anomaly/unusual-activity detection**: a lightweight action-recognition model (e.g., SlowFast or a pose-based approach using MediaPipe/OpenPose features) trained to flag loitering, abandoned objects, sudden crowd movement, or fights
- **Alert fusion engine**: correlates detections across cameras/time windows to reduce false positives before alerting an officer (e.g., "vehicle flagged at Camera A, matched at Camera B within plausible travel time")

#### Layer 3 — Command & Interoperability
- **Unified search API**: query by face/vehicle description, plate number, time window, or location — returns matches across all connected cameras regardless of source VMS
- **Real-time alert dashboard**: role-based access for control room vs. field officers, with map-based visualization of alert origin and predicted movement corridor
- **Interoperability adapter layer**: exposes a standard REST/gRPC API so existing department-specific VMS platforms can plug in without being replaced — this directly addresses the "different vendors/architectures" pain point rather than mandating a rip-and-replace

---

### 3. Why This Approach

| Design choice | Rationale |
|---|---|
| Adapter-based ingestion, not VMS replacement | Realistic given 80,000 cameras already deployed under multiple vendors — replacement is not feasible at this scale/cost |
| Re-ID over face recognition as primary tracking method | More robust to occlusion, distance, and camera angle in real outdoor CCTV conditions; face recognition used as a secondary confirmation signal only |
| Alert fusion before human notification | Reduces alert fatigue — a known failure mode in large-scale surveillance deployments |
| Edge normalization | Reduces central bandwidth/compute load, making the system scalable to tens of thousands of feeds |

---

### 4. Compliance & Governance

- Architecture designed for compliance with the **Digital Personal Data Protection (DPDP) Act, 2023**: role-based access, audit logging of every search/query, and configurable data-retention windows
- Recommend an **on-premise/state-cloud deployment** (not third-party public cloud) for sensitive surveillance data, consistent with typical law-enforcement data-residency requirements

---

### 5. Tech Stack (proposed)

- **Models**: YOLOv8/RT-DETR, OSNet (Re-ID), PaddleOCR/CRNN (ANPR), SlowFast (activity recognition)
- **Serving/inference**: NVIDIA Triton or TensorRT for edge/on-prem GPU inference
- **Streaming/ingestion**: GStreamer + ONVIF client libraries
- **Backend**: FastAPI/Go microservices, Kafka for event streaming between layers
- **Storage**: PostgreSQL + PostGIS (spatial queries), object storage for clip evidence
- **Dashboard**: React-based control room UI with map overlay (Mapbox/Leaflet)

---

### 6. Proof-of-Concept Scope for Stage 1

Given hackathon time constraints, the Stage 1 PoC will demonstrate on a **small multi-camera testbed** (2–4 simulated or public-dataset feeds):
1. Ingest feeds from at least two different "simulated vendor" formats
2. Detect and track a person/vehicle across both feeds (Re-ID demo)
3. Run ANPR on a vehicle and log a plate match
4. Trigger a fused alert only when corroborated across cameras (not on single-camera detection alone)

---

### 7. Handling Occlusion, Coverage Gaps & Loss of Visibility

A realistic system must be explicit about what it can and cannot guarantee. We frame this as a **decision-support and probability-ranking tool, not a guaranteed continuous-tracking system** — this is both technically accurate and, for a jury of technical/police evaluators, a more credible position than claiming perfect uninterrupted tracking.

#### 7.1 Brief occlusion within a single camera's view
*(e.g., a bus or crowd temporarily blocks the subject)*
- Handled at the **tracking layer**, not detection. Algorithms such as **ByteTrack** or **DeepSORT** maintain a predicted trajectory using Kalman filtering during short gaps, and re-associate the object once it reappears based on position continuity and appearance similarity.
- Effective for occlusions of roughly 1–2 seconds; beyond that, confidence in re-association drops and the system should flag lower certainty rather than silently continuing the track.

#### 7.2 Gap between non-overlapping cameras
*(subject leaves Camera A's view and hasn't yet reached Camera B)*
- This is **not** live tracking — it is **Re-ID matching**. The system captures an appearance fingerprint at Camera A (vehicle color/shape/partial plate, or for persons: clothing, build, gait, accessories) and matches it against detections at Camera B.
- Matches are weighted by **plausible travel time** between the two camera locations, using the road network distance and expected speed range. A candidate appearing outside the plausible time window is deprioritized or excluded.
- Output is a **ranked list of candidate matches with confidence scores**, presented to a human operator for confirmation — never an automatic "confirmed identity" alert. This avoids false accusations from appearance-similarity errors (e.g., two similar-colored sedans).

#### 7.3 Total loss of visibility
*(subject enters an unmonitored road, private property, or building)*
- No computer vision technique recovers a subject with no camera coverage — this must be stated plainly in the proposal rather than implied away.
- Mitigations that keep the system useful even here:
  - **Predictive path modeling**: using last known heading/speed and the road network, estimate a probability cone of likely locations and recommend which nearby cameras to prioritize monitoring.
  - **Data fusion beyond CCTV** *(subject to data access/permissions from the problem statement)*: cross-referencing with FASTag/toll records, RTO vehicle registration data, or patrol-unit field reports to re-acquire a vehicle trail.
  - **Last-seen alert broadcast**: automatically push the last known location, direction, and appearance description to nearby patrol units, shifting from "camera re-detection" to "human response" once the system's confidence in re-acquiring the subject visually drops below a usable threshold.

#### 7.4 Person-specific fallback (no clear face)
*(subject is turned away, masked, or too far/low-resolution for face recognition)*
- Falls back to **soft biometrics**: clothing color and pattern, approximate height/build, gait signature, and carried items (bags, distinctive accessories).
- These features remain reasonably stable over short time windows even without a usable facial capture, and are used the same way as vehicle appearance fingerprints — for ranked Re-ID matching, not automatic identification.

#### 7.5 Design implication for the jury/evaluation
- The system should always expose its **confidence level and reasoning** (e.g., "72% match based on color + travel-time plausibility, no plate confirmation") rather than presenting binary "found/not found" results — this keeps a human in the loop for any action with legal or operational consequences, and is a more defensible design for law-enforcement deployment.

---

### 8. Team / Applicant Note
*(Placeholder — fill in your background, prior work, publications, or relevant projects here before submission.)*

---

### 9. Open Questions to Resolve After Registration
- Exact wording and scope of the specific problem statement selected from the portal
- Whether sample data/API access is provided via the portal (similar to AIKosh sample data in comparable IndiaAI challenges) or whether public datasets must be used
- Submission format required (abstract length, PPT/PDF, code repo requirements)
