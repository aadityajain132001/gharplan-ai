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


def make_rooms(req, style):
    # normalized plot coordinates: x,y,w,h in [0,1]
    rooms=[]
    bedrooms=max(1,req.bedrooms)

    # Service / parking / garden zones vary by style.
    if style in ("front_garden","courtyard"):
        front_h=.22
        if req.garden: rooms.append(("GARDEN",.02,.02,.36,front_h,"garden"))
        if req.parking: rooms.append(("CAR PARKING",.40,.02,.26,front_h,"parking"))
        service_x=.70
    elif style=="central_living":
        front_h=.18
        if req.parking: rooms.append(("CAR PARKING",.02,.02,.24,front_h,"parking"))
        if req.garden: rooms.append(("GARDEN",.27,.02,.40,front_h,"garden"))
        service_x=.72
    else:
        front_h=.20
        if req.parking: rooms.append(("CAR PARKING",.72,.02,.26,front_h,"parking"))
        if req.garden: rooms.append(("GARDEN",.02,.02,.30,front_h,"garden"))
        service_x=.72

    # Main living/dining core
    if style in ("wide_living","central_living","front_garden"):
        living=(.28, .24, .44, .22)
    elif style=="compact_core":
        living=(.26, .25, .34, .24)
    else:
        living=(.34, .25, .36, .22)
    rooms.append(("LIVING ROOM",*living,"living"))
    rooms.append(("DINING",living[0]+living[2]*.55,living[1],living[2]*.45,living[3],"dining"))

    # Bedroom zone
    if style in ("side_bedrooms","split_bedrooms"):
        bx,by,bw,bh=.02,.47,.68,.49
    elif style=="rear_service":
        bx,by,bw,bh=.02,.49,.67,.47
    else:
        bx,by,bw,bh=.02,.50,.68,.46

    cols=2 if bedrooms>1 else 1
    rows=math.ceil(bedrooms/cols)
    gap=.006
    cw=(bw-gap*(cols-1))/cols
    ch=(bh-gap*(rows-1))/rows
    for i in range(bedrooms):
        r,c=divmod(i,cols)
        rooms.append(("MASTER BEDROOM" if i==0 else f"BEDROOM {i+1}",
                      bx+c*(cw+gap),by+r*(ch+gap),cw,ch,"bedroom"))

    # Kitchen/service
    if style=="wide_living":
        kx,ky,kw,kh=.70,.47,.28,.25
    elif style=="rear_service":
        kx,ky,kw,kh=.70,.70,.28,.26
    else:
        kx,ky,kw,kh=.70,.49,.28,.25
    rooms.append(("KITCHEN",kx,ky,kw,kh,"kitchen"))
    if req.utility:
        rooms.append(("UTILITY",kx,ky+kh+.01,kw*.58,.15,"utility"))
    if req.store:
        rooms.append(("STORE",kx+kw*.60,ky+kh+.01,kw*.40,.15,"store"))
    if req.pooja:
        rooms.append(("POOJA",.70,.34,.13,.12,"pooja"))
    if req.staircase:
        rooms.append(("STAIRCASE",.84,.34,.14,.20,"stairs"))

    # Common bath and attached bath are placed in service/central areas.
    rooms.append(("COMMON TOILET",.70,.25,.13,.12,"bath"))
    if req.attached_bath and bedrooms:
        # attached bath for master
        m=next(r for r in rooms if r[0]=="MASTER BEDROOM")
        mx,my,mw,mh,_=m
        rooms.append(("MASTER BATH",mx+mw*.68,my,mw*.30,mh*.38,"bath"))

    if req.balcony:
        rooms.append(("BALCONY",.34,.92,.36,.06,"balcony"))

    return rooms


def generate_plan(req: PlanRequest):
    style, seed, reason = ai_style(req)

    # Architectural sheet: wide enough for desktop, scales responsively on mobile.
    W,H=1800,1320
    L,T,R,B=150,160,1650,1030
    PW,PH=R-L,B-T
    sx,sy=PW/req.plot_width,PH/req.plot_length

    s=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="auto" preserveAspectRatio="xMidYMid meet">',
       '<rect width="1800" height="1320" fill="white"/>']
    s.append(txt(W/2,42,f"{req.title} - {req.bedrooms}BHK",27,"bold"))
    s.append(txt(W/2,70,f'PLOT SIZE - {req.plot_width:g}\'-0" X {req.plot_length:g}\'-0" | ORIENTATION - {req.orientation}',15))
    s.append(rect(L,T,PW,PH,"#111","white",6))

    rooms=make_rooms(req,style)
    for name,nx,ny,nw,nh,kind in rooms:
        x=L+nx*PW; y=T+ny*PH; w=nw*PW; h=nh*PH
        rw=max(4,nw*req.plot_width); rh=max(4,nh*req.plot_length)
        fill={"garden":"#f4f4f4","parking":"#fafafa","bedroom":"#fff",
              "living":"#fff","dining":"#fff","kitchen":"#fff","utility":"#fff",
              "store":"#fff","bath":"#fff","stairs":"#fff","pooja":"#fff",
              "balcony":"#f8f8f8"}.get(kind,"white")
        if kind=="garden":
            s.append(rect(x,y,w,h,"#444",fill,3))
            s.append(room_name(x+w/2,y+h*.45,name,16))
            s.append(txt(x+w/2,y+h*.45+24,f'{rw:.0f}\'-0" X {rh:.0f}\'-0"',12))
            for i in range(5):
                s.append(f'<circle cx="{x+28+i*38:.1f}" cy="{y+30:.1f}" r="12" fill="#ddd" stroke="#555"/>')
        elif kind=="parking":
            s.append(rect(x,y,w,h,"#222",fill,3))
            s.append(room_name(x+w/2,y+h*.35,name,15))
            s.append(txt(x+w/2,y+h*.35+23,f'{rw:.0f}\'-0" X {rh:.0f}\'-0"',12))
            s.append(car_symbol(x+w*.38,y+h*.46,w*.25,h*.43))
        elif kind=="bedroom":
            s.append(label_box(x,y,w,h,name,rw,rh,"white",bed_symbol))
        elif kind=="living":
            s.append(label_box(x,y,w,h,name,rw,rh,"white",sofa_symbol))
        elif kind=="dining":
            s.append(label_box(x,y,w,h,name,rw,rh,"white",table_symbol))
        elif kind=="kitchen":
            s.append(label_box(x,y,w,h,name,rw,rh,"white",kitchen_symbol))
        elif kind=="bath":
            s.append(rect(x,y,w,h,"#222","white",3))
            s.append(room_name(x+w/2,y+h*.30,name,11))
            s.append(toilet_symbol(x+w*.34,y+h*.66)); s.append(basin(x+w*.70,y+h*.60))
        elif kind=="stairs":
            s.append(rect(x,y,w,h,"#222","white",3)); s.append(stair_symbol(x+10,y+8,w-20,h-20))
        else:
            s.append(label_box(x,y,w,h,name,rw,rh,"white",None))

    # Doors/windows: architectural symbols placed around major perimeter edges.
    s.append(line(L+PW*.18,T,L+PW*.18,T+18,"#555",7))
    s.append(line(L+PW*.55,B-5,L+PW*.62,B-5,"#555",7))
    s.append(line(L+5,T+PH*.55,L+5,T+PH*.66,"#555",7))
    s.append(line(R-5,T+PH*.35,R-5,T+PH*.47,"#555",7))

    # Main entrance at the side corresponding to requested orientation.
    if req.orientation=="N":
        ex,ey=L+PW*.48,T
        s.append(txt(ex,ey-28,"MAIN ENTRANCE",14,"bold"))
    elif req.orientation=="S":
        ex,ey=L+PW*.48,B
        s.append(txt(ex,ey+28,"MAIN ENTRANCE",14,"bold"))
    elif req.orientation=="E":
        ex,ey=R,T+PH*.55
        s.append(txt(ex+70,ey,"MAIN ENTRANCE",14,"bold","start"))
    else:
        ex,ey=L,T+PH*.55
        s.append(txt(ex-70,ey,"MAIN ENTRANCE",14,"bold","end"))

    s.append(dim_h(L,R,T-42,f'{req.plot_width:g}\'-0"'))
    s.append(dim_v(T,B,L-42,f'{req.plot_length:g}\'-0"'))
    s.append(compass(1560,1175,req.orientation))

    # Title / notes block.
    by=1110
    s.append(rect(40,by,1210,165,"#222","white",2))
    s.append(txt(60,by+32,f"{req.title} ({req.bedrooms}BHK HOUSE)",18,"bold","start"))
    s.append(txt(60,by+62,f'PLOT SIZE - {req.plot_width:g}\'-0" X {req.plot_length:g}\'-0"',14,"normal","start"))
    s.append(txt(60,by+90,f"TOTAL PLOT AREA - {req.plot_width*req.plot_length:,.0f} SQ.FT.",14,"normal","start"))
    s.append(txt(60,by+118,f"LAYOUT VARIATION - {seed}",13,"normal","start"))
    s.append(txt(60,by+145,"CONCEPTUAL ARCHITECTURAL FLOOR PLAN - NOT FOR CONSTRUCTION",12,"normal","start"))

    s.append(rect(1270,by,490,165,"#222","white",2))
    s.append(txt(1290,by+30,"DESIGN NOTES",16,"bold","start"))
    notes=["AI-assisted space-planning variation","Dimensions are approximate","Verify setbacks/by-laws locally","Final working drawing by qualified architect"]
    for i,n in enumerate(notes):
        s.append(txt(1290,by+58+i*25,n,11,"normal","start"))

    s.append(txt(W/2,1295,f"Architectural Floor Plan Generator  •  by ANIK KUMAR",14,"bold"))
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
