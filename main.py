from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from html import escape
import json
import os
import random
import math

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

app = FastAPI(title="GharPlan AI - Architectural Floor Plan Generator")


class PlanRequest(BaseModel):
    bedrooms: int = Field(default=3, ge=1, le=6)
    plot_width: float = Field(default=70, gt=20, le=500)
    plot_length: float = Field(default=50, gt=20, le=500)
    parking: bool = True
    garden: bool = True
    attached_bath: bool = True
    utility: bool = True
    staircase: bool = True
    pooja: bool = False
    store: bool = True
    balcony: bool = False
    vastu: bool = False
    floors: int = Field(default=1, ge=1, le=4)
    orientation: str = "N"
    special_requirements: str = ""
    title: str = "GROUND FLOOR PLAN"
    variation: int = 0
    wall_type: str = "standard"


def esc(v):
    return escape(str(v))


def rect(x, y, w, h, stroke="#202020", fill="white", sw=3, rx=0):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(0,w):.1f}" height="{max(0,h):.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>'


def line(x1, y1, x2, y2, stroke="#222", sw=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def txt(x, y, value, size=16, weight="normal", anchor="middle", fill="#111"):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="Arial,Helvetica,sans-serif" '
            f'font-size="{size}px" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{esc(value)}</text>')


def room_name(x, y, name, size=16):
    return txt(x, y, name, size, "bold")


def dim_h(x1, x2, y, label):
    return (line(x1, y, x2, y, "#222", 1.5) +
            line(x1, y-7, x1, y+7, "#222", 1) +
            line(x2, y-7, x2, y+7, "#222", 1) +
            f'<path d="M{x1:.1f},{y:.1f} l9,-4 l0,8 z" fill="#222"/>' +
            f'<path d="M{x2:.1f},{y:.1f} l-9,-4 l0,8 z" fill="#222"/>' +
            txt((x1+x2)/2, y-9, label, 14, "bold"))


def dim_v(y1, y2, x, label):
    mid = (y1+y2)/2
    return (line(x, y1, x, y2, "#222", 1.5) +
            line(x-7, y1, x+7, y1, "#222", 1) +
            line(x-7, y2, x+7, y2, "#222", 1) +
            f'<path d="M{x:.1f},{y1:.1f} l-4,9 l8,0 z" fill="#222"/>' +
            f'<path d="M{x:.1f},{y2:.1f} l-4,-9 l8,0 z" fill="#222"/>' +
            f'<text x="{x-11:.1f}" y="{mid:.1f}" font-family="Arial" font-size="14px" '
            f'font-weight="bold" text-anchor="middle" transform="rotate(-90 {x-11:.1f} {mid:.1f})">{esc(label)}</text>')


def label_box(x, y, w, h, name, rw, rh, fill="white", furniture=None):
    s = [rect(x, y, w, h, "#202020", fill, 3)]
    fs = 15 if min(w,h) > 110 else 11
    s.append(room_name(x+w/2, y+min(34,h*.28), name, fs))
    s.append(txt(x+w/2, y+min(57,h*.28+23), f'{rw:.0f}\'-0" X {rh:.0f}\'-0"', max(9,fs-2)))
    if furniture:
        s.append(furniture(x,y,w,h))
    return "".join(s)


def bed_symbol(x,y,w,h):
    bw, bh = w*.48, h*.42
    bx, by = x+(w-bw)/2, y+(h-bh)/2+8
    return (rect(bx,by,bw,bh,"#555","white",1.5) +
            line(bx+bw/2,by,bx+bw/2,by+35,"#777",1) +
            rect(bx+8,by+8,bw/2-12,27,"#777","#fafafa",1) +
            rect(bx+bw/2+4,by+8,bw/2-12,27,"#777","#fafafa",1))


def sofa_symbol(x,y,w,h):
    return rect(x+w*.18,y+h*.55,w*.64,h*.16,"#555","white",2) + rect(x+w*.25,y+h*.37,w*.5,h*.18,"#555","white",2)


def table_symbol(x,y,w,h):
    cx,cy=x+w/2,y+h/2
    return (f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{w*.20:.1f}" ry="{h*.16:.1f}" fill="white" stroke="#555" stroke-width="2"/>' +
            "".join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="9" fill="white" stroke="#555" stroke-width="2"/>'
                    for px,py in [(cx-w*.30,cy),(cx+w*.30,cy),(cx,cy-h*.27),(cx,cy+h*.27)]))


def kitchen_symbol(x,y,w,h):
    return rect(x+w*.08,y+h*.70,w*.84,h*.12,"#444","#f7f7f7",2) + \
           f'<circle cx="{x+w*.26:.1f}" cy="{y+h*.76:.1f}" r="9" fill="none" stroke="#555" stroke-width="2"/>' + \
           f'<circle cx="{x+w*.33:.1f}" cy="{y+h*.76:.1f}" r="9" fill="none" stroke="#555" stroke-width="2"/>'


def toilet_symbol(x,y):
    return f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="12" ry="16" fill="white" stroke="#444" stroke-width="2"/><rect x="{x-8:.1f}" y="{y-25:.1f}" width="16" height="10" fill="white" stroke="#444" stroke-width="2"/>'


def basin(x,y):
    return f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="19" ry="11" fill="white" stroke="#444" stroke-width="2"/>'


def car_symbol(x,y,w,h):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{w*.15:.1f}" fill="white" stroke="#555" stroke-width="2"/>' +
            f'<rect x="{x+w*.2:.1f}" y="{y+h*.17:.1f}" width="{w*.6:.1f}" height="{h*.24:.1f}" rx="8" fill="#eee" stroke="#555"/>' +
            f'<rect x="{x+w*.2:.1f}" y="{y+h*.58:.1f}" width="{w*.6:.1f}" height="{h*.18:.1f}" rx="8" fill="#eee" stroke="#555"/>')


def stair_symbol(x,y,w,h):
    s=[rect(x,y,w,h,"#222","white",2)]
    for i in range(1,10):
        s.append(line(x,y+i*h/10,x+w,y+i*h/10,"#777",1))
    s.append(line(x+w/2,y+h-18,x+w/2,y+18,"#222",2))
    s.append(f'<path d="M{x+w/2:.1f},{y+18:.1f} l-7,12 l14,0 z" fill="#222"/>')
    s.append(txt(x+w/2,y+h+19,"UP",12,"bold"))
    return "".join(s)


def compass(x,y,ori):
    return (f'<circle cx="{x}" cy="{y}" r="38" fill="white" stroke="#222" stroke-width="2"/>' +
            f'<path d="M{x},{y-32} L{x+8},{y} L{x},{y+32} L{x-8},{y} Z" fill="#222"/>' +
            txt(x,y-46,"N",15,"bold") + txt(x,y+59,"S",15,"bold") +
            txt(x-50,y+5,"W",15,"bold") + txt(x+50,y+5,"E",15,"bold") +
            txt(x,y+80,f"FACING {ori}",11,"bold"))


def ai_style(req):
    styles = [
        "courtyard",
        "central_living",
        "side_bedrooms",
        "split_bedrooms",
        "rear_service",
        "front_garden",
        "compact_core",
        "wide_living",
    ]
    seed = req.variation or random.randint(1, 10_000_000)
    rng = random.Random(seed)
    fallback = styles[seed % len(styles)]

    key = os.getenv("OPENAI_API_KEY")
    if not key or OpenAI is None:
        return fallback, seed, "Local architectural variation"

    try:
        client = OpenAI(api_key=key)
        prompt = f"""
You are an architectural space-planning assistant. Select ONE layout strategy for a conceptual
Indian residential ground-floor plan. Do not design the drawing; only select the strategy.
Requirements: {req.bedrooms} bedrooms, plot {req.plot_width} x {req.plot_length} ft,
orientation {req.orientation}, parking={req.parking}, garden={req.garden},
attached_bath={req.attached_bath}, utility={req.utility}, staircase={req.staircase},
pooja={req.pooja}, store={req.store}, balcony={req.balcony}, vastu={req.vastu}.
Special requirements: {req.special_requirements or "none"}.
Variation seed: {seed}.
Choose exactly one of: {", ".join(styles)}.
Return only JSON: {{"style":"one_choice","reason":"short phrase"}}
"""
        response = client.responses.create(model=os.getenv("OPENAI_LAYOUT_MODEL","gpt-5.4-mini"), input=prompt)
        data = json.loads(response.output_text)
        style = data.get("style")
        if style in styles:
            return style, seed, data.get("reason","AI selected layout")
    except Exception:
        pass
    return fallback, seed, "Local fallback variation"



def _room(name, x, y, w, h, kind, door="south", window="outer"):
    """Normalized room geometry. x/y/w/h are fractions of the usable house rectangle."""
    return {
        "name": name, "x": x, "y": y, "w": w, "h": h,
        "kind": kind, "door": door, "window": window
    }


def make_rooms(req, style):
    """
    Build a clean, non-overlapping conceptual architectural plan.
    The geometry uses a house footprint inside the plot and keeps service,
    bedroom, public and entrance zones separated.
    """
    b = max(1, req.bedrooms)

    # House footprint is deliberately inset from the plot boundary so the
    # drawing reads like a site/architectural plan rather than touching the road.
    left, top, right, bottom = 0.08, 0.28, 0.92, 0.88
    W = right - left
    H = bottom - top

    rooms = []

    # Public zone: foyer + living + dining.
    rooms += [
        _room("FOYER", left + W*.40, top + H*.79, W*.20, H*.21, "foyer", "south"),
        _room("LIVING ROOM", left + W*.25, top + H*.31, W*.43, H*.38, "living", "east"),
        _room("DINING", left + W*.52, top + H*.08, W*.23, H*.23, "dining", "south"),
    ]

    # Left bedroom wing. Up to four bedrooms are stacked with realistic proportions.
    bx, by, bw = left, top + H*.08, W*.25
    available_h = H*.78
    if b <= 2:
        bed_h = available_h / 2
        bed_count = b
    else:
        bed_count = min(b, 4)
        bed_h = available_h / bed_count

    for i in range(bed_count):
        y = by + i*bed_h
        name = "MASTER BEDROOM" if i == 0 else f"BEDROOM {i+1}"
        rooms.append(_room(name, bx, y, bw, bed_h-.006, "bedroom", "east", "west"))

    # If more than four bedrooms are requested, put additional bedrooms in the
    # right/rear wing rather than overlapping existing rooms.
    extra = b - bed_count
    for i in range(extra):
        idx = i + 1
        rooms.append(_room(f"BEDROOM {bed_count+i+1}",
                           left + W*.68, top + H*(.55 + i*.16),
                           W*.24, H*.15, "bedroom", "west", "east"))

    # Service block.
    rooms.append(_room("KITCHEN", left + W*.68, top + H*.08,
                       W*.24, H*.23, "kitchen", "south", "east"))

    if req.utility:
        rooms.append(_room("UTILITY", left + W*.68, top + H*.31,
                           W*.12, H*.13, "utility", "south", "east"))
    if req.store:
        rooms.append(_room("STORE", left + W*.80, top + H*.31,
                           W*.12, H*.13, "store", "south", "east"))

    if req.staircase:
        rooms.append(_room("STAIRCASE", left + W*.68, top + H*.44,
                           W*.24, H*.22, "stairs", "south", "east"))

    # Toilets sit against the service/core side.
    rooms.append(_room("COMMON TOILET", left + W*.68, top + H*.67,
                       W*.12, H*.13, "bath", "west", "east"))

    if req.attached_bath:
        # Attached master bath is placed beside the master, never on top of it.
        m = rooms[0]
        rooms.append(_room("MASTER BATH",
                           m["x"] + m["w"]*.55, m["y"],
                           m["w"]*.45, m["h"]*.42,
                           "bath", "west", "west"))

    if req.pooja:
        rooms.append(_room("POOJA ROOM", left + W*.53, top + H*.67,
                           W*.13, H*.13, "pooja", "south", "north"))

    if req.balcony:
        rooms.append(_room("BALCONY", left + W*.29, bottom,
                           W*.42, .045, "balcony", "north", "south"))

    return rooms


def door_symbol(x, y, w, h, side="south", door_w=0.82):
    """CAD-style door leaf + swing arc. Coordinates are SVG pixels."""
    s = []
    d = min(w, h) * .18
    if side == "south":
        gx = x + w*.5
        gy = y + h
        dw = min(w*.32, 62)
        s.append(line(gx-dw/2, gy, gx+dw/2, gy, "#fff", 8))
        s.append(line(gx, gy, gx, gy-dw, "#333", 2))
        s.append(f'<path d="M{gx-dw/2:.1f},{gy:.1f} A{dw/2:.1f},{dw/2:.1f} 0 0 1 {gx:.1f},{gy-dw:.1f}" fill="none" stroke="#555" stroke-width="1.5"/>')
    elif side == "north":
        gx = x + w*.5
        gy = y
        dw = min(w*.32, 62)
        s.append(line(gx-dw/2, gy, gx+dw/2, gy, "#fff", 8))
        s.append(line(gx, gy, gx, gy+dw, "#333", 2))
        s.append(f'<path d="M{gx-dw/2:.1f},{gy:.1f} A{dw/2:.1f},{dw/2:.1f} 0 0 0 {gx:.1f},{gy+dw:.1f}" fill="none" stroke="#555" stroke-width="1.5"/>')
    elif side == "east":
        gx = x + w
        gy = y + h*.5
        dw = min(h*.32, 62)
        s.append(line(gx, gy-dw/2, gx, gy+dw/2, "#fff", 8))
        s.append(line(gx, gy, gx-dw, gy, "#333", 2))
        s.append(f'<path d="M{gx:.1f},{gy-dw/2:.1f} A{dw/2:.1f},{dw/2:.1f} 0 0 0 {gx-dw:.1f},{gy:.1f}" fill="none" stroke="#555" stroke-width="1.5"/>')
    else:
        gx = x
        gy = y + h*.5
        dw = min(h*.32, 62)
        s.append(line(gx, gy-dw/2, gx, gy+dw/2, "#fff", 8))
        s.append(line(gx, gy, gx+dw, gy, "#333", 2))
        s.append(f'<path d="M{gx:.1f},{gy-dw/2:.1f} A{dw/2:.1f},{dw/2:.1f} 0 0 1 {gx+dw:.1f},{gy:.1f}" fill="none" stroke="#555" stroke-width="1.5"/>')
    return "".join(s)


def window_symbol(x, y, w, h, side):
    """Double-line window opening."""
    s = []
    if side in ("north", "south"):
        ww = max(34, min(w*.32, 100))
        cx = x + w/2
        yy = y if side == "north" else y+h
        s.append(line(cx-ww/2, yy, cx+ww/2, yy, "#fff", 10))
        s.append(line(cx-ww/2, yy-3 if side=="north" else yy+3,
                      cx+ww/2, yy-3 if side=="north" else yy+3, "#555", 2))
        s.append(line(cx, yy-8 if side=="north" else yy+8,
                      cx, yy+8 if side=="north" else yy-8, "#777", 1.5))
    else:
        wh = max(34, min(h*.32, 100))
        cy = y+h/2
        xx = x if side == "west" else x+w
        s.append(line(xx, cy-wh/2, xx, cy+wh/2, "#fff", 10))
        s.append(line(xx-3 if side=="west" else xx+3, cy-wh/2,
                      xx-3 if side=="west" else xx+3, cy+wh/2, "#555", 2))
        s.append(line(xx-8 if side=="west" else xx+8, cy,
                      xx+8 if side=="west" else xx-8, cy, "#777", 1.5))
    return "".join(s)


def room_area_text(req, r):
    rw = max(.1, r["w"] * req.plot_width * .84)
    rh = max(.1, r["h"] * req.plot_length * .60)
    return f'{rw:.0f}\'-0" X {rh:.0f}\'-0"'


def furniture_for_room(r, x, y, w, h):
    k = r["kind"]
    if k == "bedroom":
        return bed_symbol(x, y, w, h)
    if k == "living":
        return sofa_symbol(x, y, w, h)
    if k == "dining":
        return table_symbol(x, y, w, h)
    if k == "kitchen":
        return kitchen_symbol(x, y, w, h)
    if k == "bath":
        return toilet_symbol(x+w*.34, y+h*.64) + basin(x+w*.70, y+h*.52)
    if k == "stairs":
        return stair_symbol(x+12, y+12, max(40,w-24), max(50,h-24))
    if k == "foyer":
        return rect(x+w*.30, y+h*.38, w*.40, h*.20, "#777", "white", 1.5)
    return ""


def site_zone(req, x, y, w, h, name, kind):
    s = [rect(x, y, w, h, "#333", "#fafafa", 2)]
    s.append(room_name(x+w/2, y+h*.42, name, 14))
    if kind == "parking":
        if req.special_requirements and "two cars" in req.special_requirements.lower():
            s.append(car_symbol(x+w*.17, y+h*.40, w*.25, h*.43))
            s.append(car_symbol(x+w*.58, y+h*.40, w*.25, h*.43))
        else:
            s.append(car_symbol(x+w*.35, y+h*.40, w*.30, h*.43))
    elif kind == "garden":
        for i in range(6):
            s.append(f'<circle cx="{x+22+i*w/6:.1f}" cy="{y+h*.18:.1f}" r="9" fill="none" stroke="#555" stroke-width="2"/>')
        s.append(line(x+15, y+h*.75, x+w-15, y+h*.75, "#888", 1, "6 5"))
    return "".join(s)


def generate_plan(req: PlanRequest):
    style, seed, reason = ai_style(req)

    W, H = 1900, 1400
    L, T, R, B = 125, 175, 1775, 1045
    PW, PH = R-L, B-T

    s = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="auto">',
        '<rect width="1900" height="1400" fill="white"/>',
        txt(W/2, 42, f"{req.title} — {req.bedrooms}BHK RESIDENCE", 28, "bold"),
        txt(W/2, 70, f'PLOT {req.plot_width:g}\'-0" × {req.plot_length:g}\'-0"  |  ROAD / FACING: {req.orientation}', 15),
    ]

    # Plot/site boundary and setbacks.
    s.append(rect(L, T, PW, PH, "#111", "white", 6))
    setback = 28
    s.append(rect(L+setback, T+setback, PW-2*setback, PH-2*setback, "#999", "none", 1.2, 0))

    # Site zones.
    front_y = T + 20
    front_h = PH*.20
    if req.garden:
        s.append(site_zone(req, L+25, front_y, PW*.34, front_h, "GARDEN", "garden"))
    if req.parking:
        px = L + PW*.62 if req.garden else L+25
        s.append(site_zone(req, px, front_y, PW*.30, front_h, "CAR PARKING", "parking"))

    # Main house footprint.
    house_x = L + PW*.08
    house_y = T + PH*.28
    house_w = PW*.84
    house_h = PH*.60
    wall_sizes = {
        "standard": (8, 4.5),
        "thick": (11, 6),
        "thin": (6, 4),
        "rcc_infill": (8, 4.5),
    }
    wall, inner = wall_sizes.get(req.wall_type, wall_sizes["standard"])
    s.append(rect(house_x, house_y, house_w, house_h, "#111", "white", wall))

    rooms = make_rooms(req, style)

    # Room fills and partitions.
    for r in rooms:
        x = house_x + r["x"] * PW
        y = T + r["y"] * PH
        w = r["w"] * PW
        h = r["h"] * PH
        s.append(rect(x, y, w, h, "#333", "#fff", 5))
        fs = 15 if min(w,h) > 125 else 11
        s.append(room_name(x+w/2, y+min(34,h*.25), r["name"], fs))
        s.append(txt(x+w/2, y+min(56,h*.25+22), room_area_text(req, r), max(9, fs-2), "normal"))
        furn = furniture_for_room(r, x, y, w, h)
        if furn:
            s.append(furn)

    # Doors on internal circulation edges.
    for r in rooms:
        x = house_x + r["x"] * PW
        y = T + r["y"] * PH
        w = r["w"] * PW
        h = r["h"] * PH
        s.append(door_symbol(x, y, w, h, r["door"]))

    # Perimeter windows based on exposed sides.
    for r in rooms:
        x = house_x + r["x"] * PW
        y = T + r["y"] * PH
        w = r["w"] * PW
        h = r["h"] * PH
        side = r["window"]
        if side == "west" and abs(x-house_x) < 4:
            s.append(window_symbol(x, y, w, h, "west"))
        elif side == "east" and abs((x+w)-(house_x+house_w)) < 4:
            s.append(window_symbol(x, y, w, h, "east"))
        elif side == "north" and abs(y-house_y) < 4:
            s.append(window_symbol(x, y, w, h, "north"))
        elif side == "south" and abs((y+h)-(house_y+house_h)) < 4:
            s.append(window_symbol(x, y, w, h, "south"))

    # Main entrance + porch/verandah.
    if req.orientation == "N":
        ex, ey = house_x+house_w*.50, house_y
        s.append(door_symbol(ex-house_w*.04, ey-1, house_w*.08, 20, "north"))
        s.append(txt(ex, ey-24, "MAIN ENTRANCE", 13, "bold"))
    elif req.orientation == "S":
        ex, ey = house_x+house_w*.50, house_y+house_h
        s.append(door_symbol(ex-house_w*.04, ey-20, house_w*.08, 20, "south"))
        s.append(txt(ex, ey+34, "MAIN ENTRANCE", 13, "bold"))
    elif req.orientation == "E":
        ex, ey = house_x+house_w, house_y+house_h*.50
        s.append(door_symbol(ex-20, ey-house_h*.04, 20, house_h*.08, "east"))
        s.append(txt(ex+55, ey, "MAIN ENTRANCE", 13, "bold", "start"))
    else:
        ex, ey = house_x, house_y+house_h*.50
        s.append(door_symbol(ex, ey-house_h*.04, 20, house_h*.08, "west"))
        s.append(txt(ex-55, ey, "MAIN ENTRANCE", 13, "bold", "end"))

    # Balcony/verandah outline.
    if req.balcony:
        bx = house_x + house_w*.28
        by = house_y + house_h
        bw = house_w*.44
        bh = 55
        s.append(rect(bx, by, bw, bh, "#555", "#fafafa", 3))
        s.append(txt(bx+bw/2, by+31, "BALCONY / VERANDAH", 13, "bold"))
    else:
        bx = house_x + house_w*.34
        by = house_y + house_h
        bw = house_w*.32
        bh = 45
        s.append(rect(bx, by, bw, bh, "#555", "#fafafa", 3))
        s.append(txt(bx+bw/2, by+27, "VERANDAH", 12, "bold"))

    # Dimension chains.
    s.append(dim_h(L, R, T-42, f'{req.plot_width:g}\'-0"'))
    s.append(dim_v(T, B, L-45, f'{req.plot_length:g}\'-0"'))
    s.append(dim_h(house_x, house_x+house_w, house_y-24,
                   f'{req.plot_width*.84:g}\'-0"'))
    s.append(dim_v(house_y, house_y+house_h, house_x-24,
                   f'{req.plot_length*.60:g}\'-0"'))

    # North arrow.
    s.append(compass(1660, 1180, req.orientation))

    # Professional title block.
    by = 1115
    s.append(rect(35, by, 1310, 210, "#222", "white", 2))
    s.append(txt(55, by+30, f"{req.title} — {req.bedrooms}BHK HOUSE", 18, "bold", "start"))
    s.append(txt(55, by+58, f'PLOT SIZE: {req.plot_width:g}\'-0" × {req.plot_length:g}\'-0"', 13, "normal", "start"))
    s.append(txt(55, by+83, f"PLOT AREA: {req.plot_width*req.plot_length:,.0f} SQ.FT.", 13, "normal", "start"))
    s.append(txt(55, by+108, f"ORIENTATION: {req.orientation}   |   FLOORS: {req.floors}", 13, "normal", "start"))
    s.append(txt(55, by+133, f"LAYOUT TYPE: {style.upper()}   |   VARIATION: {seed}", 12, "normal", "start"))
    wall_labels = {
        "standard": '9" external / 4.5" internal',
        "thick": '9" external / 6" internal',
        "thin": '6" external / 4.5" internal',
        "rcc_infill": '9" external / 4.5" internal — RCC frame/infill concept',
    }
    wall_label = wall_labels.get(req.wall_type, wall_labels["standard"])
    s.append(txt(55, by+158, f"WALLS: {wall_label.upper()} (CONCEPTUAL)", 11, "normal", "start"))
    s.append(txt(55, by+182, "CONCEPTUAL DESIGN — VERIFY STRUCTURE, SETBACKS AND LOCAL BY-LAWS BEFORE CONSTRUCTION", 10, "bold", "start"))

    s.append(rect(1370, by, 495, 210, "#222", "white", 2))
    s.append(txt(1390, by+30, "ARCHITECTURAL NOTES", 16, "bold", "start"))
    notes = [
        "• CAD-style wall, door and window graphics",
        "• Furniture and sanitary fixtures shown",
        "• Dimensioned site and house footprint",
        "• Final working drawing by licensed architect",
        f"• Layout strategy: {reason}",
    ]
    for i, n in enumerate(notes):
        s.append(txt(1390, by+61+i*27, n, 11, "normal", "start"))

    s.append(txt(950, 1375, "GHARPLAN AI  •  ARCHITECTURAL FLOOR PLAN GENERATOR  •  BY ANIK KUMAR", 13, "bold"))
    s.append("</svg>")
    return "".join(s)


HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GharPlan AI</title>
<style>
*{box-sizing:border-box}
body{font-family:Arial,Helvetica,sans-serif;background:#f5f6fa;margin:0;color:#202124}
header{background:#fff;padding:24px 16px;text-align:center;border-bottom:1px solid #ddd}
h1{margin:0;color:#4f46e5;font-size:34px}.byline{margin:7px 0 0;font-weight:700;color:#555}
.container{max-width:1050px;margin:20px auto;padding:16px}.card{background:#fff;padding:24px;border-radius:18px;box-shadow:0 4px 20px rgba(0,0,0,.08)}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
label{font-weight:700;display:block;margin-bottom:5px}
input,select,textarea{width:100%;padding:14px;margin-top:4px;border:1px solid #ccc;border-radius:9px;font-size:16px;background:#fff}
textarea{min-height:90px;resize:vertical}
.full{grid-column:1/-1}
.checks{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:10px}
.check{border:1px solid #ddd;border-radius:9px;padding:10px;font-weight:600}.check input{width:auto;margin-right:8px}
button{margin-top:20px;width:100%;padding:16px;border:0;border-radius:11px;background:#4f46e5;color:#fff;font-size:18px;font-weight:800;cursor:pointer}
button:disabled{opacity:.6;cursor:wait}
#result{margin-top:28px}#planWrap{border:1px solid #ccc;background:#fff;overflow:hidden}
#planWrap svg{display:block;width:100%;height:auto}
.download{display:inline-block;text-align:center;text-decoration:none;background:#111;color:#fff;padding:13px 18px;border-radius:9px;margin-top:14px;font-weight:700}
.status{padding:12px;border-radius:8px;background:#eef2ff;margin-top:12px}
@media(max-width:700px){.grid{grid-template-columns:1fr}.checks{grid-template-columns:1fr 1fr}.card{padding:18px}h1{font-size:28px}.container{padding:10px}}
@media(max-width:430px){.checks{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
<h1>GharPlan AI</h1>
<p>Architectural Floor Plan Generator</p>
<p class="byline">by ANIK KUMAR</p>
</header>
<div class="container"><div class="card">
<h2>Create Your Floor Plan</h2>
<div class="grid">
<div><label>Bedrooms / BHK</label><input id="bedrooms" type="number" value="3" min="1" max="6"></div>
<div><label>Number of Floors</label><input id="floors" type="number" value="1" min="1" max="4"></div>
<div><label>Plot Width (ft)</label><input id="plot_width" type="number" value="70" min="21" max="500" step="0.5"></div>
<div><label>Plot Length (ft)</label><input id="plot_length" type="number" value="50" min="21" max="500" step="0.5"></div>
<div><label>Road / Main Orientation</label><select id="orientation"><option value="N">North</option><option value="E">East</option><option value="S">South</option><option value="W">West</option></select></div>
<div><label>Planning Preference</label><select id="vastu"><option value="false">Flexible</option><option value="true">Vastu-conscious</option></select></div>
<div><label>Wall Type</label><select id="wall_type">
<option value="standard">Standard Masonry — 9" External / 4.5" Internal</option>
<option value="thick">Heavy Wall — 9" External / 6" Internal</option>
<option value="thin">Light Wall — 6" External / 4.5" Internal</option>
<option value="rcc_infill">RCC Frame + Infill — Concept</option>
</select></div>
<div class="full"><label>Required Spaces</label>
<div class="checks">
<label class="check"><input id="parking" type="checkbox" checked>Car Parking</label>
<label class="check"><input id="garden" type="checkbox" checked>Garden</label>
<label class="check"><input id="attached_bath" type="checkbox" checked>Attached Bath</label>
<label class="check"><input id="utility" type="checkbox" checked>Utility</label>
<label class="check"><input id="staircase" type="checkbox" checked>Staircase</label>
<label class="check"><input id="store" type="checkbox" checked>Store</label>
<label class="check"><input id="pooja" type="checkbox">Pooja Room</label>
<label class="check"><input id="balcony" type="checkbox">Balcony</label>
</div></div>
<div class="full"><label>Special Requirements</label><textarea id="special" placeholder="Example: large master bedroom, elderly-friendly toilet, two cars, separate dining, etc."></textarea></div>
</div>
<button id="generateBtn" onclick="generatePlan()">GENERATE NEW FLOOR PLAN</button>
<div id="result"></div>
</div></div>

<script>
let variation=0;

async function generatePlan(){
 const btn=document.getElementById("generateBtn"), result=document.getElementById("result");
 const bedrooms=Number(document.getElementById("bedrooms").value);
 const width=Number(document.getElementById("plot_width").value);
 const length=Number(document.getElementById("plot_length").value);
 if(!Number.isFinite(bedrooms)||bedrooms<1||bedrooms>6){result.innerHTML='<p style="color:red">BHK must be between 1 and 6.</p>';return}
 if(!Number.isFinite(width)||width<=20||width>500||!Number.isFinite(length)||length<=20||length>500){result.innerHTML='<p style="color:red">Plot dimensions must be greater than 20 ft and no more than 500 ft.</p>';return}

 variation++;
 btn.disabled=true;
 btn.textContent="GENERATING NEW PLAN...";
 result.innerHTML='<div class="status">Creating a new architectural layout...</div>';

 const data={
  bedrooms, plot_width:width, plot_length:length,
  floors:Number(document.getElementById("floors").value),
  orientation:document.getElementById("orientation").value,
  vastu:document.getElementById("vastu").value==="true",
  parking:document.getElementById("parking").checked,
  garden:document.getElementById("garden").checked,
  attached_bath:document.getElementById("attached_bath").checked,
  utility:document.getElementById("utility").checked,
  staircase:document.getElementById("staircase").checked,
  store:document.getElementById("store").checked,
  pooja:document.getElementById("pooja").checked,
  balcony:document.getElementById("balcony").checked,
  special_requirements:document.getElementById("special").value,
  title:"GROUND FLOOR PLAN",
  variation:variation
 };
 try{
  const response=await fetch("/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
  if(!response.ok){
    let detail="";
    try{const e=await response.json();detail=e.detail||""}catch(_){}
    throw new Error(detail||("Server returned "+response.status));
  }
  const svg=await response.text();
  const blob=new Blob([svg],{type:"image/svg+xml"});
  const url=URL.createObjectURL(blob);
  result.innerHTML='<h3>Generated Plan - Variation '+variation+'</h3><div id="planWrap">'+svg+
    '</div><a class="download" href="'+url+'" download="gharplan-variation-'+variation+'.svg">DOWNLOAD PLAN</a>';
 }catch(error){
  result.innerHTML='<h3 style="color:red">Generation failed</h3><p>'+String(error.message).replace(/[<>]/g,"")+'</p>';
 }finally{
  btn.disabled=false;btn.textContent="GENERATE NEW FLOOR PLAN";
 }
}
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return HTML


@app.post("/generate")
def generate(req: PlanRequest):
    return Response(content=generate_plan(req), media_type="image/svg+xml")


@app.get("/health")
def health():
    return {"status":"ok","service":"GharPlan AI","ai_enabled":bool(os.getenv("OPENAI_API_KEY"))}
