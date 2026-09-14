import { useEffect, useRef, useState } from "react";
import Hls from "hls.js";
import { api, getApiKey } from "../api";

// Plays a camera's feed via our backend's /live/{id}/index.m3u8 proxy
// (see backend/app/api/routes_stream.py) rather than hitting the CDN
// directly — the CDN requires the sandbox access-password session cookie,
// which lives in the backend, not the browser. WHEP (lower-latency WebRTC)
// is not wired up here: it needs a full RTCPeerConnection/SDP client and
// wasn't built this pass — see README's stubbed/gap list. HLS via the proxy
// is the working live-view path.
export default function LiveView({ cameraId }) {
  const videoRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    if (!cameraId || !videoRef.current) return;

    const video = videoRef.current;
    const src = api.hlsUrl(cameraId);
    let hls;

    if (Hls.isSupported()) {
      hls = new Hls({
        maxBufferLength: 10,
        // /live/* is RBAC-gated (routes_stream.py) — hls.js's own fetches
        // for the playlist and every segment need the API key header too,
        // not just the initial <video> element.
        xhrSetup: (xhr) => {
          const key = getApiKey();
          if (key) xhr.setRequestHeader("X-Sentinel-API-Key", key);
        },
      });
      hls.loadSource(src);
      hls.attachMedia(video);
      hls.on(Hls.Events.ERROR, (_evt, data) => {
        if (data.fatal) setError(`stream error: ${data.details}`);
      });
    } else if (video.canPlayType("application/vnd.apple.mpegurl")) {
      // Native Safari HLS cannot send Sentinel's required custom API-key
      // header. Do not assign src and leave an opaque blank player: a
      // signed-URL/cookie auth design is required to support this path.
      setError("Live view requires Chrome, Firefox, or Edge in this environment (Safari native HLS cannot send the required API key).");
    } else {
      setError("this browser cannot play HLS");
    }

    return () => hls?.destroy();
  }, [cameraId]);

  if (!cameraId) {
    return <div className="live-view live-view--empty">Select a camera to view its feed.</div>;
  }

  return (
    <div className="live-view">
      <video ref={videoRef} controls autoPlay muted className="live-view__video" />
      {error && <div className="live-view__error">{error} — feed may be offline or the sandbox session expired.</div>}
    </div>
  );
}
