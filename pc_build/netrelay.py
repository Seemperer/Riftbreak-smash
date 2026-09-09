"""Internet play without port forwarding: room-code matchmaking over public MQTT.

Same Peer interface as netplay.Peer (send / pump / dead / close), so all
host/guest game logic is transport-agnostic. Host publishes snapshots,
guest publishes inputs; topics isolate each room.
"""
import json
import random
import string

try:
    import paho.mqtt.client as mqtt
except Exception:
    mqtt = None

# Tried in order. Raw MQTT (1883) is fastest where allowed; plain-WebSocket
# entries (8083/8080) look like normal web traffic and pass through school
# firewalls that block 1883. Same plaintext privacy as before — no accounts,
# no secrets, just throwaway room codes and game positions.
ENDPOINTS = [
    # (host, port, transport, ws_path)
    ("broker.emqx.io", 1883, "tcp", ""),
    ("test.mosquitto.org", 1883, "tcp", ""),
    ("broker.emqx.io", 8083, "websockets", "/mqtt"),
    ("test.mosquitto.org", 8080, "websockets", "/mqtt"),
]
# Back-compat alias (host, port) for anything iterating BROKERS.
BROKERS = [(h, p) for h, p, _, _ in ENDPOINTS]
TOPIC_ROOT = "riftbreak/v1"
CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def available():
    return mqtt is not None


def make_code(n=5):
    return "".join(random.choice(CODE_ALPHABET) for _ in range(n))


def _decode(payload):
    try:
        m = json.loads(bytes(payload).decode("utf-8", "errors"))
    except Exception:
        return None
    if isinstance(m, dict) and "t" in m:
        return m
    return None


def _reachable(host, port, timeout=3.0):
    """Quick TCP probe so a firewalled endpoint fails fast instead of hanging."""
    import socket as _socket
    try:
        s = _socket.create_connection((host, port), timeout)
        try:
            s.close()
        except Exception:
            pass
        return True
    except Exception:
        return False


class RelayPeer:
    """Drop-in replacement for netplay.Peer over MQTT topics."""

    def __init__(self, code, role):
        # role "host": sub guest->host, pub host->guest (and vice versa)
        self.code = code
        self.role = role
        self.dead = False
        self.inbox = []
        self.out = []
        self.client = None
        if role == "host":
            self.sub = f"{TOPIC_ROOT}/{code}/g2h"
            self.pub = f"{TOPIC_ROOT}/{code}/h2g"
        else:
            self.sub = f"{TOPIC_ROOT}/{code}/h2g"
            self.pub = f"{TOPIC_ROOT}/{code}/g2h"

    def connect(self, timeout=8):
        if mqtt is None:
            return "need: pip install paho-mqtt"
        errs = []
        for host, port, transport, path in ENDPOINTS:
            # Bound each attempt: firewalled ports hang a raw connect for ages.
            if not _reachable(host, port, 3.0):
                errs.append(f"{host}:{port}: unreachable")
                continue
            try:
                c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, transport=transport)
                if transport == "websockets":
                    c.ws_set_options(path=path or "/mqtt")
                c.reconnect_delay_set(1, 4)
                c.on_message = self._on_message
                c.connect(host, port, timeout)
                c.subscribe(self.sub, qos=1)
                # NOTE: no loop_start() — pump() drives client.loop() on this
                # thread only. Mixing both corrupts the stream.
                self.client = c
                tag = "ws" if transport == "websockets" else "mqtt"
                self.broker = f"{host}:{port}({tag})"
                return ""
            except Exception as e:
                errs.append(f"{host}:{port}: {str(e)[:50]}")
        return "no broker reachable (" + "; ".join(errs) + ")"

    def _on_message(self, client, userdata, msg):
        try:
            if len(msg.payload) > 200000:
                return
            m = _decode(msg.payload)
            if m is not None:
                self.inbox.append(m)
                if len(self.inbox) > 200:
                    self.inbox = self.inbox[-200:]
        except Exception:
            pass

    # qos1 for handshake/control (hello/pick/bye), qos0 for hot-path
    # snaps/inputs where freshness beats reliability.
    _QOS1_TYPES = {"hello", "pick", "bye", "ping"}

    def send(self, obj):
        if self.dead or self.client is None:
            return
        try:
            data = json.dumps(obj, separators=(",", ":")).encode()
        except Exception:
            return
        if len(data) > 200000:
            return
        try:
            qos = 1 if obj.get("t") in self._QOS1_TYPES else 0
        except Exception:
            qos = 0
        self.out.append((qos, data))
        if len(self.out) > 200:
            self.out = self.out[-200:]

    def pump(self):
        msgs = []
        if self.dead:
            return msgs
        if self.client is None:
            return msgs
        try:
            self.client.loop(timeout=0.01)
        except Exception:
            pass
        while self.out:
            qos, data = self.out.pop(0)
            try:
                self.client.publish(self.pub, data, qos=qos)
            except Exception:
                self.out.insert(0, (qos, data))
                break
        try:
            self.client.loop(timeout=0)
        except Exception:
            pass
        while self.inbox:
            msgs.append(self.inbox.pop(0))
        return msgs

    def close(self):
        try:
            if self.client is not None:
                try:
                    self.client.disconnect()
                except Exception:
                    pass
        except Exception:
            pass
        self.client = None
        self.dead = True
