"""Read-only transport. Credentials are scoped to explicit official origins.

No trading, cancellation, credential creation, approval, or withdrawal methods.
Read-only POST endpoints are allowed explicitly for CLOB batch market data.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
from pathlib import Path
import time
from urllib.parse import urlsplit

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

POLY_GAMMA = "https://gamma-api.polymarket.com"
POLY_CLOB = "https://clob.polymarket.com"
POLY_DATA = "https://data-api.polymarket.com"
KALSHI_PROD = "https://external-api.kalshi.com/trade-api/v2"
KALSHI_DEMO = "https://external-api.demo.kalshi.co/trade-api/v2"
KALSHI_WS = "wss://external-api-ws.kalshi.com/trade-api/ws/v2"


def poly_signature(secret: str, timestamp: str, method: str, path: str, body: str = "") -> str:
    """L2 HMAC: seconds + uppercase method + path (no query) + exact body bytes."""
    key = base64.urlsafe_b64decode(secret)
    message = f"{timestamp}{method.upper()}{urlsplit(path).path}{body}".encode()
    return base64.urlsafe_b64encode(hmac.new(key, message, hashlib.sha256).digest()).decode()


def kalshi_signature(private_key, timestamp: str, method: str, path: str) -> str:
    """RSA-PSS/SHA256 with a SHA256-sized salt; timestamp in milliseconds."""
    message = f"{timestamp}{method.upper()}{urlsplit(path).path}".encode()
    signed = private_key.sign(message, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                                   salt_length=padding.PSS.DIGEST_LENGTH), hashes.SHA256())
    return base64.b64encode(signed).decode()


def poly_headers(method: str, path: str, body: str = "", timestamp: str | None = None):
    timestamp = timestamp or str(int(time.time()))
    return {"POLY_ADDRESS": os.environ["POLYMARKET_SIGNER_ADDRESS"],
            "POLY_API_KEY": os.environ["POLYMARKET_API_KEY"],
            "POLY_PASSPHRASE": os.environ["POLYMARKET_PASSPHRASE"],
            "POLY_TIMESTAMP": timestamp,
            "POLY_SIGNATURE": poly_signature(os.environ["POLYMARKET_SECRET"], timestamp, method, path, body)}


class PolyAuth:
    def __init__(self, key: str, secret: str, passphrase: str, signer: str):
        self.key, self.secret, self.passphrase, self.signer = key, secret, passphrase, signer

    @classmethod
    def from_env(cls):
        return cls(*(os.environ[f"POLYMARKET_{k}"] for k in
                     ("API_KEY", "SECRET", "PASSPHRASE", "SIGNER_ADDRESS")))

    def headers(self, method: str, path: str, timestamp: str | None = None):
        timestamp = timestamp or str(int(time.time()))
        return {"POLY_ADDRESS": self.signer, "POLY_API_KEY": self.key,
                "POLY_PASSPHRASE": self.passphrase, "POLY_TIMESTAMP": timestamp,
                "POLY_SIGNATURE": poly_signature(self.secret, timestamp, method, path)}


class KalshiAuth:
    def __init__(self, *, demo: bool = False):
        prefix = "KALSHI_DEMO" if demo else "KALSHI"
        self.key_id = os.environ[f"{prefix}_API_KEY_ID"]
        self.private_key = serialization.load_pem_private_key(
            Path(os.environ[f"{prefix}_PRIVATE_KEY_PATH"]).read_bytes(), password=None)
        if not isinstance(self.private_key, rsa.RSAPrivateKey):
            raise TypeError("Kalshi requires an RSA private key")

    def headers(self, method: str, path: str, timestamp: str | None = None):
        timestamp = timestamp or str(int(time.time() * 1000))
        return {"KALSHI-ACCESS-KEY": self.key_id, "KALSHI-ACCESS-TIMESTAMP": timestamp,
                "KALSHI-ACCESS-SIGNATURE": kalshi_signature(self.private_key, timestamp, method, path)}


class ReadOnlyClient:
    def __init__(self, *, min_interval: float = 0.18):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "prediction-api-verification/1.0"
        self.min_interval = min_interval
        self._last = 0.0

    def close(self):
        self.session.close()

    def request(self, base: str, path: str, *, params=None, body=None,
                auth: str | PolyAuth | KalshiAuth | None = None, method: str = "GET"):
        allowed = {POLY_GAMMA, POLY_CLOB, POLY_DATA, KALSHI_PROD, KALSHI_DEMO,
                   "https://api.elections.kalshi.com/trade-api/v2",
                   "https://demo-api.kalshi.co/trade-api/v2", "https://polymarket.com"}
        if base not in allowed or not path.startswith("/") or path.startswith("//"):
            raise ValueError("Unapproved origin/path")
        # Some APIs expose state-changing GETs. Keep known ones out of an audit.
        if any(s in path for s in ("/update", "/delete", "/create", "/derive-api-key")):
            raise ValueError("Potentially state-changing endpoint is disabled")
        if method != "GET" and not (method == "POST" and base == POLY_CLOB and path in
                                     {"/books", "/prices", "/midpoints", "/spreads", "/last-trades-prices"}):
            raise ValueError("Only GET and explicitly read-only CLOB batch POSTs are enabled")
        if (auth == "poly" or isinstance(auth, PolyAuth)) and base != POLY_CLOB:
            raise ValueError("Polymarket credentials can only go to the CLOB origin")
        if isinstance(auth, KalshiAuth) and base not in {KALSHI_PROD, KALSHI_DEMO,
                    "https://api.elections.kalshi.com/trade-api/v2", "https://demo-api.kalshi.co/trade-api/v2"}:
            raise ValueError("Kalshi credentials can only go to official API origins")
        delay = self.min_interval - (time.monotonic() - self._last)
        if delay > 0:
            time.sleep(delay)
        url = base + path
        if auth == "poly" or isinstance(auth, PolyAuth):
            if body is not None:
                raise ValueError("Authenticated POST is not supported by this read-only client")
            headers = poly_headers(method, path) if auth == "poly" else auth.headers(method, path)
        elif isinstance(auth, KalshiAuth):
            headers = auth.headers(method, urlsplit(url).path)
        else:
            headers = {}
        self._last = time.monotonic()
        # No automatic retries: each report row corresponds to exactly one attempt.
        # No redirects: authenticated headers must never escape to a different host.
        return self.session.request(method, url, params=params, json=body, headers=headers,
                                    timeout=(10, 25), allow_redirects=False)
