import { useEffect, useState } from "react";
import { api, getApiKey, setApiKey } from "../api";

// RBAC is real on the backend (api/auth.py) — every route requires
// X-Sentinel-API-Key and checks role. This is the one place the frontend
// asks for that key; api.js attaches it to every request automatically
// once set. See main.py's ensure_default_admin_key() for how to get a
// first key: it's logged once at backend startup.
export default function ApiKeyBar() {
  const [key, setKey] = useState(getApiKey());
  const [identity, setIdentity] = useState(null);
  const [error, setError] = useState(null);

  async function checkIdentity() {
    try {
      setIdentity(await api.whoami());
      setError(null);
    } catch (err) {
      setIdentity(null);
      setError(err.message);
    }
  }

  useEffect(() => {
    if (getApiKey()) checkIdentity();
  }, []);

  function save() {
    setApiKey(key.trim());
    checkIdentity();
  }

  return (
    <div className="api-key-bar">
      <input
        type="password"
        placeholder="X-Sentinel-API-Key"
        value={key}
        onChange={(e) => setKey(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && save()}
      />
      <button onClick={save}>Set key</button>
      {identity && (
        <span className="api-key-bar__identity">
          {identity.user_id} · {identity.role}
        </span>
      )}
      {error && <span className="api-key-bar__error">{error}</span>}
    </div>
  );
}
