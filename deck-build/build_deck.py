# Generates Sentinel_Solution_Presentation.pptx — the mandatory "Solution
# Presentation (PPT/PDF)" deliverable (HACKATHON_DETAILS.md §9.1). Content is
# derived from this repo's own verified docs (HLD.md, STRATEGY.md,
# SCALABILITY.md, REQUIREMENTS_COVERAGE.md) — nothing here claims a
# capability those docs don't already back with real, verified code.
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn

NAVY = RGBColor(0x0B, 0x14, 0x24)
NAVY_LIGHT = RGBColor(0x11, 0x18, 0x23)
BLUE = RGBColor(0x3B, 0x82, 0xF6)
BLUE_DARK = RGBColor(0x1D, 0x4E, 0xD8)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x14, 0x1B, 0x2A)
GRAY = RGBColor(0x5B, 0x66, 0x77)
LIGHT_GRAY = RGBColor(0xF1, 0xF4, 0xF8)
GREEN = RGBColor(0x16, 0xA3, 0x4A)
AMBER = RGBColor(0xD9, 0x7A, 0x06)
RED = RGBColor(0xDC, 0x26, 0x26)
LINE_GRAY = RGBColor(0xDD, 0xE3, 0xEA)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

prs = Presentation()
prs.slide_width = SLIDE_W
prs.slide_height = SLIDE_H
BLANK = prs.slide_layouts[6]

PAGE_NO = [0]


def add_slide():
    s = prs.slides.add_slide(BLANK)
    return s


def set_bg(slide, color):
    bg = slide.background
    bg.fill.solid()
    bg.fill.fore_color.rgb = color


def box(slide, l, t, w, h, fill=None, line=None, line_w=None, shadow=False):
    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, l, t, w, h)
    shp.shadow.inherit = False
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = line_w or Pt(1)
    return shp


def rrect(slide, l, t, w, h, fill=None, line=None, line_w=Pt(1)):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    shp.shadow.inherit = False
    try:
        shp.adjustments[0] = 0.08
    except Exception:
        pass
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = line_w
    return shp


def txt(slide, l, t, w, h, text, size=18, color=INK, bold=False, italic=False,
        align=PP_ALIGN.LEFT, font="Calibri", anchor=MSO_ANCHOR.TOP, line_spacing=1.0,
        space_after=0):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    lines = text.split("\n")
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = line_spacing
        p.space_after = Pt(space_after)
        r = p.add_run()
        r.text = line
        r.font.size = Pt(size)
        r.font.bold = bold
        r.font.italic = italic
        r.font.color.rgb = color
        r.font.name = font
    return tb


def bullets(slide, l, t, w, h, items, size=15, color=INK, font="Calibri",
            space_after=10, line_spacing=1.08, bullet_color=None, bold_lead=False):
    """items: list of (text, level) or plain strings (level 0)."""
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    bcolor = bullet_color or BLUE
    for i, item in enumerate(items):
        if isinstance(item, tuple):
            text, level = item
        else:
            text, level = item, 0
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(space_after)
        p.line_spacing = line_spacing
        p.level = 0
        indent = Inches(0.28 * level)
        marker = {0: "■ ", 1: "– ", 2: "• "}.get(level, "• ")
        r1 = p.add_run()
        r1.text = marker
        r1.font.size = Pt(size - (2 if level else 0))
        r1.font.color.rgb = bcolor if level == 0 else GRAY
        r1.font.bold = True
        r1.font.name = font
        # emulate indent via leading spaces (python-pptx indent handling is finicky)
        if level:
            p.paragraph_format if False else None
        r2 = p.add_run()
        r2.text = text
        r2.font.size = Pt(size - (2 if level else 0))
        r2.font.color.rgb = color if level == 0 else GRAY
        r2.font.bold = (level == 0 and bold_lead)
        r2.font.name = font
        pPr = p._pPr
        if pPr is None:
            pPr = p._p.get_or_add_pPr()
        pPr.set('marL', str(Emu(indent)))
        pPr.set('indent', '0')
    return tb


def footer(slide, page_label):
    box(slide, Inches(0), Inches(7.16), SLIDE_W, Inches(0.34), fill=LIGHT_GRAY)
    txt(slide, Inches(0.5), Inches(7.18), Inches(8), Inches(0.3),
        "Sentinel — Gujarat Police Innovation Challenge 2026", size=9, color=GRAY)
    txt(slide, Inches(11.6), Inches(7.18), Inches(1.4), Inches(0.3),
        page_label, size=9, color=GRAY, align=PP_ALIGN.RIGHT)


def content_slide(kicker, title, accent=BLUE):
    s = add_slide()
    set_bg(s, WHITE)
    box(s, 0, 0, SLIDE_W, Inches(1.15), fill=NAVY)
    box(s, 0, Inches(1.15), SLIDE_W, Pt(3), fill=accent)
    txt(s, Inches(0.55), Inches(0.18), Inches(11), Inches(0.32), kicker.upper(),
        size=12, color=BLUE, bold=True, font="Calibri")
    txt(s, Inches(0.55), Inches(0.46), Inches(12.2), Inches(0.62), title,
        size=27, color=WHITE, bold=True, font="Calibri")
    PAGE_NO[0] += 1
    footer(s, f"{PAGE_NO[0]:02d} / 19")
    return s


def section_slide(number, title, subtitle):
    s = add_slide()
    set_bg(s, NAVY)
    box(s, 0, 0, Inches(0.16), SLIDE_H, fill=BLUE)
    txt(s, Inches(0.9), Inches(2.55), Inches(3), Inches(1), number,
        size=64, color=BLUE_DARK, bold=True, font="Calibri")
    txt(s, Inches(0.95), Inches(3.35), Inches(11.2), Inches(1.1), title,
        size=40, color=WHITE, bold=True, font="Calibri")
    txt(s, Inches(0.97), Inches(4.35), Inches(10.8), Inches(0.9), subtitle,
        size=16, color=RGBColor(0xA8, 0xB6, 0xC9), font="Calibri")
    PAGE_NO[0] += 1
    footer(s, f"{PAGE_NO[0]:02d} / 19")
    return s


def status_chip(slide, l, t, label, kind="done"):
    colors = {"done": (GREEN, "VERIFIED"), "partial": (AMBER, "PARTIAL"),
              "gap": (RED, "GAP — STATED"), "roadmap": (GRAY, "ROADMAP")}
    color, tag = colors[kind]
    w = Inches(0.18 + 0.083 * len(tag))
    chip = rrect(slide, l, t, w, Inches(0.26), fill=color)
    tf = chip.text_frame
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = tag
    r.font.size = Pt(9)
    r.font.bold = True
    r.font.color.rgb = WHITE
    _ = label
    return chip


# ============================================================ SLIDE 1 — TITLE
s = add_slide()
set_bg(s, NAVY)
box(s, 0, Inches(5.85), SLIDE_W, Pt(2.5), fill=BLUE)
txt(s, Inches(0.95), Inches(0.7), Inches(4), Inches(0.4), "SENTINEL // CONTROL ROOM",
    size=13, color=BLUE, bold=True)
txt(s, Inches(0.9), Inches(2.15), Inches(11.5), Inches(1.5), "SENTINEL",
    size=76, color=WHITE, bold=True)
txt(s, Inches(0.97), Inches(3.35), Inches(11), Inches(1.1),
    "An open, vendor-neutral interoperability and intelligence layer\nfor Gujarat's 26-department CCTV infrastructure",
    size=20, color=RGBColor(0xC7, 0xD3, 0xE3), line_spacing=1.25)
txt(s, Inches(0.97), Inches(6.05), Inches(11), Inches(0.4),
    "Model 1 (Centralised CCTV Registry & GIS) + Model 2 (Unified Viewing & Metadata Analytics) — hybrid architecture",
    size=13, color=BLUE)
txt(s, Inches(0.97), Inches(6.55), Inches(6), Inches(0.4),
    "Gujarat Police Innovation Challenge 2026 — Phase 1 Submission", size=12, color=GRAY)
txt(s, Inches(9.7), Inches(6.55), Inches(2.7), Inches(0.4), "₹51,00,000 Prize Pool",
    size=12, color=GRAY, align=PP_ALIGN.RIGHT)

# ============================================================ SLIDE 2 — AGENDA
s = content_slide("Roadmap", "Agenda")
items = [
    "01  The problem — 26 departments, ~80,000 cameras, no unified cross-reference",
    "02  Model choice & justification — why Model 1 + Model 2, not a from-scratch platform",
    "03  Solution overview — objectives and the genuine innovation",
    "04  Architecture — pilot tier built today, production tier documented",
    "05  AI video analytics pipeline — detection through cross-camera identity",
    "06  The core differentiator — ANPR failure ≠ tracking failure",
    "07  Geo-temporal route reconstruction — observed vs. inferred, honestly labelled",
    "08  Watchlist correlation & governed alert lifecycle",
    "09  Security, RBAC & DPDP-aligned governance",
    "10  Scalability toward 80,000 cameras",
    "11  Evaluation test case status & operational benefits",
    "12  Honest gaps and roadmap",
]
bullets(s, Inches(0.6), Inches(1.55), Inches(11.8), Inches(5.4), items, size=15.5,
        space_after=13, bullet_color=BLUE)

# ============================================================ SLIDE 3 — PROBLEM
s = content_slide("The Challenge", "26 departments. ~80,000 cameras. No shared intelligence layer.")
left_items = [
    "Mixed analog and IP cameras, ~1,000 km apart — border districts to Valsad, Dahod, Dwarka",
    "Heterogeneous vendors, formats, and VMS platforms across departments",
    "Retention varies 7–15+ days, cloud or local, department by department",
    "No unified way to monitor, search, or cross-reference footage with law-enforcement databases",
]
bullets(s, Inches(0.6), Inches(1.65), Inches(6.1), Inches(4.6), left_items, size=15,
        space_after=16, line_spacing=1.15)
card = rrect(s, Inches(7.1), Inches(1.6), Inches(5.65), Inches(4.9), fill=LIGHT_GRAY)
txt(s, Inches(7.4), Inches(1.85), Inches(5.1), Inches(0.4), "Mandatory live test case",
    size=15, color=NAVY, bold=True)
tc_items = [
    "Onboard ~50 heterogeneous simulated camera feeds",
    "Track a designated vehicle by registration number",
    "Produce complete, timestamped, location-wise movement history",
    "Cross-reference every sighting against a watchlist",
    "Fire automated real-time alerts on a match",
]
bullets(s, Inches(7.4), Inches(2.35), Inches(5.1), Inches(3.9), tc_items, size=13.5,
        space_after=13, bullet_color=BLUE_DARK)

# ============================================================ SLIDE 4 — PITCH CORRECTION
s = content_slide("Positioning", "We are not proposing to replace what already exists")
box1 = rrect(s, Inches(0.6), Inches(1.6), Inches(5.8), Inches(2.5), fill=RGBColor(0xFD, 0xEC, 0xEC))
txt(s, Inches(0.9), Inches(1.8), Inches(5.2), Inches(0.4), "What we do NOT claim", size=15, color=RED, bold=True)
bullets(s, Inches(0.9), Inches(2.3), Inches(5.2), Inches(1.7), [
    "“We built Gujarat's CCTV command platform”",
    "Inventing detection, ANPR, or cross-camera tracking — already shipped by Staqu, Videonetics, Vehant, Innefu",
], size=13.5, space_after=10, bullet_color=RED, color=INK)

box2 = rrect(s, Inches(6.7), Inches(1.6), Inches(6.0), Inches(2.5), fill=RGBColor(0xEA, 0xF6, 0xEC))
txt(s, Inches(7.0), Inches(1.8), Inches(5.4), Inches(0.4), "What we actually pitch", size=15, color=GREEN, bold=True)
bullets(s, Inches(7.0), Inches(2.3), Inches(5.4), Inches(1.7), [
    "An interoperability and intelligence layer above existing VISWAS / TRINETRA / NETRAM infrastructure",
    "A genuinely new, open, explainable vehicle-identity-resolution layer on top of it",
], size=13.5, space_after=10, bullet_color=GREEN, color=INK)

txt(s, Inches(0.6), Inches(4.35), Inches(12.1), Inches(0.4), "Why this matters", size=15, color=NAVY, bold=True)
bullets(s, Inches(0.6), Inches(4.85), Inches(12.1), Inches(1.9), [
    "Gujarat already operates VISWAS/NETRAM/TRINETRA: 7,000+ cameras, 34 district NETRAM centres, Phase-II adding ~10,500 more",
    "A jury with real Gujarat Police domain knowledge will reasonably ask “what did you invent?” if we pitch a from-scratch platform",
    "Framing honestly is not a weaker pitch — it is what “innovative hybrid architecture with operational value” (an explicit bonus criterion) actually rewards",
], size=14, space_after=12, line_spacing=1.15)

# ============================================================ SLIDE 5 — MODEL JUSTIFICATION
s = content_slide("Solution Model", "Model 1 + Model 2 hybrid — with a documented Model 3/4 roadmap")
colw = Inches(3.95)
gap = Inches(0.2)
x0 = Inches(0.6)
labels = [
    ("MODEL 1", "Centralised Registry & GIS", "Mandatory foundation — camera inventory, GIS mapping, health monitoring, gap analysis, RBAC", "done"),
    ("MODEL 2", "Unified Viewing & Analytics", "Direct RTSP/catalogue integration, no middleware — ANPR, event tagging, searchable movement records, alerts", "done"),
    ("MODEL 3 / 4", "Federation → Central AI Platform", "Documented production evolution path — Kafka event bus, regional media fabric, statewide AI fabric", "roadmap"),
]
for i, (tag, title, desc, kind) in enumerate(labels):
    x = x0 + i * (colw + gap)
    card = rrect(s, x, Inches(1.65), colw, Inches(3.4), fill=LIGHT_GRAY if kind != "roadmap" else WHITE,
                 line=LINE_GRAY, line_w=Pt(1.25))
    status_chip(s, x + Inches(0.25), Inches(1.9), tag, kind="done" if kind == "done" else "roadmap")
    txt(s, x + Inches(0.25), Inches(2.3), colw - Inches(0.5), Inches(0.3), tag, size=13, color=BLUE_DARK, bold=True)
    txt(s, x + Inches(0.25), Inches(2.62), colw - Inches(0.5), Inches(0.6), title, size=16, color=NAVY, bold=True)
    txt(s, x + Inches(0.25), Inches(3.35), colw - Inches(0.5), Inches(1.6), desc, size=12.5, color=GRAY, line_spacing=1.2)

txt(s, Inches(0.6), Inches(5.35), Inches(12.1), Inches(0.4), "Why hybrid, not Model 4 (Central VMS)", size=15, color=NAVY, bold=True)
bullets(s, Inches(0.6), Inches(5.8), Inches(12.1), Inches(1.4), [
    "“Combine elements from two or more models” is the problem statement's own definition of hybrid (§7); an innovative hybrid is an explicit bonus criterion (§10)",
    "We claim credit only for what is genuinely built and verified end-to-end — Model 3/4 elements are a documented roadmap, not implemented, and we say so",
], size=13.5, space_after=10)

# ============================================================ SLIDE 6 — SOLUTION OVERVIEW / INNOVATION
s = content_slide("Solution Overview", "The genuine innovation: an open, explainable identity-resolution layer")
txt(s, Inches(0.6), Inches(1.55), Inches(12.1), Inches(0.7),
    "A persistent vehicle entity assembled from uncertain observations — plate-OCR confidence, appearance similarity, "
    "temporal feasibility, recency — where every cross-camera link records why it was made.",
    size=15, color=GRAY, line_spacing=1.25)
inn = [
    ("ANPR failure ≠ tracking failure", "A vehicle is never dropped for an unreadable plate — it's tracked by colour/type/appearance until any camera reads its plate, then the whole chain resolves retroactively."),
    ("Geo-temporal route reconstruction", "Movement history interleaves OBSERVED sightings with honestly-labelled INFERRED camera-less segments — inferred is never presented as confirmed."),
    ("Governed alert lifecycle", "Watchlist hits are live investigation items (new → acknowledged → resolved/dismissed), not fire-and-forget log lines — every transition is attributed and audited."),
    ("“Why was this linked?” explainability", "Every sighting records its link method, similarity score, and time gap — a transparency aid, not a black box, and a direct mitigation for operator automation bias."),
]
colw = Inches(5.95)
for i, (title, desc) in enumerate(inn):
    x = Inches(0.6) + (i % 2) * (colw + Inches(0.3))
    y = Inches(2.55) + (i // 2) * Inches(2.15)
    card = rrect(s, x, y, colw, Inches(1.95), fill=LIGHT_GRAY)
    box(s, x, y, Inches(0.09), Inches(1.95), fill=BLUE)
    txt(s, x + Inches(0.3), y + Inches(0.2), colw - Inches(0.6), Inches(0.45), title, size=15, color=NAVY, bold=True)
    txt(s, x + Inches(0.3), y + Inches(0.68), colw - Inches(0.6), Inches(1.2), desc, size=12, color=GRAY, line_spacing=1.2)

# ============================================================ SLIDE 7 — ARCHITECTURE
s = content_slide("Architecture", "High-level architecture — pilot tier built, production tier documented")
# Left column: pilot tier (built)
lx = Inches(0.6); lw = Inches(6.0)
pilot = rrect(s, lx, Inches(1.55), lw, Inches(5.15), fill=LIGHT_GRAY, line=BLUE, line_w=Pt(1.5))
status_chip(s, lx + Inches(0.25), Inches(1.75), "", kind="done")
txt(s, lx + Inches(1.15), Inches(1.75), lw - Inches(1.4), Inches(0.3), "PILOT / EDGE TIER — THIS SUBMISSION",
    size=12, color=BLUE_DARK, bold=True)
stages = [
    "26 Departments (incl. existing VISWAS / TRINETRA / NETRAM)",
    "Catalogue client → live camera discovery (cameras.json)",
    "Stream Manager → 1 RTSP worker/camera, TCP-forced, PTS-timed, backoff reconnect",
    "Analytics pipeline: YOLOv8 detect → plate region → enhance → PaddleOCR",
    "→ ByteTrack (within-camera) → Re-ID embedding → cross-camera identity resolution",
    "Event store: VehicleEvent, VehicleIdentity, Registry, Watchlist, Alert, AuditLog",
    "→ Watchlist engine + alerts   → RBAC-gated REST API (FastAPI)",
    "React frontend: GIS map, live HLS view, movement timeline + explainability, ops console",
]
y = Inches(2.2)
for i, st in enumerate(stages):
    txt(s, lx + Inches(0.3), y, lw - Inches(0.6), Inches(0.5), st, size=11.5, color=INK, line_spacing=1.1)
    y += Inches(0.56)
    if i < len(stages) - 1:
        txt(s, lx + Inches(0.3), y - Inches(0.14), Inches(0.4), Inches(0.2), "↓", size=12, color=BLUE, bold=True)

rx = Inches(6.85); rw = Inches(5.85)
prod = rrect(s, rx, Inches(1.55), rw, Inches(5.15), fill=WHITE, line=LINE_GRAY, line_w=Pt(1.25))
status_chip(s, rx + Inches(0.25), Inches(1.75), "", kind="roadmap")
txt(s, rx + Inches(1.15), Inches(1.75), rw - Inches(1.4), Inches(0.3), "PRODUCTION TARGET — DOCUMENTED, NOT BUILT THIS WEEK",
    size=11, color=GRAY, bold=True)
prod_items = [
    "Regional media fabric (MediaMTX/go2rtc) between connectors and AI fabric",
    "Kafka event bus for horizontal ingestion scaling",
    "AI fabric: Detector → ByteTrack → ANPR → Re-ID confirmation, sharded by region",
    "Central event plane: PostgreSQL/PostGIS at statewide scale",
    "Authorized government DB queries (VAHAN, SARTHI, eGujCop, CCTNS) — query, don't copy",
    "Governance plane: department-scoped RBAC, purpose-bound audit, retention policy",
]
bullets(s, rx + Inches(0.3), Inches(2.35), rw - Inches(0.6), Inches(3.9), prod_items, size=12.5,
        space_after=14, bullet_color=GRAY, color=GRAY, line_spacing=1.2)
txt(s, rx + Inches(0.3), Inches(6.15), rw - Inches(0.6), Inches(0.5),
    "Core principle: centralize metadata/events/identity/governance — not every raw video frame.",
    size=11.5, color=NAVY, italic=True, line_spacing=1.15)

# ============================================================ SLIDE 8 — INTEGRATION APPROACH
s = content_slide("Integration", "Heterogeneous camera & VMS integration approach")
left = [
    "Discovery, never hardcoding — every camera URL derived from the live catalogue; camera IDs and availability can change, the catalogue is the contract",
    "RTSP forced over TCP; mixed H.264/H.265 tolerated — join-time decoder warnings logged, never treated as fatal",
    "Timing correctness — every frame carries PTS (CAP_PROP_POS_MSEC); CAP_PROP_FPS is never trusted for velocity/dwell math",
    "Resilience — exponential-backoff reconnect (2s→30s cap), never a tight loop",
]
right = [
    "Scene-discontinuity handling — the sandbox's recording loop point is detected as PTS-backward and triggers an explicit tracker-state reset",
    "ONVIF as the vendor-neutral abstraction target for real heterogeneous department cameras (sandbox exposes plain RTSP directly)",
    "Cross-camera timing uses one server-side clock at persist-time — never assumes 80,000 legacy cameras share NTP sync",
    "Department tagging via CameraRegistry — bulk, manual, and API onboarding, independent of protocol/vendor",
]
bullets(s, Inches(0.6), Inches(1.65), Inches(6.0), Inches(5.2), left, size=13.5, space_after=16, line_spacing=1.2)
bullets(s, Inches(6.85), Inches(1.65), Inches(6.0), Inches(5.2), right, size=13.5, space_after=16, line_spacing=1.2)

# ============================================================ SLIDE 9 — AI PIPELINE TABLE
s = content_slide("AI Video Analytics", "The pipeline — detection through cross-camera identity")
rows = [
    ("Vehicle detection", "YOLOv8n (Ultralytics, pretrained COCO)", "done"),
    ("Plate localization", "Heuristic crop — fine-tuned localizer evaluated, not integrated", "partial"),
    ("Plate enhancement", "Grayscale + CLAHE + upscale", "done"),
    ("OCR", "PaddleOCR 2.9.1 (pinned)", "done"),
    ("Within-camera tracking", "Real ByteTrack, one persistent tracker per camera", "done"),
    ("Appearance Re-ID", "HSV colour histogram + cosine similarity (FastReID is the documented upgrade)", "partial"),
    ("Cross-camera identity", "Plate-first, appearance-second resolver — retroactive plate upgrade", "done"),
    ("Make/model classification", "Not implemented — no open-source Indian-market model exists", "gap"),
    ("Motion attributes", "Dwell / speed / direction from PTS-driven track path (image-plane, not calibrated)", "done"),
]
tbl_l = Inches(0.6); tbl_t = Inches(1.55); tbl_w = Inches(12.1)
col1, col2, col3 = Inches(3.0), Inches(7.4), Inches(1.7)
rh = Inches(0.535)
hdr = box(s, tbl_l, tbl_t, tbl_w, Inches(0.4), fill=NAVY)
txt(s, tbl_l + Inches(0.15), tbl_t + Inches(0.06), col1, Inches(0.3), "Stage", size=12, color=WHITE, bold=True)
txt(s, tbl_l + col1 + Inches(0.15), tbl_t + Inches(0.06), col2, Inches(0.3), "Implementation", size=12, color=WHITE, bold=True)
txt(s, tbl_l + col1 + col2 + Inches(0.1), tbl_t + Inches(0.06), col3, Inches(0.3), "Status", size=12, color=WHITE, bold=True)
y = tbl_t + Inches(0.4)
for i, (stage, impl, kind) in enumerate(rows):
    rowfill = LIGHT_GRAY if i % 2 == 0 else WHITE
    box(s, tbl_l, y, tbl_w, rh, fill=rowfill)
    txt(s, tbl_l + Inches(0.15), y + Inches(0.07), col1 - Inches(0.2), rh, stage, size=11.5, color=NAVY, bold=True, line_spacing=1.0)
    txt(s, tbl_l + col1 + Inches(0.15), y + Inches(0.07), col2 - Inches(0.2), rh, impl, size=11, color=INK, line_spacing=1.0)
    status_chip(s, tbl_l + col1 + col2 + Inches(0.05), y + Inches(0.12), "", kind=kind)
    y += rh
txt(s, tbl_l, y + Inches(0.12), tbl_w, Inches(0.35),
    "Real-world caveat, stated plainly: OCR verified against clean synthetic text; real Indian-plate footage accuracy is the single most jury-visible unmeasured number.",
    size=11, color=GRAY, italic=True)

# ============================================================ SLIDE 10 — CORE DIFFERENTIATOR
s = content_slide("Core Differentiator", "ANPR failure ≠ tracking failure")
cams = [
    ("Camera 1", "Plate unreadable", "Logged by colour + type + appearance embedding", "gap"),
    ("Camera 2", "Plate unreadable", "Matched to Camera 1 by appearance — same identity", "gap"),
    ("Camera 3", "Plate READ: GJ01AB1234", "Identity upgraded — retroactively resolves Cameras 1 & 2 too", "done"),
]
cw = Inches(3.75); gap2 = Inches(0.35); x0b = Inches(0.6)
for i, (cam, plate_status, desc, kind) in enumerate(cams):
    x = x0b + i * (cw + gap2)
    card = rrect(s, x, Inches(1.75), cw, Inches(2.7), fill=LIGHT_GRAY if kind == "gap" else RGBColor(0xEA, 0xF6, 0xEC),
                 line=LINE_GRAY if kind == "gap" else GREEN, line_w=Pt(1.25))
    txt(s, x + Inches(0.25), Inches(1.95), cw - Inches(0.5), Inches(0.35), cam, size=15, color=NAVY, bold=True)
    status_chip(s, x + Inches(0.25), Inches(2.35), "", kind=kind)
    txt(s, x + Inches(0.25), Inches(2.75), cw - Inches(0.5), Inches(0.5), plate_status, size=13, color=INK, bold=True)
    txt(s, x + Inches(0.25), Inches(3.25), cw - Inches(0.5), Inches(1.1), desc, size=12, color=GRAY, line_spacing=1.2)
    if i < 2:
        txt(s, x + cw + Inches(0.02), Inches(2.85), gap2, Inches(0.5), "→", size=22, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
txt(s, Inches(0.6), Inches(4.75), Inches(12.1), Inches(1.5),
    "Verified with a real (non-mocked) three-camera scenario: two deliberately unreadable plates, one successful read — "
    "all three sightings correctly merge into one VehicleIdentity, including the two anonymous ones. This is the mechanism the "
    "mandatory test case's “complete timestamped movement history” actually depends on.",
    size=14, color=NAVY, line_spacing=1.3)

# ============================================================ SLIDE 11 — GEO-TEMPORAL ROUTE
s = content_slide("Bonus Differentiator", "Geo-temporal route reconstruction — observed vs. inferred")
txt(s, Inches(0.6), Inches(1.6), Inches(12.1), Inches(0.6),
    "Between two confirmed sightings, movement history interleaves honestly-labelled INFERRED camera-less segments — "
    "straight-line (haversine) distance + time-gap feasibility, never presented as observed fact.",
    size=14.5, color=GRAY, line_spacing=1.25)
timeline_y = Inches(2.7)
pts = [("cam01", "OBSERVED", "done"), ("INFERRED\nsegment", "plausible", "roadmap"), ("cam03", "OBSERVED", "done"),
       ("INFERRED\nsegment", "not a direct\ndrive — flagged", "gap"), ("cam05", "OBSERVED", "done")]
n = len(pts)
seg_w = Inches(2.2)
start_x = Inches(0.7)
for i, (label, sub, kind) in enumerate(pts):
    x = start_x + i * seg_w
    if i % 2 == 0:
        c = rrect(s, x, timeline_y, Inches(1.7), Inches(1.15), fill=RGBColor(0xEA, 0xF6, 0xEC), line=GREEN, line_w=Pt(1.25))
        txt(s, x, timeline_y + Inches(0.18), Inches(1.7), Inches(0.35), label, size=14, color=NAVY, bold=True, align=PP_ALIGN.CENTER)
        txt(s, x, timeline_y + Inches(0.62), Inches(1.7), Inches(0.4), sub, size=10.5, color=GREEN, bold=True, align=PP_ALIGN.CENTER)
    else:
        dash_color = AMBER if kind == "roadmap" else RED
        fill_c = RGBColor(0xFB, 0xF1, 0xE3) if kind == "roadmap" else RGBColor(0xFD, 0xEC, 0xEC)
        c = rrect(s, x, timeline_y + Inches(0.15), Inches(1.7), Inches(0.85), fill=fill_c, line=dash_color, line_w=Pt(1.25))
        txt(s, x, timeline_y + Inches(0.22), Inches(1.7), Inches(0.4), label, size=11.5, color=NAVY, bold=True, align=PP_ALIGN.CENTER, line_spacing=1.0)
        txt(s, x, timeline_y + Inches(0.62), Inches(1.7), Inches(0.4), sub, size=9.5, color=dash_color, bold=True, align=PP_ALIGN.CENTER, line_spacing=1.0)
txt(s, Inches(0.6), Inches(4.3), Inches(12.1), Inches(0.5),
    "A high implied speed between two sightings flags “not a direct drive” — an unmonitored detour, or possibly a different vehicle — as a lead, not a fact.",
    size=13, color=GRAY, italic=True)
txt(s, Inches(0.6), Inches(5.15), Inches(12.1), Inches(0.4), "Deliberately not built yet (roadmap, stated honestly)", size=14, color=NAVY, bold=True)
bullets(s, Inches(0.6), Inches(5.6), Inches(12.1), Inches(1.3), [
    "Full road-network (OSM) travel-time routing — Gujarat's minor-road OSM coverage is incomplete",
    "Forward “PREDICTED next-camera” pruning — valuable at 80k-camera scale, not observable at a 50-camera pilot; would only ever be a soft ranking hint, never a hard filter",
], size=12.5, space_after=8, bullet_color=GRAY, color=GRAY)

# ============================================================ SLIDE 12 — WATCHLIST & ALERT LIFECYCLE
s = content_slide("Watchlist Correlation", "Governed alert lifecycle — a lead, not a verdict")
states = ["NEW", "ACKNOWLEDGED", "RESOLVED"]
alt = "DISMISSED\n(false positive)"
sx = Inches(0.8); sw = Inches(2.6); sy = Inches(1.85)
for i, st in enumerate(states):
    x = sx + i * (sw + Inches(0.55))
    c = rrect(s, x, sy, sw, Inches(0.85), fill=NAVY if i == 0 else (LIGHT_GRAY if i < 2 else RGBColor(0xEA, 0xF6, 0xEC)),
              line=BLUE if i == 0 else LINE_GRAY, line_w=Pt(1.25))
    txt(s, x, sy + Inches(0.27), sw, Inches(0.35), st, size=15, color=(WHITE if i == 0 else NAVY), bold=True, align=PP_ALIGN.CENTER)
    if i < 2:
        txt(s, x + sw, sy + Inches(0.22), Inches(0.5), Inches(0.4), "→", size=20, color=BLUE, bold=True, align=PP_ALIGN.CENTER)
dc = rrect(s, sx + 1 * (sw + Inches(0.55)), sy + Inches(1.25), sw, Inches(0.95), fill=RGBColor(0xFD, 0xEC, 0xEC), line=RED, line_w=Pt(1.25))
txt(s, sx + (sw + Inches(0.55)), sy + Inches(1.4), sw, Inches(0.7), alt, size=12.5, color=RED, bold=True, align=PP_ALIGN.CENTER, line_spacing=1.1)
txt(s, sx + 0.55*sw, sy + Inches(1.0), sw, Inches(0.3), "↓ (also reachable from NEW)", size=10, color=GRAY, align=PP_ALIGN.CENTER)

txt(s, Inches(0.6), Inches(3.7), Inches(5.9), Inches(0.4), "How it works", size=15, color=NAVY, bold=True)
bullets(s, Inches(0.6), Inches(4.2), Inches(5.9), Inches(2.6), [
    "Every persisted VehicleEvent with a resolved plate is checked against the watchlist at write time",
    "A match creates an Alert immediately — polled by the operator's Alerts panel",
    "Only server-declared transitions are permitted; every transition records who acted and when",
], size=13, space_after=12, line_spacing=1.2)

txt(s, Inches(6.85), Inches(3.7), Inches(5.85), Inches(0.4), "“Why was this linked?” explainability", size=15, color=NAVY, bold=True)
bullets(s, Inches(6.85), Inches(4.2), Inches(5.85), Inches(2.6), [
    "Every sighting records link method, similarity score, and time gap at the moment of resolution",
    "Fused, transparently-weighted score (plate 50% / appearance 35% / recency 15%) — a transparency aid, not a calibrated probability",
    "Direct mitigation for automation bias: low-confidence links are visually distinguished, never equal-weighted with a plate-confirmed hit",
], size=13, space_after=12, line_spacing=1.2)

# ============================================================ SLIDE 13 — SECURITY / RBAC / DPDP
s = content_slide("Governance", "Security, RBAC & DPDP-aligned privacy posture")
left = [
    ("Real RBAC, not decoration", "Every route requires an API key mapping to viewer / investigator / admin; missing or insufficient access gets a genuine 401/403"),
    ("Purpose-bound, audited queries", "Every history/search query logs the authenticated user, stated purpose, and case ID — never a client-supplied string"),
    ("Enforced retention, not policy-on-paper", "Vehicle events/identities/alerts purge automatically after a configurable window; audit logs are kept longer than the data they describe"),
]
right = [
    ("No face recognition — deliberate", "DPDP risk and NIST-documented demographic bias; not required by the mandatory vehicle test case — a governance choice, not an oversight"),
    ("Data minimization by design", "No face embeddings computed or stored anywhere — the system identifies what vehicle was seen where, not who someone is"),
    ("Found and fixed, not shipped", "An SSRF gap in the HLS proxy was found during development and closed with a same-host validation check, verified both ways"),
]
cardw = Inches(5.95)
for i, (title, desc) in enumerate(left):
    y = Inches(1.6) + i * Inches(1.7)
    c = rrect(s, Inches(0.6), y, cardw, Inches(1.5), fill=LIGHT_GRAY)
    box(s, Inches(0.6), y, Inches(0.08), Inches(1.5), fill=BLUE)
    txt(s, Inches(0.85), y + Inches(0.14), cardw - Inches(0.5), Inches(0.35), title, size=13.5, color=NAVY, bold=True)
    txt(s, Inches(0.85), y + Inches(0.52), cardw - Inches(0.5), Inches(0.9), desc, size=11.5, color=GRAY, line_spacing=1.18)
for i, (title, desc) in enumerate(right):
    y = Inches(1.6) + i * Inches(1.7)
    c = rrect(s, Inches(6.85), y, cardw, Inches(1.5), fill=LIGHT_GRAY)
    box(s, Inches(6.85), y, Inches(0.08), Inches(1.5), fill=BLUE_DARK)
    txt(s, Inches(7.1), y + Inches(0.14), cardw - Inches(0.5), Inches(0.35), title, size=13.5, color=NAVY, bold=True)
    txt(s, Inches(7.1), y + Inches(0.52), cardw - Inches(0.5), Inches(0.9), desc, size=11.5, color=GRAY, line_spacing=1.18)
txt(s, Inches(0.6), Inches(6.75), Inches(12.1), Inches(0.35),
    "DPDP Act §17 exempts law-enforcement processing — we design as if the Act's substantive obligations apply anyway.",
    size=11.5, color=NAVY, italic=True)

# ============================================================ SLIDE 14 — TECH STACK
s = content_slide("Technology", "Open-source stack, per the hackathon's requirement")
groups = [
    ("Backend & data", ["FastAPI", "SQLAlchemy (PostgreSQL-ready)", "SQLite (dev) → PostgreSQL/PostGIS (prod)"]),
    ("Computer vision & AI", ["OpenCV", "YOLOv8 (Ultralytics)", "PaddleOCR 2.9.1", "ByteTrack (Ultralytics-integrated)"]),
    ("Frontend", ["React", "Leaflet (GIS map)", "hls.js (live view)"]),
    ("Documented for scale", ["Kafka / RabbitMQ (event bus)", "MediaMTX / go2rtc (media fabric)", "pgvector / Milvus (Re-ID vector search)"]),
]
colw = Inches(2.9); gap3 = Inches(0.15)
for i, (grp, tools) in enumerate(groups):
    x = Inches(0.6) + i * (colw + gap3)
    c = rrect(s, x, Inches(1.65), colw, Inches(4.6), fill=LIGHT_GRAY if i < 3 else WHITE, line=LINE_GRAY if i == 3 else None)
    txt(s, x + Inches(0.22), Inches(1.9), colw - Inches(0.44), Inches(0.7), grp, size=14.5, color=NAVY, bold=True, line_spacing=1.1)
    items = [(t, 0) for t in tools]
    bullets(s, x + Inches(0.22), Inches(2.65), colw - Inches(0.44), Inches(3.3), items, size=12,
            space_after=12, bullet_color=(BLUE if i < 3 else GRAY), color=(INK if i < 3 else GRAY), line_spacing=1.15)
txt(s, Inches(0.6), Inches(6.5), Inches(12.1), Inches(0.5),
    "All components are open source, meeting the hackathon's Open Source Requirement in full.",
    size=13, color=GRAY, italic=True)

# ============================================================ SLIDE 15 — SCALABILITY
s = content_slide("Scalability", "From ~30-camera pilot to ~80,000 cameras statewide")
left = [
    ("Compute tiers", "Edge (RTSP + inference) → Regional (Re-ID, media relay, NETRAM-aligned) → Central (identity correlation, watchlist, RBAC, GIS)"),
    ("GPU sizing", "~20 cameras/GPU (mobile-scale models) → ~4,000 GPU-class edge units at full 80,000-camera build-out"),
    ("Bandwidth math", "Raw video centrally: ~160 Gbps / ~1.7 PB/day — not credible. Structured events instead: ~640 Mbps sustained — three orders of magnitude smaller"),
]
right = [
    ("Storage tiers", "Hot (7–15 days, PostgreSQL/PostGIS) → Warm (90 days–1 year, partitioned/TimescaleDB) → Cold (compliance archive, object storage — not raw video by default)"),
    ("HA / DR & scaling", "Stateless API tier behind a load balancer; stream-manager sharded by camera range; PostgreSQL primary/replica failover; regional outage never blocks central watchlist/RBAC"),
    ("Phased rollout", "Pilot (this submission) → District pilot → Regional rollout (Kafka introduced) → Statewide — same codebase at every phase, not a rebuild"),
]
for i, (title, desc) in enumerate(left):
    y = Inches(1.65) + i * Inches(1.55)
    txt(s, Inches(0.6), y, Inches(5.9), Inches(0.35), title, size=14, color=BLUE_DARK, bold=True)
    txt(s, Inches(0.6), y + Inches(0.4), Inches(5.9), Inches(1.1), desc, size=12, color=INK, line_spacing=1.2)
for i, (title, desc) in enumerate(right):
    y = Inches(1.65) + i * Inches(1.55)
    txt(s, Inches(6.85), y, Inches(5.9), Inches(0.35), title, size=14, color=BLUE_DARK, bold=True)
    txt(s, Inches(6.85), y + Inches(0.4), Inches(5.9), Inches(1.1), desc, size=12, color=INK, line_spacing=1.2)
txt(s, Inches(0.6), Inches(6.6), Inches(12.1), Inches(0.4),
    "Same code, different DATABASE_URL and instance count at every phase — nothing here is a throwaway demo architecture.",
    size=12.5, color=GRAY, italic=True)

# ============================================================ SLIDE 16 — TEST CASE STATUS
s = content_slide("Evaluation Readiness", "Live test case status")
rows2 = [
    ("Onboard ~50 heterogeneous cameras", "Pipeline verified; sandbox connectivity fixed & confirmed — all 30 real cameras reachable", "done"),
    ("Track a designated vehicle by plate", "Core path verified end-to-end", "done"),
    ("Complete timestamped, location-wise route", "Per-camera timeline + geo-temporal OBSERVED/INFERRED reconstruction", "done"),
    ("Cross-reference vs. watchlist", "Own representative watchlist + real-time alert on match", "done"),
    ("Automated real-time alert on match", "Governed alert lifecycle, verified through real HTTP routes with auth", "done"),
    ("Cross-camera continuity when plate unreadable", "Our differentiator — appearance-second identity resolution, retroactive upgrade", "done"),
    ("Real-footage OCR accuracy", "Verified against clean synthetic text only — real government footage unmeasured", "partial"),
]
tbl_l = Inches(0.6); tbl_t = Inches(1.55); tbl_w = Inches(12.1)
col1b, col2b, col3b = Inches(4.2), Inches(6.2), Inches(1.7)
rh2 = Inches(0.62)
box(s, tbl_l, tbl_t, tbl_w, Inches(0.4), fill=NAVY)
txt(s, tbl_l + Inches(0.15), tbl_t + Inches(0.06), col1b, Inches(0.3), "Requirement", size=12, color=WHITE, bold=True)
txt(s, tbl_l + col1b + Inches(0.15), tbl_t + Inches(0.06), col2b, Inches(0.3), "Status detail", size=12, color=WHITE, bold=True)
txt(s, tbl_l + col1b + col2b + Inches(0.1), tbl_t + Inches(0.06), col3b, Inches(0.3), "", size=12, color=WHITE, bold=True)
y = tbl_t + Inches(0.4)
for i, (req, detail, kind) in enumerate(rows2):
    rowfill = LIGHT_GRAY if i % 2 == 0 else WHITE
    box(s, tbl_l, y, tbl_w, rh2, fill=rowfill)
    txt(s, tbl_l + Inches(0.15), y + Inches(0.09), col1b - Inches(0.2), rh2, req, size=11.5, color=NAVY, bold=True, line_spacing=1.05)
    txt(s, tbl_l + col1b + Inches(0.15), y + Inches(0.09), col2b - Inches(0.2), rh2, detail, size=10.8, color=INK, line_spacing=1.05)
    status_chip(s, tbl_l + col1b + col2b + Inches(0.05), y + Inches(0.17), "", kind=kind)
    y += rh2

# ============================================================ SLIDE 17 — OPERATIONAL BENEFITS
s = content_slide("Operational Benefits", "Who this actually helps, and how")
groups2 = [
    ("For investigators", ["One search across every onboarded camera, even when some plate reads fail", "Explainable link trail — see why a sighting was attached, not just that it was", "Purpose-bound, audited queries — defensible in court, not just in a demo"]),
    ("For command / operations", ["Live GIS registry with health-colour-coded cameras and gap analysis", "Governed alert queue — acknowledgement and false-positive dismissal are first-class, auditable actions", "Cross-camera route reconstruction surfaces patterns a single-camera view never would"]),
    ("For governance & compliance", ["Enforced data retention in code, not policy-on-paper", "RBAC and hashed credentials — a database leak doesn't hand out working access", "Deliberate exclusion of face recognition keeps the system inside its narrowest defensible legal claim"]),
]
colw3 = Inches(3.95)
for i, (grp, items) in enumerate(groups2):
    x = Inches(0.6) + i * (colw3 + Inches(0.2))
    c = rrect(s, x, Inches(1.65), colw3, Inches(4.9), fill=LIGHT_GRAY)
    box(s, x, Inches(1.65), colw3, Inches(0.55), fill=BLUE_DARK)
    txt(s, x, Inches(1.79), colw3, Inches(0.35), grp, size=14, color=WHITE, bold=True, align=PP_ALIGN.CENTER)
    bullets(s, x + Inches(0.28), Inches(2.4), colw3 - Inches(0.55), Inches(4.0), items, size=12,
            space_after=16, line_spacing=1.2, bullet_color=BLUE)

# ============================================================ SLIDE 18 — HONEST GAPS
s = content_slide("Honest Gaps", "Stated, not hidden — by design")
gaps = [
    "Face recognition & fingerprint/biometric integration — deliberate DPDP/bias exclusion, not a missing feature",
    "Full 80,000-camera physical ingestion — the control plane is demonstrated to scale independently instead",
    "Real per-vendor VMS federation middleware (Model 3) — a half-built federation bus would be worse than an honest roadmap",
    "WHEP low-latency preview — HLS-via-authenticated-proxy is the working live-view path",
    "Real Indian-plate OCR accuracy — verified on synthetic text only; real government footage is unmeasured",
    "Department-scoped RBAC — single flat role set today; schema already supports the extension",
    "Fine-tuned Indian-specific detector / plate localizer — evaluated (IISc UVH-26, morsetechlab) and documented, not swapped in this build window",
    "Road-network (OSM) routing & predictive next-camera pruning — roadmap; value is at 80k scale, not the 50-camera pilot",
]
bullets(s, Inches(0.6), Inches(1.65), Inches(12.1), Inches(5.0), gaps, size=14, space_after=16,
        bullet_color=AMBER, line_spacing=1.2)

# ============================================================ SLIDE 19 — CLOSING
s = add_slide()
set_bg(s, NAVY)
box(s, 0, Inches(5.85), SLIDE_W, Pt(2.5), fill=BLUE)
txt(s, Inches(0.95), Inches(1.7), Inches(11), Inches(1.0), "Thank you",
    size=52, color=WHITE, bold=True)
txt(s, Inches(0.97), Inches(2.75), Inches(11.2), Inches(1.6),
    "An honest, verified, open-source interoperability layer — built to extend Gujarat's existing\n"
    "CCTV infrastructure, not replace it.",
    size=18, color=RGBColor(0xC7, 0xD3, 0xE3), line_spacing=1.3)
bullets(s, Inches(0.97), Inches(4.35), Inches(11), Inches(1.4), [
    "Technical Proposal (HLD) and Scalability Strategy submitted alongside this presentation",
    "Own-feed and government-feed demonstration videos submitted per §9.3/§9.4",
    "Source available for review — every claim in this deck traces to verified, runnable code",
], size=14, color=RGBColor(0xC7, 0xD3, 0xE3), space_after=10, bullet_color=BLUE)
txt(s, Inches(0.97), Inches(6.05), Inches(8), Inches(0.4),
    "Sentinel — Gujarat Police Innovation Challenge 2026", size=12, color=GRAY)

out_path = r"C:\Users\harsh\Music\Gujarat Police Hackathon Innovation Challenge 2026\Sentinel_Solution_Presentation.pptx"
prs.save(out_path)
print(f"Saved {len(prs.slides.__iter__.__self__._sldIdLst)} slides to {out_path}")
