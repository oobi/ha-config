#!/usr/bin/env python3
"""Generate the floorplan SVGs and picture-elements YAML for the Home dashboard.

Room shapes, labels and device icon positions all live in this file, in the
pixel space of the original real-estate plans (upper floor 1700x1600, site
1580 tall). Edit ROOMS / ICONS below, then run:

    python3 dashboards/home/floorplan/build_floorplan.py

It writes:
    www/floorplan/*.svg                         (served as /local/floorplan/...)
    dashboards/home/floorplan/upper_elements.yaml
    dashboards/home/floorplan/outside_elements.yaml

Each room gets two overlay SVGs cropped to its bounding box: a glow (shown
while its light entity is on) and a transparent one (shown otherwise). The
overlay doubles as the room's tap target: tap opens the room, hold toggles
its lights.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WWW = ROOT / "www" / "floorplan"
OUT = Path(__file__).resolve().parent
VERSION = 1  # bump to bust browser caches after changing SVGs

# --- palette -----------------------------------------------------------------
BG = "#0f172a"
WALL = "#52607a"
ROOM = "#162033"
OUTDOOR = "#1b2638"
OUTDOOR_EDGE = "#3b4a63"
LABEL = "#9fb0c8"
SUBLABEL = "#5f708a"
GLOW = "#fbbf24"


# --- upper floor ---------------------------------------------------------------
UPPER_W, UPPER_H = 1700, 1600


def rect(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


# key: (label, sublabel, polygon, light entity or None, subview path, label pos)
ROOMS = {
    "hallway": ("Hall", None,
                [(385, 645), (1030, 645), (1030, 745), (935, 745), (935, 1115),
                 (790, 1115), (790, 745), (385, 745)],
                "light.hallway", "hallway", (560, 712)),
    "deck": ("Front Deck", None,
             [(55, 1145), (1640, 1145), (1640, 1560), (1200, 1560), (1200, 1290), (55, 1290)],
             "light.deck", "deck", (90, 1205)),
    "master_bedroom": ("Master Bed", "3.4 × 4.3m", rect(55, 300, 385, 745),
                       "light.master_bedroom", "master-bedroom", (85, 360)),
    "ensuite": ("Ensuite", None, rect(385, 300, 600, 600),
                "light.ensuite", "ensuite", (410, 360)),
    "bathroom": ("Bath", None, rect(600, 300, 835, 640),
                 "light.bathroom", "bathroom", (625, 360)),
    "kitchen": ("Kitchen", "4.7 × 4.3m",
                [(835, 300), (1300, 300), (1300, 745), (1030, 745), (1030, 645), (835, 645)],
                None, "kitchen", (870, 360)),
    "dining": ("Dining", "3.1 × 4.3m", rect(1300, 300, 1640, 745),
               "light.dining", "dining", (1330, 360)),
    "dexters_bedroom": ("Dexter", "4.2 × 3.7m", rect(55, 745, 405, 1115),
                        "light.lokis_bedroom", "dexters-bedroom", (85, 805)),
    "lokis_bedroom": ("Loki", "2.9 × 3.7m", rect(405, 745, 790, 1115),
                      "light.enders_bedroom", "lokis-bedroom", (435, 805)),
    "living_room": ("Lounge", "6.7 × 3.7m", rect(935, 745, 1640, 1115),
                    "light.living_room", "living-room", (965, 805)),
}

BALCONY = [(55, 195), (1080, 195), (1080, 145), (1230, 145), (1230, 5), (1640, 5), (1640, 300), (55, 300)]

# Device icons: (entity, x, y, extra element options)
# tap toggles where that makes sense, otherwise opens more-info.
TOGGLE = {"tap_action": {"action": "toggle"}, "hold_action": {"action": "more-info"}}
INFO = {"tap_action": {"action": "more-info"}}
UPPER_ICONS = [
    ("light.master_bedroom", 220, 520, TOGGLE),
    ("media_player.master_bedroom_wifi", 150, 640, INFO),
    ("input_boolean.bedroom_alarm_master_bedroom", 290, 640, TOGGLE),
    ("light.ensuite", 492, 430, TOGGLE),
    ("binary_sensor.ensuite_motion_sensor_motion", 445, 525, INFO),
    ("switch.sonoff_1000eca0b7", 540, 525, TOGGLE),
    ("light.bathroom", 718, 420, TOGGLE),
    ("binary_sensor.bathroom_motion_sensor_motion", 655, 510, INFO),
    ("switch.sonoff_1000ece42c", 718, 510, TOGGLE),
    ("media_player.bathroom_speaker", 781, 510, INFO),
    ("plant.plant_5", 718, 590, INFO),
    ("media_player.kitchen_speaker", 1070, 520, INFO),
    ("light.dining", 1470, 500, TOGGLE),
    ("sensor.ecosys_ma2101cwfx", 1470, 620, INFO),
    ("light.hallway", 862, 900, TOGGLE),
    ("light.lokis_bedroom", 230, 935, TOGGLE),
    ("media_player.dexters_speaker", 165, 1040, INFO),
    ("input_boolean.bedroom_alarm_dexter", 295, 1040, TOGGLE),
    ("light.enders_bedroom", 597, 935, TOGGLE),
    ("media_player.loki_s_bedroom_speaker", 532, 1040, INFO),
    ("input_boolean.bedroom_alarm_loki", 662, 1040, TOGGLE),
    ("light.living_room", 1290, 890, TOGGLE),
    ("media_player.lg_webos_tv_1118", 1120, 1010, INFO),
    ("media_player.living_room", 1230, 1010, INFO),
    ("cover.all_blinds", 1350, 1010, INFO),
    ("vacuum.roborock_s5_max", 1470, 1010, INFO),
    ("light.deck", 1420, 1400, TOGGLE),
]
# Plants in the lounge: one icon that opens the Plants dashboard
UPPER_EXTRA = [
    ({"type": "icon", "icon": "mdi:flower", "title": "Plants",
      "tap_action": {"action": "navigate", "navigation_path": "/dashboard-plants"}},
     1570, 890, {"color": "#4ade80"}),
]


# --- outside / site plan -----------------------------------------------------
SITE_W, SITE_H = 580, 1460
SITE_ICONS = [
    ("switch.sonoff_1000b89874", 140, 310, TOGGLE),       # pool light
    ("switch.sonoff_1000b89a37", 300, 110, TOGGLE),       # pool garden lights
    ("switch.smart_plug_v2_f278f3_switch", 45, 580, TOGGLE),  # pump plug
]
SITE_LABELS = [
    ("sensor.smart_plug_v2_f278f3_power", 45, 630),
]


# --- helpers -----------------------------------------------------------------
def bbox(poly):
    xs, ys = [p[0] for p in poly], [p[1] for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


def pts(poly, dx=0, dy=0):
    return " ".join(f"{x - dx},{y - dy}" for x, y in poly)


def svg(w, h, body, aspect=True):
    par = "" if aspect else ' preserveAspectRatio="none"'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}"{par}>\n{body}\n</svg>\n')


def pct(w, h, x, y):
    return f"{x / w * 100:.2f}%", f"{y / h * 100:.2f}%"


def overlay_svgs(name, poly, color, inset=10, fill=True):
    """Glow + blank SVGs cropped to the polygon's bounding box."""
    x0, y0, x1, y1 = bbox(poly)
    w, h = x1 - x0, y1 - y0
    glow = f"""<defs>
  <radialGradient id="g" cx="50%" cy="50%" r="70%">
    <stop offset="0" stop-color="{color}" stop-opacity="0.55"/>
    <stop offset="1" stop-color="{color}" stop-opacity="0.12"/>
  </radialGradient>
</defs>
<polygon points="{pts(poly, x0, y0)}" fill="{'url(#g)' if fill else 'none'}" stroke="{color}" stroke-opacity="0.7" stroke-width="{inset}"/>"""
    blank = f'<rect width="{w}" height="{h}" fill="#000" fill-opacity="0"/>'
    (WWW / f"{name}_on.svg").write_text(svg(w, h, glow))
    (WWW / f"{name}_off.svg").write_text(svg(w, h, blank))
    return x0, y0, x1, y1


def icon_style(left, top):
    return {
        "left": left, "top": top,
        "--mdc-icon-size": "24px",
        "background": "rgba(15, 23, 42, 0.72)",
        "border-radius": "50%",
        "padding": "2px",
    }


def yaml_dump(elements):
    """Tiny YAML emitter (no PyYAML on the HA host)."""
    def q(v):
        if isinstance(v, bool):
            return "true" if v else "false"
        s = str(v)
        if not s or s.lower() in ("on", "off", "yes", "no", "true", "false", "null") \
                or s[0] in "-?%@`!&*" or any(c in s for c in ":#{}[],'\"|>"):
            return '"' + s.replace('"', '\\"') + '"'
        return s

    def dump(obj, ind):
        sp, out = " " * ind, []
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    out.append(f"{sp}{q(k)}:")
                    out += dump(v, ind + 4)
                else:
                    out.append(f"{sp}{q(k)}: {q(v)}")
        else:
            for item in obj:
                if isinstance(item, dict):
                    sub = dump(item, ind + 2)
                    sub[0] = sp + "- " + sub[0][ind + 2:]
                    out += sub
                else:
                    out.append(f"{sp}- {q(item)}")
        return out

    return "# Generated by build_floorplan.py - edit that file, not this one.\n" + "\n".join(dump(elements, 0)) + "\n"


# --- build -------------------------------------------------------------------
def build_upper():
    body = [f'<rect width="{UPPER_W}" height="{UPPER_H}" rx="28" fill="{BG}"/>']
    for poly in (BALCONY, ROOMS["deck"][2]):
        body.append(f'<polygon points="{pts(poly)}" fill="{OUTDOOR}" stroke="{OUTDOOR_EDGE}" '
                    f'stroke-width="4" stroke-dasharray="14 10"/>')
    # house footprint in wall colour, rooms inset on top so the gaps read as walls
    body.append(f'<rect x="55" y="300" width="1585" height="845" fill="{WALL}"/>')
    for key, (label, sub, poly, *_rest) in ROOMS.items():
        if key == "deck":
            continue
        x0, y0, x1, y1 = bbox(poly)
        if len(poly) == 4:
            body.append(f'<rect x="{x0 + 7}" y="{y0 + 7}" width="{x1 - x0 - 14}" height="{y1 - y0 - 14}" '
                        f'rx="6" fill="{ROOM}"/>')
        else:
            body.append(f'<polygon points="{pts(poly)}" fill="{ROOM}" stroke="{WALL}" '
                        f'stroke-width="14" stroke-linejoin="round"/>')
    # stairs
    for i in range(10):
        y = 770 + i * 34
        body.append(f'<line x1="805" y1="{y}" x2="920" y2="{y}" stroke="{OUTDOOR_EDGE}" stroke-width="3"/>')
    # labels
    for key, (label, sub, poly, _ent, _path, (lx, ly)) in ROOMS.items():
        body.append(f'<text x="{lx}" y="{ly}" fill="{LABEL}" font-family="Inter, Roboto, sans-serif" '
                    f'font-size="36" font-weight="600" letter-spacing="1">{label.upper()}</text>')
        if sub:
            body.append(f'<text x="{lx}" y="{ly + 34}" fill="{SUBLABEL}" '
                        f'font-family="Inter, Roboto, sans-serif" font-size="24">{sub}</text>')
    body.append(f'<text x="1260" y="100" fill="{LABEL}" font-family="Inter, Roboto, sans-serif" '
                f'font-size="36" font-weight="600" letter-spacing="1">BALCONY</text>')
    (WWW / "upper.svg").write_text(svg(UPPER_W, UPPER_H, "\n".join(body)))

    elements = []
    for key, (label, _sub, poly, ent, path, _lbl) in ROOMS.items():
        x0, y0, x1, y1 = overlay_svgs(key, poly, GLOW)
        left, top = pct(UPPER_W, UPPER_H, (x0 + x1) / 2, (y0 + y1) / 2)
        el = {"type": "image", "title": label}
        if ent:
            el["entity"] = ent
        el["image"] = f"/local/floorplan/{key}_off.svg?v={VERSION}"
        if ent:
            el["state_image"] = {"on": f"/local/floorplan/{key}_on.svg?v={VERSION}"}
        el["tap_action"] = {"action": "navigate", "navigation_path": f"/dashboard-home/{path}"}
        el["hold_action"] = {"action": "toggle"} if ent else {"action": "none"}
        el["style"] = {"left": left, "top": top, "width": f"{(x1 - x0) / UPPER_W * 100:.2f}%"}
        elements.append(el)
    for ent, x, y, opts in UPPER_ICONS:
        left, top = pct(UPPER_W, UPPER_H, x, y)
        elements.append({"type": "state-icon", "entity": ent, **opts, "style": icon_style(left, top)})
    for el, x, y, style in UPPER_EXTRA:
        left, top = pct(UPPER_W, UPPER_H, x, y)
        elements.append({**el, "style": {**icon_style(left, top), **style}})
    (OUT / "upper_elements.yaml").write_text(yaml_dump(elements))


def build_outside():
    W, H = SITE_W, SITE_H
    green, bed, paving, path = "#1f5130", "#3a3226", "#273246", "#222c3d"
    b = [f'<rect width="{W}" height="{H}" rx="20" fill="{BG}"/>']
    lot = [(25, 10), (570, 10), (570, 1100), (540, 1260), (470, 1450), (25, 1450)]
    b.append(f'<polygon points="{pts(lot)}" fill="{path}" stroke="{OUTDOOR_EDGE}" stroke-width="4"/>')
    # lawns
    b.append(f'<polygon points="{pts([(250, 800), (570, 800), (570, 1100), (540, 1260), (470, 1450), (300, 1450), (250, 1200)])}" fill="{green}"/>')
    b.append(f'<polygon points="{pts([(25, 1000), (85, 1000), (135, 1230), (25, 1230)])}" fill="{green}"/>')
    # pool garden: beds around paving
    b.append(f'<rect x="25" y="15" width="335" height="515" rx="8" fill="{bed}"/>')
    b.append(f'<rect x="55" y="45" width="275" height="455" rx="6" fill="{paving}"/>')
    b.append('<path d="M70 165 H210 V230 H260 V325 H210 V460 H70 V385 H55 V255 H70 Z" '
             'fill="#1d6fa5" stroke="#38bdf8" stroke-opacity="0.5" stroke-width="3"/>')
    b.append('<rect x="185" y="230" width="75" height="95" fill="#2391c9" stroke="#38bdf8" '
             'stroke-opacity="0.6" stroke-width="3"/>')
    # buildings
    house = [(65, 575), (405, 575), (405, 235), (500, 235), (500, 855), (385, 855), (385, 790), (65, 790)]
    b.append(f'<polygon points="{pts(house)}" fill="{ROOM}" stroke="{WALL}" stroke-width="10" stroke-linejoin="round"/>')
    b.append(f'<rect x="400" y="170" width="100" height="65" fill="{OUTDOOR}" stroke="{OUTDOOR_EDGE}" stroke-width="3" stroke-dasharray="8 6"/>')
    b.append(f'<rect x="455" y="20" width="80" height="50" fill="{OUTDOOR}" stroke="{OUTDOOR_EDGE}" stroke-width="3"/>')
    b.append(f'<rect x="385" y="855" width="115" height="85" fill="#5b3f26"/>')
    b.append(f'<rect x="80" y="790" width="170" height="210" fill="{paving}"/>')
    b.append(f'<polygon points="{pts([(85, 1000), (250, 1000), (250, 1200), (300, 1450), (175, 1450), (135, 1230)])}" fill="{paving}"/>')
    b.append(f'<rect x="25" y="555" width="40" height="45" fill="{OUTDOOR}" stroke="{OUTDOOR_EDGE}" stroke-width="3"/>')

    def text(x, y, s, size=24, color=LABEL, anchor="middle"):
        b.append(f'<text x="{x}" y="{y}" fill="{color}" font-family="Inter, Roboto, sans-serif" '
                 f'font-size="{size}" font-weight="600" text-anchor="{anchor}" letter-spacing="1">{s}</text>')

    text(135, 520, "POOL", 22)
    text(222, 360, "SPA", 18)
    text(260, 690, "HOUSE", 30)
    text(450, 210, "PORCH", 16)
    text(495, 52, "SHED", 16)
    text(442, 905, "DECK", 18)
    text(165, 900, "CARPORT", 20)
    text(205, 1150, "DRIVEWAY", 18, SUBLABEL)
    text(45, 548, "PUMP", 14, SUBLABEL)
    (WWW / "outside.svg").write_text(svg(W, H, "\n".join(b)))

    elements = []
    # garden glow: a warm ring around the pool beds; pool glow: cyan water
    garden = rect(25, 15, 360, 530)
    pool = [(70, 165), (210, 165), (210, 230), (260, 230), (260, 325), (210, 325), (210, 460),
            (70, 460), (70, 385), (55, 385), (55, 255), (70, 255)]
    for key, poly, ent, color in (("garden", garden, "switch.sonoff_1000b89a37", GLOW),
                                  ("pool", pool, "switch.sonoff_1000b89874", "#38bdf8")):
        ring = key == "garden"
        x0, y0, x1, y1 = overlay_svgs(key, poly, color, inset=34 if ring else 6, fill=not ring)
        left, top = pct(W, H, (x0 + x1) / 2, (y0 + y1) / 2)
        elements.append({
            "type": "image", "entity": ent,
            "image": f"/local/floorplan/{key}_off.svg?v={VERSION}",
            "state_image": {"on": f"/local/floorplan/{key}_on.svg?v={VERSION}"},
            "tap_action": {"action": "navigate", "navigation_path": "/dashboard-home/pool"},
            "hold_action": {"action": "toggle"},
            "style": {"left": left, "top": top, "width": f"{(x1 - x0) / W * 100:.2f}%"},
        })
    for ent, x, y, opts in SITE_ICONS:
        left, top = pct(W, H, x, y)
        elements.append({"type": "state-icon", "entity": ent, **opts, "style": icon_style(left, top)})
    for ent, x, y in SITE_LABELS:
        left, top = pct(W, H, x, y)
        elements.append({"type": "state-label", "entity": ent,
                         "style": {"left": left, "top": top, "color": LABEL, "font-size": "11px"}})
    (OUT / "outside_elements.yaml").write_text(yaml_dump(elements))


if __name__ == "__main__":
    WWW.mkdir(parents=True, exist_ok=True)
    build_upper()
    build_outside()
    print("wrote", sorted(p.name for p in WWW.iterdir()))
