import { useCallback, useEffect, useState } from "react";

const initial = {state:"waiting_for_start",message:"Waiting for start.",seed_plan:{},loaded_seed_counts:{},planting_cells:[],plant_profiles:[],catalog:[],operation:{name:"idle",status:"idle"},monitoring:{completed:0,total:0,issues_detected:0,weeds_removed:0}};

async function api(path, options) {
  const response = await fetch(path + (path.includes("?") ? "&" : "?") + "_ts=" + Date.now(), Object.assign({cache:"no-store",headers:{"Content-Type":"application/json"}}, options || {}));
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

export default function App() {
  const [state,setState]=useState(initial);
  const [error,setError]=useState("");
  const [plant,setPlant]=useState("");
  const [count,setCount]=useState(1);
  const [seedCounts,setSeedCounts]=useState({});

  const refresh=useCallback(async()=>{try{setState(await api("/api/state"));setError("");}catch(e){setError(e.message);}},[]);
  useEffect(()=>{refresh();const id=setInterval(refresh,500);return()=>clearInterval(id);},[refresh]);

  async function post(path,body={}){try{await api(path,{method:"POST",body:JSON.stringify(body)});await refresh();}catch(e){setError(e.message);}}
  const profiles=Object.fromEntries(state.plant_profiles.map(p=>[p.profile_id,p]));
  const planted=state.planting_cells.filter(c=>c.status==="planted").length;
  const running=state.operation && state.operation.status==="running";

  return <main>
    <header><h1>SpaceFruit Farm Robot</h1><p>{state.message}</p><b>Backend: {state.state}</b><div>Operation: {state.operation?.name} / {state.operation?.status}</div></header>
    {error && <div className="error">{error}</div>}

    <section className="card"><h2>Setup</h2>
      <button disabled={running || state.state!=="waiting_for_start"} onClick={()=>post("/api/start")}>Start robot</button>
    </section>

    <section className="card"><h2>Planting Plan</h2>
      <div className="controls"><select value={plant} onChange={e=>setPlant(e.target.value)}><option value="">Select plant</option>{state.catalog.map(p=><option key={p.name}>{p.name}</option>)}</select>
      <input type="number" min="1" max="1000" value={count} onChange={e=>setCount(Number(e.target.value))}/>
      <button disabled={!plant || state.state!=="waiting_for_confirmation"} onClick={()=>post("/api/add-plant",{plant,count})}>Add</button></div>
      {Object.entries(state.seed_plan).map(([name,qty])=><div className="plan-row" key={name}><span>{name}: {qty}</span><button onClick={()=>post("/api/remove-plant",{plant:name})}>Remove one</button></div>)}
      <button disabled={state.state!=="waiting_for_confirmation" || !Object.keys(state.seed_plan).length} onClick={()=>post("/api/confirm")}>Confirm planting plan</button>
    </section>

    <section className="card"><h2>Seeds</h2><p>Required: {state.total_requested_seeds||0} | Loaded: {state.seed_count||0}</p>
      {Object.entries(state.seed_plan).map(([name,qty])=><label className="seed-row" key={name}>{name}<input type="number" min="0" value={state.loaded_seed_counts?.[name] ?? qty} onChange={e=>setState(s=>({...s,loaded_seed_counts:{...s.loaded_seed_counts,[name]:Number(e.target.value)}}))}/></label>)}
      <button disabled={state.state!=="waiting_for_seeds"} onClick={()=>post("/api/load-seeds",{counts:{...state.loaded_seed_counts,...seedCounts}})}>Load / verify seeds</button>
      <button disabled={state.state!=="waiting_for_seeds" || running} onClick={()=>post("/api/start-planting")}>Start planting</button>
    </section>

    <section className="card"><h2>Planting Status</h2><p>{planted} / {state.planting_cells.length} plants completed.</p>
      <div className="grid">{state.planting_cells.map(cell=>{const p=profiles[cell.profile_id];const issue=p?.health_issue_detected;return <div key={cell.seed_number || cell.row+"-"+cell.column} className={"cell "+cell.status+(issue?" health-issue":"")} title={cell.plant+" — "+cell.status}>{p?.img?<img src={"/thumbs/"+p.img}/>:<span>?</span>}</div>})}</div>
    </section>

    <section className="card"><h2>Monitoring</h2><p>Checks every planted profile for health conditions and weeds.</p>
      <button disabled={state.state!=="complete" || running} onClick={()=>post("/api/start-monitoring")}>Start monitoring</button>
      <p>Checked: {state.monitoring?.completed||0}/{state.monitoring?.total||0} · Issues: {state.monitoring?.issues_detected||0} · Weeds removed: {state.monitoring?.weeds_removed||0}</p>
    </section>

    <section className="card"><h2>Plant Profiles</h2>{state.plant_profiles.map(p=><article className="profile" key={p.profile_id}><b>{p.plant_type}</b><span>{p.health_status}</span>{p.health_issues?.length>0&&<span className="issue-text">{p.health_issues.join(", ")}</span>}<small>{p.profile_id}</small></article>)}</section>
  </main>;
}
