import os
import base64
import random
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from openai import OpenAI

app = FastAPI(title="GharPlan AI")

# Put OPENAI_API_KEY in Render -> Environment.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None

VARIATIONS = [
    "Use a compact zoning arrangement with excellent circulation and a strong central living/dining core.",
    "Use a contemporary Indian residential arrangement with clear public/private separation.",
    "Try a courtyard-oriented arrangement where the plot allows it, with bedrooms kept private.",
    "Try a linear circulation arrangement with efficient plumbing and staircase placement.",
    "Try a climate-responsive arrangement emphasizing daylight, cross ventilation and shaded openings.",
    "Try a family-oriented arrangement with a generous living/dining zone and practical bedroom access.",
    "Try a Vastu-conscious arrangement when the customer selected Vastu, while still respecting all stated requirements.",
    "Create a fresh professional architect-style alternative; do not copy a previous arrangement."
]

class PlanRequest(BaseModel):
    # Plot
    bhk: int = Field(ge=1, le=12)
    plot_width: float = Field(gt=0, le=500)
    plot_length: float = Field(gt=0, le=500)
    facing: str = "North"
    road_sides: str = "One side"
    road_width: str = ""
    site_shape: str = "Rectangular"
    setbacks: str = ""
    floors: int = Field(default=1, ge=1, le=6)

    # Rooms
    bathrooms: int = Field(default=2, ge=0, le=12)
    attached_baths: str = "As needed"
    kitchen: str = "Closed kitchen"
    dining: str = "Yes"
    living_room: str = "Yes"
    family_lounge: str = "No"
    master_bedroom: str = "Yes"
    dressing: str = "No"
    guest_room: str = "No"
    pooja: str = "No"
    study: str = "No"
    store: str = "No"
    utility: str = "Yes"
    laundry: str = "No"
    servant_room: str = "No"
    courtyard: str = "No"
    balcony: str = "No"
    terrace: str = "No"
    staircase: str = "Inside"
    parking: str = "1 car"
    parking_extra: str = ""

    # Preferences
    vastu: str = "No preference"
    elderly: str = "No"
    wheelchair: str = "No"
    rental: str = "No"
    future_expansion: str = "No"
    ventilation: str = "High"
    daylight: str = "High"
    privacy: str = "Balanced"
    entry: str = "Main entrance from road"
    style: str = "Professional architectural 2D plan"

    # Free text
    special_requirements: str = ""
    customer_name: str = "Customer"

def build_prompt(p: PlanRequest, variation: str) -> str:
    return f"""
Create a professional ARCHITECTURAL 2D RESIDENTIAL FLOOR PLAN IMAGE from the
customer requirements below.

IMPORTANT:
- This is a floor-plan drawing, NOT a perspective house image.
- Top-down orthographic architectural plan.
- White background.
- Crisp black/dark grey CAD-style walls with realistic wall thickness.
- Clearly separated rooms with doors, windows and circulation.
- Show furniture symbols appropriate to each room: beds, sofa, dining table,
  kitchen counters, sanitary fixtures, wardrobes, car, staircase, etc.
- Put readable room names INSIDE rooms.
- Put room dimensions INSIDE or immediately beside rooms where practical.
- Put overall plot width and length dimension lines around the site.
- Include a north arrow/compass.
- Include main entrance and road indication.
- Include a title block such as:
  "GROUND FLOOR PLAN – {p.bhk} BHK HOUSE"
  "PLOT SIZE – {p.plot_width:g}'-0" × {p.plot_length:g}'-0""
  "ARCHITECTURAL FLOOR PLAN – CONCEPT ONLY"
  "BY ANIK KUMAR"
- The final result must look like a clean professional architectural
  presentation similar to a real 2D residential plan, not like a generic
  diagram or infographic.
- Do NOT return HTML, SVG, JSON, code, or explanations. Generate only the plan image.
- Use the actual customer dimensions and requirements. Do not invent a different
  plot size or BHK count.
- Make the layout physically coherent: rooms must connect, doors must open into
  usable circulation, bathrooms should be reachable, parking should fit, and
  furniture should fit within rooms.
- If some requested rooms cannot reasonably fit, prioritize the customer's
  mandatory spaces and arrange the remaining spaces efficiently.
- This is a CONCEPTUAL architectural visualization and is not a construction
  drawing or structural approval document.

SITE
Plot: {p.plot_width:g} ft wide × {p.plot_length:g} ft long
Facing: {p.facing}
Road access: {p.road_sides}
Road width: {p.road_width or "Not specified"}
Site shape: {p.site_shape}
Requested setbacks: {p.setbacks or "Use sensible conceptual setbacks"}
Floors: {p.floors}

ROOM PROGRAM
{p.bhk} bedrooms / BHK
Bathrooms: {p.bathrooms}
Attached bathrooms: {p.attached_baths}
Kitchen: {p.kitchen}
Living room: {p.living_room}
Dining: {p.dining}
Family lounge: {p.family_lounge}
Master bedroom: {p.master_bedroom}
Dressing: {p.dressing}
Guest room: {p.guest_room}
Pooja room: {p.pooja}
Study: {p.study}
Store: {p.store}
Utility: {p.utility}
Laundry: {p.laundry}
Servant room: {p.servant_room}
Courtyard: {p.courtyard}
Balcony: {p.balcony}
Terrace: {p.terrace}
Staircase: {p.staircase}
Parking: {p.parking}
Additional parking requirements: {p.parking_extra or "None"}

DESIGN PREFERENCES
Vastu: {p.vastu}
Elderly-friendly: {p.elderly}
Wheelchair accessibility: {p.wheelchair}
Rental requirement: {p.rental}
Future expansion: {p.future_expansion}
Ventilation: {p.ventilation}
Daylight: {p.daylight}
Privacy: {p.privacy}
Preferred entry: {p.entry}
Drawing style: {p.style}

CUSTOMER'S SPECIAL REQUIREMENTS
{p.special_requirements or "None"}

CUSTOMER: {p.customer_name}

LAYOUT VARIATION FOR THIS GENERATION
{variation}

Create a NEW layout composition for this generation. Do not simply repeat a
previous arrangement. Keep all mandatory requirements consistent.
"""

HTML = r"""
<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GharPlan AI — Architectural Floor Plan Generator</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f3f5fa;font-family:Arial,Helvetica,sans-serif;color:#171922}
.wrap{max-width:900px;margin:auto;padding:22px}
.card{background:white;border-radius:24px;padding:28px;box-shadow:0 10px 35px #00000012;margin-bottom:22px}
h1{font-size:34px;margin:0 0 8px}
h2{font-size:22px;margin:0 0 18px}
.sub{color:#687080;margin-bottom:26px}
.section{border-top:1px solid #e6e8ee;padding-top:24px;margin-top:24px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
label{font-weight:700;font-size:14px;display:block;margin-bottom:7px}
input,select,textarea{width:100%;border:1px solid #cfd3dc;border-radius:12px;padding:13px;font-size:16px;background:white}
textarea{min-height:100px;resize:vertical}
.full{grid-column:1/-1}
button{width:100%;border:0;border-radius:14px;padding:17px;background:#5146e5;color:#fff;font-size:18px;font-weight:800;cursor:pointer;margin-top:24px}
button:disabled{opacity:.6}
#status{margin-top:18px;font-weight:700}
.error{color:#d71920}
.success{color:#16803a}
.result img{width:100%;display:block;border:1px solid #d9dce4;border-radius:12px;background:white}
.download{display:block;text-align:center;text-decoration:none;background:#111827;color:white;padding:13px;border-radius:12px;margin-top:12px;font-weight:700}
.brand{text-align:center;color:#687080;font-size:13px;margin:12px 0 28px}
.checkgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.check{border:1px solid #ddd;border-radius:10px;padding:10px}
@media(max-width:650px){.wrap{padding:12px}.card{padding:20px;border-radius:18px}h1{font-size:28px}.grid,.checkgrid{grid-template-columns:1fr}.full{grid-column:auto}}
</style>
</head>
<body>
<div class="wrap">
<div class="card">
<h1>GharPlan AI</h1>
<div class="sub">Customer requirements → AI architectural floor plan</div>

<form id="planForm">
<div class="section">
<h2>1. Plot & Site</h2>
<div class="grid">
<div><label>BHK / Bedrooms</label><input name="bhk" type="number" min="1" max="12" value="3" required></div>
<div><label>Plot Width (ft)</label><input name="plot_width" type="number" min="1" value="40" required></div>
<div><label>Plot Length (ft)</label><input name="plot_length" type="number" min="1" value="60" required></div>
<div><label>Facing</label><select name="facing"><option>North</option><option>East</option><option>South</option><option>West</option></select></div>
<div><label>Road Access</label><select name="road_sides"><option>One side</option><option>Two sides</option><option>Three sides</option><option>Four sides</option></select></div>
<div><label>Road Width</label><input name="road_width" placeholder="e.g. 30 ft"></div>
<div><label>Site Shape</label><select name="site_shape"><option>Rectangular</option><option>Square</option><option>Irregular</option></select></div>
<div><label>Number of Floors</label><select name="floors"><option>1</option><option>2</option><option>3</option><option>4</option></select></div>
<div class="full"><label>Required setbacks / local restrictions</label><input name="setbacks" placeholder="If known, enter them. Otherwise leave blank."></div>
</div>
</div>

<div class="section">
<h2>2. Rooms & Facilities</h2>
<div class="grid">
<div><label>Bathrooms</label><input name="bathrooms" type="number" min="0" value="3"></div>
<div><label>Attached bathrooms</label><select name="attached_baths"><option>As needed</option><option>All bedrooms</option><option>Master only</option><option>None</option></select></div>
<div><label>Kitchen</label><select name="kitchen"><option>Closed kitchen</option><option>Open kitchen</option><option>Open + utility</option><option>Large family kitchen</option></select></div>
<div><label>Living room</label><select name="living_room"><option>Yes</option><option>No</option><option>Large</option></select></div>
<div><label>Dining</label><select name="dining"><option>Yes</option><option>No</option><option>Separate dining</option></select></div>
<div><label>Family lounge</label><select name="family_lounge"><option>No</option><option>Yes</option></select></div>
<div><label>Master bedroom</label><select name="master_bedroom"><option>Yes</option><option>No</option><option>Large</option></select></div>
<div><label>Dressing room</label><select name="dressing"><option>No</option><option>Yes</option></select></div>
<div><label>Guest room</label><select name="guest_room"><option>No</option><option>Yes</option></select></div>
<div><label>Pooja room</label><select name="pooja"><option>No</option><option>Yes</option></select></div>
<div><label>Study / office</label><select name="study"><option>No</option><option>Yes</option></select></div>
<div><label>Store room</label><select name="store"><option>No</option><option>Yes</option></select></div>
<div><label>Utility / wash area</label><select name="utility"><option>Yes</option><option>No</option></select></div>
<div><label>Laundry</label><select name="laundry"><option>No</option><option>Yes</option></select></div>
<div><label>Servant room</label><select name="servant_room"><option>No</option><option>Yes</option></select></div>
<div><label>Courtyard</label><select name="courtyard"><option>No</option><option>Yes</option></select></div>
<div><label>Balcony</label><select name="balcony"><option>No</option><option>Yes</option></select></div>
<div><label>Terrace</label><select name="terrace"><option>No</option><option>Yes</option></select></div>
<div><label>Staircase</label><select name="staircase"><option>Inside</option><option>Outside</option><option>Both</option></select></div>
<div><label>Parking</label><select name="parking"><option>1 car</option><option>2 cars</option><option>3 cars</option><option>No car</option><option>Car + bikes</option></select></div>
<div class="full"><label>Additional parking requirements</label><input name="parking_extra" placeholder="SUV, bikes, covered parking, etc."></div>
</div>
</div>

<div class="section">
<h2>3. Lifestyle & Design Preferences</h2>
<div class="grid">
<div><label>Vastu preference</label><select name="vastu"><option>No preference</option><option>Follow Vastu principles</option><option>Strong Vastu priority</option></select></div>
<div><label>Elderly-friendly</label><select name="elderly"><option>No</option><option>Yes</option></select></div>
<div><label>Wheelchair accessibility</label><select name="wheelchair"><option>No</option><option>Yes</option></select></div>
<div><label>Rental unit required</label><select name="rental"><option>No</option><option>Yes</option></select></div>
<div><label>Future expansion</label><select name="future_expansion"><option>No</option><option>Yes</option></select></div>
<div><label>Ventilation</label><select name="ventilation"><option>Balanced</option><option>High</option><option>Maximum</option></select></div>
<div><label>Natural daylight</label><select name="daylight"><option>Balanced</option><option>High</option><option>Maximum</option></select></div>
<div><label>Privacy</label><select name="privacy"><option>Balanced</option><option>High privacy</option><option>Open family layout</option></select></div>
<div class="full"><label>Preferred main entry</label><input name="entry" value="Main entrance from road"></div>
<div class="full"><label>Special requirements / anything else</label><textarea name="special_requirements" placeholder="Tell the architect everything important: room preferences, family needs, specific dimensions, garden, prayer area, guest access, separate entrance, etc."></textarea></div>
<div><label>Customer name</label><input name="customer_name" value="Customer"></div>
<div><label>Drawing style</label><select name="style"><option>Professional architectural 2D plan</option><option>Detailed CAD-style presentation</option><option>Minimal architectural plan</option></select></div>
</div>
</div>

<button id="generate" type="submit">GENERATE AI FLOOR PLAN</button>
<div id="status"></div>
</form>
</div>

<div class="card result">
<h2>Generated Plan</h2>
<div id="result">Fill the requirements and press Generate.</div>
</div>

<div class="brand">Architectural Floor Plan Generator • by ANIK KUMAR</div>
</div>

<script>
const form=document.getElementById("planForm");
const statusEl=document.getElementById("status");
const result=document.getElementById("result");
const btn=document.getElementById("generate");

form.addEventListener("submit",async(e)=>{
  e.preventDefault();
  btn.disabled=true;
  btn.textContent="AI IS DESIGNING YOUR PLAN…";
  statusEl.className="";
  statusEl.textContent="Sending the customer's complete requirements to AI. This can take some time.";
  result.innerHTML="";

  const data=Object.fromEntries(new FormData(form).entries());
  ["bhk","plot_width","plot_length","floors","bathrooms"].forEach(k=>data[k]=Number(data[k]));

  try{
    const r=await fetch("/api/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
    const j=await r.json();
    if(!r.ok) throw new Error(j.detail||"Generation failed");

    result.innerHTML=`
      <img src="${j.image}" alt="AI generated architectural floor plan">
      <a class="download" download="gharplan-ai-floor-plan.png" href="${j.image}">DOWNLOAD FLOOR PLAN</a>
    `;
    statusEl.className="success";
    statusEl.textContent="AI generated a new architectural plan from the customer's requirements.";
  }catch(err){
    statusEl.className="error";
    statusEl.textContent="Generation failed: "+err.message;
    result.innerHTML="<p>Please check the OpenAI API key and Render logs.</p>";
  }finally{
    btn.disabled=false;
    btn.textContent="GENERATE AI FLOOR PLAN";
  }
});
</script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(HTML)

@app.get("/health")
async def health():
    return {"status": "ok", "ai_enabled": bool(client)}

@app.post("/api/generate")
async def generate_plan(req: PlanRequest):
    if not client:
        return JSONResponse(
            status_code=500,
            content={"detail": "OPENAI_API_KEY is not configured on the server."}
        )

    # A fresh variation instruction is selected on every request.
    variation = random.choice(VARIATIONS)
    variation += f" Generation timestamp: {datetime.utcnow().isoformat()}"

    prompt = build_prompt(req, variation)

    try:
        # The OpenAI image model creates the actual plan image.
        response = client.images.generate(
            model="gpt-image-1.5",
            prompt=prompt,
            size="1536x1024",
            quality="high",
            output_format="png"
        )

        b64 = response.data[0].b64_json
        image_data = "data:image/png;base64," + b64

        return {
            "ok": True,
            "image": image_data,
            "model": "gpt-image-1.5",
            "variation": variation
        }

    except Exception as exc:
        # Do not expose the API key or internal secrets.
        return JSONResponse(
            status_code=502,
            content={"detail": f"OpenAI image generation failed: {str(exc)}"}
        )
