
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
import sqlite3, json, uuid, math, csv, io
from pathlib import Path
from fastapi.responses import HTMLResponse

BASE=Path(__file__).resolve().parent
DB=BASE/"gharplan.db"
INDEX_HTML = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GharPlan AI</title>\n<style>\n:root{--p:#5b67f1;--ink:#172033;--muted:#687386;--line:#e3e7ef}*{box-sizing:border-box}body{margin:0;font-family:Inter,Arial,sans-serif;background:#f5f7fb;color:var(--ink)}header{height:68px;background:#fff;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between;padding:0 26px;position:sticky;top:0;z-index:4}.logo{font-size:22px;font-weight:850}.logo b{color:var(--p)}.app{max-width:1350px;margin:auto;padding:24px 16px}.top h1{margin:0;font-size:30px}.top p{margin:6px 0 20px;color:var(--muted)}.layout{display:grid;grid-template-columns:330px 1fr;gap:18px}.card{background:#fff;border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 5px 20px #1d275b0a}.field{margin-bottom:12px}.field label{font-size:12px;font-weight:750;color:#596476;display:block;margin-bottom:5px}.field input,.field select{width:100%;height:41px;border:1px solid #d7dce7;border-radius:8px;padding:0 10px;background:#fff}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.checks{display:grid;grid-template-columns:1fr 1fr;gap:7px}.check{border:1px solid var(--line);padding:8px;border-radius:8px;font-size:13px}.btn{width:100%;height:44px;border:0;border-radius:9px;background:var(--p);color:#fff;font-weight:800;cursor:pointer}.btn.dark{background:var(--ink)}.btn.light{background:#fff;color:var(--ink);border:1px solid var(--line)}.toolbar{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px}.toolbar button{border:1px solid var(--line);background:#fff;padding:8px 10px;border-radius:8px;cursor:pointer}.plans{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.plan{border:1px solid var(--line);border-radius:12px;padding:9px;cursor:pointer}.plan.selected{border:2px solid var(--p)}.plan h3{margin:3px 0 8px;font-size:13px}.plan svg{width:100%;border:1px solid #edf0f5;background:#fff}.muted{color:var(--muted);font-size:12px}.status{min-height:18px;margin-top:8px;color:var(--p);font-size:12px}.project-list{margin-top:12px;border-top:1px solid var(--line);padding-top:10px}.project{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid #f0f2f6;font-size:12px}.project button{border:0;background:none;color:#d14b4b;cursor:pointer}.modal{position:fixed;inset:0;background:#11182766;display:none;align-items:center;justify-content:center;z-index:8}.modal .box{background:white;border-radius:16px;padding:20px;width:min(520px,92vw)}.modal textarea{width:100%;height:110px;border:1px solid var(--line);border-radius:9px;padding:10px}@media(max-width:900px){.layout{grid-template-columns:1fr}.plans{grid-template-columns:1fr}}\n@media print{header,.sidebar,.toolbar,.top p{display:none}.app{padding:0}.layout{display:block}.card{border:0;box-shadow:none}.plans{grid-template-columns:repeat(3,1fr)}}\n\n</style></head><body>\n<header><div class="logo">GharPlan <b>AI</b></div><div class="muted">Home Design Platform · MVP</div></header>\n<div class="app"><div class="top"><h1>AI Home Designer</h1><p>Generate dimension-aware Indian residential concepts, save projects and export room schedules.</p></div>\n<div class="layout">\n<aside class="card sidebar"><h3>Project requirements</h3>\n<div class="row"><div class="field"><label>Length (ft)</label><input id="L" type="number" value="70" min="30"></div><div class="field"><label>Width (ft)</label><input id="W" type="number" value="25" min="15"></div></div>\n<div class="row"><div class="field"><label>House type</label><select id="bhk"><option>2BHK</option><option>1BHK</option><option>3BHK</option><option>Custom</option></select></div><div class="field"><label>Floors</label><select id="floors"><option>Ground floor</option><option>G+1</option><option>G+2</option></select></div></div>\n<div class="field"><label>Parking</label><select id="parking"><option>1 Car</option><option>2 Cars</option><option>No parking</option></select></div>\n<div class="field"><label>Preferences</label><div class="checks"><label class="check"><input id="garden" type="checkbox" checked> Garden</label><label class="check"><input id="vastu" type="checkbox"> Vastu</label></div></div>\n<div class="field"><label>Road side</label><select id="road"><option value="front">Front</option><option value="north">North</option><option value="east">East</option><option value="west">West</option><option value="south">South</option></select></div>\n<div class="field"><label>Additional rooms (comma separated)</label><input id="custom" placeholder="Puja, Store, Office"></div>\n<button class="btn" onclick="generate()">Generate 3 Plans</button><div class="status" id="status"></div>\n<hr><div class="field"><label>Project name</label><input id="name" value="70x25 2BHK House"></div>\n<button class="btn dark" onclick="save()">Save selected plan</button>\n<button class="btn light" style="margin-top:7px" onclick="loadProjects()">Refresh projects</button>\n<div id="projects" class="project-list"></div>\n</aside>\n<section class="card"><div class="toolbar"><div><h3 style="margin:0">Generated concepts</h3><span class="muted">Select a plan to save/export</span></div><div><button onclick="window.print()">Print / PDF</button></div></div>\n<div id="plans" class="plans"></div><div id="details" class="muted" style="margin-top:14px"></div></section>\n</div></div>\n\n<script>\n\nlet data=null,selected=0;\nfunction fill(p){return ({bedroom:"#f8f1e9",kitchen:"#eef7ef",utility:"#eef7ef",toilet:"#f3f3fb",parking:"#f5f0e8",garden:"#eaf6ea",living:"#f2f4f8",dining:"#f2f4f8",access:"#fafbfc"})[p]||"#f7f8fb"}\nfunction svg(p){let L=p.plot.length_ft,W=p.plot.width_ft,S=Math.min(3,240/L,330/W),ox=28,oy=25,pw=L*S,ph=W*S,s=`<svg viewBox="0 0 ${Math.max(290,pw+55)} ${Math.max(370,ph+45)}" xmlns="http://www.w3.org/2000/svg"><text x="${(pw+55)/2}" y="12" text-anchor="middle" font-size="9" font-weight="bold">OPTION ${p.option}</text><line x1="${ox}" y1="${oy-6}" x2="${ox+pw}" y2="${oy-6}" stroke="#5b67f1"/><text x="${ox+pw/2}" y="${oy-9}" text-anchor="middle" font-size="6" fill="#5b67f1">${L}′</text><text x="8" y="${oy+ph/2}" font-size="6" fill="#5b67f1">${W}′</text>`;\n for(let r of p.rooms){if(r.width_ft<=0||r.depth_ft<=0)continue;let x=ox+r.x_ft*S,y=oy+r.y_ft*S,w=r.width_ft*S,h=r.depth_ft*S;s+=`<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${fill(r.purpose)}" stroke="#172033"/><text x="${x+w/2}" y="${y+h/2}" text-anchor="middle" dominant-baseline="middle" font-size="6">${r.name}</text>`}return s+"</svg>"}\nfunction render(){if(!data)return;plans.innerHTML=data.plans.map((p,i)=>`<div class="plan ${i===selected?"selected":""}" onclick="selected=${i};render()"><h3>Option ${p.option} · ${p.score}/99</h3>${svg(p)}<div class="muted">${p.warnings[0]}</div></div>`).join("");let p=data.plans[selected];details.innerHTML=`<b>Selected option ${p.option}</b> · ${p.rooms.filter(r=>r.width_ft>0).length} spaces · Plot ${p.plot.length_ft}′ × ${p.plot.width_ft}′`}\nasync function generate(){let customRooms=custom.value.split(",").map(x=>x.trim()).filter(Boolean);let body={length_ft:+L.value,width_ft:+W.value,bhk:bhk.value,floors:floors.value,parking:parking.value,garden:garden.checked,vastu:vastu.checked,road_side:road.value,custom_rooms:customRooms};status.textContent="Generating with backend…";try{let r=await fetch("/api/v1/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});let x=await r.json();if(!r.ok)throw Error(x.detail||"Generation failed");data=x;selected=0;render();status.textContent="3 plans generated."; }catch(e){status.textContent=e.message}}\nasync function save(){if(!data)return alert("Generate a plan first");let req={length_ft:+L.value,width_ft:+W.value,bhk:bhk.value,floors:floors.value,parking:parking.value,garden:garden.checked,vastu:vastu.checked,road_side:road.value,custom_rooms:custom.value.split(",").map(x=>x.trim()).filter(Boolean)};let r=await fetch("/api/v1/projects",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name:name.value,request:req,plan:data.plans[selected]})});let x=await r.json();status.textContent="Saved: "+x.id;loadProjects()}\nasync function loadProjects(){let r=await fetch("/api/v1/projects"),xs=await r.json();projects.innerHTML=xs.length?xs.map(x=>`<div class="project"><span>${x.name}</span><button onclick="del(\'${x.id}\')">Delete</button></div>`).join(""):"<span class=\'muted\'>No saved projects</span>"}\nasync function del(id){await fetch("/api/v1/projects/"+id,{method:"DELETE"});loadProjects()}\ngenerate();\n</script>\n\n</body></html>'
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
    L,W=req.length_ft,req.width_ft
    if L<30 or W<15: raise HTTPException(400,"Minimum supported conceptual plot is 30×15 ft.")
    garden=min(15,W*.30) if req.garden else 0
    park=min(16,W*.32) if req.parking!="No parking" else 0
    if W-garden-park<24:
        garden=max(4,garden-3);park=max(0,park-3)
    y=garden+park; band=max(8,(W-y)/3); rooms=[]
    if req.garden: rooms.append(R("Garden",0,0,L,garden,"garden"))
    if req.parking!="No parking":
        pw=min(16,L*.30)
        rooms.append(R("Car Parking",0,garden,pw,park,"parking"))
        if pw<L: rooms.append(R("Entry/Walway",pw,garden,L-pw,park,"access"))
    if req.bhk=="1BHK":
        rooms += [R("Living",0,y,L*.55,band,"living"),R("Bedroom",L*.55,y,L*.45,band,"bedroom"),
                  R("Kitchen",0,y+band,L*.55,band,"kitchen"),R("Toilet",L*.55,y+band,L*.45,band,"toilet"),
                  R("Dining/Utility",0,y+2*band,L,band,"dining")]
    elif req.bhk=="3BHK":
        if option==1:
            rooms += [R("Living",0,y,L*.5,band,"living"),R("Bedroom 1",L*.5,y,L*.5,band,"bedroom"),
                      R("Bedroom 2",0,y+band,L*.5,band,"bedroom"),R("Bedroom 3",L*.5,y+band,L*.5,band,"bedroom"),
                      R("Kitchen",0,y+2*band,L*.55,band,"kitchen"),R("Toilets",L*.55,y+2*band,L*.45,band,"toilet")]
        else:
            rooms += [R("Bedroom 1",0,y,L*.45,band,"bedroom"),R("Living",L*.45,y,L*.55,band,"living"),
                      R("Bedroom 2",0,y+band,L*.5,band,"bedroom"),R("Bedroom 3",L*.5,y+band,L*.5,band,"bedroom"),
                      R("Dining",0,y+2*band,L*.55,band,"dining"),R("Kitchen",L*.55,y+2*band,L*.45,band,"kitchen")]
    else:
        variants=[
        [("Living",0,.50),("Bedroom 1",.50,.50),("Bedroom 2",0,.50)],
        [("Living/Dining",0,.58),("Kitchen",.58,.42),("Bedroom 1",0,.50),("Bedroom 2",.50,.50)],
        [("Bedroom 1",0,.45),("Living",.45,.55),("Dining",0,.55),("Kitchen",.55,.45),("Bedroom 2",0,.38)]][option-1]
        if option==1:
            rooms += [R("Living",0,y,L*.5,band,"living"),R("Bedroom 1",L*.5,y,L*.5,band,"bedroom"),
                      R("Bedroom 2",0,y+band,L*.5,band,"bedroom"),R("Kitchen",L*.5,y+band,L*.3,band,"kitchen"),
                      R("Toilet 1",L*.8,y+band,L*.2,band,"toilet"),R("Dining/Utility",0,y+2*band,L*.62,band,"dining"),
                      R("Toilet 2",L*.62,y+2*band,L*.38,band,"toilet")]
        elif option==2:
            rooms += [R("Living/Dining",0,y,L*.58,band,"living"),R("Kitchen",L*.58,y,L*.42,band,"kitchen"),
                      R("Bedroom 1",0,y+band,L*.5,band,"bedroom"),R("Bedroom 2",L*.5,y+band,L*.5,band,"bedroom"),
                      R("Toilet 1",0,y+2*band,L*.34,band,"toilet"),R("Utility",L*.34,y+2*band,L*.34,band,"utility"),
                      R("Toilet 2",L*.68,y+2*band,L*.32,band,"toilet")]
        else:
            rooms += [R("Bedroom 1",0,y,L*.45,band,"bedroom"),R("Living",L*.45,y,L*.55,band,"living"),
                      R("Dining",0,y+band,L*.55,band,"dining"),R("Kitchen",L*.55,y+band,L*.45,band,"kitchen"),
                      R("Bedroom 2",0,y+2*band,L*.38,band,"bedroom"),R("Toilet",L*.38,y+2*band,L*.3,band,"toilet"),
                      R("Utility",L*.68,y+2*band,L*.32,band,"utility")]
    if req.custom_rooms:
        # Add requested spaces into a compact metadata list; full auto-placement is next optimizer layer.
        for n in req.custom_rooms[:6]:
            rooms.append(R(n,0,0,0,0,"custom"))
    score=68+(8 if req.garden else 0)+(7 if req.parking!="No parking" else 0)+(4 if req.vastu else 0)+(3 if option==2 else 0)
    return {"option":option,"score":min(score,99),"plot":{"length_ft":L,"width_ft":W},
            "rooms":rooms,"metadata":{"bhk":req.bhk,"floors":req.floors,"road_side":req.road_side},
            "warnings":["Conceptual AI-assisted planning only.","Verify local setbacks/bylaws and obtain professional structural/architectural review before construction."]}

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
