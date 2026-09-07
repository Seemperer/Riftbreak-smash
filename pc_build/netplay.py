"""Host-authoritative online play (LAN, TCP, stdlib only).

Architecture: the HOST runs the full simulation. The GUEST sends inputs
every frame and renders state snapshots (20Hz) with local cosmetic fx.
No determinism required; works over LAN / ZeroTier / Hamachi.
"""
import socket
import json

PORT = 7001
SNAP_EVERY = 3  # frames between snapshots (60fps -> 20Hz)


def dumps(o):
    return (json.dumps(o, separators=(",", ":")) + "\n").encode()


class Peer:
    """Line-delimited JSON over a non-blocking socket. Never raises."""

    def __init__(self, sock):
        try:
            sock.setblocking(False)
        except Exception:
            pass
        self.sock = sock
        self.buf = b""
        self.out = b""
        self.dead = False

    def send(self, obj):
        if self.dead:
            return
        try:
            self.out += dumps(obj)
        except Exception:
            self.dead = True

    def pump(self):
        msgs = []
        if self.dead:
            return msgs
        if self.out:
            try:
                n = self.sock.send(self.out)
                self.out = self.out[n:]
            except BlockingIOError:
                pass
            except Exception:
                self.dead = True
                return msgs
        try:
            while True:
                try:
                    chunk = self.sock.recv(65536)
                except BlockingIOError:
                    break
                if not chunk:
                    self.dead = True
                    break
                self.buf += chunk
                if len(self.buf) > 1000000:
                    self.dead = True
                    self.buf = b""
                    break
        except Exception:
            self.dead = True
        while b"\n" in self.buf:
            line, self.buf = self.buf.split(b"\n", 1)
            if not line.strip():
                continue
            if len(line) > 200000:
                continue
            try:
                m = json.loads(line.decode("utf-8", "errors"))
            except Exception:
                continue
            if isinstance(m, dict) and "t" in m:
                msgs.append(m)
        return msgs

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.dead = True


def host_socket(port=PORT):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(1)
    s.setblocking(False)
    return s


def local_ip():
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def r2(v):
    try:
        return round(float(v), 2)
    except Exception:
        return 0


def fighter_state(f):
    a = f.atk
    return {
        "cid": f.cid, "x": r2(f.x), "y": r2(f.y), "vx": r2(f.vx), "vy": r2(f.vy),
        "facing": f.facing, "pct": r2(f.pct), "stocks": f.stocks, "jumps": f.jumps,
        "shield": r2(f.shield_hp), "ult": r2(f.ult), "combo": f.combo,
        "state": f.state, "charge": r2(f.charge),
        "atk": None if not a else {"kind": a["kind"], "t": r2(a["t"]), "dur": a["dur"],
                                   "md": {k: (r2(v) if isinstance(v, float) else v)
                                          for k, v in a["md"].items()}},
        "shielding": bool(f.shielding), "invuln": r2(f.invuln), "helpless": bool(f.helpless),
        "counter": r2(f.counter), "armor": r2(f.armor), "burn": r2(f.burn), "slow": r2(f.slow),
        "ground": bool(f.on_ground), "mv": f.move_dir, "dash": r2(f.dash_t),
        "rot": r2(f.rot), "sx": r2(f.sx), "sy": r2(f.sy), "flash": r2(f.flash),
        "star": r2(f.star_t), "hammer": r2(f.hammer_t), "fuse": r2(f.fuse),
        "maxp": r2(f.max_pct), "pop": r2(f.pop),
    }


def proj_state(p, owner_idx):
    return {"o": owner_idx, "x": r2(p.x), "y": r2(p.y), "vx": r2(p.vx), "vy": r2(p.vy),
            "dmg": p.dmg, "kb": p.kb, "kind": p.kind, "color": list(p.color),
            "size": p.size, "life": r2(p.life)}


def ring_state(r):
    return {"x": r2(r.x), "y": r2(r.y), "r": r2(r.r), "color": list(r.color),
            "life": r2(r.life), "max": r2(r.max), "w": r2(r.width)}


def slash_state(s):
    return {"x": r2(s.x), "y": r2(s.y), "facing": s.facing, "rng": r2(s.rng),
            "hi": r2(s.hi), "color": list(s.color), "life": r2(s.life),
            "max": r2(s.max), "spin": bool(s.spin)}


def drop_state(d):
    return {"kind": d["kind"], "x": r2(d["x"]), "y": r2(d["y"]), "t": r2(d["t"]),
            "life": r2(d["life"])}
