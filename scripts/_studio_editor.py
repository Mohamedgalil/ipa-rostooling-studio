# -*- coding: utf-8 -*-
"""
_studio_editor.py -- the /ros-studio editor page as one raw-string template.

Kept separate from ros_studio.py only so that file stays readable. ros_studio.render_editor
injects three markers: /*__PALETTE_CSS__*/ (shared palette), /*__JS_PRIMITIVES__*/ (the
shared STUDIO helper library) and /*__DATA__*/null (the project + the three autocomplete
datasets). The page has no network access; the only non-local reference is the SVG namespace
URI used by the shared primitives.
"""

EDITOR_TEMPLATE = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>/ros-studio — editor</title>
<style>
/*__PALETTE_CSS__*/
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);font-size:14px;-webkit-font-smoothing:antialiased;display:flex;flex-direction:column;overflow:hidden}
  button{font-family:inherit}
  .banner{background:var(--warn-wash);color:var(--warn);font-size:.76rem;padding:.35rem .8rem;text-align:center;border-bottom:1px solid var(--rule);font-family:var(--mono)}
  .banner b{color:var(--ink)}
  .banner.err{background:var(--dead-wash);color:var(--dead)}

  .topbar{display:flex;align-items:center;gap:.9rem;padding:.55rem .9rem;border-bottom:1px solid var(--rule);background:var(--surface);flex-shrink:0}
  .brand{font-family:var(--display);font-size:1.05rem;font-weight:600;letter-spacing:-.01em}
  .brand .sub{font-family:var(--mono);font-size:.66rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin-left:.5rem}
  .sysname{display:flex;align-items:center;gap:.4rem;font-size:.82rem;color:var(--ink-2)}
  .sysname input{font-family:var(--mono);font-size:.82rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:5px;padding:.2rem .45rem;color:var(--ink);width:16ch}
  .spacer{flex:1}
  .seg{display:inline-flex;border:1px solid var(--rule);border-radius:7px;overflow:hidden;background:var(--surface)}
  .seg button{font-size:.75rem;font-weight:600;color:var(--ink-2);background:transparent;border:none;border-right:1px solid var(--rule);padding:.34rem .6rem;cursor:pointer}
  .seg button:last-child{border-right:none}
  .seg button.on{background:var(--accent);color:#fff}
  .seg button:disabled{opacity:.38;cursor:default}
  .savestate{font-family:var(--mono);font-size:.66rem;color:var(--ink-3);white-space:nowrap}
  .savestate.warn{color:var(--warn)}
  .tbtn{font-size:.78rem;font-weight:600;color:var(--ink-2);background:var(--surface);border:1px solid var(--rule);border-radius:6px;padding:.4rem .7rem;cursor:pointer}
  .tbtn:hover{color:var(--ink);border-color:var(--ink-3)}
  .tbtn.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
  .tbtn.primary:hover{background:var(--accent-2)}

  .main{flex:1;display:flex;min-height:0}
  .rail{width:190px;flex-shrink:0;border-right:1px solid var(--rule);background:var(--surface);display:flex;flex-direction:column;gap:1rem;padding:.85rem;overflow-y:auto}
  .rail h4{margin:0 0 .35rem;font-family:var(--mono);font-size:.64rem;letter-spacing:.11em;text-transform:uppercase;color:var(--ink-3);font-weight:600}
  .rail .grp{display:flex;flex-direction:column;gap:.4rem}
  body.mode-view .editonly{display:none}
  .railbtn{display:flex;align-items:center;gap:.45rem;font-size:.8rem;font-weight:600;color:var(--ink);background:var(--surface-2);border:1px solid var(--rule);border-radius:6px;padding:.45rem .55rem;cursor:pointer;text-align:left}
  .railbtn:hover{border-color:var(--accent)}
  .railbtn .plus{color:var(--accent);font-weight:700}
  .filter label{display:flex;align-items:center;gap:.4rem;font-size:.76rem;color:var(--ink-2);padding:.12rem 0;cursor:pointer}
  .filter .sw{width:11px;height:11px;border-radius:3px;flex-shrink:0}
  .filter input{accent-color:var(--accent);width:13px;height:13px}
  .issues .row{display:flex;align-items:center;gap:.45rem;font-size:.78rem;padding:.2rem 0}
  .issues .cnt{font-family:var(--mono);font-weight:700}
  .issues .err{color:var(--dead)} .issues .wrn{color:var(--warn)} .issues .ok{color:var(--accent-2)}
  .issuelist{display:flex;flex-direction:column;gap:.3rem;margin-top:.3rem}
  .issuelist .it{font-size:.72rem;line-height:1.3;color:var(--ink-2);border-left:2px solid var(--warn);padding-left:.45rem}
  .issuelist .it.e{border-color:var(--dead)}

  /* The viewport clips and NOTHING scrolls natively: pan and zoom are one CSS transform on
     .canvas, so the SVG wire layer -- a child of the same element -- is carried by the exact
     same matrix as the node layer and an edge can never drift off its port. touch-action:none
     hands the browser's own pan/pinch gestures to the wheel/pointer handlers instead. */
  .canvas-wrap{flex:1;position:relative;overflow:hidden;min-width:0;touch-action:none}
  /* will-change:transform is set only WHILE panning/zooming, never at rest. Held permanently it
     promotes the layer to the GPU, and the browser then keeps rasterising the text once and
     scaling the bitmap -- every label goes soft the moment you zoom in. Dropping the hint at
     rest forces a re-raster at the current scale, which is what makes the text sharp again. */
  .canvas{position:relative;width:1600px;height:1100px;transform-origin:0 0;background-image:radial-gradient(circle,var(--rule-soft) 1px,transparent 1px);background-size:22px 22px}
  .canvas.moving{will-change:transform}
  /* Text is the thing being scaled, so hint the rasteriser to optimise for legibility over
     speed, and keep glyph geometry from being rounded to the device grid at fractional zoom. */
  .node{text-rendering:geometricPrecision;-webkit-font-smoothing:antialiased}
  /* the inline editor sits where the text was, so the card does not jump when it opens */
  .node input.inline{font:inherit;font-size:.8rem;padding:.05em .25em;border:1px solid var(--accent);
    border-radius:3px;background:var(--surface);color:var(--ink);min-width:60px;max-width:22ch}
  .canvas-wrap.panning{cursor:grabbing}
  .canvas-wrap.dropping{outline:2px dashed var(--accent);outline-offset:-6px}
  /* floating over the transformed layer, so they keep their size at every zoom level */
  .findbar,.viewbar{position:absolute;z-index:6;display:flex;align-items:center;gap:.3rem;background:var(--surface);border:1px solid var(--rule);border-radius:8px;box-shadow:var(--shadow);padding:.3rem .35rem}
  .findbar{top:.6rem;left:.6rem}
  .viewbar{bottom:.6rem;left:.6rem}
  .findbar input{font-family:var(--mono);font-size:.74rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:5px;padding:.22rem .4rem;color:var(--ink);width:15ch}
  .findbar .fcount{font-family:var(--mono);font-size:.64rem;color:var(--ink-3);min-width:4.2em;text-align:center}
  .cbtn{font-family:var(--mono);font-size:.68rem;font-weight:600;color:var(--ink-2);background:var(--surface-2);border:1px solid var(--rule);border-radius:5px;padding:.2rem .42rem;cursor:pointer}
  .cbtn:hover{color:var(--ink);border-color:var(--accent)}
  .cbtn:disabled{opacity:.35;cursor:default}
  .viewbar .tgl{display:flex;align-items:center;gap:.25rem;cursor:pointer;user-select:none}
  .viewbar .tgl input{margin:0}
  .viewbar .zlvl{font-family:var(--mono);font-size:.66rem;color:var(--ink-3);min-width:3.6em;text-align:center}
  /* a find narrows the canvas rather than filtering it: a non-match stays visible (its edges
     are the reason you were looking) but recedes, so the hits read at a glance. */
  .node.fdim{opacity:.28}
  .node.fhit{border-color:var(--warn)}
  .node.fcur{border-color:var(--warn);box-shadow:0 0 0 3px var(--warn-wash),var(--shadow-lift)}
  .canvas svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1}
  .node{position:absolute;z-index:2;background:var(--surface);border:1.5px solid var(--rule);border-radius:9px;box-shadow:var(--shadow);min-width:190px;user-select:none}
  .node.sel{border-color:var(--accent);box-shadow:var(--shadow-lift)}
  .node.cat{border-style:dashed}
  /* a subSystems: node is not declared by THIS file -- dimmed and dotted so it reads as
     borrowed, and it is read-only everywhere in the inspector. */
  .node.sub{border-style:dotted;opacity:.9}
  .node.hasdiag{border-color:var(--dead)}
  .node .nhead{display:flex;align-items:center;gap:.4rem;padding:.45rem .6rem;border-bottom:1px solid var(--rule-soft);cursor:grab}
  .node .nhead:active{cursor:grabbing}
  .node .ntitle{font-weight:650;font-size:.84rem}
  .node .nfrom{font-family:var(--mono);font-size:.63rem;color:var(--ink-3);padding:.25rem .6rem 0}
  .node .badge{font-family:var(--mono);font-size:.56rem;letter-spacing:.04em;text-transform:uppercase;padding:.06em .4em;border-radius:3px;background:var(--surface-2);color:var(--ink-3)}
  .node .badge.cat{background:var(--accent-wash);color:var(--accent-2)}
  .node .diagflag{font-size:.62rem;color:var(--dead);font-family:var(--mono);padding:.1rem .6rem .3rem}
  .ifaces{padding:.35rem .1rem .5rem}
  .iface{position:relative;display:flex;align-items:center;gap:.4rem;padding:.13rem .6rem;font-size:.75rem}
  .iface .kd{font-family:var(--mono);font-size:.56rem;font-weight:700;text-transform:uppercase;width:2.2em;text-align:center;border-radius:3px;padding:.05em 0;color:#fff}
  .iface .inm{font-weight:600}
  .iface .ity{font-family:var(--mono);font-size:.63rem;color:var(--ink-3);margin-left:auto;max-width:12ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .kd.pub{background:var(--k-pub)} .kd.sub{background:var(--k-sub)} .kd.ss{background:var(--k-ss)}
  .kd.sc{background:var(--k-sc)} .kd.as{background:var(--k-as)} .kd.ac{background:var(--k-ac)}
  .port{position:absolute;top:50%;width:12px;height:12px;border-radius:50%;border:2px solid var(--surface);transform:translateY(-50%);cursor:crosshair;z-index:3}
  .port.src{right:-6px} .port.snk{left:-6px}
  /* Auto side placement overrides the kind default. A port on the bottom edge sits under the
     row it belongs to, so which interface an edge lands on is still readable. */
  .port.side-l{left:-6px;right:auto} .port.side-r{right:-6px;left:auto}
  .port.side-b{top:auto;bottom:-6px;left:50%;right:auto;transform:translateX(-50%)}
  .port.side-b.legal{transform:translateX(-50%) scale(1.25)}
  .port.pub{background:var(--k-pub)} .port.sub{background:var(--k-sub)} .port.ss{background:var(--k-ss)}
  .port.sc{background:var(--k-sc)} .port.as{background:var(--k-as)} .port.ac{background:var(--k-ac)}
  .port.legal{box-shadow:0 0 0 4px color-mix(in srgb,var(--glow) 55%,transparent);transform:translateY(-50%) scale(1.25)}
  .port.illegal{opacity:.2}
  .iface[data-hidden="1"]{display:none}
  /* read-only detail levels */
  body.mode-view .port{pointer-events:none}
  .canvas.lvl1 .ifaces{display:none}
  .canvas.lvl2 .iface .ity{display:none}
  .canvas.deps .node .ifaces{display:none}
  .pkgbox{position:absolute;z-index:2;background:var(--surface-2);border:1.5px solid var(--ink-3);border-radius:9px;padding:.5rem .6rem;min-width:150px;font-size:.78rem}
  .pkgbox.res{border-color:var(--accent-2)}
  .pkgbox.unres{border-color:var(--warn)}
  .pkgbox .pt{font-weight:650}
  .pkgbox .ps{font-family:var(--mono);font-size:.62rem;color:var(--ink-3);margin-top:.15rem}

  path.edge{fill:none;stroke:var(--edge);stroke-width:1.7;transition:stroke .12s,opacity .12s}
  path.edge.topic{marker-end:url(#ah)}
  path.edge.rr{marker-end:url(#ah);marker-start:url(#ahOpen)}
  path.edge.sel{stroke:var(--edge-hot);stroke-width:2.4}
  path.rubber{stroke:var(--edge-hot);stroke-width:2;stroke-dasharray:5 4;fill:none}

  .inspector{width:298px;flex-shrink:0;border-left:1px solid var(--rule);background:var(--surface);overflow-y:auto;padding:.85rem}
  .inspector.empty{display:flex;align-items:center;justify-content:center;color:var(--ink-3);font-size:.82rem;text-align:center;padding:2rem}
  .insec{margin-bottom:1rem}
  .insec h4{margin:0 0 .5rem;font-family:var(--mono);font-size:.64rem;letter-spacing:.11em;text-transform:uppercase;color:var(--ink-3);border-top:1px solid var(--rule-soft);padding-top:.6rem}
  .insec:first-child h4{border-top:none;padding-top:0}
  .fld{display:flex;flex-direction:column;gap:.2rem;margin-bottom:.5rem}
  .fld label{font-size:.7rem;color:var(--ink-3)}
  .fld input,.fld select{font-family:var(--mono);font-size:.76rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:5px;padding:.3rem .4rem;color:var(--ink);width:100%}
  .fld .derived{font-family:var(--mono);font-size:.72rem;color:var(--ink-3);background:var(--surface-2);border:1px dashed var(--rule);border-radius:5px;padding:.3rem .4rem;word-break:break-all}
  .radio{display:flex;gap:.5rem;font-size:.76rem}
  .radio label{display:flex;align-items:center;gap:.3rem;cursor:pointer}
  .iedit{display:flex;align-items:center;gap:.4rem;font-size:.74rem;padding:.28rem .35rem;border:1px solid var(--rule-soft);border-radius:5px;margin-bottom:.3rem;background:var(--surface-2)}
  .iedit .kd{cursor:pointer;width:2.2em;text-align:center;border-radius:3px;color:#fff;font-family:var(--mono);font-size:.56rem;font-weight:700;text-transform:uppercase;padding:.1em 0}
  .iedit .grow{flex:1;min-width:0}
  .iedit .inm2{font-weight:600}
  .iedit .ity2{font-family:var(--mono);font-size:.62rem;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .iedit .del{cursor:pointer;color:var(--ink-3);font-weight:700}
  .iedit .del:hover{color:var(--dead)}
  .iedit .lblrow{display:flex;align-items:center;gap:.35rem;margin-top:.2rem}
  .iedit .ilbl{flex:1;min-width:0;font-family:var(--mono);font-size:.62rem;padding:.12rem .3rem;border:1px solid var(--rule);border-radius:3px;background:var(--surface);color:var(--ink)}
  .iedit .expchk{display:flex;align-items:center;gap:.2rem;font-size:.6rem;color:var(--ink-3);white-space:nowrap;cursor:pointer}
  .iedit .expchk input{margin:0}
  .iedit.orphan{border-color:var(--dead);background:var(--dead-wash)}
  .iedit .qtog{cursor:pointer;font-family:var(--mono);font-size:.56rem;font-weight:700;text-transform:uppercase;color:var(--ink-3);border:1px solid var(--rule);border-radius:3px;padding:.1em .3em;white-space:nowrap}
  .iedit .qtog.set{color:var(--accent-2);border-color:var(--accent);background:var(--accent-wash)}
  .qosbox{margin:-.1rem 0 .35rem;padding:.4rem .45rem;border:1px solid var(--rule);border-top:none;border-radius:0 0 5px 5px;background:var(--surface)}
  .qosbox .qrow{display:flex;align-items:center;gap:.35rem;margin-bottom:.18rem}
  .qosbox .qrow label{flex:0 0 6.6em;font-family:var(--mono);font-size:.62rem;color:var(--ink-3)}
  .qosbox .qrow select,.qosbox .qrow input{flex:1;min-width:0;font-family:var(--mono);font-size:.66rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:4px;padding:.15rem .25rem;color:var(--ink)}
  .qosbox .qnote{font-size:.6rem;line-height:1.35;margin:0 0 .3rem 6.95em;color:var(--ink-3)}
  .qosbox .qnote.i{color:var(--ink-3)} .qosbox .qnote.w{color:var(--warn)} .qosbox .qnote.e{color:var(--dead);font-weight:600}
  .qosbox .qnote:empty{display:none}
  .iedit .ctog{cursor:pointer;font-family:var(--mono);font-size:.56rem;font-weight:700;text-transform:uppercase;color:var(--ink-3);border:1px solid var(--rule);border-radius:3px;padding:.1em .3em;white-space:nowrap}
  .iedit .ctog.set{color:var(--accent-2);border-color:var(--accent);background:var(--accent-wash)}
  .cmtbox{margin:-.1rem 0 .35rem;padding:.4rem .45rem;border:1px solid var(--rule);border-top:none;border-radius:0 0 5px 5px;background:var(--surface)}
  .cmtbox .crow{display:flex;flex-direction:column;gap:.12rem;margin-bottom:.3rem}
  .cmtbox .crow label{font-size:.6rem;color:var(--ink-3)}
  .cmtbox .crow input,.cmtbox .crow textarea{width:100%;font-family:var(--mono);font-size:.66rem;line-height:1.4;background:var(--surface-2);border:1px solid var(--rule);border-radius:4px;padding:.15rem .25rem;color:var(--ink);resize:vertical}
  .syspanel .pkgrow{margin-bottom:.5rem}
  .syspanel .pkgrow .pn{font-family:var(--mono);font-size:.7rem;font-weight:600;margin-bottom:.15rem}
  .syspanel .frow{display:flex;align-items:center;gap:.3rem;margin-bottom:.15rem}
  .syspanel .frow input{flex:1;min-width:0;font-family:var(--mono);font-size:.68rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:4px;padding:.15rem .25rem;color:var(--ink)}
  .syspanel .frow button{flex:0 0 auto;font-family:var(--mono);font-size:.58rem;color:var(--ink-3);background:var(--surface);border:1px solid var(--rule);border-radius:4px;padding:.18rem .35rem;cursor:pointer}
  .syspanel .fnote{font-size:.6rem;line-height:1.35;margin:0 0 .28rem .2rem;color:var(--ink-3)}
  .syspanel .fnote.w{color:var(--warn)} .syspanel .fnote.e{color:var(--dead);font-weight:600}
  .syspanel .fnote:empty{display:none}
  .hint{font-size:.66rem;line-height:1.4;color:var(--ink-3);margin-top:.15rem}
  .hint.w{color:var(--warn)}
  .addform{display:flex;flex-direction:column;gap:.35rem;padding:.5rem;border:1px dashed var(--rule);border-radius:6px;margin-top:.35rem}
  .kseg{display:flex;gap:2px}
  .kseg button{flex:1;font-family:var(--mono);font-size:.6rem;font-weight:700;text-transform:uppercase;padding:.28rem 0;border:1px solid var(--rule);background:var(--surface);color:var(--ink-3);cursor:pointer;border-radius:4px}
  .kseg button.on{color:#fff}
  .kseg button.on[data-k=pub]{background:var(--k-pub);border-color:var(--k-pub)}
  .kseg button.on[data-k=sub]{background:var(--k-sub);border-color:var(--k-sub)}
  .kseg button.on[data-k=ss]{background:var(--k-ss);border-color:var(--k-ss)}
  .kseg button.on[data-k=sc]{background:var(--k-sc);border-color:var(--k-sc)}
  .kseg button.on[data-k=as]{background:var(--k-as);border-color:var(--k-as)}
  .kseg button.on[data-k=ac]{background:var(--k-ac);border-color:var(--k-ac)}
  .minibtn{font-size:.72rem;font-weight:600;color:var(--accent-2);background:var(--accent-wash);border:1px solid var(--accent);border-radius:5px;padding:.32rem .5rem;cursor:pointer}
  .typestate{font-size:.66rem;margin-top:.15rem}
  .typestate.ok{color:var(--accent-2)} .typestate.warn{color:var(--warn)}
  .delnode{width:100%;font-size:.75rem;color:var(--dead);background:var(--dead-wash);border:1px solid var(--dead);border-radius:5px;padding:.35rem;cursor:pointer;margin-top:.3rem}
  .roinfo{font-size:.72rem;color:var(--ink-3);font-family:var(--mono);line-height:1.5}

  .scrim{position:fixed;inset:0;background:rgba(0,0,0,.42);display:none;align-items:center;justify-content:center;z-index:50}
  .scrim.on{display:flex}
  .modal{background:var(--surface);border:1px solid var(--rule);border-radius:11px;box-shadow:var(--shadow-lift);width:min(720px,92vw);max-height:86vh;display:flex;flex-direction:column;overflow:hidden}
  .modal h3{margin:0;padding:.8rem 1rem;font-family:var(--display);font-size:1.1rem;border-bottom:1px solid var(--rule);display:flex;align-items:center;gap:.5rem}
  .modal .close{margin-left:auto;cursor:pointer;color:var(--ink-3);font-size:1.1rem;background:none;border:none}
  .modal .body{padding:1rem;overflow-y:auto}
  .catsearch{width:100%;font-family:var(--mono);font-size:.82rem;padding:.45rem .6rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:6px;color:var(--ink);margin-bottom:.7rem}
  .catrow{display:flex;align-items:center;gap:.6rem;padding:.5rem .55rem;border:1px solid var(--rule-soft);border-radius:7px;margin-bottom:.4rem}
  .catrow .cinfo{flex:1;min-width:0}
  .catrow .ckey{font-family:var(--mono);font-size:.8rem;font-weight:600}
  .catrow .cif{font-family:var(--mono);font-size:.66rem;color:var(--ink-3);margin-top:.15rem}
  .catrow .cfile{font-family:var(--mono);font-size:.6rem;color:var(--ink-3)}
  .tabs{display:flex;gap:.3rem;margin-bottom:.6rem;flex-wrap:wrap}
  .tabs button{font-family:var(--mono);font-size:.72rem;padding:.3rem .6rem;border:1px solid var(--rule);background:var(--surface-2);border-radius:5px;cursor:pointer;color:var(--ink-2)}
  .tabs button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
  pre.gen{font-family:var(--mono);font-size:.74rem;line-height:1.5;background:var(--surface-2);border:1px solid var(--rule);border-radius:7px;padding:.7rem .8rem;overflow-x:auto;margin:0;white-space:pre;color:var(--ink)}
  textarea.copybox{width:100%;height:160px;font-family:var(--mono);font-size:.7rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:7px;color:var(--ink);padding:.6rem;margin-top:.6rem}
  .gennote{font-size:.72rem;color:var(--warn);background:var(--warn-wash);border-radius:5px;padding:.4rem .55rem;margin-bottom:.6rem;font-family:var(--mono)}
  .modalbtns{display:flex;gap:.5rem;margin-top:.7rem;flex-wrap:wrap}
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body class="mode-edit">
<div class="banner" id="banner">/ros-studio — author in the browser, then <b>Commit</b> to generate &amp; validate in the Python companion.</div>

<div class="topbar">
  <div class="brand">RosTooling <span class="sub">/ros-studio</span></div>
  <div class="sysname">system <input id="sysname" value=""></div>
  <div class="seg" id="modeSeg">
    <button data-mode="view">View</button><button data-mode="edit" class="on">Edit</button>
  </div>
  <div class="seg" id="levelSeg" style="display:none">
    <button data-lvl="1">System</button><button data-lvl="2">Interfaces</button><button data-lvl="3" class="on">Full</button><button data-lvl="4">Deps</button>
  </div>
  <div class="seg editonly" id="histSeg">
    <button id="undoBtn" title="Undo (Ctrl+Z)" disabled>&#8630; Undo</button><button id="redoBtn" title="Redo (Ctrl+Shift+Z / Ctrl+Y)" disabled>&#8631; Redo</button>
  </div>
  <div class="spacer"></div>
  <span class="savestate" id="saveState"></span>
  <button class="tbtn" id="reset">Reset layout</button>
  <button class="tbtn" id="theme">&#9680; Theme</button>
  <button class="tbtn" id="openBtn" title="Open a project.json, or a .rossystem with its .ros2/.ros files (several at once). You can also drag them onto the canvas.">&#8679; Open</button>
  <input type="file" id="openInput" multiple accept=".rossystem,.ros2,.ros,.json" style="display:none">
  <button class="tbtn primary" id="commit">&#8681; Commit</button>
</div>

<div class="main">
  <aside class="rail">
    <div class="grp editonly">
      <h4>Add</h4>
      <button class="railbtn" id="addNode"><span class="plus">+</span> Node (hand-authored)</button>
      <button class="railbtn" id="addCat"><span class="plus">+</span> From catalogue&hellip;</button>
    </div>
    <div class="grp filter">
      <h4>Show kinds</h4>
      <div id="filterBox"></div>
    </div>
    <div class="grp issues">
      <h4>Issues</h4>
      <div class="row"><span class="cnt err" id="errCnt">0</span> errors &nbsp; <span class="cnt wrn" id="wrnCnt">0</span> warnings</div>
      <div class="issuelist" id="issueList"></div>
    </div>
    <div class="grp" style="margin-top:auto">
      <h4>Legend</h4>
      <div id="legend" style="display:flex;flex-direction:column;gap:.2rem;font-size:.72rem;color:var(--ink-2)"></div>
    </div>
  </aside>

  <div class="canvas-wrap" id="canvasWrap">
    <div class="canvas lvl3" id="canvas">
      <svg id="wires"></svg>
    </div>
    <div class="findbar">
      <input id="findBox" placeholder="find a node&hellip;" spellcheck="false"
             title="matches the node label, its package.node, its namespace, and any interface name or type">
      <span class="fcount" id="findCount"></span>
      <button class="cbtn" id="findPrev" title="previous match (Shift+Enter)" disabled>&#8593;</button>
      <button class="cbtn" id="findNext" title="next match (Enter)" disabled>&#8595;</button>
    </div>
    <div class="viewbar">
      <button class="cbtn editonly" id="autoLayout" title="Arrange in layers that follow the connection direction">Auto layout</button>
      <label class="cbtn tgl" id="autoSidesWrap" title="Put each connected port on the edge facing its partner (left, right or bottom) instead of the fixed kind side, so wires stop crossing the card">
        <input type="checkbox" id="autoSides"> auto sides</label>
      <button class="cbtn" id="zFit" title="Fit to content (F)">Fit</button>
      <button class="cbtn" id="zOut" title="Zoom out (&minus;). Ctrl/&#8984;+wheel zooms at the pointer; plain wheel pans.">&minus;</button>
      <span class="zlvl" id="zLvl">100%</span>
      <button class="cbtn" id="zIn" title="Zoom in (+)">+</button>
      <button class="cbtn" id="zOne" title="Actual size (0)">100%</button>
    </div>
  </div>

  <aside class="inspector empty" id="inspector">Select a node to edit it, or add one from the rail.</aside>
</div>

<datalist id="typelist"></datalist>
<datalist id="pkglist"></datalist>
<datalist id="ftypelist"></datalist>
<datalist id="nslist"></datalist>
<datalist id="artlist"></datalist>

<div class="scrim" id="catScrim">
  <div class="modal">
    <h3>Reference an existing package <button class="close" data-close>&#10005;</button></h3>
    <div class="body">
      <input class="catsearch" id="catSearch" placeholder="search catalogue (package.node)&hellip;">
      <div id="catList"></div>
    </div>
  </div>
</div>

<div class="scrim" id="commitScrim">
  <div class="modal">
    <h3>Commit &mdash; hand off to the Python companion <button class="close" data-close>&#10005;</button></h3>
    <div class="body">
      <div class="gennote">Download (or copy) this project.json, then run <b>generate</b> in the companion. The previews below are indicative; the deterministic files come from the Python emitter, which also validates against the real language server.</div>
      <div class="modalbtns">
        <button class="tbtn primary" id="dlJson">&#8681; Download project.json</button>
        <button class="tbtn" id="selJson">Select copy text</button>
      </div>
      <div class="tabs" id="genTabs"></div>
      <pre class="gen" id="genOut"></pre>
      <textarea class="copybox" id="copyBox" spellcheck="false" readonly></textarea>
    </div>
  </div>
</div>

<!-- No [data-close] and data-locked: restoring or discarding browser-held work is a decision,
     not something to dismiss by clicking the backdrop. -->
<div class="scrim" id="restoreScrim" data-locked="1">
  <div class="modal">
    <h3>Unsaved work found in this browser</h3>
    <div class="body">
      <div class="gennote">This page was rendered from the project the Python companion seeded. An autosave for the same system is held in this browser and has <b>not</b> been applied.</div>
      <div class="roinfo" id="restoreInfo"></div>
      <div class="modalbtns">
        <button class="tbtn primary" id="doRestore">&#8631; Restore the autosave</button>
        <button class="tbtn" id="doDiscard">Discard it and use the seeded project</button>
      </div>
    </div>
  </div>
</div>

<script>
"use strict";
/*__JS_PRIMITIVES__*/
var DATA = /*__DATA__*/null;
(function(){
  var NS=STUDIO.NS, esc=STUDIO.esc;
  // YAML/Xtext-compatible quoting for the preview (mirrors the Python emitter): backslash
  // escaping works in double quotes for both parsers; a ' or \ forces a single-quoted scalar
  // to the double-quoted form.
  function qd(s){s=String(s);return '"'+s.replace(/\\/g,"\\\\").replace(/"/g,'\\"')+'"';}
  function qs2(s){s=String(s);return (s.indexOf("'")>=0||s.indexOf("\\")>=0)?qd(s):"'"+s+"'";}
  var KINDS=DATA.kindOrder, KIND_LABEL=DATA.kindLabels;
  var SRC_SIDE={pub:1,ss:1,as:1,sub:0,sc:0,ac:0};
  var COMPLEMENT={pub:"sub",sub:"pub",ss:"sc",sc:"ss",as:"ac",ac:"as"};
  var PAIR_TOPIC={pub:1,sub:1};
  var BLOCK=DATA.blocks;                  // kind -> .ros2 spec block, from _studio_common
  var TYPES=DATA.types||[], TYPESET={}; TYPES.forEach(function(t){TYPESET[t]=1;});
  var TYPEFILES=DATA.typeFiles||{};       // {type: relative .ros file} -- drives the RM089 comment
  var SEGBLOCK=DATA.typeSegBlocks||{};    // msg/srv/action -> msgs/srvs/actions
  // .ros vocabulary (rosmodel_lint's own tables). ROSSEG is the inverse of SEGBLOCK: a spec's
  // qualified name spells the SEGMENT ('pkg/msg/Type') while the file spells the BLOCK
  // ('msgs:'), and _companion_ros() crosses between them for every line it writes.
  var ROS=DATA.ros||{blocks:[],bodies:{},scalars:[],arrays:[],nameKeywords:[]};
  var ROSSEG={}; Object.keys(SEGBLOCK).forEach(function(s){ROSSEG[SEGBLOCK[s]]=s;});
  var ROSPRIM={}; (ROS.scalars||[]).concat(ROS.arrays||[]).forEach(function(t){ROSPRIM[t]=1;});
  var ROSKW={}; (ROS.nameKeywords||[]).forEach(function(k){ROSKW[k]=1;});
  // packages the vendored catalogue owns -- _catalogue_packages(), off the same embedded map.
  var CATPKG={}; Object.keys(TYPEFILES).forEach(function(t){CATPKG[t.split("/")[0]]=1;});
  var QOS=DATA.qos||{fields:[],enums:{},newer:[],discouraged:[],durations:[]};
  var QOS_NEW={}, QOS_DISC={}, QOS_DUR={};
  (QOS.newer||[]).forEach(function(k){QOS_NEW[k]=1;});
  (QOS.discouraged||[]).forEach(function(k){QOS_DISC[k]=1;});
  (QOS.durations||[]).forEach(function(k){QOS_DUR[k]=1;});
  var PACKAGES=DATA.packages||[];
  var CATALOGUE=DATA.catalogue||{};
  var CATTYPES=DATA.catalogueTypes||{};   // {pkg.node: {ifaceName: type}} from the vendored .ros2
  var SYSTEMS=DATA.systems||{};           // catalogued systems, for a subSystems: reference

  var project=DATA.project;
  project.nodes=project.nodes||[];
  project.connections=project.connections||[];
  project.packages=project.packages||{};
  project.types=project.types||{};        // formatVersion 4: locally defined message specs
  project.system=project.system||{};
  var DIAG=(project.diagnostics&&project.diagnostics.byNode)||{};
  var uid=1000; function nid(){return "x"+(++uid);}

  var HOME=project.nodes.map(function(n){return {id:n.id,x:n.x,y:n.y};});

  var canvas=document.getElementById("canvas"), svg=document.getElementById("wires"),
      canvasWrap=document.getElementById("canvasWrap"),
      inspector=document.getElementById("inspector");
  STUDIO.makeArrowMarkers(svg,"");
  var selNode=null, selEdge=null, addKind="pub", mode="edit", level=3;
  // which interfaces have their QoS panel open. Kept OUTSIDE `project` on purpose: it is view
  // state, and putting it in the model would make opening a panel an undoable edit.
  var qosOpen={}, cmtOpen={};
  // Comment panels are wired by a per-render registry key rather than by a model id, because the
  // same panel shape serves nodes, interfaces, parameters, connections, the system and a
  // package -- and only the first two of those have an id at all.
  var cmtReg={};
  var kindShown={}; KINDS.forEach(function(k){kindShown[k]=true;});

  document.getElementById("sysname").value=(project.system&&project.system.name)||"system";
  if(DATA.banner){ var b=document.getElementById("banner"); b.className="banner err"; b.innerHTML="<b>"+esc(DATA.banner)+"</b>"; }

  // ---- datalists (offline autocomplete) ----
  (function(){
    var tl=document.getElementById("typelist");
    TYPES.forEach(function(t){var o=document.createElement("option");o.value=t;tl.appendChild(o);});
    var pl=document.getElementById("pkglist");
    PACKAGES.forEach(function(p){var o=document.createElement("option");o.value=p;pl.appendChild(o);});
    // .ros field types: the primitives only. A spec reference is quoted and fully qualified,
    // which no list can enumerate for types the author has not written yet.
    var fl=document.getElementById("ftypelist");
    (ROS.scalars||[]).concat(ROS.arrays||[]).forEach(function(t){
      var o=document.createElement("option");o.value=t;fl.appendChild(o);});
    fillNsList();
  })();

  // `namespace:` has no catalogue to draw on -- it is invented per system, not looked up -- so
  // the useful suggestions are the ones THIS project already uses (typing the second node's
  // namespace should not mean retyping it exactly) plus the two shapes the corpus writes.
  // Rebuilt on demand: a namespace typed into one node should be offered on the next.
  function fillNsList(){
    var el=document.getElementById("nslist");
    if(!el) return;
    var seen={}, out=[];
    (project.nodes||[]).forEach(function(n){
      var v=(n.namespace==null?"":String(n.namespace)).trim();
      if(v&&!seen[v]){seen[v]=1;out.push(v);}
    });
    ["/","/robot1","/robot2"].forEach(function(v){if(!seen[v]){seen[v]=1;out.push(v);}});
    el.innerHTML="";
    out.forEach(function(v){var o=document.createElement("option");o.value=v;el.appendChild(o);});

    // the same argument for `artifact:`: two nodes backed by one artifact is an ordinary
    // shape (the emitter folds them into a single .ros2 block), and it has no catalogue either.
    var al=document.getElementById("artlist");
    if(!al) return;
    var aseen={}, arts=[];
    (project.nodes||[]).forEach(function(n){
      var v=(n.artifact==null?"":String(n.artifact)).trim();
      if(v&&!aseen[v]){aseen[v]=1;arts.push(v);}
    });
    al.innerHTML="";
    arts.sort().forEach(function(v){
      var o=document.createElement("option");o.value=v;al.appendChild(o);});
  }

  function nodeById(id){for(var i=0;i<project.nodes.length;i++)if(project.nodes[i].id===id)return project.nodes[i];return null;}
  function ifaceById(n,id){if(!n)return null;for(var i=0;i<n.ifaces.length;i++)if(n.ifaces[i].id===id)return n.ifaces[i];return null;}

  // ============================ history (undo / redo) ============================
  // ALL editor state is in `project`, so a snapshot is its JSON and undo is a stack of them.
  // Snapshots rather than inverse commands on purpose: Delete removes a node AND every
  // connection touching it, and an inverse would be a second, subtly different implementation
  // of that rule -- the kind that reinstates the node and loses the edges.
  var UNDO_CAP=50, COALESCE_MS=700;
  var undoStack=[], redoStack=[], lastTag=null, lastTagAt=0;
  var dirty=false;

  function snapshot(){ return JSON.stringify(project); }
  function pushSnapshot(s){
    undoStack.push(s);
    if(undoStack.length>UNDO_CAP) undoStack.shift();   // cap: a long session must not grow memory
    redoStack.length=0;                                // a new edit forks the future away
    markDirty();
  }
  // Call BEFORE mutating. `tag` folds a burst of keystrokes in one field into ONE entry: the
  // first keystroke records the pre-edit project and the rest ride along, so Ctrl+Z undoes the
  // word rather than the letter. Discrete actions pass no tag and always push.
  function pushUndo(tag){
    var now=Date.now();
    if(tag && tag===lastTag && (now-lastTagAt)<COALESCE_MS){ lastTagAt=now; markDirty(); return; }
    lastTag=tag||null; lastTagAt=now;
    pushSnapshot(snapshot());
  }
  function markDirty(){ dirty=true; scheduleSave(); updateHistoryUI(); }

  // Re-rendering replaces every DOM node, so a field being typed into loses focus. Put it back
  // by id (or by the iface id on the exposure-label inputs, which have no id).
  function keepFocus(fn){
    var a=document.activeElement, id=(a&&a.id)||"", lbl=(a&&a.dataset&&a.dataset.lbl)||"";
    fn();
    var t=id?document.getElementById(id)
           :(lbl?inspector.querySelector('[data-lbl="'+STUDIO.cssEsc(lbl)+'"]'):null);
    if(t&&t.focus){ try{ t.focus();
      if(t.setSelectionRange&&typeof t.value==="string") t.setSelectionRange(t.value.length,t.value.length);
    }catch(e){} }
  }
  // A restored autosave brings back ids minted by a PREVIOUS session ("x1042"), but this
  // session's counter restarts at 1000 -- restart it above them or the next add collides.
  function syncUid(){
    function bump(id){ var m=/^x(\d+)$/.exec(id||""); if(m) uid=Math.max(uid,+m[1]); }
    project.nodes.forEach(function(n){ bump(n.id);
      (n.ifaces||[]).forEach(function(f){bump(f.id);});
      (n.params||[]).forEach(function(p){bump(p.id);}); });
    project.connections.forEach(function(c){ bump(c.id); });
  }
  function applyState(json){
    project=JSON.parse(json);
    project.nodes=project.nodes||[]; project.connections=project.connections||[];
    project.packages=project.packages||{}; project.system=project.system||{};
    syncUid();
    document.getElementById("sysname").value=(project.system&&project.system.name)||"system";
    if(selNode&&!nodeById(selNode)) selNode=null;   // it may have been deleted in this state
    lastTag=null;                                   // never coalesce across a jump in history
    keepFocus(function(){ render(); fillInspector(); });
    updateHistoryUI();
  }
  // dirty BEFORE applyState: it repaints the topbar, which reports the unsaved state.
  function undo(){ if(!undoStack.length) return;
    redoStack.push(snapshot()); dirty=true; scheduleSave(); applyState(undoStack.pop()); }
  function redo(){ if(!redoStack.length) return;
    undoStack.push(snapshot()); dirty=true; scheduleSave(); applyState(redoStack.pop()); }
  function updateHistoryUI(){
    var u=document.getElementById("undoBtn"), r=document.getElementById("redoBtn");
    if(u) u.disabled=!undoStack.length;
    if(r) r.disabled=!redoStack.length;
    var s=document.getElementById("saveState");
    if(s){ s.textContent=saveNote(); s.className="savestate"+(storageNote?" warn":""); }
  }

  // ============================ autosave ============================
  // Commit is a manual download, so closing the tab used to lose the session. The key is the
  // system name the page was RENDERED with, not the live one: renaming mid-session must not
  // orphan the session's own autosave, and two systems in two tabs must not clobber each other.
  var SAVE_KEY="ros-studio/v1/"+((project.system&&project.system.name)||"system");
  var storage=(function(){
    // Merely touching localStorage throws when storage is blocked, and a private-browsing
    // quota of 0 only shows up on write -- so probe with a real write before trusting it.
    try{ var s=window.localStorage; s.setItem("ros-studio/probe","1"); s.removeItem("ros-studio/probe"); return s; }
    catch(e){ return null; }
  })();
  var storageNote=storage?null:"autosave unavailable — Commit before closing";
  var saveTimer=null, savedAt=null;

  function scheduleSave(){
    if(!storage) return;
    if(saveTimer) clearTimeout(saveTimer);
    saveTimer=setTimeout(saveNow,800);          // debounced: a drag or a typed word is one write
  }
  function saveNow(){
    saveTimer=null;
    if(!storage) return;
    try{
      storage.setItem(SAVE_KEY,JSON.stringify({at:Date.now(),
        system:(project.system&&project.system.name)||"",project:project}));
      savedAt=Date.now();
    }catch(e){
      storage=null;                             // quota exceeded: stop retrying, say so once
      storageNote="autosave failed ("+((e&&e.name)||"error")+") — Commit before closing";
    }
    updateHistoryUI();
  }
  function saveNote(){
    if(storageNote) return storageNote;
    if(dirty) return savedAt?"autosaved locally":"unsaved changes";
    return savedAt?"committed":"";
  }
  function clearDirty(){ dirty=false; updateHistoryUI(); }

  // ============================ viewport (zoom / pan) ============================
  // ONE transform on #canvas moves the node layer and the SVG wire layer together, so the two
  // stay registered by construction. Everything that reads a screen rectangle back into model
  // coordinates therefore has to divide by `view.k` -- portCenter(), drawDeps() and the drag
  // handlers below all do, and that division is the whole reason edges do not detach at zoom.
  var MINZ=0.15, MAXZ=3, view={k:1,tx:0,ty:0};
  function clampZ(k){ return k<MINZ?MINZ:(k>MAXZ?MAXZ:k); }
  // While the view is changing the layer is worth promoting; once it settles the promotion is
  // what makes the text blurry (see .canvas.moving), so it is dropped again a beat later.
  var settleTimer=null;
  function markMoving(){
    canvas.classList.add("moving");
    if(settleTimer) clearTimeout(settleTimer);
    settleTimer=setTimeout(function(){canvas.classList.remove("moving");settleTimer=null;},180);
  }
  function applyView(){
    canvas.style.transform="translate("+view.tx+"px,"+view.ty+"px) scale("+view.k+")";
    markMoving();
    var z=document.getElementById("zLvl");
    if(z) z.textContent=Math.round(view.k*100)+"%";
  }
  // The viewport clips, so the SVG has to be at least as big as the content or an edge to a
  // far node is cut off at the old fixed 1600x1100. Measured, not guessed: a node's height
  // depends on how many interface rows it drew.
  function contentBox(){
    var els=canvas.querySelectorAll(".node,.pkgbox");
    if(!els.length) return {x:0,y:0,w:600,h:400};
    var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
    [].slice.call(els).forEach(function(e){
      x0=Math.min(x0,e.offsetLeft); y0=Math.min(y0,e.offsetTop);
      x1=Math.max(x1,e.offsetLeft+e.offsetWidth); y1=Math.max(y1,e.offsetTop+e.offsetHeight);
    });
    return {x:x0,y:y0,w:Math.max(1,x1-x0),h:Math.max(1,y1-y0)};
  }
  function sizeCanvas(){
    var b=contentBox();
    canvas.style.width=Math.max(1600,b.x+b.w+240)+"px";
    canvas.style.height=Math.max(1100,b.y+b.h+240)+"px";
  }
  // zoom about a point given in VIEWPORT coordinates, so the model point under the pointer
  // (or under the middle of the viewport, for the buttons) does not move.
  function zoomAt(px,py,factor){
    var k2=clampZ(view.k*factor);
    if(k2===view.k) return;
    view.tx=px-(px-view.tx)*(k2/view.k);
    view.ty=py-(py-view.ty)*(k2/view.k);
    view.k=k2; applyView();
  }
  function zoomCentre(factor){
    zoomAt(canvasWrap.clientWidth/2, canvasWrap.clientHeight/2, factor);
  }
  function fitView(){
    var b=contentBox(), pad=44;
    var W=canvasWrap.clientWidth, H=canvasWrap.clientHeight;
    if(W<=0||H<=0) return;
    view.k=clampZ(Math.min((W-2*pad)/b.w,(H-2*pad)/b.h,1.4));
    view.tx=(W-b.w*view.k)/2-b.x*view.k;
    view.ty=(H-b.h*view.k)/2-b.y*view.k;
    applyView();
  }
  function centreOn(nodeId){
    var el=canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(nodeId)+'"]');
    if(!el) return;
    view.tx=canvasWrap.clientWidth/2-(el.offsetLeft+el.offsetWidth/2)*view.k;
    view.ty=canvasWrap.clientHeight/2-(el.offsetTop+el.offsetHeight/2)*view.k;
    applyView();
  }

  // ============================ render ============================
  function render(){
    canvas.className="canvas "+(level===4?"deps":"lvl"+level);
    [].slice.call(canvas.querySelectorAll(".node,.pkgbox")).forEach(function(e){e.remove();});
    for(var i=0;i<project.nodes.length;i++) renderNode(project.nodes[i]);
    if(level===4) renderDeps();
    sizeCanvas();          // before drawEdges: the SVG follows the canvas box at 100%/100%
    drawEdges();
    applyFind();           // render() replaced every element, so the highlight has to go back
    runIssues();
  }
  function renderNode(n){
    var el=document.createElement("div");
    el.className="node"+(n.backing==="cat"?" cat":"")+(n.backing==="sub"?" sub":"")+(selNode===n.id?" sel":"")+((DIAG[n.id]&&DIAG[n.id].length)?" hasdiag":"");
    el.style.left=n.x+"px"; el.style.top=n.y+"px"; el.dataset.n=n.id;
    var fromStr='"'+n.pkg+"."+n.node+'"';
    var badge=n.backing==="sub"?"subsystem":(n.backing==="cat"?"catalogue":"authored");
    var h='<div class="nhead" data-drag><span class="ntitle">'+esc(n.label)+'</span>'
      +'<span class="badge '+(n.backing==="cat"?"cat":"")+'" title="'
      +(n.backing==="sub"?"reached through subSystems: &quot;"+esc(n.subRef||"")+"&quot; — declared in that file, not this one":"")
      +'">'+badge+'</span></div>'
      +'<div class="nfrom">from: '+esc(fromStr)
      +((n.namespace&&String(n.namespace).trim())?'<br>namespace: '+esc(n.namespace):'')
      +'</div><div class="ifaces"></div>';
    el.innerHTML=h;
    var box=el.querySelector(".ifaces");
    for(var j=0;j<n.ifaces.length;j++){
      var f=n.ifaces[j], src=SRC_SIDE[f.kind];
      var row=document.createElement("div");
      row.className="iface"; row.dataset.i=f.id; row.dataset.kind=f.kind;
      row.dataset.hidden=kindShown[f.kind]?"0":"1";
      var sideCls=autoSides?(" side-"+portSide(n,f)):"";
      row.innerHTML='<span class="kd '+f.kind+'">'+f.kind+'</span>'
        +'<span class="inm">'+esc(f.name)+'</span>'
        +'<span class="ity" title="'+esc(f.type||"")+'">'+esc(f.type||"—")+'</span>'
        +'<span class="port '+(src?"src":"snk")+sideCls+' '+f.kind+'" data-n="'+n.id+'" data-i="'+f.id+'" data-kind="'+f.kind+'" data-src="'+src+'" data-type="'+esc(f.type||"")+'"></span>';
      box.appendChild(row);
    }
    if(DIAG[n.id]&&DIAG[n.id].length){
      var d=document.createElement("div"); d.className="diagflag";
      d.textContent="⚠ "+DIAG[n.id].join(" | "); el.appendChild(d);
    }
    canvas.appendChild(el);
  }

  // ---- deps (level 4): bipartite node -> package, resolved against the catalogue ----
  var pkgEls={};
  function renderDeps(){
    pkgEls={};
    var packages={}, order=[];
    project.nodes.forEach(function(n){
      var p=n.pkg||"(local)";
      if(!packages[p]){packages[p]={name:p,nodes:[],resolved:false};order.push(p);}
      packages[p].nodes.push(n);
      var key=n.pkg+"."+n.node;
      if(CATALOGUE[key]||n.backing==="cat") packages[p].resolved=true;
    });
    var colX=980, y=80;
    order.forEach(function(p){
      var pk=packages[p];
      var el=document.createElement("div");
      el.className="pkgbox "+(pk.resolved?"res":"unres");
      el.style.left=colX+"px"; el.style.top=y+"px";
      el.innerHTML='<div class="pt">'+esc(pk.name)+'</div><div class="ps">'+(pk.resolved?"in catalogue":"local / not in catalogue")+' · '+pk.nodes.length+' node(s)</div>';
      canvas.appendChild(el); pkgEls[p]=el; y+=90;
    });
  }

  function esc2(s){return esc(s);}
  // Model coordinates, NOT screen ones: getBoundingClientRect() reports the transformed box,
  // so every delta has to come back through the zoom factor. Skipping that division is exactly
  // how a wire layer detaches from its ports the moment the canvas is not at 100%.
  function portCenter(nId,iId){
    var p=canvas.querySelector('.port[data-n="'+nId+'"][data-i="'+iId+'"]');
    var cr=canvas.getBoundingClientRect(), k=view.k||1;
    if(p){var pr=p.getBoundingClientRect(); if(pr.width>0) return {x:(pr.left-cr.left+pr.width/2)/k,y:(pr.top-cr.top+pr.height/2)/k};}
    // fall back to node-box centre (level 1 hides ports)
    var nb=canvas.querySelector('.node[data-n="'+nId+'"]');
    if(!nb) return null;
    var br=nb.getBoundingClientRect();
    return {x:(br.left-cr.left+br.width/2)/k, y:(br.top-cr.top+br.height/2)/k};
  }
  function edgeKindPair(c){
    var a=ifaceById(nodeById(c.from.n),c.from.i);
    return (a&&PAIR_TOPIC[a.kind])?"topic":"rr";
  }
  // REQUIREMENT: the kind filter must hide EDGES, not just interface rows. drawEdges reads the
  // live kindShown set and skips any connection whose from- OR to-interface kind is disabled;
  // the filter checkboxes mutate kindShown and call render(), so edges recompute every change.
  function drawEdges(){
    [].slice.call(svg.querySelectorAll("path.edge,path.depedge")).forEach(function(e){e.remove();});
    if(level===4){ drawDeps(); return; }
    for(var i=0;i<project.connections.length;i++){
      var c=project.connections[i];
      var a=ifaceById(nodeById(c.from.n),c.from.i), bb=ifaceById(nodeById(c.to.n),c.to.i);
      if(!a||!bb) continue;
      if(!kindShown[a.kind] || !kindShown[bb.kind]) continue;   // <-- edge hidden by filter
      var s=portCenter(c.from.n,c.from.i), t=portCenter(c.to.n,c.to.i);
      if(!s||!t) continue;
      var path=document.createElementNS(NS,"path");
      path.setAttribute("class","edge "+edgeKindPair(c)+(selEdge===c.id?" sel":""));
      path.setAttribute("d",STUDIO.bezier(s.x,s.y,t.x,t.y));
      path.dataset.c=c.id; path.style.pointerEvents="stroke"; path.style.cursor="pointer";
      (function(cid){path.addEventListener("click",function(ev){ev.stopPropagation();selEdge=cid;selNode=null;render();fillInspector();});})(c.id);
      svg.appendChild(path);
    }
  }
  function drawDeps(){
    project.nodes.forEach(function(n){
      var pe=pkgEls[n.pkg||"(local)"]; if(!pe) return;
      var nb=canvas.querySelector('.node[data-n="'+n.id+'"]'); if(!nb) return;
      var cr=canvas.getBoundingClientRect(), a=nb.getBoundingClientRect(), b=pe.getBoundingClientRect(), k=view.k||1;
      var ax=(a.right-cr.left)/k, ay=(a.top-cr.top+a.height/2)/k,
          bx=(b.left-cr.left)/k, by=(b.top-cr.top+b.height/2)/k;
      var path=document.createElementNS(NS,"path"); path.setAttribute("class","depedge edge");
      path.setAttribute("marker-end","url(#ah)");
      path.setAttribute("d",STUDIO.bezier(ax,ay,bx,by)); svg.appendChild(path);
    });
  }

  // ============================ automatic port sides ============================
  // Opt-in, because it MOVES things: with it off, a port's edge is decided by its kind (sources
  // right, sinks left), which is predictable and is what the read-only views assume. With it on,
  // each CONNECTED port moves to the edge that faces its partner, so a wire to a node on the
  // left leaves from the left instead of looping around the card. That is where the spaghetti
  // comes from: a fixed side forces every backwards edge to travel the full width of both cards.
  //
  // The rule per port, using model coordinates (the nodes' own x/y, so it does not depend on
  // having been rendered yet):
  //   * unconnected            -> the kind default, unchanged. Nothing to face.
  //   * partners mostly left   -> left edge
  //   * partners mostly right  -> right edge
  //   * partners mostly below, and the vertical separation dominates the horizontal one
  //                            -> bottom edge, which is what stops a stack of vertical wires
  //                               from being dragged sideways through the card first.
  // Ties keep the kind default, so the layout stays stable rather than flickering between two
  // equally good answers as a node is dragged past its partner.
  var autoSides=false;
  // Measured off the rendered card when there is one (a card's width follows its longest type
  // string), with the stylesheet's min-width as the fallback for the first paint.
  function nodeBox(n){
    var el=canvas.querySelector('.node[data-n="'+n.id+'"]'), k=view.k||1;
    if(el){
      var r=el.getBoundingClientRect();
      if(r.width>0) return {w:r.width/k,h:r.height/k};
    }
    return {w:190,h:120};
  }
  function nodeCentre(n){
    var b=nodeBox(n);
    return {x:(n.x||0)+b.w/2, y:(n.y||0)+b.h/2};
  }
  function portSide(n,f){
    var def=SRC_SIDE[f.kind]?"r":"l";
    var me=nodeCentre(n), dx=0, dy=0, seen=0;
    (project.connections||[]).forEach(function(c){
      var other=null;
      if(c.from.n===n.id&&c.from.i===f.id) other=nodeById(c.to.n);
      else if(c.to.n===n.id&&c.to.i===f.id) other=nodeById(c.from.n);
      if(!other) return;
      var oc=nodeCentre(other);
      dx+=oc.x-me.x; dy+=oc.y-me.y; seen++;
    });
    if(!seen) return def;
    dx/=seen; dy/=seen;
    if(dy>60&&Math.abs(dy)>Math.abs(dx)*1.4) return "b";
    if(dx>20) return "r";
    if(dx<-20) return "l";
    return def;
  }

  // ============================ opening files in the page ============================
  // The companion's `init` is the AUTHORITATIVE seeder and stays that way: it resolves the
  // vendored catalogue, walks sibling directories, and reports what it could not carry. This is
  // the same job done offline, on the files the browser is handed, for the case the whole page
  // exists to serve -- someone opens ros-studio.html and wants to look at a model without
  // going back to a shell.
  //
  // Two implementations of one seeder is exactly the shape that has silently truncated this
  // project's models three times, so this one is held to the Python one file-for-file by
  // tests/studio_parity.js (SEED cases): same nodes, exposures, connections, subSystems,
  // namespaces, parameters, qos, types and comments, or the test fails. Where it CANNOT match
  // -- a catalogue node the page's embedded index does not carry, a subSystems: target whose
  // file was not opened -- it says so in the load report rather than quietly seeding less.

  function splitLines(text){
    return String(text).replace(/\r\n/g,"\n").replace(/\r/g,"\n").split("\n");
  }
  function indentOf(line){
    var m=/^[ \t]*/.exec(line)[0], col=0;
    for(var i=0;i<m.length;i++) col = m[i]==="\t" ? ((col>>3)+1)*8 : col+1;
    return col;
  }
  // A comment runs to end of line, and a '#' inside quotes is not one. Mirrors
  // ros_studio._split_comment.
  function splitComment(line){
    var q=null;
    for(var i=0;i<line.length;i++){
      var ch=line[i];
      if(q){ if(ch===q) q=null; continue; }
      if(ch==='"'||ch==="'"){ q=ch; continue; }
      if(ch==="#") return [line.slice(0,i), line.slice(i+1)];
    }
    return [line,null];
  }
  function cleanNote(t){ return t==null?null:String(t).replace(/^ /,"").replace(/\s+$/,""); }
  function unq(s){
    s=String(s==null?"":s).trim();
    if(s.length>1&&((s[0]==='"'&&s[s.length-1]==='"')||(s[0]==="'"&&s[s.length-1]==="'")))
      return s.slice(1,-1);
    return s;
  }
  function cmtSet(obj,slot,val){
    if(val==null||(Array.isArray(val)&&!val.length)||val==="") return;
    (obj.comments=obj.comments||{})[slot]=val;
  }

  // ---- .ros2 ---------------------------------------------------------------------------
  function parseRos2(text){
    var BLOCK_TO_KIND={};
    Object.keys(BLOCK).forEach(function(k){ BLOCK_TO_KIND[BLOCK[k]]=k; });
    var lines=splitLines(text), out={pkg:null,git:null,artifacts:[],comments:{}}, lead=[];
    var art=null, sect=null, iface=null, param=null, qos=null, seenRoot=false;
    for(var i=0;i<lines.length;i++){
      var raw=lines[i], parts=splitComment(raw), code=parts[0], note=cleanNote(parts[1]);
      var body=code.trim();
      if(!body){ if(note!=null) lead.push(note); continue; }
      var ind=indentOf(code), key=/^("[^"]*"|'[^']*'|[^:#]+?)\s*:\s*(.*)$/.exec(body);
      var kw=key?unq(key[1]):null, val=key?key[2].trim():null;
      if(!seenRoot&&key&&!val){
        out.pkg=kw; seenRoot=true;
        if(lead.length){ out.comments.header=lead.slice(); lead=[]; }
        continue;
      }
      if(!seenRoot) continue;
      if(key&&kw==="fromGitRepo"){ out.git=unq(val); lead=[]; continue; }
      if(key&&kw==="artifacts"&&!val){ sect="artifacts"; continue; }
      if(sect!=="artifacts") continue;
      if(key&&!val&&ind<=4&&kw!=="qos"){
        art={name:kw,node:null,ifaces:[],params:[]};
        cmtSet(art,"ros2Before",lead.slice()); cmtSet(art,"ros2Line",note);
        lead=[]; out.artifacts.push(art); iface=null; param=null; qos=null;
        continue;
      }
      if(!art) continue;
      if(key&&kw==="node"&&val){ art.node=unq(val); lead=[]; continue; }
      if(key&&!val&&BLOCK_TO_KIND[kw]){ art.block=BLOCK_TO_KIND[kw]; art.inParams=false;
                                        iface=null; param=null; qos=null; continue; }
      if(key&&!val&&kw==="parameters"){ art.inParams=true; art.block=null;
                                        iface=null; param=null; qos=null; continue; }
      if(key&&!val&&kw==="qos"){ qos=(iface&&iface.qos)?iface.qos:{}; if(iface) iface.qos=qos;
                                 continue; }
      if(qos&&key&&val){ qos[kw]=unq(val); continue; }
      if(key&&!val&&art.block){
        iface={id:null,name:kw,kind:art.block,type:null,qos:null,label:null,exposed:false};
        cmtSet(iface,"ros2Before",lead.slice()); cmtSet(iface,"ros2Line",note);
        lead=[]; art.ifaces.push(iface); param=null; qos=null; continue;
      }
      if(key&&!val&&art.inParams){
        param={name:kw,ptype:"String",value:null};
        cmtSet(param,"ros2Before",lead.slice()); cmtSet(param,"ros2Line",note);
        lead=[]; art.params.push(param); iface=null; qos=null; continue;
      }
      if(key&&val&&iface&&kw==="type"){ iface.type=unq(val); cmtSet(iface,"ros2Type",note);
                                        lead=[]; continue; }
      if(key&&val&&param&&kw==="type"){ param.ptype=unq(val); lead=[]; continue; }
      if(key&&val&&param&&(kw==="default"||kw==="value")){ param.value=unq(val); param.slot=kw;
                                                           lead=[]; continue; }
      lead=[];
    }
    return out;
  }

  // ---- .ros ----------------------------------------------------------------------------
  function parseRos(text){
    var lines=splitLines(text), types={}, pkg=null, block=null, spec=null, bodyKw=null;
    var blockNames=(ROS.blocks||["msgs","srvs","actions"]);
    var SEG={msgs:"msg",srvs:"srv",actions:"action"};
    for(var i=0;i<lines.length;i++){
      var code=splitComment(lines[i])[0], body=code.trim();
      if(!body) continue;
      var key=/^([^:#]+?)\s*:\s*(.*)$/.exec(body), kw=key?key[1].trim():null;
      if(key&&!key[2]&&indentOf(code)===0){ pkg=kw; block=null; spec=null; bodyKw=null; continue; }
      if(!pkg) continue;
      if(key&&!key[2]&&blockNames.indexOf(kw)>=0){ block=kw; spec=null; bodyKw=null; continue; }
      if(!block) continue;
      var bodies=(ROS.bodies&&ROS.bodies[block])||[];
      if(bodies.indexOf(body)>=0){ bodyKw=body; if(spec) spec.fields[bodyKw]=spec.fields[bodyKw]||[];
                                   continue; }
      if(!key&&/^[A-Za-z_][A-Za-z0-9_]*$/.test(body)){
        spec={fields:{}}; bodyKw=null;
        types[pkg+"/"+SEG[block]+"/"+body]=spec; continue;
      }
      if(spec&&bodyKw){
        var tok=body.split(/\s+/);
        if(tok.length===2) spec.fields[bodyKw].push({type:tok[0],name:tok[1]});
        else if(tok.length===1&&tok[0].indexOf("=")>0) spec.fields[bodyKw].push({type:"",name:tok[0]});
      }
    }
    return types;
  }

  // ---- .rossystem ----------------------------------------------------------------------
  function parseRossystem(text){
    var ARROW_RE=/^\s*-?\s*("[^"]*"|'[^']*'|[^:]+?)\s*:\s*(pub|sub|ss|sc|as|ac)->\s*(.*)$/;
    // `- "label": "artifact::name"` -- a RosParameter exposure. No arrow, so it is only ever
    // matched inside a node's `parameters:` block (RosSystem.xtext:78-82).
    var PARAM_RE=/^\s*-\s*("[^"]*"|'[^']*'|[^\s:]+)\s*:\s*(\S.*?)\s*$/;
    var lines=splitLines(text);
    var out={name:null,fromFile:null,subSystems:[],nodes:[],params:[],connections:[],
             comments:{}};
    var lead=[], sect=null, node=null, sub=false, seenRoot=false;
    var topIndent=null, nsub=null, sysParam=null;
    for(var i=0;i<lines.length;i++){
      var raw=lines[i], parts=splitComment(raw), code=parts[0], note=cleanNote(parts[1]);
      var body=code.trim();
      if(!body){ if(note!=null) lead.push(note); continue; }
      var ind=indentOf(code);
      var key=/^("[^"]*"|'[^']*'|[^:#]+?)\s*:\s*(.*)$/.exec(body);
      var kw=key?unq(key[1]):null, val=key?key[2].trim():null;

      if(!seenRoot&&key&&!val){
        out.name=kw; seenRoot=true;
        if(lead.length){ out.comments.header=lead.slice(); lead=[]; }
        continue;
      }
      if(!seenRoot) continue;

      if(key&&kw==="fromFile"&&val){ out.fromFile=unq(val); cmtSet(out,"fromFile",note);
                                     lead=[]; continue; }
      // A top-level block key is recognised by INDENT, not by name alone: `parameters:` is
      // BOTH a system-level block and a node member, and only the indent tells them apart.
      // Keying on anything else made ur_robot.rossystem's system parameters parse as NODES.
      if(key&&!val&&(kw==="nodes"||kw==="connections"||kw==="subSystems"||kw==="processes"
                     ||kw==="parameters")){
        if(topIndent==null) topIndent=ind;
        if(ind<=topIndent){
          sect=kw; node=null; nsub=null; sysParam=null;
          sub=(kw==="subSystems"); lead=[]; continue;
        }
      }
      // a subSystems: entry is one bare (optionally quoted) name, positionally recognised
      if(sub&&!key&&body.indexOf(":")<0){
        var ref=unq(body.replace(/^-\s*/,""));
        if(ref){ var e={ref:ref,file:null};
                 cmtSet(e,"before",lead.slice()); cmtSet(e,"line",note);
                 lead=[]; out.subSystems.push(e); continue; }
      }
      if(sect==="connections"){
        var m=/^-\s*\[\s*("?[^,\]"]+"?)\s*,\s*("?[^,\]"]+"?)\s*\]/.exec(body);
        if(m){ var c={from:unq(m[1]),to:unq(m[2])};
               cmtSet(c,"before",lead.slice()); cmtSet(c,"line",note);
               lead=[]; out.connections.push(c); continue; }
      }
      // ---- system-level parameters: a MAPPING entry (`name:` then ns/type/default/value),
      // not a dash item. Parameter, Basics.xtext:41-49.
      if(sect==="parameters"&&node==null){
        if(key&&!val){
          sysParam={name:kw,ptype:null,"default":null,value:null,ns:null};
          cmtSet(sysParam,"before",lead.slice()); cmtSet(sysParam,"line",note);
          lead=[]; out.params.push(sysParam); continue;
        }
        if(sysParam&&key&&val){
          // `default:` belongs to the ParameterType, `value:` to the Parameter -- two
          // different slots, never folded together.
          if(kw==="type"){ sysParam.ptype=unq(val); cmtSet(sysParam,"type",note); lead=[];
                           continue; }
          if(kw==="default"){ sysParam["default"]=unq(val); lead=[]; continue; }
          if(kw==="value"){ sysParam.value=unq(val); cmtSet(sysParam,"value",note); lead=[];
                            continue; }
          if(kw==="ns"){ sysParam.ns=unq(val); cmtSet(sysParam,"ns",note); lead=[]; continue; }
        }
      }
      if(sect==="nodes"){
        // a node's own `interfaces:` / `parameters:` sub-block
        if(key&&!val&&node&&(kw==="interfaces"||kw==="parameters")){
          nsub=kw; lead=[]; continue;
        }
        if(nsub==="parameters"&&node){
          var pm=PARAM_RE.exec(body);
          if(pm){
            var pt=unq(pm[2]), pb=pt.split("::");
            var np={label:unq(pm[1]),
                    name:pb.length>1?pb[1]:pb[0],
                    artifact:pb.length>1?pb[0]:null, value:null};
            cmtSet(np,"before",lead.slice()); cmtSet(np,"line",note);
            lead=[]; node.params.push(np); continue;
          }
          if(key&&val&&kw==="value"&&node.params.length){
            node.params[node.params.length-1].value=unq(val); lead=[]; continue;
          }
        }
        var arrow=ARROW_RE.exec(body);
        if(arrow&&node){
          var tgt=unq(arrow[3]), bits=tgt.split("::");
          var f={label:unq(arrow[1]),kind:arrow[2],
                 artifact:bits.length>1?bits[0]:null,
                 ifaceName:bits.length>1?bits[1]:bits[0]};
          cmtSet(f,"before",lead.slice()); cmtSet(f,"line",note);
          lead=[]; node.ifaces.push(f); continue;
        }
        if(key&&!val&&ind<=4&&!arrow){
          node={label:kw,from:null,namespace:null,ifaces:[],params:[]};
          cmtSet(node,"before",lead.slice()); cmtSet(node,"line",note);
          lead=[]; nsub=null; out.nodes.push(node); continue;
        }
        if(node&&key&&val&&kw==="from"){ node.from=unq(val); cmtSet(node,"from",note);
                                         lead=[]; continue; }
        if(node&&key&&val&&kw==="namespace"){ node.namespace=unq(val); lead=[]; continue; }
      }
      lead=[];
    }
    return out;
  }

  // ---- seeding ---------------------------------------------------------------------------
  // Mirrors ros_studio.seed_from_rossystem. Every rule that fixed a silent truncation is
  // repeated here on purpose, with the same reasoning, because this path can lose a model the
  // same way the Python one used to:
  //   * the exposure LABEL and the interface NAME are different slots, both preserved;
  //   * `exposed` is independent of connectivity;
  //   * an exposure the backing artifact does not declare is kept and flagged `orphan`;
  //   * a (name, kind) match wins, and the name-only fallback is refused when the same name
  //     exists under another kind (a pub/sub pair would otherwise invent an exposure);
  //   * the ARTIFACT the arrow spells beats the node name when several artifacts share a node.
  // MIRRORS ros_studio._merge_params. A parameter lives in two unrelated grammar rules:
  // Parameter (the .ros2 artifact DECLARES it, with a type and a default) and RosParameter
  // (this system EXPOSES it under a label and overrides its value). Matching is by the
  // artifact parameter NAME the `ref` arrow-points at, never by the label -- the label is free
  // text and the corpus does spell it differently from the name.
  function mergeParams(declared,exposed,nid){
    var out=[], byName={};
    (declared||[]).forEach(function(p){
      var rec={id:nid("p"),name:p.name,ptype:p.ptype,value:p.value,
               label:null,exposed:false,sysValue:null};
      if(p.comments) rec.comments=p.comments;
      byName[p.name]=rec; out.push(rec);
    });
    (exposed||[]).forEach(function(e){
      var name=e.name||e.label, rec=byName[name];
      if(rec===undefined){
        // exposed but declared by no .ros2 the project carries -- kept and flagged, the same
        // way an exposure of an undeclared INTERFACE is
        rec={id:nid("p"),name:name,ptype:null,value:null,
             label:e.label,exposed:true,sysValue:e.value,
             orphan:!(declared&&declared.length)};
        if(e.comments) rec.comments=e.comments;
        byName[name]=rec; out.push(rec);
        return;
      }
      rec.label=e.label; rec.exposed=true; rec.sysValue=e.value;
      if(e.comments){ rec.comments=rec.comments||{};
                      Object.keys(e.comments).forEach(function(k){ rec.comments[k]=e.comments[k]; }); }
    });
    return out;
  }
  function seedFromFiles(files){
    var sysFiles=[], ros2=[], rosTypes={}, report=[], uid=0;
    function nid(p){ uid++; return p+uid; }

    files.forEach(function(f){
      if(/\.rossystem$/i.test(f.name)) sysFiles.push({name:f.name,model:parseRossystem(f.text)});
      else if(/\.ros2$/i.test(f.name)) ros2.push({name:f.name,pkg:parseRos2(f.text)});
      else if(/\.ros$/i.test(f.name)){
        var t=parseRos(f.text);
        Object.keys(t).forEach(function(k){ rosTypes[k]=t[k]; });
      }
    });
    if(!sysFiles.length) return {error:"no .rossystem among the opened files"};

    // index every artifact by (package, artifact) and by (package, node); an ambiguous node
    // key is refused rather than resolved to an arbitrary winner (ros_studio.resolve_artifact)
    var byArt={}, byNode={}, pkgGit={}, ros2Cmts={};
    ros2.forEach(function(entry){
      var p=entry.pkg;
      if(!p.pkg) return;
      if(p.git) pkgGit[p.pkg]=p.git;
      ros2Cmts[p.pkg]=p.comments||{};
      p.artifacts.forEach(function(a){
        byArt[p.pkg+" "+a.name]={pkg:p.pkg,art:a};
        var k=p.pkg+" "+a.node;
        if(byNode[k]===undefined) byNode[k]={pkg:p.pkg,art:a};
        else if(byNode[k]&&byNode[k].art!==a) byNode[k]=null;   // ambiguous
      });
    });
    function resolveArtifact(pkg,nodeName,artifact){
      if(artifact){ var hit=byArt[pkg+" "+artifact]; if(hit) return hit; }
      var byN=byNode[pkg+" "+nodeName];
      return byN||null;
    }

    var primary=sysFiles[0];
    if(sysFiles.length>1)
      report.push(sysFiles.length+" .rossystem files were opened; '"+primary.name+"' is the "
        +"project and the others are available as subSystems: targets. Merging several systems "
        +"into one is `init <dir>` in the companion, not this loader.");

    var model=primary.model, nodes=[], conns=[], subSystems=[], packages={}, types={};
    var subExposure={};

    // subSystems: resolved against the OTHER opened .rossystem files, then the embedded
    // catalogue. Unresolved is reported, never silently skipped.
    model.subSystems.forEach(function(entry){
      var target=null;
      for(var i=1;i<sysFiles.length;i++){
        var cand=sysFiles[i], base=cand.name.replace(/\.rossystem$/i,"");
        if(base===entry.ref||cand.model.name===entry.ref){ target=cand; break; }
      }
      var cat=SYSTEMS[entry.ref];
      var rec={ref:entry.ref,file:(!target&&cat)?(cat.file||null):null};
      if(entry.comments) rec.comments=entry.comments;
      subSystems.push(rec);
      if(!target&&cat&&!cat.hasOwnSubsystems){
        // catalogued: the same table L.load_system_index() serves the companion
        Object.keys(cat.nodes||{}).sort().forEach(function(label){
          var info=cat.nodes[label]||{}, frm=info.from||"", dot=frm.indexOf(".");
          var n={id:nid("n"),label:label,backing:"sub",subRef:entry.ref,
                 pkg:dot>0?frm.slice(0,dot):"",node:dot>0?frm.slice(dot+1):"",
                 artifact:null,catalogueFile:null,namespace:null,
                 x:120+nodes.length*40,y:520,ifaces:[],params:[]};
          Object.keys(info.interfaces||{}).sort().forEach(function(nm){
            var k=info.interfaces[nm];
            if(KINDS.indexOf(k)<0) return;
            var nf={id:nid("i"),name:nm,kind:k,type:null,qos:null,label:nm,exposed:true};
            n.ifaces.push(nf);
            if(subExposure[nm]===undefined) subExposure[nm]=[n,nf];
          });
          nodes.push(n);
        });
        return;
      }
      if(!target){
        report.push("subSystems: '"+entry.ref+"' is neither among the opened files nor in the "
          +"vendored catalogue, so the nodes it provides are missing and any connection naming "
          +"one of them cannot be re-linked. Open "+entry.ref+".rossystem alongside this file, "
          +"or seed with the companion.");
        return;
      }
      target.model.nodes.forEach(function(sn){
        var frm=sn.from||"", dot=frm.indexOf("."), n={
          id:nid("n"), label:sn.label, backing:"sub", subRef:entry.ref,
          pkg:dot>0?frm.slice(0,dot):"", node:dot>0?frm.slice(dot+1):"",
          artifact:null, catalogueFile:null, namespace:null,
          x:120+nodes.length*40, y:520, ifaces:[], params:[]
        };
        sn.ifaces.forEach(function(f){
          var nf={id:nid("i"),name:f.label,kind:f.kind,type:null,qos:null,
                  label:f.label,exposed:true};
          n.ifaces.push(nf);
          if(subExposure[f.label]===undefined) subExposure[f.label]=[n,nf];
        });
        nodes.push(n);
      });
    });

    model.nodes.forEach(function(mn,idx){
      var frm=mn.from||"", dot=frm.indexOf(".");
      var pkg=dot>0?frm.slice(0,dot):"", nodeName=dot>0?frm.slice(dot+1):"";
      var artifact=null;
      for(var i=0;i<mn.ifaces.length;i++){ if(mn.ifaces[i].artifact){ artifact=mn.ifaces[i].artifact; break; } }
      var hit=resolveArtifact(pkg,nodeName,artifact);
      var cat=CATALOGUE[frm];
      var n={id:nid("n"), label:mn.label, backing:hit?"hand":(cat?"cat":"hand"),
             pkg:pkg, node:nodeName, artifact:artifact||(hit?hit.art.name:(cat?cat.artifact:nodeName)),
             catalogueFile:(!hit&&cat)?cat.file:null, namespace:mn.namespace||null,
             x:120+(idx%4)*260, y:120+Math.floor(idx/4)*200, ifaces:[], params:[]};
      if(mn.comments) n.comments=mn.comments;
      // the node carries BOTH its .rossystem comments (before/line/from) and the backing
      // artifact's own (ros2Before/ros2Line) -- they annotate one element across two files,
      // and emit_ros2 writes the second pair back into the .ros2
      if(hit&&hit.art.comments){
        n.comments=n.comments||{};
        Object.keys(hit.art.comments).forEach(function(k){ n.comments[k]=hit.art.comments[k]; });
      }

      // exposures indexed by the interface NAME they target, per kind, so the LABEL survives
      var byPair={}, byName={}, kindsFor={};
      mn.ifaces.forEach(function(f){
        var tgt=f.ifaceName||f.label;
        if(byPair[tgt+" "+f.kind]===undefined) byPair[tgt+" "+f.kind]=f;
        if(byName[tgt]===undefined) byName[tgt]=f;
        (kindsFor[tgt]=kindsFor[tgt]||{})[f.kind]=1;
      });

      var claimed={};
      var declared=hit?hit.art.ifaces:(cat?catIfaces(frm):null);
      if(declared){
        declared.forEach(function(d){
          var src=byPair[d.name+" "+d.kind];
          if(src===undefined){
            var only=Object.keys(kindsFor[d.name]||{});
            if(!only.length) src=byName[d.name];        // no exposure of that name at all
            else src=undefined;                          // exists under another kind: not ours
          }
          if(src) claimed[src.label]=1;
          var nf={id:nid("i"),name:d.name,kind:d.kind,type:d.type||null,
                  qos:d.qos||null,label:src?src.label:null,exposed:!!src};
          if(src&&src.comments) nf.comments=src.comments;
          if(d.comments){ nf.comments=nf.comments||{};
                          Object.keys(d.comments).forEach(function(k){ nf.comments[k]=d.comments[k]; }); }
          n.ifaces.push(nf);
        });
        mn.ifaces.forEach(function(f){
          if(claimed[f.label]) return;
          var nf={id:nid("i"),name:f.ifaceName||f.label,kind:f.kind,type:null,qos:null,
                  label:f.label,exposed:true,orphan:true};
          if(f.comments) nf.comments=f.comments;
          n.ifaces.push(nf);
        });
        n.params=mergeParams(hit?hit.art.params:[], mn.params||[], nid);
      } else {
        // nothing backs it: keep exactly what the .rossystem exposed
        mn.ifaces.forEach(function(f){
          var nf={id:nid("i"),name:f.ifaceName||f.label,kind:f.kind,type:null,qos:null,
                  label:f.label,exposed:true};
          if(f.comments) nf.comments=f.comments;
          n.ifaces.push(nf);
        });
        n.params=mergeParams([], mn.params||[], nid);
        if(!cat) report.push("node '"+mn.label+"' has no .ros2 among the opened files, so its "
          +"interface TYPES and parameters are unknown. Open "+(pkg||"its package")+".ros2 too.");
      }
      if(n.backing==="hand"&&pkg){
        packages[pkg]=packages[pkg]||{fromGitRepo:pkgGit[pkg]||null};
        if(ros2Cmts[pkg]&&ros2Cmts[pkg].header)
          packages[pkg].comments={header:ros2Cmts[pkg].header};
      }
      nodes.push(n);
    });

    function catIfaces(frm){
      var entry=CATALOGUE[frm]; if(!entry) return null;
      var typemap=CATTYPES[frm]||{}, out=[];
      Object.keys(entry.interfaces||{}).sort().forEach(function(name){
        out.push({name:name,kind:entry.interfaces[name],type:typemap[name]||null,qos:null});
      });
      return out;
    }

    // connections: endpoints name LABELS, resolved against local exposures then subsystems
    var byLabel={};
    nodes.forEach(function(n){ n.ifaces.forEach(function(f){
      if(f.label&&byLabel[f.label]===undefined) byLabel[f.label]=[n,f]; }); });
    model.connections.forEach(function(c){
      var a=byLabel[c.from]||subExposure[c.from], b=byLabel[c.to]||subExposure[c.to];
      if(!a||!b){
        report.push("connection ["+c.from+", "+c.to+"] could not be re-linked: "
          +(!a?("'"+c.from+"'"):("'"+c.to+"'"))+" matches no exposure among the opened files. "
          +"It is NOT carried into the project.");
        return;
      }
      var rec={id:nid("c"),from:{n:a[0].id,i:a[1].id},to:{n:b[0].id,i:b[1].id}};
      if(c.comments) rec.comments=c.comments;
      conns.push(rec);
    });

    Object.keys(rosTypes).forEach(function(k){ types[k]=rosTypes[k]; });

    // the system-level `parameters:` block: a peer of nodes: and connections:, not a node
    var sysParams=(model.params||[]).map(function(p){
      var rec={id:nid("sp"),name:p.name,ptype:p.ptype,
               "default":p["default"],value:p.value,ns:p.ns};
      if(p.comments) rec.comments=p.comments;
      return rec;
    });
    var project={
      formatVersion:5,
      system:{name:model.name||"system",fromFile:model.fromFile||null},
      subSystems:subSystems, params:sysParams, nodes:nodes, connections:conns,
      packages:packages, types:types,
      diagnostics:{global:report.slice(),byNode:{}},
      seededFrom:primary.name, seededInBrowser:true
    };
    if(model.comments&&Object.keys(model.comments).length) project.comments=model.comments;
    return {project:project, report:report, name:primary.name};
  }

  // ---- the Open control ------------------------------------------------------------------
  function readFiles(fileList, done){
    var files=Array.prototype.slice.call(fileList||[]), out=[], left=files.length;
    if(!left){ done([]); return; }
    files.forEach(function(f,idx){
      var r=new FileReader();
      r.onload=function(){ out[idx]={name:f.name,text:String(r.result||"")};
                           if(--left===0) done(out.filter(Boolean)); };
      r.onerror=function(){ out[idx]=null; if(--left===0) done(out.filter(Boolean)); };
      r.readAsText(f);
    });
  }

  function applyLoadedProject(next, sourceName, report){
    // Same guard the autosave prompt uses: replacing the model is not undoable past the stack,
    // so unsaved work gets a chance to survive.
    if(dirty && !window.confirm("Replace the current project with "+sourceName+"?\n\n"
        +"There are changes since the last Commit. Loading discards them.")) return false;
    pushUndo("load:"+sourceName);
    project=next;
    selNode=null; selEdge=null;
    if(project.system&&project.system.name)
      document.getElementById("sysname").value=project.system.name;
    fillNsList();
    sizeCanvas(); render(); fillInspector(); fitView();
    var b=document.getElementById("banner");
    if(report&&report.length){
      b.className="banner warn";
      b.innerHTML="<b>Loaded "+esc(sourceName)+"</b> with "+report.length
        +" note(s) — the companion's <code>init</code> is the authoritative seeder:<br>"
        +report.map(function(r){return "• "+esc(r);}).join("<br>");
    } else {
      b.className="banner";
      b.innerHTML="<b>Loaded "+esc(sourceName)+".</b> Edit, then <b>Commit</b> to hand the "
        +"project.json back to the Python companion for generation and validation.";
    }
    return true;
  }

  function openFiles(fileList){
    readFiles(fileList, function(files){
      if(!files.length) return;
      var proj=null, projName=null;
      files.forEach(function(f){
        if(!/\.json$/i.test(f.name)) return;
        try{
          var parsed=JSON.parse(f.text);
          if(parsed&&parsed.nodes&&parsed.system){ proj=parsed; projName=f.name; }
        }catch(e){
          window.alert(f.name+" is not readable JSON: "+((e&&e.message)||e));
        }
      });
      if(proj){
        // a project.json is the page's OWN format -- loaded exactly, never re-seeded
        applyLoadedProject(proj, projName, (proj.diagnostics&&proj.diagnostics.global)||[]);
        return;
      }
      var res=seedFromFiles(files);
      if(res.error){ window.alert("Could not load: "+res.error); return; }
      applyLoadedProject(res.project, res.name, res.report);
    });
  }

  (function wireOpen(){
    var input=document.getElementById("openInput"), btn=document.getElementById("openBtn");
    if(btn&&input){
      btn.onclick=function(){ input.value=""; input.click(); };
      input.onchange=function(){ openFiles(input.files); };
    }
    // Drag a whole model set onto the canvas. The default browser behaviour for a dropped file
    // is to NAVIGATE to it, which would discard the session, so both handlers are required.
    var zone=document.getElementById("canvasWrap")||document.body;
    ["dragenter","dragover"].forEach(function(ev){
      zone.addEventListener(ev,function(e){
        if(!e.dataTransfer||!e.dataTransfer.types) return;
        if(Array.prototype.indexOf.call(e.dataTransfer.types,"Files")<0) return;
        e.preventDefault(); e.stopPropagation();
        e.dataTransfer.dropEffect="copy";
        zone.classList.add("dropping");
      });
    });
    ["dragleave","dragend"].forEach(function(ev){
      zone.addEventListener(ev,function(){ zone.classList.remove("dropping"); });
    });
    zone.addEventListener("drop",function(e){
      if(!e.dataTransfer||!e.dataTransfer.files||!e.dataTransfer.files.length) return;
      e.preventDefault(); e.stopPropagation();
      zone.classList.remove("dropping");
      openFiles(e.dataTransfer.files);
    });
    window.addEventListener("dragover",function(e){
      if(e.dataTransfer&&Array.prototype.indexOf.call(e.dataTransfer.types||[],"Files")>=0)
        e.preventDefault();
    });
    window.addEventListener("drop",function(e){
      if(e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files.length) e.preventDefault();
    });
  })();

  // ============================ inline editing on the card ============================
  // The inspector remains the complete surface -- every field lives there. This covers the two
  // or three edits you reach for constantly (rename the instance, rename an exposure, retype
  // it) without crossing the window for each one. Double-click the text; Enter commits, Escape
  // cancels, blur commits. Read-only backings (subsystem, and a catalogue node's interfaces)
  // refuse, because those names belong to the referenced file, not to this one.
  function inlineEdit(el,value,opts,commit){
    if(!el||canvas.querySelector("[data-inline]")) return;      // one editor at a time
    opts=opts||{};
    var inp=document.createElement("input");
    inp.setAttribute("data-inline","1");
    inp.className="inline";
    inp.value=value==null?"":String(value);
    if(opts.list) inp.setAttribute("list",opts.list);
    if(opts.placeholder) inp.placeholder=opts.placeholder;
    // width in MODEL units: the card is inside the zoom transform, so a screen-space width
    // would shrink the box as you zoom out.
    var w=el.getBoundingClientRect().width/(view.k||1);
    inp.style.width=Math.round(Math.max(w,60)+28)+"px";
    el.parentNode.insertBefore(inp,el);
    el.style.display="none";
    var done=false;
    function finish(ok){
      if(done) return;
      done=true;
      var v=inp.value;
      if(inp.parentNode) inp.parentNode.removeChild(inp);
      el.style.display="";
      if(ok) commit(v); else render();
    }
    inp.addEventListener("keydown",function(e){
      // the canvas owns Ctrl+Z / Delete / arrow keys; while typing a name it must not.
      e.stopPropagation();
      if(e.key==="Enter"){e.preventDefault();finish(true);}
      else if(e.key==="Escape"){e.preventDefault();finish(false);}
    });
    inp.addEventListener("blur",function(){finish(true);});
    inp.addEventListener("pointerdown",function(e){e.stopPropagation();});
    inp.focus();
    inp.select();
  }

  function wireInline(){
    canvas.addEventListener("dblclick",function(ev){
      if(document.body.classList.contains("mode-view")) return;
      var nEl=ev.target.closest(".node");
      if(!nEl) return;
      var n=nodeById(nEl.dataset.n);
      if(!n||n.backing==="sub") return;          // declared in the referenced file
      var title=ev.target.closest(".ntitle");
      if(title){
        // the LABEL is this system's own instance name, editable whatever backs the node
        inlineEdit(title,n.label,{placeholder:"instance label"},function(v){
          v=v.trim();
          if(!v||v===n.label){render();return;}
          pushUndo("label:"+n.id);
          n.label=v;
          render();
          fillInspector();
        });
        return;
      }
      var row=ev.target.closest(".iface");
      if(!row) return;
      var f=ifaceById(n,row.dataset.i);
      if(!f||n.backing!=="hand") return;         // a catalogue artifact's names are its own
      var ty=ev.target.closest(".ity");
      if(ty){
        inlineEdit(ty,f.type||"",{list:"typelist",placeholder:"pkg/msg/Type"},function(v){
          v=v.trim();
          if(v===(f.type||"")){render();return;}
          pushUndo("itype:"+f.id);
          f.type=v||null;
          render();
          fillInspector();
        });
        return;
      }
      var nm=ev.target.closest(".inm");
      if(nm){
        inlineEdit(nm,f.name,{placeholder:"interface name"},function(v){
          v=v.trim();
          if(!v||v===f.name){render();return;}
          pushUndo("iname:"+f.id);
          f.name=v;
          render();
          fillInspector();
        });
      }
    });
  }

  // ============================ node drag ============================
  project.nodes.forEach(function(){});
  function wireCanvas(){
    canvas.addEventListener("pointerdown",function(ev){
      // The WHOLE card selects and drags, not just its title bar: a node is one object, and
      // having to hit a 20px strip to pick it up is the kind of thing you only forgive in
      // software you wrote yourself. Three exceptions, each of which owns its own gesture:
      // a port starts a wire, an inline editor is being typed into, and anything explicitly
      // marked interactive.
      if(ev.target.closest(".port")||ev.target.closest("[data-inline]")
         ||ev.target.closest("input,textarea,select,button")) return;
      var el=ev.target.closest(".node");
      if(!el) return;
      var n=nodeById(el.dataset.n);
      if(!n) return;
      // snapshot the pre-drag layout now; it is only pushed on pointerup if the pointer
      // actually moved, so selecting a node does not fill the undo stack with no-ops.
      dragState={n:n,px:ev.clientX,py:ev.clientY,ox:n.x,oy:n.y,moved:0,snap:snapshot()};
      try{el.setPointerCapture(ev.pointerId);}catch(e){}
    });
    canvas.addEventListener("pointermove",function(ev){
      if(!dragState) return;
      var k=view.k||1;
      var ddx=(ev.clientX-dragState.px)/k, ddy=(ev.clientY-dragState.py)/k;
      dragState.moved+=Math.abs(ddx)*k+Math.abs(ddy)*k;   // the click threshold is in PIXELS
      // never negative: the SVG wire layer starts at the canvas origin, so a node dragged
      // above/left of it would keep its box but lose its edges.
      dragState.n.x=Math.max(0,dragState.ox+ddx); dragState.n.y=Math.max(0,dragState.oy+ddy);
      var el=canvas.querySelector('.node[data-n="'+dragState.n.id+'"]');
      el.style.left=dragState.n.x+"px"; el.style.top=dragState.n.y+"px"; drawEdges();
    });
    canvas.addEventListener("pointerup",function(ev){
      if(!dragState) return;
      var wasClick=dragState.moved<5, n=dragState.n, snap=dragState.snap; dragState=null;
      if(wasClick){selNode=n.id;selEdge=null;render();fillInspector();}
      else {sizeCanvas();pushSnapshot(snap);}
    });
    // Background drag = PAN. It shares its pointerdown with "click empty space to deselect",
    // which is why the deselect only fires when the pointer did not travel: dragging the
    // canvas to look somewhere else is not a decision to drop the selection.
    canvas.addEventListener("pointerdown",function(ev){
      if(ev.target!==canvas&&ev.target!==svg) return;
      panState={px:ev.clientX,py:ev.clientY,tx:view.tx,ty:view.ty,moved:0};
      canvasWrap.classList.add("panning");
      try{canvas.setPointerCapture(ev.pointerId);}catch(e){}
    });
    canvas.addEventListener("pointermove",function(ev){
      if(!panState) return;
      var dx=ev.clientX-panState.px, dy=ev.clientY-panState.py;
      panState.moved+=Math.abs(dx)+Math.abs(dy);
      view.tx=panState.tx+dx; view.ty=panState.ty+dy; applyView();
    });
    canvas.addEventListener("pointerup",function(ev){
      if(!panState) return;
      var wasClick=panState.moved<5; panState=null;
      canvasWrap.classList.remove("panning");
      if(wasClick){selNode=null;selEdge=null;render();fillInspector();}
    });
    // connection drawing
    canvas.addEventListener("pointerdown",function(ev){
      if(mode!=="edit") return;
      var port=ev.target.closest(".port"); if(!port) return;
      ev.stopPropagation();
      var srcKind=port.dataset.kind, wantKind=COMPLEMENT[srcKind], srcType=port.dataset.type||"";
      wire={from:{n:port.dataset.n,i:port.dataset.i,kind:srcKind}};
      try{canvas.setPointerCapture(ev.pointerId);}catch(e){}
      canvas.querySelectorAll(".port").forEach(function(p){
        if(p===port) return;
        var tt=p.dataset.type||"";
        // both kinds must complement AND (when both types are known) they must match --
        // the server rejects a connection whose endpoints differ in type.
        var typeOk=(!srcType||!tt||srcType===tt);
        var legal=(p.dataset.kind===wantKind && p.dataset.n!==port.dataset.n && typeOk);
        p.classList.add(legal?"legal":"illegal");
      });
      var rb=document.createElementNS(NS,"path"); rb.setAttribute("class","rubber"); rb.id="rb"; svg.appendChild(rb);
    });
    canvas.addEventListener("pointermove",function(ev){
      if(!wire) return;
      var s=portCenter(wire.from.n,wire.from.i), cr=canvas.getBoundingClientRect(),
          k=view.k||1;
      var mx=(ev.clientX-cr.left)/k, my=(ev.clientY-cr.top)/k, rb=document.getElementById("rb");
      if(s&&rb) rb.setAttribute("d",STUDIO.bezier(s.x,s.y,mx,my));
    });
    canvas.addEventListener("pointerup",function(ev){
      if(!wire) return;
      var tgt=ev.target.closest(".port.legal");
      if(tgt){
        var a={n:wire.from.n,i:wire.from.i,kind:wire.from.kind};
        var bb={n:tgt.dataset.n,i:tgt.dataset.i,kind:tgt.dataset.kind};
        var fromEnd=SRC_SIDE[a.kind]?a:bb, toEnd=SRC_SIDE[a.kind]?bb:a;
        var dup=project.connections.some(function(c){return c.from.n===fromEnd.n&&c.from.i===fromEnd.i&&c.to.n===toEnd.n&&c.to.i===toEnd.i;});
        if(!dup){ pushUndo(); project.connections.push({id:nid(),from:{n:fromEnd.n,i:fromEnd.i},to:{n:toEnd.n,i:toEnd.i}}); }
      }
      wire=null;
      canvas.querySelectorAll(".port").forEach(function(p){p.classList.remove("legal","illegal");});
      var rb=document.getElementById("rb"); if(rb) rb.remove();
      render();
    });
  }
  var dragState=null, wire=null, panState=null;
  wireCanvas();
  wireInline();

  // ============================ wheel: pan, ctrl/pinch: zoom ============================
  // Trackpad semantics, and the only ones that work for both input devices: a two-finger
  // scroll arrives as a plain wheel event and pans; a pinch arrives as ctrlKey+wheel and
  // zooms at the pointer, which is also what Ctrl+wheel means on a mouse. preventDefault is
  // required for the ctrl case or the browser page-zooms instead.
  canvasWrap.addEventListener("wheel",function(ev){
    ev.preventDefault();
    if(ev.ctrlKey||ev.metaKey){
      var r=canvasWrap.getBoundingClientRect();
      zoomAt(ev.clientX-r.left, ev.clientY-r.top, Math.pow(0.99, ev.deltaY));
      return;
    }
    if(ev.shiftKey){ view.tx-=(ev.deltaX||ev.deltaY); }
    else { view.tx-=ev.deltaX; view.ty-=ev.deltaY; }
    applyView();
  },{passive:false});

  // ============================ find on canvas ============================
  // The catalogue modal has always had a search; the CANVAS had none, so on anything past a
  // handful of nodes "where is amcl" meant reading every box. Matches the label, the
  // package.node the file will spell, the namespace, and every interface name and type --
  // finding a node by the topic it publishes is the question that actually gets asked.
  var findQ="", findHits=[], findIdx=0;
  function findMatches(){
    var q=findQ.replace(/^\s+|\s+$/g,"").toLowerCase();
    if(!q) return [];
    var out=[];
    project.nodes.forEach(function(n){
      var hay=[n.label,(n.pkg||"")+"."+(n.node||""),n.namespace||""];
      (n.ifaces||[]).forEach(function(f){ hay.push(f.name); hay.push(f.type||""); });
      for(var i=0;i<hay.length;i++)
        if(String(hay[i]).toLowerCase().indexOf(q)>=0){ out.push(n.id); return; }
    });
    return out;
  }
  function applyFind(){
    findHits=findMatches();
    if(findIdx>=findHits.length) findIdx=0;
    var on=findHits.length>0, set={};
    findHits.forEach(function(id){set[id]=1;});
    [].slice.call(canvas.querySelectorAll(".node")).forEach(function(el){
      var id=el.dataset.n;
      el.classList.toggle("fdim", on&&!set[id]);
      el.classList.toggle("fhit", on&&!!set[id]);
      el.classList.toggle("fcur", on&&findHits[findIdx]===id);
    });
    var c=document.getElementById("findCount");
    if(c) c.textContent=findQ.replace(/^\s+|\s+$/g,"")
      ? (on?(findIdx+1)+"/"+findHits.length:"0/0") : "";
    var p=document.getElementById("findPrev"), n2=document.getElementById("findNext");
    if(p) p.disabled=!on; if(n2) n2.disabled=!on;
  }
  function findStep(delta){
    if(!findHits.length) return;
    findIdx=(findIdx+delta+findHits.length)%findHits.length;
    applyFind(); centreOn(findHits[findIdx]);
  }

  // ============================ auto layout ============================
  // Layered (Sugiyama-style), not force-directed: this graph is a directed dataflow, and a
  // reader's question is "what feeds what", which a left-to-right layering answers and a
  // force layout scrambles. Pure JS, no library -- the page is offline and self-contained.
  //
  // Sizes are MEASURED off the rendered nodes rather than estimated: a node's height is its
  // interface count, which varies by an order of magnitude across a real system, and stacking
  // by a guessed height is how a layout ends up with boxes on top of each other.
  function nodeBox(id){
    var el=canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(id)+'"]');
    if(el&&el.offsetWidth) return {w:el.offsetWidth,h:el.offsetHeight};
    var n=nodeById(id);
    return {w:200,h:56+22*((n&&n.ifaces&&n.ifaces.length)||0)};
  }
  function layeredPositions(){
    var ids=project.nodes.map(function(n){return n.id;});
    var idx={}; ids.forEach(function(id,i){idx[id]=i;});
    var succ={}, pred={}, degree={};
    ids.forEach(function(id){succ[id]=[];pred[id]=[];degree[id]=0;});
    project.connections.forEach(function(c){
      var a=c.from.n, b=c.to.n;
      if(!(a in succ)||!(b in succ)||a===b) return;
      succ[a].push(b); pred[b].push(a); degree[a]++; degree[b]++;
    });
    // Break cycles by DFS: an edge back to a vertex still on the stack is a back edge and is
    // ignored for LAYERING only (it is still drawn). A ROS graph has feedback loops -- a
    // controller subscribing to what it ultimately drives -- so a layering that refuses to
    // handle one would refuse most real systems.
    var colour={}, keep={};
    ids.forEach(function(id){colour[id]=0;});
    ids.forEach(function(root){
      if(colour[root]!==0) return;
      var stack=[{id:root,i:0}]; colour[root]=1;
      while(stack.length){
        var top=stack[stack.length-1];
        if(top.i>=succ[top.id].length){ colour[top.id]=2; stack.pop(); continue; }
        var nx=succ[top.id][top.i++];
        if(colour[nx]===1) continue;                 // back edge -> dropped from the DAG
        keep[top.id+""+nx]=1;
        if(colour[nx]===0){ colour[nx]=1; stack.push({id:nx,i:0}); }
      }
    });
    var dagSucc={}, indeg={};
    ids.forEach(function(id){dagSucc[id]=[];indeg[id]=0;});
    ids.forEach(function(a){
      succ[a].forEach(function(b){
        if(!keep[a+""+b]) return;
        dagSucc[a].push(b); indeg[b]++;
      });
    });
    // longest-path layering over the acyclic subgraph (Kahn, keeping the input order stable)
    var layer={}, queue=[];
    ids.forEach(function(id){ layer[id]=0; if(!indeg[id]) queue.push(id); });
    var seen=0;
    while(queue.length){
      var v=queue.shift(); seen++;
      dagSucc[v].forEach(function(w){
        if(layer[w]<layer[v]+1) layer[w]=layer[v]+1;
        if(--indeg[w]===0) queue.push(w);
      });
    }
    // Isolated nodes get their own trailing column: mixed into layer 0 they pad out the
    // sources and hide where the graph actually starts.
    var maxL=0; ids.forEach(function(id){ if(degree[id]&&layer[id]>maxL) maxL=layer[id]; });
    ids.forEach(function(id){ if(!degree[id]) layer[id]=maxL+1; });

    var layers=[];
    ids.forEach(function(id){ (layers[layer[id]]=layers[layer[id]]||[]).push(id); });
    for(var i=0;i<layers.length;i++) layers[i]=layers[i]||[];
    // Barycentre ordering, four sweeps. Crossings are what makes a layered drawing readable
    // or not, and the median/barycentre heuristic removes most of them for a few lines.
    var order={};
    layers.forEach(function(row){ row.forEach(function(id,i){ order[id]=i; }); });
    function sweep(useSucc){
      var seq=useSucc?layers.slice().reverse():layers;
      seq.forEach(function(row){
        var bary={};
        row.forEach(function(id,i){
          var nb=(useSucc?succ[id]:pred[id]).filter(function(o){return order[o]!=null;});
          var s=0;
          nb.forEach(function(o){ s+=order[o]; });
          bary[id]=nb.length?s/nb.length:order[id];
        });
        row.sort(function(a,b){ return (bary[a]-bary[b])||(idx[a]-idx[b]); });
        row.forEach(function(id,i){ order[id]=i; });
      });
    }
    for(var s2=0;s2<2;s2++){ sweep(false); sweep(true); }

    var GAPX=110, GAPY=30, X0=60, Y0=60, pos={}, colX=X0, heights=[];
    layers.forEach(function(row){
      var h=0;
      row.forEach(function(id,i){ h+=nodeBox(id).h+(i?GAPY:0); });
      heights.push(h);
    });
    var tallest=0; heights.forEach(function(h){ if(h>tallest) tallest=h; });
    layers.forEach(function(row,li){
      var wmax=0;
      row.forEach(function(id){ wmax=Math.max(wmax,nodeBox(id).w); });
      var y=Y0+(tallest-heights[li])/2;
      row.forEach(function(id){
        var b=nodeBox(id);
        pos[id]={x:Math.round(colX+(wmax-b.w)/2), y:Math.round(y)};
        y+=b.h+GAPY;
      });
      colX+=wmax+GAPX;
    });
    return pos;
  }
  function autoLayout(){
    var pos=layeredPositions();
    pushUndo();          // node x/y live in project.json, so a layout is an undoable EDIT
    project.nodes.forEach(function(n){
      var p=pos[n.id];
      if(p){ n.x=p.x; n.y=p.y; }
    });
    render(); fitView();
  }

  // ============================ qos editing ============================
  // QoS was seeded by parse_ros2 and emitted by _emit_qos long before it was editable, so a
  // seeded model could carry a QoS block the author could neither see nor repair. The
  // vocabulary and the severities below all come from DATA.qos, which ros_studio fills from
  // rosmodel_lint's own tables -- the control cannot offer a field the linter would reject.
  function qosVal(f,k){ return (f.qos&&f.qos[k]!=null)?String(f.qos[k]):""; }
  function qosCount(f){
    var c=0; if(!f.qos) return 0;
    QOS.fields.forEach(function(k){ if(f.qos[k]!=null&&f.qos[k]!=="") c++; });
    return c;
  }
  // RM035, mirrored at ENTRY time rather than after Commit. CheckDuration calls
  // Integer.parseInt on the value and the unit is NANOSECONDS, so the whole field tops out at
  // about 2.147 seconds -- every human-plausible timeout ("5000000000" = 5 s) is an ERROR.
  // Confirmed against the real validator, oracle case 14.
  function qosDurationProblem(v){
    v=String(v==null?"":v).trim();
    if(!v||v==="infinite") return null;
    if(!/^[+-]?[0-9]+$/.test(v))
      return "RM035 ERROR — Integer.parseInt rejects decimal points, underscores, exponents "
           + "and spaces. Use a bare integer of nanoseconds, or the keyword infinite.";
    var n=parseInt(v,10);
    if(n<QOS.int32Min||n>QOS.int32Max)
      return "RM035 ERROR — overflows signed 32-bit. The unit is NANOSECONDS, so ~2.147 s is "
           + "the longest expressible duration; the validator throws on this value. Use "
           + "infinite if you meant “no limit”.";
    return null;
  }
  function qosNote(k,v){
    v=String(v==null?"":v).trim();
    if(!v) return ["",""];
    if(QOS_DUR[k]){ var p=qosDurationProblem(v); if(p) return ["e",p]; }
    if(QOS_NEW[k]) return ["i","RM031 INFO — legal on the current server (verified), but a "
      +"consumer on a toolchain built before 2025-10-16 cannot even LEX this keyword."];
    if(QOS_DISC[k]) return ["w","RM034 — Corpus B suppresses this field. Keep it only if the "
      +"value came from the source; never invent one."];
    return ["",""];
  }
  function qosPanel(f){
    if(!qosOpen[f.id]) return "";
    var h='<div class="qosbox">';
    QOS.fields.forEach(function(k){
      var v=qosVal(f,k), note=qosNote(k,v);
      h+='<div class="qrow"><label>'+esc(k)+'</label>';
      if(QOS.enums[k]){
        h+='<select data-qk="'+k+'" data-qi="'+f.id+'"><option value=""'+(v?"":" selected")+'>—</option>'
          +QOS.enums[k].map(function(o){return '<option'+(o===v?" selected":"")+'>'+esc(o)+'</option>';}).join("")
          +'</select>';
      }else{
        h+='<input data-undo="1" data-qk="'+k+'" data-qi="'+f.id+'" value="'+esc(v)+'" placeholder="'
          +(QOS_DUR[k]?"nanoseconds, or infinite":(k==="depth"?"non-negative integer":""))+'">';
      }
      h+='</div><div class="qnote '+note[0]+'" data-qnote="'+k+'/'+f.id+'">'+esc(note[1])+'</div>';
    });
    h+='<div class="hint">blank clears a field; with nothing set, no qos: block is written.</div></div>';
    return h;
  }

  // ============================ comments ============================
  // Byte-parity with _clean_comment/_comment_list/_comment_block/_note_suffix in ros_studio.py.
  // `generate` used to emit only its own provenance lines, so every comment the author wrote was
  // deleted on the first edit cycle; these slots are where they live now, and they are EDITABLE
  // here because the point is to maintain them where you model, not to ferry them through.
  function cmtClean(s){ return String(s==null?"":s).replace(/[\r\n]+/g," ").replace(/\s+$/,""); }
  // A leading block, from a JSON array or a textarea. Interior blanks are the author's paragraph
  // breaks and are kept; leading/trailing ones go, so a textarea's final newline does not grow a
  // stray "#" on every keystroke.
  function cmtList(v){
    if(v==null) return [];
    var items=(Object.prototype.toString.call(v)==="[object Array]")?v:String(v).split("\n"), out=[];
    items.forEach(function(x){
      String(x==null?"":x).split("\n").forEach(function(y){ out.push(cmtClean(y)); });
    });
    while(out.length&&out[out.length-1]==="") out.pop();
    while(out.length&&out[0]==="") out.shift();
    return out;
  }
  function cmtOf(o,k){ var c=(o&&o.comments)||{}; return c[k]; }
  function cmtBlock(o,k,indent){
    return cmtList(cmtOf(o,k)).map(function(t){return indent+(t?"# "+t:"#")+"\n";}).join("");
  }
  // `auto` is the emitter's own provenance body (RM088/RM089). An authored comment REPLACES it
  // once it already names that file -- repeating the path teaches the reader nothing -- and
  // otherwise the provenance is kept with the authored text appended, so an edit cannot silently
  // delete the disclosure those two rules require.
  function noteSuffix(note,auto){
    note=cmtClean(note); auto=String(auto==null?"":auto).trim();
    if(!note) return auto?("  # "+auto):"";
    if(auto&&note.indexOf(auto.split("/").pop())<0) note=auto+" -- "+note;
    return "  # "+note;
  }
  // which slots hold a BLOCK of lines rather than one trailing comment: "header", "before",
  // "ros2Before". Matching on the suffix case-insensitively, because "before" and "ros2Before"
  // differ only in case and a `indexOf("Before")` test silently classed the plain "before"
  // slot -- the most-used one -- as single-line.
  function cmtMulti(k){ return k==="header"||/before$/i.test(k); }
  function cmtCount(o){
    var c=(o&&o.comments)||{}, n=0;
    for(var k in c){ if(cmtMulti(k)?cmtList(c[k]).length:cmtClean(c[k])) n++; }
    return n;
  }
  // slot -> the label says WHICH FILE the text lands in: one interface appears in both the
  // .rossystem and the .ros2, and its two comments there are different text.
  var CMT_FIELDS={
    node:[["before","block above the node (.rossystem)"],["line","trailing on the node line"],
          ["from","trailing on from:"],["ros2Before","block above the artifact (.ros2)"],
          ["ros2Line","trailing on the artifact line (.ros2)"]],
    iface:[["before","block above the exposure (.rossystem)"],["line","trailing on the exposure"],
           ["ros2Before","block above the interface (.ros2)"],
           ["ros2Line","trailing on the interface (.ros2)"],["ros2Type","trailing on type: (.ros2)"]],
    param:[["ros2Before","block above the parameter (.ros2)"],
           ["ros2Line","trailing on the parameter (.ros2)"]],
    conn:[["before","block above the connection (.rossystem)"],["line","trailing on the connection"]],
    system:[["header","file header block (.rossystem)"],["fromFile","trailing on fromFile:"]],
    sub:[["before","block above the subSystems: entry"],["line","trailing on the entry"]],
    pkg:[["header","file header block (.ros2)"]]
  };
  function cmtRows(o,kind,key){
    cmtReg[key]=o;
    return CMT_FIELDS[kind].map(function(fd){
      var multi=cmtMulti(fd[0]), v=cmtOf(o,fd[0]);
      var txt=multi?cmtList(v).join("\n"):cmtClean(v);
      var ctl=multi
        ? '<textarea data-undo="1" rows="'+Math.min(10,Math.max(2,txt.split("\n").length))
          +'" data-cmt="'+esc(key)+'" data-ck="'+fd[0]+'">'+esc(txt)+'</textarea>'
        : '<input data-undo="1" data-cmt="'+esc(key)+'" data-ck="'+fd[0]+'" value="'+esc(txt)+'">';
      return '<div class="crow"><label>'+esc(fd[1])+'</label>'+ctl+'</div>';
    }).join("");
  }
  function cmtPanel(o,kind,key){
    if(!cmtOpen[key]) return "";
    return '<div class="cmtbox">'+cmtRows(o,kind,key)
      +'<div class="hint">written as "# text"; a line break inside one becomes a space, since a '
      +'comment runs to end of line.</div></div>';
  }
  function cmtChip(o,key){
    var c=cmtCount(o);
    return '<span class="ctog'+(c?" set":"")+'" data-ctog="'+esc(key)+'" title="comments carried '
      +'into the generated files">cmt'+(c?"·"+c:"")+'</span>';
  }
  function wireComments(){
    inspector.querySelectorAll("[data-ctog]").forEach(function(x){x.onclick=function(){
      var k=x.dataset.ctog; cmtOpen[k]=!cmtOpen[k]; fillInspector();};});
    inspector.querySelectorAll("[data-cmt]").forEach(function(x){x.oninput=function(){
      var o=cmtReg[x.dataset.cmt]; if(!o) return;
      var k=x.dataset.ck;
      pushUndo("cmt:"+x.dataset.cmt+":"+k);
      if(!o.comments) o.comments={};
      var v=cmtMulti(k)?cmtList(x.value):cmtClean(x.value);
      if(cmtMulti(k)?!v.length:!v) delete o.comments[k]; else o.comments[k]=v;
      // an empty object would be written into project.json and read back as "has comments";
      // drop the key so a cleared slot is indistinguishable from one that never existed.
      if(!Object.keys(o.comments).length) delete o.comments;
      var tog=inspector.querySelector('[data-ctog="'+STUDIO.cssEsc(x.dataset.cmt)+'"]');
      if(tog){ var c=cmtCount(o); tog.className="ctog"+(c?" set":""); tog.textContent="cmt"+(c?"·"+c:""); }
    };});
  }

  // ============================ inspector ============================
  function fillInspector(){
    cmtReg={};                       // the panel is rebuilt from scratch; so is its registry
    if(selEdge){ return fillEdgeInspector(); }
    var n=selNode&&nodeById(selNode);
    if(!n) return fillSystemInspector();
    inspector.className="inspector";
    if(mode!=="edit"){ return fillReadonlyNode(n); }
    // A subSystems: node belongs to the REFERENCED file. Editing it here would be a lie: its
    // label, from: and interfaces are never written by this project, and deleting it would strip
    // the connections that name it while the subSystems: line still claimed to provide it.
    if(n.backing==="sub"){ return fillSubsystemNode(n); }
    var cat=n.backing==="cat";
    var ih='<div class="insec"><h4>node: '+esc(n.label)+'</h4>'
      +'<div class="fld"><label>label (rossystem instance)</label><input id="f_label" data-undo="1" value="'+esc(n.label)+'"></div>'
      +'<div class="fld"><label>backing</label><div class="radio">'
      +'<label><input type="radio" name="bk" value="hand" '+(cat?"":"checked")+'> hand-authored</label>'
      +'<label><input type="radio" name="bk" value="cat" '+(cat?"checked":"")+'> catalogue</label></div></div>'
      +'<div class="fld"><label>package '+(cat?"":"(lowercase — uppercase is an ERROR)")+'</label><input id="f_pkg" data-undo="1" list="pkglist" value="'+esc(n.pkg)+'" '+(cat?"disabled":"")+'></div>'
      +'<div class="fld"><label>node</label><input id="f_node" data-undo="1" value="'+esc(n.node)+'" '+(cat?"disabled":"")+'></div>'
      +'<div class="fld"><label>artifact (arrow target base)</label><input id="f_art" data-undo="1" list="artlist" value="'+esc(n.artifact||"")+'" '+(cat?"disabled":"")+'></div>'
      // namespace is a property of the node INSTANCE in the system, not of the backing
      // artifact, so it is editable for catalogue nodes too. Blank = omit the key.
      +'<div class="fld"><label>namespace (optional)</label><input id="f_ns" data-undo="1" list="nslist" value="'+esc(n.namespace||"")+'" placeholder="e.g. /robot1">'
      +((n.namespace&&String(n.namespace).trim())
        ?'<div class="hint w">emitted between from: and interfaces:. 0 of 52 corpus files use it — rosmodel_lint warns (RM044); the 3.1.0 server accepts it.</div>'
        :'<div class="hint">set this to scope the node in a multi-robot system.</div>')+'</div>'
      +'<div class="fld"><label>from: (derived)</label><div class="derived">"'+esc(n.pkg)+'.'+esc(n.node)+'"</div></div></div>';
    ih+='<div class="insec"><h4>interfaces</h4>';
    for(var j=0;j<n.ifaces.length;j++){var f=n.ifaces[j];
      var conn=ifaceConnected(n,f);
      ih+='<div class="iedit'+(f.orphan?" orphan":"")+'" data-i="'+f.id+'"><span class="kd '+f.kind+'" title="'+KIND_LABEL[f.kind]+'">'+f.kind+'</span>'
        +'<span class="grow"><span class="inm2">'+esc(f.name)+'</span><br><span class="ity2">'+esc(f.type||"—")+' · "'+esc(n.artifact||"")+'::'+esc(f.name)+'"</span>'
        +'<span class="lblrow"><input class="ilbl" data-undo="1" data-lbl="'+f.id+'" value="'+esc(f.label||"")+'" placeholder="'+esc(f.name)+'" title="exposure label — the key written into the .rossystem. Blank derives it from the interface name.">'
        +'<label class="expchk" title="'+(conn?"connected — always exposed":"write this interface into the .rossystem even with nothing wired to it")+'">'
        +'<input type="checkbox" data-exp="'+f.id+'"'+((f.exposed||conn)?" checked":"")+(conn?" disabled":"")+'>expose</label>'
        +'<span class="qtog'+(qosCount(f)?" set":"")+'" data-qtog="'+f.id+'" title="quality of service — written into the .ros2, not the .rossystem">qos'+(qosCount(f)?"·"+qosCount(f):"")+'</span>'
        +cmtChip(f,"i:"+f.id)
        +'</span></span>'
        +'<span class="del" data-del="'+f.id+'">✕</span></div>'
        +qosPanel(f)+cmtPanel(f,"iface","i:"+f.id);
    }
    ih+='<div class="addform"><div class="kseg" id="kseg">'+KINDS.map(function(k){return '<button data-k="'+k+'" class="'+(k===addKind?"on":"")+'">'+k+'</button>';}).join("")+'</div>'
      +'<input id="ni_name" placeholder="interface name (quoted for you)">'
      +'<input id="ni_type" list="typelist" placeholder="type e.g. std_msgs/msg/String">'
      +'<div class="typestate" id="ni_ts"></div>'
      +'<button class="minibtn" id="ni_add">+ add interface</button></div></div>';
    ih+='<div class="insec"><h4>parameters</h4>';
    for(var p=0;p<n.params.length;p++){var pp=n.params[p];
      ih+='<div class="iedit"><span class="kd" style="background:var(--k-param)">'+(pp.ptype||"Str").slice(0,3)+'</span>'
        +'<span class="grow"><span class="inm2">'+esc(pp.name)+'</span> <span class="ity2">= '+esc(String(pp.value))+'</span></span>'
        +cmtChip(pp,"p:"+pp.id)
        +'<span class="del" data-delp="'+pp.id+'">✕</span></div>'+cmtPanel(pp,"param","p:"+pp.id);
    }
    ih+='<div class="addform"><input id="np_name" placeholder="param name">'
      +'<select id="np_type"><option>Integer</option><option>Double</option><option>String</option><option>Boolean</option></select>'
      +'<input id="np_val" placeholder="value (typed-safe: no True/int traps)">'
      +'<button class="minibtn" id="np_add">+ add parameter</button></div></div>';
    // the node's own comments, always open: a leading block is the one an author reaches for
    // most and hiding it behind a chip would keep it out of sight in exactly the file it
    // documents.
    ih+='<div class="insec"><h4>comments</h4>'+cmtRows(n,"node","n:"+n.id)
      +'<div class="hint">re-emitted at these positions on generate; everything else is '
      +'reported by <code>init</code> and dropped.</div></div>';
    ih+='<button class="delnode" id="delNode">Delete node</button>';
    inspector.innerHTML=ih;
    wireInspector(n);
  }
  // fromFile is a SYSTEM member and fromGitRepo a PACKAGE member, so neither has a node to
  // hang off; both were seeded and emitted with no way to edit them, which meant every
  // from-scratch project shipped without fromFile and took an RM053 warning. The inspector's
  // idle state (nothing selected) is where they live now.
  function handPackages(){
    var seen={}, out=[];
    project.nodes.forEach(function(n){
      if(n.backing==="hand"&&n.pkg&&!seen[n.pkg]){ seen[n.pkg]=1; out.push(n.pkg); }
    });
    return out.sort();
  }
  // ============================ .ros message types ============================
  // A companion .ros used to be generated from type NAMES alone, so a type invented here came
  // out as a spec with an empty body -- legal (RM080 INFO) but silent data loss whenever the
  // author knew the fields. These are the entry-time notes for a field row, mirroring
  // rosmodel_lint's check_ros_field_type / check_ros_field_name. Advisory only: nothing here
  // is ever emitted, so it needs no byte-parity with Python -- what it must not do is disagree
  // with the checker about which value is legal.
  var RE_MA_ATOM='(?:[A-Za-z_][A-Za-z_0-9]*|"[^"]*"|\'[^\']*\')';
  var RE_MSG_ASSIGN=new RegExp("^"+RE_MA_ATOM+"=(?:"+RE_MA_ATOM+"|-?[0-9]+)$");
  var RE_XID=/^[A-Za-z_][A-Za-z_0-9]*$/;
  var RE_QNAME=/^[A-Za-z_][A-Za-z_0-9]*\/(msg|srv|action)\/[A-Za-z_][A-Za-z_0-9]*$/;

  function trim(s){ return String(s==null?"":s).replace(/^\s+|\s+$/g,""); }

  function rosTypeNote(tok,known){
    tok=trim(tok);
    if(!tok) return ["e","a MessagePart is exactly two tokens, a Type then a name."];
    if(ROSPRIM[tok]) return ["",""];
    if(/\[\s*[0-9]+\s*\]$/.test(tok)||/<=[0-9]+$/.test(tok))
      return ["e","fixed- and bounded-size arrays have no production at all (RM075) — the "
        +"grammar hard-codes the literal '[]'. The oracle fails to LEX 'float32[3]', so the "
        +"whole file stops parsing. Emit the unbounded form and note the lost bound."];
    if(/^(time|duration|Header)\[\]$/.test(tok))
      return ["e","'"+tok+"' has no array form (RM074) — AbstractType lists exactly fourteen "
        +"*Array rules and this is not among them. Only these take '[]': "
        +(ROS.arrays||[]).map(function(t){return t.slice(0,-2);}).join(", ")+"."];
    var base=/\[\]$/.test(tok)?tok.slice(0,-2):tok;
    var q=base.length>=2&&base.charAt(0)===base.charAt(base.length-1)
          &&(base.charAt(0)==='"'||base.charAt(0)==="'");
    if(!q)
      return ["e","unknown type '"+tok+"' (RM074). A bare name can NEVER resolve — every spec "
        +"is qualified '<pkg>/msg/<Name>', which contains '/' and no Xtext ID can spell it, "
        +"even for a type in the same package. Write '\""+tok+"\"' fully qualified, or use a "
        +"primitive: "+(ROS.scalars||[]).join(", ")+"."];
    var inner=base.slice(1,-1);
    if(!RE_QNAME.test(inner))
      return ["w","'"+inner+"' is not '<package>/<msg|srv|action>/<Type>' (RM076) — RosQNP "
        +"names every spec that way and nothing else links."];
    if(TYPEFILES[inner]) return ["","assets/roscommonobjects/"+TYPEFILES[inner]];
    if(known[inner]) return ["","defined in this project"];
    return ["w","'"+inner+"' is defined neither here nor in the vendored catalogue — "
      +"generation is refused until it is (\"Couldn't resolve reference to TopicSpec\")."];
  }

  function rosNameNote(tok){
    tok=trim(tok);
    if(!tok) return ["e","a MessagePart is exactly two tokens, a Type then a name."];
    if(ROSKW[tok]||RE_MSG_ASSIGN.test(tok)||RE_XID.test(tok)) return ["",""];
    if(tok.indexOf("=")>=0)
      return ["e","a constant is ONE token: no whitespace around '=' (MESSAGE_ASIGMENT, "
        +"Basics.xtext:206-208). Write 'FAN_OFF=0'; 'FAN_OFF = 0' lexes as three tokens."];
    return ["e","'"+tok+"' is not a legal Data token (RM077) — an unquoted name must be an "
      +"Xtext ID ([A-Za-z_][A-Za-z_0-9]*); '.', '-' and '/' need quoting."];
  }

  // every spec a companion .ros will declare, as its qualified name -- the set a field's spec
  // reference can resolve against without the catalogue.
  function definedTypeKeys(){
    var out={}, ct=companionTypes();
    Object.keys(ct).forEach(function(p){
      Object.keys(ct[p]).forEach(function(b){
        Object.keys(ct[p][b]).forEach(function(n){ out[p+"/"+ROSSEG[b]+"/"+n]=1; });
      });
    });
    return out;
  }
  function fieldList(key,body){
    var t=project.types[key]=(project.types[key]||{fields:{}});
    t.fields=t.fields||{};
    t.fields[body]=t.fields[body]||[];
    return t.fields[body];
  }

  function typesSection(edit){
    var known=definedTypeKeys(), ct=companionTypes();
    var files=Object.keys(ct).sort(), keys=Object.keys(project.types||{}).sort();
    var h='<div class="insec"><h4>message types (.ros)</h4>';
    h+='<div class="roinfo">'+(files.length
        ? esc(files.map(function(p){return p+".ros";}).join(", "))
        : "no companion .ros — every referenced type resolves in the vendored catalogue")
      +'</div>';
    var bodiless=[];
    Object.keys(known).forEach(function(k){ if(!project.types[k]) bodiless.push(k); });
    if(bodiless.length)
      h+='<div class="hint w">'+bodiless.length+' referenced type(s) carry no field definition '
        +'and are written with an empty body — legal (RM080) but silent loss if you know the '
        +'fields: '+esc(bodiless.sort().join(", "))+'</div>';
    keys.forEach(function(key){
      var p=String(key).split("/"), block=(p.length===3)?SEGBLOCK[p[1]]:null;
      h+='<div class="pkgrow"><div class="pn">'+esc(key)+'</div>';
      if(!block){
        h+='<div class="hint w">not &lt;package&gt;/&lt;msg|srv|action&gt;/&lt;Name&gt; — the '
          +'only shape a spec\'s qualified name takes; generation is refused.</div></div>';
        return;
      }
      if(CATPKG[p[0]])
        h+='<div class="hint w">\''+esc(p[0])+'\' is a package the vendored catalogue owns, so '
          +'this .ros and the staged catalogue file would both declare it (RM009). Generation '
          +'is refused — rename the package.</div>';
      (ROS.bodies[block]||[]).forEach(function(body){
        var rows=((project.types[key]||{}).fields||{})[body]||[];
        h+='<div class="fld"><label>'+esc(body)+(rows.length?"":" (no fields)")+'</label>';
        rows.forEach(function(f,i){
          if(!edit){
            h+='<div class="derived">'+esc(trim(f.type)+" "+trim(f.name))+'</div>';
            return;
          }
          var tn=rosTypeNote(f.type,known), nn=rosNameNote(f.name);
          var tag=esc(key)+"|"+body+"|"+i;
          h+='<div class="frow">'
            +'<input data-ft="'+tag+'" data-undo="1" list="ftypelist" placeholder="float32" '
            +'value="'+esc(f.type||"")+'">'
            +'<input data-fn="'+tag+'" data-undo="1" placeholder="x — or FAN_OFF=0" '
            +'value="'+esc(f.name||"")+'">'
            +'<button data-fdel="'+tag+'" title="remove this field">×</button></div>'
            +'<div class="fnote '+(tn[0]||nn[0])+'">'+esc(tn[1]||nn[1])+'</div>';
        });
        if(edit) h+='<button class="minibtn" data-fadd="'+esc(key)+'|'+body+'">+ field</button>';
        h+='</div>';
      });
      if(edit) h+='<button class="delnode" data-tdel="'+esc(key)+'">Delete '+esc(key)+'</button>';
      h+='</div>';
    });
    if(edit)
      h+='<div class="addform"><input id="nt_key" placeholder="my_msgs/msg/Reading">'
        +'<button class="minibtn" id="ntAdd">Define message type</button>'
        +'<div class="hint" id="nt_msg">A srv gets request + response, an action goal + result '
        +'+ feedback — the keyword is mandatory even with no fields. Reference another spec by '
        +'its QUOTED qualified name, "my_msgs/msg/Reading", including one in this same package: '
        +'there is no short form.</div></div>';
    return h+'</div>';
  }

  function wireTypes(){
    inspector.querySelectorAll("[data-ft],[data-fn]").forEach(function(x){
      var isType=!!x.dataset.ft, ref=(x.dataset.ft||x.dataset.fn).split("|");
      x.oninput=function(){
        // text coalesces on a per-field tag, so a typed word is one undo entry
        pushUndo("rosfield:"+(x.dataset.ft||x.dataset.fn)+(isType?":t":":n"));
        var row=fieldList(ref[0],ref[1])[+ref[2]];
        if(!row) return;
        row[isType?"type":"name"]=x.value;
        // the note sits immediately after the row; updating it in place rather than
        // re-rendering the panel is what keeps the caret where the author put it
        var note=x.parentNode.nextElementSibling, known=definedTypeKeys();
        if(note&&/(^|\s)fnote(\s|$)/.test(note.className)){
          var tn=rosTypeNote(row.type,known), nn=rosNameNote(row.name);
          note.className="fnote "+(tn[0]||nn[0]);
          note.textContent=tn[1]||nn[1];
        }
        runIssues();
      };
    });
    inspector.querySelectorAll("[data-fadd]").forEach(function(x){x.onclick=function(){
      var p=x.dataset.fadd.split("|");
      pushUndo(); fieldList(p[0],p[1]).push({type:"",name:""}); fillSystemInspector();};});
    inspector.querySelectorAll("[data-fdel]").forEach(function(x){x.onclick=function(){
      var p=x.dataset.fdel.split("|");
      pushUndo(); fieldList(p[0],p[1]).splice(+p[2],1); fillSystemInspector(); runIssues();};});
    inspector.querySelectorAll("[data-tdel]").forEach(function(x){x.onclick=function(){
      pushUndo(); delete project.types[x.dataset.tdel]; fillSystemInspector(); runIssues();};});
    var add=document.getElementById("ntAdd");
    if(add) add.onclick=function(){
      var msg=document.getElementById("nt_msg");
      var key=trim(document.getElementById("nt_key").value), p=key.split("/");
      var block=(p.length===3&&p[0]&&p[2])?SEGBLOCK[p[1]]:null;
      function refuse(text){ msg.className="hint w"; msg.textContent=text; }
      if(!block) return refuse("Write it as <package>/<msg|srv|action>/<Name> — RosQNP.xtend "
        +"qualifies every spec that way and no other shape can link.");
      if(CATPKG[p[0]]) return refuse("'"+p[0]+"' is a package the vendored catalogue owns; "
        +"defining a spec there would collide with the staged catalogue file (RM009).");
      if(TYPEFILES[key]) return refuse("'"+key+"' is already defined by the vendored catalogue "
        +"(assets/roscommonobjects/"+TYPEFILES[key]+") — reference it, do not redefine it.");
      if(project.types[key]) return refuse("'"+key+"' is already defined in this project.");
      pushUndo();
      (ROS.bodies[block]||[]).forEach(function(b){ fieldList(key,b); });
      fillSystemInspector(); runIssues();
    };
  }

  function fillSystemInspector(){
    inspector.className="inspector syspanel";
    var ff=(project.system&&project.system.fromFile)||"", pkgs=handPackages(), edit=(mode==="edit");
    var h='<div class="insec"><h4>system</h4>';
    if(edit){
      h+='<div class="fld"><label>fromFile (the launch file this system stands for)</label>'
        +'<input id="f_fromfile" data-undo="1" value="'+esc(ff)+'" placeholder="pkg/launch/bringup.launch.py">'
        // STATUS.md sec 4 / N3 claimed omitting fromFile makes the validator NPE. Re-probed
        // against the rebuilt 3.1.0 server on 2026-08-13: ACCEPTED, 0 errors, 0 warnings. So
        // this is a lint warning, not a crash -- do NOT fabricate a path to dodge it.
        +(ff?'<div class="hint">written as the first line of the .rossystem.</div>'
            :'<div class="hint w">absent — rosmodel_lint warns (RM053). The current 3.1.0 '
             +'server ACCEPTS a system without it (re-verified), so leave it blank rather '
             +'than inventing a path you do not have.</div>')
        +'</div>';
    }else{
      h+='<div class="fld"><label>fromFile</label><div class="derived">'+esc(ff||"(absent)")+'</div></div>';
    }
    var own=project.nodes.filter(function(n){return n.backing!=="sub";}).length;
    h+='<div class="fld"><label>contents</label><div class="derived">'+own
      +' node(s)'+((project.nodes.length-own)?(' + '+(project.nodes.length-own)+' via subSystems:'):'')
      +' · '+project.connections.length+' connection(s)</div></div>';
    // the .rossystem file header lives on the PROJECT, not on any node, so this panel is the
    // only place it can be edited -- and on the TurtleBot 3 example it is 40 lines of the
    // author's reasoning, which `generate` used to delete outright.
    if(edit) h+=cmtRows(project,"system","sys");
    h+='</div>';

    // subSystems: is reference-only -- the entries come from the seeded file and there is no UI
    // to invent one, because a reference that resolves to nothing exposes nothing connectable
    // (RM091) and the studio has no way to check a name the author types. Their comments ARE
    // editable: on the TurtleBot 3 example the single entry carries the line naming exactly
    // which catalogue file it resolves to and which nodes it brings in.
    var subs=project.subSystems||[];
    if(subs.length){
      h+='<div class="insec"><h4>subsystems (reused compositions)</h4>';
      subs.forEach(function(s,i){
        var got=project.nodes.filter(function(n){return n.backing==="sub"&&n.subRef===s.ref;});
        h+='<div class="pkgrow"><div class="pn">"'+esc(s.ref)+'"</div>'
          +'<div class="roinfo">'+esc(s.file?("assets/rosmodelscatalog/"+s.file):"(not in the vendored catalogue)")
          +'<br>'+got.length+' node(s) reached: '+esc(got.map(function(n){return n.label;}).join(", ")||"none")+'</div>'
          +(edit?cmtRows(s,"sub","sub:"+i):"")+'</div>';
      });
      h+='</div>';
    }

    h+='<div class="insec"><h4>packages (.ros2)</h4>';
    if(!pkgs.length) h+='<div class="roinfo">No hand-authored package yet — catalogue nodes '
      +'reference a vendored .ros2 and generate none.</div>';
    pkgs.forEach(function(p){
      // the package entry is derived from the nodes, so it may not exist yet -- and the .ros2
      // file header has nowhere else to hang.
      var entry=project.packages[p]=(project.packages[p]||{});
      var git=entry.fromGitRepo||"";
      h+='<div class="pkgrow"><div class="pn">'+esc(p)+'.ros2</div>'
        +(edit?'<input data-git="'+esc(p)+'" data-undo="1" value="'+esc(git)
               +'" placeholder="fromGitRepo — https://github.com/org/repo/">'
               +cmtRows(entry,"pkg","pkg:"+p)
              :'<div class="derived">'+esc(git||"(no fromGitRepo)")+'</div>')
        +'</div>';
    });
    h+='</div>'+typesSection(edit)
      +'<div class="insec"><h4>selection</h4><div class="roinfo">Select a node to '
      +(edit?'edit it, or add one from the rail':'inspect it')+'.</div></div>';
    inspector.innerHTML=h;

    var ffi=document.getElementById("f_fromfile");
    if(ffi) ffi.oninput=function(e){
      pushUndo("fromfile");
      project.system.fromFile=e.target.value.trim()||null;
      runIssues();};
    inspector.querySelectorAll("[data-git]").forEach(function(x){x.oninput=function(){
      var p=x.dataset.git;
      pushUndo("git:"+p);
      if(!project.packages[p]) project.packages[p]={};
      project.packages[p].fromGitRepo=x.value.trim()||null;};});
    wireTypes();
    wireComments();
  }
  // A node reached through subSystems:. Read-only by construction -- what it exposes is decided
  // by the referenced file's OWN interfaces: block, never by the .ros2 its from: points at
  // (checkIfInterfaceInSystem, RosSystemValidator.xtend:87-109). Its interfaces are still listed
  // and still connectable on the canvas: that is the entire point of the reference.
  function fillSubsystemNode(n){
    var sub=null;
    (project.subSystems||[]).forEach(function(s){ if(s.ref===n.subRef) sub=s; });
    var rows=n.ifaces.map(function(f){
      return f.kind+"  "+f.name+(f.type?"  "+f.type:"")
        +(ifaceConnected(n,f)?"   (connected)":"");}).join("\n")||"(none)";
    inspector.innerHTML='<div class="insec"><h4>node: '+esc(n.label)+'</h4>'
      +'<div class="roinfo">via subSystems: "'+esc(n.subRef||"")+'"'
      +((sub&&sub.file)?'<br>'+esc("assets/rosmodelscatalog/"+sub.file):'')
      +'<br>from: "'+esc(n.pkg)+'.'+esc(n.node)+'"</div>'
      +'<div class="hint">read-only: this node is declared in the referenced system, not here. '
      +'Edit it there, or drop the subSystems: entry and declare it under this file\'s own '
      +'nodes: instead — declaring it in both is RM090.</div></div>'
      +'<div class="insec"><h4>interfaces (from the referenced system)</h4>'
      +'<pre class="roinfo" style="white-space:pre-wrap">'+esc(rows)+'</pre>'
      +'<div class="hint">a connections: endpoint spells these names verbatim; they are not '
      +'re-labelled here.</div></div>';
  }
  function fillReadonlyNode(n){
    var rows=n.ifaces.map(function(f){
      var q=qosCount(f)?("  qos["+QOS.fields.filter(function(k){return f.qos[k]!=null&&f.qos[k]!=="";})
                                            .map(function(k){return k+"="+f.qos[k];}).join(" ")+"]"):"";
      return f.kind+"  "+f.name+(f.type?"  "+f.type:"")+q;}).join("\n")||"(none)";
    var pr=n.params.map(function(p){return p.name+" : "+p.ptype+" = "+p.value;}).join("\n")||"(none)";
    // View mode is read-only, but a comment the author wrote is model content: showing it here
    // means switching to View does not make it look as if the file has none.
    var cm=cmtBlock(n,"before","")+CMT_FIELDS.node.slice(1).map(function(fd){
      var v=cmtMulti(fd[0])?cmtList(cmtOf(n,fd[0])).join("\n"):cmtClean(cmtOf(n,fd[0]));
      return v?(fd[1]+": "+v+"\n"):"";}).join("");
    inspector.innerHTML='<div class="insec"><h4>node: '+esc(n.label)+'</h4>'
      +'<div class="roinfo">from: "'+esc(n.pkg)+'.'+esc(n.node)+'"'
      +((n.namespace&&String(n.namespace).trim())?'<br>namespace: '+esc(n.namespace):'')
      +'<br>backing: '+n.backing+'<br>artifact: '+esc(n.artifact||"")+'</div></div>'
      +'<div class="insec"><h4>interfaces</h4><pre class="roinfo" style="white-space:pre-wrap">'+esc(rows)+'</pre></div>'
      +'<div class="insec"><h4>parameters</h4><pre class="roinfo" style="white-space:pre-wrap">'+esc(pr)+'</pre></div>'
      +(cm?'<div class="insec"><h4>comments</h4><pre class="roinfo" style="white-space:pre-wrap">'+esc(cm)+'</pre></div>':'')
      +((DIAG[n.id]&&DIAG[n.id].length)?'<div class="insec"><h4>diagnostics</h4><pre class="roinfo" style="white-space:pre-wrap;color:var(--dead)">'+esc(DIAG[n.id].join("\n"))+'</pre></div>':'');
  }
  function fillEdgeInspector(){
    var c=null; for(var i=0;i<project.connections.length;i++)if(project.connections[i].id===selEdge)c=project.connections[i];
    if(!c){selEdge=null;return fillInspector();}
    var a=ifaceById(nodeById(c.from.n),c.from.i), bb=ifaceById(nodeById(c.to.n),c.to.i);
    if(!a||!bb){selEdge=null;return fillInspector();}
    var pair=PAIR_TOPIC[a.kind]?"Topic (one-way)":"Service/Action (request ⇄ response)";
    inspector.className="inspector";
    var h='<div class="insec"><h4>connection</h4>'
      +'<div class="fld"><label>kind</label><div class="derived">'+pair+'</div></div>'
      +'<div class="fld"><label>from (server/publisher)</label><div class="derived">'+esc(nodeById(c.from.n).label)+' · '+esc(a.name)+' ('+a.kind+')</div></div>'
      +'<div class="fld"><label>to (client/subscriber)</label><div class="derived">'+esc(nodeById(c.to.n).label)+' · '+esc(bb.name)+' ('+bb.kind+')</div></div>';
    h+='</div>';
    // a connection has no name of its own, so its comment is keyed by the LABEL PAIR both here
    // and in emit_rossystem -- which is why it has to be editable from the edge, not the node.
    if(mode==="edit") h+='<div class="insec"><h4>comments</h4>'+cmtRows(c,"conn","c:"+c.id)
      +'</div><button class="delnode" id="delEdge">Delete connection</button>';
    inspector.innerHTML=h;
    wireComments();
    var de=document.getElementById("delEdge");
    if(de) de.onclick=function(){pushUndo();project.connections=project.connections.filter(function(x){return x.id!==c.id;});selEdge=null;render();fillInspector();};
  }
  function wireInspector(n){
    // Text fields coalesce on a per-field tag, so a typed word is one undo entry, not one per
    // character; every other control here is a discrete action and pushes unconditionally.
    document.getElementById("f_label").oninput=function(e){pushUndo("label:"+n.id);n.label=e.target.value;render();};
    var pkg=document.getElementById("f_pkg"), nod=document.getElementById("f_node"), art=document.getElementById("f_art");
    if(pkg) pkg.oninput=function(e){pushUndo("pkg:"+n.id);n.pkg=e.target.value.toLowerCase();e.target.value=n.pkg;render();};
    if(nod) nod.oninput=function(e){pushUndo("node:"+n.id);n.node=e.target.value;render();};
    if(art) art.oninput=function(e){pushUndo("art:"+n.id);n.artifact=e.target.value;fillNsList();render();};
    var ns=document.getElementById("f_ns");
    // no fillInspector() here: the RM044 hint under the field only changes between "set" and
    // "unset", and rebuilding the panel mid-word would cost the caret. render() repaints the
    // node card (which shows the namespace) and re-runs the instant checks.
    if(ns) ns.oninput=function(e){pushUndo("ns:"+n.id);n.namespace=e.target.value.trim()||null;fillNsList();render();};
    inspector.querySelectorAll("[data-qtog]").forEach(function(x){x.onclick=function(){
      var id=x.dataset.qtog; qosOpen[id]=!qosOpen[id]; fillInspector();};});
    inspector.querySelectorAll("[data-qk]").forEach(function(x){
      var apply=function(){
        var f=ifaceById(n,x.dataset.qi); if(!f) return;
        var k=x.dataset.qk, v=String(x.value).trim();
        pushUndo("qos:"+f.id+":"+k);
        if(!f.qos) f.qos={};
        if(v==="") delete f.qos[k]; else f.qos[k]=v;
        if(!qosCount(f)) f.qos=null;
        var note=qosNote(k,v);
        var el=inspector.querySelector('[data-qnote="'+STUDIO.cssEsc(k+"/"+f.id)+'"]');
        if(el){ el.className="qnote "+note[0]; el.textContent=note[1]; }
        var tog=inspector.querySelector('[data-qtog="'+STUDIO.cssEsc(f.id)+'"]');
        if(tog){ var c=qosCount(f); tog.className="qtog"+(c?" set":""); tog.textContent="qos"+(c?"·"+c:""); }
        render();
      };
      if(x.tagName==="SELECT") x.onchange=apply; else x.oninput=apply;
    });
    inspector.querySelectorAll("[name=bk]").forEach(function(r){r.onchange=function(e){pushUndo();n.backing=e.target.value;render();fillInspector();};});
    inspector.querySelectorAll("[data-del]").forEach(function(x){x.onclick=function(){
      pushUndo();
      var id=x.dataset.del; n.ifaces=n.ifaces.filter(function(f){return f.id!==id;});
      project.connections=project.connections.filter(function(c){return !((c.from.n===n.id&&c.from.i===id)||(c.to.n===n.id&&c.to.i===id));});
      render();fillInspector();};});
    inspector.querySelectorAll("[data-delp]").forEach(function(x){x.onclick=function(){pushUndo();n.params=n.params.filter(function(p){return p.id!==x.dataset.delp;});render();fillInspector();};});
    inspector.querySelectorAll("[data-lbl]").forEach(function(x){x.oninput=function(){
      var f=ifaceById(n,x.dataset.lbl); if(!f) return;
      pushUndo("ilbl:"+f.id);
      f.label=x.value.trim()||null;    // NOT a repair for `orphan` -- that is about the arrow
      render();};});                   // TARGET (f.name), which the backing artifact must declare
    inspector.querySelectorAll("[data-exp]").forEach(function(x){x.onchange=function(){
      var f=ifaceById(n,x.dataset.exp); if(!f) return;
      pushUndo();
      f.exposed=x.checked; render();fillInspector();};});
    var kseg=document.getElementById("kseg");
    if(kseg) kseg.querySelectorAll("button").forEach(function(b){b.onclick=function(){addKind=b.dataset.k;kseg.querySelectorAll("button").forEach(function(x){x.classList.remove("on");});b.classList.add("on");};});
    var tyIn=document.getElementById("ni_type"), ts=document.getElementById("ni_ts");
    if(tyIn) tyIn.oninput=function(){
      var v=tyIn.value.trim(), pk=v.split("/")[0];
      if(!v){ts.textContent="";ts.className="typestate";}
      else if(TYPESET[v]){ts.textContent="✓ resolves in the type catalogue";ts.className="typestate ok";}
      else if(pk===n.pkg){ts.textContent="self-referencing — a companion .ros will be generated";ts.className="typestate warn";}
      else {ts.textContent="not in catalogue — you will need to define or vendor this type";ts.className="typestate warn";}
    };
    var add=document.getElementById("ni_add");
    if(add) add.onclick=function(){
      var nm=document.getElementById("ni_name").value.trim(); if(!nm) return;
      pushUndo();
      // a hand-added interface is exposed on sight: the author typed it in to model it, so it
      // belongs in the .rossystem whether or not it is wired up yet.
      n.ifaces.push({id:nid(),name:nm,kind:addKind,type:document.getElementById("ni_type").value.trim()||null,qos:null,label:null,exposed:true});
      render();fillInspector();};
    var pAdd=document.getElementById("np_add");
    if(pAdd) pAdd.onclick=function(){
      var nm=document.getElementById("np_name").value.trim(); if(!nm) return;
      pushUndo();
      var t=document.getElementById("np_type").value, raw=document.getElementById("np_val").value.trim(), val=raw;
      if(t==="Boolean") val=/^(t|1|y|true)/i.test(raw)?"true":"false";
      else if(t==="Integer") val=String(parseInt(raw||"0",10)||0);
      else if(t==="Double") val=(raw.indexOf(".")>=0?raw:String((parseFloat(raw||"0")||0).toFixed(1)));
      n.params.push({id:nid(),name:nm,ptype:t,value:val});
      render();fillInspector();};
    wireComments();
    var del=document.getElementById("delNode");
    if(del) del.onclick=function(){
      pushUndo();
      project.connections=project.connections.filter(function(c){return c.from.n!==n.id&&c.to.n!==n.id;});
      project.nodes=project.nodes.filter(function(x){return x.id!==n.id;});
      selNode=null;render();fillInspector();};
  }

  // ============================ rail ============================
  document.getElementById("addNode").onclick=function(){
    pushUndo();
    var n={id:nid(),label:"new_node",backing:"hand",pkg:"new_package",node:"new_node",artifact:"new_node",
      catalogueFile:null,namespace:null,x:200+Math.random()*120,y:340+Math.random()*80,ifaces:[],params:[]};
    project.nodes.push(n); selNode=n.id; selEdge=null; render(); fillInspector();
  };
  var catScrim=document.getElementById("catScrim");
  document.getElementById("addCat").onclick=function(){catScrim.classList.add("on");renderCat("");document.getElementById("catSearch").focus();};
  document.getElementById("catSearch").oninput=function(e){renderCat(e.target.value);};
  function renderCat(q){
    q=(q||"").toLowerCase();
    var list=document.getElementById("catList"); list.innerHTML="";
    var keys=Object.keys(CATALOGUE), shown=0;
    for(var i=0;i<keys.length && shown<200;i++){
      var key=keys[i], e=CATALOGUE[key];
      if(q && key.toLowerCase().indexOf(q)<0) continue;
      shown++;
      var ifs=Object.keys(e.interfaces||{}).map(function(k){return '<span style="color:var(--k-'+e.interfaces[k]+')">'+esc(k)+'·'+e.interfaces[k]+'</span>';}).join("  ");
      var row=document.createElement("div"); row.className="catrow";
      row.innerHTML='<div class="cinfo"><div class="ckey">'+esc(key)+'</div><div class="cif">'+ifs+'</div><div class="cfile">'+esc(e.file||"")+'</div></div><button class="minibtn">instantiate</button>';
      (function(key,e){row.querySelector("button").onclick=function(){instantiate(key,e);};})(key,e);
      list.appendChild(row);
    }
    if(!shown) list.innerHTML='<div class="roinfo">No catalogue entries match.</div>';
  }
  function instantiate(key,e){
    pushUndo();
    var parts=key.split("."), pkg=parts[0], node=parts.slice(1).join(".");
    var tmap=CATTYPES[key]||{};   // real interface types recovered from the vendored .ros2
    var n={id:nid(),label:node,backing:"cat",pkg:pkg,node:node,artifact:e.artifact||node,catalogueFile:e.file||null,
      namespace:null,x:220+Math.random()*140,y:120+Math.random()*120,
      // a catalogue node arrives with its FULL interface set; exposing all of it would write
      // dozens of unwired lines, so these start unexposed and surface as you connect them.
      ifaces:Object.keys(e.interfaces||{}).map(function(nm){return {id:nid(),name:nm,kind:e.interfaces[nm],type:tmap[nm]||null,qos:null,label:null,exposed:false};}),params:[]};
    project.nodes.push(n); selNode=n.id; catScrim.classList.remove("on"); render(); fillInspector();
  }
  [].slice.call(document.querySelectorAll("[data-close]")).forEach(function(b){b.onclick=function(e){e.target.closest(".scrim").classList.remove("on");};});
  [].slice.call(document.querySelectorAll(".scrim:not([data-locked])")).forEach(function(s){s.onclick=function(e){if(e.target===s)s.classList.remove("on");};});

  var KCOL={pub:"--k-pub",sub:"--k-sub",ss:"--k-ss",sc:"--k-sc",as:"--k-as",ac:"--k-ac"};
  (function(){
    var fb=document.getElementById("filterBox");
    // only the six arrow kinds -- params are never drawn on the editor canvas, so a `param`
    // toggle would be a no-op.
    KINDS.forEach(function(k){
      var l=document.createElement("label");
      l.innerHTML='<input type="checkbox" checked data-k="'+k+'"><span class="sw" style="background:var('+KCOL[k]+')"></span>'+k;
      l.querySelector("input").onchange=function(e){kindShown[k]=e.target.checked;render();};
      fb.appendChild(l);
    });
    var lg=document.getElementById("legend");
    [["pub → sub","Topic — one-way ▶"],["ss → sc","Service — request ⇄ response"],["as → ac","Action — request ⇄ response"]]
      .forEach(function(pair){var d=document.createElement("div");d.innerHTML='<b style="font-family:var(--mono);font-size:.66rem">'+pair[0]+'</b> — '+pair[1];lg.appendChild(d);});
  })();

  // ============================ issues ============================
  function runIssues(){
    var issues=[];
    var labels={};
    for(var i=0;i<project.nodes.length;i++){var n=project.nodes[i];
      if(n.backing==="hand" && /[A-Z]/.test(n.pkg)) issues.push(["e",'package "'+n.pkg+'" has uppercase — validator ERROR (RM010)']);
      labels[n.label]=(labels[n.label]||0)+1;
      // RM044: legal and the server accepts it, but 0 of 52 corpus files use it, so the linter
      // warns. Surface it here rather than letting Commit be the first mention.
      if(n.namespace&&String(n.namespace).trim())
        issues.push(["w",n.label+': namespace "'+n.namespace+'" has zero corpus support (RM044)']);
      var seen={};
      for(var j=0;j<n.ifaces.length;j++){var f=n.ifaces[j];
        if(seen[f.name]) issues.push(["w",n.label+": duplicate interface name \""+f.name+"\""]); seen[f.name]=1;
        // B2: a hand-authored interface with no type blocks generation (server can't resolve it)
        if(n.backing==="hand" && (!f.type||String(f.type).trim()==="")) issues.push(["e",n.label+": interface \""+f.name+"\" ("+f.kind+") has no message type"]);
        // RM035 on a QoS duration is a hard ERROR that would stop `generate` after the files
        // are already written; the panel has to say so while it is still editable.
        if(f.qos) (QOS.durations||[]).forEach(function(k){
          if(qosDurationProblem(f.qos[k]))
            issues.push(["e",n.label+': qos '+k+' "'+f.qos[k]+'" is rejected by CheckDuration (RM035)']);
        });
      }
      if(!project.nodes.length){}
      if(DIAG[n.id]) DIAG[n.id].forEach(function(m){issues.push(["e",m]);});
    }
    for(var l in labels) if(labels[l]>1) issues.push(["e",'duplicate node label "'+l+'" (RM009)']);
    // .ros field rows. _validate_types() blocks generation on exactly these, so the counter
    // has to see them too -- otherwise the page reads "no issues" for a project `generate`
    // then refuses.
    (function(){
      var known=definedTypeKeys();
      // a hand-authored interface whose type resolves nowhere. RM081 is only a WARNING (linking
      // is cross-file), but the server REJECTS with "Couldn't resolve reference to TopicSpec",
      // so validate_project blocks generation on it and this has to say so first.
      project.nodes.forEach(function(n){
        if(n.backing!=="hand") return;
        (n.ifaces||[]).forEach(function(f){
          var typ=String(f.type||"").replace(/^\s+|\s+$/g,"");
          if(!typ||typ.indexOf("TODO")===0||typ.indexOf("/")<0) return;
          if(known[typ]||TYPEFILES[typ]) return;
          issues.push(["e",n.label+": "+f.name+" type '"+typ+"' is defined neither here nor in "
            +"the catalogue — define it under 'message types (.ros)'"]);
        });
      });
      Object.keys(project.types||{}).sort().forEach(function(key){
        var p=String(key).split("/"), block=(p.length===3)?SEGBLOCK[p[1]]:null;
        if(!block){issues.push(["e",key+" is not <package>/<msg|srv|action>/<Name>"]);return;}
        if(CATPKG[p[0]]){issues.push(["e",key+": '"+p[0]+"' is a catalogue package — "
          +"redeclaring it is RM009"]);return;}
        (ROS.bodies[block]||[]).forEach(function(body){
          (((project.types[key]||{}).fields||{})[body]||[]).forEach(function(f){
            var tn=rosTypeNote(f.type,known), nn=rosNameNote(f.name);
            if(tn[0]) issues.push([tn[0],key+" / "+body+": "+tn[1]]);
            else if(nn[0]) issues.push([nn[0],key+" / "+body+": "+nn[1]]);
          });
        });
      });
    })();
    if(!project.nodes.length) issues.push(["e","system has no nodes — add one before generating (the server rejects an empty nodes: block)"]);
    // RM053. A warning, not an error: the current server ACCEPTS a system with no fromFile
    // (re-probed 2026-08-13, 0 errors / 0 warnings), so this must not be dressed up as a crash.
    if(!(project.system&&project.system.fromFile))
      issues.push(["w","no fromFile — rosmodel_lint warns (RM053); set it in the system panel (deselect to reach it)"]);
    // B1: a drawn connection whose endpoints carry different types is rejected by the server
    for(var ci=0;ci<project.connections.length;ci++){var c=project.connections[ci];
      var fa=ifaceById(nodeById(c.from.n),c.from.i), ta=ifaceById(nodeById(c.to.n),c.to.i);
      if(fa&&ta&&fa.type&&ta.type&&String(fa.type).trim()&&String(ta.type).trim()&&fa.type!==ta.type)
        issues.push(["e","type mismatch: "+fa.name+" ("+fa.type+") ↔ "+ta.name+" ("+ta.type+") — endpoints must share one type"]);
    }
    var errs=issues.filter(function(x){return x[0]==="e";}).length, wrns=issues.length-errs;
    var ec=document.getElementById("errCnt"), wc=document.getElementById("wrnCnt");
    ec.textContent=errs; ec.className="cnt "+(errs?"err":"ok");
    wc.textContent=wrns; wc.className="cnt "+(wrns?"wrn":"ok");
    var il=document.getElementById("issueList"); il.innerHTML="";
    if(!issues.length) il.innerHTML='<div class="it" style="border-color:var(--accent)">No issues from the instant checks.</div>';
    issues.slice(0,10).forEach(function(x){var d=document.createElement("div");d.className="it"+(x[0]==="e"?" e":"");d.textContent=x[1];il.appendChild(d);});
  }

  // ============================ commit / generate preview ============================
  // MUST stay in step with _exposure_labels() in ros_studio.py -- this is the live preview of
  // what that emitter will write. An interface is exposed when it is flagged `exposed` OR a
  // connection touches it, and a label carried over from the source wins verbatim.
  function exposureLabels(){
    var wanted=[], seen={};
    function want(n,f){var k=n.id+"/"+f.id; if(!seen[k]){seen[k]=1;wanted.push([n,f]);}}
    project.nodes.forEach(function(n){n.ifaces.forEach(function(f){if(f.exposed)want(n,f);});});
    project.connections.forEach(function(c){
      [c.from,c.to].forEach(function(end){
        var n=nodeById(end.n), f=ifaceById(n,end.i);
        if(n&&f) want(n,f);
      });
    });
    // MIRRORS ros_studio._exposure_labels. An exposure label's SCOPE IS THE NODE -- it is a key
    // inside that node's interfaces: list, and two nodes may both expose "scan" (RM065's hint
    // says so, and the corpus does it throughout). A file-wide used-set renamed the second
    // node's label to something the author never wrote. subLabels stays file-wide: those come
    // from the referenced file, and a DERIVED label matching one would resolve to the wrong node.
    var labels={}, usedByNode={}, subLabels={};
    function claim(n,lbl){ (usedByNode[n.id]=usedByNode[n.id]||{})[lbl]=1; }
    function taken(n,lbl){ return !!(usedByNode[n.id]&&usedByNode[n.id][lbl]); }
    // pass 0: a subSystems: node's label belongs to the REFERENCED file and cannot be renamed
    // here -- it is the exact string a connections: endpoint has to spell. Two subsystem nodes
    // sharing a label (the catalogued turtlebot's "tf") both map to that one string: that
    // ambiguity is the source file's (RM065), and inventing a distinct label would emit an
    // endpoint resolving to nothing.
    wanted.forEach(function(p){
      if(p[0].backing!=="sub") return;
      var lbl=String(p[1].label||p[1].name||"").trim();
      if(lbl){ labels[p[0].id+"/"+p[1].id]=lbl; claim(p[0],lbl); subLabels[lbl]=1; }
    });
    wanted.forEach(function(p){                       // pass 1: source labels are authoritative
      var lbl=(p[1].label||"").trim();
      if(lbl&&!taken(p[0],lbl)){claim(p[0],lbl);labels[p[0].id+"/"+p[1].id]=lbl;}
    });
    var rest=wanted.filter(function(p){return !labels[p[0].id+"/"+p[1].id];});
    var counts={}; rest.forEach(function(p){counts[p[1].name]=(counts[p[1].name]||0)+1;});
    rest.forEach(function(p){                         // pass 2: derive, avoiding pass-1 names
      var n=p[0], f=p[1], lbl=(counts[f.name]>1)?f.name+"_"+f.kind:f.name;
      function clash(c){ return taken(n,c)||!!subLabels[c]; }
      if(clash(lbl)) lbl=f.name+"_"+f.kind+"_"+n.label.replace(/[^A-Za-z0-9_]/g,"_");
      var sfx=2; while(clash(lbl)){lbl=f.name+"_"+f.kind+"_"+n.label.replace(/[^A-Za-z0-9_]/g,"_")+"_"+sfx; sfx++;}
      claim(n,lbl); labels[n.id+"/"+f.id]=lbl;
    });
    return labels;
  }
  function ifaceConnected(n,f){
    for(var i=0;i<project.connections.length;i++){
      var c=project.connections[i];
      if((c.from.n===n.id&&c.from.i===f.id)||(c.to.n===n.id&&c.to.i===f.id)) return true;
    }
    return false;
  }
  function genSystem(){
    var labels=exposureLabels();
    var name=document.getElementById("sysname").value||"system";
    var o=cmtBlock(project,"header","")+name+":\n";
    if(project.system&&project.system.fromFile)
      o+='  fromFile: '+qd(project.system.fromFile)+noteSuffix(cmtOf(project,"fromFile"))+'\n';
    // ROSSYSTEM_TOP_KEYS: fromFile -> subSystems -> processes -> nodes -> parameters ->
    // connections. 'components+=SubSystem*' is a repetition, so each entry is one bare
    // (optionally quoted) EString on its own indented line -- there is no bracket form (RM093).
    var subs=project.subSystems||[];
    if(subs.length){
      o+="  subSystems:\n";
      subs.forEach(function(s){
        o+=cmtBlock(s,"before","    ")+'    '+qd(s.ref)
          +noteSuffix(cmtOf(s,"line"),s.file?("assets/rosmodelscatalog/"+s.file):"")+'\n';
      });
    }
    o+="  nodes:\n";
    project.nodes.forEach(function(n){
      // provided by the subSystems: block above -- re-declaring it under this file's own
      // nodes: is RM090 ("two distinct RosNode objects answer to the same name").
      if(n.backing==="sub") return;
      o+=cmtBlock(n,"before","    ")+'    '+qd(n.label)+':'+noteSuffix(cmtOf(n,"line"))+'\n';
      o+='      from: '+qd(n.pkg+"."+n.node)
        +noteSuffix(cmtOf(n,"from"),
                    (n.backing==="cat"&&n.catalogueFile)?("assets/rosmodelscatalog/"+n.catalogueFile):"")
        +'\n';
      // RosSystem.xtext:60-75 fixes from -> namespace -> interfaces -> parameters (RM039).
      var ns=String(n.namespace==null?"":n.namespace).trim();
      if(ns) o+='      namespace: '+qd(ns)+'\n';
      var exposed=n.ifaces.filter(function(f){return labels[n.id+"/"+f.id];});
      // emit_rossystem() writes the exposures sorted by (kind order, name). Without the same
      // sort the preview matched only for a freshly seeded project, where the seeder happens
      // to build n.ifaces in that order -- the first interface ADDED in the editor is appended
      // and the preview then shows it in a position the emitter will not use.
      exposed.sort(function(a,b){var d=KINDS.indexOf(a.kind)-KINDS.indexOf(b.kind);
        return d||(a.name<b.name?-1:(a.name>b.name?1:0));});
      if(exposed.length){
        o+="      interfaces:\n";
        exposed.forEach(function(f){
          o+=cmtBlock(f,"before","        ")
            +'        - '+qd(labels[n.id+"/"+f.id])+': '+f.kind+'-> '
            +qd((n.artifact||"")+"::"+f.name)+noteSuffix(cmtOf(f,"line"))+'\n';});
      }
      // ROSSYSTEM_NODE_KEYS puts `parameters:` last. A RosParameter is an EXPOSURE with an
      // override value ('- "label": "artifact::name"' / 'value: v'), not a declaration -- the
      // declaration is the artifact's and goes into the .ros2 via genRos2.
      var pex=(n.params||[]).filter(function(p){return p.exposed;})
        .sort(function(a,b){return a.name<b.name?-1:(a.name>b.name?1:0);});
      if(pex.length){
        o+="      parameters:\n";
        pex.forEach(function(p){
          var t=String(p.ptype||"").trim()||inferPtype(p.sysValue);
          o+=cmtBlock(p,"before","        ")
            +'        - '+qd(p.label||p.name)+': '
            +qd((n.artifact||"")+"::"+p.name)+noteSuffix(cmtOf(p,"line"))
            +'\n          value: '+fmtParamValue(t,p.sysValue)+'\n';
        });
      }
    });
    // The system-level `parameters:` block sits between nodes: and connections:.
    var sp=project.params||[];
    if(sp.length){
      o+="  parameters:\n";
      sp.forEach(function(p){
        o+=cmtBlock(p,"before","    ")+'    '+qd(p.name)+':'+noteSuffix(cmtOf(p,"line"))+'\n';
        var ns=String(p.ns==null?"":p.ns).trim();
        // `ns:` is a Namespace: one of three bare KEYWORDS (GlobalNamespace |
        // RelativeNamespace | PrivateNamespace, Basics.xtext:13-32), NOT an EString. Quoting
        // it is a parse error in the real server -- see the note in emit_rossystem.
        if(ns) o+='      ns: '+ns+noteSuffix(cmtOf(p,"ns"))+'\n';
        // Slot order ns -> type (-> its default) -> value. `default:` belongs to the
        // ParameterType, `value:` to the Parameter: two different slots, never folded.
        var d=p["default"];
        var t=String(p.ptype||"").trim()||inferPtype((d!=null&&d!=="")?d:p.value);
        o+='      type: '+t+noteSuffix(cmtOf(p,"type"))+'\n';
        if(d!=null&&d!=="") o+='      default: '+fmtParamValue(t,d)+'\n';
        if(p.value!=null&&p.value!=="")
          o+='      value: '+fmtParamValue(t,p.value)+noteSuffix(cmtOf(p,"value"))+'\n';
      });
    }
    if(project.connections.length){
      o+="  connections:\n";
      project.connections.forEach(function(c){
        var fl=labels[c.from.n+"/"+c.from.i], tl=labels[c.to.n+"/"+c.to.i];
        if(fl&&tl) o+=cmtBlock(c,"before","    ")+'    - ['+qd(fl)+', '+qd(tl)+']'
          +noteSuffix(cmtOf(c,"line"))+'\n';
      });
    }
    return o;
  }
  // ---- .ros2 preview -----------------------------------------------------------------
  // Byte-parity with generate_files()/emit_ros2() in ros_studio.py, and pinned by
  // tests/studio_parity.js. It used to be a rough sketch (no fromGitRepo, no qos, unsorted
  // artifacts, a lowercased package name) -- tolerable while nothing in this file was
  // .ros2-only, but QoS and fromGitRepo are editable HERE and nowhere else, so this preview
  // is the only place an author can check them before handing the project to the companion.
  function handPkgNodes(){
    var by={}, order=[];
    project.nodes.forEach(function(n){
      if(n.backing!=="hand"||!n.pkg) return;
      if(!by[n.pkg]){ by[n.pkg]=[]; order.push(n.pkg); }
      by[n.pkg].push(n);
    });
    order.sort();
    return {by:by,order:order};
  }
  // _local_type_packages(): the packages a companion .ros may be written for -- every
  // hand-authored node's package, PLUS every package a locally defined spec names. The second
  // half is what makes a type invented here emittable when no interface references it (the
  // inner type of a self-referencing message, say).
  function localTypePkgs(){
    var out={};
    project.nodes.forEach(function(n){ if(n.backing==="hand"&&n.pkg) out[n.pkg]=1; });
    Object.keys(project.types||{}).forEach(function(key){
      var p=String(key).split("/");
      if(p.length===3&&p[0]&&!TYPEFILES[key]) out[p[0]]=1;
    });
    return out;
  }
  // _companion_types(): the specs each companion .ros must declare, {pkg:{block:{Name:1}}}.
  // A type reached only through an interface still counts -- that is the bodiless case -- and
  // its reference then carries NO "# assets/roscommonobjects/..." disclosure comment.
  function companionTypes(){
    var local=localTypePkgs(), out={};
    function add(pkg,block,name){
      if(!out[pkg]) out[pkg]={};
      if(!out[pkg][block]) out[pkg][block]={};
      out[pkg][block][name]=1;
    }
    Object.keys(project.types||{}).forEach(function(key){
      var p=String(key).split("/");
      if(p.length!==3) return;
      var block=SEGBLOCK[p[1]];
      if(local[p[0]]&&block&&!TYPEFILES[key]) add(p[0],block,p[2]);
    });
    project.nodes.forEach(function(n){
      if(n.backing!=="hand") return;
      (n.ifaces||[]).forEach(function(f){
        var typ=f.type;
        if(!typ||String(typ).indexOf("/")<0) return;
        var p=String(typ).split("/");
        if(p.length!==3) return;
        var block=SEGBLOCK[p[1]];
        if(local[p[0]]&&block&&!TYPEFILES[typ]) add(p[0],block,p[2]);
      });
    });
    return out;
  }
  function companionPkgs(){
    var out={}, ct=companionTypes();
    Object.keys(ct).forEach(function(p){ out[p]=1; });
    return out;
  }
  // the RM089 disclosure BODY (no "# "); noteSuffix() merges it with whatever the author wrote
  // on that line, so an edit cannot silently delete the disclosure.
  function typeAutoNote(typ,comp){
    if(!typ||String(typ).indexOf("/")<0) return "";
    if(comp[String(typ).split("/")[0]]) return "";
    return TYPEFILES[typ]?("assets/roscommonobjects/"+TYPEFILES[typ]):"";
  }
  // Python float(): anything it would reject becomes 0.0 in _fmt_param_value. This accepts the
  // plain numeral forms only -- float() also takes "inf", "1_0" and surrounding tabs, which no
  // parameter default in the corpus uses.
  function pyFloat(raw){
    raw=String(raw==null?"":raw).trim();
    if(!/^[+-]?([0-9]+\.?[0-9]*|\.[0-9]+)([eE][+-]?[0-9]+)?$/.test(raw)) return 0;
    var f=parseFloat(raw);
    return isFinite(f)?f:0;
  }
  // Python repr() of a float, which is NOT String(Number): CPython switches to exponential at
  // 1e16 and below 1e-4 (JS: 1e21 and 1e-7) and pads the exponent to two digits. Getting this
  // wrong would print "1e+16" where the emitter writes "1.0e+16" -- and a mantissa with no
  // '.' is the RM041 DECINT trap the emitter exists to avoid.
  function pyRepr(f){
    if(f===0) return (1/f===-Infinity)?"-0.0":"0.0";
    var ex=f.toExponential(), at=ex.indexOf("e"), e=parseInt(ex.slice(at+1),10);
    if(e>=-4&&e<=15){ var s=String(f); return (s.indexOf(".")<0)?s+".0":s; }
    var mant=ex.slice(0,at);
    if(mant.indexOf(".")<0) mant+=".0";
    var a=Math.abs(e);
    return mant+"e"+(e<0?"-":"+")+(a<10?("0"+a):String(a));
  }
  function fmtParamValue(ptype,value){
    ptype=String(ptype||"String").trim();
    var raw=(value==null)?"":String(value);
    if(ptype==="Boolean") return /^\s*(t|1|y|true)/i.test(raw)?"true":"false";
    if(ptype==="Integer"){
      if(!raw) return "0";
      var t=Math.trunc(pyFloat(raw));
      // Python's int() is exact for any float; JS String() gives "1e+30" past 1e21, so hand
      // the out-of-safe-range case to BigInt, which prints the same digits int() would.
      if(Math.abs(t)>9007199254740991&&typeof BigInt==="function") return BigInt(t).toString();
      return String(t);
    }
    if(ptype==="Double") return pyRepr(pyFloat(raw));
    return qs2(raw);
  }
  // MIRRORS ros_studio._infer_ptype. A parameter the project knows only as a .rossystem
  // exposure carries a value and no type -- RosParameter has no `type:` slot -- but the .ros2
  // declaration this project writes for a hand-backed artifact needs one (Basics.xtext:46).
  function inferPtype(value){
    var raw=((value==null)?"":String(value)).trim();
    if(!raw) return "String";
    var lo=raw.toLowerCase();
    if(lo==="true"||lo==="false") return "Boolean";
    var c=raw.charAt(0);
    if(c==='"'||c==="'"||c==="[") return "String";
    if(/^[+-]?\d+$/.test(raw)) return "Integer";
    if(raw===String(pyFloat(raw))||/^[+-]?(\d+\.\d*|\.\d+)([eE][+-]?\d+)?$/.test(raw)
       ||/^[+-]?\d+[eE][+-]?\d+$/.test(raw)) return "Double";
    return "String";
  }
  // MIRRORS ros_studio._art_param_decl -- ONE definition of the .ros2 declaration half, used by
  // both genRos2 and projectFacts so the emitter and its prediction cannot drift.
  function artParamDecl(p){
    var val=p.value;
    if((val==null||val==="")&&p.sysValue!=null&&p.sysValue!=="") val=p.sysValue;
    var t=String(p.ptype||"").trim()||inferPtype(val);
    return [t,val];
  }
  // MIRRORS ros_studio._sys_param_fact. Slot order is ns -> type (-> its default) -> value.
  function sysParamFact(p){
    var d=p["default"], v=p.value;
    var t=String(p.ptype||p.type||"").trim()
          ||inferPtype((d!=null&&d!=="")?d:v);
    var out=[];
    if(p.ns!=null&&p.ns!=="") out.push("ns="+p.ns);
    out.push("type="+t);
    if(d!=null&&d!=="") out.push("default="+unquoteEmitted(fmtParamValue(t,d)));
    if(v!=null&&v!=="") out.push("value="+unquoteEmitted(fmtParamValue(t,v)));
    return out.join("; ");
  }
  function genQos(qos,indent){
    if(!qos) return "";
    var out=[];
    QOS.fields.forEach(function(k){
      var v=qos[k];
      if(v==null||v==="") return;
      v=String(v);
      // 'infinite' is a grammar keyword, not an EString: quoting it is an RM035 error.
      if(QOS_DUR[k]&&v!=="infinite") v=qd(v);
      out.push(indent+"  "+k+": "+v+"\n");
    });
    return out.length?(indent+"qos:\n"+out.join("")):"";
  }
  // MIRRORS ros_studio._fold_artifacts. Two nodes may share one `from: pkg.ARTIFACT` -- two
  // instances of a node type, or two merged systems reusing a package -- and the artifact is one
  // definition either way, so the .ros2 declares it ONCE with the union of what each node
  // exposes. Emitting it per referring node is a duplicate key (RM009). The Python emitter folds;
  // without this the preview showed the author a file `generate` would never write.
  function foldArtifacts(recs){
    var byArt={}, order=[];
    recs.forEach(function(rec){
      var key=String(rec.artifact||"");
      if(!byArt[key]){
        var copy={}; for(var k in rec) if(Object.prototype.hasOwnProperty.call(rec,k)) copy[k]=rec[k];
        copy.ifaces=(rec.ifaces||[]).slice();
        copy.params=(rec.params||[]).slice();
        byArt[key]=copy; order.push(key);
        return;
      }
      var into=byArt[key], have={}, haveP={};
      // '|' cannot occur in a ROS interface name, so it separates the pair unambiguously
      into.ifaces.forEach(function(f){have[f.kind+"|"+f.name]=1;});
      (rec.ifaces||[]).forEach(function(f){
        var kk=f.kind+"|"+f.name;
        if(!have[kk]){have[kk]=1;into.ifaces.push(f);}
      });
      into.params.forEach(function(pr){haveP[pr.name]=1;});
      (rec.params||[]).forEach(function(pr){
        if(!haveP[pr.name]){haveP[pr.name]=1;into.params.push(pr);}
      });
    });
    return order.map(function(k){return byArt[k];});
  }
  function genRos2(pkg){
    var g=handPkgNodes(), comp=companionPkgs();
    var nodes=foldArtifacts((g.by[pkg]||[]).slice()).sort(function(a,b){
      var x=String(a.artifact||""), y=String(b.artifact||"");
      return x<y?-1:(x>y?1:0);});
    var entry=project.packages[pkg]||{}, git=entry.fromGitRepo;
    var o=cmtBlock(entry,"header","")+pkg+":\n";
    if(git) o+="  fromGitRepo: "+qd(git)+"\n";
    o+="  artifacts:\n";
    nodes.forEach(function(n){
      o+=cmtBlock(n,"ros2Before","    ")+"    "+(n.artifact||"")+":"
        +noteSuffix(cmtOf(n,"ros2Line"))+"\n      node: "+n.node+"\n";
      KINDS.forEach(function(k){
        var fs=n.ifaces.filter(function(f){return f.kind===k;}).sort(function(a,b){
          return a.name<b.name?-1:(a.name>b.name?1:0);});
        if(!fs.length) return;
        o+="      "+BLOCK[k]+":\n";
        fs.forEach(function(f){
          var typ=f.type||"TODO_pkg/msg/Type";
          o+=cmtBlock(f,"ros2Before","        ")
            +"        "+qs2(f.name)+":"+noteSuffix(cmtOf(f,"ros2Line"))
            +"\n          type: "+qs2(typ)
            +noteSuffix(cmtOf(f,"ros2Type"),typeAutoNote(typ,comp))+"\n";
          o+=genQos(f.qos,"          ");
        });
      });
      var ps=(n.params||[]).slice().sort(function(a,b){
        return a.name<b.name?-1:(a.name>b.name?1:0);});
      if(ps.length){
        o+="      parameters:\n";
        ps.forEach(function(p){
          var d=artParamDecl(p);
          o+=cmtBlock(p,"ros2Before","        ")
            +"        "+qs2(p.name)+":"+noteSuffix(cmtOf(p,"ros2Line"))
            +"\n          type: "+d[0]
            +"\n          default: "+fmtParamValue(d[0],d[1])+"\n";
        });
      }
    });
    return o;
  }
  // _companion_ros(). The four-BEGIN ladder: package 0 / block 2 / spec name 4 (the one named
  // element in the language with NO trailing ':') / body keyword 6 / field 8. Every body
  // keyword is written even when empty -- Ros.xtext:81-104 makes the keyword mandatory and
  // only its indented body optional, which is why a bodiless `response` is the normal shape.
  function genRos(pkg){
    var specs=companionTypes()[pkg]||{}, o=pkg+":\n";
    (ROS.blocks||[]).forEach(function(block){
      var names=Object.keys(specs[block]||{}).sort();
      if(!names.length) return;
      o+="  "+block+":\n";
      var seg=ROSSEG[block];
      names.forEach(function(name){
        o+="    "+name+"\n";
        var fields=((project.types||{})[pkg+"/"+seg+"/"+name]||{}).fields||{};
        (ROS.bodies[block]||[]).forEach(function(body){
          o+="      "+body+"\n";
          (fields[body]||[]).forEach(function(f){
            var t=String(f.type==null?"":f.type).replace(/^\s+|\s+$/g,"");
            var n=String(f.name==null?"":f.name).replace(/^\s+|\s+$/g,"");
            // a half-filled row is blocked by validate_project before anything is written, so
            // skipping it here matches the emitter rather than inventing a broken line.
            if(t&&n) o+="        "+t+" "+n+"\n";
          });
        });
      });
    });
    return o;
  }
  // ---- "what changed since the seed" -------------------------------------------------
  // The companion embeds the SEED's fact tree (DATA.seedFacts, built by source_facts() from
  // the .rossystem the project was seeded from). This side rebuilds the AFTER tree from the
  // live project and diffs the two, so the answer is live while the author edits and needs no
  // network. projectFacts/diffFacts/formatDiff mirror project_facts()/diff_facts()/
  // format_diff() in ros_studio.py and are held to them by tests/studio_parity.js -- the same
  // discipline as genSystem(), for the same reason: a preview that drifts lies about the model.
  //
  // A TEXT diff is not offered on purpose. The emitter fixes key order, quotes every EString
  // and sorts each node's interfaces, so a round-trip that changed nothing still rewrites most
  // lines; only the fact tree can tell an edit from a reformat.
  function factStr(v){ return v==null?"":String(v); }
  // one layer of the emitter's own quoting, undone -- the seed side was read back through a
  // YAML composer that had already resolved the quote style and the \\ / \" escapes.
  function unquoteEmitted(s){
    s=String(s);
    if(s.length>=2&&s.charAt(0)===s.charAt(s.length-1)&&(s.charAt(0)==='"'||s.charAt(0)==="'")){
      var inner=s.slice(1,-1);
      // NUL as the placeholder, never a space: a value that legitimately contains spaces
      // would otherwise come back with every one of them turned into a backslash.
      if(s.charAt(0)==='"')
        return inner.replace(/\\\\/g,"\u0000").replace(/\\"/g,'"').replace(/\u0000/g,"\\");
      return inner;
    }
    return s;
  }
  function paramFact(ptype,value){
    return (ptype||"String")+" = "+unquoteEmitted(fmtParamValue(ptype,value));
  }
  // a qos: block as one line, in QOS_PINNED order -- the order _emit_qos writes it, so the
  // parsed and the predicted forms agree.
  function qosFact(qos){
    if(!qos) return "";
    var out=[];
    (QOS.fields||[]).forEach(function(k){
      var v=qos[k];
      if(v==null||v==="") return;
      out.push(k+"="+v);
    });
    return out.join("; ");
  }
  function ifaceFactKey(kind,name){ return kind+" "+name; }
  function projectFacts(){
    var labels=exposureLabels();
    var facts={system:{name:factStr(document.getElementById("sysname").value||"system"),
                       fromFile:factStr(project.system&&project.system.fromFile)},
               subSystems:(project.subSystems||[]).map(function(s){return factStr(s.ref);}),
               nodes:{}, params:{}, connections:[], packages:{}, types:{}};
    (project.params||[]).forEach(function(p){ facts.params[p.name]=sysParamFact(p); });
    project.nodes.forEach(function(n){
      if(n.backing==="sub") return;      // the subSystems: block provides it (RM090)
      var rec={from:n.pkg+"."+n.node,
               namespace:factStr(String(n.namespace==null?"":n.namespace).replace(/^\s+|\s+$/g,"")),
               exposures:{}, parameters:{}};
      (n.ifaces||[]).forEach(function(f){
        var lbl=labels[n.id+"/"+f.id];
        if(lbl==null) return;
        rec.exposures[lbl]=f.kind+"-> "+(n.artifact||"")+"::"+f.name;
      });
      // keyed by the exposure LABEL, matching source_facts, which reads it back off the
      // `- "label": "artifact::name"` line the emitter writes.
      (n.params||[]).forEach(function(p){
        if(p.exposed) rec.parameters[p.label||p.name]=factStr(p.sysValue);
      });
      facts.nodes[n.label]=rec;
    });
    project.connections.forEach(function(c){
      var fl=labels[c.from.n+"/"+c.from.i], tl=labels[c.to.n+"/"+c.to.i];
      if(fl&&tl) facts.connections.push(fl+" -> "+tl);
    });
    var hp=handPkgNodes();
    hp.order.forEach(function(pkg){
      var entry=(project.packages||{})[pkg]||{};
      var pentry={fromGitRepo:factStr(entry.fromGitRepo), artifacts:{}};
      facts.packages[pkg]=pentry;
      hp.by[pkg].forEach(function(n){
        var arec={node:factStr(n.node), interfaces:{}, qos:{}, parameters:{}};
        (n.ifaces||[]).forEach(function(f){
          var key=ifaceFactKey(f.kind,f.name);
          // the placeholder emit_ros2 writes for a type-less interface: the file spells it,
          // so the fact tree has to as well.
          arec.interfaces[key]=factStr(f.type||"TODO_pkg/msg/Type");
          var q=qosFact(f.qos);
          if(q) arec.qos[key]=q;
        });
        (n.params||[]).forEach(function(p){
          var d=artParamDecl(p);
          arec.parameters[p.name]=paramFact(d[0],d[1]);
        });
        pentry.artifacts[factStr(n.artifact)]=arec;
      });
    });
    var ct=companionTypes();
    Object.keys(ct).forEach(function(pkg){
      Object.keys(ct[pkg]).forEach(function(block){
        Object.keys(ct[pkg][block]).forEach(function(name){
          var key=pkg+"/"+ROSSEG[block]+"/"+name, o={};
          var fields=((project.types||{})[key]||{}).fields||{};
          (ROS.bodies[block]||[]).forEach(function(body){
            o[body]=(fields[body]||[]).filter(function(f){
              return String(f.type==null?"":f.type).replace(/^\s+|\s+$/g,"")
                  && String(f.name==null?"":f.name).replace(/^\s+|\s+$/g,"");
            }).map(function(f){
              return String(f.type).replace(/^\s+|\s+$/g,"")+" "
                   + String(f.name).replace(/^\s+|\s+$/g,"");
            });
          });
          facts.types[key]=o;
        });
      });
    });
    return facts;
  }

  var FACT_SECTIONS=["system","subSystems","nodes","connections","packages","types"];
  var FACT_MISSING={};
  function isFactObj(v){ return v!==null&&typeof v==="object"&&!(v instanceof Array); }
  function factSummary(value){
    if(isFactObj(value)){
      var parts=[];
      Object.keys(value).sort().forEach(function(k){
        var v=value[k];
        if(isFactObj(v)){ if(Object.keys(v).length) parts.push(k+": "+Object.keys(v).length); }
        else if(v instanceof Array){ if(v.length) parts.push(k+": "+v.length); }
        else if(v!=="") parts.push(k+"="+v);
      });
      return parts.join("; ")||"(empty)";
    }
    if(value instanceof Array) return value.length+" item(s)";
    return String(value);
  }
  function diffWalk(path,before,after,out){
    if(before===FACT_MISSING&&after===FACT_MISSING) return;
    if(before===FACT_MISSING){ out.push({op:"added",path:path,before:"",after:factSummary(after)}); return; }
    if(after===FACT_MISSING){ out.push({op:"removed",path:path,before:factSummary(before),after:""}); return; }
    if(isFactObj(before)&&isFactObj(after)){
      var keys={};
      Object.keys(before).forEach(function(k){keys[k]=1;});
      Object.keys(after).forEach(function(k){keys[k]=1;});
      Object.keys(keys).sort().forEach(function(k){
        diffWalk(path?path+"."+k:k,
                 Object.prototype.hasOwnProperty.call(before,k)?before[k]:FACT_MISSING,
                 Object.prototype.hasOwnProperty.call(after,k)?after[k]:FACT_MISSING,out);
      });
      return;
    }
    if((before instanceof Array)&&(after instanceof Array)){
      // multiset + an order check: `connections` has no key of its own (the label pair IS its
      // identity) and a message body's field list is ordered but not unique, so neither can be
      // walked by index without reporting one insertion as a rewrite of every line after it.
      var rest=after.slice(), i;
      before.forEach(function(item){
        var at=rest.indexOf(item);
        if(at>=0) rest.splice(at,1);
        else out.push({op:"removed",path:path,before:item,after:""});
      });
      var left=before.slice();
      after.forEach(function(item){
        var at=left.indexOf(item);
        if(at>=0) left.splice(at,1);
        else out.push({op:"added",path:path,before:"",after:item});
      });
      if(before.join("\u0000")!==after.join("\u0000")
         && before.slice().sort().join("\u0000")===after.slice().sort().join("\u0000"))
        out.push({op:"reordered",path:path,before:before.length+" item(s)",
                  after:"same, different order"});
      return;
    }
    if(before!==after)
      out.push({op:"changed",path:path,before:factSummary(before),after:factSummary(after)});
  }
  function diffFacts(before,after){
    var out=[];
    FACT_SECTIONS.forEach(function(sec){
      diffWalk(sec,
               Object.prototype.hasOwnProperty.call(before,sec)?before[sec]:FACT_MISSING,
               Object.prototype.hasOwnProperty.call(after,sec)?after[sec]:FACT_MISSING,out);
    });
    return out;
  }
  var DIFF_OP_MARK={added:"+",removed:"-",changed:"~",reordered:"%"};
  function diffShow(s){ return s===""?"(none)":s; }
  function padTo(s,w){ s=String(s); while(s.length<w) s+=" "; return s; }
  function formatDiff(records){
    if(!records.length) return "no model-level change since the seed.";
    var width=0;
    records.forEach(function(r){ if(r.path.length>width) width=r.path.length; });
    if(width>46) width=46;
    var lines=[], section=null, counts={};
    records.forEach(function(r){
      var sec=r.path.split(".")[0];
      if(sec!==section){ section=sec; lines.push("  "+sec); }
      var detail=r.op==="added"?r.after
                :(r.op==="removed"?r.before:(diffShow(r.before)+" -> "+diffShow(r.after)));
      lines.push("    "+DIFF_OP_MARK[r.op]+" "+padTo(r.path,width)+"  "+detail);
      counts[r.op]=(counts[r.op]||0)+1;
    });
    var tail=Object.keys(counts).sort().map(function(k){return counts[k]+" "+k;}).join(", ");
    lines.push("");
    lines.push("  "+records.length+" change(s): "+tail);
    return lines.join("\n");
  }
  function seedDiffText(){
    if(!DATA.seedFacts)
      return (DATA.seedNote||"no seed source recorded.")
        + "\n\nRun the companion's `ros_studio.py diff project.json --against FILE.rossystem` "
        + "to compare against a file of your choosing.";
    var head="seed: "+(DATA.seedFrom||[]).join(", ")
      +(DATA.seedMerged?"  (merged — the label uniquifier is replayed on the seed side)":"")
      +"\n\n";
    return head+formatDiff(diffFacts(DATA.seedFacts,projectFacts()));
  }

  function genProjectJson(){
    project.system=project.system||{}; project.system.name=document.getElementById("sysname").value;
    return JSON.stringify(project,null,2);
  }
  var commitScrim=document.getElementById("commitScrim");
  document.getElementById("commit").onclick=function(){commitScrim.classList.add("on");document.getElementById("copyBox").value=genProjectJson();showGen("system");};
  function showGen(tab){
    var tabs=[["system",".rossystem"],["ros2",".ros2 (per package)"],
              ["ros",".ros (message types)"],["json","project.json"],
              // last on purpose: the first four answer "what will be written", this one
              // answers "what did I change", which is the question you ask on the way out.
              ["diff","changed since the seed"]];
    var tb=document.getElementById("genTabs"); tb.innerHTML="";
    tabs.forEach(function(t){var bt=document.createElement("button");bt.textContent=t[1];bt.className=t[0]===tab?"on":"";bt.onclick=function(){showGen(t[0]);};tb.appendChild(bt);});
    var out="";
    if(tab==="system") out=genSystem();
    else if(tab==="ros2"){
      var order=handPkgNodes().order;
      out=order.length
        ? order.map(function(p){return "# "+p+".ros2\n"+genRos2(p);}).join("\n")
        : "(no hand-authored package — catalogue-only systems generate no .ros2)";
    }
    else if(tab==="ros"){
      var pk=Object.keys(companionTypes()).sort();
      out=pk.length
        ? pk.map(function(p){return "# "+p+".ros\n"+genRos(p);}).join("\n")
        : "(every type this project references resolves in the vendored catalogue — no "
          +"companion .ros is generated)";
    }
    else if(tab==="diff") out=seedDiffText();
    else out=genProjectJson();
    document.getElementById("genOut").textContent=out;
  }
  document.getElementById("dlJson").onclick=function(){
    var blob=new Blob([genProjectJson()],{type:"application/json"});
    var url=URL.createObjectURL(blob), a=document.createElement("a");
    a.href=url; a.download=(document.getElementById("sysname").value||"project")+".project.json";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
    clearDirty();     // the project has left the page; the beforeunload guard stands down
  };
  document.getElementById("selJson").onclick=function(){var t=document.getElementById("copyBox");t.focus();t.select();
    // copy-to-clipboard is the other hand-off route to the companion, so it counts as committed
    try{if(document.execCommand("copy")) clearDirty();}catch(e){}};

  // ============================ mode / level ============================
  var modeSeg=document.getElementById("modeSeg"), levelSeg=document.getElementById("levelSeg");
  modeSeg.querySelectorAll("button").forEach(function(b){b.onclick=function(){
    mode=b.dataset.mode;
    modeSeg.querySelectorAll("button").forEach(function(x){x.classList.toggle("on",x===b);});
    document.body.className=mode==="edit"?"mode-edit":"mode-view";
    levelSeg.style.display=mode==="edit"?"none":"inline-flex";
    if(mode==="edit"){ level=3; setLevelButtons(); }
    selEdge=null; render(); fillInspector();
  };});
  levelSeg.querySelectorAll("button").forEach(function(b){b.onclick=function(){level=+b.dataset.lvl;setLevelButtons();render();};});
  function setLevelButtons(){levelSeg.querySelectorAll("button").forEach(function(x){x.classList.toggle("on",+x.dataset.lvl===level);});}

  // ============================ canvas controls ============================
  document.getElementById("autoLayout").onclick=autoLayout;
  (function(){
    var box=document.getElementById("autoSides");
    if(!box) return;
    // a VIEW preference, not model content: it never enters project.json and never touches undo
    try{ autoSides=localStorage.getItem("rosStudio.autoSides")==="1"; }catch(e){}
    box.checked=autoSides;
    box.onchange=function(){
      autoSides=box.checked;
      try{ localStorage.setItem("rosStudio.autoSides",autoSides?"1":"0"); }catch(e){}
      render();          // ports move, and drawEdges reads their rendered positions
    };
  })();
  document.getElementById("zFit").onclick=fitView;
  document.getElementById("zIn").onclick=function(){zoomCentre(1.25);};
  document.getElementById("zOut").onclick=function(){zoomCentre(1/1.25);};
  // 100% keeps what you are looking at, at actual size -- resetting the pan as well would
  // throw away the one thing the author had just navigated to.
  document.getElementById("zOne").onclick=function(){zoomCentre(1/view.k);};
  var findBox=document.getElementById("findBox");
  findBox.oninput=function(e){ findQ=e.target.value; findIdx=0; applyFind();
    if(findHits.length) centreOn(findHits[0]); };
  findBox.onkeydown=function(e){
    if(e.key==="Enter"){ e.preventDefault(); findStep(e.shiftKey?-1:1); }
    if(e.key==="Escape"){ e.preventDefault(); findBox.value=""; findQ=""; findIdx=0;
      applyFind(); findBox.blur(); }
  };
  document.getElementById("findPrev").onclick=function(){findStep(-1);};
  document.getElementById("findNext").onclick=function(){findStep(1);};

  // ============================ misc ============================
  STUDIO.wireTheme(document.getElementById("theme"));
  document.getElementById("reset").onclick=function(){pushUndo();HOME.forEach(function(h){var n=nodeById(h.id);if(n){n.x=h.x;n.y=h.y;}});render();fitView();};
  document.getElementById("sysname").oninput=function(e){pushUndo("sysname");project.system=project.system||{};project.system.name=e.target.value;};
  document.getElementById("undoBtn").onclick=undo;
  document.getElementById("redoBtn").onclick=redo;
  addEventListener("keydown",function(e){
    var ae=document.activeElement, typing=ae&&/^(INPUT|TEXTAREA|SELECT)$/.test(ae.tagName||"");
    if((e.ctrlKey||e.metaKey)&&!e.altKey){
      var k=(e.key||"").toLowerCase();
      if(k==="z"||k==="y"){
        // A field bound to the project (data-undo) writes straight into the model, and its
        // keystrokes were already coalesced into ONE project-level entry -- the browser's
        // per-field undo would rewind the DOM and leave the model behind. Every other field
        // (catalogue search, the not-yet-added interface form) holds text the model has never
        // seen, so its native undo is the right one and we do not steal the key.
        if(typing && !(ae.dataset&&ae.dataset.undo==="1")) return;
        e.preventDefault();
        if(k==="y"||e.shiftKey) redo(); else undo();
        return;
      }
      if(k==="f"){ e.preventDefault(); findBox.focus(); findBox.select(); return; }
    }
    // viewport keys, only when the caret is not in a field
    if(!typing&&!e.ctrlKey&&!e.metaKey&&!e.altKey){
      if(e.key==="f"||e.key==="F"){ e.preventDefault(); fitView(); return; }
      if(e.key==="0"){ e.preventDefault(); zoomCentre(1/view.k); return; }
      if(e.key==="+"||e.key==="="){ e.preventDefault(); zoomCentre(1.25); return; }
      if(e.key==="-"||e.key==="_"){ e.preventDefault(); zoomCentre(1/1.25); return; }
    }
    if(e.key==="Escape"&&findQ){ findBox.value=""; findQ=""; findIdx=0; applyFind(); return; }
    if(e.key==="Escape"){[].slice.call(document.querySelectorAll(".scrim.on:not([data-locked])")).forEach(function(s){s.classList.remove("on");});selNode=null;selEdge=null;render();fillInspector();}
    if(mode==="view" && e.key>="1" && e.key<="4" && !typing){level=+e.key;setLevelButtons();render();}
    if((e.key==="Delete"||e.key==="Backspace")&&mode==="edit"&&selNode&&!typing){
      // a subSystems: node is provided by the referenced file; deleting it here would strip the
      // connections that name it while the subSystems: line still claimed to provide them. The
      // inspector offers no Delete button for one either.
      var sn=nodeById(selNode); if(sn&&sn.backing==="sub") return;
      pushUndo();
      project.connections=project.connections.filter(function(c){return c.from.n!==selNode&&c.to.n!==selNode;});
      project.nodes=project.nodes.filter(function(x){return x.id!==selNode;});selNode=null;render();fillInspector();}
  });
  addEventListener("beforeunload",function(e){
    if(!dirty) return;                  // clean since the last Commit: never nag
    e.preventDefault(); e.returnValue="";   // the browser supplies its own wording
  });

  // Restore prompt. NEVER silently override the project the companion rendered into this page:
  // name what is on offer, show both sides, and make the author choose.
  (function(){
    if(!storage) { updateHistoryUI(); return; }
    var raw=null, saved=null;
    try{ raw=storage.getItem(SAVE_KEY); }catch(e){ return; }
    if(!raw) return;
    try{ saved=JSON.parse(raw); }catch(e){ try{storage.removeItem(SAVE_KEY);}catch(e2){} return; }
    if(!saved||!saved.project||!saved.project.nodes){ try{storage.removeItem(SAVE_KEY);}catch(e){} return; }
    if(JSON.stringify(saved.project)===snapshot()) return;      // identical: nothing to decide
    function count(p){return (p.nodes||[]).length+" node(s) · "+(p.connections||[]).length+" connection(s)";}
    var when=new Date(saved.at||Date.now());
    document.getElementById("restoreInfo").innerHTML=
      'autosave &nbsp;"'+esc(saved.system||"")+'" — '+count(saved.project)+' — '+esc(when.toLocaleString())
      +'<br>seeded &nbsp;&nbsp;"'+esc((project.system&&project.system.name)||"")+'" — '+count(project)+' — rendered by the companion';
    var scrim=document.getElementById("restoreScrim"); scrim.classList.add("on");
    document.getElementById("doRestore").onclick=function(){
      pushSnapshot(snapshot());          // the seeded project stays one Ctrl+Z away
      applyState(JSON.stringify(saved.project));
      scrim.classList.remove("on");
    };
    document.getElementById("doDiscard").onclick=function(){
      try{ storage.removeItem(SAVE_KEY); }catch(e){}
      savedAt=null; scrim.classList.remove("on"); updateHistoryUI();
    };
  })();

  render();
  fillInspector();      // the idle inspector is the SYSTEM panel (fromFile, fromGitRepo), not
  updateHistoryUI();    // a placeholder, so it has to be painted before anything is selected
  // Open at 100% when the system fits, and only zoom OUT when it does not: a three-node
  // project blown up to fill the viewport looks like a rendering bug, and the author's mental
  // model of "actual size" is the one the drag handles work in.
  (function(){
    var b=contentBox(), pad=44, W=canvasWrap.clientWidth, H=canvasWrap.clientHeight;
    if(W<=0||H<=0) return;
    if(b.w+2*pad<=W&&b.h+2*pad<=H){ view.k=1; view.tx=pad-b.x; view.ty=pad-b.y; applyView(); }
    else fitView();
  })();
})();
</script>
</body>
</html>
'''
