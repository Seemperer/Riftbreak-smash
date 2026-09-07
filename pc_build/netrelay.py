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

BROKERS = [("broker.emqx.io", 1883), ("test.mosquitto.org", 1883)]
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
        for host, port in BROKERS:
            try:
                c = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
                c.reconnect_delay_set(1, 4)
                c.on_message = self._on_message
                c.connect(host, port, timeout)
                c.subscribe(self.sub, qos=1)
                # NOTE: no loop_start() — pump() drives client.loop() on this
                # thread only. Mixing both corrupts the stream.
                self.client = c
                self.broker = f"{host}:{port}"
                return ""
            except Exception as e:
                errs.append(f"{host}: {str(e)[:50]}")
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
