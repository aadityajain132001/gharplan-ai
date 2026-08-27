import os
import base64
from typing import Optional

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types

app = FastAPI(title="GharPlan AI - Architectural Floor Plan Generator")

MODEL = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image")


def build_prompt(data: dict) -> str:
    rooms = ", ".join(data["rooms"]) if data["rooms"] else "as required"
    extras = ", ".join(data["extras"]) if data["extras"] else "none"

    return f"""
Create a professional architectural 2D residential floor-plan drawing from the
customer requirements below.

CUSTOMER REQUIREMENTS
- BHK / bedrooms: {data["bhk"]}
- Plot width: {data["plot_width"]} ft
- Plot length: {data["plot_length"]} ft
- Plot orientation / road side: {data["orientation"]}
- Required rooms/spaces: {rooms}
- Additional facilities: {extras}
- Special requirements: {data["special"]}
- Wall preference: {data["wall_type"]}
- Staircase: {data["staircase"]}
- Parking: {data["parking"]}
- Vastu preference: {data["vastu"]}

ARCHITECTURAL DRAWING REQUIREMENTS
- Generate ONE clear top-view 2D floor plan, not a 3D render.
- Use realistic architectural drafting conventions.
- Show all external and internal walls with consistent wall thickness.
- Clearly label every room (Bedroom, Master Bedroom, Living, Dining,
  Kitchen, Toilet, Staircase, Store, Puja, Balcony, Parking, etc. as applicable).
- Put approximate room dimensions inside/near rooms.
- Show doors with swing arcs and windows/openings in conventional symbols.
- Show circulation and logical room connections.
- Respect the given plot dimensions and orientation as much as possible.
- Put a north arrow and road/entrance indication.
- Add overall plot/building dimensions and important internal dimensions.
- Keep plumbing spaces sensibly grouped where possible.
- Do not invent unnecessary rooms.
- Make the drawing look like a clean professional Indian residential
  architectural floor plan suitable as a concept design.
- Use a white drawing background, black/dark drafting lines and restrained
  technical annotation.
- Do NOT create a perspective view, exterior elevation, furniture-only image,
  mood board, or photorealistic house.
- Do not put a giant title over the drawing.
- If the requirements conflict with the plot size, prioritize a practical
  buildable arrangement and clearly fit the requested spaces into the plot.
"""


def generate_image(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured on the server. "
            "Add it in Render Environment Variables."
        )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            response_format={
                "image": {
                    "aspect_ratio": "4:3",
                    "image_size": "2K",
                }
            },
        ),
    )

    for part in response.parts:
        if part.inline_data is not None:
            image = part.as_image()
            # Save in memory as PNG, then return a data URL for the browser.
            import io
            buf = io.BytesIO()
            image.save(buf, format="PNG")
            return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")

    raise RuntimeError("Gemini returned no image. Please try again.")


PAGE = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Architectural Floor Plan Generator</title>
<style>
*{box-sizing:border-box}
body{margin:0;background:#f3f5fa;color:#17181c;font-family:Arial,sans-serif}
.wrap{max-width:900px;margin:28px auto;padding:18px}
.card{background:#fff;border-radius:24px;padding:30px;box-shadow:0 10px 35px #00000012}
h1{margin:0 0 8px;font-size:34px}
.sub{color:#666;margin-bottom:28px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.full{grid-column:1/-1}
label{font-weight:700;display:block;margin:0 0 8px}
input,select,textarea{width:100%;padding:14px;border:1px solid #d6d8df;border-radius:12px;font-size:16px;background:#fff}
textarea{min-height:100px;resize:vertical}
.section{margin-top:28px;padding-top:22px;border-top:1px solid #eee}
.checks{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.check{border:1px solid #ddd;border-radius:12px;padding:12px;background:#fafafa}
button{width:100%;margin-top:26px;padding:17px;border:0;border-radius:14px;background:#4c43e8;color:#fff;font-size:18px;font-weight:800;cursor:pointer}
button:disabled{opacity:.6}
.result{margin-top:30px}
.result img{display:block;width:100%;border:1px solid #ddd;border-radius:14px;background:#fff}
.error{background:#fff0f0;color:#b00020;padding:15px;border-radius:12px;margin-top:20px;white-space:pre-wrap}
.brand{text-align:center;color:#777;margin-top:20px;font-weight:600}
@media(max-width:700px){.grid{grid-template-columns:1fr}.full{grid-column:auto}.checks{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
<div class="card">
<h1>Architectural Floor Plan Generator</h1>
<div class="sub">Tell us what you need. AI will create a new architectural 2D concept plan.</div>

<form id="planForm">
<div class="grid">
<div>
<label>BHK / Bedrooms</label>
<input name="bhk" type="number" min="1" max="20" required value="3">
</div>
<div>
<label>Plot Width (ft)</label>
<input name="plot_width" type="number" min="10" required value="70">
</div>
<div>
<label>Plot Length (ft)</label>
<input name="plot_length" type="number" min="10" required value="50">
</div>
<div>
<label>Road / Main Entrance Orientation</label>
<select name="orientation">
<option>North</option><option>East</option><option>South</option><option>West</option>
</select>
</div>

<div class="full section">
<label>Required Rooms / Spaces</label>
<div class="checks">
<label class="check"><input type="checkbox" name="rooms" value="Living Room" checked> Living Room</label>
<label class="check"><input type="checkbox" name="rooms" value="Kitchen" checked> Kitchen</label>
<label class="check"><input type="checkbox" name="rooms" value="Dining" checked> Dining</label>
<label class="check"><input type="checkbox" name="rooms" value="Master Bedroom" checked> Master Bedroom</label>
<label class="check"><input type="checkbox" name="rooms" value="Common Toilet" checked> Common Toilet</label>
<label class="check"><input type="checkbox" name="rooms" value="Attached Toilet"> Attached Toilet</label>
<label class="check"><input type="checkbox" name="rooms" value="Staircase"> Staircase</label>
<label class="check"><input type="checkbox" name="rooms" value="Store"> Store</label>
<label class="check"><input type="checkbox" name="rooms" value="Puja Room"> Puja Room</label>
<label class="check"><input type="checkbox" name="rooms" value="Balcony"> Balcony</label>
<label class="check"><input type="checkbox" name="rooms" value="Study Room"> Study Room</label>
<label class="check"><input type="checkbox" name="rooms" value="Utility"> Utility</label>
</div>
</div>

<div class="full section">
<label>Additional Facilities</label>
<div class="checks">
<label class="check"><input type="checkbox" name="extras" value="Car Parking"> Car Parking</label>
<label class="check"><input type="checkbox" name="extras" value="Two-wheeler Parking"> Two-wheeler Parking</label>
<label class="check"><input type="checkbox" name="extras" value="Garden/Open Space"> Garden/Open Space</label>
<label class="check"><input type="checkbox" name="extras" value="Front Verandah"> Front Verandah</label>
<label class="check"><input type="checkbox" name="extras" value="Back Open Space"> Back Open Space</label>
<label class="check"><input type="checkbox" name="extras" value="Laundry Area"> Laundry Area</label>
</div>
</div>

<div>
<label>Wall Type</label>
<select name="wall_type">
<option>Standard masonry wall</option>
<option>Thick external wall with thinner internal partitions</option>
<option>Uniform wall thickness</option>
</select>
</div>
<div>
<label>Staircase Requirement</label>
<select name="staircase">
<option>Not required</option>
<option>Internal staircase</option>
<option>External staircase</option>
<option>U-shaped staircase</option>
<option>L-shaped staircase</option>
</select>
</div>
<div>
<label>Parking</label>
<select name="parking">
<option>No parking</option>
<option>1 car</option>
<option>2 cars</option>
<option>1 car + 2 two-wheelers</option>
<option>2 cars + two-wheelers</option>
</select>
</div>
<div>
<label>Vastu Preference</label>
<select name="vastu">
<option>Not specified</option>
<option>Prefer Vastu principles</option>
<option>Strong Vastu priority</option>
</select>
</div>
<div class="full">
<label>Special Requirements</label>
<textarea name="special" placeholder="Describe anything important: room sizes, privacy, elderly-friendly access, separate entrance, servant room, work-from-home space, etc."></textarea>
</div>
</div>

<button id="btn" type="submit">GENERATE NEW FLOOR PLAN</button>
</form>

<div id="result" class="result"></div>
</div>
<div class="brand">Architectural Floor Plan Generator<br>by ANIK KUMAR</div>
</div>

<script>
const form=document.getElementById("planForm");
const btn=document.getElementById("btn");
const result=document.getElementById("result");

form.addEventListener("submit",async(e)=>{
 e.preventDefault();
 btn.disabled=true;
 btn.textContent="GENERATING FLOOR PLAN...";
 result.innerHTML="<p>Creating your architectural concept plan...</p>";

 const fd=new FormData(form);
 try{
   const r=await fetch("/generate",{method:"POST",body:fd});
   const data=await r.json();
   if(!r.ok) throw new Error(data.detail || "Generation failed");
   result.innerHTML='<h2>Generated Plan</h2><img alt="Generated architectural floor plan" src="'+data.image+'">';
 }catch(err){
   result.innerHTML='<div class="error"><b>Generation failed</b><br>'+err.message+'</div>';
 }finally{
   btn.disabled=false;
   btn.textContent="GENERATE NEW FLOOR PLAN";
 }
});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home():
    return PAGE


@app.post("/generate")
async def generate(
    bhk: int = Form(...),
    plot_width: float = Form(...),
    plot_length: float = Form(...),
    orientation: str = Form(...),
    rooms: Optional[list[str]] = Form(None),
    extras: Optional[list[str]] = Form(None),
    special: str = Form(""),
    wall_type: str = Form("Standard masonry wall"),
    staircase: str = Form("Not required"),
    parking: str = Form("No parking"),
    vastu: str = Form("Not specified"),
):
    data = {
        "bhk": bhk,
        "plot_width": plot_width,
        "plot_length": plot_length,
        "orientation": orientation,
        "rooms": rooms or [],
        "extras": extras or [],
        "special": special.strip() or "None",
        "wall_type": wall_type,
        "staircase": staircase,
        "parking": parking,
        "vastu": vastu,
    }

    try:
        prompt = build_prompt(data)
        image = generate_image(prompt)
        return {"image": image}
    except Exception as exc:
        # Do not expose the API key or other secrets.
        message = str(exc)
        if "API key" in message or "api_key" in message.lower():
            message = "Gemini API key is missing or invalid. Check GEMINI_API_KEY in Render."
        return {"detail": message}


@app.get("/health")
def health():
    return {"status": "ok"}
