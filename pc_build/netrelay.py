"""Secure Internet Rooms for Riftbreak Smash (real-time WebSocket, no MQTT).

Flow:
  1. Host calls create_room() -> service reserves an 8-char room (Redis-backed).
  2. Service returns {room, ticket, role, relayUrl}.
  3. Both sides open a TLS WebSocket to relayUrl and auth with the ticket.
  4. Host stays authoritative: host sends state snapshots (~20Hz),
     guest sends inputs every frame. Same Peer interface as netplay.py,
     so LAN and Internet share game logic.

Works across different homes / different Wi-Fi because game traffic is
relayed through the server — no port forwarding, no same-LAN requirement.
Transport is raw WebSocket JSON (real-time), not MQTT.
"""
import json
import os
import queue
import sys
import threading
import urllib.error
import urllib.request

try:
    import websocket
except Exception:
    websocket = None


DEFAULT_SERVICE_URL = "https://riftbreak-smash.vercel.app"
MAX_MESSAGE_BYTES = 48 * 1024


def _candidate_bases():
    try:
        if getattr(sys, "frozen", False):
            yield os.path.dirname(sys.executable)
    except Exception:
        pass
    try:
        yield os.path.dirname(os.path.abspath(__file__))
    except Exception:
        pass
    try:
        yield os.getcwd()
    except Exception:
        pass


def service_url():
    """Resolve the room service URL.

    Priority: env RIFTBREAK_RELAY_URL > relay_url.txt next to the .exe >
    relay_url.txt next to source > built-in default. This is what makes a
    downloaded .exe work without the friend setting env vars: ship a
    relay_url.txt with the exe, or leave the default deployed service URL.
    """
    env = (os.environ.get("RIFTBREAK_RELAY_URL") or "").strip().rstrip("/")
    if env:
        return env
    for base in _candidate_bases():
        try:
            path = os.path.join(base, "relay_url.txt")
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as fh:
                    value = fh.read().strip().rstrip("/")
                if value.startswith("http://") or value.startswith("https://"):
                    return value
        except Exception:
            continue
    return DEFAULT_SERVICE_URL


def available():
    return websocket is not None


def _friendly_http_error(status, body_text):
    try:
        result = json.loads(body_text or "")
        msg = str(result.get("error", "")).strip()
    except Exception:
        msg = ""
    if status == 503 and "not been configured" in msg:
        return ("online rooms are offline: the server has no REDIS_URL set. "
                "Host must set REDIS_URL (Upstash) on the relay service")
    if msg:
        return msg[:140]
    if status == 404:
        return "room not found or expired — check the 8-character code"
    if status == 409:
        return "room is already full"
    if status == 400:
        return "bad room request — update both players to the same build"
    return "online rooms are unavailable (HTTP %s)" % status


def _request(payload, timeout=10):
    base = service_url()
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        base + "/api/rooms", data=data,
        headers={"Content-Type": "application/json",
                 "User-Agent": "RiftbreakSmash/1"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
        try:
            result = json.loads(raw)
        except Exception:
            return None, "online service sent an invalid response"
    except urllib.error.HTTPError as error:
        try:
            body = error.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        return None, _friendly_http_error(getattr(error, "code", 0) or 0, body)[:140]
    except Exception as error:
        text = str(error)
        if "NameResolution" in type(error).__name__ or "getaddrinfo" in text:
            return None, "could not reach online service: check internet/DNS"
        if "timed out" in text.lower():
            return None, "online service timed out — try again"
        return None, ("could not reach online service: " + text)[:140]
    if not isinstance(result, dict) or not result.get("room") or not result.get("ticket") or not result.get("relayUrl"):
        return None, "online service sent an invalid response"
    return result, ""


def create_room():
    return _request({"op": "create"})


def join_room(code):
    cleaned = "".join(ch for ch in str(code).upper() if ch.isalnum())
    return _request({"op": "join", "room": cleaned})


class RelayPeer:
    """A reconnecting, non-blocking Peer backed by the owned WebSocket relay."""

    def __init__(self, reservation):
        self.code = reservation["room"]
        self.role = reservation["role"]
        self.ticket = reservation["ticket"]
        self.url = reservation["relayUrl"]
        self.dead = False
        self.inbox = queue.Queue(maxsize=240)
        self.outbox = queue.Queue(maxsize=240)
        self._ready = threading.Event()
        self._closed = threading.Event()
        self._socket = None
        self._lock = threading.Lock()
        self._last_error = ""
        self._thread = None

    def connect(self, timeout=10):
        if websocket is None:
            # In the frozen .exe this means the build missed websocket-client.
            if getattr(sys, "frozen", False):
                return "online support is missing — reinstall the game"
            return "need: pip install websocket-client"
        self._thread = threading.Thread(target=self._run, name="riftbreak-relay", daemon=True)
        self._thread.start()
        if self._ready.wait(timeout):
            return ""
        self.close()
        return self._last_error or "online service did not respond — try again"

    def _run(self):
        delay = 0.35
        while not self._closed.is_set():
            self._ready.clear()
            app = websocket.WebSocketApp(self.url, on_open=self._on_open,
                                         on_message=self._on_message, on_error=self._on_error,
                                         on_close=self._on_close)
            with self._lock:
                self._socket = app
            try:
                # Older websocket-client versions reject skip_utf8_validation.
                try:
                    app.run_forever(ping_interval=20, ping_timeout=8,
                                    skip_utf8_validation=True)
                except TypeError:
                    app.run_forever(ping_interval=20, ping_timeout=8)
            except Exception as error:
                if not self._last_error:
                    self._last_error = str(error)[:140]
            with self._lock:
                if self._socket is app:
                    self._socket = None
            if self._closed.is_set():
                break
            # Serverless relays recycle long-lived sockets. Reusing the signed
            # ticket makes a reconnect invisible inside a normal match.
            self._closed.wait(delay)
            delay = min(3.0, delay * 1.8)

    def _on_open(self, app):
        try:
            app.send(json.dumps({"t": "_auth", "ticket": self.ticket}, separators=(",", ":")))
        except Exception as error:
            self._last_error = str(error)[:140]

    def _on_message(self, _, raw):
        if isinstance(raw, bytes):
            try:
                raw = raw.decode("utf-8")
            except Exception:
                raw = raw.decode("utf-8", "replace")
        if len(raw.encode("utf-8", "ignore")) > MAX_MESSAGE_BYTES:
            return
        try:
            message = json.loads(raw)
        except Exception:
            return
        if not isinstance(message, dict):
            return
        if message.get("t") == "_ready":
            if message.get("role") == self.role:
                self._last_error = ""
                self._ready.set()
            return
        if message.get("t") == "_error":
            self._last_error = str(message.get("message", "online service rejected the connection"))[:140]
            return
        if "t" not in message:
            return
        try:
            self.inbox.put_nowait(message)
        except queue.Full:
            try:
                self.inbox.get_nowait()
                self.inbox.put_nowait(message)
            except Exception:
                pass

    def _on_error(self, _, error):
        if error and not self._ready.is_set():
            self._last_error = str(error)[:140]

    def _on_close(self, _, status, message):
        if not self._closed.is_set() and not self._ready.is_set():
            if status not in (None, 1000):
                self._last_error = str(message or "connection closed")[:140]

    def send(self, obj):
        if self.dead or not isinstance(obj, dict):
            return
        try:
            raw = json.dumps(obj, separators=(",", ":"))
        except Exception:
            return
        if len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
            return
        try:
            self.outbox.put_nowait(raw)
        except queue.Full:
            try:
                self.outbox.get_nowait()
                self.outbox.put_nowait(raw)
            except Exception:
                pass

    def pump(self):
        if self.dead:
            return []
        with self._lock:
            app = self._socket
        if app is not None and self._ready.is_set():
            while True:
                try:
                    app.send(self.outbox.get_nowait())
                except queue.Empty:
                    break
                except Exception:
                    break
        messages = []
        while True:
            try:
                messages.append(self.inbox.get_nowait())
            except queue.Empty:
                break
        return messages

    def close(self):
        self.dead = True
        self._closed.set()
        with self._lock:
            app = self._socket
        if app is not None:
            try:
                app.close()
            except Exception:
                pass
