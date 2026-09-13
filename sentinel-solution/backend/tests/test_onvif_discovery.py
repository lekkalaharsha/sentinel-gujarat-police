"""Regression coverage for streaming/onvif_discovery.py and catalogue.py's
ONVIF-first-with-sandbox-fallback wiring.

No live ONVIF device or network access is available in this environment
(nor does the hackathon sandbox itself expose an ONVIF endpoint — see
HACKATHON_DETAILS.md §13a), so every test here mocks the two network
boundaries (WS-Discovery UDP responses, ONVIF SOAP HTTP responses) and
verifies the real parsing/fallback logic around them — not the ONVIF
protocol conformance of a real camera, which cannot be exercised here.
This mirrors this repo's existing pattern (test_anpr.py tests pure
pattern-matching helpers without a real OCR engine).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.streaming import onvif_discovery as od


PROBE_MATCH_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">
  <e:Body>
    <d:ProbeMatches>
      <d:ProbeMatch>
        <d:XAddrs>http://192.168.1.50/onvif/device_service</d:XAddrs>
      </d:ProbeMatch>
    </d:ProbeMatches>
  </e:Body>
</e:Envelope>"""

GET_CAPABILITIES_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <GetCapabilitiesResponse>
      <Capabilities>
        <tt:Media><tt:XAddr>http://192.168.1.50/onvif/media_service</tt:XAddr></tt:Media>
      </Capabilities>
    </GetCapabilitiesResponse>
  </s:Body>
</s:Envelope>"""

GET_PROFILES_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
  <s:Body>
    <GetProfilesResponse>
      <trt:Profiles token="Profile_1"/>
      <trt:Profiles token="Profile_2"/>
    </GetProfilesResponse>
  </s:Body>
</s:Envelope>"""

GET_STREAM_URI_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <GetStreamUriResponse>
      <MediaUri><tt:Uri>rtsp://192.168.1.50:554/profile1</tt:Uri></MediaUri>
    </GetStreamUriResponse>
  </s:Body>
</s:Envelope>"""


def _mock_response(content: bytes) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.raise_for_status = MagicMock()
    return resp


def test_parse_probe_match_extracts_first_xaddr():
    xaddr = od._parse_probe_match(PROBE_MATCH_XML)
    assert xaddr == "http://192.168.1.50/onvif/device_service"


def test_parse_probe_match_returns_none_for_garbage():
    assert od._parse_probe_match(b"not xml at all") is None


def test_parse_probe_match_ignores_message_with_no_xaddrs():
    empty = b"""<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
                          xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery">
      <e:Body><d:ProbeMatches/></e:Body></e:Envelope>"""
    assert od._parse_probe_match(empty) is None


def test_ws_security_header_contains_digest_nonce_and_created():
    header = od._ws_security_header("admin", "secret")
    assert "<Username>admin</Username>" in header
    assert "PasswordDigest" in header
    assert "<Nonce" in header
    assert "<Created" in header


def test_probe_ws_discovery_survives_a_blocked_socket(monkeypatch):
    """If UDP multicast can't even be sent (no route / blocked, the real
    situation in most CI/sandboxed environments), probing must report
    0 devices, not raise — matches the documented "expected fallback,
    not an error" behavior."""

    class _BoomSocket:
        def setsockopt(self, *a, **kw):
            pass

        def settimeout(self, *a, **kw):
            pass

        def sendto(self, *a, **kw):
            raise OSError("network is unreachable")

        def close(self):
            pass

    monkeypatch.setattr(od.socket, "socket", lambda *a, **kw: _BoomSocket())
    assert od.probe_ws_discovery(timeout_s=0.1) == []


@patch("app.streaming.onvif_discovery.requests.post")
def test_fetch_stream_urls_walks_capabilities_profiles_stream_uri(mock_post):
    mock_post.side_effect = [
        _mock_response(GET_CAPABILITIES_XML),
        _mock_response(GET_PROFILES_XML),
        _mock_response(GET_STREAM_URI_XML),
        _mock_response(GET_STREAM_URI_XML),
    ]
    device = od.OnvifDevice(xaddr="http://192.168.1.50/onvif/device_service")
    urls = od.fetch_stream_urls(device, username=None, password=None)

    assert urls == {
        "Profile_1": "rtsp://192.168.1.50:554/profile1",
        "Profile_2": "rtsp://192.168.1.50:554/profile1",
    }
    # First call hits the device service (GetCapabilities); the remaining
    # three hit the Media service address GetCapabilities actually returned
    # — not the device service again — confirming the two-address handoff.
    assert mock_post.call_args_list[0].args[0] == "http://192.168.1.50/onvif/device_service"
    for call in mock_post.call_args_list[1:]:
        assert call.args[0] == "http://192.168.1.50/onvif/media_service"


@patch("app.streaming.onvif_discovery.requests.post")
def test_fetch_stream_urls_propagates_network_failure(mock_post):
    mock_post.side_effect = ConnectionError("no route to host")
    device = od.OnvifDevice(xaddr="http://192.168.1.50/onvif/device_service")
    with pytest.raises(ConnectionError):
        od.fetch_stream_urls(device, username=None, password=None)


def test_discover_returns_empty_dict_when_no_devices_found(monkeypatch):
    monkeypatch.setattr(od, "probe_ws_discovery", lambda timeout_s: [])
    assert od.discover(probe_timeout_s=0.1) == {}


def test_discover_skips_a_device_that_fails_media_handshake_but_keeps_others(monkeypatch):
    devices = [od.OnvifDevice(xaddr="http://10.0.0.1/onvif"), od.OnvifDevice(xaddr="http://10.0.0.2/onvif")]
    monkeypatch.setattr(od, "probe_ws_discovery", lambda timeout_s: devices)

    def fake_fetch(device, username, password):
        if device.xaddr.endswith(".1/onvif"):
            raise ConnectionError("device dropped mid-handshake")
        return {"Profile_1": "rtsp://10.0.0.2:554/main"}

    monkeypatch.setattr(od, "fetch_stream_urls", fake_fetch)
    cameras = od.discover(probe_timeout_s=0.1)

    assert len(cameras) == 1
    cam = next(iter(cameras.values()))
    assert cam.rtsp_url == "rtsp://10.0.0.2:554/main"
    assert cam.live is True
    assert cam.raw["source"] == "onvif"


def test_discover_builds_one_cameinfo_per_profile_token(monkeypatch):
    monkeypatch.setattr(od, "probe_ws_discovery", lambda timeout_s: [od.OnvifDevice(xaddr="http://10.0.0.5/onvif")])
    monkeypatch.setattr(
        od,
        "fetch_stream_urls",
        lambda device, username, password: {
            "Profile_1": "rtsp://10.0.0.5:554/p1",
            "Profile_2": "rtsp://10.0.0.5:554/p2",
        },
    )
    cameras = od.discover(probe_timeout_s=0.1)
    assert len(cameras) == 2
    assert {c.rtsp_url for c in cameras.values()} == {"rtsp://10.0.0.5:554/p1", "rtsp://10.0.0.5:554/p2"}


# --- catalogue.py's ONVIF-first, sandbox-fallback wiring -------------------


def test_catalogue_refresh_uses_onvif_when_it_finds_cameras(monkeypatch):
    from app import config
    from app.catalogue import CameraInfo, CatalogueClient

    monkeypatch.setattr(config, "ONVIF_DISCOVERY_ENABLED", True)
    client = CatalogueClient(url="http://unused", password="x", email="x@example.com")

    fake_camera = CameraInfo(
        id="onvif-0-Profile_1", location="http://10.0.0.5/onvif", codec=None, live=True,
        rtsp_url="rtsp://10.0.0.5:554/p1", whep_url="", hls_url="", raw={},
    )
    monkeypatch.setattr(client, "_try_onvif_discovery", lambda: {"onvif-0-Profile_1": fake_camera})
    # If ONVIF succeeds, the sandbox HTTP login/refresh path must never run.
    monkeypatch.setattr(client, "_login", lambda: (_ for _ in ()).throw(AssertionError("sandbox login should not be attempted")))

    cameras = client.refresh()
    assert cameras == {"onvif-0-Profile_1": fake_camera}


def test_catalogue_refresh_falls_back_to_sandbox_when_onvif_finds_nothing(monkeypatch):
    from app import config
    from app.catalogue import CatalogueClient

    monkeypatch.setattr(config, "ONVIF_DISCOVERY_ENABLED", True)
    client = CatalogueClient(url="http://unused", password="x", email="x@example.com")
    monkeypatch.setattr(client, "_try_onvif_discovery", lambda: {})
    # No real sandbox reachable here — _login() failing (no credentials
    # reaching a real host) is the expected outcome; the point of this test
    # is that refresh() actually FALLS THROUGH to attempt it, not that the
    # sandbox login itself succeeds.
    login_called = []
    monkeypatch.setattr(client, "_login", lambda: login_called.append(True) or False)

    result = client.refresh()
    assert login_called == [True]
    assert result == {}


def test_catalogue_refresh_skips_onvif_entirely_when_disabled(monkeypatch):
    from app import config
    from app.catalogue import CatalogueClient

    monkeypatch.setattr(config, "ONVIF_DISCOVERY_ENABLED", False)
    client = CatalogueClient(url="http://unused", password="x", email="x@example.com")
    monkeypatch.setattr(
        client, "_try_onvif_discovery", lambda: (_ for _ in ()).throw(AssertionError("ONVIF must not be attempted when disabled"))
    )
    login_called = []
    monkeypatch.setattr(client, "_login", lambda: login_called.append(True) or False)

    client.refresh()
    assert login_called == [True]


def test_catalogue_onvif_discovery_failure_falls_back_not_raises(monkeypatch):
    from app import config
    from app.catalogue import CatalogueClient

    monkeypatch.setattr(config, "ONVIF_DISCOVERY_ENABLED", True)
    client = CatalogueClient(url="http://unused", password="x", email="x@example.com")

    def boom():
        raise RuntimeError("WS-Discovery socket error")

    # _try_onvif_discovery itself is the boundary that must never raise —
    # verify its own internal try/except, not by re-raising past it.
    with patch("app.streaming.onvif_discovery.discover", side_effect=RuntimeError("boom")):
        result = client._try_onvif_discovery()
    assert result == {}


# --- SSRF hardening (found 2026-09-13) ---------------------------------
#
# device.xaddr comes from an unauthenticated UDP multicast ProbeMatch reply,
# and media_xaddr (used for the follow-up GetProfiles/GetStreamUri calls)
# comes from that same untrusted device's own GetCapabilities SOAP
# response. A hostile/compromised "camera" could hand back a URL pointing
# at an internal service (e.g. a cloud metadata endpoint) instead of
# itself — _validate_onvif_address() is the choke point _soap_call() must
# run before ever making the HTTP request.


@pytest.mark.parametrize(
    "xaddr",
    [
        "http://169.254.169.254/latest/meta-data/",  # cloud metadata (link-local)
        "http://127.0.0.1:9999/admin",                # loopback
        "http://[::1]:9999/admin",                    # loopback, IPv6
        "ftp://192.168.1.50/onvif/device_service",    # disallowed scheme
        "not-a-url",                                  # no host at all
    ],
)
def test_validate_onvif_address_rejects_ssrf_targets(xaddr):
    with pytest.raises(od.UntrustedOnvifAddressError):
        od._validate_onvif_address(xaddr)


def test_validate_onvif_address_accepts_private_lan_ip():
    od._validate_onvif_address("http://192.168.1.50/onvif/device_service")  # must not raise


@patch("app.streaming.onvif_discovery.requests.post")
def test_soap_call_rejects_untrusted_xaddr_without_making_a_request(mock_post):
    with pytest.raises(od.UntrustedOnvifAddressError):
        od._soap_call("http://169.254.169.254/", "<body/>", None, None)
    mock_post.assert_not_called()


@patch("app.streaming.onvif_discovery.requests.post")
def test_soap_call_disables_redirects(mock_post):
    mock_post.return_value = MagicMock(content=GET_CAPABILITIES_XML)
    od._soap_call("http://192.168.1.50/onvif/device_service", "<body/>", None, None)
    assert mock_post.call_args.kwargs["allow_redirects"] is False


@patch("app.streaming.onvif_discovery.requests.post")
def test_fetch_stream_urls_rejects_malicious_media_xaddr_from_device_response(mock_post):
    """The device's OWN GetCapabilities response can point media_xaddr
    anywhere — a malicious device redirecting Sentinel to probe its
    internal network must be rejected, not silently followed."""
    malicious_capabilities = b"""<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <GetCapabilitiesResponse>
      <Capabilities>
        <tt:Media><tt:XAddr>http://169.254.169.254/latest/meta-data/</tt:XAddr></tt:Media>
      </Capabilities>
    </GetCapabilitiesResponse>
  </s:Body>
</s:Envelope>"""
    mock_post.return_value = MagicMock(content=malicious_capabilities)
    device = od.OnvifDevice(xaddr="http://192.168.1.50/onvif/device_service")

    with pytest.raises(od.UntrustedOnvifAddressError):
        od.fetch_stream_urls(device, None, None)

    # Only the (trusted) initial GetCapabilities call should have gone out.
    assert mock_post.call_count == 1
