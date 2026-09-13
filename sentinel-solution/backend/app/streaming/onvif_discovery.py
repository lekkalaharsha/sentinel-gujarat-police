"""ONVIF camera discovery: WS-Discovery + Media GetStreamUri.

Two steps turn "a camera on the network" into "an RTSP URL this pipeline
can consume": WS-Discovery (UDP multicast Probe/ProbeMatch) finds device
service addresses, then Device GetCapabilities -> Media GetProfiles ->
Media GetStreamUri retrieves each device's actual RTSP URL(s).

Implemented as raw UDP multicast + hand-built SOAP/XML rather than a
zeep-based client: this small a protocol surface (one probe, three SOAP
calls) doesn't justify a WSDL-parsing dependency.

Verified only against mocked WS-Discovery/SOAP exchanges
(tests/test_onvif_discovery.py) — no ONVIF-conformant device is reachable
from this environment to test against live.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import ipaddress
import logging
import os
import socket
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
# ProbeMatch/SOAP responses come from untrusted network devices — use
# defusedxml's fromstring() to guard against XXE, not stdlib xml.etree.
# Element/ParseError are the same stdlib types either way (defusedxml
# doesn't subclass them), so importing those directly is safe.
from defusedxml.ElementTree import fromstring as _safe_fromstring
from xml.etree.ElementTree import Element, ParseError

from ..catalogue import CameraInfo

logger = logging.getLogger("sentinel.onvif")

WS_DISCOVERY_MULTICAST_ADDR = "239.255.255.250"
WS_DISCOVERY_PORT = 3702

_NS = {
    "d": "http://schemas.xmlsoap.org/ws/2005/04/discovery",
    "tt": "http://www.onvif.org/ver10/schema",
    "trt": "http://www.onvif.org/ver10/media/wsdl",
}

_PROBE_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<e:Envelope xmlns:e="http://www.w3.org/2003/05/soap-envelope"
            xmlns:w="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <e:Header>
    <w:MessageID>uuid:{message_id}</w:MessageID>
    <w:To e:mustUnderstand="1">urn:schemas-xmlsoap-org:ws:2005:04:discovery</w:To>
    <w:Action e:mustUnderstand="1">http://schemas.xmlsoap.org/ws/2005/04/discovery/Probe</w:Action>
  </e:Header>
  <e:Body>
    <d:Probe>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
    </d:Probe>
  </e:Body>
</e:Envelope>"""

_GET_CAPABILITIES_BODY = (
    '<GetCapabilities xmlns="http://www.onvif.org/ver10/device/wsdl">'
    "<Category>Media</Category></GetCapabilities>"
)
_GET_PROFILES_BODY = '<GetProfiles xmlns="http://www.onvif.org/ver10/media/wsdl"/>'
_GET_STREAM_URI_BODY_TEMPLATE = """<GetStreamUri xmlns="http://www.onvif.org/ver10/media/wsdl">
  <StreamSetup>
    <Stream xmlns="http://www.onvif.org/ver10/schema">RTP-Unicast</Stream>
    <Transport xmlns="http://www.onvif.org/ver10/schema"><Protocol>RTSP</Protocol></Transport>
  </StreamSetup>
  <ProfileToken>{token}</ProfileToken>
</GetStreamUri>"""


@dataclass
class OnvifDevice:
    """One WS-Discovery ProbeMatch result: the device service address."""

    xaddr: str


def _parse_probe_match(data: bytes) -> Optional[str]:
    try:
        root = _safe_fromstring(data)
    except ParseError:
        return None
    xaddrs_el = root.find(".//d:XAddrs", _NS)
    if xaddrs_el is None or not xaddrs_el.text:
        return None
    # XAddrs can be a space-separated list of equivalent addresses — the
    # first is sufficient to start talking to the device.
    return xaddrs_el.text.strip().split()[0]


def probe_ws_discovery(timeout_s: float = 3.0) -> List[OnvifDevice]:
    """Sends one WS-Discovery Probe multicast and collects ProbeMatch
    responses for `timeout_s` seconds. Never raises: a blocked/absent
    multicast route is reported as "0 devices found", same as silence."""
    message_id = str(uuid.uuid4())
    probe = _PROBE_TEMPLATE.format(message_id=message_id).encode("utf-8")

    devices: List[OnvifDevice] = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    try:
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
        sock.settimeout(timeout_s)
        sock.sendto(probe, (WS_DISCOVERY_MULTICAST_ADDR, WS_DISCOVERY_PORT))
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            sock.settimeout(remaining)
            try:
                data, _addr = sock.recvfrom(65535)
            except socket.timeout:
                break
            xaddr = _parse_probe_match(data)
            if xaddr and not any(d.xaddr == xaddr for d in devices):
                devices.append(OnvifDevice(xaddr=xaddr))
    except OSError as exc:
        logger.info(
            "WS-Discovery probe could not be sent (%s) — treating as 0 devices found "
            "(no multicast route, or UDP %d is blocked).",
            exc,
            WS_DISCOVERY_PORT,
        )
    finally:
        sock.close()
    return devices


def _ws_security_header(username: str, password: str) -> str:
    """WS-Security UsernameToken (PasswordDigest) — ONVIF's standard device
    auth: digest = base64(SHA1(nonce || created || password)), with the
    raw nonce and timestamp sent alongside so the device can recompute it
    and compare, per the WS-Security UsernameToken Profile 1.0."""
    nonce = os.urandom(16)
    created = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    digest = base64.b64encode(
        hashlib.sha1(nonce + created.encode("utf-8") + password.encode("utf-8")).digest()
    ).decode("utf-8")
    nonce_b64 = base64.b64encode(nonce).decode("utf-8")
    return f"""<s:Header xmlns:s="http://www.w3.org/2003/05/soap-envelope">
  <Security xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
    <UsernameToken>
      <Username>{username}</Username>
      <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>
      <Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce_b64}</Nonce>
      <Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>
    </UsernameToken>
  </Security>
</s:Header>"""


def _soap_envelope(body: str, security_header: str = "") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">'
        f"{security_header}<s:Body>{body}</s:Body></s:Envelope>"
    )


class UntrustedOnvifAddressError(ValueError):
    """Raised when a device/SOAP-response-supplied address fails SSRF validation."""


def _validate_onvif_address(xaddr: str) -> None:
    """`xaddr` values originate from untrusted network input: WS-Discovery
    ProbeMatch replies are unauthenticated UDP multicast, and the "Media"
    XAddr used for follow-up calls comes from the device's own
    GetCapabilities SOAP response. A hostile or compromised device could
    hand back a URL pointing anywhere reachable from this backend (internal
    admin panels, cloud metadata endpoints, etc.) — this is the classic
    SSRF-via-service-discovery shape, so validate before any request.Post()
    ever touches the value. ONVIF discovery is inherently LAN-scoped, so
    only http(s) to a private/link-local-excluded IPv4/IPv6 literal or
    resolvable hostname is accepted; loopback and link-local (which covers
    the 169.254.169.254 cloud-metadata address) are explicitly rejected.
    """
    parsed = urlparse(xaddr)
    if parsed.scheme not in ("http", "https"):
        raise UntrustedOnvifAddressError(f"rejected ONVIF address with scheme {parsed.scheme!r}: {xaddr!r}")
    host = parsed.hostname
    if not host:
        raise UntrustedOnvifAddressError(f"rejected ONVIF address with no host: {xaddr!r}")
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise UntrustedOnvifAddressError(f"could not resolve ONVIF address host {host!r}: {exc}") from exc
    for addr in addrs:
        ip = ipaddress.ip_address(addr)
        if ip.is_loopback or ip.is_link_local or ip.is_unspecified or ip.is_multicast:
            raise UntrustedOnvifAddressError(
                f"rejected ONVIF address {xaddr!r}: host {host!r} resolves to disallowed address {addr}"
            )


def _soap_call(
    xaddr: str, body: str, username: Optional[str], password: Optional[str], timeout_s: float = 5.0
) -> Element:
    _validate_onvif_address(xaddr)
    header = _ws_security_header(username, password) if username and password else ""
    envelope = _soap_envelope(body, header)
    resp = requests.post(
        xaddr,
        data=envelope.encode("utf-8"),
        headers={"Content-Type": "application/soap+xml; charset=utf-8"},
        timeout=timeout_s,
        # A malicious/compromised device must not be able to redirect this
        # backend to an arbitrary internal URL via a 30x SOAP response.
        allow_redirects=False,
    )
    resp.raise_for_status()
    return _safe_fromstring(resp.content)


def fetch_stream_urls(
    device: OnvifDevice, username: Optional[str], password: Optional[str]
) -> Dict[str, str]:
    """GetCapabilities (Media service address, often different from the
    device service) -> GetProfiles -> GetStreamUri per profile. Returns
    {profile_token: rtsp_url}. Raises on any SOAP/network failure — the
    caller decides how to fall back."""
    caps_root = _soap_call(device.xaddr, _GET_CAPABILITIES_BODY, username, password)
    media_xaddr_el = caps_root.find(".//tt:Media/tt:XAddr", _NS)
    media_xaddr = (
        media_xaddr_el.text.strip() if media_xaddr_el is not None and media_xaddr_el.text else device.xaddr
    )

    profiles_root = _soap_call(media_xaddr, _GET_PROFILES_BODY, username, password)
    tokens = [
        p.get("token") for p in profiles_root.findall(".//trt:Profiles", _NS) if p.get("token")
    ]

    urls: Dict[str, str] = {}
    for token in tokens:
        uri_root = _soap_call(
            media_xaddr, _GET_STREAM_URI_BODY_TEMPLATE.format(token=token), username, password
        )
        uri_el = uri_root.find(".//tt:Uri", _NS)
        if uri_el is not None and uri_el.text:
            urls[token] = uri_el.text.strip()
    return urls


def discover(
    username: Optional[str] = None,
    password: Optional[str] = None,
    probe_timeout_s: float = 3.0,
) -> Dict[str, CameraInfo]:
    """WS-Discovery probe, then Media GetStreamUri against every device
    that answers. Returns an empty dict, never raises, if no device
    responds or every device fails its Media handshake — the caller
    (catalogue.py) treats that as "fall back to the sandbox catalogue"."""
    devices = probe_ws_discovery(probe_timeout_s)
    if not devices:
        logger.info("ONVIF WS-Discovery found no devices (probed %.1fs).", probe_timeout_s)
        return {}

    cameras: Dict[str, CameraInfo] = {}
    for index, device in enumerate(devices):
        try:
            urls = fetch_stream_urls(device, username, password)
        except Exception as exc:  # noqa: BLE001 — one unresponsive device must not block the rest
            logger.warning(
                "ONVIF device at %s did not complete the Media GetStreamUri handshake (%s) — skipping it.",
                device.xaddr,
                exc,
            )
            continue
        for token, rtsp_url in urls.items():
            cam_id = f"onvif-{index}-{token}"
            cameras[cam_id] = CameraInfo(
                id=cam_id,
                location=device.xaddr,
                codec=None,
                live=True,
                rtsp_url=rtsp_url,
                whep_url="",
                hls_url="",
                raw={"xaddr": device.xaddr, "profile_token": token, "source": "onvif"},
            )

    logger.info("ONVIF discovery: %d device(s) responded, %d stream(s) resolved.", len(devices), len(cameras))
    return cameras
