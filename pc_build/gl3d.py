"""GL-powered low-poly 3D stage renderer (ModernGL + numpy, optional).

Renders each arena as real 3D geometry (lit islands, shader sky, animated
water/lava, bloom) to an offscreen buffer and hands back raw RGB bytes for
pygame to blit.  Everything here is presentation-only: collision, physics,
fighters and HUD stay exactly as they are.

If moderngl/numpy/the GPU context is unavailable, import still succeeds with
AVAILABLE = False and the game keeps its software renderer.
"""
import math

try:
    import moderngl
    import numpy as np
    _IMPORTS_OK = True
except Exception:
    moderngl = None
    np = None
    _IMPORTS_OK = False

AVAILABLE = _IMPORTS_OK

W, H = 960, 540

# ---------------------------------------------------------------- shaders

SKY_VERT = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = in_pos * 0.5 + 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

SKY_FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_col;
uniform vec3 topC, midC, botC;
uniform vec2 sunDir;      // direction TO sun in uv space (y up)
uniform vec3 sunC;
uniform float sunSize, sunI;
uniform float starAmt, time;
uniform vec3 aurC;
uniform float auroraAmt;
uniform float vortexAmt;
uniform vec3 vorC1, vorC2;
uniform float cloudAmt;
uniform vec3 cloudC;

float hash21(vec2 p) {
    p = fract(p * vec2(234.34, 435.345));
    p += dot(p, p + 34.23);
    return fract(p.x * p.y);
}

void main() {
    vec2 uv = v_uv;
    vec2 p = uv - vec2(0.5, 0.42);
    vec3 midW = midC;
    vec3 botW = botC;
    // rift vortex swirl
    if (vortexAmt > 0.001) {
        float r = length(p * vec2(1.0, 1.6));
        float a = atan(p.y * 1.6, p.x);
        float sw = vortexAmt * (2.2 / (0.25 + r)) + time * 0.35 * vortexAmt;
        float bands = sin(a * 3.0 + sw + r * 9.0) * 0.5 + 0.5;
        vec3 vc = mix(vorC1, vorC2, bands);
        float vm = smoothstep(0.85, 0.15, r) * vortexAmt;
        midW = mix(midW, vc, vm * 0.85);
        botW = mix(botW, vorC1 * 0.5, vm * 0.7);
    }
    // vertical gradient sky
    vec3 col = mix(botW, midW, smoothstep(0.0, 0.55, uv.y));
    col = mix(col, topC, smoothstep(0.5, 1.0, uv.y));
    // soft horizontal cloud bands
    if (cloudAmt > 0.001) {
        float cl = sin(uv.x * 14.0 + time * 0.10 + sin(uv.y * 22.0 + time * 0.07) * 1.4);
        cl = smoothstep(0.55, 0.95, cl) * smoothstep(0.15, 0.45, uv.y)
             * smoothstep(0.95, 0.6, uv.y);
        col = mix(col, cloudC, cl * cloudAmt * 0.5);
    }
    // sun / moon disc + halo
    vec2 sd = normalize(sunDir);
    float d = length((uv - vec2(0.5, 0.5)) - sd * 0.30);
    float disc = smoothstep(sunSize, sunSize * 0.82, d);
    float halo = pow(max(0.0, 1.0 - d * 1.6), 3.0);
    col += sunC * (disc * sunI + halo * 0.35 * sunI);
    // aurora ribbons
    if (auroraAmt > 0.001) {
        for (int i = 0; i < 2; i++) {
            float fi = float(i);
            float yy = 0.62 + fi * 0.13
                + sin(uv.x * 6.0 + time * (0.4 + fi * 0.23) + fi * 2.0) * 0.045;
            float band = smoothstep(0.055, 0.0, abs(uv.y - yy));
            col += aurC * band * auroraAmt * (0.55 - fi * 0.18)
                 * (0.7 + 0.3 * sin(time * 1.3 + uv.x * 9.0 + fi * 3.0));
        }
    }
    // hash starfield (upper sky, hidden near sun)
    if (starAmt > 0.001) {
        vec2 g = uv * vec2(160.0, 90.0);
        vec2 cell = floor(g);
        float h = hash21(cell);
        if (h > 0.978) {
            vec2 sp = fract(g) - 0.5;
            float tw = 0.5 + 0.5 * sin(time * (2.0 + h * 4.0) + h * 40.0);
            float st = smoothstep(0.28, 0.0, length(sp)) * tw;
            st *= smoothstep(0.35, 0.6, uv.y) * (1.0 - disc);
            col += vec3(0.9, 0.93, 1.0) * st * starAmt;
        }
    }
    // dither against banding
    col += (hash21(uv * 913.7 + time) - 0.5) * 0.012;
    f_col = vec4(col, 1.0);
}
"""

TEX_SKY_VERT = """
#version 330
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

TEX_SKY_FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_col;
uniform sampler2D tex;
uniform float dim;
uniform vec2 uvScale;
uniform vec2 uvOff;
void main() {
    vec3 c = texture(tex, v_uv * uvScale + uvOff).rgb * dim;
    f_col = vec4(c, 1.0);
}
"""

GEO_VERT = """
#version 330
in vec3 in_pos;
in vec3 in_nrm;
in vec3 in_col;
in float in_emit;
out vec3 v_col;
out vec3 v_nrm;
out vec3 v_wp;
out float v_emit;
uniform mat4 mvp;
uniform mat4 model;
void main() {
    vec4 wp = model * vec4(in_pos, 1.0);
    v_wp = wp.xyz;
    v_nrm = mat3(model) * in_nrm;
    v_col = in_col;
    v_emit = in_emit;
    gl_Position = mvp * vec4(in_pos, 1.0);
}
"""

GEO_FRAG = """
#version 330
in vec3 v_col;
in vec3 v_nrm;
in vec3 v_wp;
in float v_emit;
out vec4 f_col;
uniform vec3 lightDir, lightCol, ambC, camPos, fogC;
uniform vec2 fogNF;
uniform float specAmt, emitBoost;
void main() {
    // faceforward: builders use mixed winding, so always light the
    // visible side of every face (no culling anywhere in the scene).
    // I = incident vector INTO the surface (-V): keeps normals that
    // already face the camera, flips the rest.
    vec3 V = normalize(camPos - v_wp);
    vec3 N = faceforward(normalize(v_nrm), -V, normalize(v_nrm));
    vec3 L = normalize(lightDir);
    float diff = max(dot(N, L), 0.0);
    // wrap lighting so shadow sides are never pitch black
    diff = diff * 0.75 + 0.25 * max(dot(N, normalize(vec3(-L.x, 0.35, -L.z))), 0.0);
    vec3 hv = normalize(L + V);
    float spec = pow(max(dot(N, hv), 0.0), 28.0) * specAmt;
    vec3 col = v_col * (ambC + lightCol * diff) + lightCol * spec;
    col += v_col * v_emit * emitBoost;
    float dist = length(camPos - v_wp);
    float f = smoothstep(fogNF.x, fogNF.y, dist);
    col = mix(col, fogC, f);
    f_col = vec4(col, 1.0);
}
"""

SCROLL_VERT = """
#version 330
in vec3 in_pos;
in vec2 in_uv;
out vec2 v_uv;
out vec3 v_wp;
uniform mat4 mvp;
uniform mat4 model;
void main() {
    vec4 wp = model * vec4(in_pos, 1.0);
    v_wp = wp.xyz;
    v_uv = in_uv;
    gl_Position = mvp * vec4(in_pos, 1.0);
}
"""

SCROLL_FRAG = """
#version 330
in vec2 v_uv;
in vec3 v_wp;
out vec4 f_col;
uniform vec3 cA, cB, fogC;
uniform vec3 camPos;
uniform vec2 fogNF;
uniform float time, freq, speed, alpha, edgeFade, dirX, dirY;
void main() {
    float ph = (v_uv.x * dirX + v_uv.y * dirY) * freq - time * speed;
    float s = sin(ph) * 0.5 + 0.5;
    s = smoothstep(0.25, 0.75, s);
    vec3 col = mix(cA, cB, s);
    float a = alpha;
    if (edgeFade > 0.001) {
        // edge fade uses wrapped uvs so tiled bands (lava) stay opaque
        vec2 fuv = fract(v_uv);
        float e = smoothstep(0.0, edgeFade, fuv.x) * smoothstep(1.0, 1.0 - edgeFade, fuv.x)
                * smoothstep(0.0, edgeFade, fuv.y) * smoothstep(1.0, 1.0 - edgeFade, fuv.y);
        a *= e;
    }
    float dist = length(camPos - v_wp);
    float f = smoothstep(fogNF.x, fogNF.y, dist);
    col = mix(col, fogC, f * 0.85);
    f_col = vec4(col, a);
}
"""

BRIGHT_FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_col;
uniform sampler2D tex;
uniform float threshold;
void main() {
    vec3 c = texture(tex, v_uv).rgb;
    float l = dot(c, vec3(0.299, 0.587, 0.114));
    f_col = vec4(c * smoothstep(threshold, threshold + 0.35, l), 1.0);
}
"""

BLUR_FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_col;
uniform sampler2D tex;
uniform vec2 pxdir;
void main() {
    vec3 c = texture(tex, v_uv).rgb * 0.227;
    vec2 o1 = pxdir * 1.384, o2 = pxdir * 3.230;
    c += texture(tex, v_uv + o1).rgb * 0.316;
    c += texture(tex, v_uv - o1).rgb * 0.316;
    c += texture(tex, v_uv + o2).rgb * 0.0703;
    c += texture(tex, v_uv - o2).rgb * 0.0703;
    f_col = vec4(c, 1.0);
}
"""

COMP_FRAG = """
#version 330
in vec2 v_uv;
out vec4 f_col;
uniform sampler2D scene;
uniform sampler2D bloom;
uniform float bloomAmt;
void main() {
    vec3 c = texture(scene, v_uv).rgb + texture(bloom, v_uv).rgb * bloomAmt;
    // gentle filmic-ish lift + vignette-friendly grade
    c = c / (c * 0.12 + 0.88);
    c = pow(max(c, 0.0), vec3(0.96));
    f_col = vec4(c, 1.0);
}
"""

# ---------------------------------------------------------------- math

def _persp(fov_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    m = np.zeros((4, 4), dtype="f4")
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m


def _look(eye, center, up=(0.0, 1.0, 0.0)):
    e = np.array(eye, dtype="f4")
    c = np.array(center, dtype="f4")
    u = np.array(up, dtype="f4")
    f = c - e
    f = f / np.linalg.norm(f)
    s = np.cross(f, u)
    s = s / np.linalg.norm(s)
    u2 = np.cross(s, f)
    m = np.eye(4, dtype="f4")
    m[0, :3] = s
    m[1, :3] = u2
    m[2, :3] = -f
    m[0, 3] = -np.dot(s, e)
    m[1, 3] = -np.dot(u2, e)
    m[2, 3] = np.dot(f, e)
    return m


def _ident():
    return np.eye(4, dtype="f4")


def _rot_y(a):
    m = np.eye(4, dtype="f4")
    m[0, 0] = math.cos(a)
    m[0, 2] = math.sin(a)
    m[2, 0] = -math.sin(a)
    m[2, 2] = math.cos(a)
    return m


def _translate(x, y, z):
    m = np.eye(4, dtype="f4")
    m[0, 3], m[1, 3], m[2, 3] = x, y, z
    return m


def _mul(*ms):
    out = ms[0]
    for m in ms[1:]:
        out = out @ m
    return out

# ------------------------------------------------------------ mesh kit
# geo vertex: pos(3) nrm(3) col(3) emit(1).  non-indexed, flat normals.


def _rgb(c):
    return (c[0] / 255.0, c[1] / 255.0, c[2] / 255.0)


class Mesh:
    def __init__(self):
        self.tris = []

    def tri(self, a, b, c, col, emit=0.0, col_b=None, col_c=None):
        a = np.array(a, dtype="f4")
        b = np.array(b, dtype="f4")
        cc = np.array(c, dtype="f4")
        n = np.cross(b - a, cc - a)
        ln = np.linalg.norm(n)
        n = n / ln if ln > 1e-9 else np.array((0.0, 1.0, 0.0), dtype="f4")
        ca = _rgb(col)
        cb = _rgb(col_b or col)
        cc2 = _rgb(col_c or col)
        self.tris.append((a, n, ca, emit, b, n, cb, emit, cc, n, cc2, emit))

    def quad(self, a, b, c, d, col, emit=0.0):
        self.tri(a, b, c, col, emit)
        self.tri(a, c, d, col, emit)

    def finish(self):
        if not self.tris:
            return np.zeros((0, 10), dtype="f4")
        out = np.zeros((len(self.tris) * 3, 10), dtype="f4")
        for i, t in enumerate(self.tris):
            for k in range(3):
                p, n, co, e = t[k * 4], t[k * 4 + 1], t[k * 4 + 2], t[k * 4 + 3]
                out[i * 3 + k, 0:3] = p
                out[i * 3 + k, 3:6] = n
                out[i * 3 + k, 6:9] = co
                out[i * 3 + k, 9] = e
        return out


def slab(m, x, y_top, w, z0, z1, thick, top_c, side_c, bot_c=None, emit=0.0):
    """Axis box: bright top face, shaded sides, dark bottom."""
    bot_c = bot_c or side_c
    # top
    m.quad((x, y_top, z0), (x + w, y_top, z0), (x + w, y_top, z1), (x, y_top, z1), top_c, emit)
    yb = y_top - thick
    # front (+z)
    m.quad((x, yb, z1), (x + w, yb, z1), (x + w, y_top, z1), (x, y_top, z1), side_c)
    # back
    m.quad((x + w, yb, z0), (x, yb, z0), (x, y_top, z0), (x + w, y_top, z0), side_c)
    # left / right
    m.quad((x, yb, z0), (x, yb, z1), (x, y_top, z1), (x, y_top, z0), side_c)
    m.quad((x + w, yb, z1), (x + w, yb, z0), (x + w, y_top, z0), (x + w, y_top, z1), side_c)
    # bottom
    m.quad((x, yb, z1), (x + w, yb, z1), (x + w, yb, z0), (x, yb, z0), bot_c)


def rock_under(m, cx, y_top, w, zc, zd, depth, col, pinch=0.18):
    """Floating-island tapered rock underside (inverted pyramid)."""
    x0, x1 = cx - w / 2, cx + w / 2
    z0, z1 = zc - zd / 2, zc + zd / 2
    bx0, bx1 = cx - w * pinch / 2, cx + w * pinch / 2
    bz0, bz1 = zc - zd * pinch / 2, zc + zd * pinch / 2
    yb = y_top - depth
    m.quad((x0, y_top, z1), (x1, y_top, z1), (bx1, yb, bz1), (bx0, yb, bz1), col)
    m.quad((x1, y_top, z0), (x0, y_top, z0), (bx0, yb, bz0), (bx1, yb, bz0), col)
    m.quad((x0, y_top, z0), (x0, y_top, z1), (bx0, yb, bz1), (bx0, yb, bz0), col)
    m.quad((x1, y_top, z1), (x1, y_top, z0), (bx1, yb, bz0), (bx1, yb, bz1), col)
    m.quad((bx0, yb, bz1), (bx1, yb, bz1), (bx1, yb, bz0), (bx0, yb, bz0), col)


def cone(m, cx, y_base, r, h, z, col, sides=7, emit=0.0, col_tip=None):
    pts = [(cx + math.cos(i / sides * 6.2832) * r, y_base,
            z + math.sin(i / sides * 6.2832) * r) for i in range(sides)]
    tip = (cx, y_base + h, z)
    for i in range(sides):
        m.tri(pts[i], pts[(i + 1) % sides], tip, col, emit, col, col_tip or col)


def prism(m, cx, y_base, r, h, z, col, sides=6, emit=0.0):
    pts0 = [(cx + math.cos(i / sides * 6.2832) * r, y_base,
             z + math.sin(i / sides * 6.2832) * r) for i in range(sides)]
    pts1 = [(x, y_base + h, zz) for (x, _, zz) in pts0]
    for i in range(sides):
        j = (i + 1) % sides
        m.quad(pts0[i], pts0[j], pts1[j], pts1[i], col, emit)
    m.tri(pts1[0], pts1[1], pts1[2], col, emit)
    if sides > 3:
        m.tri(pts1[0], pts1[2], pts1[3], col, emit)


def crystal(m, cx, y_base, r, h, z, col, emit=0.5):
    cone(m, cx, y_base, r, h * 0.62, z, col, 5, emit)
    m2y = y_base + h * 0.62
    pts = [(cx + math.cos(i / 5 * 6.2832) * r, m2y,
            z + math.sin(i / 5 * 6.2832) * r) for i in range(5)]
    for i in range(5):
        m.tri(pts[(i + 1) % 5], pts[i], (cx, y_base + h, z), col, emit)


class ScrollMesh:
    """pos(3) + uv(2) quads for water/lava/falls/beams."""
    def __init__(self):
        self.quads = []  # (a,b,c,d, kind) kind indexes uniform set

    def quad(self, a, b, c, d, kind=0, uvs=None):
        uvs = uvs or ((0, 0), (1, 0), (1, 1), (0, 1))
        self.quads.append((a, b, c, d, kind, uvs))

    def finish(self):
        if not self.quads:
            return np.zeros((0, 5), dtype="f4"), []
        out = np.zeros((len(self.quads) * 6, 5), dtype="f4")
        kinds = []
        for i, (a, b, c, d, kind, uvs) in enumerate(self.quads):
            seq = ((a, uvs[0]), (b, uvs[1]), (c, uvs[2]), (a, uvs[0]), (c, uvs[2]), (d, uvs[3]))
            for k, (p, uv) in enumerate(seq):
                out[i * 6 + k, 0:3] = p
                out[i * 6 + k, 3:5] = uv
            kinds.append(kind)
        return out, kinds

# ------------------------------------------------------- stage scenes

def _mix(c1, c2, k):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3))


def _skin_colors(st):
    """Top / side / underside / glow colors derived from the stage skin."""
    base = st["plat"]
    glow = st["glow"]
    skin = st.get("skin", "")
    if skin in ("shroom", "bark", "thorn"):
        top = _mix(base, (250, 240, 180), 0.62)
    elif skin == "frost":
        top = (213, 227, 243)
    elif skin in ("obsidian", "magmarock"):
        top = _mix(base, (255, 200, 150), 0.55)
    elif skin in ("voidcrystal", "rift", "station"):
        top = _mix(base, (255, 255, 255), 0.55)
    elif skin in ("foundry", "brass"):
        top = _mix(base, (255, 235, 200), 0.55)
    elif skin == "abyss":
        top = (215, 240, 248)
    elif skin == "cloud":
        top = (255, 243, 214)
    else:
        top = _mix(base, (255, 255, 255), 0.60)
    side = _mix(base, (255, 255, 255), 0.10)
    under = _mix(base, (0, 0, 0), 0.45)
    return top, side, under, glow


# game y-down  -> world y-up
def GY(gy):
    return H - gy


SKY_THEMES = {
    # name: (stars, aurora, aurC, vortex, cloud, sunI, sunSize, sunC, sunDir)
    "Ember Arena":     (0.25, 0.0, (120, 255, 170), 0.0, 0.25, 1.2, 0.055, (255, 150, 80), (0.55, -0.35)),
    "Sky Battlefield": (0.0, 0.0, (120, 255, 170), 0.0, 0.80, 1.5, 0.045, (255, 246, 210), (0.62, 0.45)),
    "Void Final":      (1.0, 0.0, (120, 255, 170), 0.0, 0.05, 0.5, 0.030, (200, 170, 255), (-0.5, 0.3)),
    "Fungal Hollow":   (0.35, 0.0, (120, 255, 170), 0.0, 0.10, 0.7, 0.035, (210, 235, 200), (-0.55, 0.25)),
    "Storm Spire":     (0.0, 0.0, (120, 255, 170), 0.0, 0.35, 0.6, 0.040, (235, 240, 250), (0.3, 0.5)),
    "Tide Vault":      (0.0, 0.15, (120, 255, 200), 0.0, 0.20, 1.3, 0.050, (200, 235, 255), (0.2, 0.6)),
    "Iron Foundry":    (0.1, 0.0, (120, 255, 170), 0.0, 0.15, 1.0, 0.045, (255, 170, 100), (0.5, -0.2)),
    "Thorn Garden":    (0.6, 0.0, (120, 255, 170), 0.0, 0.15, 0.9, 0.038, (235, 225, 245), (-0.6, 0.35)),
    "Glacier":         (0.5, 1.0, (120, 255, 190), 0.0, 0.20, 0.9, 0.035, (240, 248, 255), (0.55, 0.4)),
    "Dune Sea":        (0.0, 0.0, (120, 255, 170), 0.0, 0.25, 1.7, 0.060, (255, 240, 200), (0.1, 0.45)),
    "Hollow Star":     (1.0, 0.25, (170, 150, 255), 0.0, 0.05, 0.6, 0.030, (220, 210, 255), (0.5, 0.4)),
    "Clockwork":       (0.0, 0.0, (120, 255, 170), 0.0, 0.30, 1.1, 0.045, (255, 225, 170), (-0.4, 0.4)),
    "Magma Core":      (0.15, 0.0, (120, 255, 170), 0.0, 0.15, 1.2, 0.050, (255, 140, 70), (0.4, -0.3)),
    "Cloud Nine":      (0.0, 0.0, (120, 255, 170), 0.0, 0.85, 1.2, 0.045, (255, 252, 235), (-0.55, 0.45)),
    "The Rift":        (0.7, 0.0, (120, 255, 170), 1.0, 0.05, 0.4, 0.030, (255, 120, 140), (0.0, 0.2)),
    "Harbor Town":     (0.1, 0.0, (120, 255, 170), 0.0, 0.40, 1.3, 0.048, (255, 225, 180), (-0.3, 0.15)),
    "World Tree":      (0.0, 0.0, (120, 255, 170), 0.0, 0.50, 1.4, 0.045, (255, 250, 220), (0.0, 0.55)),
    "Sunset Keep":     (0.15, 0.0, (120, 255, 170), 0.0, 0.60, 1.6, 0.062, (255, 190, 120), (0.05, -0.25)),
}


def build_stage(st):
    """Compile one stage dict into static geometry + sky/uniform recipe.

    Returns dict(geo=np, scroll=np, kinds, sky=..., fog=..., light=...,
                 dyn_kinds=[...]) — all in world coords (y-up, islands at z~0).
    """
    m = Mesh()
    s = ScrollMesh()
    top_c, side_c, under_c, glow = _skin_colors(st)
    main = st["main"]
    # main island: slab + tapered rock root
    slab(m, main["x"], GY(main["y"]), main["w"], -30, 30, 26, top_c, side_c, under_c)
    rock_under(m, main["x"] + main["w"] / 2, GY(main["y"]) - 26, main["w"] * 0.94,
               0, 44, 120, under_c)
    # floating islands
    for pl in st["plats"]:
        slab(m, pl["x"], GY(pl["y"]), pl["w"], -48, -8, 15, top_c, side_c, under_c)
        rock_under(m, pl["x"] + pl["w"] / 2, GY(pl["y"]) - 15, pl["w"] * 0.8,
                   -28, 30, 46, under_c)
    # pads: glowing launch plates on the main
    for pd in st.get("pads", []):
        slab(m, pd["x"], GY(pd["y"]) + 2, pd["w"], -14, 14, 8,
             _mix(glow, (255, 255, 255), 0.4), side_c, under_c, emit=0.9)
    # spikes: themed cones rooted on the main
    skin = st.get("skin", "")
    if skin == "thorn":
        scol = (90, 160, 90)
    elif skin == "frost":
        scol = (150, 200, 235)
    elif skin in ("foundry", "magmarock", "obsidian"):
        scol = (200, 90, 50)
    else:
        scol = (200, 60, 60)
    for sp in st.get("spikes", []):
        n = max(2, int(sp["w"] // 22))
        for k in range(n):
            cone(m, sp["x"] + (k + 0.5) * sp["w"] / n, GY(sp["y"]), sp["w"] / n * 0.48,
                 17, 0, scol, 4, emit=0.35)
    # lava pools: bright scrolling quads riding just above their rim,
    # pushed in front of the island face so depth never swallows them
    for lv in st.get("lava", []):
        x, w, y = lv["x"], lv["w"], GY(lv["y"]) + 1
        s.quad((x, y - 7, 33), (x + w, y - 7, 33), (x + w, y + 2, 33), (x, y + 2, 33),
               kind=1, uvs=((0, 0), (w / 60.0, 0), (w / 60.0, 1), (0, 1)))
        slab(m, x - 6, y + 1, w + 12, -30, 30, 5, (120, 30, 10), (90, 25, 12), (60, 15, 10))
    _set_piece(m, s, st)
    geo = m.finish()
    scroll, kinds = s.finish()
    top = st["top"]
    bot = st["bot"]
    mid = _mix(top, bot, 0.55)
    theme = SKY_THEMES.get(st["name"], (0, 0, (120, 255, 170), 0, 0.2, 1.0, 0.045,
                                        (255, 240, 210), (0.4, 0.3)))
    stars, aur, aurC, vort, cloud, sunI, sunSize, sunC, sunDir = theme
    vorC1 = (150, 30, 60) if st["name"] == "The Rift" else glow
    vorC2 = (90, 40, 160) if st["name"] == "The Rift" else (255, 255, 255)
    return {
        "geo": geo, "scroll": scroll, "kinds": kinds,
        "sky": {"topC": top, "midC": mid, "botC": bot, "sunDir": sunDir, "sunC": sunC,
                "sunSize": sunSize, "sunI": sunI, "stars": stars, "aur": aur, "aurC": aurC,
                "vort": vort, "vorC1": vorC1, "vorC2": vorC2, "cloud": cloud,
                "cloudC": _mix(bot, (255, 255, 255), 0.6)},
        "fog": _mix(mid, (232, 238, 248), 0.25),
        "name": st["name"],
    }


def _set_piece(m, s, st):
    """Per-arena background set dressing (static low-poly geometry)."""
    name = st["name"]
    glow = st["glow"]
    dark = _mix(st["bot"], (0, 0, 0), 0.45)

    def mountains(cx, base_y, z, s0, col, n=4, spread=420):
        for i in range(n):
            cone(m, cx + (i - n / 2) * spread + (i % 2) * 90, base_y,
                 s0 * (0.8 + (i % 3) * 0.25), s0 * (1.1 + (i % 2) * 0.5), z, col, 5)

    if name == "Ember Arena":
        cone(m, 500, GY(540), 260, 260, -420, dark, 7)
        cone(m, 500, GY(280), 60, 40, -420, (255, 110, 40), 7, emit=1.6)
        cone(m, 2500, GY(540), 300, 220, -520, dark, 7)
        for i in range(3):
            prism(m, 1100 + i * 260, GY(540), 40, 200 - i * 30, -300, dark, 6)
    elif name == "Sky Battlefield":
        for i, (ix, iy, iw) in enumerate(((700, 260, 150), (1600, 300, 110), (2300, 230, 130))):
            slab(m, ix, GY(iy), iw, -220, -160, 22, (150, 190, 150), (90, 115, 140), dark)
            rock_under(m, ix + iw / 2, GY(iy) - 22, iw * 0.85, -190, 44, 70, (90, 115, 140))
            s.quad((ix + iw * 0.7, GY(iy + 90), -150), (ix + iw * 0.7 + 16, GY(iy + 90), -150),
                   (ix + iw * 0.7 + 16, GY(iy), -150), (ix + iw * 0.7, GY(iy), -150), kind=0)
        mountains(1600, GY(540), -700, 260, _mix(st["bot"], (70, 110, 150), 0.5))
    elif name == "Void Final":
        for i, mx in enumerate((700, 2100)):
            slab(m, mx - 35, GY(180 + i * 30), 70, -260, -200, 260, dark, dark, dark)
            for j in range(3):
                slab(m, mx - 6, GY(260 + j * 60 + i * 20) + 5, 12, -228, -216, 10,
                     glow, glow, glow, emit=1.4)
        for i in range(5):
            crystal(m, 500 + i * 450, GY(540), 26, 90 + (i % 3) * 40, -350, (90, 70, 130), emit=0.4)
    elif name == "Fungal Hollow":
        for i, (mx, mh, mr) in enumerate(((700, 260, 60), (1600, 200, 80), (2300, 280, 52))):
            prism(m, mx, GY(540), 16, mh, -260, (50, 70, 60), 6)
            cone(m, mx, GY(540 - mh), mr, 46, -260, (120, 70, 150), 8, emit=0.25)
        for i in range(6):
            cone(m, 500 + i * 350, GY(540), 14, 40, -180, (130, 90, 160), 6, emit=0.3)
    elif name == "Storm Spire":
        prism(m, 2200, GY(540), 95, 420, -380, (36, 44, 66), 4)
        cone(m, 2200, GY(120), 70, 60, -380, (30, 36, 56), 4)
        for j in range(4):
            slab(m, 2200 - 16, GY(150 + j * 62) + 6, 32, -330, -318, 12,
                 (255, 235, 150), (255, 235, 150), (255, 235, 150), emit=1.2)
        mountains(1400, GY(540), -700, 240, _mix(st["bot"], (50, 58, 86), 0.5))
    elif name == "Tide Vault":
        for i, (px, ph) in enumerate(((700, 300), (1200, 220), (1700, 330), (2200, 200))):
            prism(m, px, GY(540), 26, ph, -280, (45, 95, 120), 6)
            slab(m, px - 30, GY(540 - ph) + 8, 60, -300, -260, 14, (70, 135, 160),
                 (45, 95, 120), dark)
        slab(m, 1050, GY(200) + 10, 420, -300, -260, 22, (45, 95, 120), (45, 95, 120), dark)
        s.quad((300, GY(540), -180), (2700, GY(540), -180), (2700, GY(120), -180),
               (300, GY(120), -180), kind=3)
    elif name == "Iron Foundry":
        for i, stx in enumerate((900, 2200)):
            prism(m, stx, GY(190), 34, 350, -300, (40, 30, 30), 6)
            slab(m, stx - 42, GY(176) + 8, 84, -320, -280, 16, (30, 22, 22),
                 (30, 22, 22), dark)
        for i, (gx, gy, r) in enumerate(((1500, 210, 62), (1700, 300, 40))):
            prism(m, gx, gy - r, r, r * 2, -260, (52, 44, 46), 6)
        for i in range(3):
            slab(m, 1150 + i * 350 - 40, GY(470) + 8, 80, -120, -60, 26,
                 (255, 130, 50), (120, 50, 25), dark, emit=1.5)
    elif name == "Thorn Garden":
        for i in range(3):
            prism(m, 800 + i * 650, GY(540), 20, 300 + i * 30, -320, (40, 70, 45), 5)
            cone(m, 800 + i * 650, GY(240 - i * 30), 26, 30, -320, (70, 130, 75), 5, emit=0.3)
            slab(m, 800 + i * 650 + 40, GY(280) + 4, 16, -320, -300, 8,
                 (210, 130, 220), (210, 130, 220), (210, 130, 220), emit=1.2)
        mountains(1500, GY(540), -700, 220, _mix(st["bot"], (40, 70, 50), 0.5))
    elif name == "Glacier":
        mountains(1600, GY(540), -650, 260, (90, 130, 165))
        for i in range(4):
            crystal(m, 600 + i * 500, GY(540), 22, 80 + (i % 2) * 40, -280,
                    (170, 215, 240), emit=0.35)
    elif name == "Dune Sea":
        for i in range(3):
            prism(m, 900 + i * 800, GY(540), 320, 60 + i * 14, -420 - i * 120,
                  _mix(st["plat"], (0, 0, 0), 0.15 + i * 0.1), 4)
        prism(m, 2300, GY(540), 46, 260, -380, (120, 90, 60), 4)
        slab(m, 2300 - 20, GY(280) + 8, 40, -400, -360, 16, (150, 115, 75),
             (120, 90, 60), dark, emit=0.4)
    elif name == "Hollow Star":
        # planet curve: wide flattened banded disc low behind
        for bi, bc in enumerate(((70, 60, 120), (90, 80, 150), (120, 110, 180))):
            slab(m, -600, GY(620) + bi * 26, 4200, -950, -850, 24, bc, bc, bc)
        for i in range(12):
            a = i / 12 * 6.2832
            slab(m, 1500 + math.cos(a) * 480 - 30, GY(140) + math.sin(a) * 60 + 8, 60,
                 -300, -240, 16, (50, 45, 70), (50, 45, 70), dark,
                 emit=1.0 if i % 2 == 0 else 0.0)
        for i in range(4):
            slab(m, 600 + i * 550, GY(300 + (i % 2) * 100) + 4, 34, -260, -220, 8,
                 (60, 60, 80), (60, 60, 80), dark)
    elif name == "Clockwork":
        _gear(m, 700, GY(380), 60, -260, (70, 58, 48))
        _gear(m, 2450, GY(380), 74, -260, (60, 50, 42))
        prism(m, 1050, GY(260), 18, 280, -300, (50, 42, 38), 6)
        prism(m, 2000, GY(260), 18, 280, -300, (50, 42, 38), 6)
    elif name == "Magma Core":
        for i, bx in enumerate((900, 1250, 2000, 2350)):
            prism(m, bx, GY(120 + (i % 2) * 40), 52, 420, -320, (32, 14, 14), 6)
        for i, mfx in enumerate((1400, 2000)):
            s.quad((mfx - 14, GY(540), -240), (mfx + 14, GY(540), -240),
                   (mfx + 14, GY(60), -240), (mfx - 14, GY(60), -240), kind=2)
    elif name == "Cloud Nine":
        for i in range(3):
            slab(m, 700 + i * 600, GY(150 + i * 40) + 10, 130, -320, -200, 34,
                 (248, 246, 240), (228, 232, 242), dark)
        for i in range(2):
            prism(m, 1100 + i * 700, GY(540), 200, 40, -500, (244, 246, 250), 5)
    elif name == "The Rift":
        for i in range(9):
            a = i / 9 * 6.2832
            slab(m, 2100 + math.cos(a) * 430 - 22, GY(230) + math.sin(a) * 200 + 6, 44,
                 -260, -200, 14, (110, 70, 140), (80, 50, 110), dark, emit=0.5)
        for i in range(3):
            crystal(m, 1400 + i * 700, GY(540), 30, 120, -320, (150, 50, 90), emit=0.7)
        slab(m, 1500, GY(470) + 4, 1200, -140, -60, 10, (255, 80, 100),
             (150, 30, 45), dark, emit=1.4)
    elif name == "Harbor Town":
        for i, (bx, bw, bh) in enumerate(((500, 150, 220), (900, 130, 170), (1900, 160, 240),
                                          (2300, 120, 180))):
            slab(m, bx, GY(540 - bh), bw, -380, -300, bh, (48, 60, 88), (40, 50, 75), dark)
            for wx in range(3):
                for wy in range(3):
                    if (wx * 3 + wy + i) % 3 != 0:
                        slab(m, bx + 18 + wx * 40, GY(500 - bh + wy * 34) + 5, 20,
                             -338, -330, 10, (255, 220, 150), (255, 220, 150),
                             (255, 220, 150), emit=1.3)
        prism(m, 2500, GY(180), 26, 360, -320, (200, 200, 210), 6)
        slab(m, 2500 - 30, GY(150) + 6, 60, -340, -300, 14, (200, 90, 90),
             (200, 90, 90), dark, emit=0.8)
        for i in range(2):
            prism(m, 1100 + i * 500, GY(330), 10, 210, -200, (70, 55, 45), 4)
    elif name == "World Tree":
        prism(m, 1500, GY(540), 80, 420, -350, (70, 55, 40), 7)
        prism(m, 1360, GY(120), 40, 120, -350, (95, 75, 55), 5)
        prism(m, 1660, GY(140), 40, 110, -350, (95, 75, 55), 5)
        for i, (cx, cy, cr) in enumerate(((1360, 90, 170), (1650, 120, 160), (1500, 30, 220))):
            cone(m, cx, GY(cy + 40), cr, 100, -350, (60, 140, 90), 8)
            cone(m, cx, GY(cy + 10), cr * 0.7, 70, -350, (95, 185, 120), 8, emit=0.15)
    elif name == "Sunset Keep":
        slab(m, 1440, GY(220), 120, -360, -280, 320, (70, 50, 80), (60, 44, 70), dark)
        for i, tx in enumerate((1290, 1710)):
            slab(m, tx - 40, GY(270), 80, -360, -280, 270, (62, 44, 72), (55, 40, 65), dark)
            cone(m, tx, GY(0), 56, 60, -320, (50, 36, 60), 4)
            s.quad((tx - 44, GY(196), -300), (tx, GY(196), -300), (tx, GY(218), -300),
                   (tx - 44, GY(218), -300), kind=4)
        for j in range(3):
            slab(m, 1500 - 16, GY(260 + j * 50) + 6, 32, -318, -310, 20,
                 (255, 190, 120), (255, 190, 120), (255, 190, 120), emit=1.2)
    else:
        mountains(1500, GY(540), -650, 240, dark)


def _gear(m, cx, cy, r, z, col):
    prism(m, cx, cy - r, r, r * 2, z, col, 8)
    for i in range(8):
        a = i / 8 * 6.2832
        slab(m, cx + math.cos(a) * r * 1.05 - 10, cy + math.sin(a) * r * 1.05 + 7, 20,
             z - 12, z + 12, 14, col, col, col)

# ------------------------------------------------------------- renderer

SCROLL_KIND_UNIFORMS = {
    # kind: (freq, speed, alpha, edge, dx, dy)
    0: (6.0, 2.2, 0.85, 0.08, 0.0, 1.0),   # waterfall
    1: (9.0, 3.0, 0.95, 0.05, 1.0, 0.3),   # lava
    2: (7.0, 4.2, 0.95, 0.10, 0.0, 1.0),   # lavafall
    3: (5.0, 0.8, 0.55, 0.15, 0.3, 1.0),   # deep water
    4: (4.0, 1.2, 0.95, 0.05, 1.0, 0.2),   # banner
    5: (6.0, 1.0, 0.35, 0.45, 0.0, 0.0),   # beam
}

SCROLL_KIND_COLORS = {
    0: ((200, 230, 245), (255, 255, 255)),
    1: ((220, 80, 20), (255, 200, 110)),
    2: ((255, 120, 40), (255, 220, 150)),
    3: ((40, 110, 160), (120, 200, 240)),
    4: ((200, 80, 90), (235, 150, 150)),
    5: ((255, 244, 200), (255, 244, 200)),
}


class Renderer:
    """Owns a standalone GL context; renders stages to RGB bytes (top-down)."""

    FOV = 42.0
    EYE_Y = 446.0
    EYE_Z = 742.0
    LOOK_Y = 288.0
    LOOK_Z = 0.0
    FOG_NEAR = 650.0
    FOG_FAR = 1500.0

    def __init__(self, w=W, h=H):
        self.w, self.h = w, h
        self.ctx = moderngl.create_standalone_context()
        ctx = self.ctx
        self.prog_sky = ctx.program(vertex_shader=SKY_VERT, fragment_shader=SKY_FRAG)
        self.prog_texsky = ctx.program(vertex_shader=TEX_SKY_VERT, fragment_shader=TEX_SKY_FRAG)
        self.prog_geo = ctx.program(vertex_shader=GEO_VERT, fragment_shader=GEO_FRAG)
        self.prog_scroll = ctx.program(vertex_shader=SCROLL_VERT, fragment_shader=SCROLL_FRAG)
        self.prog_bright = ctx.program(vertex_shader=SKY_VERT, fragment_shader=BRIGHT_FRAG)
        self.prog_blur = ctx.program(vertex_shader=SKY_VERT, fragment_shader=BLUR_FRAG)
        self.prog_comp = ctx.program(vertex_shader=SKY_VERT, fragment_shader=COMP_FRAG)
        # fullscreen triangle
        tri = np.array([-1.0, -1.0, 3.0, -1.0, -1.0, 3.0], dtype="f4")
        self.vbo_tri = ctx.buffer(tri.tobytes())
        self.vao_sky = ctx.vertex_array(self.prog_sky, [(self.vbo_tri, "2f", "in_pos")])
        self.vao_bright = ctx.vertex_array(self.prog_bright, [(self.vbo_tri, "2f", "in_pos")])
        self.vao_blur = ctx.vertex_array(self.prog_blur, [(self.vbo_tri, "2f", "in_pos")])
        self.vao_comp = ctx.vertex_array(self.prog_comp, [(self.vbo_tri, "2f", "in_pos")])
        # textured-sky quad
        quad = np.array([-1, -1, 0, 0, 1, -1, 1, 0, 1, 1, 1, 1,
                         -1, -1, 0, 0, 1, 1, 1, 1, -1, 1, 0, 1], dtype="f4")
        self.vbo_quad = ctx.buffer(quad.tobytes())
        self.vao_texsky = ctx.vertex_array(self.prog_texsky,
                                           [(self.vbo_quad, "2f 2f", "in_pos", "in_uv")])
        # targets
        self.fbo_scene = ctx.framebuffer(
            color_attachments=[ctx.texture((w, h), 4)],
            depth_attachment=ctx.depth_texture((w, h)))
        hw, hh = w // 2, h // 2
        self.tex_bright = ctx.texture((hw, hh), 4)
        self.fbo_bright = ctx.framebuffer(color_attachments=[self.tex_bright])
        self.tex_blur_a = ctx.texture((hw, hh), 4)
        self.fbo_blur_a = ctx.framebuffer(color_attachments=[self.tex_blur_a])
        self.tex_blur_b = ctx.texture((hw, hh), 4)
        self.fbo_blur_b = ctx.framebuffer(color_attachments=[self.tex_blur_b])
        self.fbo_final = ctx.framebuffer(color_attachments=[ctx.texture((w, h), 3)])
        self.stages = {}
        self.paintings = {}
        self._last_mvp = np.eye(4, dtype="f4")
        self.proj = _persp(self.FOV, w / h, 10.0, 4000.0)

    # -- stage cache ------------------------------------------------
    def stage(self, st):
        key = st["name"]
        hit = self.stages.get(key)
        if hit is None:
            data = build_stage(st)
            vbo = self.ctx.buffer(data["geo"].tobytes())
            vao = self.ctx.vertex_array(
                self.prog_geo, [(vbo, "3f 3f 3f 1f", "in_pos", "in_nrm", "in_col", "in_emit")])
            svbo, kinds = data["scroll"], data["kinds"]
            svbo_gl = self.ctx.buffer(svbo.tobytes()) if len(svbo) else None
            svao = (self.ctx.vertex_array(
                self.prog_scroll, [(svbo_gl, "3f 2f", "in_pos", "in_uv")])
                if svbo_gl is not None else None)
            hit = {"vao": vao, "n": len(data["geo"]) // 3,
                   "svao": svao, "skinds": kinds, "sky": data["sky"], "fog": data["fog"]}
            self.stages[key] = hit
        return hit

    def set_painting(self, name, rgb_bytes, pw, ph, mid_bytes=None, mw=0, mh=0):
        if name in self.paintings:
            return
        tex = self.ctx.texture((pw, ph), 3, rgb_bytes)
        tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        # cover-fit crop of the painting into 16:9
        sc = max(self.w / pw, self.h / ph)
        su, sv = (self.w / sc / pw), (self.h / sc / ph)
        ou, ov = (1.0 - su) / 2.0, (1.0 - sv) / 2.0
        mid = None
        if mid_bytes:
            mid = self.ctx.texture((mw, mh), 4, mid_bytes)
            mid.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.paintings[name] = {"tex": tex, "mid": mid, "su": su, "sv": sv,
                                "ou": ou, "ov": ov}

    # -- frame ------------------------------------------------------
    def render(self, st, cam_cx, t, dyn=(), shx=0.0, shy=0.0, dyn_extra=()):
        """Render stage; dyn = extra geo boxes; returns top-down RGB bytes."""
        ctx = self.ctx
        S = self.stage(st)
        cx = cam_cx + shx
        sway = math.sin(t * 0.25) * 10.0
        eye = (cx + sway, self.EYE_Y + shy * 0.5, self.EYE_Z)
        look = (cx + sway, self.LOOK_Y + shy * 0.5, self.LOOK_Z)
        view = _look(eye, look)
        mvp = self.proj @ view
        self._last_mvp = mvp
        fog_c = np.array(_rgb(S["fog"]), dtype="f4")

        paint = self.paintings.get(st["name"])
        self.fbo_scene.use()
        ctx.clear(0.0, 0.0, 0.0, 1.0)
        ctx.disable(moderngl.BLEND)
        ctx.disable(moderngl.DEPTH_TEST)
        if paint is not None:
            tex, mid = paint["tex"], paint["mid"]
            par = -cx * 0.00003
            tex.use(0)
            self.prog_texsky["tex"] = 0
            self.prog_texsky["dim"] = 0.92
            self.prog_texsky["uvScale"] = (paint["su"], paint["sv"])
            self.prog_texsky["uvOff"] = (paint["ou"] + par, paint["ov"])
            self.vao_texsky.render(moderngl.TRIANGLES)
            if mid is not None:
                ctx.enable(moderngl.BLEND)
                mid.use(0)
                self.prog_texsky["tex"] = 0
                self.prog_texsky["dim"] = 1.0
                self.prog_texsky["uvScale"] = (paint["su"], paint["sv"])
                self.prog_texsky["uvOff"] = (paint["ou"] + par * 2.2, paint["ov"])
                self.vao_texsky.render(moderngl.TRIANGLES)
                ctx.disable(moderngl.BLEND)
        else:
            sk = S["sky"]
            P = self.prog_sky
            P["topC"] = _rgb(sk["topC"])
            P["midC"] = _rgb(sk["midC"])
            P["botC"] = _rgb(sk["botC"])
            P["sunDir"] = tuple(sk["sunDir"])
            P["sunC"] = _rgb(sk["sunC"])
            P["sunSize"] = float(sk["sunSize"])
            P["sunI"] = float(sk["sunI"])
            P["starAmt"] = float(sk["stars"])
            P["time"] = float(t)
            P["aurC"] = _rgb(sk["aurC"])
            P["auroraAmt"] = float(sk["aur"])
            P["vortexAmt"] = float(sk["vort"])
            P["vorC1"] = _rgb(sk["vorC1"])
            P["vorC2"] = _rgb(sk["vorC2"])
            P["cloudAmt"] = float(sk["cloud"])
            P["cloudC"] = _rgb(sk["cloudC"])
            self.vao_sky.render(moderngl.TRIANGLES)

        # opaque geometry
        ctx.enable(moderngl.DEPTH_TEST)
        G = self.prog_geo
        G["mvp"].write(mvp.T.astype("f4").tobytes())
        G["model"].write(_ident().tobytes())
        G["lightDir"] = (0.55, 0.75, 0.65)
        G["lightCol"] = (1.0, 0.96, 0.90)
        G["ambC"] = (0.42, 0.44, 0.50)
        G["camPos"] = tuple(eye)
        G["fogC"] = tuple(fog_c)
        G["fogNF"] = (self.FOG_NEAR, self.FOG_FAR)
        G["specAmt"] = 0.35
        G["emitBoost"] = 1.0
        S["vao"].render(moderngl.TRIANGLES)
        if dyn:
            dm = Mesh()
            for b in dyn:
                top, side = b["top"], b["side"]
                slab(dm, b["x"], GY(b["y"]), b["w"], -48, -8, b.get("thick", 15),
                     top, side, side, emit=b.get("emit", 0.0))
                if b.get("rock", True):
                    rock_under(dm, b["x"] + b["w"] / 2, GY(b["y"]) - 15, b["w"] * 0.8,
                               -28, 30, 46, side)
            arr = dm.finish()
            if len(arr):
                vb = ctx.buffer(arr.tobytes())
                va = ctx.vertex_array(
                    self.prog_geo, [(vb, "3f 3f 3f 1f", "in_pos", "in_nrm", "in_col", "in_emit")])
                va.render(moderngl.TRIANGLES)
                vb.release()
                va.release()
        for item in dyn_extra:
            # (verts_array, model_matrix)
            arr, model = item
            vb = ctx.buffer(arr.tobytes())
            va = ctx.vertex_array(
                self.prog_geo, [(vb, "3f 3f 3f 1f", "in_pos", "in_nrm", "in_col", "in_emit")])
            G["model"].write(model.T.astype("f4").tobytes())
            va.render(moderngl.TRIANGLES)
            vb.release()
            va.release()
        G["model"].write(_ident().tobytes())

        # translucent scroll layers
        if S["svao"] is not None:
            ctx.enable(moderngl.BLEND)
            ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            SC = self.prog_scroll
            SC["mvp"].write(mvp.T.astype("f4").tobytes())
            SC["model"].write(_ident().tobytes())
            SC["camPos"] = tuple(eye)
            SC["fogC"] = tuple(fog_c)
            SC["fogNF"] = (self.FOG_NEAR, self.FOG_FAR)
            SC["time"] = float(t)
            for qi, kind in enumerate(S["skinds"]):
                (cA, cB), (freq, speed, alpha, edge, dx, dy) = \
                    SCROLL_KIND_COLORS[kind], SCROLL_KIND_UNIFORMS[kind]
                SC["cA"] = _rgb(cA)
                SC["cB"] = _rgb(cB)
                SC["freq"] = freq
                SC["speed"] = speed
                SC["alpha"] = alpha
                SC["edgeFade"] = edge
                SC["dirX"] = dx
                SC["dirY"] = dy
                # render single quad qi
                S["svao"].render(moderngl.TRIANGLES, first=qi * 6, vertices=6)
            ctx.disable(moderngl.BLEND)

        # bloom: bright-pass at half res, blur, composite
        self.fbo_bright.use()
        ctx.disable(moderngl.DEPTH_TEST)
        ctx.disable(moderngl.BLEND)
        self.fbo_scene.color_attachments[0].use(0)
        self.prog_bright["tex"] = 0
        self.prog_bright["threshold"] = 0.72
        self.vao_bright.render(moderngl.TRIANGLES)
        self.tex_bright.use(0)
        self.fbo_blur_a.use()
        self.prog_blur["tex"] = 0
        self.prog_blur["pxdir"] = (1.0 / (self.w // 2), 0.0)
        self.vao_blur.render(moderngl.TRIANGLES)
        self.tex_blur_a.use(0)
        self.fbo_blur_b.use()
        self.prog_blur["tex"] = 0
        self.prog_blur["pxdir"] = (0.0, 1.0 / (self.h // 2))
        self.vao_blur.render(moderngl.TRIANGLES)
        self.fbo_final.use()
        self.fbo_scene.color_attachments[0].use(0)
        self.tex_blur_b.use(1)
        self.prog_comp["scene"] = 0
        self.prog_comp["bloom"] = 1
        self.prog_comp["bloomAmt"] = 0.85
        self.vao_comp.render(moderngl.TRIANGLES)

        raw = self.fbo_final.read(components=3)
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(self.h, self.w, 3)
        return np.ascontiguousarray(arr[::-1]).tobytes()

    def w2s(self, x, gy, z=0.0):
        """World (game coords, y-down) -> screen px + perspective scale.

        Uses the current frame's camera. Matches the GL projection exactly
        so software-drawn fighters/fx plant onto the 3D islands.
        """
        mvp = self._last_mvp
        v = mvp @ np.array([x, H - gy, z, 1.0], dtype="f4")
        w = float(v[3])
        v = v / w
        sx = (v[0] * 0.5 + 0.5) * self.w
        sy = (1 - (v[1] * 0.5 + 0.5)) * self.h
        # perspective scale: screen px per world unit at this depth
        sc = 0.5 * self.h * float(mvp[1, 1]) / max(1.0, w)
        sc = min(2.0, max(0.5, sc))
        return float(sx), float(sy), float(sc)


def dyn_clock_hands(t, cx=1500.0, cy=None, z=-230.0):
    """Two thin boxes rotating like clock hands (world-space, built per frame)."""
    if cy is None:
        cy = float(GY(170))
    items = []
    for ln, wd, spd, col in ((44, 5, 0.10, (240, 220, 180)), (66, 3, 0.8, (255, 200, 120))):
        a = (t * spd) % 6.2832
        m = Mesh()
        # hand extends upward from pivot, length ln
        slab(m, cx - wd / 2, cy + ln, wd, z - 6, z + 6, 6, col, col, col)
        ca, sa = math.cos(a), math.sin(a)
        rot = np.eye(4, dtype="f4")
        rot[0, 0], rot[0, 1], rot[1, 0], rot[1, 1] = ca, -sa, sa, ca
        model = _mul(_translate(cx, cy, z), rot, _translate(-cx, -cy, -z))
        items.append((m.finish(), model))
    return items
