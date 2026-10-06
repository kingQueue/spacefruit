import { useEffect, useState } from "react";

const otherGrowersListings = {
  trade: [
    { id:"t-1", produce:"Tomato", variety:"Heirloom mix", quantity:"3 lb", grower:"Maya's Moon Garden", location:"Northside", lookingFor:"Fresh basil" },
    { id:"t-2", produce:"Cucumber", variety:"Marketmore", quantity:"6 cucumbers", grower:"The Little Greenhouse", location:"Riverside", lookingFor:"Zucchini or squash" },
    { id:"t-3", produce:"Strawberry", variety:"Albion", quantity:"2 pints", grower:"Fern & Fig Farm", location:"Old Town", lookingFor:"Leafy greens" },
    { id:"t-4", produce:"Bell Pepper", variety:"Sweet bell mix", quantity:"4 peppers", grower:"Sunpatch Neighbors", location:"East End", lookingFor:"Herbs or tomatoes" },
  ],
  buy: [
    { id:"b-1", produce:"Carrot", variety:"Nantes", quantity:"2 bunches", grower:"Clover Patch", location:"Northside", price:"$4 / bunch" },
    { id:"b-2", produce:"Spinach", variety:"Baby leaf", quantity:"1 bag · 8 oz", grower:"Maya's Moon Garden", location:"Northside", price:"$3 / bag" },
    { id:"b-3", produce:"Zucchini", variety:"Green zucchini", quantity:"5 small squash", grower:"The Little Greenhouse", location:"Riverside", price:"$2 / lb" },
    { id:"b-4", produce:"Kale", variety:"Curly green", quantity:"2 bunches", grower:"Fern & Fig Farm", location:"Old Town", price:"$3 / bunch" },
    { id:"b-5", produce:"Basil", variety:"Sweet basil", quantity:"1 bunch", grower:"Sunpatch Neighbors", location:"East End", price:"$2 / bunch" },
    { id:"b-6", produce:"Potato", variety:"Yukon Gold", quantity:"3 lb", grower:"Clover Patch", location:"Northside", price:"$5 / bag" },
  ],
  donate: [
    { id:"d-1", produce:"Lettuce", variety:"Butterhead", quantity:"3 heads", grower:"Fern & Fig Farm", location:"Old Town", note:"Extra from this morning's picking" },
    { id:"d-2", produce:"Cilantro", variety:"Fresh bunches", quantity:"2 bunches", grower:"Maya's Moon Garden", location:"Northside", note:"Take what you need" },
    { id:"d-3", produce:"Pumpkin", variety:"Sugar pie", quantity:"2 pumpkins", grower:"Clover Patch", location:"Northside", note:"A few extras to share" },
    { id:"d-4", produce:"Swiss Chard", variety:"Rainbow chard", quantity:"1 bunch", grower:"Sunpatch Neighbors", location:"East End", note:"Free for a neighbor" },
  ],
};

const sections = [
  { id:"trade", title:"Trade", icon:"🔁", description:"Swap a little of what you have for something another grower has." },
  { id:"buy", title:"Buy / Sell", icon:"🪙", description:"Find produce to buy or offer your own fresh-picked harvest for sale." },
  { id:"donate", title:"Donate", icon:"💛", description:"Share an extra harvest with someone in the community." },
];

function thumbnailFor(produce) {
  return produce.trim().toLowerCase().replace(/[\s-]+/g,"_")+".svg";
}

function MarketSection({ section, ownListings, selectedPurchaseIds, purchasedListingIds, onTogglePurchase, onConfirmPurchase }) {
  const [query,setQuery]=useState("");
  const listedByUser=ownListings.filter(listing=>listing.active&&listing.section===section.id).map(listing=>({
    ...listing,produce:listing.plant_type,variety:"From your harvest inventory",grower:"Your garden",location:"Your neighborhood",isMine:true,
  }));
  const listings=[...otherGrowersListings[section.id].filter(listing=>!purchasedListingIds.has(listing.id)),...listedByUser].filter(listing=>listing.produce.toLowerCase().includes(query.trim().toLowerCase()));

  return <section className="card market-section" id={`market-${section.id}`}>
    <div className="section-heading"><span className="section-icon">{section.icon}</span><div><p className="eyebrow">COMMUNITY PRODUCE</p><h2>{section.title}</h2></div><span className="listing-count">{listings.length} {listings.length===1?"listing":"listings"}</span></div>
    <p className="section-intro">{section.description}</p>
    <label className="market-search"><span aria-hidden="true">⌕</span><input type="search" value={query} onChange={event=>setQuery(event.target.value)} aria-label={`Search ${section.title.toLowerCase()} listings by produce type`} placeholder="Search by produce type…"/></label>
    {section.id==="buy"&&<div className="purchase-toolbar"><span>{selectedPurchaseIds.length?`${selectedPurchaseIds.length} produce ${selectedPurchaseIds.length===1?"item":"items"} selected`:"Select produce cards to purchase"}</span><button className="primary-button" type="button" disabled={!selectedPurchaseIds.length} onClick={onConfirmPurchase}>Review purchase{selectedPurchaseIds.length?` · ${selectedPurchaseIds.length}`:""}</button></div>}
    {listings.length?<div className="market-listings">{listings.map(listing=>{
      const selectable=section.id==="buy"&&!listing.isMine;
      const selected=selectedPurchaseIds.includes(listing.id);
      return <article className={`market-listing ${selectable?"purchase-selectable":""} ${selected?"purchase-selected":""}`} key={listing.id} role={selectable?"checkbox":undefined} aria-checked={selectable?selected:undefined} tabIndex={selectable?0:undefined} onClick={selectable?()=>onTogglePurchase(listing.id):undefined} onKeyDown={selectable?event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();onTogglePurchase(listing.id);}}:undefined}>
      <img src={`/thumbs/${listing.img||thumbnailFor(listing.produce)}`} alt="" loading="lazy" onError={event=>{event.currentTarget.src="/thumbs/default.svg";event.currentTarget.onerror=null;}}/>
      <div className="listing-body"><div className="listing-title"><div><h3>{listing.produce}</h3><span>{listing.variety||"Fresh from the garden"}</span></div><b className={`listing-tag ${section.id}-tag`}>{listing.isMine?(section.id==="buy"&&listing.asking_price!=null&&Number.isFinite(Number(listing.asking_price))?`$${Number(listing.asking_price).toFixed(2)}`:"Your listing"):section.id==="trade"?"Swap":section.id==="buy"?listing.price||"For sale":"Free"}</b></div>
        <p className="listing-quantity">{listing.quantity} {listing.isMine?"available":""}{listing.weight?` · ${listing.weight} ${listing.weight_unit} each`:""}</p><p className="listing-grower">Grown by <b>{listing.grower}</b> <span>· {listing.location}</span></p>
        {section.id==="trade"?<p className="listing-note">{listing.lookingFor?<>Hoping to find: <b>{listing.lookingFor}</b></>:listing.isMine?"Open to a friendly swap":"Open to trade"}</p>:section.id==="donate"?<p className="listing-note">{listing.note||"Shared with the community"}</p>:null}
      </div>
    </article>})}</div>:<div className="market-empty"><span>🌿</span><p>No {section.title.toLowerCase()} listings for “{query}” yet.</p><small>Try another produce type.</small></div>}
  </section>;
}

function MyListings({ listings, onDeactivate, onRemove }) {
  return <section className="card market-section my-listings" id="my-listings">
    <div className="section-heading"><span className="section-icon">📦</span><div><p className="eyebrow">YOUR SHARED HARVEST</p><h2>My listings</h2></div><span className="listing-count">{listings.length} {listings.length===1?"item":"items"}</span></div>
    <p className="section-intro">Manage the produce you have offered to the community.</p>
    {listings.length?<div className="my-listing-list">{listings.slice().reverse().map(listing=><article className={`my-listing ${listing.active?"":"is-inactive"}`} key={listing.id}>
      <img src={`/thumbs/${listing.img||thumbnailFor(listing.plant_type)}`} alt="" onError={event=>{event.currentTarget.src="/thumbs/default.svg";event.currentTarget.onerror=null;}}/>
      <div className="my-listing-info"><b>{listing.plant_type} <span>· {listing.quantity}{listing.weight?` × ${listing.weight} ${listing.weight_unit||"lb"}`:""}</span></b><small>{sections.find(section=>section.id===listing.section)?.title}{listing.asking_price!=null&&Number.isFinite(Number(listing.asking_price))?` · $${Number(listing.asking_price).toFixed(2)} asking`:""} · {listing.active?"On the marketplace":"No longer listed"}</small></div>
      <div className="my-listing-actions">{listing.active&&<button className="secondary-button" onClick={()=>onDeactivate(listing.id)}>Mark as no longer listed</button>}<button className="remove-listing-button" onClick={()=>onRemove(listing.id)}>Remove</button></div>
    </article>)}</div>:<div className="market-empty"><span>🧺</span><p>You have not listed any produce yet.</p><small>Choose a few things from your harvest inventory to get started.</small></div>}
  </section>;
}

export default function Marketplace({ onBack, inventoryItems=[] }) {
  const [ownListings,setOwnListings]=useState([]);
  const [showListingForm,setShowListingForm]=useState(false);
  const [listingSection,setListingSection]=useState("buy");
  const [selectedItems,setSelectedItems]=useState({});
  const [error,setError]=useState("");
  const [notice,setNotice]=useState("");
  const [selectedPurchaseIds,setSelectedPurchaseIds]=useState([]);
  const [purchasedListingIds,setPurchasedListingIds]=useState(()=>{
    try { return new Set(JSON.parse(localStorage.getItem("spacefruit-market-purchases")||"[]")); }
    catch { return new Set(); }
  });
  const [showPurchaseConfirmation,setShowPurchaseConfirmation]=useState(false);

  async function refreshListings() {
    try {
      const response=await fetch("/api/marketplace/listings?_ts="+Date.now(),{cache:"no-store"});
      const data=await response.json();
      if(!response.ok) throw new Error(data.error||"Could not load your marketplace listings.");
      setOwnListings(data.listings||[]);
    } catch (exception) { setError(exception.message); }
  }

  useEffect(()=>{refreshListings();},[]);

  function remainingFor(item) {
    const reserved=ownListings.filter(listing=>listing.active&&listing.plant_type===item.plant_type).reduce((total,listing)=>total+listing.quantity,0);
    return Math.max(0,item.quantity-reserved);
  }

  function toggleSelectedItem(plantType,checked) {
    setSelectedItems(current=>{
      if(checked) return {...current,[plantType]:{quantity:1,weight:"",weight_unit:"lb",asking_price:""}};
      const next={...current};
      delete next[plantType];
      return next;
    });
  }

  function updateSelectedItem(plantType,field,value) {
    setSelectedItems(current=>({...current,[plantType]:{...current[plantType], [field]:value}}));
  }

  async function acceptListings(event) {
    event.preventDefault();
    const items=Object.entries(selectedItems).filter(([,details])=>Number(details.quantity)>0).map(([plant_type,details])=>({plant_type,quantity:Number(details.quantity),weight:Number(details.weight),weight_unit:details.weight_unit,asking_price:listingSection==="buy"?Number(details.asking_price):null}));
    setError("");
    try {
      const response=await fetch("/api/marketplace/listings",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({section:listingSection,items})});
      const data=await response.json();
      if(!response.ok) throw new Error(data.error||"Could not list the selected produce.");
      setOwnListings(current=>[...current,...(data.listings||[])]);
      setNotice(`${items.length} ${items.length===1?"item":"items"} added to your ${sections.find(section=>section.id===listingSection)?.title} listings.`);
      setSelectedItems({});
      setShowListingForm(false);
    } catch (exception) { setError(exception.message); }
  }

  async function updateListing(id,action) {
    setError("");
    try {
      const response=await fetch(`/api/marketplace/listings/${id}`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({action})});
      const data=await response.json();
      if(!response.ok) throw new Error(data.error||"Could not update this listing.");
      if(action==="remove") setOwnListings(current=>current.filter(listing=>listing.id!==id));
      else setOwnListings(current=>current.map(listing=>listing.id===id?{...listing,active:false}:listing));
      setNotice(action==="remove"?"Listing removed.":"Listing is no longer on the marketplace.");
    } catch (exception) { setError(exception.message); }
  }

  const listableItems=inventoryItems.filter(item=>remainingFor(item)>0);
  const selectedCount=Object.values(selectedItems).filter(details=>Number(details.quantity)>0).length;
  const selectedPurchaseListings=otherGrowersListings.buy.filter(listing=>selectedPurchaseIds.includes(listing.id));

  function togglePurchase(id) {
    setSelectedPurchaseIds(current=>current.includes(id)?current.filter(itemId=>itemId!==id):[...current,id]);
  }

  function confirmPurchase() {
    if(!selectedPurchaseListings.length) return;
    const updatedPurchases=new Set([...purchasedListingIds,...selectedPurchaseListings.map(listing=>listing.id)]);
    localStorage.setItem("spacefruit-market-purchases",JSON.stringify([...updatedPurchases]));
    setPurchasedListingIds(updatedPurchases);
    setNotice(`Purchase confirmed for ${selectedPurchaseListings.map(listing=>listing.produce).join(", ")}.`);
    setSelectedPurchaseIds([]);
    setShowPurchaseConfirmation(false);
  }

  return <>
    <header className="app-header market-header"><div className="brand-lockup"><div className="brand-mark" aria-hidden="true">✦</div><div><span className="brand-kicker">GROW A LITTLE CLOSER</span><h1>Garden Marketplace</h1></div></div><div className="market-header-actions"><button className="marketplace-button list-produce-button" onClick={()=>{setError("");setNotice("");setShowListingForm(true);}}>＋ List produce</button><button className="marketplace-button back-to-garden" onClick={onBack}><span aria-hidden="true">←</span> Back to garden</button></div></header>
    <section className="garden-hero market-hero"><div className="hero-copy"><p className="eyebrow">GOOD THINGS GROW BETTER TOGETHER</p><h2>From one garden to another</h2><p className="hero-message">Trade, find, or share a fresh harvest with your neighborhood growers.</p></div><div className="market-hero-art" aria-hidden="true">🧺<span>✧</span></div></section>
    <nav className="market-tabs" aria-label="Marketplace sections">{sections.map(section=><a key={section.id} href={`#market-${section.id}`}>{section.icon} {section.title}</a>)}<a href="#my-listings">📦 My listings</a></nav>
    <div className="market-note"><span aria-hidden="true">✦</span> Community board <b>·</b> Sample listings from other local growers</div>
    {error&&<div className="error market-feedback" role="alert">{error}</div>}{notice&&<div className="market-success" role="status">{notice}</div>}
    <MyListings listings={ownListings} onDeactivate={id=>updateListing(id,"deactivate")} onRemove={id=>updateListing(id,"remove")}/>
    {sections.map(section=><MarketSection key={section.id} section={section} ownListings={ownListings} selectedPurchaseIds={selectedPurchaseIds} purchasedListingIds={purchasedListingIds} onTogglePurchase={togglePurchase} onConfirmPurchase={()=>setShowPurchaseConfirmation(true)}/>)}

    {showPurchaseConfirmation&&<div className="modal-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)setShowPurchaseConfirmation(false);}}><section className="replant-modal purchase-confirmation" role="dialog" aria-modal="true" aria-labelledby="purchase-confirm-title"><button type="button" className="close-listing-modal" aria-label="Close" onClick={()=>setShowPurchaseConfirmation(false)}>×</button><p className="eyebrow">FRESH FROM THE NEIGHBORHOOD</p><h2 id="purchase-confirm-title">Confirm your purchase</h2><p className="section-intro">Review the produce you selected before confirming.</p><ul>{selectedPurchaseListings.map(listing=><li key={listing.id}><b>{listing.produce}</b><span>{listing.quantity} · {listing.price}</span><small>From {listing.grower}</small></li>)}</ul><div className="modal-actions"><button type="button" onClick={()=>setShowPurchaseConfirmation(false)}>Keep browsing</button><button type="button" className="primary-button" disabled={!selectedPurchaseListings.length} onClick={confirmPurchase}>Confirm purchase</button></div></section></div>}

    {showListingForm&&<div className="modal-backdrop" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)setShowListingForm(false);}}>
      <section className="replant-modal listing-modal" role="dialog" aria-modal="true" aria-labelledby="list-produce-title">
        <button type="button" className="close-listing-modal" aria-label="Close" onClick={()=>setShowListingForm(false)}>×</button>
        <p className="eyebrow">SHARE FROM YOUR HARVEST</p><h2 id="list-produce-title">Add produce to the marketplace</h2>
        <form onSubmit={acceptListings}>
          <label className="listing-section-select">Marketplace section<select value={listingSection} onChange={event=>setListingSection(event.target.value)}>{sections.map(section=><option value={section.id} key={section.id}>{section.title}</option>)}</select></label>
          <fieldset className="inventory-checklist"><legend>Select items from your harvest inventory</legend>
            {listableItems.length?listableItems.map(item=>{
              const remaining=remainingFor(item);
              const details=selectedItems[item.plant_type];
              const checked=!!details;
              return <div className={`inventory-check-row ${checked?"selected":""}`} key={item.plant_type}>
                <label className="inventory-check-plant"><input type="checkbox" checked={checked} onChange={event=>toggleSelectedItem(item.plant_type,event.target.checked)}/><img src={`/thumbs/${item.img||thumbnailFor(item.plant_type)}`} alt="" onError={event=>{event.currentTarget.src="/thumbs/default.svg";event.currentTarget.onerror=null;}}/><span className="inventory-check-name"><b>{item.plant_type}</b><small>{remaining} available</small></span></label>
                <label className="listing-field"><span>Quantity</span><input type="number" aria-label={`Quantity of ${item.plant_type} to list`} min="1" max={remaining} value={details?.quantity??1} disabled={!checked} required={checked} onChange={event=>updateSelectedItem(item.plant_type,"quantity",Math.min(remaining,Math.max(1,Number(event.target.value)||1)))}/></label>
                <label className="listing-field"><span>Weight each</span><span className="weight-entry"><input type="number" aria-label={`Weight of each ${item.plant_type}`} min="0.01" step="0.01" value={details?.weight??""} placeholder="0.0" disabled={!checked} required={checked} onChange={event=>updateSelectedItem(item.plant_type,"weight",event.target.value)}/><select aria-label={`Weight unit for ${item.plant_type}`} value={details?.weight_unit||"lb"} disabled={!checked} onChange={event=>updateSelectedItem(item.plant_type,"weight_unit",event.target.value)}><option value="lb">lb</option><option value="oz">oz</option><option value="kg">kg</option><option value="g">g</option></select></span></label>
                {listingSection==="buy"&&<label className="listing-field"><span>Asking price each</span><span className="price-entry"><span>$</span><input type="number" aria-label={`Asking price for ${item.plant_type}`} min="0.01" step="0.01" value={details?.asking_price??""} placeholder="0.00" disabled={!checked} required={checked} onChange={event=>updateSelectedItem(item.plant_type,"asking_price",event.target.value)}/></span></label>}
              </div>;
            }):<p className="empty-inventory-note">Your harvest inventory has no unlisted produce available right now.</p>}
          </fieldset>
          <div className="modal-actions"><button type="button" onClick={()=>setShowListingForm(false)}>Cancel</button><button className="primary-button" type="submit" disabled={!selectedCount||!listableItems.length}>Accept and list {selectedCount?`${selectedCount} ${selectedCount===1?"item":"items"}`:"selected items"}</button></div>
        </form>
      </section>
    </div>}
  </>;
}
