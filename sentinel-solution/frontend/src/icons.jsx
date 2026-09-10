// Minimal inline SVG icon set shared across the sidebar/KPI cards — no
// icon-font/library dependency, kept tiny and consistent (stroke, 24x24 viewBox).
const base = { fill: "none", stroke: "currentColor", strokeWidth: 2 };

export const IconGrid = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>
);
export const IconMap = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M9 20l-6-3V4l6 3 6-3 6 3v13l-6-3-6 3z"/><path d="M9 4v13M15 7v13"/></svg>
);
export const IconGraph = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><circle cx="6" cy="6" r="2.5"/><circle cx="18" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><circle cx="18" cy="18" r="2.5"/><path d="M8.2 6h7.6M6 8.2v7.6M18 8.2v7.6M8.2 18h7.6"/></svg>
);
export const IconCar = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M3 12l1.5-5A2 2 0 0 1 6.4 5.5h11.2A2 2 0 0 1 19.5 7L21 12v6a1 1 0 0 1-1 1h-1a1 1 0 0 1-1-1v-1H6v1a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z"/><circle cx="7.5" cy="15.5" r="1.5"/><circle cx="16.5" cy="15.5" r="1.5"/></svg>
);
export const IconCamera = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><rect x="2" y="6" width="15" height="12" rx="2"/><path d="M17 10l5-3v10l-5-3"/></svg>
);
export const IconAlert = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M12 3l9 16H3l9-16z"/><path d="M12 10v4M12 17.5v.01"/></svg>
);
export const IconEye = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>
);
export const IconSearch = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3" strokeLinecap="round"/></svg>
);
export const IconFolder = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M4 4h16v13H8l-4 4V4z"/></svg>
);
export const IconEvidence = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><rect x="4" y="3" width="16" height="18" rx="1.5"/><path d="M8 8h8M8 12h8M8 16h5"/></svg>
);
export const IconReport = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M6 3h9l5 5v13H6z"/><path d="M15 3v5h5"/></svg>
);
export const IconPulse = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M3 12h4l2 7 4-14 2 7h6"/></svg>
);
export const IconLayers = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><rect x="9" y="3" width="6" height="6" rx="1"/><rect x="3" y="15" width="6" height="6" rx="1"/><rect x="15" y="15" width="6" height="6" rx="1"/><path d="M12 9v3M12 12H6v3M12 12h6v3"/></svg>
);
export const IconSettings = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1 1.55V21a2 2 0 1 1-4 0v-.09A1.7 1.7 0 0 0 9 19.36a1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06A1.7 1.7 0 0 0 4.64 15a1.7 1.7 0 0 0-1.55-1H3a2 2 0 1 1 0-4h.09A1.7 1.7 0 0 0 4.64 9a1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.7 1.7 0 0 0 9 4.64a1.7 1.7 0 0 0 1-1.55V3a2 2 0 1 1 4 0v.09a1.7 1.7 0 0 0 1 1.55 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06A1.7 1.7 0 0 0 19.36 9a1.7 1.7 0 0 0 1.55 1H21a2 2 0 1 1 0 4h-.09a1.7 1.7 0 0 0-1.51 1z"/></svg>
);
export const IconBell = (p) => (
  <svg viewBox="0 0 24 24" {...base} {...p}><path d="M6 8a6 6 0 0 1 12 0c0 3 1 4.5 2 6H4c1-1.5 2-3 2-6z"/><path d="M9.5 19a2.5 2.5 0 0 0 5 0"/></svg>
);
export const IconShield = (p) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2" {...p}><path d="M12 3l7 3v6c0 5-3 8-7 9-4-1-7-4-7-9V6l7-3z"/><path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round"/></svg>
);
export const IconVehicleSide = (p) => (
  <svg viewBox="0 0 64 32" fill="none" stroke="currentColor" strokeWidth="2" strokeLinejoin="round" {...p}>
    <path d="M4 24 L8 14 Q10 10 16 10 H26 L32 4 H44 Q50 4 52 10 L56 14 H60 V24" />
    <circle cx="18" cy="26" r="4" fill="currentColor" stroke="none" />
    <circle cx="46" cy="26" r="4" fill="currentColor" stroke="none" />
  </svg>
);
