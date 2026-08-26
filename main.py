
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
import sqlite3, json, uuid, math, csv, io
from pathlib import Path
from fastapi.responses import HTMLResponse

BASE=Path(__file__).resolve().parent
DB=BASE/"gharplan.db"
INDEX_HTML = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GharPlan AI</title>\n<style>\n:root{--p:#5b67f1;--ink:#172033;--muted:#687386;--line:#e3e7ef}*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:var(--ink)}header{height:68px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 26px;position:sticky;top:0;z-index:4}.logo{font-size:22px;font-weight:850}.logo b{color:var(--p)}.app{max-width:1350px;margin:auto;padding:24px 16px}.top h1{margin:0;font-size:30px}.top p{margin:6px 0 20px;color:var(--muted)}.layout{display:grid;grid-template-columns:330px 1fr;gap:18px}.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 5px 20px #1d275b0a}.field{margin-bottom:12px}.field label{font-size:12px;font-weight:750;color:#596476;display:block;margin-bottom:5px}.field input,.field select{width:100%;height:41px;border:1px solid #d7dce7;border-radius:8px;padding:0 10px;background:#fff}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.checks{display:grid;grid-template-columns:1fr 1fr;gap:7px}.check{border:1px solid var(--line);padding:8px;border-radius:8px;font-size:13px}.btn{width:100%;height:44px;border:0;border-radius:9px;background:var(--p);color:#fff;font-weight:800;cursor:pointer}.btn.dark{background:var(--ink)}.btn.light{background:#fff;color:var(--ink);border:1px solid var(--line)}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px}.toolbar button{border:1px solid var(--line);background:#fff;padding:8px 10px;border-radius:8px;cursor:pointer}.plans{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.plan{border:1px solid var(--line);border-radius:12px;padding:9px;cursor:pointer}.plan.selected{border:2px solid var(--p)}.plan h3{margin:3px 0 8px;font-size:13px}.plan svg{width:100%;border:1px solid #111827;background:#fff}.cadplan{shape-rendering:geometricPrecision}.room text{pointer-events:none}.muted{color:var(--muted);font-size:12px}.status{min-height:18px;margin-top:8px;color:var(--p);font-size:12px}.project-list{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}.project{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f0f2f6;font-size:12px}.project button{border:0;background:none;color:#d14b4b;cursor:pointer}.modal{position:fixed;inset:0;background:#11182766;display:none;align-items:center;justify-content:center;z-index:8}.modal .box{background:white;border-radius:16px;padding:20px;width:min(520px,92vw)}.modal textarea{width:100%;height:110px;border:1px solid var(--line);border-radius:9px;padding:10px}@media(max-width:900px){.layout{grid-template-columns:1fr}.plans{grid-template-columns:1fr}}\n@media print{header,.sidebar,.toolbar,.top p{display:none}.app{padding:0}.layout{display:block}.card{border:0;box-shadow:none}.plans{grid-template-columns:repeat(3,1fr)}}\n\n</style></head><body>\n<header><div class="logo">GharPlan <b>AI</b></div><div class="muted">Home Design Platform · MVP</div></header>\n<div class="app"><div class="top"><h1>AI Home Designer</h1><p>Generate dimension-rich architectural concepts with room sizes, internal dimensions, walls, furniture symbols, entry, north arrow and title block.</p></div>\n<div class="layout">\n<aside class="card sidebar"><h3>Project requirements</h3>\n<div class="row"><div class="field"><label>Length (ft)</label><input id="L" type="number" value="70" min="30"></div><div class="field"><label>Width (ft)</label><input id="W" type="number" value="25" min="15"></div></div>\n<div class="row"><div class="field"><label>House type</label><select id="bhk"><option>2BHK</option><option>1BHK</option><option>3BHK</option><option>Custom</option></select></div><div class="field"><label>Floors</label><select id="floors"><option>Ground floor</option><option>G+1</option><option>G+2</option></select></div></div>\n<div class="field"><label>Parking</label><select id="parking"><option>1 Car</option><option>2 Cars</option><option>No parking</option></select></div>\n<div class="field"><label>Preferences</label><div class="checks"><label class="check"><input id="garden" type="checkbox" checked> Garden</label><label class="check"><input id="vastu" type="checkbox"> Vastu</label></div></div>\n<div class="field"><label>Road side</label><select id="road"><option value="front">Front</option><option value="north">North</option><option value="east">East</option><option value="west">West</option><option value="south">South</option></select></div>\n<div class="field"><label>Additional rooms (comma separated)</label><input id="custom" placeholder="Puja, Store, Office"></div>\n<button class="btn" onclick="generate()">Generate 3 Plans</button><div class="status" id="status"></div>\n<hr><div class="field"><label>Project name</label><input id="name" value="70x25 2BHK House"></div>\n<button class="btn dark" onclick="save()">Save selected plan</button>\n<button class="btn light" style="margin-top:7px" onclick="loadProjects()">Refresh projects</button>\n<div id="projects" class="project-list"></div>\n</aside>\n<section class="card"><div class="toolbar"><div><h3 style="margin:0">Generated concepts</h3><span class="muted">Select a plan to save/export</span></div><div><button onclick="window.print()">Print / PDF</button></div></div>\n<div id="plans" class="plans"></div><div id="details" class="muted" style="margin-top:14px"></div></section>\n</div></div>\n\n<script>\n\nlet data=null,selected=0;\nfunction fill(p){return ({bedroom:"#f8f1e9",kitchen:"#eef7ef",utility:"#eef7ef",toilet:"#f3f3fb",parking:"#f5f0e8",garden:"#eaf6ea",living:"#f2f4f8",dining:"#f2f4f8",access:"#fafbfc"})[p]||"#f7f8fb"}\nfunction svg(p){\n const L=p.plot.length_ft,W=p.plot.width_ft,S=Math.min(8,760/L,360/W),ox=72,oy=64,pw=L*S,ph=W*S,vw=pw+145,vh=ph+150;\n const esc=x=>String(x).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");\n let out=`<svg class="cadplan" viewBox="0 0 ${vw} ${vh}" xmlns="http://www.w3.org/2000/svg"><rect width="${vw}" height="${vh}" fill="#fff"/>\n <text x="${vw/2}" y="20" text-anchor="middle" font-size="14" font-weight="800">GROUND FLOOR PLAN · ${esc(p.metadata.bhk)} · OPTION ${p.option}</text>\n <text x="${vw/2}" y="39" text-anchor="middle" font-size="9">PLOT SIZE — ${L}′-0″ × ${W}′-0″ | CONCEPTUAL ARCHITECTURAL PLAN</text>\n <rect x="${ox}" y="${oy}" width="${pw}" height="${ph}" fill="#fff" stroke="#111827" stroke-width="5"/><rect x="${ox+4}" y="${oy+4}" width="${pw-8}" height="${ph-8}" fill="none" stroke="#374151"/>\n <line x1="${ox}" y1="${oy-31}" x2="${ox+pw}" y2="${oy-31}" stroke="#111827"/><line x1="${ox}" y1="${oy-37}" x2="${ox}" y2="${oy-25}" stroke="#111827"/><line x1="${ox+pw}" y1="${oy-37}" x2="${ox+pw}" y2="${oy-25}" stroke="#111827"/><text x="${ox+pw/2}" y="${oy-36}" text-anchor="middle" font-size="11" font-weight="700">${L}′-0″</text>\n <line x1="${ox-32}" y1="${oy}" x2="${ox-32}" y2="${oy+ph}" stroke="#111827"/><line x1="${ox-38}" y1="${oy}" x2="${ox-26}" y2="${oy}" stroke="#111827"/><line x1="${ox-38}" y1="${oy+ph}" x2="${ox-26}" y2="${oy+ph}" stroke="#111827"/><text x="${ox-43}" y="${oy+ph/2}" transform="rotate(-90 ${ox-43} ${oy+ph/2})" text-anchor="middle" font-size="11" font-weight="700">${W}′-0″</text>`;\n for(const r of p.rooms){if(r.width_ft<=0||r.depth_ft<=0)continue;const x=ox+r.x_ft*S,y=oy+r.y_ft*S,w=r.width_ft*S,h=r.depth_ft*S,fs=Math.max(7,Math.min(12,Math.min(w,h)/9));out+=`<g class="room"><rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill(r.purpose)}" stroke="#111827" stroke-width="2"/><text x="${x+w/2}" y="${y+h/2-fs/2}" text-anchor="middle" font-size="${fs}" font-weight="800">${esc(r.name)}</text><text x="${x+w/2}" y="${y+h/2+fs+2}" text-anchor="middle" font-size="${Math.max(6,fs-2)}" fill="#374151">${r.width_ft}′-0″ × ${r.depth_ft}′-0″</text>`;if(w>45)out+=`<line x1="${x+7}" y1="${y+10}" x2="${x+w-7}" y2="${y+10}" stroke="#4b5563" stroke-width=".7"/><text x="${x+w/2}" y="${y+8}" text-anchor="middle" font-size="6" fill="#374151">${r.width_ft}′</text>`;if(h>45)out+=`<line x1="${x+10}" y1="${y+8}" x2="${x+10}" y2="${y+h-8}" stroke="#4b5563" stroke-width=".7"/><text x="${x+7}" y="${y+h/2}" transform="rotate(-90 ${x+7} ${y+h/2})" text-anchor="middle" font-size="6" fill="#374151">${r.depth_ft}′</text>`;out+=`</g>`;}\n for(const r of p.rooms){if(r.width_ft<=0||r.depth_ft<=0)continue;const x=ox+r.x_ft*S,y=oy+r.y_ft*S,w=r.width_ft*S,h=r.depth_ft*S;if(/BEDROOM/i.test(r.name))out+=`<rect x="${x+w*.32}" y="${y+h*.30}" width="${w*.36}" height="${h*.35}" rx="2" fill="none" stroke="#6b7280"/><line x1="${x+w*.32}" y1="${y+h*.39}" x2="${x+w*.68}" y2="${y+h*.39}" stroke="#6b7280"/><circle cx="${x+w*.38}" cy="${y+h*.35}" r="3" fill="none" stroke="#9ca3af"/><circle cx="${x+w*.62}" cy="${y+h*.35}" r="3" fill="none" stroke="#9ca3af"/>`;if(/LIVING/i.test(r.name))out+=`<rect x="${x+w*.30}" y="${y+h*.48}" width="${w*.40}" height="${Math.min(18,h*.16)}" rx="5" fill="none" stroke="#6b7280"/>`;if(/DINING/i.test(r.name))out+=`<ellipse cx="${x+w/2}" cy="${y+h/2+18}" rx="${Math.min(w*.22,45)}" ry="${Math.min(h*.12,25)}" fill="none" stroke="#6b7280"/>`;if(/KITCHEN/i.test(r.name))out+=`<path d="M ${x+w*.18} ${y+h*.25} H ${x+w*.82} V ${y+h*.36} H ${x+w*.18} Z" fill="none" stroke="#6b7280"/><circle cx="${x+w*.64}" cy="${y+h*.30}" r="5" fill="none" stroke="#6b7280"/>`;}\n out+=`<text x="${ox+pw/2}" y="${oy+ph+25}" text-anchor="middle" font-size="10" font-weight="800">MAIN ENTRANCE / ROAD</text><path d="M ${ox+pw*.48} ${oy+ph} v 28 M ${ox+pw*.52} ${oy+ph} v 28" stroke="#111827" stroke-width="2"/><g transform="translate(${vw-68},${vh-72})"><circle cx="0" cy="0" r="25" fill="none" stroke="#111827"/><path d="M0 -24 L5 0 L0 24 L-5 0 Z" fill="#111827"/><text x="0" y="-31" text-anchor="middle" font-weight="800">N</text><text x="31" y="5" text-anchor="middle">E</text><text x="0" y="38" text-anchor="middle">S</text><text x="-31" y="5" text-anchor="middle">W</text></g><rect x="${ox}" y="${vh-66}" width="${Math.min(360,pw*.58)}" height="50" fill="#fff" stroke="#111827"/><text x="${ox+8}" y="${vh-49}" font-size="10" font-weight="800">GROUND FLOOR PLAN (${esc(p.metadata.bhk)} HOUSE)</text><text x="${ox+8}" y="${vh-34}" font-size="8">PLOT SIZE — ${L}′-0″ × ${W}′-0″</text><text x="${ox+8}" y="${vh-21}" font-size="8">GENERATED BY GHARPLAN AI · CONCEPT ONLY</text></svg>`;return out;}\nfunction render(){if(!data)return;plans.innerHTML=data.plans.map((p,i)=>`<div class="plan ${i===selected?"selected":""}" onclick="selected=${i};render()"><h3>Option ${p.option} · ${p.score}/99</h3>${svg(p)}<div class="muted">${p.warnings[0]}</div></div>`).join("");let p=data.plans[selected];details.innerHTML=`<b>Selected option ${p.option}</b> · ${p.rooms.filter(r=>r.width_ft>0).length} spaces · Plot ${p.plot.length_ft}′ × ${p.plot.width_ft}′`}\nasync function generate(){let customRooms=custom.value.split(",").map(x=>x.trim()).filter(Boolean);let body={length_ft:+L.value,width_ft:+W.value,bhk:bhk.value,floors:floors.value,parking:parking.value,garden:garden.checked,vastu:vastu.checked,road_side:road.value,custom_rooms:customRooms};status.textContent="Generating with backend…";try{let r=await fetch("/api/v1/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});let x=await r.json();if(!r.ok)throw Error(x.detail||"Generation failed");data=x;selected=0;render();status.textContent="3 plans generated."; }catch(e){status.textContent=e.message}}\nasync function save(){if(!data)return alert("Generate a plan first");let req={length_ft:+L.value,width_ft:+W.value,bhk:bhk.value,floors:floors.value,parking:parking.value,garden:garden.checked,vastu:vastu.checked,road_side:road.value,custom_rooms:custom.value.split(",").map(x=>x.trim()).filter(Boolean)};let r=await fetch("/api/v1/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name.value,request:req,plan:data.plans[selected]})});let x=await r.json();status.textContent="Saved: "+x.id;loadProjects()}\nasync function loadProjects(){let r=await fetch("/api/v1/projects"),xs=await r.json();projects.innerHTML=xs.length?xs.map(x=>`<div class="project"><span>${x.name}</span><button onclick="del(\'${x.id}\')">Delete</button></div>`).join(""):"<span class=\'muted\'>No saved projects</span>"}\nasync function del(id){await fetch("/api/v1/projects/"+id,{method:"DELETE"});loadProjects()}\ngenerate();\n</script>\n\n</body></html>'
app=FastAPI(title="GharPlan AI",version="1.0.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_methods=["*"],allow_headers=["*"])

class Req(BaseModel):
    length_ft: float=Field(gt=0)
    width_ft: float=Field(gt=0)
    bhk: Literal["1BHK","2BHK","3BHK","Custom"]="2BHK"
    floors: Literal["Ground floor","G+1","G+2"]="Ground floor"
    parking: Literal["1 Car","2 Cars","No parking"]="1 Car"
    garden: bool=True
    vastu: bool=False
    road_side: Literal["front","north","east","west","south"]="front"
    custom_rooms: list[str]=[]

class Save(BaseModel):
    name: str="Untitled Project"
    request: Req
    plan: dict

def con():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

@app.on_event("startup")
def init():
    c=con()
    c.execute("""CREATE TABLE IF NOT EXISTS projects(
      id TEXT PRIMARY KEY,name TEXT,request TEXT,plan TEXT,created_at DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    c.commit();c.close()

def R(n,x,y,w,d,p):
    return {"name":n,"x_ft":round(x,2),"y_ft":round(y,2),"width_ft":round(w,2),"depth_ft":round(d,2),"purpose":p}

def generate(req, option):
    L, W = req.length_ft, req.width_ft
    if L < 45 or W < 18:
        raise HTTPException(400, "Use at least 45 ft depth × 18 ft frontage for this 2BHK concept.")
    front=min(15.0,max(12.0,L*0.20)); house=L-front; a=W/2; rooms=[]
    if req.parking!="No parking":
        pw=min(12.5,W*0.50)
        rooms += [R("CAR PARKING",0,0,pw,front,"parking"),
                  R("GARDEN" if req.garden else "ENTRY COURT",pw,0,W-pw,front,"garden" if req.garden else "access")]
    elif req.garden: rooms.append(R("GARDEN",0,0,W,front,"garden"))
    else: rooms.append(R("FRONT SETBACK",0,0,W,front,"access"))
    y=front
    if req.bhk=="2BHK":
        layouts={
        1:[R("LIVING",0,y,W,11,"living"),R("DINING",0,y+11,a,9,"dining"),R("KITCHEN",a,y+11,a,9,"kitchen"),R("MASTER BEDROOM",0,y+20,a,13,"bedroom"),R("BEDROOM 2",a,y+20,a,13,"bedroom"),R("MASTER TOILET",0,y+33,6.5,7,"toilet"),R("COMMON TOILET",6.5,y+33,6.5,7,"toilet"),R("UTILITY",13,y+33,6,7,"utility"),R("STAIR / STORE",19,y+33,W-19,7,"stair"),R("REAR OPEN / WASH",0,y+40,W,max(1,house-40),"open")],
        2:[R("LIVING + DINING",0,y,W,12,"living"),R("KITCHEN",0,y+12,a,9,"kitchen"),R("MASTER BEDROOM",a,y+12,a,13,"bedroom"),R("BEDROOM 2",0,y+25,a,13,"bedroom"),R("MASTER TOILET",a,y+25,6.5,7,"toilet"),R("COMMON TOILET",W-6.5,y+25,6.5,7,"toilet"),R("UTILITY",a,y+32,a,7,"utility"),R("REAR OPEN / WASH",0,y+39,W,max(1,house-39),"open")],
        3:[R("LIVING",0,y,a,12,"living"),R("DINING",a,y,a,12,"dining"),R("MASTER BEDROOM",0,y+12,a,13,"bedroom"),R("BEDROOM 2",a,y+12,a,13,"bedroom"),R("KITCHEN",0,y+25,a,9,"kitchen"),R("TOILETS",a,y+25,a,7,"toilet"),R("UTILITY",0,y+34,a,7,"utility"),R("REAR OPEN / WASH",0,y+41,W,max(1,house-41),"open")]}
        rooms += layouts[option]
    elif req.bhk=="1BHK":
        rooms += [R("LIVING",0,y,W,12,"living"),R("KITCHEN + DINING",0,y+12,a,10,"kitchen"),R("BEDROOM",a,y+12,a,13,"bedroom"),R("TOILET",0,y+25,6.5,7,"toilet"),R("UTILITY",6.5,y+25,6.5,7,"utility"),R("REAR OPEN",13,y+25,W-13,max(1,house-25),"open")]
    else:
        rooms += [R("LIVING + DINING",0,y,W,11,"living"),R("BEDROOM 1",0,y+11,a,12,"bedroom"),R("BEDROOM 2",a,y+11,a,12,"bedroom"),R("KITCHEN",0,y+23,a,9,"kitchen"),R("BEDROOM 3",a,y+23,a,12,"bedroom"),R("TOILETS",0,y+32,a,7,"toilet"),R("UTILITY / REAR",a,y+32,a,max(1,house-32),"utility")]
    rooms=[r for r in rooms if r["x_ft"]+r["width_ft"]<=W+0.01 and r["y_ft"]+r["depth_ft"]<=L+0.01]
    score=84+(4 if req.garden else 0)+(4 if req.parking!="No parking" else 0)+(2 if req.vastu else 0)+(2 if option==2 else 0)
    return {"option":option,"score":min(score,99),"plot":{"length_ft":L,"width_ft":W,"frontage_ft":W,"depth_ft":L},"rooms":rooms,"metadata":{"bhk":req.bhk,"floors":req.floors,"road_side":req.road_side,"front_open_depth_ft":front},"warnings":["Conceptual architectural floor plan — not a construction drawing.","Verify setbacks, ventilation, bylaws and structural requirements with a licensed professional."]}

@app.get("/")
def root(): return HTMLResponse(INDEX_HTML)
@app.get("/health")
def health(): return {"status":"ok","version":"1.0.0"}

@app.post("/api/v1/generate")
def gen(req:Req): return {"plans":[generate(req,i) for i in (1,2,3)]}

@app.post("/api/v1/projects")
def save(p:Save):
    pid=str(uuid.uuid4());c=con()
    c.execute("INSERT INTO projects VALUES(?,?,?,?,CURRENT_TIMESTAMP)",(pid,p.name,p.request.model_dump_json(),json.dumps(p.plan)))
    c.commit();c.close();return {"id":pid,"name":p.name}

@app.get("/api/v1/projects")
def projects():
    c=con();r=c.execute("SELECT id,name,created_at FROM projects ORDER BY created_at DESC").fetchall();c.close()
    return [dict(x) for x in r]

@app.get("/api/v1/projects/{pid}")
def project(pid):
    c=con();r=c.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchone();c.close()
    if not r: raise HTTPException(404,"Project not found")
    return {"id":r["id"],"name":r["name"],"request":json.loads(r["request"]),"plan":json.loads(r["plan"]),"created_at":r["created_at"]}

@app.delete("/api/v1/projects/{pid}")
def delete(pid):
    c=con();c.execute("DELETE FROM projects WHERE id=?",(pid,));c.commit();c.close();return {"deleted":pid}

@app.get("/api/v1/export/{pid}.csv")
def export_csv(pid):
    p=project(pid);out=io.StringIO();w=csv.writer(out)
    w.writerow(["Room","X (ft)","Y (ft)","Width (ft)","Depth (ft)","Purpose"])
    for r in p["plan"]["rooms"]: w.writerow([r["name"],r["x_ft"],r["y_ft"],r["width_ft"],r["depth_ft"],r["purpose"]])
    return Response(out.getvalue(),media_type="text/csv",headers={"Content-Disposition":f'attachment; filename="{pid}.csv"'})
