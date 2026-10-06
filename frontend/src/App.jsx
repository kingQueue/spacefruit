import { useCallback, useEffect, useState } from "react";
import Marketplace from "./Marketplace";

const initial = {state:"waiting_for_start",message:"Waiting for start.",seed_plan:{},loaded_seed_counts:{},planting_cells:[],plant_profiles:[],catalog:[],harvest_inventory:{},harvest_inventory_items:[],harvested_items:[],operation:{name:"idle",status:"idle"},monitoring:{completed:0,total:0,issues_detected:0,weeds_removed:0,weeding_completed:0,weeding_total:0,weeding_percent:0,alerts:[]}};

async function api(path, options) {
  const response = await fetch(path + (path.includes("?") ? "&" : "?") + "_ts=" + Date.now(), Object.assign({cache:"no-store",headers:{"Content-Type":"application/json"}}, options || {}));
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Request failed");
  return data;
}

function fallbackThumbnail(event) {
  const image=event.currentTarget;
  if (!image.dataset.fallback) {
    image.dataset.fallback="true";
    image.src="/thumbs/default.svg";
  }
}

function thumbnailFor(plantType, storedPath) {
  if (storedPath && storedPath !== "default.svg") return storedPath;
  if (!plantType || plantType === "Empty Plot") return "default.svg";
  return plantType.trim().toLowerCase().replace(/[\s-]+/g,"_")+".svg";
}

export default function App() {
  const [state,setState]=useState(initial);
  const [error,setError]=useState("");
  const [plant,setPlant]=useState("");
  const [count,setCount]=useState(1);
  const [seedCounts,setSeedCounts]=useState({});
  const [selectedProfileId,setSelectedProfileId]=useState("");
  const [showReplantModal,setShowReplantModal]=useState(false);
  const [replantPlant,setReplantPlant]=useState("");
  const [view,setView]=useState("garden");

  const refresh=useCallback(async()=>{try{setState(await api("/api/state"));setError("");}catch(e){setError(e.message);}},[]);
  useEffect(()=>{refresh();const id=setInterval(refresh,500);return()=>clearInterval(id);},[refresh]);

  async function post(path,body={}){try{await api(path,{method:"POST",body:JSON.stringify(body)});await refresh();}catch(e){setError(e.message);}}
  function openProfile(profileId){setSelectedProfileId(profileId);document.getElementById("harvest-panel")?.scrollIntoView({behavior:"smooth",block:"center"});}
  const profiles=Object.fromEntries(state.plant_profiles.map(p=>[p.profile_id,p]));
  const planted=state.planting_cells.filter(c=>c.status==="planted"||c.status==="harvested").length;
  const running=state.operation && state.operation.status==="running";
  const requestedSeedTotal=Object.values(state.seed_plan).reduce((total,quantity)=>total+quantity,0);
  const seedsVerified=Object.keys(state.seed_plan).length>0 &&
    Object.entries(state.seed_plan).every(([name,quantity])=>Number(state.loaded_seed_counts?.[name])===quantity) &&
    state.seed_count===requestedSeedTotal;
  const currentSeedCounts=Object.fromEntries(Object.entries(state.seed_plan).map(([name,quantity])=>[
    name,seedCounts[name] ?? state.loaded_seed_counts?.[name] ?? quantity,
  ]));
  const selectedProfile=profiles[selectedProfileId];
  const selectedCell=state.planting_cells.find(c=>c.profile_id===selectedProfileId);
  const canHarvest=state.state==="complete" && !running && selectedProfile?.harvest_status!=="harvested" && selectedCell?.status==="planted";
  const canReplant=state.state==="complete" && !running && selectedProfile?.plant_type==="Empty Plot" && selectedCell?.status==="empty_plot";

  return <main className="app-shell">
    {view==="marketplace"?<Marketplace onBack={()=>setView("garden")} inventoryItems={state.harvest_inventory_items||[]}/>:<>
    <header className="app-header"><div className="brand-lockup"><div className="brand-mark" aria-hidden="true">✦</div><div><span className="brand-kicker">YOUR LITTLE PATCH IN SPACE</span><h1>SpaceFruit</h1></div></div><div className="header-actions"><a className="promo-link" href="/promo.html">About SpaceFruit <span aria-hidden="true">↗</span></a><button className="marketplace-button" onClick={()=>setView("marketplace")}>Marketplace <span aria-hidden="true">↗</span></button><div className="connection-badge"><span className="status-dot"/>Robot is {state.state.replaceAll("_"," ")}</div></div></header>
    {error && <div className="error">{error}</div>}

    <section className="garden-hero">
      <div className="hero-copy"><p className="eyebrow">A FRESH LOOK AT YOUR GARDEN</p><h2>Today in the garden</h2><p className="hero-message">{state.message}</p><div className="hero-stats"><span>🌱 <b>{planted}</b> growing</span><span>🧺 <b>{Object.values(state.harvest_inventory||{}).reduce((sum,quantity)=>sum+quantity,0)}</b> harvested</span><span className="operation-pill">{state.operation?.name} · {state.operation?.status}</span></div></div>
      <div className="garden-robot" aria-hidden="true"><span className="robot-sparkle">✧</span><div className="robot-orbit"><span>🤖</span></div><span className="robot-leaf">🌿</span></div>
    </section>

    <nav className="garden-nav" aria-label="Garden sections"><a href="#garden">Garden map</a><a href="#plan">Planting</a><a href="#monitoring">Daily care</a><a href="#harvest-panel">Harvest basket</a></nav>

    <section className="card task-card" id="setup"><div className="section-heading"><span className="section-icon">✦</span><div><p className="eyebrow">FIRST THINGS FIRST</p><h2>Wake up your garden robot</h2></div></div><p className="section-intro">Your helper will take a look around and suggest what to grow today.</p>
      <button className="primary-button" disabled={running || state.state!=="waiting_for_start"} onClick={()=>post("/api/start")}>Start garden check</button>
    </section>

    <section className="card task-card" id="plan"><div className="section-heading"><span className="section-icon">🌱</span><div><p className="eyebrow">GROW SOMETHING LOVELY</p><h2>Planting plan</h2></div></div><p className="section-intro">Pick what to grow and how many seeds to tuck into the soil.</p>
      <div className="controls"><select value={plant} onChange={e=>setPlant(e.target.value)}><option value="">Select plant</option>{state.catalog.map(p=><option key={p.name}>{p.name}</option>)}</select>
      <input type="number" min="1" max="1000" value={count} onChange={e=>setCount(Number(e.target.value))}/>
      <button disabled={!plant || state.state!=="waiting_for_confirmation"} onClick={()=>post("/api/add-plant",{plant,count})}>Add</button></div>
      {Object.entries(state.seed_plan).map(([name,qty])=><div className="plan-row" key={name}><span>{name}: {qty}</span><button onClick={()=>post("/api/remove-plant",{plant:name})}>Remove one</button></div>)}
      <button disabled={state.state!=="waiting_for_confirmation" || !Object.keys(state.seed_plan).length} onClick={()=>post("/api/confirm")}>Confirm planting plan</button>
    </section>

    <section className="card task-card" id="seeds"><div className="section-heading"><span className="section-icon">🌰</span><div><p className="eyebrow">READY FOR THE SOIL</p><h2>Seed tray</h2></div></div><p className="section-intro">Needed: <b>{state.total_requested_seeds||0}</b> seeds <span className="soft-separator">·</span> In the planter: <b>{state.seed_count||0}</b></p>
      {Object.entries(state.seed_plan).map(([name,qty])=><label className="seed-row" key={name}>{name}<input type="number" min="0" value={seedCounts[name] ?? state.loaded_seed_counts?.[name] ?? qty} onChange={e=>setSeedCounts(s=>({...s,[name]:Number(e.target.value)}))}/></label>)}
      <button className="secondary-button" disabled={state.state!=="waiting_for_seeds"} onClick={()=>post("/api/load-seeds",{counts:currentSeedCounts})}>Check seed tray</button>
      <button className="primary-button" disabled={state.state!=="waiting_for_seeds" || running || !seedsVerified} onClick={()=>post("/api/start-planting")}>Plant the garden</button>
    </section>

    <section className="card plot-card" id="garden"><div className="section-heading"><span className="section-icon">🪴</span><div><p className="eyebrow">YOUR LITTLE PATCH</p><h2>Garden map</h2></div><span className="plot-count">{planted} / {state.planting_cells.length} growing</span></div><div className="plot-legend"><span><i className="legend-dot planted-dot"/>Growing</span><span><i className="legend-dot empty-dot"/>Empty plot</span><span><i className="legend-dot issue-dot"/>Needs a little care</span></div>
      <div className="grid">{state.planting_cells.map(cell=>{const p=profiles[cell.profile_id];const issue=p?.health_issue_detected;return <button type="button" key={cell.seed_number || cell.row+"-"+cell.column} className={"cell plot-cell-button "+cell.status+(issue?" health-issue":"")} title={cell.plant+" — "+cell.status} aria-label={p?`Open ${cell.plant} plant profile`:`${cell.plant} plot has no profile yet`} disabled={!p} onClick={()=>openProfile(p.profile_id)}>{p?.img?<img src={"/thumbs/"+thumbnailFor(cell.plant,p.img)} alt={cell.plant} onError={fallbackThumbnail}/>:<span>{cell.status==="empty_plot"?"＋":"…"}</span>}</button>})}</div>
    </section>

    <section className="card task-card care-card" id="monitoring"><div className="section-heading"><span className="section-icon">💧</span><div><p className="eyebrow">A LITTLE DAILY CARE</p><h2>Garden checkup</h2></div></div><p className="section-intro">Your robot clears weeds before checking each plant for signs of trouble.</p>
      <button className="primary-button" disabled={state.state!=="complete" || running || !state.planting_cells.some(c=>c.status==="planted")} onClick={()=>post("/api/start-monitoring")}>Check on my plants</button>
      <div className="weeding-progress"><div><b>Weeding completed</b><span>{state.monitoring?.weeding_completed||0}/{state.monitoring?.weeding_total||0} locations · {state.monitoring?.weeding_percent||0}%</span></div><progress max="100" value={state.monitoring?.weeding_percent||0} aria-label="Weeding completion" /></div>
      <p>Plants checked: {state.monitoring?.completed||0}/{state.monitoring?.total||0} · Issues: {state.monitoring?.issues_detected||0} · Weeds removed: {state.monitoring?.weeds_removed||0}</p>
      {!!state.monitoring?.alerts?.length&&<div className="alerts"><h3>Camera alerts</h3><ul>{state.monitoring.alerts.map(alert=><li role="alert" key={alert.profile_id}><b>{alert.plant_type}:</b> {alert.issues.join(", ")} <small>({alert.profile_id})</small></li>)}</ul></div>}
    </section>

    <section className="card harvest-card" id="harvest-panel"><div className="section-heading"><span className="section-icon">🧺</span><div><p className="eyebrow">GOOD THINGS GATHERED</p><h2>Harvest basket</h2></div></div>
      <div className="inventory"><h3>Harvest inventory</h3>{state.harvest_inventory_items?.length?<div className="inventory-cards">{state.harvest_inventory_items.filter(item=>item.quantity>0).map(item=><article className="inventory-item" key={item.plant_type}><img src={"/thumbs/"+thumbnailFor(item.plant_type,item.img)} alt={item.plant_type} onError={fallbackThumbnail}/><div><b>{item.plant_type}</b><span>Quantity: {item.quantity}</span></div></article>)}</div>:<p>Nothing harvested yet.</p>}</div>
      {selectedProfile?<article className="profile-detail"><button className="close-profile" onClick={()=>{setSelectedProfileId("");setShowReplantModal(false);}}>Close profile</button><h3>{selectedProfile.plant_type}</h3><p>{selectedProfile.health_status}</p>{selectedProfile.health_issues?.length>0&&<p className="issue-text">{selectedProfile.health_issues.join(", ")}</p>}<small>Profile {selectedProfile.profile_id} · {selectedProfile.x_m.toFixed(2)}m, {selectedProfile.y_m.toFixed(2)}m</small>{selectedProfile.plant_type==="Empty Plot"?<><p>This location is empty and ready for a new plant.</p><button disabled={!canReplant} onClick={()=>{setReplantPlant("");setShowReplantModal(true);}}>Plant something different</button></>:<><p><b>Harvest status:</b> {selectedProfile.harvest_status?.replaceAll("_"," ")||"not checked"}</p>{selectedProfile.harvest_check_summary&&<p>{selectedProfile.harvest_check_summary}</p>}<button disabled={!canHarvest} onClick={()=>post("/api/harvest",{profile_id:selectedProfile.profile_id})}>{selectedProfile.harvest_status==="checking"?"Checking readiness…":selectedProfile.harvest_status==="harvested"?"Already harvested":"Harvest plant"}</button></>}
        {showReplantModal&&<div className="modal-backdrop" role="presentation"><section className="replant-modal" role="dialog" aria-modal="true" aria-labelledby="replant-title"><h3 id="replant-title">Replant empty plot</h3><label>Choose a plant<select value={replantPlant} onChange={e=>setReplantPlant(e.target.value)}><option value="">Select plant</option>{state.catalog.map(item=><option key={item.name} value={item.name}>{item.name}</option>)}</select></label>{replantPlant&&<div className="replant-verification"><b>Verify planting</b><p>Plant 1 {replantPlant} at this plot ({selectedProfile.x_m.toFixed(2)}m, {selectedProfile.y_m.toFixed(2)}m).</p><p>The robot will go to this location, plant one seed, and create a new plant profile.</p></div>}<div className="modal-actions"><button onClick={()=>setShowReplantModal(false)}>Cancel</button><button disabled={!replantPlant||!canReplant} onClick={()=>{post("/api/replant",{profile_id:selectedProfile.profile_id,plant:replantPlant});setShowReplantModal(false);}}>Start planting</button></div></section></div>}
      </article>:<p>Open a plant profile below to check harvest readiness or replant an empty plot.</p>}
      {!!state.harvested_items?.length&&<div className="harvest-log"><h3>Recent harvests</h3><ul>{state.harvested_items.slice().reverse().map(item=><li key={item.profile_id}>{item.quantity} {item.plant_type} · {item.harvested_at}</li>)}</ul></div>}
    </section>

    <section className="card"><h2>Plant Profiles</h2>{state.plant_profiles.map(p=><article className={"profile "+(p.plant_type==="Empty Plot"?"empty-profile":"")} key={p.profile_id}><b>{p.plant_type}</b><span>{p.health_status}</span>{p.health_issues?.length>0&&<span className="issue-text">{p.health_issues.join(", ")}</span>}<small>{p.profile_id}</small><button className="open-profile" onClick={()=>openProfile(p.profile_id)}>Open profile</button></article>)}</section>
    </>}
  </main>;
}
