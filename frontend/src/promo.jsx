import { createRoot } from "react-dom/client";
import "./promo.css";

function Brand({ light = false }) {
  return <a className={`promo-brand${light ? " promo-brand-light" : ""}`} href="/promo.html" aria-label="SpaceFruit home">
    <span className="promo-brand-mark" aria-hidden="true">✦</span>
    <span><small>YOUR LITTLE PATCH IN SPACE</small><b>SpaceFruit</b></span>
  </a>;
}

function RobotIllustration() {
  return <div className="robot-scene" aria-label="Illustration of the SpaceFruit garden robot">
    <span className="scene-star star-one">✦</span><span className="scene-star star-two">✧</span>
    <span className="scene-orbit orbit-one"/><span className="scene-orbit orbit-two"/>
    <span className="scene-leaf leaf-one">❋</span><span className="scene-leaf leaf-two">❋</span>
    <div className="little-robot"><div className="robot-camera"><i/><i/></div><div className="robot-shell"><span className="robot-eye"/><span className="robot-eye"/><span className="robot-smile"/><span className="robot-badge">✦</span></div><div className="robot-bumper"/><div className="robot-wheel wheel-left"/><div className="robot-wheel wheel-right"/><span className="robot-arm arm-left"/><span className="robot-arm arm-right"/></div>
    <span className="scene-plant plant-one">🌱</span><span className="scene-plant plant-two">🌿</span>
    <div className="scene-caption"><span className="caption-dot"/>GARDEN HELPER · READY TO GROW</div>
  </div>;
}

function Promo() {
  return <main className="promo-page">
    <header className="promo-nav"><Brand/><nav aria-label="Main navigation"><a href="#how-it-helps">How it helps</a><a href="#demo">Video demo</a><a className="nav-app-link" href="/">Open the garden app <span aria-hidden="true">↗</span></a></nav></header>
    <section className="promo-hero">
      <div className="hero-text"><p className="promo-eyebrow"><span>✧</span> SMALL ROBOT, BIG GARDEN ENERGY</p><h1>A little help for everything <em>growing.</em></h1><p className="hero-lede">Meet SpaceFruit: a friendly garden robot concept made to help plant seeds, keep an eye on growing things, and bring in the harvest.</p><div className="hero-buttons"><a className="button-primary" href="#how-it-helps">Meet your garden helper <span aria-hidden="true">↓</span></a><a className="button-soft" href="#demo">See the video space</a></div><div className="hero-note"><span>✦</span> Thoughtful garden care, one little plot at a time.</div></div>
      <RobotIllustration/>
    </section>
    <section className="promise-strip" aria-label="Robot capabilities"><span><b>01</b> Plant</span><i/><span><b>02</b> Tend</span><i/><span><b>03</b> Harvest</span><i/><span><b>04</b> Share</span></section>
    <section className="help-section" id="how-it-helps"><div className="section-intro"><p className="promo-eyebrow">A GARDEN SIDEKICK</p><h2>From first seed to full basket.</h2><p>SpaceFruit brings the everyday garden jobs into one calm, easy-to-follow experience.</p></div>
      <div className="feature-grid">
        <article className="feature-card feature-plant"><span className="feature-icon">🌱</span><p className="feature-number">01 · GET GROWING</p><h3>Plant with a plan</h3><p>Choose what goes in each plot and follow the planting progress as your robot gets seeds in the ground.</p><span className="feature-decoration">✦</span></article>
        <article className="feature-card feature-care"><span className="feature-icon">🔎</span><p className="feature-number">02 · KEEP WATCH</p><h3>A little daily care</h3><p>Track garden checkups, weeding progress, and camera-detected plant health alerts from one friendly dashboard.</p><span className="feature-decoration">❋</span></article>
        <article className="feature-card feature-harvest"><span className="feature-icon">🧺</span><p className="feature-number">03 · GATHER GOOD THINGS</p><h3>Harvest and share</h3><p>Check if a plant is ready, collect the harvest, and keep a growing record of what your garden gives back.</p><span className="feature-decoration">✧</span></article>
      </div>
    </section>
    <section className="demo-section" id="demo"><div className="demo-heading"><div><p className="promo-eyebrow">A PEEK AT SPACEFRUIT</p><h2>See the little helper in action.</h2></div><span className="demo-tag"><i/> VIDEO DEMO</span></div>
      {/* Replace this accessible placeholder with the demo video embed when footage is ready. */}
      <div className="video-placeholder" role="img" aria-label="Reserved space for the SpaceFruit robot video demonstration"><div className="video-vine vine-left">❋</div><div className="video-vine vine-right">❋</div><div className="video-play" aria-hidden="true">▶</div><p>Our garden adventure is growing.</p><span>Space reserved for the SpaceFruit video demo</span><div className="video-progress"><i/></div><div className="video-controls"><span>▶</span><span>00:00</span><div/><span>◖))</span><span>⛶</span></div></div>
      <p className="demo-footnote"><span>✦</span> We’re making room for a closer look at the robot, its garden tools, and the app that keeps it all connected.</p>
    </section>
    <section className="closing-card"><div className="closing-spark">✧</div><p className="promo-eyebrow">COME ON IN</p><h2>Your garden’s next chapter starts small.</h2><p>Take a look around the SpaceFruit garden app and see what’s growing.</p><a className="button-primary" href="/">Visit the garden app <span aria-hidden="true">↗</span></a><div className="closing-stars" aria-hidden="true">✦　·　✧　·　✦</div></section>
    <footer className="promo-footer"><Brand/><span>Made with a little soil, a little starlight, and lots of care.</span><a href="#top" onClick={(event)=>{event.preventDefault();window.scrollTo({top:0,behavior:"smooth"});}}>Back to top ↑</a></footer>
  </main>;
}

createRoot(document.getElementById("root")).render(<Promo/>);
