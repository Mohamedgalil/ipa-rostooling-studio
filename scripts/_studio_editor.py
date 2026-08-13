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

  .canvas-wrap{flex:1;position:relative;overflow:auto;min-width:0}
  .canvas{position:relative;width:1600px;height:1100px;background-image:radial-gradient(circle,var(--rule-soft) 1px,transparent 1px);background-size:22px 22px}
  .canvas svg{position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:1}
  .node{position:absolute;z-index:2;background:var(--surface);border:1.5px solid var(--rule);border-radius:9px;box-shadow:var(--shadow);min-width:190px;user-select:none}
  .node.sel{border-color:var(--accent);box-shadow:var(--shadow-lift)}
  .node.cat{border-style:dashed}
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
  <div class="spacer"></div>
  <button class="tbtn" id="reset">Reset layout</button>
  <button class="tbtn" id="theme">&#9680; Theme</button>
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
  </div>

  <aside class="inspector empty" id="inspector">Select a node to edit it, or add one from the rail.</aside>
</div>

<datalist id="typelist"></datalist>
<datalist id="pkglist"></datalist>

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
  var BLOCK={pub:"publishers",sub:"subscribers",ss:"serviceservers",sc:"serviceclients",as:"actionservers",ac:"actionclients"};
  var TYPES=DATA.types||[], TYPESET={}; TYPES.forEach(function(t){TYPESET[t]=1;});
  var PACKAGES=DATA.packages||[];
  var CATALOGUE=DATA.catalogue||{};
  var CATTYPES=DATA.catalogueTypes||{};   // {pkg.node: {ifaceName: type}} from the vendored .ros2

  var project=DATA.project;
  project.nodes=project.nodes||[];
  project.connections=project.connections||[];
  var DIAG=(project.diagnostics&&project.diagnostics.byNode)||{};
  var uid=1000; function nid(){return "x"+(++uid);}

  var HOME=project.nodes.map(function(n){return {id:n.id,x:n.x,y:n.y};});

  var canvas=document.getElementById("canvas"), svg=document.getElementById("wires"),
      inspector=document.getElementById("inspector");
  STUDIO.makeArrowMarkers(svg,"");
  var selNode=null, selEdge=null, addKind="pub", mode="edit", level=3;
  var kindShown={}; KINDS.forEach(function(k){kindShown[k]=true;});

  document.getElementById("sysname").value=(project.system&&project.system.name)||"system";
  if(DATA.banner){ var b=document.getElementById("banner"); b.className="banner err"; b.innerHTML="<b>"+esc(DATA.banner)+"</b>"; }

  // ---- datalists (offline autocomplete) ----
  (function(){
    var tl=document.getElementById("typelist");
    TYPES.forEach(function(t){var o=document.createElement("option");o.value=t;tl.appendChild(o);});
    var pl=document.getElementById("pkglist");
    PACKAGES.forEach(function(p){var o=document.createElement("option");o.value=p;pl.appendChild(o);});
  })();

  function nodeById(id){for(var i=0;i<project.nodes.length;i++)if(project.nodes[i].id===id)return project.nodes[i];return null;}
  function ifaceById(n,id){if(!n)return null;for(var i=0;i<n.ifaces.length;i++)if(n.ifaces[i].id===id)return n.ifaces[i];return null;}

  // ============================ render ============================
  function render(){
    canvas.className="canvas "+(level===4?"deps":"lvl"+level);
    [].slice.call(canvas.querySelectorAll(".node,.pkgbox")).forEach(function(e){e.remove();});
    for(var i=0;i<project.nodes.length;i++) renderNode(project.nodes[i]);
    if(level===4) renderDeps();
    drawEdges();
    runIssues();
  }
  function renderNode(n){
    var el=document.createElement("div");
    el.className="node"+(n.backing==="cat"?" cat":"")+(selNode===n.id?" sel":"")+((DIAG[n.id]&&DIAG[n.id].length)?" hasdiag":"");
    el.style.left=n.x+"px"; el.style.top=n.y+"px"; el.dataset.n=n.id;
    var fromStr='"'+n.pkg+"."+n.node+'"';
    var h='<div class="nhead" data-drag><span class="ntitle">'+esc(n.label)+'</span>'
      +'<span class="badge '+(n.backing==="cat"?"cat":"")+'">'+(n.backing==="cat"?"catalogue":"authored")+'</span></div>'
      +'<div class="nfrom">from: '+esc(fromStr)+'</div><div class="ifaces"></div>';
    el.innerHTML=h;
    var box=el.querySelector(".ifaces");
    for(var j=0;j<n.ifaces.length;j++){
      var f=n.ifaces[j], src=SRC_SIDE[f.kind];
      var row=document.createElement("div");
      row.className="iface"; row.dataset.i=f.id; row.dataset.kind=f.kind;
      row.dataset.hidden=kindShown[f.kind]?"0":"1";
      row.innerHTML='<span class="kd '+f.kind+'">'+f.kind+'</span>'
        +'<span class="inm">'+esc(f.name)+'</span>'
        +'<span class="ity" title="'+esc(f.type||"")+'">'+esc(f.type||"—")+'</span>'
        +'<span class="port '+(src?"src":"snk")+' '+f.kind+'" data-n="'+n.id+'" data-i="'+f.id+'" data-kind="'+f.kind+'" data-src="'+src+'" data-type="'+esc(f.type||"")+'"></span>';
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
  function portCenter(nId,iId){
    var p=canvas.querySelector('.port[data-n="'+nId+'"][data-i="'+iId+'"]');
    var cr=canvas.getBoundingClientRect();
    if(p){var pr=p.getBoundingClientRect(); if(pr.width>0) return {x:pr.left-cr.left+pr.width/2,y:pr.top-cr.top+pr.height/2};}
    // fall back to node-box centre (level 1 hides ports)
    var nb=canvas.querySelector('.node[data-n="'+nId+'"]');
    if(!nb) return null;
    var br=nb.getBoundingClientRect();
    return {x:br.left-cr.left+br.width/2, y:br.top-cr.top+br.height/2};
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
      var cr=canvas.getBoundingClientRect(), a=nb.getBoundingClientRect(), b=pe.getBoundingClientRect();
      var ax=a.right-cr.left, ay=a.top-cr.top+a.height/2, bx=b.left-cr.left, by=b.top-cr.top+b.height/2;
      var path=document.createElementNS(NS,"path"); path.setAttribute("class","depedge edge");
      path.setAttribute("marker-end","url(#ah)");
      path.setAttribute("d",STUDIO.bezier(ax,ay,bx,by)); svg.appendChild(path);
    });
  }

  // ============================ node drag ============================
  project.nodes.forEach(function(){});
  function wireCanvas(){
    canvas.addEventListener("pointerdown",function(ev){
      var head=ev.target.closest("[data-drag]");
      if(!head) return;
      var el=head.closest(".node"), n=nodeById(el.dataset.n);
      dragState={n:n,px:ev.clientX,py:ev.clientY,ox:n.x,oy:n.y,moved:0};
      try{el.setPointerCapture(ev.pointerId);}catch(e){}
    });
    canvas.addEventListener("pointermove",function(ev){
      if(!dragState) return;
      var ddx=ev.clientX-dragState.px, ddy=ev.clientY-dragState.py;
      dragState.moved+=Math.abs(ddx)+Math.abs(ddy);
      dragState.n.x=dragState.ox+ddx; dragState.n.y=dragState.oy+ddy;
      var el=canvas.querySelector('.node[data-n="'+dragState.n.id+'"]');
      el.style.left=dragState.n.x+"px"; el.style.top=dragState.n.y+"px"; drawEdges();
    });
    canvas.addEventListener("pointerup",function(ev){
      if(!dragState) return;
      var wasClick=dragState.moved<5, n=dragState.n; dragState=null;
      if(wasClick){selNode=n.id;selEdge=null;render();fillInspector();}
    });
    canvas.addEventListener("pointerdown",function(ev){ if(ev.target===canvas||ev.target===svg){selNode=null;selEdge=null;render();fillInspector();} });
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
      var s=portCenter(wire.from.n,wire.from.i), cr=canvas.getBoundingClientRect();
      var mx=ev.clientX-cr.left, my=ev.clientY-cr.top, rb=document.getElementById("rb");
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
        if(!dup) project.connections.push({id:nid(),from:{n:fromEnd.n,i:fromEnd.i},to:{n:toEnd.n,i:toEnd.i}});
      }
      wire=null;
      canvas.querySelectorAll(".port").forEach(function(p){p.classList.remove("legal","illegal");});
      var rb=document.getElementById("rb"); if(rb) rb.remove();
      render();
    });
  }
  var dragState=null, wire=null;
  wireCanvas();

  // ============================ inspector ============================
  function fillInspector(){
    if(selEdge){ return fillEdgeInspector(); }
    var n=selNode&&nodeById(selNode);
    if(!n){inspector.className="inspector empty";inspector.textContent="Select a node to "+(mode==="edit"?"edit":"inspect")+" it.";return;}
    inspector.className="inspector";
    if(mode!=="edit"){ return fillReadonlyNode(n); }
    var cat=n.backing==="cat";
    var ih='<div class="insec"><h4>node: '+esc(n.label)+'</h4>'
      +'<div class="fld"><label>label (rossystem instance)</label><input id="f_label" value="'+esc(n.label)+'"></div>'
      +'<div class="fld"><label>backing</label><div class="radio">'
      +'<label><input type="radio" name="bk" value="hand" '+(cat?"":"checked")+'> hand-authored</label>'
      +'<label><input type="radio" name="bk" value="cat" '+(cat?"checked":"")+'> catalogue</label></div></div>'
      +'<div class="fld"><label>package '+(cat?"":"(lowercase — uppercase is an ERROR)")+'</label><input id="f_pkg" list="pkglist" value="'+esc(n.pkg)+'" '+(cat?"disabled":"")+'></div>'
      +'<div class="fld"><label>node</label><input id="f_node" value="'+esc(n.node)+'" '+(cat?"disabled":"")+'></div>'
      +'<div class="fld"><label>artifact (arrow target base)</label><input id="f_art" value="'+esc(n.artifact||"")+'" '+(cat?"disabled":"")+'></div>'
      +'<div class="fld"><label>from: (derived)</label><div class="derived">"'+esc(n.pkg)+'.'+esc(n.node)+'"</div></div></div>';
    ih+='<div class="insec"><h4>interfaces</h4>';
    for(var j=0;j<n.ifaces.length;j++){var f=n.ifaces[j];
      var conn=ifaceConnected(n,f);
      ih+='<div class="iedit'+(f.orphan?" orphan":"")+'" data-i="'+f.id+'"><span class="kd '+f.kind+'" title="'+KIND_LABEL[f.kind]+'">'+f.kind+'</span>'
        +'<span class="grow"><span class="inm2">'+esc(f.name)+'</span><br><span class="ity2">'+esc(f.type||"—")+' · "'+esc(n.artifact||"")+'::'+esc(f.name)+'"</span>'
        +'<span class="lblrow"><input class="ilbl" data-lbl="'+f.id+'" value="'+esc(f.label||"")+'" placeholder="'+esc(f.name)+'" title="exposure label — the key written into the .rossystem. Blank derives it from the interface name.">'
        +'<label class="expchk" title="'+(conn?"connected — always exposed":"write this interface into the .rossystem even with nothing wired to it")+'">'
        +'<input type="checkbox" data-exp="'+f.id+'"'+((f.exposed||conn)?" checked":"")+(conn?" disabled":"")+'>expose</label></span></span>'
        +'<span class="del" data-del="'+f.id+'">✕</span></div>';
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
        +'<span class="del" data-delp="'+pp.id+'">✕</span></div>';
    }
    ih+='<div class="addform"><input id="np_name" placeholder="param name">'
      +'<select id="np_type"><option>Integer</option><option>Double</option><option>String</option><option>Boolean</option></select>'
      +'<input id="np_val" placeholder="value (typed-safe: no True/int traps)">'
      +'<button class="minibtn" id="np_add">+ add parameter</button></div></div>';
    ih+='<button class="delnode" id="delNode">Delete node</button>';
    inspector.innerHTML=ih;
    wireInspector(n);
  }
  function fillReadonlyNode(n){
    var rows=n.ifaces.map(function(f){return f.kind+"  "+f.name+(f.type?"  "+f.type:"");}).join("\n")||"(none)";
    var pr=n.params.map(function(p){return p.name+" : "+p.ptype+" = "+p.value;}).join("\n")||"(none)";
    inspector.innerHTML='<div class="insec"><h4>node: '+esc(n.label)+'</h4>'
      +'<div class="roinfo">from: "'+esc(n.pkg)+'.'+esc(n.node)+'"<br>backing: '+n.backing+'<br>artifact: '+esc(n.artifact||"")+'</div></div>'
      +'<div class="insec"><h4>interfaces</h4><pre class="roinfo" style="white-space:pre-wrap">'+esc(rows)+'</pre></div>'
      +'<div class="insec"><h4>parameters</h4><pre class="roinfo" style="white-space:pre-wrap">'+esc(pr)+'</pre></div>'
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
    if(mode==="edit") h+='<button class="delnode" id="delEdge">Delete connection</button>';
    h+='</div>';
    inspector.innerHTML=h;
    var de=document.getElementById("delEdge");
    if(de) de.onclick=function(){project.connections=project.connections.filter(function(x){return x.id!==c.id;});selEdge=null;render();fillInspector();};
  }
  function wireInspector(n){
    document.getElementById("f_label").oninput=function(e){n.label=e.target.value;render();};
    var pkg=document.getElementById("f_pkg"), nod=document.getElementById("f_node"), art=document.getElementById("f_art");
    if(pkg) pkg.oninput=function(e){n.pkg=e.target.value.toLowerCase();e.target.value=n.pkg;render();};
    if(nod) nod.oninput=function(e){n.node=e.target.value;render();};
    if(art) art.oninput=function(e){n.artifact=e.target.value;render();};
    inspector.querySelectorAll("[name=bk]").forEach(function(r){r.onchange=function(e){n.backing=e.target.value;render();fillInspector();};});
    inspector.querySelectorAll("[data-del]").forEach(function(x){x.onclick=function(){
      var id=x.dataset.del; n.ifaces=n.ifaces.filter(function(f){return f.id!==id;});
      project.connections=project.connections.filter(function(c){return !((c.from.n===n.id&&c.from.i===id)||(c.to.n===n.id&&c.to.i===id));});
      render();fillInspector();};});
    inspector.querySelectorAll("[data-delp]").forEach(function(x){x.onclick=function(){n.params=n.params.filter(function(p){return p.id!==x.dataset.delp;});render();fillInspector();};});
    inspector.querySelectorAll("[data-lbl]").forEach(function(x){x.oninput=function(){
      var f=ifaceById(n,x.dataset.lbl); if(!f) return;
      f.label=x.value.trim()||null;    // NOT a repair for `orphan` -- that is about the arrow
      render();};});                   // TARGET (f.name), which the backing artifact must declare
    inspector.querySelectorAll("[data-exp]").forEach(function(x){x.onchange=function(){
      var f=ifaceById(n,x.dataset.exp); if(!f) return;
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
      // a hand-added interface is exposed on sight: the author typed it in to model it, so it
      // belongs in the .rossystem whether or not it is wired up yet.
      n.ifaces.push({id:nid(),name:nm,kind:addKind,type:document.getElementById("ni_type").value.trim()||null,qos:null,label:null,exposed:true});
      render();fillInspector();};
    var pAdd=document.getElementById("np_add");
    if(pAdd) pAdd.onclick=function(){
      var nm=document.getElementById("np_name").value.trim(); if(!nm) return;
      var t=document.getElementById("np_type").value, raw=document.getElementById("np_val").value.trim(), val=raw;
      if(t==="Boolean") val=/^(t|1|y|true)/i.test(raw)?"true":"false";
      else if(t==="Integer") val=String(parseInt(raw||"0",10)||0);
      else if(t==="Double") val=(raw.indexOf(".")>=0?raw:String((parseFloat(raw||"0")||0).toFixed(1)));
      n.params.push({id:nid(),name:nm,ptype:t,value:val});
      render();fillInspector();};
    var del=document.getElementById("delNode");
    if(del) del.onclick=function(){
      project.connections=project.connections.filter(function(c){return c.from.n!==n.id&&c.to.n!==n.id;});
      project.nodes=project.nodes.filter(function(x){return x.id!==n.id;});
      selNode=null;render();fillInspector();};
  }

  // ============================ rail ============================
  document.getElementById("addNode").onclick=function(){
    var n={id:nid(),label:"new_node",backing:"hand",pkg:"new_package",node:"new_node",artifact:"new_node",
      catalogueFile:null,x:200+Math.random()*120,y:340+Math.random()*80,ifaces:[],params:[]};
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
    var parts=key.split("."), pkg=parts[0], node=parts.slice(1).join(".");
    var tmap=CATTYPES[key]||{};   // real interface types recovered from the vendored .ros2
    var n={id:nid(),label:node,backing:"cat",pkg:pkg,node:node,artifact:e.artifact||node,catalogueFile:e.file||null,
      x:220+Math.random()*140,y:120+Math.random()*120,
      // a catalogue node arrives with its FULL interface set; exposing all of it would write
      // dozens of unwired lines, so these start unexposed and surface as you connect them.
      ifaces:Object.keys(e.interfaces||{}).map(function(nm){return {id:nid(),name:nm,kind:e.interfaces[nm],type:tmap[nm]||null,qos:null,label:null,exposed:false};}),params:[]};
    project.nodes.push(n); selNode=n.id; catScrim.classList.remove("on"); render(); fillInspector();
  }
  [].slice.call(document.querySelectorAll("[data-close]")).forEach(function(b){b.onclick=function(e){e.target.closest(".scrim").classList.remove("on");};});
  [].slice.call(document.querySelectorAll(".scrim")).forEach(function(s){s.onclick=function(e){if(e.target===s)s.classList.remove("on");};});

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
      var seen={};
      for(var j=0;j<n.ifaces.length;j++){var f=n.ifaces[j];
        if(seen[f.name]) issues.push(["w",n.label+": duplicate interface name \""+f.name+"\""]); seen[f.name]=1;
        // B2: a hand-authored interface with no type blocks generation (server can't resolve it)
        if(n.backing==="hand" && (!f.type||String(f.type).trim()==="")) issues.push(["e",n.label+": interface \""+f.name+"\" ("+f.kind+") has no message type"]);
      }
      if(!project.nodes.length){}
      if(DIAG[n.id]) DIAG[n.id].forEach(function(m){issues.push(["e",m]);});
    }
    for(var l in labels) if(labels[l]>1) issues.push(["e",'duplicate node label "'+l+'" (RM009)']);
    if(!project.nodes.length) issues.push(["e","system has no nodes — add one before generating (the server rejects an empty nodes: block)"]);
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
    var labels={}, used={};
    wanted.forEach(function(p){                       // pass 1: source labels are authoritative
      var lbl=(p[1].label||"").trim();
      if(lbl&&!used[lbl]){used[lbl]=1;labels[p[0].id+"/"+p[1].id]=lbl;}
    });
    var rest=wanted.filter(function(p){return !labels[p[0].id+"/"+p[1].id];});
    var counts={}; rest.forEach(function(p){counts[p[1].name]=(counts[p[1].name]||0)+1;});
    rest.forEach(function(p){                         // pass 2: derive, avoiding pass-1 names
      var n=p[0], f=p[1], lbl=(counts[f.name]>1)?f.name+"_"+f.kind:f.name;
      if(used[lbl]) lbl=f.name+"_"+f.kind+"_"+n.label.replace(/[^A-Za-z0-9_]/g,"_");
      var sfx=2; while(used[lbl]){lbl=f.name+"_"+f.kind+"_"+n.label.replace(/[^A-Za-z0-9_]/g,"_")+"_"+sfx; sfx++;}
      used[lbl]=1; labels[n.id+"/"+f.id]=lbl;
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
    var o=name+":\n";
    if(project.system&&project.system.fromFile) o+='  fromFile: '+qd(project.system.fromFile)+'\n';
    o+="  nodes:\n";
    project.nodes.forEach(function(n){
      o+='    '+qd(n.label)+':\n      from: '+qd(n.pkg+"."+n.node);
      o+=(n.backing==="cat"&&n.catalogueFile)?"  # assets/rosmodelscatalog/"+n.catalogueFile+"\n":"\n";
      var exposed=n.ifaces.filter(function(f){return labels[n.id+"/"+f.id];});
      if(exposed.length){
        o+="      interfaces:\n";
        exposed.forEach(function(f){o+='        - '+qd(labels[n.id+"/"+f.id])+': '+f.kind+'-> '+qd((n.artifact||"")+"::"+f.name)+'\n';});
      }
    });
    if(project.connections.length){
      o+="  connections:\n";
      project.connections.forEach(function(c){
        var fl=labels[c.from.n+"/"+c.from.i], tl=labels[c.to.n+"/"+c.to.i];
        if(fl&&tl) o+='    - ['+qd(fl)+', '+qd(tl)+']\n';
      });
    }
    return o;
  }
  function genRos2(n){
    var o=n.pkg.toLowerCase()+":\n  artifacts:\n    "+(n.artifact||n.node)+":\n      node: "+n.node+"\n";
    KINDS.forEach(function(k){
      var fs=n.ifaces.filter(function(f){return f.kind===k;}).sort(function(a,b){return a.name<b.name?-1:1;});
      if(!fs.length) return;
      o+="      "+BLOCK[k]+":\n";
      fs.forEach(function(f){o+="        "+qs2(f.name)+":\n          type: "+qs2(f.type||"TODO_pkg/msg/Type")+"\n";});
    });
    if(n.params.length){
      o+="      parameters:\n";
      n.params.forEach(function(p){o+="        "+qs2(p.name)+":\n          type: "+p.ptype+"\n          default: "+(p.ptype==="String"?qs2(p.value):p.value)+"\n";});
    }
    return o;
  }
  function genProjectJson(){
    project.system=project.system||{}; project.system.name=document.getElementById("sysname").value;
    return JSON.stringify(project,null,2);
  }
  var commitScrim=document.getElementById("commitScrim");
  document.getElementById("commit").onclick=function(){commitScrim.classList.add("on");document.getElementById("copyBox").value=genProjectJson();showGen("system");};
  function showGen(tab){
    var tabs=[["system",".rossystem"],["ros2",".ros2 (per package)"],["json","project.json"]];
    var tb=document.getElementById("genTabs"); tb.innerHTML="";
    tabs.forEach(function(t){var bt=document.createElement("button");bt.textContent=t[1];bt.className=t[0]===tab?"on":"";bt.onclick=function(){showGen(t[0]);};tb.appendChild(bt);});
    var out="";
    if(tab==="system") out=genSystem();
    else if(tab==="ros2") out=project.nodes.filter(function(n){return n.backing==="hand";}).map(genRos2).join("\n");
    else out=genProjectJson();
    document.getElementById("genOut").textContent=out;
  }
  document.getElementById("dlJson").onclick=function(){
    var blob=new Blob([genProjectJson()],{type:"application/json"});
    var url=URL.createObjectURL(blob), a=document.createElement("a");
    a.href=url; a.download=(document.getElementById("sysname").value||"project")+".project.json";
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
  };
  document.getElementById("selJson").onclick=function(){var t=document.getElementById("copyBox");t.focus();t.select();try{document.execCommand("copy");}catch(e){}};

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

  // ============================ misc ============================
  STUDIO.wireTheme(document.getElementById("theme"));
  document.getElementById("reset").onclick=function(){HOME.forEach(function(h){var n=nodeById(h.id);if(n){n.x=h.x;n.y=h.y;}});render();};
  document.getElementById("sysname").oninput=function(e){project.system=project.system||{};project.system.name=e.target.value;};
  addEventListener("keydown",function(e){
    if(e.key==="Escape"){[].slice.call(document.querySelectorAll(".scrim.on")).forEach(function(s){s.classList.remove("on");});selNode=null;selEdge=null;render();fillInspector();}
    if(mode==="view" && e.key>="1" && e.key<="4" && document.activeElement.tagName!=="INPUT"){level=+e.key;setLevelButtons();render();}
    if((e.key==="Delete"||e.key==="Backspace")&&mode==="edit"&&selNode&&document.activeElement.tagName!=="INPUT"){
      project.connections=project.connections.filter(function(c){return c.from.n!==selNode&&c.to.n!==selNode;});
      project.nodes=project.nodes.filter(function(x){return x.id!==selNode;});selNode=null;render();fillInspector();}
  });

  render();
})();
</script>
</body>
</html>
'''
