from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field
from html import escape
import math

app = FastAPI(title="GharPlan AI - Architectural Floor Plan Generator")


class PlanRequest(BaseModel):
    bedrooms: int = Field(default=3, ge=1, le=6)
    plot_width: float = Field(default=70, gt=20, le=150)
    plot_length: float = Field(default=50, gt=20, le=150)
    parking: bool = True
    garden: bool = True
    attached_bath: bool = True
    utility: bool = True
    staircase: bool = True
    orientation: str = "N"
    title: str = "GROUND FLOOR PLAN"


def rect(x, y, w, h, stroke="#111", fill="white", sw=3):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def line(x1, y1, x2, y2, stroke="#111", sw=2):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"/>'


def text(x, y, value, size=16, weight="normal", anchor="middle", fill="#111"):
    return (f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" '
            f'font-size="{size}px" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">'
            f'{escape(str(value))}</text>')


def room_label(x, y, name):
    return text(x, y, name, 17, "bold")


def window(x, y, w, horizontal=True):
    if horizontal:
        return line(x, y, x + w, y, "#555", 5) + line(x, y + 7, x + w, y + 7, "#555", 2)
    return line(x, y, x, y + w, "#555", 5) + line(x + 7, y, x + 7, y + w, "#555", 2)


def dimension_horizontal(x1, x2, y, label):
    return (line(x1, y, x2, y, "#222", 1.5) +
            line(x1, y - 7, x1, y + 7, "#222", 1) +
            line(x2, y - 7, x2, y + 7, "#222", 1) +
            f'<path d="M {x1} {y} l 9 -4 l 0 8 z" fill="#222"/>' +
            f'<path d="M {x2} {y} l -9 -4 l 0 8 z" fill="#222"/>' +
            text((x1 + x2) / 2, y - 8, label, 14, "bold"))


def dimension_vertical(y1, y2, x, label):
    mid = (y1 + y2) / 2
    return (line(x, y1, x, y2, "#222", 1.5) +
            line(x - 7, y1, x + 7, y1, "#222", 1) +
            line(x - 7, y2, x + 7, y2, "#222", 1) +
            f'<path d="M {x} {y1} l -4 9 l 8 0 z" fill="#222"/>' +
            f'<path d="M {x} {y2} l -4 -9 l 8 0 z" fill="#222"/>' +
            f'<text x="{x-10}" y="{mid}" font-family="Arial" font-size="14px" '
            f'font-weight="bold" text-anchor="middle" transform="rotate(-90 {x-10} {mid})">'
            f'{escape(label)}</text>')


def bed(x, y, w, h):
    return (rect(x, y, w, h, "#444", "white", 1.5) +
            rect(x + 8, y + 8, (w - 20) / 2, 35, "#777", "#fafafa", 1) +
            rect(x + w / 2 + 2, y + 8, (w - 20) / 2, 35, "#777", "#fafafa", 1) +
            line(x + w / 2, y + 8, x + w / 2, y + 43, "#777", 1))


def sofa(x, y, w, h):
    return rect(x, y, w, h, "#555", "#fafafa", 2) + rect(x + 10, y + 8, w - 20, h - 16, "#777", "none", 1)


def dining_table(x, y, w, h):
    s = [f'<ellipse cx="{x+w/2}" cy="{y+h/2}" rx="{w/2}" ry="{h/2}" fill="white" stroke="#444" stroke-width="2"/>']
    for cx, cy in [(x-20,y+h/2),(x+w+20,y+h/2),(x+w/2,y-20),(x+w/2,y+h+20)]:
        s.append(f'<circle cx="{cx}" cy="{cy}" r="12" fill="white" stroke="#555" stroke-width="2"/>')
    return "".join(s)


def kitchen_counter(x, y, w, h):
    s = [rect(x, y, w, h, "#333", "#f5f5f5", 2)]
    sx, sy = x + w/2 - 30, y + 10
    s.append(rect(sx, sy, 60, 40, "#555", "white", 1))
    for dx in [15, 45]:
        for dy in [13, 28]:
            s.append(f'<circle cx="{sx+dx}" cy="{sy+dy}" r="5" fill="none" stroke="#555"/>')
    s.append(rect(x+w-55, y+10, 35, 30, "#555", "white", 1))
    return "".join(s)


def toilet_symbol(x, y):
    return (f'<ellipse cx="{x}" cy="{y}" rx="13" ry="18" fill="white" stroke="#444" stroke-width="2"/>'
            f'<rect x="{x-9}" y="{y-28}" width="18" height="12" fill="white" stroke="#444" stroke-width="2"/>')


def wash_basin(x, y):
    return f'<ellipse cx="{x}" cy="{y}" rx="22" ry="13" fill="white" stroke="#444" stroke-width="2"/>'


def car(x, y, w, h):
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w*.15}" fill="white" stroke="#555" stroke-width="2"/>',
         f'<rect x="{x+w*.2}" y="{y+h*.18}" width="{w*.6}" height="{h*.25}" rx="8" fill="#eee" stroke="#555"/>',
         f'<rect x="{x+w*.2}" y="{y+h*.57}" width="{w*.6}" height="{h*.2}" rx="8" fill="#eee" stroke="#555"/>']
    for yy in [y+h*.18, y+h*.68]:
        s += [f'<circle cx="{x+5}" cy="{yy}" r="7" fill="#333"/>',
              f'<circle cx="{x+w-5}" cy="{yy}" r="7" fill="#333"/>']
    return "".join(s)


def stairs(x, y, w, h):
    s = [rect(x, y, w, h, "#222", "white", 2)]
    step_h = h / 9
    for i in range(1, 9):
        s.append(line(x, y+i*step_h, x+w, y+i*step_h, "#555", 1))
    s.append(line(x+w/2, y+h-15, x+w/2, y+15, "#222", 2))
    s.append(f'<path d="M {x+w/2} {y+15} l -7 12 l 14 0 z" fill="#222"/>')
    s.append(text(x+w/2, y+h+20, "UP", 13, "bold"))
    return "".join(s)


def compass(x, y):
    return (f'<circle cx="{x}" cy="{y}" r="34" fill="white" stroke="#222" stroke-width="2"/>'
            f'<path d="M {x} {y-30} L {x+7} {y} L {x} {y+30} L {x-7} {y} Z" fill="#222"/>'
            f'<path d="M {x} {y+30} L {x+7} {y} L {x} {y-30} L {x-7} {y} Z" fill="white" stroke="#222"/>'
            + text(x, y-43, "N", 15, "bold") + text(x, y+55, "S", 15, "bold")
            + text(x-45, y+5, "W", 15, "bold") + text(x+45, y+5, "E", 15, "bold"))


def generate_plan(req: PlanRequest):
    W, H = 1800, 1250
    left, top, right, bottom = 150, 150, 1650, 900
    plot_w, plot_h = right-left, bottom-top
    sx, sy = plot_w/req.plot_width, plot_h/req.plot_length
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
    s.append(rect(0, 0, W, H, "#222", "white", 0))
    s.append(text(W/2, 45, f'{req.title} - {req.bedrooms}BHK', 25, "bold"))
    s.append(text(W/2, 75, f'PLOT SIZE - {req.plot_width:g}\'-0" X {req.plot_length:g}\'-0"', 14))
    s.append(rect(left, top, plot_w, plot_h, "#111", "#fff", 6))

    garden_w = plot_w*.20
    parking_w = plot_w*.27
    center_x = left+garden_w
    right_zone_x = right-parking_w

    garden_h = plot_h*.43
    if req.garden:
        s.append(rect(left+4, top+4, garden_w-8, garden_h-8, "#444", "#f8f8f8", 3))
        s.append(room_label(left+garden_w/2, top+garden_h/2, "GARDEN"))
        s.append(text(left+garden_w/2, top+garden_h/2+24, f'{garden_w/sx:.0f}\'-0" X {garden_h/sy:.0f}\'-0"', 13))
        for i in range(5):
            s.append(f'<circle cx="{left+30+i*42}" cy="{top+35}" r="13" fill="#ddd" stroke="#555"/>')
        for i in range(6):
            s.append(f'<circle cx="{left+25}" cy="{top+75+i*50}" r="12" fill="#ddd" stroke="#555"/>')

    if req.parking:
        parking_h = plot_h*.50
        s.append(rect(right_zone_x, top, parking_w, parking_h, "#222", "#fafafa", 3))
        s.append(room_label(right_zone_x+parking_w/2, top+150, "CAR PARKING"))
        s.append(text(right_zone_x+parking_w/2, top+178, '15\'-0" X 25\'-0"', 14))
        s.append(car(right_zone_x+parking_w*.38, top+210, parking_w*.25, 210))

    living_top = top+plot_h*.43
    living_h = plot_h*.28
    living_x = center_x
    living_w = right_zone_x-center_x

    s.append(rect(living_x, living_top, living_w*.52, living_h, "#222", "white", 3))
    s.append(room_label(living_x+living_w*.26, living_top+90, "LIVING ROOM"))
    s.append(text(living_x+living_w*.26, living_top+115, '14\'-0" X 16\'-0"', 13))
    s.append(sofa(living_x+40, living_top+140, 120, 45))

    dining_x = living_x+living_w*.52
    s.append(rect(dining_x, living_top, living_w*.48, living_h, "#222", "white", 3))
    s.append(room_label(dining_x+living_w*.24, living_top+90, "DINING"))
    s.append(text(dining_x+living_w*.24, living_top+115, '10\'-0" X 13\'-0"', 13))
    s.append(dining_table(dining_x+55, living_top+145, 100, 55))

    bedroom_area_h = living_top-(top+5)
    bedroom_x, bedroom_w = center_x, living_w*.52
    rows = math.ceil(req.bedrooms/2)
    cell_w, cell_h = bedroom_w/2, bedroom_area_h/rows

    for i in range(req.bedrooms):
        row, col = i//2, i%2
        x, y = bedroom_x+col*cell_w, top+5+row*cell_h
        s.append(rect(x, y, cell_w, cell_h, "#222", "#fff", 3))
        name = "MASTER BEDROOM" if i == 0 else f"BEDROOM {i+1}"
        s.append(room_label(x+cell_w/2, y+45, name))
        s.append(text(x+cell_w/2, y+68, f'{cell_w/sx:.0f}\'-0" X {cell_h/sy:.0f}\'-0"', 12))
        s.append(bed(x+cell_w*.27, y+cell_h*.35, cell_w*.45, cell_h*.42))
        if i == 0 and req.attached_bath:
            bath_w, bath_h = cell_w*.28, cell_h*.30
            bx, by = x+cell_w-bath_w, y
            s.append(rect(bx, by, bath_w, bath_h, "#222", "#fafafa", 2))
            s.append(text(bx+bath_w/2, by+25, "MASTER BATH", 11, "bold"))
            s.append(toilet_symbol(bx+bath_w*.35, by+bath_h*.65))
            s.append(wash_basin(bx+bath_w*.72, by+bath_h*.55))

    kitchen_x, kitchen_y = right_zone_x, living_top+living_h
    kitchen_h = bottom-kitchen_y
    s.append(rect(kitchen_x, kitchen_y, parking_w, kitchen_h, "#222", "#fff", 3))
    s.append(room_label(kitchen_x+parking_w/2, kitchen_y+kitchen_h/2, "KITCHEN"))
    s.append(text(kitchen_x+parking_w/2, kitchen_y+kitchen_h/2+25, '16\'-0" X 10\'-0"', 13))
    s.append(kitchen_counter(kitchen_x+20, kitchen_y+40, parking_w-40, 65))

    if req.utility:
        utility_w, utility_h = parking_w*.55, plot_h*.18
        utility_x, utility_y = right_zone_x, top+plot_h*.50
        s.append(rect(utility_x, utility_y, utility_w, utility_h, "#222", "#fff", 3))
        s.append(room_label(utility_x+utility_w/2, utility_y+45, "UTILITY"))
        s.append(text(utility_x+utility_w/2, utility_y+68, '10\'-0" X 6\'-0"', 12))
        s.append(text(utility_x+utility_w-35, utility_y+40, "HW", 12, "bold"))

    storage_x, storage_y = right_zone_x+parking_w*.55, top+plot_h*.50
    storage_w, storage_h = parking_w*.45, plot_h*.18
    s.append(rect(storage_x, storage_y, storage_w, storage_h, "#222", "#fff", 3))
    s.append(room_label(storage_x+storage_w/2, storage_y+50, "STORAGE"))
    s.append(text(storage_x+storage_w/2, storage_y+73, '6\'-0" X 6\'-0"', 12))

    if req.staircase:
        s.append(stairs(living_x+living_w*.70, living_top+10, 85, 220))

    bath_x, bath_y = left+garden_w, living_top
    bath_w, bath_h = bedroom_w*.30, living_h*.55
    s.append(rect(bath_x, bath_y, bath_w, bath_h, "#222", "#fff", 3))
    s.append(room_label(bath_x+bath_w/2, bath_y+45, "BATH"))
    s.append(text(bath_x+bath_w/2, bath_y+68, '9\'-0" X 6\'-0"', 12))
    s.append(toilet_symbol(bath_x+bath_w*.32, bath_y+bath_h*.62))
    s.append(wash_basin(bath_x+bath_w*.72, bath_y+bath_h*.60))

    wardrobe_y = bath_y+bath_h
    wardrobe_h = living_top+living_h-wardrobe_y
    s.append(rect(bath_x, wardrobe_y, bath_w, wardrobe_h, "#222", "#fff", 3))
    s.append(room_label(bath_x+bath_w/2, wardrobe_y+wardrobe_h/2, "WARDROBE"))

    deck_x, deck_y, deck_w, deck_h = left+garden_w, top, 75, garden_h
    s.append(rect(deck_x, deck_y, deck_w, deck_h, "#777", "#f2f2f2", 2))
    s.append(text(deck_x+deck_w/2, deck_y+deck_h/2, "DECK", 13, "bold"))

    entrance_x = W/2
    s.append(rect(entrance_x-75, bottom, 150, 55, "#222", "#fff", 2))
    for i in range(1,4):
        s.append(line(entrance_x-75, bottom+i*13, entrance_x+75, bottom+i*13, "#555", 1))
    s.append(text(entrance_x, bottom+85, "MAIN ENTRANCE", 14, "bold"))

    s.append(dimension_horizontal(left, right, top-40, f'{req.plot_width:g}\'-0"'))
    s.append(dimension_vertical(top, bottom, left-40, f'{req.plot_length:g}\'-0"'))

    s.append(window(left+garden_w+40, top, 70))
    s.append(window(right-200, bottom, 80))
    s.append(window(left, living_top+50, 80, False))
    s.append(compass(1560, 1040))

    block_y = 980
    s.append(rect(40, block_y, 1200, 170, "#222", "#fff", 2))
    s.append(text(60, block_y+35, f"{req.title} ({req.bedrooms}BHK HOUSE)", 19, "bold", "start"))
    s.append(text(60, block_y+70, f'PLOT SIZE - {req.plot_width:g}\'-0" X {req.plot_length:g}\'-0"', 15, "normal", "start"))
    area = req.plot_width*req.plot_length
    s.append(text(60, block_y+105, f"TOTAL PLOT AREA - {area:,.0f} SQ.FT.", 15, "normal", "start"))
    s.append(text(60, block_y+140, "CONCEPTUAL ARCHITECTURAL FLOOR PLAN", 13, "normal", "start"))

    s.append(rect(1260, block_y, 500, 170, "#222", "#fff", 2))
    s.append(text(1280, block_y+32, "NOTES", 17, "bold", "start"))
    notes = [
        "1. ALL DIMENSIONS ARE IN FEET & INCHES.",
        "2. CONCEPTUAL PLAN ONLY.",
        "3. DO NOT SCALE THE DRAWING.",
        "4. FINAL DESIGN TO BE VERIFIED BY AN ARCHITECT."
    ]
    for i, note in enumerate(notes):
        s.append(text(1280, block_y+62+i*25, note, 12, "normal", "start"))

    s.append("</svg>")
    return "".join(s)


HTML = r"""
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GharPlan AI</title>
<style>
body{font-family:Arial,sans-serif;background:#f5f6fa;margin:0;color:#202124}
header{background:white;padding:20px;text-align:center;border-bottom:1px solid #ddd}
h1{margin:0;color:#4f46e5}.container{max-width:1000px;margin:25px auto;padding:20px}
.card{background:white;padding:25px;border-radius:15px;box-shadow:0 4px 20px rgba(0,0,0,.08)}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:15px}
label{font-weight:bold}input,select{width:100%;padding:12px;margin-top:6px;border:1px solid #ccc;border-radius:8px;box-sizing:border-box}
button{margin-top:20px;width:100%;padding:15px;border:0;border-radius:10px;background:#4f46e5;color:white;font-size:18px;font-weight:bold}
#result{margin-top:30px;overflow-x:auto}#result img{width:100%;min-width:900px;border:1px solid #ccc}
@media(max-width:600px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header><h1>GharPlan AI</h1><p>Architectural Floor Plan Generator</p></header>
<div class="container"><div class="card">
<h2>Create Your Floor Plan</h2>
<div class="grid">
<div><label>Bedrooms / BHK</label><input id="bedrooms" type="number" value="3" min="1" max="6"></div>
<div><label>Plot Width (ft)</label><input id="plot_width" type="number" value="70"></div>
<div><label>Plot Length (ft)</label><input id="plot_length" type="number" value="50"></div>
<div><label>Orientation</label><select id="orientation"><option value="N">North</option><option value="E">East</option><option value="S">South</option><option value="W">West</option></select></div>
</div>
<button onclick="generatePlan()">GENERATE FLOOR PLAN</button>
<div id="result"></div>
</div></div>
<script>
async function generatePlan(){
 const result=document.getElementById("result");
 result.innerHTML="<h3>Generating architectural plan...</h3>";
 const data={
 bedrooms:parseInt(document.getElementById("bedrooms").value),
 plot_width:parseFloat(document.getElementById("plot_width").value),
 plot_length:parseFloat(document.getElementById("plot_length").value),
 orientation:document.getElementById("orientation").value,
 parking:true,garden:true,attached_bath:true,utility:true,staircase:true,title:"GROUND FLOOR PLAN"
 };
 try{
  const response=await fetch("/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
  if(!response.ok)throw new Error("Server returned "+response.status);
  const svg=await response.text();
  const blob=new Blob([svg],{type:"image/svg+xml"});
  const url=URL.createObjectURL(blob);
  result.innerHTML=`<h3>Generated Plan</h3><img src="${url}"><br><a href="${url}" download="gharplan-floor-plan.svg"><button>DOWNLOAD PLAN</button></a>`;
 }catch(error){result.innerHTML="<h3 style='color:red'>Generation failed</h3><p>"+error.message+"</p>";}
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
    return {"status": "ok", "service": "GharPlan AI"}
