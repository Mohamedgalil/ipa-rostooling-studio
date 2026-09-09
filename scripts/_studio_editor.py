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
<script>/*__THEME_BOOT__*/</script>
<script>
/* Same reason the theme is restored up here rather than in the body script: the panels would
   otherwise paint at their default widths and jump to the stored ones on the next frame. Runs
   before the stylesheet below is parsed, so the custom properties are already set the first
   time .rail/.inspector are laid out. Deliberately does no clamping -- the body script re-clamps
   against the live viewport once it can measure one; this only has to avoid the flash. */
try{
  var pw=JSON.parse(localStorage.getItem("rosStudio.panelWidths")||"{}");
  if(pw&&typeof pw.rail==="number") document.documentElement.style.setProperty("--rail-w",pw.rail+"px");
  if(pw&&typeof pw.insp==="number") document.documentElement.style.setProperty("--insp-w",pw.insp+"px");
}catch(e){}
</script>
<style>
/*__PALETTE_CSS__*/
  *{box-sizing:border-box}
  /* The browser's own [hidden]{display:none} lives in the UA stylesheet, and ANY author rule
     that sets `display` beats it -- specificity never enters into it, author always wins over
     UA. So `el.hidden=true` on an element whose class sets a display silently does nothing.
     This has now bitten twice (the .secdot dot, then the issue-list's collapsible groups, whose
     .itkids sets display:flex -- so a "collapsed" group stayed fully expanded while its caret
     and aria-expanded both claimed otherwise). One rule here ends the whole class of it rather
     than adding a [hidden] override per element forever. */
  [hidden]{display:none!important}
  html,body{height:100%}
  body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--body);font-size:14px;-webkit-font-smoothing:antialiased;display:flex;flex-direction:column;overflow:hidden}
  button{font-family:inherit}
  .srOnly{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap}
  /* status chip, beside the system name -- replaces the old full-width instructional banner,
     which spent the WARN colour on text that was never a warning and so taught everyone to
     ignore it (see the comment above buildStatus()). ok is deliberately NOT --accent: that
     token means selection/brand elsewhere on this page, and a chip idling green in the toolbar
     would compete with it. */
  .statuschip{font-family:var(--mono);font-size:.68rem;font-weight:700;border-radius:999px;padding:.15rem .55rem;display:inline-flex;align-items:center;gap:.3rem;cursor:pointer;border:1px solid var(--rule);background:var(--surface-2);color:var(--ink-3);line-height:1.5}
  .statuschip:hover{filter:brightness(0.97)}
  .statuschip:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  .statuschip.warn{background:var(--warn-wash);color:var(--warn);border-color:var(--warn)}
  .statuschip.err{background:var(--dead-wash);color:var(--dead);border-color:var(--dead)}
  .statuschip.pulse{animation:chippulse 1.2s ease-out 2}
  @keyframes chippulse{0%{box-shadow:0 0 0 0 var(--dead-wash)}70%{box-shadow:0 0 0 7px transparent}100%{box-shadow:0 0 0 0 transparent}}
  @media (prefers-reduced-motion:reduce){.statuschip.pulse{animation:none}}
  #statusPop,#nodeIssuePop{position:fixed;margin:0;width:min(380px,calc(100vw - 1.5rem));max-height:70vh;overflow:auto;
    background:var(--surface);color:var(--ink);border:1px solid var(--rule);border-radius:10px;
    box-shadow:var(--shadow-lift);padding:.75rem .85rem .75rem 2.1rem;font-size:.78rem;line-height:1.45}
  #statusPop::backdrop,#nodeIssuePop::backdrop{background:transparent}
  #statusPop .popclose,#nodeIssuePop .popclose{position:absolute;top:.5rem;right:.5rem;width:1.4rem;height:1.4rem;border-radius:50%;
    border:none;background:transparent;color:var(--ink-3);font-size:1rem;line-height:1;cursor:pointer}
  #statusPop .popclose:hover,#nodeIssuePop .popclose:hover{background:var(--surface-2);color:var(--ink)}
  #statusPop h5,#nodeIssuePop h5{margin:0 0 .35rem;font-family:var(--mono);font-size:.64rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}
  #statusPop .poprow,#nodeIssuePop .poprow{padding:.45rem 0;border-top:1px solid var(--rule-soft)}
  #statusPop .poprow:first-child,#nodeIssuePop .poprow:first-child{padding-top:0;border-top:none}
  #statusPop pre,#nodeIssuePop pre{white-space:pre-wrap;font-family:var(--mono);font-size:.72rem;color:var(--dead);margin:0}
  #statusPop .popissue,#nodeIssuePop .popissue{display:block;width:100%;text-align:left;background:none;border:none;border-left:2px solid var(--warn);padding:.15rem 0 .15rem .5rem;font-size:.74rem;color:var(--ink-2);cursor:pointer}
  #statusPop .popissue.e,#nodeIssuePop .popissue.e{border-color:var(--dead)}
  #statusPop .popissue:hover,#nodeIssuePop .popissue:hover{background:var(--surface-2)}
  #statusPop .popissue.noref,#nodeIssuePop .popissue.noref{cursor:default}
  #statusPop .popissue.noref:hover,#nodeIssuePop .popissue.noref:hover{background:none}
  #statusPop .popfoot,#nodeIssuePop .popfoot{margin-top:.5rem}
  /* the node-issue popover's row is heavier than a status-popover row: it carries the "what to
     do", which the status popover leaves to the rail. */
  #nodeIssuePop .popissuewrap{border-left:2px solid var(--warn);padding:.3rem 0 .3rem .5rem;margin-bottom:.3rem}
  #nodeIssuePop .popissuewrap.e{border-color:var(--dead)}
  #nodeIssuePop .popissuewrap button.popissue{border-left:none;padding:0;margin-bottom:.15rem;font-weight:600}
  #statusPop .popfix,#nodeIssuePop .popfix{color:var(--ink-3);font-size:.72rem;line-height:1.35;margin-top:.1rem}

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
  .insptabs{width:100%;margin-bottom:.8rem}
  .insptabs button{flex:1;text-align:center}
  .savestate{font-family:var(--mono);font-size:.66rem;color:var(--ink-3);white-space:nowrap}
  .savestate.warn{color:var(--warn)}
  .tbtn{font-size:.78rem;font-weight:600;color:var(--ink-2);background:var(--surface);border:1px solid var(--rule);border-radius:6px;padding:.4rem .7rem;cursor:pointer}
  .tbtn:hover{color:var(--ink);border-color:var(--ink-3)}
  .tbtn.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
  .tbtn.primary:hover{background:var(--accent-2)}

  .main{flex:1;display:flex;min-height:0}
  .rail{width:var(--rail-w,190px);flex-shrink:0;border-right:1px solid var(--rule);background:var(--surface);display:flex;flex-direction:column;gap:1rem;padding:.85rem;overflow-y:auto}
  /* A 5px grab target is a miss more often than a hit, so the hit area is widened with a
     transparent margin that eats into the neighbours -- the VISIBLE line stays 1px (the
     panel's own border), which is what the layout was designed around. */
  .resizer{flex:0 0 5px;margin:0 -2px;position:relative;z-index:5;cursor:col-resize;
    background:transparent;transition:background .12s ease}
  .resizer:hover,.resizer:focus-visible,.resizer.dragging{background:var(--accent);outline:none}
  .resizer:focus-visible{box-shadow:0 0 0 2px var(--accent-wash)}
  /* While a drag is live the pointer is captured by the handle, so it can leave it -- and any
     text it crosses would select, and every hovered element would flicker its own cursor. */
  body.resizing{cursor:col-resize;user-select:none;-webkit-user-select:none}
  body.resizing .canvas-wrap{pointer-events:none}
  @media (prefers-reduced-motion:reduce){ .resizer{transition:none} }
  .rail h4{margin:0 0 .35rem;font-family:var(--mono);font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-2);font-weight:700}
  .rail .secbody{display:flex;flex-direction:column;gap:.4rem}
  body.mode-view .editonly{display:none}
  .railbtn{display:flex;align-items:center;gap:.45rem;font-size:.8rem;font-weight:600;color:var(--ink);background:var(--surface-2);border:1px solid var(--rule);border-radius:6px;padding:.45rem .55rem;cursor:pointer;text-align:left}
  .railbtn:hover{border-color:var(--accent)}
  .railbtn .plus{color:var(--accent);font-weight:700}
  .filter label{display:flex;align-items:center;gap:.4rem;font-size:.76rem;color:var(--ink-2);padding:.12rem 0;cursor:pointer}
  .filter .sw{width:11px;height:11px;border-radius:3px;flex-shrink:0}
  .filter input{accent-color:var(--accent);width:13px;height:13px}
  /* a system name is long and arbitrary (it is a filename stem), so it gets the flexible column
     and truncates, while the node count stays pinned and readable at the right. */
  .filter .sysnm{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-family:var(--mono);font-size:.7rem}
  .filter .syscnt{flex:none;font-family:var(--mono);font-size:.66rem;color:var(--ink-3)}
  .sysfoot{margin-top:.4rem;font-size:.68rem;line-height:1.35;color:var(--ink-3)}
  /* "seed from ROS 2 source" panel */
  .srcform{display:flex;flex-direction:column;gap:.6rem;margin:.6rem 0}
  .srcform label{display:flex;flex-direction:column;gap:.2rem;font-size:.78rem;font-weight:600;color:var(--ink-2)}
  .srcform input{font-family:var(--mono);font-size:.76rem;padding:.35rem .45rem;border:1px solid var(--rule);border-radius:5px;background:var(--surface);color:var(--ink)}
  .srcform input:focus{outline:none;border-color:var(--accent)}
  .srcform .hint{font-weight:400;font-size:.68rem;line-height:1.35;color:var(--ink-3)}
  .srcform .req{font-weight:700;font-size:.62rem;letter-spacing:.04em;text-transform:uppercase;color:var(--dead)}
  .srcstate{font-size:.72rem;color:var(--ink-3);align-self:center}
  .srcstate.bad{color:var(--dead)}
  /* an unfilled placeholder must be impossible to miss in the copied block */
  .gen .ph{background:var(--dead-wash);color:var(--dead);font-weight:700;border-radius:3px;padding:0 .15rem}
  .issues .row{display:flex;align-items:center;gap:.45rem;font-size:.78rem;padding:.2rem 0}
  .issues .cnt{font-family:var(--mono);font-weight:700}
  .issues .err{color:var(--dead)} .issues .wrn{color:var(--warn)} .issues .ok{color:var(--accent-2)}
  .issuelist{display:flex;flex-direction:column;gap:.3rem;margin-top:.3rem}
  .issuelist .it{font-size:.72rem;line-height:1.3;color:var(--ink-2);border-left:2px solid var(--warn);padding:.15rem 0 .15rem .45rem;
    display:flex;gap:.4rem;align-items:baseline}
  .issuelist .it.e{border-color:var(--dead)}
  .issuelist .ittext{flex:1;text-align:left}
  .issuelist .itcode{font-family:var(--mono);font-size:.9em;color:var(--ink-3);flex-shrink:0}
  .issuelist .itfix{font-weight:400;color:var(--ink-3);font-size:.92em;line-height:1.35;margin-top:.1rem}
  .itgroup .itgrouphead{width:100%}
  .itkids{padding-left:.6rem;margin-top:.25rem;display:flex;flex-direction:column;gap:.25rem;border-left:1px dashed var(--rule-soft)}
  /* a row with somewhere to jump to -- what's interactive should look interactive */
  button.it{width:100%;background:transparent;border:none;border-left:2px solid var(--warn);cursor:pointer;font:inherit;color:var(--ink-2)}
  button.it.e{border-color:var(--dead)}
  button.it:hover{background:var(--surface-2)}
  button.it:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
  .issuelist .it.noref{cursor:default}
  .issuelist .it.ok{border-color:var(--accent);color:var(--accent-2)}
  .issuelist .itmini{margin-left:.4rem;font-size:.9em;padding:.05rem .4rem;border-radius:4px;border:1px solid var(--rule);background:var(--surface);color:var(--ink-2);cursor:pointer;flex-shrink:0}
  .issuelist .itmini:hover{background:var(--surface-2)}
  .issuelist .itmore{font-size:.72rem;color:var(--ink-3);background:transparent;border:none;text-decoration:underline;cursor:pointer;padding:.2rem 0;text-align:left}
  /* transient "you just clicked this" pointer, distinct from .sel (current selection, accent) and
     .hasdiag (persistent, the server's verdict) */
  .node.flash{border-color:var(--warn)!important;box-shadow:0 0 0 3px var(--warn-wash),var(--shadow-lift)!important}
  .node.flash.e{border-color:var(--dead)!important;box-shadow:0 0 0 3px var(--dead-wash),var(--shadow-lift)!important}
  .iedit.flash,.pkgrow.flash,input.flash{outline:2px solid var(--warn);outline-offset:1px}
  .iedit.flash.e,.pkgrow.flash.e,input.flash.e{outline:2px solid var(--dead)}

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
  /* the typeahead dropdown -- see makeTypeahead(). position:fixed + document.body so it floats
     free of the canvas's own zoom/pan transform (the input it belongs to may be inside that
     transform; the dropdown never should be) and free of the inspector's overflow:auto clipping. */
  .typeahead-box{position:fixed;z-index:80;max-height:280px;overflow:auto;
    background:var(--surface);border:1px solid var(--rule);border-radius:8px;box-shadow:var(--shadow-lift);
    padding:.25rem;font-size:.78rem}
  .typeahead-box .ta-row{padding:.3rem .5rem;border-radius:5px;cursor:pointer;font-family:var(--mono);
    white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .typeahead-box .ta-row.active,.typeahead-box .ta-row:hover{background:var(--accent-wash);color:var(--accent-2)}
  .typeahead-box .ta-empty{padding:.3rem .5rem;color:var(--ink-3)}
  .typeahead-box .ta-divider{padding:.3rem .5rem .15rem;font-family:var(--mono);font-size:.64rem;
    letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3)}
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
  /* origin system: which source .rossystem this node was merged/imported from. The index class
     only sets two custom properties, so the rule that PAINTS is `.node.orig` at the same
     specificity as .sel / .hasdiag / .issue-e -- and it is written above them on purpose, so
     selection and diagnostics win the border back. Where a card came from matters less than
     "this one is selected" or "the server rejected this one". */
  .node.s0{--org:var(--s0);--org-bg:var(--s0-bg)}
  .node.s1{--org:var(--s1);--org-bg:var(--s1-bg)}
  .node.s2{--org:var(--s2);--org-bg:var(--s2-bg)}
  .node.s3{--org:var(--s3);--org-bg:var(--s3-bg)}
  .node.s4{--org:var(--s4);--org-bg:var(--s4-bg)}
  .node.s5{--org:var(--s5);--org-bg:var(--s5-bg)}
  .node.s6{--org:var(--s6);--org-bg:var(--s6-bg)}
  .node.s7{--org:var(--s7);--org-bg:var(--s7-bg)}
  /* a 5px left edge carries the identity even when the border colour is taken over by .sel or
     .hasdiag, so a selected card does not stop saying where it came from. */
  .node.orig{border-color:var(--org);border-left:5px solid var(--org)}
  .node.orig .nhead{background:var(--org-bg)}
  .node.sel{border-color:var(--accent);box-shadow:var(--shadow-lift)}
  .node.cat{border-style:dashed}
  /* a subSystems: node is not declared by THIS file -- dimmed and dotted so it reads as
     borrowed, and it is read-only everywhere in the inspector. */
  .node.sub{border-style:dotted;opacity:.9}
  .node.hasdiag{border-color:var(--dead)}
  /* live instant-check severity, distinct from .hasdiag (the server's own verdict from a prior
     Commit): an ERROR earns the same red border treatment, a WARNING only gets the icon below,
     not a border colour change -- most warnings here are informational (RM044 is legal and the
     server accepts it), and ringing every warned node in colour would just be noise. */
  .node.issue-e{border-color:var(--dead)}
  .node .nhead{display:flex;align-items:center;gap:.4rem;padding:.45rem .6rem;border-bottom:1px solid var(--rule-soft);cursor:grab}
  .node .nhead:active{cursor:grabbing}
  .node .ntitle{font-weight:650;font-size:.84rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;min-width:0}
  .node .nfrom{font-family:var(--mono);font-size:.63rem;color:var(--ink-3);padding:.25rem .6rem 0}
  .node .badge{font-family:var(--mono);font-size:.56rem;letter-spacing:.04em;text-transform:uppercase;padding:.06em .4em;border-radius:3px;background:var(--surface-2);color:var(--ink-3)}
  .node .badge.cat{background:var(--accent-wash);color:var(--accent-2)}
  .node .diagflag{font-size:.62rem;color:var(--dead);font-family:var(--mono);padding:.1rem .6rem .3rem}
  /* the per-node warning icon: persists for as long as nodeIssueIndex carries an entry for this
     node, and only that long -- see the comment above indexIssuesByNode(). */
  .node .nwarn{flex-shrink:0;display:inline-flex;align-items:center;justify-content:center;gap:.15rem;border:none;cursor:pointer;
    background:var(--warn-wash);color:var(--warn);border-radius:999px;padding:.2rem .45rem;font-size:.68rem;line-height:1.4;min-height:1.5rem}
  .node .nwarn.e{background:var(--dead-wash);color:var(--dead)}
  .node .nwarn:hover{filter:brightness(0.95)}
  .node .nwarn:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
  .node .nwarnc{font-family:var(--mono);font-weight:700}
  .ifaces{padding:.35rem .1rem .5rem}
  .iface{position:relative;display:flex;align-items:center;gap:.4rem;padding:.13rem .6rem;font-size:.75rem}
  .iface .kd{font-family:var(--mono);font-size:.56rem;font-weight:700;text-transform:uppercase;width:2.2em;text-align:center;border-radius:3px;padding:.05em 0;color:#fff}
  .iface .inm{font-weight:600}
  .iface .ity{font-family:var(--mono);font-size:.63rem;color:var(--ink-3);margin-left:auto;max-width:12ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  /* Parameters are NOT connectable -- no arrow kind, no port, no edge. They are drawn as a
     separate band below the interfaces so a node whose only content is parameters stops
     rendering as an empty box. */
  .params{border-top:1px dashed var(--rule);padding:.1rem 0 .15rem}
  .params .phead{font-size:.55rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-3);padding:.1rem .6rem .05rem}
  .prow{display:flex;align-items:center;gap:.4rem;padding:.1rem .6rem;font-size:.72rem}
  .prow .pk{font-family:var(--mono);font-size:.52rem;font-weight:700;text-transform:uppercase;width:2.2em;text-align:center;border-radius:3px;padding:.05em 0;color:#fff;background:var(--k-param);flex:none}
  .prow .pnm{font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .prow .plb{font-family:var(--mono);font-size:.58rem;color:var(--k-param);flex:none}
  .prow .pvl{font-family:var(--mono);font-size:.62rem;color:var(--ink-3);margin-left:auto;max-width:11ch;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .prow.orphan .pnm{text-decoration:underline wavy var(--bad)}
  .node.sysparams{border-style:dashed;border-color:var(--k-param)}
  /* ---- subsystem abstraction views ------------------------------------------------------
     A subSystems: reference is ONE reused composition. Three ways to look at it, all pure
     presentation: the state lives in project.view and is excluded from the fact tree, so
     collapsing, framing or drilling in cannot change one emitted byte. */
  /* the System level's container: one box per source system, coloured by that system's slot.
     Same shape as a collapsed subsystem box (below) because it is the same idea on a different
     axis -- a group of nodes standing as one unit, with the group's exposure labels as ports. */
  .node.sysbox{border-width:2px;border-color:var(--org);background:var(--surface);min-width:230px}
  .node.sysbox .nhead{background:var(--org-bg);gap:.3rem}
  .node.sysbox .nhead .sw{width:.6rem;height:.6rem;border-radius:2px;flex:none}
  .node.sysbox .nfrom{font-style:italic}
  .node.subbox{border-width:2px;border-color:var(--k-sub);background:var(--panel)}
  .node.subbox .nhead{background:color-mix(in srgb,var(--k-sub) 12%,transparent)}
  .node.subbox .nfrom{font-style:italic}
  .subtog{cursor:pointer;font-family:var(--mono);font-size:.62rem;padding:0 .25em;border-radius:3px;user-select:none}
  .subtog:hover{background:var(--hover)}
  .iface.unwired{opacity:.45}
  .iface .amb{font-size:.55rem;color:var(--warn);flex:none}
  /* the frame sits BEHIND the cards it encloses; the cards are position:absolute siblings */
  .subframe{position:absolute;border:2px dashed var(--k-sub);border-radius:12px;
            background:color-mix(in srgb,var(--k-sub) 5%,transparent);z-index:0;pointer-events:none}
  .subframe .sfhead{position:absolute;top:-.85rem;left:.8rem;background:var(--panel);
                    border:1px solid var(--k-sub);border-radius:999px;padding:.05rem .55rem;
                    font-size:.62rem;font-weight:700;color:var(--k-sub);pointer-events:auto;
                    display:flex;align-items:center;gap:.35rem;white-space:nowrap}
  .node{z-index:1}
  .drillbar{display:flex;align-items:center;gap:.5rem;padding:.3rem .7rem;border-bottom:1px solid var(--rule);
            background:color-mix(in srgb,var(--k-sub) 8%,var(--panel));font-size:.75rem}
  .drillbar b{font-family:var(--mono)}
  .drillbar .crumb{color:var(--ink-3)}
  .drillbar button{font-size:.7rem}
  .node.ro{opacity:.95}
  .node.ro .nhead{background:var(--wash)}
  .canvas.lvl2 .prow .pvl,.canvas.lvl2 .params .phead{display:none}
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
  .pkgbox{position:absolute;z-index:2;background:var(--surface-2);border:1.5px solid var(--ink-3);border-radius:9px;padding:.5rem .6rem;min-width:150px;font-size:.78rem;cursor:grab;user-select:none}
  .pkgbox:active{cursor:grabbing}
  .pkgbox.res{border-color:var(--accent-2)}
  .pkgbox.unres{border-color:var(--warn)}
  .pkgbox .pt{font-weight:650}
  .pkgbox .ps{font-family:var(--mono);font-size:.62rem;color:var(--ink-3);margin-top:.15rem}

  path.edge{fill:none;stroke:var(--edge);stroke-width:1.7;transition:stroke .12s,opacity .12s}
  path.edge.topic{marker-end:url(#ah)}
  path.edge.rr{marker-end:url(#ah);marker-start:url(#ahOpen)}
  path.edge.sel{stroke:var(--edge-hot);stroke-width:2.4}
  path.rubber{stroke:var(--edge-hot);stroke-width:2;stroke-dasharray:5 4;fill:none}

  .inspector{width:var(--insp-w,298px);flex-shrink:0;border-left:1px solid var(--rule);background:var(--surface);overflow-y:auto;padding:.85rem}
  .inspector.empty{display:flex;align-items:center;justify-content:center;color:var(--ink-3);font-size:.82rem;text-align:center;padding:2rem}
  .insec{margin-bottom:1rem}
  .insec h4{margin:0;font-family:var(--mono);font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-2);font-weight:700;border-top:1px solid var(--rule-soft)}
  .insec:first-child h4{border-top:none}
  .insec:first-child .sechead{padding-top:0}
  .sechead{display:flex;align-items:center;gap:.4rem;width:100%;background:none;border:none;cursor:pointer;color:inherit;font:inherit;letter-spacing:inherit;text-transform:inherit;padding:.6rem 0 .5rem;text-align:left}
  .sechead:hover .caret{color:var(--accent)}
  .sechead:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  .caret{display:inline-block;transition:transform .12s;color:var(--ink-3);font-size:.7em;flex-shrink:0}
  .secmeta{margin-left:auto;font-weight:400;color:var(--ink-3);display:flex;align-items:center;gap:.3rem;white-space:nowrap;text-transform:none;letter-spacing:normal}
  .secdot{width:6px;height:6px;border-radius:50%;display:inline-block;flex-shrink:0}
  .secdot[hidden]{display:none}
  .secdot.e{background:var(--dead)}
  .secdot.w{background:var(--warn)}
  .secbody{padding-bottom:.1rem}
  .insec.collapsed .secbody{display:none}
  .insec.collapsed .caret{transform:rotate(-90deg)}
  @media (prefers-reduced-motion:reduce){.caret{transition:none}}
  .fld{display:flex;flex-direction:column;gap:.2rem;margin-bottom:.5rem}
  .fld label{font-size:.7rem;color:var(--ink-3)}
  .fld input,.fld select{font-family:var(--mono);font-size:.76rem;background:var(--surface-2);border:1px solid var(--rule);border-radius:5px;padding:.3rem .4rem;color:var(--ink);width:100%}
  .fld .derived{font-family:var(--mono);font-size:.72rem;color:var(--ink-3);background:var(--surface-2);border:1px dashed var(--rule);border-radius:5px;padding:.3rem .4rem;word-break:break-all}
  .radio{display:flex;gap:.5rem;font-size:.76rem}
  .radio label{display:flex;align-items:center;gap:.3rem;cursor:pointer}
  .iedit{display:flex;align-items:center;gap:.4rem;font-size:.74rem;padding:.28rem .35rem;border:1px solid var(--rule-soft);border-radius:5px;margin-bottom:.3rem;background:var(--surface-2)}
  .iedit .kd{cursor:pointer;width:2.2em;text-align:center;border-radius:3px;color:#fff;font-family:var(--mono);font-size:.56rem;font-weight:700;text-transform:uppercase;padding:.1em 0}
  /* a <select> carrying the same .kd class as the read-only badge, so an editable kind looks
     IDENTICAL to a locked one -- appearance:none strips the native chrome a plain <span> never had. */
  select.kd{appearance:none;-webkit-appearance:none;-moz-appearance:none;border:none;align-self:flex-start}
  select.kd:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
  .iedit .grow{flex:1;min-width:0}
  .iedit .inm2{font-weight:600}
  .iedit .ity2{font-family:var(--mono);font-size:.62rem;color:var(--ink-3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  /* the row IS the editor: same field an existing interface/parameter is edited through is what
     a brand-new one (blank, from "+ interface") first appears as -- no separate add-form. */
  .iedit .iname,.iedit .itype{display:block;width:100%;font-family:inherit;font-size:.78rem;font-weight:600;
    padding:.12rem .3rem;border:1px solid var(--rule);border-radius:3px;background:var(--surface);color:var(--ink);margin-bottom:.15rem}
  .iedit .itype{font-family:var(--mono);font-size:.66rem;font-weight:400}
  .iedit .ity2.deriv{margin-bottom:.15rem;display:block}
  .addifacebtn,.addparambtn{width:100%}
  .iedit .del{cursor:pointer;color:var(--ink-3);font-weight:700}
  .iedit .del:hover{color:var(--dead)}
  .iedit .lblrow{display:flex;align-items:center;gap:.35rem;margin-top:.2rem}
  .iedit .ilbl{flex:1;min-width:0;font-family:var(--mono);font-size:.62rem;padding:.12rem .3rem;border:1px solid var(--rule);border-radius:3px;background:var(--surface);color:var(--ink)}
  .subempty{color:var(--dead);font-weight:600}
  .expose{margin-top:.4rem;padding-top:.35rem;border-top:1px solid var(--rule-soft)}
  .expose.none{border-top-color:var(--warn)}
  .expose .expnode{font-family:var(--mono);font-size:.62rem;color:var(--ink-3);margin:.3rem 0 .1rem}
  .expline{display:flex;align-items:center;gap:.3rem;font-size:.68rem;padding:.06rem 0;cursor:pointer}
  .expline input{margin:0}
  .expline .kd{flex:none;width:2.2em;text-align:center;border-radius:3px;color:#fff;font-family:var(--mono);
    font-size:.54rem;font-weight:700;text-transform:uppercase;padding:.05em 0}
  .expline .expname{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .bulkrow{display:flex;align-items:center;gap:.3rem;font-size:.66rem;color:var(--ink-3);margin-bottom:.35rem}
  .bulkrow .bulkcount{margin-left:auto;font-family:var(--mono);font-size:.62rem}
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
  /* NOT scoped to .cmtbox: cmtRows() is called bare in six places (the system panel, a
     subSystems: entry, a system parameter, a package, a connection) and only two of them wrap it
     in a .cmtbox. Scoped, those six rendered as an unstyled label beside a browser-default
     textarea -- ~20 rows tall, overflowing the panel and overlapping the row above. */
  .crow{display:flex;flex-direction:column;gap:.12rem;margin-bottom:.3rem}
  .crow label{font-size:.6rem;color:var(--ink-3)}
  .crow input,.crow textarea{width:100%;font-family:var(--mono);font-size:.66rem;line-height:1.4;background:var(--surface-2);border:1px solid var(--rule);border-radius:4px;padding:.15rem .25rem;color:var(--ink);resize:vertical}
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
  .askline{display:flex;align-items:center;gap:.4rem;font-size:.78rem;color:var(--ink-2);margin:.2rem 0}
  #wrapName{width:100%;font-family:inherit;font-size:.82rem;padding:.4rem .55rem;border:1px solid var(--rule);
    border-radius:5px;background:var(--surface);color:var(--ink);margin-bottom:.4rem}
  #wrapErr{color:var(--warn);font-size:.72rem;margin-bottom:.4rem}
  /* Transient, non-blocking confirmation for something the app did on its own (a type copied
     across a wire, N nodes imported). Deliberately NOT a modal and NOT the status chip: the
     point is to make an invisible action visible for a moment without asking for a click. */
  .toasts{position:fixed;left:50%;transform:translateX(-50%);bottom:1.1rem;z-index:95;
    display:flex;flex-direction:column;gap:.35rem;align-items:center;pointer-events:none}
  .toast{background:var(--ink);color:var(--paper);font-size:.75rem;padding:.4rem .8rem;border-radius:999px;
    box-shadow:0 6px 20px rgba(0,0,0,.22);opacity:0;transform:translateY(6px);
    transition:opacity .16s ease,transform .16s ease;max-width:min(70vw,520px);text-align:center}
  .toast.in{opacity:1;transform:none}
  @media (prefers-reduced-motion:reduce){ .toast{transition:none} }
  .ctxmenu{position:fixed;z-index:90;background:var(--surface);border:1px solid var(--rule);border-radius:7px;
    box-shadow:0 6px 20px rgba(0,0,0,.18);padding:.25rem;min-width:180px}
  .ctxmenu button{display:block;width:100%;text-align:left;padding:.4rem .6rem;font-family:inherit;
    font-size:.78rem;background:none;border:none;border-radius:4px;color:var(--ink);cursor:pointer}
  .ctxmenu button:hover{background:var(--surface-2)}

  /* ================================ the guided tutorial ================================
     A coach mark, not a slide deck. The whole point of the walkthrough is that the reader
     drives the REAL editor -- adds the real catalogue node, drags the real wire -- while this
     panel follows and reacts. So there is deliberately NO scrim behind it and nothing here ever
     swallows a click: .tourhalo is pointer-events:none, because an overlay that ringed a button
     and then ate the click aimed at it would be strictly worse than no tutorial at all.

     Positioned exactly the way .typeahead-box already is -- position:fixed, parented to
     document.body, placed from the anchor's getBoundingClientRect() and clamped to the viewport
     -- so it floats free of the canvas's zoom/pan transform (three steps point at ports on a
     card inside it) and free of the inspector's overflow:auto clipping. A second positioning
     scheme would have drifted from that one the first time either was fixed.

     z-index sits ABOVE .scrim (50): three steps point at controls inside the Commit modal, and
     one at the catalogue modal's search box. It stays below nothing -- toasts (95) are bottom
     centre and never collide with an anchored card. */
  .tourhalo{position:fixed;z-index:94;pointer-events:none;border:2px solid var(--accent);
    border-radius:8px;box-shadow:0 0 0 3px var(--accent-wash)}
  .tourhalo.pulse{animation:tourring 1.8s ease-out infinite}
  @keyframes tourring{0%{box-shadow:0 0 0 3px var(--accent-wash)}
                      70%{box-shadow:0 0 0 11px transparent}
                      100%{box-shadow:0 0 0 3px transparent}}
  /* The page kills every transition under reduced motion already (bottom of this stylesheet);
     an animation is not a transition, so the ring has to be turned off by name. It degrades to
     the static border+wash above, which is the part that actually carries the meaning. */
  @media (prefers-reduced-motion:reduce){.tourhalo.pulse{animation:none}}
  .tourcard{position:fixed;z-index:96;width:min(350px,calc(100vw - 1.5rem));background:var(--surface);
    color:var(--ink);border:1px solid var(--accent);border-radius:10px;box-shadow:var(--shadow-lift);
    padding:.65rem .8rem .55rem;font-size:.78rem;line-height:1.5}
  .tourcard:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  .tourcard .thead{display:flex;align-items:baseline;gap:.45rem;margin-bottom:.15rem}
  .tourcard .tstep{font-family:var(--mono);font-size:.6rem;letter-spacing:.09em;text-transform:uppercase;color:var(--ink-3);flex:none}
  .tourcard h5{margin:0;font-family:var(--display);font-size:.95rem;line-height:1.3;flex:1}
  .tourcard .tclose{flex:none;background:none;border:none;color:var(--ink-3);font-size:1rem;line-height:1;cursor:pointer;padding:0 .1rem}
  .tourcard .tclose:hover{color:var(--ink)}
  .tourcard .tclose:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
  .tourcard .tbody{color:var(--ink-2)}
  .tourcard .tbody p{margin:.4rem 0}
  .tourcard .tbody code{font-family:var(--mono);font-size:.92em;background:var(--surface-2);border-radius:3px;padding:0 .2em}
  .tourcard .twait{margin-top:.5rem;font-family:var(--mono);font-size:.68rem;line-height:1.4;
    color:var(--warn);background:var(--warn-wash);border-radius:5px;padding:.3rem .45rem}
  .tourcard .twait.done{color:var(--accent-2);background:var(--accent-wash)}
  .tourcard .tfoot{display:flex;align-items:center;gap:.35rem;margin-top:.55rem;padding-top:.5rem;border-top:1px solid var(--rule-soft)}
  .tourcard .tfoot .grow{flex:1}
  .tourcard .tfoot button{font-family:inherit;font-size:.72rem;padding:.3rem .55rem;border-radius:5px;
    cursor:pointer;border:1px solid var(--rule);background:var(--surface-2);color:var(--ink-2)}
  .tourcard .tfoot button.go{background:var(--accent);border-color:var(--accent);color:#fff;font-weight:600}
  .tourcard .tfoot button:disabled{opacity:.42;cursor:default}
  .tourcard .tfoot button:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
  .tourbar{display:flex;gap:2px;margin-top:.5rem}
  /* Colour is never the only channel here either: the bar repeats what "STEP 7 OF 15" already
     says in words, for the same reason the Source systems legend counts its rows. */
  .tourbar i{flex:1;height:3px;border-radius:2px;background:var(--rule)}
  .tourbar i.on{background:var(--accent)}

  /* ================================ small screens ================================
     The desktop layout is three columns: a 190px rail, the canvas, a 298px inspector. That is
     ~490px of chrome before any graph, so on a phone there was nothing left to draw on.

     Below the breakpoint the two side panels become OVERLAY DRAWERS: the canvas gets the whole
     viewport and each panel slides in over it, one at a time, behind a backdrop.

     Keyed off `body.narrow`, NOT a media query. The first attempt used @media (max-width:860px)
     while the JS asked matchMedia separately -- two independent judgements of one question,
     which is a bug waiting to happen and duly happened: on a phone the buttons appeared (so the
     query had matched for THAT rule) while the panels stayed in column flow. A class set once,
     from one measurement, cannot disagree with itself. It also survives a webview that ignores
     the viewport meta and lays the page out at some notional desktop width, because the
     measurement below consults screen.width too. */
  .drawerbtn{display:none}
  /* The persisted kind/param filter can hide content silently -- on a phone the rail carrying
     the checkboxes that explain why is behind this exact button, closed by default, so the
     one place a "something is filtered" cue can live is here. */
  #railToggle.hasfilter::after{content:"";width:6px;height:6px;border-radius:50%;background:var(--warn);margin-left:.15rem}
  .scrim.drawer{display:none}
  #drawerClose{display:none}
  body.narrow{font-size:15px}            /* 14px is below comfortable reading size on a phone */
  body.narrow .drawerbtn{display:inline-flex;align-items:center;gap:.3rem}
  /* One row that SCROLLS SIDEWAYS rather than a wrapping block. Twelve controls wrapped on a
     390px screen is four rows -- half the viewport gone before the graph starts. */
  body.narrow .topbar{flex-wrap:nowrap;overflow-x:auto;overflow-y:hidden;gap:.4rem;
                      padding:.4rem .55rem;-webkit-overflow-scrolling:touch;scrollbar-width:none}
  body.narrow .topbar::-webkit-scrollbar{display:none}
  body.narrow .topbar>*{flex:none}       /* or the segmented controls compress to unreadable */
  body.narrow .brand{font-size:.95rem}
  body.narrow .sysname{font-size:.76rem}
  body.narrow .sysname input{width:11ch}
  body.narrow .spacer{display:none}      /* a flex spacer in a scrolling row stretches forever */
  body.narrow .main{position:relative}
  /* Off-canvas, inside .main (not fixed) so a drawer is clipped to the app area and cannot
     slide up over the toolbar. */
  body.narrow .rail,body.narrow .inspector{
      position:absolute;top:0;bottom:0;z-index:40;width:min(84vw,320px);
      box-shadow:var(--shadow-lift);transition:transform .18s ease}
  /* Belt and braces: `visibility` and `pointer-events` as well as the transform. A closed
     drawer that is merely translated away is still a live, visible box if anything overrides
     `transform` -- a webview's injected stylesheet, a future rule of our own -- and the failure
     mode is the panel sitting open across the canvas with no obvious way out. Three properties
     have to be defeated for that to happen instead of one. */
  body.narrow .rail,body.narrow .inspector{visibility:hidden;pointer-events:none}
  body.narrow .rail{left:0;transform:translateX(-101%)}
  body.narrow .inspector{right:0;transform:translateX(101%)}
  body.narrow.drawer-l .rail{transform:translateX(0);visibility:visible;pointer-events:auto}
  body.narrow.drawer-r .inspector{transform:translateX(0);visibility:visible;pointer-events:auto}
  body.narrow .main{overflow:hidden}     /* an off-canvas panel must not make .main scrollable */
  /* A drawer overlays the canvas rather than sitting beside it, so there is no width to trade
     and nothing for a separator to separate. Its `width` above also overrides --rail-w/--insp-w
     outright, so a width dragged on a desktop cannot leak into the phone layout. */
  body.narrow .resizer{display:none}
  /* The backdrop covers .main ONLY. As a fixed full-page element it sat over the toolbar and
     swallowed taps on the very buttons that open and close the drawers. */
  body.narrow.drawer-l .scrim.drawer,body.narrow.drawer-r .scrim.drawer{
      display:block;position:absolute;inset:0;background:rgba(0,0,0,.34);z-index:39}
  /* An explicit close control, pinned to the drawer's inner edge. The backdrop and the toolbar
     button both close it too -- three independent ways out, because "I can never dismiss it"
     is the one failure mode that makes the whole panel worse than not having it. */
  #drawerClose{position:absolute;top:.5rem;z-index:41;font-size:1rem;line-height:1;
               padding:.35rem .5rem;min-width:34px;min-height:34px}
  body.narrow.drawer-l #drawerClose{display:block;left:calc(min(84vw,320px) - 2.9rem)}
  body.narrow.drawer-r #drawerClose{display:block;right:calc(min(84vw,320px) - 2.9rem)}
  /* The floating bars stack instead of sitting at opposite corners, and scroll sideways --
     the viewbar alone is wider than a phone. */
  body.narrow .findbar,body.narrow .viewbar{max-width:calc(100vw - 1.2rem);overflow-x:auto;
                                            flex-wrap:nowrap}
  body.narrow .findbar input{width:9ch}
  body.narrow .viewbar{bottom:.5rem;left:.5rem;right:.5rem}
  body.narrow .modal{width:96vw;max-height:90vh}
  /* A card that tracks an anchor needs room beside it, and on a phone there is none: anything
     placed under a topbar button covers half the canvas and anything placed under a rail button
     is inside a drawer. So it stops following and docks to the bottom edge, where it can never
     sit on top of the control the step is asking you to press. !important because tourPlace()
     writes top/left INLINE while tracking: it stops writing them once docked, but the ones from
     before the viewport narrowed are still on the element and would otherwise win. */
  body.narrow .tourcard{left:.5rem!important;right:.5rem!important;top:auto!important;
                        bottom:.5rem!important;width:auto!important;max-height:46vh;overflow-y:auto}
  /* At true phone width the wordmark is the one thing on the bar that does no work. */
  body.tiny .brand{display:none}
  body.tiny #levelSeg button{font-size:.7rem;padding:.34rem .45rem}
  body.tiny .findbar{top:.5rem;left:.5rem;right:.5rem}
  /* A finger is not a mouse pointer: 12px ports were unhittable. The visible dot keeps its size
     -- growing it would change how the graph reads -- and an invisible ::after enlarges the
     TOUCH TARGET around it instead. */
  @media (pointer:coarse){
    .port::after{content:"";position:absolute;left:50%;top:50%;width:34px;height:34px;
                 transform:translate(-50%,-50%);border-radius:50%}
    .cbtn,.tbtn,.minibtn{min-height:32px}
    .seg button{min-height:32px}
    .iedit .del,.pkgrow .del,.subtog{min-width:30px;min-height:30px;display:inline-flex;
                                     align-items:center;justify-content:center}
    /* :hover sticks after a tap on touch and leaves controls looking permanently focused */
    .railbtn:hover,.cbtn:hover,.tbtn:hover{border-color:var(--rule)}
  }
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
</head>
<body class="mode-edit">

<div class="topbar">
  <div class="brand">RosTooling <span class="sub">/ros-studio</span></div>
  <button class="tbtn drawerbtn" id="railToggle" title="Add, filters, issues and legend">&#9776; Tools</button>
  <div class="sysname">system <input id="sysname" value="">
    <button type="button" class="statuschip ok" id="statusChip" popovertarget="statusPop" aria-haspopup="dialog" title="/ros-studio status">
      <span id="chipGlyph">&#9432;</span><span id="chipCount"></span>
    </button>
  </div>
  <div popover="auto" id="statusPop"></div>
  <div popover="auto" id="nodeIssuePop" role="dialog" aria-label="Node issues"></div>
  <span id="statusLive" class="srOnly" aria-live="polite"></span>
  <div class="seg" id="modeSeg">
    <button data-mode="view">View</button><button data-mode="edit" class="on">Edit</button>
  </div>
  <div class="seg" id="levelSeg">
    <button data-lvl="1">System</button><button data-lvl="2">Interfaces</button><button data-lvl="3" class="on">Full</button><button data-lvl="4">Deps</button>
  </div>
  <div class="seg editonly" id="histSeg">
    <button id="undoBtn" title="Undo (Ctrl+Z)" disabled>&#8630; Undo</button><button id="redoBtn" title="Redo (Ctrl+Shift+Z / Ctrl+Y)" disabled>&#8631; Redo</button>
  </div>
  <div class="spacer"></div>
  <span class="savestate" id="saveState"></span>
  <!-- In the topbar, not the rail: the rail collapses into a "Tools" drawer on a narrow screen
       and its sections are individually collapsible, so the one entry point a first-time reader
       has to be able to find is the one place that is always visible. -->
  <button class="tbtn" id="tourBtn" title="A guided walkthrough that builds a small, real TurtleBot 3 system in this editor">&#9873; Tutorial</button>
  <button class="tbtn" id="reset">Reset layout</button>
  <button class="tbtn" id="theme">&#9680; Theme</button>
  <button class="tbtn" id="openBtn" title="Open a project.json, or a .rossystem with its .ros2/.ros files -- REPLACES the current project. To add systems to what's already on the canvas, use Import instead.">&#8679; Open</button>
  <input type="file" id="openInput" multiple accept=".rossystem,.ros2,.ros,.json" style="display:none">
  <button class="tbtn" id="importBtn" title="Add a project.json, or one or more .rossystem files (with their .ros2/.ros companions), to what's already on the canvas. Same as dragging them onto it.">&#8615; Import</button>
  <input type="file" id="importInput" multiple accept=".rossystem,.ros2,.ros,.json" style="display:none">
  <button class="tbtn" id="clearBtn" title="Empty the canvas and start a new, blank system">Clear</button>
  <button class="tbtn drawerbtn" id="inspToggle" title="Inspector for the current selection">&#9998; Inspect</button>
  <button class="tbtn primary" id="commit">&#8681; Commit</button>
</div>

<div class="main">
  <aside class="rail">
    <div class="insec editonly" data-sec="rail/add">
      <h4><button type="button" class="sechead" aria-expanded="true" aria-controls="secb_rail-add"><span class="caret">&#9662;</span><span class="sectitle">Add</span></button></h4>
      <div class="secbody" id="secb_rail-add">
        <button class="railbtn" id="addNode"><span class="plus">+</span> Node (hand-authored)</button>
        <button class="railbtn" id="addCat"><span class="plus">+</span> From catalogue&hellip;</button>
        <button class="railbtn" id="fromSrc"><span class="plus">&#8681;</span> From ROS 2 source&hellip;</button>
      </div>
    </div>
    <div class="insec issues" data-sec="rail/issues">
      <h4><button type="button" class="sechead" aria-expanded="true" aria-controls="secb_rail-issues"><span class="caret">&#9662;</span><span class="sectitle">Issues</span>
        <span class="secmeta"><span class="secdot e" id="issDot" hidden></span><span id="errCnt">0</span>&nbsp;err &middot; <span id="wrnCnt">0</span>&nbsp;wrn</span></button></h4>
      <div class="secbody" id="secb_rail-issues">
        <div class="issuelist" id="issueList"></div>
      </div>
    </div>
    <!-- Hidden entirely for a single-source project (see syncSystemFilter): one system needs no
         legend, and an always-present section listing one entry would just be noise. -->
    <div class="insec filter" data-sec="rail/systems" id="sysFilterSec" hidden>
      <h4><button type="button" class="sechead" aria-expanded="true" aria-controls="secb_rail-systems"><span class="caret">&#9662;</span><span class="sectitle">Source systems</span></button></h4>
      <div class="secbody" id="secb_rail-systems">
        <div id="sysFilterBox"></div>
        <div class="sysfoot">Colour marks which source <code>.rossystem</code> each node came from. At the <b>System</b> level each becomes one box.</div>
      </div>
    </div>
    <div class="insec filter" data-sec="rail/kinds">
      <h4><button type="button" class="sechead" aria-expanded="true" aria-controls="secb_rail-kinds"><span class="caret">&#9662;</span><span class="sectitle">Show kinds</span></button></h4>
      <div class="secbody" id="secb_rail-kinds"><div id="filterBox"></div></div>
    </div>
    <div class="insec" data-sec="rail/legend" style="margin-top:auto">
      <h4><button type="button" class="sechead" aria-expanded="true" aria-controls="secb_rail-legend"><span class="caret">&#9662;</span><span class="sectitle">Legend</span></button></h4>
      <div class="secbody" id="secb_rail-legend">
        <div id="legend" style="display:flex;flex-direction:column;gap:.2rem;font-size:.72rem;color:var(--ink-2)"></div>
      </div>
    </div>
  </aside>

  <!-- Separators, not decoration: role=separator with aria-valuenow is what makes a resizable
       pane legible to a screen reader, and tabindex+arrow keys are the only way to move one
       without a pointer. Both vanish under body.narrow, where the panels are overlay drawers
       and there is nothing beside them to trade width with. -->
  <div class="resizer" id="railResizer" role="separator" aria-orientation="vertical"
       aria-label="Resize the tools panel" tabindex="0"></div>

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
      <button class="cbtn" id="autoLayout" title="Arrange in layers that follow the connection direction">Auto layout</button>
      <label class="cbtn tgl" id="autoSidesWrap" title="Put each connected port on the edge facing its partner (left, right or bottom) instead of the fixed kind side, so wires stop crossing the card">
        <input type="checkbox" id="autoSides"> auto sides</label>
      <button class="cbtn" id="zFit" title="Fit to content (F)">Fit</button>
      <button class="cbtn" id="zOut" title="Zoom out (&minus;). Ctrl/&#8984;+wheel zooms at the pointer; plain wheel pans.">&minus;</button>
      <span class="zlvl" id="zLvl">100%</span>
      <button class="cbtn" id="zIn" title="Zoom in (+)">+</button>
      <button class="cbtn" id="zOne" title="Actual size (0)">100%</button>
    </div>
  </div>

  <div class="resizer" id="inspResizer" role="separator" aria-orientation="vertical"
       aria-label="Resize the inspector panel" tabindex="0"></div>

  <aside class="inspector empty" id="inspector">Select a node to edit it, or add one from the rail.</aside>
  <!-- Both only exist under body.narrow; either one closes whichever drawer is open. -->
  <div class="scrim drawer" id="drawerScrim"></div>
  <button class="tbtn" id="drawerClose" title="Close this panel" aria-label="Close panel">&#10005;</button>
</div>

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
      <div class="gennote"><b>Save all</b> downloads the real generated files &mdash; the <code>.rossystem</code>, every <code>.ros2</code>, every companion <code>.ros</code>, and the <code>project.json</code> &mdash; straight from this page. The previews below are not approximations: <code>tests/studio_parity.js</code> holds them to the Python emitter byte for byte. What it cannot do is <b>validate</b>: run <b>generate</b> in the companion for <code>rosmodel_lint</code> and the real language server, and to stage a project-local <code>subSystems:</code> target.</div>
      <div class="modalbtns">
        <button class="tbtn primary" id="saveAll">&#8681; Save all files</button>
        <button class="tbtn" id="dlJson">&#8681; project.json only</button>
        <button class="tbtn" id="selJson">Select copy text</button>
      </div>
      <div class="gennote" id="saveAllNote" style="display:none"></div>
      <div class="tabs" id="genTabs"></div>
      <pre class="gen" id="genOut"></pre>
      <textarea class="copybox" id="copyBox" spellcheck="false" readonly></textarea>
    </div>
  </div>
</div>

<!-- Seeding from a real ROS 2 repository. This page is a file:// document with no network and
     no way to spawn a process: it CANNOT run the extractors, and pretending otherwise (a button
     that appears to import a repo and silently does nothing) would be worse than not offering
     it. So it does the part it genuinely can -- assemble the exact, correctly ordered,
     correctly flagged commands from the paths the user knows -- and says plainly who has to run
     them. Every flag below is taken from the two extractors' own argparse and from
     skills/ros-model/SKILL.md; none is invented. -->
<div class="scrim" id="srcScrim">
  <div class="modal">
    <h3>Seed a project from ROS 2 source <button class="close" data-close>&#10005;</button></h3>
    <div class="body">
      <div class="gennote">This page runs offline from <code>file://</code>, so it cannot execute the extractors itself. Fill in the paths and it writes the exact commands &mdash; run them in a terminal, or paste them to Claude Code and ask it to run them. The last one produces the <code>project.json</code> you then <b>Open</b> here.</div>
      <div class="srcform">
        <label>Source tree <span class="req">required</span>
          <input id="srcRepo" spellcheck="false" placeholder="path/to/ros2_ws/src">
          <span class="hint">A ROS 2 package, or a directory of them. The extractor walks it for <code>package.xml</code>.</span></label>
        <label>Launch file <span class="req">required</span>
          <input id="srcLaunch" spellcheck="false" placeholder="path/to/pkg/launch/bringup.launch.py">
          <span class="hint">Nothing can discover this for you, and there is usually more than one. Several are accepted (space-separated); the <b>first</b> decides <code>fromFile:</code> and the default system name.</span></label>
        <label>Output directory
          <input id="srcOut" spellcheck="false" placeholder="ros_model" value="ros_model">
          <span class="hint">Everything below is written here: <code>rosnodes/*.ros2</code>, <code>msgs/*.ros</code>, and the <code>.rossystem</code> beside them.</span></label>
        <label>System name
          <input id="srcName" spellcheck="false" placeholder="(defaults to the launch file's stem)">
          <span class="hint">Names the <code>.rossystem</code> and the system inside it.</span></label>
        <label>Controller config
          <input id="srcCtrl" spellcheck="false" placeholder="(optional) path/to/controllers.yaml">
          <span class="hint">Only for <code>ros2_control</code> systems. Auto-discovered from the launch arguments when it can be; pass it when the extractor says it could not.</span></label>
      </div>
      <div class="modalbtns">
        <button class="tbtn primary" id="srcCopy">Copy commands</button>
        <span class="srcstate" id="srcState"></span>
      </div>
      <pre class="gen" id="srcOutBox"></pre>
      <div class="gennote" id="srcAfter"></div>
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

<!-- No [data-close]: clearing is destructive enough that a stray backdrop click shouldn't do it. -->
<div class="scrim" id="clearScrim" data-locked="1">
  <div class="modal">
    <h3>Clear the canvas?</h3>
    <div class="body">
      <div class="gennote">This empties the system back to zero nodes and zero connections. Ctrl+Z undoes it right after, same as any other edit -- but it is not a separate "trash" you can dig back through once you keep working.</div>
      <label class="askline"><input type="checkbox" id="clearDontAsk"> Don&rsquo;t ask again</label>
      <div class="modalbtns">
        <button class="tbtn primary" id="doClear">Clear</button>
        <button class="tbtn" id="cancelClear">Cancel</button>
      </div>
    </div>
  </div>
</div>

<div class="ctxmenu" id="ctxMenu" hidden>
  <button type="button" id="ctxWrap">Wrap in subsystem&hellip;</button>
</div>

<!-- Generic yes/no. Replaces the one native window.confirm() this page used to raise (Open,
     over unsaved work): a native dialog blocks the whole JS thread, looks nothing like the
     rest of the app, and was the only one left once Clear and Wrap got custom modals. -->
<div class="scrim" id="confirmScrim" data-locked="1">
  <div class="modal">
    <h3 id="confirmTitle"></h3>
    <div class="body">
      <div class="gennote" id="confirmBody"></div>
      <div class="modalbtns">
        <button class="tbtn primary" id="confirmOk">OK</button>
        <button class="tbtn" id="confirmCancel">Cancel</button>
      </div>
    </div>
  </div>
</div>

<!-- No [data-close]: same reasoning as Clear -- this creates a NEW file on Commit, not a
     backdrop-dismissable no-op. -->
<div class="scrim" id="wrapScrim" data-locked="1">
  <div class="modal">
    <h3>Wrap in subsystem</h3>
    <div class="body">
      <div class="gennote">The selected nodes become a separate system, reached from here through subSystems: &mdash; same as one you imported. Commit will hand back a second .rossystem for it, alongside this one. Their own connections to each other move with them; anything wired to the rest of this system stays wired.</div>
      <input type="text" id="wrapName" placeholder="subsystem name (e.g. nav_stack)" autocomplete="off">
      <div class="roinfo" id="wrapErr" hidden></div>
      <div class="modalbtns">
        <button class="tbtn primary" id="doWrap">Wrap</button>
        <button class="tbtn" id="cancelWrap">Cancel</button>
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
  // Recently-picked message types, most-recent-first, surfaced by the typeahead's empty-query
  // state (see makeTypeahead's opts.getMru). Recorded where a type actually ENTERS the model
  // -- an interface row's [data-itype] blur handler and inlineEdit's commit callback, both
  // below -- not inside the typeahead's own pick(): that fires for a suggestion the user
  // clicked or arrowed to and then changed their mind about (browsing, not choosing), and it
  // never fires at all for someone who types a full type and tabs away, which would make the
  // fastest users invisible to it.
  var RECENT_TYPES_KEY="rosStudio.recentTypes";
  function loadRecentTypes(){
    try{
      var arr=JSON.parse(localStorage.getItem(RECENT_TYPES_KEY)||"[]");
      // drop anything that no longer resolves: a different project's catalogue, a stale entry.
      return arr.filter(function(t){return TYPESET[t];});
    }catch(e){ return []; }
  }
  function recordRecentType(v){
    v=String(v||"").trim();
    if(!v||!TYPESET[v]) return;   // only record types that actually resolve
    var arr=loadRecentTypes().filter(function(t){return t!==v;});
    arr.unshift(v);
    try{ localStorage.setItem(RECENT_TYPES_KEY,JSON.stringify(arr.slice(0,8))); }catch(e){}
  }
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
  project.subSystems=project.subSystems||[];
  project.params=project.params||[];
  var DIAG=(project.diagnostics&&project.diagnostics.byNode)||{};
  var uid=1000; function nid(){return "x"+(++uid);}
  var importSeq=0;                        // one prefix per imported fragment -- see importFiles

  var HOME=project.nodes.map(function(n){return {id:n.id,x:n.x,y:n.y};});

  var canvas=document.getElementById("canvas"), svg=document.getElementById("wires"),
      canvasWrap=document.getElementById("canvasWrap"),
      inspector=document.getElementById("inspector");
  STUDIO.makeArrowMarkers(svg,"");
  var selNode=null, selEdge=null, addKind="pub", mode="edit", level=3;
  // Ctrl/Cmd+click adds a node to this set instead of replacing selNode, so several nodes can
  // be dragged as one group; {} (nothing beyond selNode) and a single leftover entry both
  // collapse back to plain single-selection -- see wireCanvas's pointerdown/up.
  var multiSel=Object.create(null);
  // which interfaces have their QoS panel open. Kept OUTSIDE `project` on purpose: it is view
  // state, and putting it in the model would make opening a panel an undoable edit.
  var qosOpen={}, cmtOpen={};
  // Collapsible-section open/closed state: a UI preference like theme or autoSides, not model
  // content, so it lives in localStorage keyed by rosStudio.secOpen and NEVER in project.json or
  // the undo stack -- collapsing a section must not become an undoable "edit". Keyed by a fixed
  // context+slug (e.g. "node/interfaces"), not by node id or rendered title, so "I collapsed
  // interfaces" applies to every node rather than being re-asked per selection.
  var secOpen=(function(){ try{ return JSON.parse(localStorage.getItem("rosStudio.secOpen")||"{}"); }catch(e){ return {}; } })();
  var SEC_DEFAULT_CLOSED={"rail/legend":1,"rail/kinds":1,"sys/types":1};
  function secClosed(key){
    return Object.prototype.hasOwnProperty.call(secOpen,key) ? secOpen[key]===false : !!SEC_DEFAULT_CLOSED[key];
  }
  function saveSecOpen(){ try{ localStorage.setItem("rosStudio.secOpen",JSON.stringify(secOpen)); }catch(e){} }
  function secDomId(key){ return "secb_"+key.replace(/\//g,"-"); }
  // Shared by the inspector (rebuilt on every selection -- `closed` is read fresh each call, so
  // the class is simply baked into the string) and the rail (static markup -- applySecState
  // below stamps the class on once at startup instead).
  function sec(key,titleHtml,bodyHtml,metaHtml){
    var closed=secClosed(key);
    return '<div class="insec'+(closed?' collapsed':'')+'" data-sec="'+key+'">'
      +'<h4><button type="button" class="sechead" aria-expanded="'+(closed?'false':'true')+'" aria-controls="'+secDomId(key)+'">'
      +'<span class="caret">&#9662;</span><span class="sectitle">'+titleHtml+'</span>'
      +(metaHtml?('<span class="secmeta">'+metaHtml+'</span>'):'')
      +'</button></h4><div class="secbody" id="'+secDomId(key)+'">'+bodyHtml+'</div></div>';
  }
  function toggleSecBox(box){
    var key=box.getAttribute("data-sec"); if(!key) return;
    var closing=!box.classList.contains("collapsed");
    box.classList.toggle("collapsed",closing);
    var btn=box.querySelector(".sechead");
    if(btn) btn.setAttribute("aria-expanded",closing?"false":"true");
    secOpen[key]=!closing; saveSecOpen();
  }
  function expandSec(key){
    // used by issue routing: a target hidden inside a collapsed section has to open first,
    // and the point was to go there, so the expansion is persisted rather than temporary.
    if(!secClosed(key)) return;
    secOpen[key]=true; saveSecOpen();
    var box=document.querySelector('.insec[data-sec="'+key+'"]');
    if(box){ box.classList.remove("collapsed"); var btn=box.querySelector(".sechead"); if(btn) btn.setAttribute("aria-expanded","true"); }
  }
  function wireSecClicks(root){
    if(!root) return;
    root.addEventListener("click",function(e){
      var btn=e.target.closest(".sechead"); if(!btn||!root.contains(btn)) return;
      var box=btn.closest(".insec"); if(box) toggleSecBox(box);
    });
  }
  function applySecState(root){
    if(!root) return;
    [].slice.call(root.querySelectorAll(".insec[data-sec]")).forEach(function(box){
      var closed=secClosed(box.getAttribute("data-sec"));
      box.classList.toggle("collapsed",closed);
      var btn=box.querySelector(".sechead"); if(btn) btn.setAttribute("aria-expanded",closed?"false":"true");
    });
  }
  // Which half of the inspector is showing: the current selection, or the project (system-level)
  // panel. Reaching Project used to require deselecting -- there was no other way in -- which is
  // why fillSystemInspector's fromFile hint had to end with "(deselect to reach it)". A tab
  // switch is presentation, not a model edit: it never touches selNode/selEdge, never
  // pushUndo()s, and (unlike a collapse) is NOT persisted -- it always starts on Selected/Project
  // to match whatever got clicked, and a fresh selection always wins Selected back.
  var inspTab="proj", lastSelForTab=null;
  function tabStrip(){
    var has=!!(selNode||selEdge);
    return '<div class="seg insptabs">'
      +'<button type="button" data-insptab="sel"'+(inspTab==="sel"?' class="on"':'')+(has?"":" disabled")+'>Selected</button>'
      +'<button type="button" data-insptab="proj"'+(inspTab==="proj"?' class="on"':'')+'>Project</button></div>';
  }
  // Comment panels are wired by a per-render registry key rather than by a model id, because the
  // same panel shape serves nodes, interfaces, parameters, connections, the system and a
  // package -- and only the first two of those have an id at all.
  var cmtReg={};
  // Persisted the same way autoSides (a couple hundred lines away) already is -- a view
  // preference, never model data -- except THIS one hides content rather than just changing
  // how it's drawn, which is the classic "where did my data go" trap if it's silently
  // restored with no visible sign anything is filtered. railToggle's "(filtered)" marker,
  // wired further down where the checkboxes are built, is the mitigation.
  var HIDDEN_KINDS_KEY="rosStudio.hiddenKinds";
  var hiddenKinds=(function(){ try{ return JSON.parse(localStorage.getItem(HIDDEN_KINDS_KEY)||"[]"); }catch(e){ return []; } })();
  function hiddenKindList(){
    var out=[];
    KINDS.forEach(function(k){ if(!kindShown[k]) out.push(k); });
    if(!paramShown) out.push("param");
    return out;
  }
  function saveHiddenKinds(){
    try{ localStorage.setItem(HIDDEN_KINDS_KEY,JSON.stringify(hiddenKindList())); }catch(e){}
    updateFilterIndicator();
  }
  // The other direction, for a project.json that carries a saved filter: set the state, put the
  // checkboxes back in step with it (they are built once, with `checked` baked in, so nothing
  // else would re-tick them), and persist it as the running preference.
  function setHiddenKinds(list){
    var hid={}; (list||[]).forEach(function(k){ hid[k]=1; });
    KINDS.forEach(function(k){ kindShown[k]=!hid[k]; });
    paramShown=!hid["param"];
    var fb=document.getElementById("filterBox");
    if(fb) [].slice.call(fb.querySelectorAll("input[data-k]")).forEach(function(cb){
      cb.checked=(cb.dataset.k==="param")?paramShown:!!kindShown[cb.dataset.k];
    });
    saveHiddenKinds();
  }
  var kindShown={}; KINDS.forEach(function(k){kindShown[k]=hiddenKinds.indexOf(k)<0;});
  // `param` is a pseudo-kind: it has its own filter toggle but no port and no edge, because a
  // parameter is not an interaction.
  var paramShown=hiddenKinds.indexOf("param")<0;
  function updateFilterIndicator(){
    var rt=document.getElementById("railToggle"); if(!rt) return;
    var anyHidden=!paramShown||KINDS.some(function(k){return !kindShown[k];});
    rt.classList.toggle("hasfilter",anyHidden);
  }
  // The ParameterTypes the emitter can write a value for. List/Struct/Base64/Array exist in the
  // grammar (Basics.xtext:51-52) but _fmt_param_value has no representation for them, so
  // offering them here would let the author author a value the emitter cannot spell.
  var PTYPES=["String","Boolean","Integer","Double"];

  document.getElementById("sysname").value=(project.system&&project.system.name)||"system";
  // The status chip's one-time notice: sourced from the companion's own DATA.banner (a
  // generation/validation error) here at load, or replaced by a file-load report in
  // applyLoadedProject. Independent of the live lint severity that also feeds the chip --
  // buildStatus() takes the max of the two.
  // The title and severity come from the companion now instead of being hard-coded to
  // "Generation failed". They are not all failures: a real-server validation that could not RUN
  // leaves the files written and the lint clean, and labelling that "Generation failed" is
  // simply untrue -- a page that overstates one thing gets believed less about the next.
  var opNotice=DATA.banner?{sev:(DATA.bannerSev==="warn"?"warn":"err"),
                            title:DATA.bannerTitle||"Generation failed",
                            html:'<pre>'+esc(DATA.banner)+'</pre>'}:null;

  // ---- datalists (offline autocomplete) ----
  // Message types are NOT a <datalist> here -- see makeTypeahead()/wireTypeahead() below. At
  // 600+ vendored entries, the native control had no search and rendered the whole list.
  (function(){
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
  // Same rule the wire-drop inference below uses (search "Infer, don't just permit"), just
  // triggered by an EDIT to an already-typed interface instead of a fresh connection: retyping
  // one end of a wire almost always means the message on the wire changed too, so any partner
  // this interface is already connected to gets the same type -- but only if that partner is
  // still BLANK (a real, different type on the other end is a mismatch to flag, not overwrite)
  // and only if it is hand-authored (a catalogue or subSystems: interface's type is fixed by
  // the file it comes from; this editor has no way to change what that file says).
  // Returns the labels it filled, so the caller can SAY it happened -- silently rewriting a
  // field on a node the author is not looking at is correct but indistinguishable from a bug.
  //
  // Only ever call this on a COMMITTED value (blur, or a typeahead pick), never per keystroke.
  // Per keystroke it fills the partner from the first character typed, and every later keystroke
  // then sees a non-blank partner and declines -- leaving the neighbour permanently set to "s"
  // and reporting a type mismatch on a node the author never touched.
  function propagateInterfaceType(node,iface){
    var v=String(iface.type||"").trim(), filled=[];
    if(!v) return filled;
    project.connections.forEach(function(c){
      var other=null;
      if(c.from.n===node.id&&c.from.i===iface.id) other={n:c.to.n,i:c.to.i};
      else if(c.to.n===node.id&&c.to.i===iface.id) other={n:c.from.n,i:c.from.i};
      if(!other) return;
      var oNode=nodeById(other.n), oIface=oNode&&ifaceById(oNode,other.i);
      if(!oNode||!oIface||oNode.backing!=="hand") return;
      if(String(oIface.type||"").trim()) return;
      oIface.type=v;
      filled.push(oNode.label+"."+oIface.name);
    });
    // This writes to a node the author is not editing, from a blur handler that does NOT go
    // through pushUndo -- and pushUndo is the only thing that marks the project dirty and
    // schedules the autosave. Without this the fill lived in memory only: the debounced save
    // had already fired for the keystrokes, nothing scheduled another, and beforeunload (which
    // stays quiet while autosave is healthy) let the tab close on top of it.
    if(filled.length) markDirty();
    return filled;
  }
  function announceTypeFill(filled,typ){
    if(!filled||!filled.length) return;
    toast(filled.length===1 ? ("Set "+filled[0]+" to "+typ)
                            : (filled.length+" connected interfaces set to "+typ));
  }

  // ============================ history (undo / redo) ============================
  // ALL editor state is in `project`, so a snapshot is its JSON and undo is a stack of them.
  // Snapshots rather than inverse commands on purpose: Delete removes a node AND every
  // connection touching it, and an inverse would be a second, subtly different implementation
  // of that rule -- the kind that reinstates the node and loses the edges.
  var UNDO_CAP=50, COALESCE_MS=700;
  var undoStack=[], redoStack=[], lastTag=null, lastTagAt=0;
  var dirty=false;

  // syncViewState() first, so every serialised copy -- undo entry, autosave, downloaded
  // project.json -- carries the arrangement that was on screen when it was taken. Without it the
  // view keys would only ever be as fresh as the last time something happened to write them.
  function snapshot(){ syncViewState(); return JSON.stringify(project); }
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
    // Any edit invalidates the server's prior verdict wholesale, not just for the node touched:
    // DIAG is what the last Commit said about the file as it stood THEN, and the file has now
    // changed. Without this, fixing exactly what a diagnostic complained about left its warning
    // icon on screen forever -- there was no code path that ever cleared DIAG at all.
    if(Object.keys(DIAG).length) DIAG={};
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
  // `full` distinguishes the two callers. Undo/redo (full falsy) restores only the LAYOUT half of
  // the view -- the subsystem and package box positions Auto layout clears -- so Ctrl+Z genuinely
  // puts the arrangement back, while the level/mode/filter you happen to be looking through does
  // not lurch backwards every time you undo an unrelated edit. The autosave prompt (full true) is
  // a different project arriving, so it restores the whole visualization.
  function applyState(json,full){
    project=JSON.parse(json);
    project.nodes=project.nodes||[]; project.connections=project.connections||[];
    project.packages=project.packages||{}; project.system=project.system||{};
    // Re-derive, not just clear: this path also serves "restore autosave" (a genuinely
    // different project's data). Both minters assign node ids sequentially and deterministically
    // ("x1001", "n1", ...), so loading a different project here without resyncing DIAG risks
    // its old entries surviving under an id that now names an unrelated node -- a stale server
    // diagnostic reappearing, permanently, on the wrong card.
    DIAG=(project.diagnostics&&project.diagnostics.byNode)||{};
    syncUid();
    if(full) restoreViewState(); else restoreViewLayout();
    document.getElementById("sysname").value=(project.system&&project.system.name)||"system";
    if(selNode&&!nodeById(selNode)) selNode=null;   // it may have been deleted in this state
    Object.keys(multiSel).forEach(function(id){ if(!nodeById(id)) delete multiSel[id]; });
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
  // A SAVE_KEY entry only ever gets removed when the user clicks Discard on the restore
  // prompt (search doDiscard) -- every system name ever opened otherwise stays in this
  // bucket forever. On a file:// origin the bucket is shared across every local HTML page
  // on the machine, so it fills faster than one project's own history would suggest; when
  // it does, saveNow's quota catch permanently disables autosave for the rest of THIS
  // session (storage=null) while leaving the stale entries that caused it untouched. Keep
  // only the most recent few, run once at startup; never prunes the CURRENT session's own
  // key regardless of age, since that one has not necessarily saved yet.
  (function pruneOldAutosaves(){
    if(!storage) return;
    try{
      var entries=[];
      for(var i=0;i<localStorage.length;i++){
        var k=localStorage.key(i);
        if(k&&k.indexOf("ros-studio/v1/")===0&&k!==SAVE_KEY){
          var at=0;
          try{ at=(JSON.parse(localStorage.getItem(k))||{}).at||0; }catch(e){}
          entries.push({k:k,at:at});
        }
      }
      entries.sort(function(a,b){ return b.at-a.at; });
      entries.slice(7).forEach(function(e){ try{ localStorage.removeItem(e.k); }catch(e2){} });
    }catch(e){}
  })();

  function scheduleSave(){
    if(!storage) return;
    if(saveTimer) clearTimeout(saveTimer);
    saveTimer=setTimeout(saveNow,800);          // debounced: a drag or a typed word is one write
  }
  function saveNow(){
    saveTimer=null;
    if(!storage) return;
    try{
      syncViewState();
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
  // ============================ subsystem abstraction ============================
  // A `subSystems:` entry names one whole reused composition. The studio used to flatten its
  // nodes onto this file's canvas, marked only by a badge -- so a system reusing the catalogued
  // turtlebot gained three cards indistinguishable from its own, and one reusing
  // turtlebot3_navigation2 would gain fourteen. ros_plot went the other way and resolved every
  // connection into a subsystem to a dashed "(dangling endpoint)" ghost. Neither showed the
  // thing a reader wants: how the reused pieces connect, without their internals.
  //
  // Three states, all pure PRESENTATION -- project.view is excluded from _seed_facts /
  // _project_facts, and emit_rossystem skips `backing:"sub"` nodes regardless, so the state
  // cannot reach an emitted byte. tests/studio_parity.js pins that by emitting under each.
  //
  //   collapsed (default)  one box; its ports are the labels the referenced file exposes
  //   framed               the internals, inside a labelled frame
  //   drill-in             that file alone, read-only, with a breadcrumb back
  var drillRef=null, subPos={}, selSub=null, pkgPos={}, sysPos={};
  function subState(ref){
    var v=(project.view&&project.view.subsystems)||{};
    return v[ref]==="framed"?"framed":"collapsed";
  }
  function setSubState(ref,st){
    project.view=project.view||{};
    project.view.subsystems=project.view.subsystems||{};
    project.view.subsystems[ref]=st;
  }
  // ---- the whole visualization, not just the subsystem states ------------------------------
  // Everything a reader arranged used to be split three ways: node x/y in project.json, the
  // subsystem states in project.view, and EVERYTHING ELSE -- the subsystem box positions, the
  // Deps package-box positions, the abstraction level, the edit/view mode, the kind filter, auto
  // sides, the camera -- in plain JS variables that died with the tab. So "I built this exact
  // picture" survived a reload only by accident, and Auto layout (which clears subPos/pkgPos)
  // threw the rest away with no way back.
  //
  // The fix is not to move these into the MODEL -- they are views, and the invariant is that no
  // view can change an emitted byte. They go under project["view"], which both fact trees
  // exclude by construction: _project_facts()/projectFacts() build from an allow-list of model
  // keys, so a key added here can never enter the diff or the emitter. tests/studio_parity.js's
  // compareViewStates() asserts that rather than trusting it, by emitting under populated view
  // states and byte-comparing.
  //
  // `subsystems` is deliberately NOT written by syncViewState(): subState() reads it live out of
  // project.view, so it is already current, and re-writing it here would fight that reader.
  function syncViewState(){
    project.view=project.view||{};
    var v=project.view;
    v.subPos=subPos; v.pkgPos=pkgPos; v.sysPos=sysPos;
    v.level=level; v.mode=mode; v.autoSides=autoSides;
    // systemShown is written through setOriginShown() directly (like view.subsystems), so it is
    // already live on project.view -- nothing to copy here, and copying would fight that writer.
    v.hiddenKinds=hiddenKindList();
    // The camera is the one piece that is arguably NOT part of "the picture I built" -- it is
    // where you were standing, not what you arranged. It is saved anyway (a reader who zoomed
    // into one corner of a 40-node system and saved wants that corner back) but restored only
    // by an explicit load, and a project.json carrying none still gets the fit-on-open pass.
    v.camera={k:view.k,tx:view.tx,ty:view.ty};
  }
  // A view changed, so the autosave is now stale even though the MODEL did not change.
  //
  // markDirty() is deliberately not called: a view is not an edit, so it must not arm the
  // unsaved-work guard or push an undo entry. But scheduleSave() was reached ONLY through
  // markDirty(), which meant project.view in the autosave was only ever as fresh as the last
  // content edit -- arrange three containers, switch to View, hide a system, close the tab, and
  // the restore prompt offered the arrangement from before any of it. The whole visualization
  // round-tripped through an explicit Commit and not through the mechanism the page actually
  // relies on to keep a session safe.
  function noteViewChange(){ scheduleSave(); }
  // Layout-ish view state only: the positions Auto layout destroys. Undo/redo restores THESE, so
  // "Auto layout ate my arrangement" is a Ctrl+Z away, while the level/mode/filter you happened
  // to be on does not lurch backwards every time you undo an unrelated edit. That line -- layout
  // is undoable, preferences are not -- is the same one secOpen already draws.
  function restoreViewLayout(){
    var v=project.view||{};
    subPos=v.subPos||{}; pkgPos=v.pkgPos||{}; sysPos=v.sysPos||{};
  }
  // The full restore, for the paths where a genuinely different project arrives: Open, drop, and
  // the autosave prompt. A project.json saved before this existed carries none of these keys, so
  // every one falls back to what the page already had.
  function restoreViewState(){
    var v=project.view||{};
    restoreViewLayout();
    if(typeof v.level==="number"&&v.level>=1&&v.level<=4){ level=v.level; setLevelButtons(); }
    if(v.mode==="edit"||v.mode==="view") setMode(v.mode);
    if(typeof v.autoSides==="boolean") setAutoSides(v.autoSides);
    if(Array.isArray(v.hiddenKinds)) setHiddenKinds(v.hiddenKinds);
    if(v.camera&&typeof v.camera.k==="number"){
      view.k=clampZ(v.camera.k); view.tx=v.camera.tx||0; view.ty=v.camera.ty||0; applyView();
    }
    return !!(v.camera&&typeof v.camera.k==="number");
  }
  function subEntry(ref){
    var l=project.subSystems||[];
    for(var i=0;i<l.length;i++) if(l[i].ref===ref) return l[i];
    return null;
  }
  function subMembers(ref){
    return project.nodes.filter(function(n){return n.backing==="sub"&&n.subRef===ref;});
  }
  // Every ref that actually has member nodes on this canvas. A reference that resolved to
  // nothing has no box to draw and no internals to frame -- it stays a row in the inspector.
  function liveSubRefs(){
    var seen={}, out=[];
    project.nodes.forEach(function(n){
      if(n.backing!=="sub"||!n.subRef) return;
      if(!seen[n.subRef]){seen[n.subRef]=1;out.push(n.subRef);}
    });
    return out;
  }
  function isCollapsedMember(n){
    return n.backing==="sub"&&!!n.subRef&&subState(n.subRef)==="collapsed";
  }
  // Every exposure label already spoken for in the OUTER file, which is the namespace a
  // connections: endpoint resolves in. Both label-pinning paths (wrapping a selection, and
  // exposing an interface afterwards) have to avoid all of it, not just their own subsystem:
  //   - an outer node's own label, taken VERBATIM by _exposure_labels pass 1, which does not
  //     disambiguate against a subsystem's -- a collision there is an emitted endpoint naming
  //     two interfaces (RM051/RM065), not a renamed one;
  //   - every other wrapped subsystem's pinned labels, claimed file-wide by pass 0;
  //   - and unexposed-but-labelled interfaces too, since exposing one later reuses its label.
  // `skipNodeIds` drops the nodes being wrapped right now, so their own current labels do not
  // block them from keeping those names.
  function projectLabelsInUse(skipNodeIds){
    var used=Object.create(null);
    project.nodes.forEach(function(n){
      if(skipNodeIds&&skipNodeIds[n.id]) return;
      (n.ifaces||[]).forEach(function(f){
        var l=String(f.label||"").trim(); if(l) used[l]=1;
        // an unlabelled outer interface derives its label from the NAME, so that is taken too
        if(!l&&f.name&&n.backing!=="sub") used[String(f.name).trim()]=1;
      });
    });
    (project.subSystems||[]).forEach(function(s){
      if(!s.content) return;
      (s.content.nodes||[]).forEach(function(cn){
        if(skipNodeIds&&skipNodeIds[cn.id]) return;
        (cn.ifaces||[]).forEach(function(cf){
          var l=String(cf.label||"").trim(); if(l) used[l]=1;
        });
      });
    });
    return used;
  }
  // Extracts a group of this project's OWN hand-authored nodes into a brand new subsystem --
  // the reverse of importing one. Unlike every other subSystems: entry in this file, there is
  // no external .rossystem behind this one yet: `content` below is a self-contained,
  // project-shaped snapshot of exactly what was pulled out, and it is what generate_files()
  // (ros_studio.py) reads to write a SECOND .rossystem alongside this one on Commit -- see
  // _normalize_subproject there. Until that Commit happens, the wrapped nodes exist only here.
  function wrapNodesInSubsystem(ids,refName){
    var idSet=Object.create(null); ids.forEach(function(id){idSet[id]=1;});
    var wrapped=ids.map(nodeById).filter(Boolean);
    if(wrapped.length<2) return {error:"select at least two nodes to wrap"};
    // A catalogue node CAN be wrapped: the extracted .rossystem writes it as a `from:` reference
    // exactly like this file does, and _emit_system_into only generates .ros2 files for
    // hand-authored packages, so nothing tries to rewrite the vendored one. A driver stack
    // assembled from catalogue nodes is the single most useful thing to wrap, and refusing it
    // was the wrong call. A `sub` node is genuinely out: it is already a stand-in for another
    // file's node, and this file has nothing to extract for it.
    var already=wrapped.filter(function(n){return n.backing==="sub";});
    if(already.length) return {error:"'"+already[0].label+"' already comes from the subsystem '"
      +(already[0].subRef||"?")+"' — its definition lives in that file, so there is nothing here "
      +"to move into a new one."};
    refName=String(refName||"").trim();
    if(!refName) return {error:"name the subsystem"};
    if((project.subSystems||[]).some(function(s){return s.ref===refName;}))
      return {error:"'"+refName+"' is already a subSystems: reference in this project"};
    // Every system this project writes is emitted as "<its name>.rossystem" into one output
    // directory, so two systems sharing a name means one file, and the loser is simply gone --
    // name a wrapped subsystem after its own parent and the entire outer system disappears from
    // the output with a clean lint and exit 0.
    if(refName===String((project.system&&project.system.name)||"").trim())
      return {error:"'"+refName+"' is this system's own name — both would be written to "
        +refName+".rossystem and one would overwrite the other."};

    // internal: both endpoints are being wrapped, so the connection moves with them and stops
    // being this file's business. external: it crosses the new boundary and stays exactly as
    // it is -- ids do not change, so nothing about it needs to be rewritten.
    var internal=[], external=[];
    project.connections.forEach(function(c){
      var aIn=!!idSet[c.from.n], bIn=!!idSet[c.to.n];
      (aIn&&bIn?internal:external).push(c);
    });

    var pkgs={}, types={};
    wrapped.forEach(function(n){
      if(n.pkg&&project.packages[n.pkg]) pkgs[n.pkg]=project.packages[n.pkg];
      (n.ifaces||[]).forEach(function(f){ if(f.type&&project.types[f.type]) types[f.type]=project.types[f.type]; });
    });

    // ---- pin the exposure labels BEFORE anything is split -------------------------------
    // The two files each derive their own labels (ros_studio._exposure_labels), from their own
    // node sets, and a connections: endpoint is a LABEL STRING, not an id. So a cross-boundary
    // connection only survives if both files spell its endpoint the same way -- which they will
    // not, left to derive it: the outer file sees one node set, the extracted file another, and
    // pass 2's disambiguation differs between them. Pinning an explicit label into BOTH copies
    // makes pass 1 take it verbatim on both sides, so the endpoint matches by construction.
    //
    // Unique across the WHOLE OUTER FILE, not just this subsystem: in the outer file every one
    // of these belongs to a `backing:"sub"` node, and those labels are claimed FILE-WIDE by
    // _exposure_labels' pass 0 (an endpoint naming one has to resolve to exactly one interface).
    // Scoping the uniqueness to the wrapped set alone produced two silent failures: two separate
    // wraps both exposing "scan" emitted two different wires spelled identically (RM065), and a
    // pinned label colliding with an outer node's AUTHOR-WRITTEN label -- which pass 1 takes
    // verbatim and does not disambiguate -- emitted two endpoints with one name (RM051).
    var pinned=projectLabelsInUse(idSet);
    function pinLabel(n,f){
      var base=String(f.label||f.name||"").trim()||"iface";
      if(!pinned[base]){ pinned[base]=1; return base; }
      var cand=base+"_"+f.kind;
      if(!pinned[cand]){ pinned[cand]=1; return cand; }
      cand=base+"_"+f.kind+"_"+sanitiseHint(n.label);
      var k=2;
      while(pinned[cand]){ cand=base+"_"+f.kind+"_"+sanitiseHint(n.label)+"_"+k; k++; }
      pinned[cand]=1; return cand;
    }
    // What the extracted file must DECLARE. An interface counts if the author already marked it
    // exposed, or if any connection touches it -- including one that is about to become
    // external. That last case is the one that silently broke: the connection moves to the outer
    // file, so the extracted file's own `connections:` no longer mentions the interface, and
    // _exposure_labels there would not consider it exposed at all -- the subsystem would declare
    // nothing for the outer file's endpoint to resolve against (RM050 at generate time).
    var mustExpose=Object.create(null);   // node id + " " + iface id -> pinned label
    wrapped.forEach(function(n){
      (n.ifaces||[]).forEach(function(f){
        if(!(f.exposed||ifaceConnected(n,f))) return;
        mustExpose[n.id+" "+f.id]=pinLabel(n,f);
      });
    });

    // presentation-only, same shape seedFromFiles builds for an externally-resolved reference
    // (see its subSystems.forEach) -- built from what is already in hand rather than a
    // re-parsed file, since there is no file yet.
    function shownLabel(n,f){ return mustExpose[n.id+" "+f.id]||f.label||f.name; }
    var graph={
      nodes:wrapped.map(function(n){
        return {label:n.label, from:n.pkg+"."+n.node,
                interfaces:(n.ifaces||[]).map(function(f){
                  return {label:shownLabel(n,f), kind:f.kind, name:f.name, artifact:null};
                })};
      }),
      connections:internal.map(function(c){
        var an=nodeById(c.from.n), af=ifaceById(an,c.from.i);
        var bn=nodeById(c.to.n), bf=ifaceById(bn,c.to.i);
        return [af?shownLabel(an,af):"", bf?shownLabel(bn,bf):""];
      })
    };
    // cloned BEFORE the wrapped nodes are stripped down below -- content needs their full,
    // original (hand-authored) shape, not the read-only shadow the outer project keeps instead.
    var content={
      system:{name:refName,fromFile:null},
      nodes:JSON.parse(JSON.stringify(wrapped)),
      connections:JSON.parse(JSON.stringify(internal)),
      packages:JSON.parse(JSON.stringify(pkgs)),
      types:JSON.parse(JSON.stringify(types)),
      params:[]
    };
    // the extracted file's side of the pin: explicit label + explicit `exposed`, so what it
    // declares does not depend on which connections happened to stay behind.
    content.nodes.forEach(function(cn){
      (cn.ifaces||[]).forEach(function(cf){
        var lbl=mustExpose[cn.id+" "+cf.id];
        if(!lbl) return;
        cf.label=lbl; cf.exposed=true;
      });
    });

    pushUndo("wrap:"+refName);
    var cx=0,cy=0;
    wrapped.forEach(function(n){
      cx+=n.x||0; cy+=n.y||0;
      // mirrors exactly what _subsystem_project_nodes (ros_studio.py) builds for a member of an
      // externally-resolved reference: a read-only shadow, no params -- everything real now
      // lives in `content` above. `exposed` stays FALSE here even for a pinned interface: this
      // file does not declare them (emit_rossystem skips a sub node's whole block), and marking
      // one exposed would only claim its name file-wide and push a local interface's derived
      // label sideways for nothing. The pinned LABEL does matter, though -- it is the string a
      // cross-boundary endpoint resolves through (pass 0).
      n.backing="sub"; n.subRef=refName;
      n.ifaces=(n.ifaces||[]).map(function(f){
        return {id:f.id,name:f.name,kind:f.kind,type:null,qos:null,
                label:mustExpose[n.id+" "+f.id]||f.label||null,exposed:false};
      });
      n.params=[];
    });
    project.connections=external;
    project.subSystems.push({ref:refName,file:null,invented:true,content:content,graph:graph});
    subPos[refName]={x:Math.max(0,Math.round(cx/wrapped.length)),y:Math.max(0,Math.round(cy/wrapped.length))};
    return {ok:true,ref:refName};
  }

  // ---- what a wrapped subsystem exposes, after the fact ----------------------------------
  // Only ever an INVENTED entry: a reference seeded from a file exposes what that file says it
  // does, and this project has no business rewriting it. See subExposeEditor for the UI.
  function subContentIface(entry,nodeId,ifaceId){
    var cn=null, cf=null;
    (entry.content.nodes||[]).forEach(function(x){ if(x.id===nodeId) cn=x; });
    if(cn) (cn.ifaces||[]).forEach(function(y){ if(y.id===ifaceId) cf=y; });
    return {node:cn,iface:cf};
  }
  // A connection on EITHER side of the boundary forces exposure: the outer file's endpoint has
  // to resolve to something the subsystem declares, and the subsystem's own internal connection
  // makes _exposure_labels declare it regardless of the flag. Unticking either would be a
  // checkbox that says one thing while the emitted file says another.
  function subIfaceWired(entry,nodeId,ifaceId){
    function touches(c){ return (c.from.n===nodeId&&c.from.i===ifaceId)||(c.to.n===nodeId&&c.to.i===ifaceId); }
    return project.connections.some(touches)||((entry.content.connections||[]).some(touches));
  }
  // Unique across the whole OUTER FILE, for the same reason wrapNodesInSubsystem pins in the
  // first place: in the outer file these are `sub` labels, claimed file-wide, and an endpoint
  // naming a duplicated one resolves to two interfaces. projectLabelsInUse covers the other
  // subsystems and the outer nodes' own labels; this one interface is excluded so re-ticking a
  // box it already owns keeps the same name rather than walking it to name_kind_2 each time.
  function pinSubLabel(entry,cn,cf){
    var used=projectLabelsInUse(null);
    var mine=String(cf.label||"").trim();
    if(mine) delete used[mine];
    var base=String(cf.label||cf.name||"").trim()||"iface";
    if(!used[base]) return base;
    var cand=base+"_"+cf.kind;
    if(!used[cand]) return cand;
    var stem=base+"_"+cf.kind+"_"+sanitiseHint(cn.label), k=2;
    cand=stem;
    while(used[cand]){ cand=stem+"_"+k; k++; }
    return cand;
  }
  function mirrorSubLabel(ref,nodeId,ifaceId,label){
    var sn=nodeById(nodeId), sf=sn&&ifaceById(sn,ifaceId);
    if(sn&&sn.backing==="sub"&&sn.subRef===ref&&sf) sf.label=label;
  }
  // the drill-in view reads graph labels, so keep them saying what the file will say
  function refreshSubGraphLabels(entry){
    if(!entry.graph) return;
    (entry.graph.nodes||[]).forEach(function(gn){
      var cn=null;
      (entry.content.nodes||[]).forEach(function(x){ if(x.label===gn.label) cn=x; });
      if(!cn) return;
      // name AND kind: one node routinely has a `pub image` and a `sub image`, and matching on
      // the name alone overwrote both graph rows with whichever interface came last.
      (gn.interfaces||[]).forEach(function(gf){
        (cn.ifaces||[]).forEach(function(cf){
          if(cf.name===gf.name&&cf.kind===gf.kind) gf.label=cf.label||cf.name;
        });
      });
    });
  }
  function exposeSubIface(entry,ref,cn,cf){
    cf.exposed=true;
    cf.label=pinSubLabel(entry,cn,cf);
    mirrorSubLabel(ref,cn.id,cf.id,cf.label);
  }
  // A connection endpoint that lands on a WRAPPED subsystem's interface has to be something
  // that subsystem's own emitted file declares, or the endpoint resolves to nothing. Returns
  // what it exposed (for the toast), or null when there was nothing to do -- an already-exposed
  // interface, an ordinary node, or a subsystem referencing a file this project does not own.
  function ensureSubEndpointExposed(nodeId,ifaceId){
    var n=nodeById(nodeId);
    if(!n||n.backing!=="sub"||!n.subRef) return null;
    var entry=subEntry(n.subRef);
    if(!entry||!entry.invented||!entry.content) return null;
    var hit=subContentIface(entry,nodeId,ifaceId);
    if(!hit.iface||hit.iface.exposed) return null;
    exposeSubIface(entry,n.subRef,hit.node,hit.iface);
    refreshSubGraphLabels(entry);
    return (hit.node.label||"?")+"."+(hit.iface.name||"?");
  }
  // Both of these take the undo snapshot THEMSELVES, and only once they know something will
  // actually change. Snapshotting in the click handler instead meant a refused toggle (a wired
  // interface cannot be withdrawn) still pushed an entry and marked the project dirty, so
  // clicking a locked checkbox a few times buried the real last edit under no-op undo steps.
  function setSubExposure(ref,nodeId,ifaceId,on){
    var entry=subEntry(ref); if(!entry||!entry.content) return;
    var hit=subContentIface(entry,nodeId,ifaceId);
    if(!hit.iface) return;
    if(!!hit.iface.exposed===!!on) return;              // nothing to do
    if(!on&&subIfaceWired(entry,nodeId,ifaceId)){
      toast('"'+(hit.iface.label||hit.iface.name)+'" is wired — it has to stay exposed');
      return;                       // the re-render puts the checkbox back
    }
    pushUndo();
    if(on) exposeSubIface(entry,ref,hit.node,hit.iface);
    else cf_unexpose(hit.iface);
    refreshSubGraphLabels(entry);
  }
  function cf_unexpose(cf){ cf.exposed=false; }   // label kept: re-ticking should reuse the name
  function setSubExposureAll(ref,on){
    var entry=subEntry(ref); if(!entry||!entry.content) return;
    var todo=[];
    (entry.content.nodes||[]).forEach(function(cn){
      (cn.ifaces||[]).forEach(function(cf){
        if(!!cf.exposed===!!on) return;
        if(!on&&subIfaceWired(entry,cn.id,cf.id)) return;   // wired ones cannot be withdrawn
        todo.push({node:cn,iface:cf});
      });
    });
    if(!todo.length) return;
    pushUndo();
    todo.forEach(function(t){ if(on) exposeSubIface(entry,ref,t.node,t.iface); else cf_unexpose(t.iface); });
    refreshSubGraphLabels(entry);
  }
  // The collapsed box's rows: one per distinct exposed LABEL, because a connections: endpoint
  // is a bare label resolved file-wide -- the label IS the subsystem's port, and that is the
  // DSL's own view of it. A label two member nodes both declare (the catalogued turtlebot's
  // "tf") collapses to ONE row and is badged: the ambiguity is real (RM065) and this is the
  // first view in which it is visible rather than buried.
  // ============================ origin systems ============================
  // A merged or imported project holds nodes from SEVERAL source .rossystem files, and once
  // merged they were indistinguishable: one undifferentiated pile of cards, with the renames in
  // init's diagnostics the only surviving hint of where anything came from. `n.srcSystem` (set
  // by seed_from_many's pass A and by the in-page importer) is that provenance, and everything
  // below is what the canvas does with it -- tint, legend, filter, and a container per system at
  // the System level.
  //
  // Deliberately inert for a single-source project: originList() returns one entry, multiOrigin()
  // is false, and every consumer short-circuits. A blank project, or one seeded from one file,
  // looks exactly as it did before -- no colours, no legend section, no containers.
  //
  // A node carries an origin AND may separately be part of a `subSystems:` reference. Those are
  // two different groupings and nesting them is not attempted: a `backing:"sub"` node returns a
  // null origin and stays inside the subsystem machinery that already owns it. That is why
  // wrapping a selection needs no special handling -- wrap mutates the node in place, so its
  // srcSystem survives untouched and simply stops being consulted while it is a sub member.
  function originOf(n){
    if(!n||n.backing==="sub") return null;
    return n.srcSystem||(project.system&&project.system.name)||"(this project)";
  }
  // First-appearance order, not sorted: the colour a system gets should not shuffle because a
  // later import happens to sort before it, and node order is stable across a save/load.
  // Memoised per render pass. originList() walks every node, and originHidden()/isBoxedByOrigin()/
  // originIdx()/multiOrigin() all call it -- render() once per node, renderNode() twice more, and
  // drawEdges() twice per CONNECTION, which made the whole paint O(N^2 + E*N) on exactly the
  // merged projects this feature exists for. The cache is dropped by render() (and by anything
  // that changes the node set), so it can never outlive the picture it describes.
  var _originCache=null;
  function invalidateOrigins(){ _originCache=null; }
  function originList(){
    if(_originCache) return _originCache;
    var seen={}, out=[];
    project.nodes.forEach(function(n){
      var o=originOf(n);
      if(o&&!seen[o]){ seen[o]=1; out.push(o); }
    });
    _originCache=out;
    return out;
  }
  function multiOrigin(){ return originList().length>1; }
  var ORIGIN_SLOTS=8;
  function originIdx(sys){
    var i=originList().indexOf(sys);
    // More systems than slots wraps rather than running out of colours. The legend still names
    // every system, so a repeated hue is ambiguous only until you read the label.
    return i<0?0:(i%ORIGIN_SLOTS);
  }
  function originShown(sys){
    var v=(project.view&&project.view.systemShown)||{};
    return v[sys]!==false;
  }
  function setOriginShown(sys,on){
    project.view=project.view||{};
    project.view.systemShown=project.view.systemShown||{};
    project.view.systemShown[sys]=!!on;
  }
  // Hidden by the legend filter. Checked everywhere a node is drawn or an edge is resolved, the
  // same way kindShown gates a port -- a filter that hid the card but kept its wires would draw
  // edges to nothing.
  function originHidden(n){
    if(!multiOrigin()) return false;
    var o=originOf(n);
    return !!o&&!originShown(o);
  }
  function originMembers(sys){
    return project.nodes.filter(function(n){ return originOf(n)===sys; });
  }
  // True when this node is standing in for its origin's container rather than being drawn.
  // Mirrors isCollapsedMember() exactly, for the other grouping axis.
  function isBoxedByOrigin(n){
    return level===1&&multiOrigin()&&!!originOf(n)&&originShown(originOf(n));
  }
  // The rail's "Source systems" legend: one labelled swatch per origin, with a checkbox that
  // shows or hides that system's nodes. Rebuilt from render() rather than wired once, because
  // Import can add a system at any time and a legend that missed it would be worse than none.
  //
  // The whole section is hidden unless there is more than one source. Colour-coding one system
  // says nothing, and a section listing a single entry is noise -- this is the "inert for a
  // single-source project" rule, enforced in the one place the user can see it.
  //
  // Colour is never the only channel: every row is labelled with its system name and its node
  // count, so the legend reads correctly with no colour vision at all.
  function syncSystemFilter(){
    var sec=document.getElementById("sysFilterSec"), box=document.getElementById("sysFilterBox");
    if(!sec||!box) return;
    var list=originList();
    sec.hidden=list.length<2;
    // Clear the cache key with the rows. Leaving it set meant a project that dropped to one
    // system and came back to the SAME two (undo, or re-opening the same file) rebuilt an
    // identical signature, matched the early return below, and un-hid a section whose rows had
    // been emptied -- a legend with no entries, permanently, since this is its only writer.
    if(sec.hidden){ box.innerHTML=""; box.dataset.sig=""; return; }
    var sig=list.map(function(s){ return s+":"+(originShown(s)?1:0)+":"+originMembers(s).length; }).join("|");
    if(box.dataset.sig===sig) return;      // nothing changed; leave the DOM (and focus) alone
    box.dataset.sig=sig;
    box.innerHTML="";
    list.forEach(function(sys){
      var l=document.createElement("label");
      l.title=sys+" — "+originMembers(sys).length+" node(s)";
      l.innerHTML='<input type="checkbox" '+(originShown(sys)?"checked ":"")+'>'
        +'<span class="sw" style="background:var(--s'+originIdx(sys)+')"></span>'
        +'<span class="sysnm">'+esc(sys)+'</span>'
        +'<span class="syscnt">'+originMembers(sys).length+'</span>';
      l.querySelector("input").onchange=function(e){
        // A view, not an edit: no pushUndo, exactly like the kind filter.
        setOriginShown(sys,e.target.checked);
        if(selNode&&originHidden(nodeById(selNode))){ selNode=null; fillInspector(); }
        noteViewChange(); render();
      };
      box.appendChild(l);
    });
  }
  // Generalised out of subPorts(): "one row per exposure label across this set of nodes, with
  // every (node, interface) pair behind it". Both groupings need exactly this -- a collapsed
  // subsystem box and a System-level origin container are the same idea on different axes.
  function groupPorts(members){
    var rows=[], byLabel={};
    members.forEach(function(n){
      (n.ifaces||[]).forEach(function(f){
        var lbl=String(f.label||f.name||"");
        if(!lbl) return;
        var r=byLabel[lbl];
        if(!r){ r=byLabel[lbl]={label:lbl,kind:f.kind,pairs:[],wired:false}; rows.push(r); }
        r.pairs.push({n:n,f:f});
        if(ifaceConnected(n,f)) r.wired=true;
      });
    });
    rows.sort(function(a,b){
      var d=KINDS.indexOf(a.kind)-KINDS.indexOf(b.kind);
      return d||(a.label<b.label?-1:(a.label>b.label?1:0));
    });
    return rows;
  }
  // One line, on purpose. This used to BE the loop now living in groupPorts(); leaving a second
  // copy here is the shape STATUS.md keeps recording -- two implementations of one rule that
  // agree until someone fixes only one of them.
  function subPorts(ref){ return groupPorts(subMembers(ref)); }
  function renderSubBox(ref){
    var entry=subEntry(ref)||{}, members=subMembers(ref), rows=subPorts(ref);
    var el=document.createElement("div");
    el.className="node subbox"+(selSub===ref?" sel":"");
    var pos=subPos[ref]||{x:60,y:60};
    el.style.left=pos.x+"px"; el.style.top=pos.y+"px";
    el.dataset.sub=ref;
    var wired=0;
    rows.forEach(function(r){ if(r.wired) wired++; });
    var where=entry.file?("assets/rosmodelscatalog/"+entry.file)
                        :(entry.localFile||(entry.invented?"(new -- written on Commit)":"(not resolved)"));
    el.innerHTML='<div class="nhead" data-drag>'
      +'<span class="subtog" data-expand="'+esc(ref)+'" title="show the internals inside a frame">&#9656;</span>'
      +'<span class="ntitle">'+esc(ref)+'</span>'
      +'<span class="badge" title="'+(entry.invented
        ?"wrapped out of this project &mdash; Commit writes it as its own .rossystem"
        :"reached through subSystems: &mdash; declared in that file, not this one")+'">subsystem</span>'
      +'<span class="subtog" data-drill="'+esc(ref)+'" title="open this system on its own canvas">&#8599;</span></div>'
      +'<div class="nfrom">'+esc(where)
      +'<br>'+members.length+' node(s) &middot; '+(rows.length
        ?(wired+' of '+rows.length+' interface(s) wired')
        // "0 of 0 wired" reads as "not wired up yet" when it actually means "there is nothing
        // here to wire, ever" -- the single most common defect in the real corpus.
        :'<span class="subempty">no interfaces — nothing can connect to this</span>')+'</div>'
      +'<div class="ifaces"></div>';
    var box=el.querySelector(".ifaces");
    rows.forEach(function(r){
      if(!kindShown[r.kind]) return;
      var src=SRC_SIDE[r.kind];
      var row=document.createElement("div");
      row.className="iface"+(r.wired?"":" unwired");
      row.dataset.kind=r.kind;
      // One VISIBLE port plus one invisible port per additional (node, interface) pair behind
      // it. portCenter() resolves an edge by querying [data-n][data-i], so every pair needs an
      // element with non-zero size or its edge silently disappears -- and stacking them is
      // honest: at this level of abstraction they really are one port.
      var ports="";
      r.pairs.forEach(function(pr,i){
        ports+='<span class="port '+(src?"src":"snk")+' '+r.kind+'"'
          +(i?' style="opacity:0;pointer-events:none"':'')
          +' data-n="'+pr.n.id+'" data-i="'+pr.f.id+'" data-kind="'+r.kind+'"'
          +' data-src="'+src+'" data-type="'+esc(pr.f.type||"")+'"></span>';
      });
      var amb=(r.pairs.length>1)
        ? ('<span class="amb" title="'+r.pairs.length+' nodes in this subsystem declare the label &quot;'
           +esc(r.label)+'&quot;. A connections: endpoint resolves by name only, so naming it is '
           +'genuinely ambiguous (RM065) &mdash; the referenced file owns that ambiguity, not this one.">'
           +'&#9888;'+r.pairs.length+'</span>')
        : "";
      row.innerHTML='<span class="kd '+r.kind+'">'+r.kind+'</span>'
        +'<span class="inm">'+esc(r.label)+'</span>'+amb
        +'<span class="ity">'+esc(r.pairs[0].f.type||"—")+'</span>'+ports;
      box.appendChild(row);
    });
    canvas.appendChild(el);
  }
  // The System level's unit is a SYSTEM. Level 1 already hid every interface row, so a merged
  // project at that level was a heap of bare name cards with no indication that they came from
  // three different files -- the one level whose name promised exactly that grouping was the
  // level that showed it least.
  //
  // This is renderSubBox() on the other axis, and deliberately the same mechanic rather than a
  // parallel one: one box per origin system, its ports being the exposure labels its members
  // declare (groupPorts, shared with the subsystem boxes), wired ones solid and unwired dimmed.
  // The invisible-stacked-port trick is carried over for the same reason it exists there --
  // drawEdges() resolves an endpoint by querying [data-n][data-i], so every (node, interface)
  // pair behind a collapsed row still needs an element, or its edge silently disappears.
  // First placement for the containers. A box has no x/y of its own -- it stands for N nodes --
  // so without this they all stack in the default corner, which is the defect the Deps view's
  // package boxes were just fixed for (f014526). Laid out in a ROW rather than at each group's
  // centroid: centroids of overlapping groups overlap too, and two boxes on top of each other is
  // strictly worse than a row that needs one drag. Ordered BY centroid, so the row still roughly
  // matches where the reader last saw those nodes. Only ever fills in what is missing, so a
  // dragged or saved position is never overwritten.
  function placeOriginBoxes(){
    var list=originList();
    var need=list.filter(function(s){ return !sysPos[s]; });
    if(!need.length) return;
    var cen={};
    list.forEach(function(s){
      var m=originMembers(s), sx=0;
      m.forEach(function(n){ sx+=(n.x||0); });
      cen[s]=m.length?sx/m.length:0;
    });
    need.sort(function(a,b){ return cen[a]-cen[b]; });
    // Start to the right of anything already placed, so a system added by a later Import lands
    // beside the existing row instead of on top of it.
    // y=100, not 60: the floating find control sits over canvas coordinates y 46..80 at the
    // default zoom, and a box placed at 60 opens with its title bar underneath it -- measured,
    // not guessed. x=60 is clear of it because the row starts left of the control's own inset.
    var startX=60, ROW_Y=100, STEP=300;
    list.forEach(function(s){ if(sysPos[s]) startX=Math.max(startX,sysPos[s].x+STEP); });
    need.forEach(function(s,i){ sysPos[s]={x:startX+i*STEP,y:ROW_Y}; });
  }
  function renderOriginBox(sys){
    var members=originMembers(sys), rows=groupPorts(members);
    var el=document.createElement("div");
    el.className="node sysbox s"+originIdx(sys);
    var pos=sysPos[sys]||{x:60,y:60};
    el.style.left=pos.x+"px"; el.style.top=pos.y+"px";
    el.dataset.sys=sys;
    var wired=0;
    rows.forEach(function(r){ if(r.wired) wired++; });
    el.innerHTML='<div class="nhead" data-drag>'
      +'<span class="sw" style="background:var(--s'+originIdx(sys)+')"></span>'
      +'<span class="ntitle">'+esc(sys)+'</span>'
      +'<span class="badge" title="every node this project merged or imported from '
      +esc(sys)+'. Switch to Interfaces or Full to open it back up into its nodes.">system</span></div>'
      +'<div class="nfrom">'+members.length+' node(s) &middot; '+(rows.length
        ?(wired+' of '+rows.length+' interface(s) wired')
        :'<span class="subempty">no interfaces — nothing can connect to this</span>')+'</div>'
      +'<div class="ifaces"></div>';
    var box=el.querySelector(".ifaces");
    rows.forEach(function(r){
      if(!kindShown[r.kind]) return;
      var src=SRC_SIDE[r.kind];
      var row=document.createElement("div");
      row.className="iface"+(r.wired?"":" unwired");
      row.dataset.kind=r.kind;
      var ports="";
      r.pairs.forEach(function(pr,i){
        ports+='<span class="port '+(src?"src":"snk")+' '+r.kind+'"'
          +(i?' style="opacity:0;pointer-events:none"':'')
          +' data-n="'+pr.n.id+'" data-i="'+pr.f.id+'" data-kind="'+r.kind+'"'
          +' data-src="'+src+'" data-type="'+esc(pr.f.type||"")+'"></span>';
      });
      // Unlike a subsystem's ⚠2, a repeated label here is not someone else's ambiguity to
      // report: these are THIS project's nodes, and init/import already renamed a genuine
      // collision (RM065). Several pairs on one row means several nodes legitimately expose the
      // same-named interface, so the count is shown plainly rather than as a warning.
      var many=(r.pairs.length>1)
        ? ('<span class="amb" title="'+r.pairs.length+' nodes in '+esc(sys)+' expose &quot;'
           +esc(r.label)+'&quot;">&times;'+r.pairs.length+'</span>')
        : "";
      row.innerHTML='<span class="kd '+r.kind+'">'+r.kind+'</span>'
        +'<span class="inm">'+esc(r.label)+'</span>'+many
        +'<span class="ity">'+esc(r.pairs[0].f.type||"—")+'</span>'+ports;
      box.appendChild(row);
    });
    canvas.appendChild(el);
  }

  // The bounding box of a framed subsystem's member cards, measured off what was rendered
  // rather than estimated -- the same rule nodeBox() follows and for the same reason.
  function memberRect(ref){
    var PAD=22, TOP=26, x0=1e9,y0=1e9,x1=-1e9,y1=-1e9, found=false;
    subMembers(ref).forEach(function(n){
      var el=canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(n.id)+'"]');
      if(!el) return;
      found=true;
      x0=Math.min(x0,el.offsetLeft); y0=Math.min(y0,el.offsetTop);
      x1=Math.max(x1,el.offsetLeft+el.offsetWidth);
      y1=Math.max(y1,el.offsetTop+el.offsetHeight);
    });
    if(!found) return null;
    return {x:x0-PAD, y:y0-TOP, w:(x1-x0)+2*PAD, h:(y1-y0)+TOP+PAD};
  }
  function renderSubFrame(ref,rect){
    var el=document.createElement("div");
    el.className="subframe"; el.dataset.frame=ref;
    el.style.left=rect.x+"px"; el.style.top=rect.y+"px";
    el.style.width=rect.w+"px"; el.style.height=rect.h+"px";
    el.innerHTML='<div class="sfhead">'
      +'<span class="subtog" data-collapse="'+esc(ref)+'" title="collapse to one box">&#9662;</span>'
      +esc(ref)
      +'<span class="subtog" data-drill="'+esc(ref)+'" title="open this system on its own canvas">&#8599;</span>'
      +'</div>';
    canvas.appendChild(el);
  }

  function render(){
    if(drillRef){ renderDrill(); return; }
    var db=document.getElementById("drillbar");
    if(db) db.remove();
    // BEFORE the node loop, not after: renderNode() reads nodeIssueIndex (built here) to paint
    // the per-node warning icon, so the index has to be current before any card exists. Nodes
    // are removed and rebuilt from scratch on every render() (next line), which is exactly what
    // keeps that icon from ever going stale -- there is no incremental patch to get wrong, only
    // a fresh paint against whatever runIssues() just computed.
    invalidateOrigins();   // the node set may have changed since the last paint
    runIssues();
    syncSystemFilter();    // Import can add a source system between renders
    canvas.className="canvas "+(level===4?"deps":"lvl"+level);
    [].slice.call(canvas.querySelectorAll(".node,.pkgbox,.subframe")).forEach(function(e){e.remove();});
    for(var i=0;i<project.nodes.length;i++){
      var nd=project.nodes[i];
      if(isCollapsedMember(nd)) continue;    // the subsystem box below stands for it
      if(originHidden(nd)) continue;         // hidden by the legend's per-system filter
      if(isBoxedByOrigin(nd)) continue;      // the origin container below stands for it
      renderNode(nd);
    }
    liveSubRefs().forEach(function(ref){
      if(subState(ref)==="collapsed") renderSubBox(ref);
    });
    // One container per source system, at the System level only. multiOrigin() keeps this inert
    // for a single-source or blank project, which is most of them.
    if(level===1&&multiOrigin()){
      placeOriginBoxes();
      originList().forEach(function(sys){ if(originShown(sys)) renderOriginBox(sys); });
    }
    // frames are measured off the RENDERED member cards, so they are drawn after them
    liveSubRefs().forEach(function(ref){
      if(subState(ref)!=="framed") return;
      var r=memberRect(ref);
      if(r) renderSubFrame(ref,r);
    });
    wireSubToggles();
    if(level===4) renderDeps();
    sizeCanvas();          // before drawEdges: the SVG follows the canvas box at 100%/100%
    drawEdges();
    applyFind();           // render() replaced every element, so the highlight has to go back
    refreshNodeIssuePopIfOpen();   // nodes exist again now -- safe to look the icon back up
  }
  function wireSubToggles(){
    canvas.querySelectorAll("[data-expand]").forEach(function(x){
      x.onclick=function(ev){ ev.stopPropagation();
        setSubState(x.dataset.expand,"framed"); relayoutSubs(); noteViewChange(); render(); fillInspector(); };
    });
    canvas.querySelectorAll("[data-collapse]").forEach(function(x){
      x.onclick=function(ev){ ev.stopPropagation();
        setSubState(x.dataset.collapse,"collapsed"); relayoutSubs(); noteViewChange(); render(); fillInspector(); };
    });
    canvas.querySelectorAll("[data-drill]").forEach(function(x){
      x.onclick=function(ev){ ev.stopPropagation(); openDrill(x.dataset.drill); };
    });
  }
  function openDrill(ref){
    var e=subEntry(ref);
    if(!e||!e.graph){
      // Not a failure to hide: the reference resolved (its nodes are on the canvas) but the
      // referenced FILE was not readable at seed time, so there is nothing to open.
      alertBar("No graph was captured for “"+ref+"”, so it cannot be opened. Re-seed with "
               +"the companion, or open its .rossystem alongside this one.");
      return;
    }
    // The drilled-in view wipes every outer .node from the canvas (renderDrill draws the
    // referenced file's OWN graph instead), so any open per-node popover is now anchored over
    // a card that no longer exists. render()'s early return for drillRef also means neither
    // runIssues() nor refreshNodeIssuePopIfOpen() run while drilled in, so nothing else would
    // catch this.
    var nip=document.getElementById("nodeIssuePop");
    if(nip&&nip.hidePopover&&nip.matches&&nip.matches(":popover-open")) nip.hidePopover();
    nodePopNodeId=null;
    drillRef=ref; selNode=null; selEdge=null; multiSel=Object.create(null); render(); fillInspector();
  }
  function closeDrill(){ drillRef=null; render(); fillInspector(); }
  // Drill-in: the referenced system ALONE, read-only. Nothing here is part of this project --
  // these cards are built from subSystems[i].graph, which is presentation data excluded from
  // the fact tree, and none of them can be edited, moved into this file or wired.
  function renderDrill(){
    var entry=subEntry(drillRef)||{}, g=entry.graph||{nodes:[],connections:[]};
    canvas.className="canvas lvl"+(level===4?3:level);
    [].slice.call(canvas.querySelectorAll(".node,.pkgbox,.subframe")).forEach(function(e){e.remove();});
    [].slice.call(svg.querySelectorAll("path.edge,path.depedge")).forEach(function(e){e.remove();});

    var ids=g.nodes.map(function(n){return n.label;});
    var edges=[];
    // A connections: endpoint is a bare LABEL resolved file-wide, so an edge is placed by
    // looking up which node declares that label. Two nodes declaring one label is the same
    // RM065 ambiguity the collapsed box badges; the first in file order wins, deterministically.
    var owner={};
    g.nodes.forEach(function(n){
      (n.interfaces||[]).forEach(function(f){
        if(owner[f.label]===undefined) owner[f.label]=n.label;
      });
    });
    (g.connections||[]).forEach(function(c){
      var a=owner[c[0]], b=owner[c[1]];
      if(a&&b&&a!==b) edges.push([a,b]);
    });
    var DW=210;
    function boxOf(id){
      var n=null;
      for(var i=0;i<g.nodes.length;i++) if(g.nodes[i].label===id) n=g.nodes[i];
      return {w:DW,h:56+22*((n&&n.interfaces&&n.interfaces.length)||0)};
    }
    var pos=layoutGraph(ids,edges,boxOf);

    g.nodes.forEach(function(n){
      var el=document.createElement("div");
      el.className="node ro";
      var pt=pos[n.label]||{x:60,y:60};
      el.style.left=pt.x+"px"; el.style.top=pt.y+"px";
      el.style.width=DW+"px";
      el.dataset.dn=n.label;
      var h='<div class="nhead"><span class="ntitle">'+esc(n.label)+'</span>'
        +'<span class="badge" title="declared in '+esc(drillRef)+', not in this project">read-only</span></div>'
        +'<div class="nfrom">from: "'+esc(n.from||"")+'"</div><div class="ifaces"></div>';
      el.innerHTML=h;
      var box=el.querySelector(".ifaces");
      (n.interfaces||[]).forEach(function(f){
        if(!kindShown[f.kind]) return;
        var row=document.createElement("div");
        row.className="iface"; row.dataset.kind=f.kind;
        row.innerHTML='<span class="kd '+f.kind+'">'+f.kind+'</span>'
          +'<span class="inm">'+esc(f.label)+'</span>'
          +'<span class="port '+(SRC_SIDE[f.kind]?"src":"snk")+' '+f.kind+'"'
          +' data-dn="'+esc(n.label)+'" data-df="'+esc(f.label)+'"></span>';
        box.appendChild(row);
      });
      canvas.appendChild(el);
    });
    sizeCanvas();
    // edges between the read-only cards, resolved through the same label-owner map
    (g.connections||[]).forEach(function(c){
      var a=canvas.querySelector('.port[data-df="'+STUDIO.cssEsc(c[0])+'"]');
      var b=canvas.querySelector('.port[data-df="'+STUDIO.cssEsc(c[1])+'"]');
      if(!a||!b) return;
      var cr=canvas.getBoundingClientRect(), k=view.k||1;
      var ar=a.getBoundingClientRect(), br=b.getBoundingClientRect();
      var path=document.createElementNS(NS,"path");
      path.setAttribute("class","edge topic");
      path.setAttribute("d",STUDIO.bezier((ar.left-cr.left+ar.width/2)/k,(ar.top-cr.top+ar.height/2)/k,
                                          (br.left-cr.left+br.width/2)/k,(br.top-cr.top+br.height/2)/k));
      svg.appendChild(path);
    });
    showDrillBar(g);
  }
  function showDrillBar(g){
    var old=document.getElementById("drillbar");
    if(old) old.remove();
    var bar=document.createElement("div");
    bar.className="drillbar"; bar.id="drillbar";
    var sysname=(project.system&&project.system.name)||"system";
    bar.innerHTML='<button class="minibtn" id="drillBack">&#9664; back</button>'
      +'<span class="crumb">'+esc(sysname)+' &rsaquo; </span><b>'+esc(drillRef)+'</b>'
      +'<span class="crumb">'+g.nodes.length+' node(s), '+(g.connections||[]).length
      +' internal connection(s) &mdash; read-only, declared in that file</span>';
    canvasWrap.insertBefore(bar,canvasWrap.firstChild);
    document.getElementById("drillBack").onclick=closeDrill;
  }
  // Says what just happened, then gets out of the way. Used for actions the app takes on the
  // author's behalf without being asked -- copying a message type across a wire, folding N
  // imported nodes in -- which were previously invisible: correct, but indistinguishable from
  // nothing having happened. Never used for anything that needs a decision; that is a modal.
  function toast(msg){
    var host=document.getElementById("toasts");
    if(!host){ host=document.createElement("div"); host.className="toasts"; host.id="toasts";
               document.body.appendChild(host); }
    var t=document.createElement("div"); t.className="toast"; t.textContent=msg;
    host.appendChild(t);
    requestAnimationFrame(function(){ t.classList.add("in"); });
    setTimeout(function(){
      t.classList.remove("in");
      setTimeout(function(){ if(t.parentNode) t.remove(); },200);
    },2600);
  }
  // Its own id, NOT the drill-in bar's: render() removes #drillbar unconditionally (the drill
  // bar is rebuilt per render), so an alert borrowing that id vanished on the next render --
  // which is exactly what the callers do. "Could not load: ..." was drawn and wiped in the same
  // frame, leaving a failed Open looking like nothing had happened at all.
  function alertBar(msg){
    var b=document.getElementById("alertbar");
    if(b) b.remove();
    var bar=document.createElement("div");
    bar.className="drillbar"; bar.id="alertbar";
    bar.innerHTML='<button class="minibtn" id="alertBarClose">&#10005;</button><span>'+esc(msg)+'</span>';
    canvasWrap.insertBefore(bar,canvasWrap.firstChild);
    document.getElementById("alertBarClose").onclick=function(){bar.remove();};
  }
  function renderNode(n){
    var el=document.createElement("div");
    var live=nodeIssueIndex[n.id]||[];
    var liveErrs=live.filter(function(it){return it.sev==="e";}).length, liveWarns=live.length-liveErrs;
    var hasdiag=DIAG[n.id]&&DIAG[n.id].length;
    // .hasdiag and .issue-e render identically (both border-color:var(--dead)) -- they're kept
    // as separate classes for what each MEANS in the CSS comments (the server's last verdict vs.
    // the live instant checks), not because they look different, so there's no reason to gate
    // one on the absence of the other.
    // The origin tint is a CLASS, not an inline style: it has to lose to .sel, .hasdiag and
    // .issue-e, all of which say something more urgent about this card than where it came from,
    // and CSS ordering is what arranges that. `orig` is absent entirely for a single-source
    // project, so nothing about those cards changes.
    var org=multiOrigin()?originOf(n):null;
    el.className="node"+(n.backing==="cat"?" cat":"")+(n.backing==="sub"?" sub":"")+((selNode===n.id||multiSel[n.id])?" sel":"")
      +(org?(" orig s"+originIdx(org)):"")
      +(hasdiag?" hasdiag":"")+(liveErrs?" issue-e":"");
    if(org) el.dataset.orig=org;
    el.style.left=n.x+"px"; el.style.top=n.y+"px"; el.dataset.n=n.id;
    var fromStr='"'+n.pkg+"."+n.node+'"';
    var badge=n.backing==="sub"?"subsystem":(n.backing==="cat"?"catalogue":"authored");
    var warnLabel=(liveErrs?liveErrs+" error"+(liveErrs===1?"":"s"):"")+(liveErrs&&liveWarns?", ":"")+(liveWarns?liveWarns+" warning"+(liveWarns===1?"":"s"):"");
    var h='<div class="nhead" data-drag><span class="ntitle">'+esc(n.label)+'</span>'
      +(live.length?'<button type="button" class="nwarn'+(liveErrs?" e":"")+'" '
        +'aria-haspopup="true" aria-expanded="false" aria-label="'+esc(n.label+": "+warnLabel)+'" title="'+esc(warnLabel)+' — click for details">'
        +'<span aria-hidden="true">⚠<span class="nwarnc">'+live.length+'</span></span></button>':'')
      +'<span class="badge '+(n.backing==="cat"?"cat":"")+'" title="'
      +(n.backing==="sub"?"reached through subSystems: &quot;"+esc(n.subRef||"")+"&quot; — declared in that file, not this one":"")
      +'">'+badge+'</span></div>'
      +'<div class="nfrom">from: '+esc(fromStr)
      +((n.namespace&&String(n.namespace).trim())?'<br>namespace: '+esc(n.namespace):'')
      +'</div><div class="ifaces"></div>';
    el.innerHTML=h;
    var warnBtn=el.querySelector(".nwarn");
    if(warnBtn) warnBtn.onclick=function(ev){ ev.stopPropagation(); openNodeIssuePop(n.id,warnBtn); };
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
    // The parameter band. Two facts are shown per row that nothing else on the canvas showed:
    // the exposure LABEL when it differs from the artifact parameter name (the split that made
    // these vanish on every round-trip), and the EFFECTIVE value -- the .rossystem override
    // where there is one, otherwise the artifact's declared default.
    var ps=(n.params||[]).filter(function(p){return paramShown;});
    if(ps.length){
      var pbox=document.createElement("div");
      pbox.className="params";
      var ph='<div class="phead">parameters ('+ps.length+')</div>';
      ps.forEach(function(p){
        var over=(p.sysValue!=null&&p.sysValue!=="");
        var val=over?p.sysValue:p.value;
        var t=String(p.ptype||"").trim()||inferPtype(over?p.sysValue:p.value);
        var lbl=(p.exposed&&p.label&&p.label!==p.name)?('<span class="plb" title="exposed to this system as &quot;'+esc(p.label)+'&quot;">'+esc(p.label)+'</span>'):"";
        ph+='<div class="prow'+(p.orphan?" orphan":"")+'" data-p="'+p.id+'"'
          +' title="'+esc(p.name+" : "+t+(over?("  (overridden here: "+val+")"):("  = "+(val==null?"—":val))))
          +(p.orphan?"  — the backing artifact does not declare this parameter":"")+'">'
          +'<span class="pk">'+esc(t.slice(0,3))+'</span>'
          +'<span class="pnm">'+esc(p.name)+'</span>'+lbl
          +'<span class="pvl">'+esc(val==null||val===""?"—":String(val))+(over?" *":"")+'</span></div>';
      });
      pbox.innerHTML=ph;
      el.appendChild(pbox);
    }
    if(DIAG[n.id]&&DIAG[n.id].length){
      var d=document.createElement("div"); d.className="diagflag";
      d.textContent="⚠ "+DIAG[n.id].join(" | "); el.appendChild(d);
    }
    canvas.appendChild(el);
  }

  // ---- deps (level 4): bipartite node -> package, resolved against the catalogue ----
  var pkgEls={};
  // A fixed column (the old colX=980) overlapped whatever the node graph's own auto layout had
  // already put there -- a wide or deeply-layered system runs well past x=980, so switching to
  // Deps dropped the package boxes on top of the nodes rather than beside them. render() always
  // draws the node/subsystem cards before calling renderDeps() (see render(), above), so this
  // reads their REAL rendered extent -- collapsed boxes, framed members, everything already on
  // the canvas -- rather than re-deriving it from project.nodes and getting collapsed/framed
  // subsystems wrong a second way.
  function depsColumnX(){
    var els=canvas.querySelectorAll(".node"), maxRight=0;
    [].slice.call(els).forEach(function(e){ maxRight=Math.max(maxRight,e.offsetLeft+e.offsetWidth); });
    return Math.round(Math.max(600,maxRight+110));
  }
  function renderDeps(){
    pkgEls={};
    var packages={}, order=[];
    project.nodes.forEach(function(n){
      // The per-system filter has to reach THIS view too. Hiding a system removed its node card
      // here but left its package box standing (and a dep edge pointing at it), so the Deps
      // level answered "show me only these systems" with a box for a system that was not being
      // shown. A package whose every node is hidden contributes nothing and is skipped; one that
      // still has a visible node keeps its box, with a count that matches what is on screen.
      if(originHidden(n)) return;
      var p=n.pkg||"(local)";
      if(!packages[p]){packages[p]={name:p,nodes:[],resolved:false};order.push(p);}
      packages[p].nodes.push(n);
      var key=n.pkg+"."+n.node;
      if(CATALOGUE[key]||n.backing==="cat") packages[p].resolved=true;
    });
    var colX=depsColumnX(), y=80;
    order.forEach(function(p){
      var pk=packages[p];
      // pkgPos is a VIEW (same reasoning as subPos): a box dragged here is remembered for this
      // session but never touches the model. Only a package with no remembered position yet
      // gets the freshly computed default column, so a manual drag survives further renders.
      var pos=pkgPos[p]; if(!pos){ pos={x:colX,y:y}; pkgPos[p]=pos; }
      var el=document.createElement("div");
      el.className="pkgbox "+(pk.resolved?"res":"unres");
      el.dataset.pkg=p;
      el.style.left=pos.x+"px"; el.style.top=pos.y+"px";
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
    if(!nb){
      // ...or to whichever CONTAINER is standing in for that node right now. Level 1 hides every
      // port, so the width>0 test above fails even when a collapsed box does carry this pair's
      // port, and the member card itself is deliberately not rendered -- so both lookups miss and
      // the edge was silently dropped. That is the wrong answer at the one level whose whole job
      // is showing how the groups connect: the wire should land on the group.
      var nn=nodeById(nId);
      if(nn&&nn.backing==="sub"&&nn.subRef)
        nb=canvas.querySelector('.node.subbox[data-sub="'+STUDIO.cssEsc(nn.subRef)+'"]');
      else if(nn&&originOf(nn))
        nb=canvas.querySelector('.node.sysbox[data-sys="'+STUDIO.cssEsc(originOf(nn))+'"]');
    }
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
      // Same requirement for the per-system filter: hiding a system has to take its wires with
      // it, or the canvas draws edges into empty space where the cards used to be.
      if(originHidden(nodeById(c.from.n))||originHidden(nodeById(c.to.n))) continue;
      var s=portCenter(c.from.n,c.from.i), t=portCenter(c.to.n,c.to.i);
      if(!s||!t) continue;
      // Both endpoints resolved to the SAME point. That happens whenever a connection is
      // internal to whatever is standing in for both of its nodes -- most often a connection
      // between two nodes of one source system while the System level is showing that system as
      // one container, which for a merged project is the majority of connections. Drawing it
      // gives a zero-length path that still carries an arrowhead marker, so the box collects a
      // little pile of arrowheads pointing at its own centre. An edge wholly inside a collapsed
      // unit is not visible at this level of abstraction; that is what collapsing MEANS, and the
      // honest drawing of it is no line at all.
      if(Math.abs(s.x-t.x)<0.5&&Math.abs(s.y-t.y)<0.5) continue;
      var path=document.createElementNS(NS,"path");
      path.setAttribute("class","edge "+edgeKindPair(c)+(selEdge===c.id?" sel":""));
      path.setAttribute("d",STUDIO.bezier(s.x,s.y,t.x,t.y));
      path.dataset.c=c.id; path.style.pointerEvents="stroke"; path.style.cursor="pointer";
      (function(cid){path.addEventListener("click",function(ev){ev.stopPropagation();selEdge=cid;selNode=null;multiSel=Object.create(null);render();fillInspector();});})(c.id);
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
      // MIRRORS ros_studio._subsystem_graph. Presentation only -- excluded from the fact tree,
      // so a subsystem view can never change an emitted byte. Without it the collapsed/framed/
      // drill-in views have nothing to draw inside a subsystem.
      if(target){
        rec.graph={
          nodes:target.model.nodes.map(function(sn){
            return {label:sn.label, from:sn.from,
                    interfaces:(sn.ifaces||[]).map(function(f){
                      return {label:f.label, kind:f.kind,
                              name:f.ifaceName||f.label, artifact:f.artifact};})};
          }),
          connections:(target.model.connections||[]).map(function(c){return [c.from,c.to];})
        };
      }else if(cat&&!cat.hasOwnSubsystems){
        rec.graph={
          nodes:Object.keys(cat.nodes||{}).sort().map(function(lbl){
            var info=cat.nodes[lbl]||{};
            return {label:lbl, from:info.from||null,
                    interfaces:Object.keys(info.interfaces||{}).sort().map(function(nm){
                      // the index records the LABEL and the kind; the underlying interface
                      // name is not carried, and at this level of abstraction the label is
                      // what a connections: endpoint spells anyway
                      return {label:nm, kind:info.interfaces[nm], name:nm, artifact:null};})};
          }),
          connections:(cat.connections||[]).map(function(c){return [c[0],c[1]];})
        };
      }
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

  // ============================ import: add files to the CURRENT project ==================
  // Open (above) REPLACES the project -- the one file you are working on. Dropping files onto
  // the canvas means something else: bring these systems in ALONGSIDE what is already here, so
  // they can be wired to it by hand. Never touches `dirty`'s replace-guard confirm; there is
  // nothing to discard.
  function sanitiseHint(s){ return String(s||"").replace(/[^A-Za-z0-9_]/g,"_"); }
  // A node label (RM009) and an exposure label (RM065) must each be unique across the WHOLE
  // project once merged, even though they were perfectly fine as the only file on someone's
  // disk. Mirrors ros_studio._unique_label's convention (name_hint, then name_hint_2, ...) so a
  // label an import renames here reads the same way a `seed_from_many` merge would have named it.
  function uniqueLabel(base,used,hint){
    if(!used[base]) return base;
    var h=sanitiseHint(hint), cand=base+"_"+h, n=2;
    while(used[cand]){ cand=base+"_"+h+"_"+n; n++; }
    return cand;
  }
  // seedFromFiles() (and a dropped project.json) each mint their own ids from 1 -- fine standing
  // alone, but two imports in the same drop, or an import against a project that already has
  // ids, would collide outright. Prefixing every id in the fragment with a per-import tag makes
  // collision impossible without needing to know anything about what is already on the canvas.
  function remapFragmentIds(proj,prefix){
    var nodeMap={}, ifaceMap={};
    (proj.nodes||[]).forEach(function(n){ nodeMap[n.id]=prefix+n.id; });
    (proj.nodes||[]).forEach(function(n){
      (n.ifaces||[]).forEach(function(f){ ifaceMap[n.id+" "+f.id]=prefix+f.id; });
    });
    (proj.connections||[]).forEach(function(c){
      var fi=ifaceMap[c.from.n+" "+c.from.i], ti=ifaceMap[c.to.n+" "+c.to.i];
      c.id=prefix+c.id;
      if(nodeMap[c.from.n]) c.from.n=nodeMap[c.from.n]; if(fi) c.from.i=fi;
      if(nodeMap[c.to.n]) c.to.n=nodeMap[c.to.n]; if(ti) c.to.i=ti;
    });
    (proj.nodes||[]).forEach(function(n){
      (n.ifaces||[]).forEach(function(f){ f.id=prefix+f.id; });
      (n.params||[]).forEach(function(p){ p.id=prefix+p.id; });
      n.id=prefix+n.id;
    });
    (proj.params||[]).forEach(function(p){ p.id=prefix+p.id; });
  }
  // Lands an imported fragment's own little grid (laid out relative to itself, starting near
  // the origin) as a whole block to the right of whatever is already on the canvas, so a second
  // and third import line up left-to-right instead of stacking on top of the first.
  function placeFragmentNodes(nodes){
    if(!nodes||!nodes.length) return;
    var DW=240, DH=130, GAP=60, bbox=null, fbbox=null;
    function grow(b,x,y,w,h){
      if(!b) return {minX:x,minY:y,maxX:x+w,maxY:y+h};
      b.minX=Math.min(b.minX,x); b.minY=Math.min(b.minY,y);
      b.maxX=Math.max(b.maxX,x+w); b.maxY=Math.max(b.maxY,y+h); return b;
    }
    project.nodes.forEach(function(n){ bbox=grow(bbox,n.x||0,n.y||0,DW,DH); });
    nodes.forEach(function(n){ fbbox=grow(fbbox,n.x||0,n.y||0,DW,DH); });
    var offX=bbox?(bbox.maxX+GAP-fbbox.minX):(80-fbbox.minX);
    var offY=bbox?(bbox.minY-fbbox.minY):(80-fbbox.minY);
    nodes.forEach(function(n){ n.x=(n.x||0)+offX; n.y=(n.y||0)+offY; });
  }
  // Folds one already-built project fragment (a seedFromFiles() result, or a dropped
  // project.json's own top level) into the live project: renames anything that collides,
  // merges packages/types/system-parameters without clobbering what is already declared, and
  // reports every rename or skip so nothing changes silently under the author.
  function mergeFragmentIntoProject(proj,srcName){
    var report=[];
    var hint=(proj.system&&proj.system.name)||srcName.replace(/\.[^.]+$/,"");
    remapFragmentIds(proj,"imp"+(++importSeq)+"_");

    var labelUsed={}; project.nodes.forEach(function(n){ labelUsed[n.label]=1; });
    var exposureUsed={};
    project.nodes.forEach(function(n){ (n.ifaces||[]).forEach(function(f){ if(f.label) exposureUsed[f.label]=1; }); });

    (proj.nodes||[]).forEach(function(n){
      // Provenance, the same field init's merge stamps (ros_studio.py, seed_from_many pass A).
      // An imported project.json fragment may already carry origins of its own from an earlier
      // merge -- keep those rather than flattening them onto this file's name, because the node
      // really did come from that system and re-labelling it here would lose a distinction the
      // canvas is about to draw. Only an untagged node adopts this import's name.
      if(!n.srcSystem) n.srcSystem=hint;
      var lbl=uniqueLabel(n.label,labelUsed,hint);
      if(lbl!==n.label){
        report.push("node '"+n.label+"' collides with one already on the canvas, renamed to '"+lbl+"'.");
        n.label=lbl;
      }
      labelUsed[lbl]=1;
      (n.ifaces||[]).forEach(function(f){
        if(!f.label) return;
        var elbl=uniqueLabel(f.label,exposureUsed,hint);
        if(elbl!==f.label){
          report.push("interface '"+f.label+"' on node '"+n.label+"' collides with an exposure "
            +"already on the canvas, renamed to '"+elbl+"'.");
          f.label=elbl;
        }
        exposureUsed[elbl]=1;
      });
    });

    placeFragmentNodes(proj.nodes||[]);
    project.nodes=project.nodes.concat(proj.nodes||[]);
    project.connections=project.connections.concat(proj.connections||[]);

    (proj.subSystems||[]).forEach(function(s){
      if(project.subSystems.some(function(x){return x.ref===s.ref;})) return;
      project.subSystems.push(s);
    });
    Object.keys(proj.packages||{}).forEach(function(pkg){
      if(!project.packages[pkg]) project.packages[pkg]=proj.packages[pkg];
    });
    Object.keys(proj.types||{}).forEach(function(k){
      if(!project.types[k]) project.types[k]=proj.types[k];
    });
    var spNames={}; project.params.forEach(function(p){ spNames[p.name]=1; });
    (proj.params||[]).forEach(function(p){
      if(spNames[p.name]){
        report.push("system parameter '"+p.name+"' is already declared, skipped from "+srcName+".");
        return;
      }
      project.params.push(p); spNames[p.name]=1;
    });

    return {added:(proj.nodes||[]).length, report:report};
  }
  // The drop target: one or more .rossystem (with whatever .ros2/.ros companions were dropped
  // alongside them, shared across all of them for type/artifact resolution) and/or project.json
  // files, each folded in as its own fragment via mergeFragmentIntoProject. Every .rossystem is
  // seeded on its OWN -- sibling .rossystem files in the same drop are deliberately NOT offered
  // to each other for subSystems: cross-linking, so two unrelated systems never partially merge
  // into one another by accident; each simply lands on the canvas as its own real nodes, ready
  // to be wired to anything else here by hand.
  function importFiles(fileList){
    readFiles(fileList, function(files){
      if(!files.length) return;
      var jsonFiles=[], sysFiles=[], companions=[];
      files.forEach(function(f){
        if(/\.json$/i.test(f.name)){
          try{
            var parsed=JSON.parse(f.text);
            if(parsed&&parsed.nodes&&parsed.system) jsonFiles.push({name:f.name,project:parsed});
            else alertBar(f.name+" does not look like a /ros-studio project.json.");
          }catch(e){ alertBar(f.name+" is not readable JSON: "+((e&&e.message)||e)); }
        } else if(/\.rossystem$/i.test(f.name)) sysFiles.push(f);
        else companions.push(f);   // .ros2 / .ros -- a shared type/artifact pool, not a system of its own
      });
      if(!jsonFiles.length&&!sysFiles.length){
        alertBar("Drop a project.json, or one or more .rossystem files (with their .ros2/.ros "
          +"companions if you have them, for real interface types and parameters).");
        return;
      }
      pushUndo("import");
      var notices=[];
      jsonFiles.forEach(function(jf){
        var rep=mergeFragmentIntoProject(jf.project,jf.name);
        notices.push({name:jf.name,added:rep.added,report:rep.report});
      });
      sysFiles.forEach(function(sf){
        var res=seedFromFiles([sf].concat(companions));
        if(res.error){ notices.push({name:sf.name,added:0,report:[res.error]}); return; }
        var rep=mergeFragmentIntoProject(res.project,sf.name);
        notices.push({name:sf.name,added:rep.added,report:(res.report||[]).concat(rep.report)});
      });
      fillNsList();
      var totalAdded=notices.reduce(function(s,n){return s+n.added;},0);
      var allNotes=[];
      notices.forEach(function(n){ n.report.forEach(function(r){ allNotes.push(n.name+": "+r); }); });
      opNotice={sev:allNotes.length?"warn":"ok",
        title:"Imported "+notices.length+" file(s)",
        html:"<b>"+totalAdded+" node(s) added</b> from "+notices.map(function(n){return esc(n.name);}).join(", ")
          +(allNotes.length?("<br>"+allNotes.map(function(r){return "&bull; "+esc(r);}).join("<br>")):"")
          +"<br>Wire them to the rest of the system, then <b>Commit</b>."};
      // The status chip carries the detail; this is just so a drop that lands off-screen, or one
      // that renames a colliding label, is not indistinguishable from a drop that did nothing.
      toast(totalAdded+" node(s) added from "+notices.map(function(n){return n.name;}).join(", ")
        +(allNotes.length?(" — "+allNotes.length+" note(s), see the status chip"):""));
      sizeCanvas(); render(); fillInspector(); fitView();
    });
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

  // Custom yes/no, in place of window.confirm(): a native dialog freezes the page's whole JS
  // thread while it is up (long enough to look like a hang to anything driving the page) and
  // matches nothing else in this UI. Callback rather than a return value, because unlike
  // confirm() this cannot answer synchronously.
  function askConfirm(title,bodyHtml,okLabel,onOk){
    var scrim=document.getElementById("confirmScrim");
    if(!scrim){ onOk(); return; }                       // no modal in the DOM: never block the action
    document.getElementById("confirmTitle").textContent=title;
    document.getElementById("confirmBody").innerHTML=bodyHtml;
    var ok=document.getElementById("confirmOk");
    ok.textContent=okLabel||"OK";
    scrim.classList.add("on");
    ok.onclick=function(){ scrim.classList.remove("on"); onOk(); };
    document.getElementById("confirmCancel").onclick=function(){ scrim.classList.remove("on"); };
    setTimeout(function(){ ok.focus(); },0);
  }
  function applyLoadedProject(next, sourceName, report, confirmed){
    // Same guard the autosave prompt uses: replacing the model is not undoable past the stack,
    // so unsaved work gets a chance to survive. `confirmed` is set only by the modal's own
    // callback below -- the guard asks once, then the answer comes back through here.
    if(dirty&&!confirmed){
      askConfirm("Replace the current project?",
        "<b>"+esc(sourceName)+"</b> replaces everything on this canvas. There are changes since "
        +"the last Commit, and loading discards them.<br>Import adds a file to what is already "
        +"here instead, without replacing it.",
        "Replace",
        function(){ applyLoadedProject(next,sourceName,report,true); });
      return false;
    }
    pushUndo("load:"+sourceName);
    project=next;
    DIAG=(project.diagnostics&&project.diagnostics.byNode)||{};   // this is a different project now
    selNode=null; selEdge=null; multiSel=Object.create(null);
    // The whole point of saving the view: a project.json comes back looking the way it was
    // saved. Returns whether it carried a camera, so the fitView() below is skipped when the
    // file already says where the reader was standing.
    var hadCamera=restoreViewState();
    if(project.system&&project.system.name)
      document.getElementById("sysname").value=project.system.name;
    fillNsList();
    if(report&&report.length){
      opNotice={sev:"warn",title:"Loaded "+sourceName,html:"<b>"+report.length
        +" note(s)</b> — the companion's <code>init</code> is the authoritative seeder:<br>"
        +report.map(function(r){return "• "+esc(r);}).join("<br>")};
    } else {
      opNotice={sev:"ok",title:"Loaded "+sourceName,html:"Edit, then <b>Commit</b> to hand the "
        +"project.json back to the Python companion for generation and validation."};
    }
    sizeCanvas(); render(); fillInspector();   // render() -> runIssues() -> buildStatus() picks up opNotice
    if(!hadCamera) fitView();                  // no saved camera: fall back to framing the system
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
          alertBar(f.name+" is not readable JSON: "+((e&&e.message)||e));
        }
      });
      if(proj){
        // a project.json is the page's OWN format -- loaded exactly, never re-seeded
        applyLoadedProject(proj, projName, (proj.diagnostics&&proj.diagnostics.global)||[]);
        return;
      }
      var res=seedFromFiles(files);
      if(res.error){ alertBar("Could not load: "+res.error); return; }
      applyLoadedProject(res.project, res.name, res.report);
    });
  }

  // Shared by the Open and Import buttons: both pick the same kind of files, they just hand
  // the result to a different function (openFiles replaces the project, importFiles adds to
  // it). pickerId keys the File System Access API's remembered last-used directory -- kept
  // distinct per button so opening your working project doesn't overwrite the folder memory
  // for the systems you import into it, and vice versa.
  function wireFilePickerButton(btn,input,pickerId,onFiles){
    if(!btn||!input) return;
    btn.onclick=function(){
      // The File System Access API remembers the last-used directory FOR THIS id across
      // reloads (Chromium keeps a per-id, not per-file, memory) -- <input type=file> gives the
      // page no visibility into which folder was used at all, by design, so there was nothing
      // for this app's own code to remember. Feature-detected here (call time, not load time)
      // so Firefox/Safari fall through to the plain input exactly as before; <input> itself
      // stays in the DOM either way.
      if(window.showOpenFilePicker){
        // MUST be the first thing that runs in this handler, with no await ahead of it: the
        // click's user-activation is what authorizes the picker, and it does not survive a
        // microtask boundary -- an async gap here turns this into a SecurityError instead of
        // a dialog.
        window.showOpenFilePicker({
          id:pickerId,
          multiple:true,
          excludeAcceptAllOption:false,       // keep "All files" reachable
          types:[{description:"RosTooling model files",
            accept:{"application/octet-stream":[".rossystem",".ros2",".ros",".json"]}}]
        }).then(function(handles){
          return Promise.all(handles.map(function(h){ return h.getFile(); }));
        }).then(onFiles)
        .catch(function(err){
          if(err&&err.name==="AbortError") return;   // the user cancelled -- not a failure
          input.value=""; input.click();              // anything else: fall back rather than look inert
        });
        return;
      }
      input.value=""; input.click();
    };
    input.onchange=function(){ onFiles(input.files); };
  }
  (function wireOpen(){
    wireFilePickerButton(document.getElementById("openBtn"),document.getElementById("openInput"),
      "rosStudioOpen",openFiles);
    wireFilePickerButton(document.getElementById("importBtn"),document.getElementById("importInput"),
      "rosStudioImport",importFiles);
    // Drag a whole model set onto the canvas. The default browser behaviour for a dropped file
    // is to NAVIGATE to it, which would discard the session, so both handlers are required.
    // Unlike Open (above), a drop IMPORTS -- adds to what is already on the canvas -- rather
    // than replacing it, so it never asks the dirty-guard question Open does.
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
      importFiles(e.dataTransfer.files);
    });
    window.addEventListener("dragover",function(e){
      if(e.dataTransfer&&Array.prototype.indexOf.call(e.dataTransfer.types||[],"Files")>=0)
        e.preventDefault();
    });
    window.addEventListener("drop",function(e){
      if(e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files.length) e.preventDefault();
    });
  })();

  // ---- Clear: wipe back to a blank system, with a one-time-skippable confirmation --------
  var SKIP_CLEAR_KEY="rosStudio.skipClearConfirm";
  function doClearProject(){
    pushUndo("clear");
    project.nodes=[]; project.connections=[]; project.subSystems=[]; project.params=[];
    project.packages={}; project.types={};
    project.system={name:"new_system",fromFile:null};
    delete project.comments;
    DIAG={}; selNode=null; selEdge=null; multiSel=Object.create(null);
    document.getElementById("sysname").value=project.system.name;
    fillNsList();
    opNotice={sev:"ok",title:"Cleared",
      html:"Blank system. Add a node from the rail, or drag .rossystem files onto the canvas to import."};
    sizeCanvas(); render(); fillInspector(); fitView();
  }
  (function wireClear(){
    var btn=document.getElementById("clearBtn"), scrim=document.getElementById("clearScrim");
    if(!btn||!scrim) return;
    btn.onclick=function(){
      var skip=false;
      try{ skip=localStorage.getItem(SKIP_CLEAR_KEY)==="1"; }catch(e){}
      if(skip){ doClearProject(); return; }
      document.getElementById("clearDontAsk").checked=false;
      scrim.classList.add("on");
    };
    document.getElementById("doClear").onclick=function(){
      if(document.getElementById("clearDontAsk").checked){
        try{ localStorage.setItem(SKIP_CLEAR_KEY,"1"); }catch(e){}
      }
      scrim.classList.remove("on");
      doClearProject();
    };
    document.getElementById("cancelClear").onclick=function(){ scrim.classList.remove("on"); };
  })();

  // ---- right-click a multi-selection: "Wrap in subsystem" ---------------------------------
  (function wireWrap(){
    var menu=document.getElementById("ctxMenu"), wrapBtn=document.getElementById("ctxWrap");
    if(!menu||!wrapBtn) return;
    var pendingIds=null;
    function closeMenu(){ menu.hidden=true; pendingIds=null; }
    canvas.addEventListener("contextmenu",function(ev){
      var el=ev.target.closest(".node");
      // only meaningful on a node that is part of an ACTIVE (2+) multi-selection -- a lone
      // node, or one outside the current selection, has nothing to wrap it WITH.
      if(!el||el.dataset.sub!==undefined) return;
      var id=el.dataset.n, keys=Object.keys(multiSel);
      if(keys.length<2||!multiSel[id]) return;
      ev.preventDefault();
      pendingIds=keys.slice();
      wrapBtn.textContent="Wrap "+keys.length+" nodes in a subsystem…";
      var mw=220, mh=44;   // clamp on-screen -- a right-click near the edge must not open off-canvas
      menu.style.left=Math.min(ev.clientX,window.innerWidth-mw-4)+"px";
      menu.style.top=Math.min(ev.clientY,window.innerHeight-mh-4)+"px";
      menu.hidden=false;
    });
    document.addEventListener("pointerdown",function(ev){
      if(!menu.hidden&&!menu.contains(ev.target)) closeMenu();
    });
    window.addEventListener("blur",closeMenu);
    document.addEventListener("scroll",closeMenu,true);

    var wrapScrim=document.getElementById("wrapScrim"), wrapName=document.getElementById("wrapName"),
        wrapErr=document.getElementById("wrapErr");
    var pendingWrapIds=null;
    wrapBtn.onclick=function(){
      var ids=pendingIds; closeMenu();
      if(!ids) return;
      pendingWrapIds=ids;
      wrapName.value=""; wrapErr.hidden=true;
      wrapScrim.classList.add("on");
      setTimeout(function(){ wrapName.focus(); },0);
    };
    function submitWrap(){
      var res=wrapNodesInSubsystem(pendingWrapIds||[],wrapName.value);
      if(res.error){ wrapErr.textContent=res.error; wrapErr.hidden=false; return; }
      wrapScrim.classList.remove("on"); pendingWrapIds=null;
      multiSel=Object.create(null); selNode=null; selEdge=null; selSub=res.ref||null;
      render(); fillInspector(); fitView();
    }
    document.getElementById("doWrap").onclick=submitWrap;
    document.getElementById("cancelWrap").onclick=function(){
      wrapScrim.classList.remove("on"); pendingWrapIds=null;
    };
    wrapName.addEventListener("keydown",function(ev){
      if(ev.key==="Enter"){ ev.preventDefault(); submitWrap(); }
    });
  })();

  // ============================ inline editing on the card ============================
  // The inspector remains the complete surface -- every field lives there. This covers the two
  // or three edits you reach for constantly (rename the instance, rename an exposure, retype
  // it) without crossing the window for each one. Double-click the text; Enter commits, Escape
  // cancels, blur commits. Read-only backings (subsystem, and a catalogue node's interfaces)
  // refuse, because those names belong to the referenced file, not to this one.
  // A small "search as you type" dropdown for a text input backed by a candidate list, in
  // place of the browser's own <datalist> -- which, for this app's message-type catalogue
  // (600+ entries once a real project is loaded), renders every one of them, unfiltered and
  // unstyled, in whatever a given browser feels like doing with a list that long. Returns a
  // controller rather than wiring its own keydown/blur listeners, so a caller that already owns
  // the input's keyboard handling (inlineEdit, below) can drive it without two listeners on the
  // same element racing each other over the same keys.
  // opts.getMru, when given, is called fresh on every open() -- a function, not a snapshot
  // array, so a pick recorded by ANOTHER instance of this widget (the inline canvas editor
  // and the add-interface form each make their own) is visible the next time either opens.
  function makeTypeahead(inputEl,candidates,onPick,opts){
    var box=null,items=[],activeIdx=-1,dividerAt=-1;
    function close(){ if(box){ box.remove(); box=null; } activeIdx=-1; }
    function position(){
      if(!box) return;
      var r=inputEl.getBoundingClientRect();
      box.style.left=Math.max(4,Math.min(r.left,window.innerWidth-box.offsetWidth-4))+"px";
      box.style.top=(r.bottom+2)+"px"; box.style.width=Math.max(r.width,240)+"px";
    }
    function open(){
      var q=inputEl.value.trim().toLowerCase();
      dividerAt=-1;
      if(!q&&opts&&opts.getMru){
        // empty query: recent picks first (already most-recent-first), backfilled with the
        // rest of the catalogue -- deduped -- up to 40, rather than showing 8 rows and
        // nothing else, which would look broken. A blank query previously fell through to
        // the sort below with every indexOf("") tying at 0, so it silently showed the 40
        // SHORTEST names in the whole catalogue -- not "recent", not alphabetical, just an
        // artifact of the comparator -- which is exactly the empty-box case MRU replaces.
        var seen={}, mru=[];
        (opts.getMru()||[]).forEach(function(m){ if(candidates.indexOf(m)>=0&&!seen[m]){ seen[m]=1; mru.push(m); } });
        if(mru.length){
          var rest=[];
          candidates.forEach(function(c){ if(rest.length+mru.length<40&&!seen[c]){ seen[c]=1; rest.push(c); } });
          items=mru.concat(rest);
          dividerAt=mru.length<items.length?mru.length:-1;
        } else items=candidates.slice(0,40);
      } else {
        // substring, not prefix: a package/msg/Name string is often recalled by the NAME
        // ("Odometry") rather than the package it lives in, which a prefix-only match would
        // miss entirely. Ranked so a prefix/earlier hit still sorts above a coincidental one.
        var matches=q?candidates.filter(function(c){return c.toLowerCase().indexOf(q)>=0;}):candidates;
        items=matches.slice().sort(function(a,b){
          var aw=a.toLowerCase().indexOf(q),bw=b.toLowerCase().indexOf(q);
          return aw!==bw?aw-bw:a.length-b.length;
        }).slice(0,40);      // 602 rows was the whole complaint -- never render anywhere near that many
      }
      if(activeIdx>=items.length) activeIdx=items.length-1;
      if(!box){
        box=document.createElement("div"); box.className="typeahead-box";
        // On the CONTAINER, not just each row: a row's own preventDefault() left the box's own
        // padding, its "no match" state, and -- the list is routinely taller than its 280px
        // max-height, so there is always one -- its scrollbar free to blur the input on
        // mousedown after all, which (now that blur closes the box immediately, see wireTypeahead)
        // tore the box out from under a click aimed at it.
        box.onmousedown=function(ev){ ev.preventDefault(); };
        document.body.appendChild(box);
      }
      box.innerHTML="";
      if(!items.length){ var e=document.createElement("div"); e.className="ta-empty"; e.textContent="no match"; box.appendChild(e); }
      items.forEach(function(m,i){
        if(i===0&&dividerAt>0){ var h1=document.createElement("div"); h1.className="ta-divider"; h1.textContent="recent"; box.appendChild(h1); }
        if(i===dividerAt){ var h2=document.createElement("div"); h2.className="ta-divider"; h2.textContent="all types"; box.appendChild(h2); }
        var row=document.createElement("div"); row.className="ta-row"+(i===activeIdx?" active":"");
        row.textContent=m;
        row.onmousedown=function(){ pick(m); };
        box.appendChild(row);
      });
      position();
    }
    function pick(v){ inputEl.value=v; close(); onPick(v); }
    return {
      open:open, close:close,
      isOpen:function(){ return !!box; },
      moveActive:function(delta){ if(!box) open(); activeIdx=Math.max(0,Math.min(items.length-1,activeIdx+delta)); open(); },
      pickActive:function(){ if(activeIdx>=0&&items[activeIdx]){ pick(items[activeIdx]); return true; } return false; }
    };
  }
  // Wires a typeahead onto a PERSISTENT input (an interface row's own type field, a .ros field
  // type box) -- as opposed to inlineEdit's transient one, below, which owns the input's whole
  // lifecycle.
  function wireTypeahead(inputEl,candidates){
    // picking dispatches a real "input" event so any OTHER listener already on this element
    // (the row's own resolve-status hint, wired at its call site) still fires -- but that event
    // would otherwise also reach the "input" listener two lines down and immediately reopen the
    // box it was just closed by. suppressNext eats exactly that one echo.
    var suppressNext=false;
    var ta=makeTypeahead(inputEl,candidates,function(){
      suppressNext=true; inputEl.dispatchEvent(new Event("input",{bubbles:true})); inputEl.focus();
    },{getMru:loadRecentTypes});
    inputEl.addEventListener("input",function(){ if(suppressNext){ suppressNext=false; return; } ta.open(); });
    inputEl.addEventListener("focus",ta.open);
    // Close IMMEDIATELY, not after a delay: a row's own mousedown already calls
    // preventDefault() (below), which cancels the browser's default focus-change behaviour for
    // that click -- the input never actually blurs from a row click, so there was nothing for a
    // delay to protect. What it did instead: a REAL blur (moving focus to another control, e.g.
    // "+ add interface" sitting right below this field) left the still-open dropdown -- a
    // position:fixed, z-index:80 box -- sitting on top of that control for the next 120ms, and a
    // click landing in that window hit the (unhandled) dropdown background instead of the
    // button underneath it. Silently. That was bug-for-bug identical to the type actually having
    // been picked and the add going nowhere.
    inputEl.addEventListener("blur",ta.close);
    inputEl.addEventListener("keydown",function(e){
      if(e.key==="ArrowDown"){ e.preventDefault(); ta.moveActive(1); }
      else if(e.key==="ArrowUp"){ e.preventDefault(); ta.moveActive(-1); }
      else if(e.key==="Enter"){ if(ta.pickActive()) e.preventDefault(); }
      else if(e.key==="Escape"&&ta.isOpen()){ ta.close(); e.preventDefault(); e.stopPropagation(); }
    });
  }
  function inlineEdit(el,value,opts,commit){
    if(!el||canvas.querySelector("[data-inline]")) return;      // one editor at a time
    opts=opts||{};
    var inp=document.createElement("input");
    inp.setAttribute("data-inline","1");
    inp.className="inline";
    inp.autocomplete="off";
    inp.value=value==null?"":String(value);
    if(opts.placeholder) inp.placeholder=opts.placeholder;
    // width in MODEL units: the card is inside the zoom transform, so a screen-space width
    // would shrink the box as you zoom out.
    var w=el.getBoundingClientRect().width/(view.k||1);
    inp.style.width=Math.round(Math.max(w,60)+28)+"px";
    el.parentNode.insertBefore(inp,el);
    el.style.display="none";
    var done=false;
    var ta=opts.typeahead?makeTypeahead(inp,opts.typeahead,function(){finish(true);},{getMru:loadRecentTypes}):null;
    function finish(ok){
      if(done) return;
      done=true;
      if(ta) ta.close();
      var v=inp.value;
      if(inp.parentNode) inp.parentNode.removeChild(inp);
      el.style.display="";
      if(ok) commit(v); else render();
    }
    inp.addEventListener("input",function(){ if(ta) ta.open(); });
    inp.addEventListener("keydown",function(e){
      // the canvas owns Ctrl+Z / Delete / arrow keys; while typing a name it must not.
      e.stopPropagation();
      if(ta&&e.key==="ArrowDown"){ e.preventDefault(); ta.moveActive(1); return; }
      if(ta&&e.key==="ArrowUp"){ e.preventDefault(); ta.moveActive(-1); return; }
      if(e.key==="Enter"){ e.preventDefault(); if(ta&&ta.pickActive()) return; finish(true); }
      else if(e.key==="Escape"){ e.preventDefault(); if(ta&&ta.isOpen()){ ta.close(); return; } finish(false); }
    });
    inp.addEventListener("blur",function(){finish(true);});
    inp.addEventListener("pointerdown",function(e){e.stopPropagation();});
    inp.focus();
    inp.select();
    // seeing the full (top-40) list right away, before typing a character, is more useful than
    // an empty box when the author is re-editing a value they already know roughly, not typing
    // one from nothing.
    if(ta) ta.open();
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
        inlineEdit(ty,f.type||"",{typeahead:TYPES,placeholder:"pkg/msg/Type"},function(v){
          v=v.trim();
          if(v===(f.type||"")){render();return;}
          pushUndo("itype:"+f.id);
          f.type=v||null;
          announceTypeFill(propagateInterfaceType(n,f),v);
          recordRecentType(v);
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
  function wireCanvas(){
    canvas.addEventListener("pointerdown",function(ev){
      // The WHOLE card selects and drags, not just its title bar: a node is one object, and
      // having to hit a 20px strip to pick it up is the kind of thing you only forgive in
      // software you wrote yourself. Three exceptions, each of which owns its own gesture:
      // a port starts a wire, an inline editor is being typed into, and anything explicitly
      // marked interactive.
      if(ev.target.closest(".port")||ev.target.closest("[data-inline]")
         ||ev.target.closest("input,textarea,select,button")) return;
      // A deps-view package box is not a node either -- same reasoning as the subsystem box
      // below, its position lives in pkgPos (a VIEW), never touches the model, and is not
      // undoable. Checked first because .pkgbox carries no "node" class (see the .node,.pkgbox
      // pairing everywhere else this view is touched) and so would otherwise fall through to
      // "no drag target" below.
      var pkgEl=ev.target.closest(".pkgbox");
      if(pkgEl){
        closeNodeIssuePopIfOpen();
        var pname=pkgEl.dataset.pkg, pp=pkgPos[pname]||{x:pkgEl.offsetLeft,y:pkgEl.offsetTop};
        pkgPos[pname]=pp;
        dragState={pkg:pname,px:ev.clientX,py:ev.clientY,ox:pp.x,oy:pp.y,moved:0};
        try{pkgEl.setPointerCapture(ev.pointerId);}catch(e){}
        return;
      }
      var el=ev.target.closest(".node");
      if(!el) return;
      closeNodeIssuePopIfOpen();   // about to drag -- see the comment on this function
      // A collapsed subsystem box stands for N nodes but is not one: its position lives in
      // subPos (a VIEW), not on any node, so it is dragged without touching the model and
      // without entering the undo history -- undo restores what the file will say.
      if(el.dataset.sub!==undefined){
        var sref=el.dataset.sub, sp=subPos[sref]||{x:el.offsetLeft,y:el.offsetTop};
        subPos[sref]=sp;
        dragState={sub:sref,px:ev.clientX,py:ev.clientY,ox:sp.x,oy:sp.y,moved:0};
        try{el.setPointerCapture(ev.pointerId);}catch(e){}
        return;
      }
      // An origin container is the same kind of thing on the other axis: it stands for N nodes,
      // its position is a VIEW (sysPos), and dragging it must not touch the model or the undo
      // history. Its member nodes keep their own x/y untouched underneath.
      if(el.dataset.sys!==undefined){
        var yref=el.dataset.sys, yp=sysPos[yref]||{x:el.offsetLeft,y:el.offsetTop};
        sysPos[yref]=yp;
        dragState={sys:yref,px:ev.clientX,py:ev.clientY,ox:yp.x,oy:yp.y,moved:0};
        try{el.setPointerCapture(ev.pointerId);}catch(e){}
        return;
      }
      var n=nodeById(el.dataset.n);
      if(!n) return;
      // Ctrl/Cmd+click adjusts the multi-selection instead of picking the node up: a held
      // modifier means "add/remove this from what's selected," never "start a drag." The first
      // Ctrl+click after a plain single selection folds that existing selNode in too, so two
      // clicks (one plain, one Ctrl) are enough to start a group of two.
      if(ev.ctrlKey||ev.metaKey){
        if(!Object.keys(multiSel).length&&selNode&&selNode!==n.id) multiSel[selNode]=1;
        if(multiSel[n.id]) delete multiSel[n.id]; else multiSel[n.id]=1;
        var keys=Object.keys(multiSel);
        if(keys.length<=1){ selNode=keys.length?keys[0]:null; multiSel=Object.create(null); }
        else selNode=null;
        selEdge=null; selSub=null; render(); fillInspector();
        return;
      }
      // Picking up a node that is already part of an active (2+) multi-selection drags the
      // whole group, each member keeping its own offset from the pointer.
      var group=null;
      if(multiSel[n.id]&&Object.keys(multiSel).length>1){
        group=Object.keys(multiSel).map(function(id){
          var nn=nodeById(id); return nn?{node:nn,ox:nn.x,oy:nn.y}:null;
        }).filter(Boolean);
      }
      // snapshot the pre-drag layout now; it is only pushed on pointerup if the pointer
      // actually moved, so selecting a node does not fill the undo stack with no-ops.
      dragState={n:n,group:group,px:ev.clientX,py:ev.clientY,ox:n.x,oy:n.y,moved:0,snap:snapshot()};
      try{el.setPointerCapture(ev.pointerId);}catch(e){}
    });
    canvas.addEventListener("pointermove",function(ev){
      if(!dragState) return;
      var k=view.k||1;
      var ddx=(ev.clientX-dragState.px)/k, ddy=(ev.clientY-dragState.py)/k;
      dragState.moved+=Math.abs(ddx)*k+Math.abs(ddy)*k;   // the click threshold is in PIXELS
      if(dragState.sub){
        var sp=subPos[dragState.sub];
        sp.x=Math.max(0,dragState.ox+ddx); sp.y=Math.max(0,dragState.oy+ddy);
        var sel=canvas.querySelector('.node.subbox[data-sub="'+STUDIO.cssEsc(dragState.sub)+'"]');
        if(sel){ sel.style.left=sp.x+"px"; sel.style.top=sp.y+"px"; }
        drawEdges();
        return;
      }
      if(dragState.pkg){
        var pp=pkgPos[dragState.pkg];
        pp.x=Math.max(0,dragState.ox+ddx); pp.y=Math.max(0,dragState.oy+ddy);
        var pel=canvas.querySelector('.pkgbox[data-pkg="'+STUDIO.cssEsc(dragState.pkg)+'"]');
        if(pel){ pel.style.left=pp.x+"px"; pel.style.top=pp.y+"px"; }
        drawEdges();
        return;
      }
      if(dragState.sys){
        var yp=sysPos[dragState.sys];
        yp.x=Math.max(0,dragState.ox+ddx); yp.y=Math.max(0,dragState.oy+ddy);
        var yel=canvas.querySelector('.node.sysbox[data-sys="'+STUDIO.cssEsc(dragState.sys)+'"]');
        if(yel){ yel.style.left=yp.x+"px"; yel.style.top=yp.y+"px"; }
        drawEdges();
        return;
      }
      if(dragState.group){
        dragState.group.forEach(function(g){
          g.node.x=Math.max(0,g.ox+ddx); g.node.y=Math.max(0,g.oy+ddy);
          var gel=canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(g.node.id)+'"]');
          if(gel){ gel.style.left=g.node.x+"px"; gel.style.top=g.node.y+"px"; }
        });
        drawEdges();
        return;
      }
      // never negative: the SVG wire layer starts at the canvas origin, so a node dragged
      // above/left of it would keep its box but lose its edges.
      dragState.n.x=Math.max(0,dragState.ox+ddx); dragState.n.y=Math.max(0,dragState.oy+ddy);
      var el=canvas.querySelector('.node[data-n="'+dragState.n.id+'"]');
      el.style.left=dragState.n.x+"px"; el.style.top=dragState.n.y+"px"; drawEdges();
    });
    canvas.addEventListener("pointerup",function(ev){
      if(!dragState) return;
      var wasClick=dragState.moved<5, n=dragState.n, snap=dragState.snap;
      var sref=dragState.sub, pref=dragState.pkg, yref=dragState.sys; dragState=null;
      if(yref){
        // Like the package box: no inspector of its own (the nodes it stands for each have one,
        // and they are one level down), so a click is a no-op and only a real drag needs the
        // canvas re-measured.
        if(!wasClick) noteViewChange();
        if(!wasClick) sizeCanvas();
        return;
      }
      if(sref){
        // a click on the box selects it and shows the system panel, where its view state and
        // its "open" button live; a drag just leaves it where it was dropped (no undo entry)
        if(wasClick){ selSub=sref; selNode=null; selEdge=null; multiSel=Object.create(null); render(); fillInspector();
                      revealInspector(); }
        else { noteViewChange(); sizeCanvas(); }
        return;
      }
      if(pref){
        // no inspector of its own -- a package box is a read-only summary -- so a click is a
        // no-op and only an actual drag (which already moved it live, above) needs the canvas
        // re-measured for scrollbars/fitView.
        if(!wasClick){ noteViewChange(); sizeCanvas(); }
        return;
      }
      if(wasClick){
        // a plain click (no drag) always narrows the selection down to just this node, whether
        // it was part of a group or not; Ctrl+click (handled in pointerdown, above) is the only
        // gesture that ADDS to a group.
        multiSel=Object.create(null);
        selNode=n.id;selEdge=null;selSub=null;render();fillInspector();revealInspector();
      }
      else {sizeCanvas();pushSnapshot(snap);}
    });
    // Background drag = PAN. It shares its pointerdown with "click empty space to deselect",
    // which is why the deselect only fires when the pointer did not travel: dragging the
    // canvas to look somewhere else is not a decision to drop the selection.
    canvas.addEventListener("pointerdown",function(ev){
      if(ev.target!==canvas&&ev.target!==svg) return;
      closeNodeIssuePopIfOpen();
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
      if(wasClick){selNode=null;selEdge=null;multiSel=Object.create(null);render();fillInspector();}
    });
    // connection drawing
    canvas.addEventListener("pointerdown",function(ev){
      if(mode!=="edit") return;
      var port=ev.target.closest(".port"); if(!port) return;
      ev.stopPropagation();
      closeNodeIssuePopIfOpen();   // a 380px, up-to-70vh popover can otherwise sit over the drop target for the whole drag
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
      // NOT ev.target: canvas.setPointerCapture() above (needed so the rubber-band keeps
      // tracking even when the pointer strays off the canvas mid-drag) means every subsequent
      // event for this pointer -- pointermove AND pointerup -- reports its target as the
      // capturing element itself, per the Pointer Events spec, regardless of what is actually
      // under the cursor at drop time. ev.target.closest(".port.legal") was therefore
      // evaluating against <canvas>, which is never a port and never has one as an ancestor --
      // a REAL drag-drop onto a port could not complete; a synthetic test that dispatches
      // pointerup directly at a port element (bypassing capture redirection) never exercised the
      // bug. elementFromPoint reads the real geometry instead.
      var real=document.elementFromPoint(ev.clientX,ev.clientY);
      var tgt=real&&real.closest(".port");
      // the dot itself is a 12px target, half of it hanging off the card edge -- releasing on
      // the interface ROW (the natural, much bigger target) is a legitimate drop, not a miss.
      if(!tgt&&real){ var rowEl=real.closest(".iface"); if(rowEl) tgt=rowEl.querySelector(".port"); }
      // Legality is recomputed HERE, fresh, against the model -- not read off the `.legal` CSS
      // class the pointerdown handler stamped onto ports at drag-START. Anything that calls
      // render() mid-drag (an inline editor -- rename a node, then without clicking elsewhere
      // start dragging a wire -- commits and re-renders on blur, and the pointerdown that begins
      // the drag can itself trigger exactly that blur) throws every node card away and redraws
      // it, taking the stamped classes with it; the drop would otherwise fail on a perfectly
      // legal target for a reason that has nothing to do with the drop itself.
      if(tgt){
        var srcIface=ifaceById(nodeById(wire.from.n),wire.from.i);
        var srcType=(srcIface&&srcIface.type)||"", wantKind=COMPLEMENT[wire.from.kind];
        var ttType=tgt.dataset.type||"";
        var typeOk=(!srcType||!ttType||srcType===ttType);
        var legal=(tgt.dataset.kind===wantKind && tgt.dataset.n!==wire.from.n && typeOk);
        if(!legal) tgt=null;
      }
      if(tgt){
        var a={n:wire.from.n,i:wire.from.i,kind:wire.from.kind};
        var bb={n:tgt.dataset.n,i:tgt.dataset.i,kind:tgt.dataset.kind};
        var fromEnd=SRC_SIDE[a.kind]?a:bb, toEnd=SRC_SIDE[a.kind]?bb:a;
        var dup=project.connections.some(function(c){return c.from.n===fromEnd.n&&c.from.i===fromEnd.i&&c.to.n===toEnd.n&&c.to.i===toEnd.i;});
        if(!dup){
          pushUndo();
          // Infer, don't just permit: wiring a fresh subscriber to a typed publisher (or the
          // reverse) almost always means the same message, and retyping the SAME thing on both
          // ends of a wire the author just drew by hand is exactly the busywork this editor
          // exists to remove. Only ever fills a BLANK side -- both-typed already had to match to
          // be a legal drop (see the `typeOk` check above) -- and only on a hand-authored node: a
          // catalogue or subSystems: interface's type is fixed by the file it comes from, and
          // this editor has no way to change what that file says.
          var fromIface=ifaceById(nodeById(fromEnd.n),fromEnd.i), toIface=ifaceById(nodeById(toEnd.n),toEnd.i);
          var fromNode=nodeById(fromEnd.n), toNode=nodeById(toEnd.n);
          if(fromIface&&toIface){
            var fromBlank=!String(fromIface.type||"").trim(), toBlank=!String(toIface.type||"").trim();
            if(fromBlank&&!toBlank&&fromNode&&fromNode.backing==="hand"){
              fromIface.type=toIface.type;
              announceTypeFill([fromNode.label+"."+fromIface.name],fromIface.type);
            } else if(toBlank&&!fromBlank&&toNode&&toNode.backing==="hand"){
              toIface.type=fromIface.type;
              announceTypeFill([toNode.label+"."+toIface.name],toIface.type);
            }
          }
          project.connections.push({id:nid(),from:{n:fromEnd.n,i:fromEnd.i},to:{n:toEnd.n,i:toEnd.i}});
          // The other half of setSubExposure's rule. That one refuses to UNexpose a wired
          // interface; nothing exposed one when a wire was newly drawn to it -- and a wrapped
          // subsystem's box offers a port for every interface it has, exposed or not. So wiring
          // one of the unexposed ones produced an endpoint in this file naming an interface the
          // subsystem's own file never declares: RM050, the exact failure wrapping was fixed for.
          var exposedNow=[ensureSubEndpointExposed(fromEnd.n,fromEnd.i),
                          ensureSubEndpointExposed(toEnd.n,toEnd.i)].filter(Boolean);
          if(exposedNow.length)
            toast(exposedNow.join(" and ")+" now exposed by its subsystem");
        }
      }
      wire=null;
      canvas.querySelectorAll(".port").forEach(function(p){p.classList.remove("legal","illegal");});
      var rb=document.getElementById("rb"); if(rb) rb.remove();
      render();
    });
    // A pointercancel (the OS takes the gesture -- a system gesture, an alt-tab mid-drag, a
    // touch scroll claimed by the browser) fires instead of pointerup and none of the three
    // gestures above listen for it, so wire/dragState/panState, the .legal/.illegal classes and
    // the rubber-band path could all outlive the drag that created them.
    canvas.addEventListener("pointercancel",function(){
      wire=null; dragState=null; panState=null;
      canvasWrap.classList.remove("panning");
      canvas.querySelectorAll(".port").forEach(function(p){p.classList.remove("legal","illegal");});
      var rb=document.getElementById("rb"); if(rb) rb.remove();
      render();
    });
  }
  var dragState=null, wire=null, panState=null;
  wireCanvas();
  wireInline();

  // ============================ small screens ============================
  // The two side panels become overlay drawers below 860px (see the media query). Everything
  // here is inert on a desktop: the buttons are display:none and the class on <body> selects
  // nothing, so there is one layout in the DOM and only its presentation changes.
  // ONE measurement, one class, consulted by both the stylesheet and the code below. screen.width
  // is in the list because an in-app webview may ignore the viewport meta and lay the page out
  // at a notional desktop width -- the CSS pixels then say "desktop" while the device in the
  // user's hand is 390px across, which is exactly the case that shipped broken.
  var NARROW_PX=860, TINY_PX=520;
  function viewportW(){
    var w=[];
    if(document.documentElement&&document.documentElement.clientWidth)
      w.push(document.documentElement.clientWidth);
    if(window.innerWidth) w.push(window.innerWidth);
    if(window.screen&&window.screen.width) w.push(window.screen.width);
    return w.length?Math.min.apply(Math,w):1200;
  }
  function syncNarrow(){
    var w=viewportW(), narrow=w<=NARROW_PX;
    document.body.classList.toggle("narrow",narrow);
    document.body.classList.toggle("tiny",narrow&&w<=TINY_PX);
    if(!narrow) closeDrawers();          // the button that would close it is hidden up there
  }
  function isNarrow(){ return document.body.classList.contains("narrow"); }
  function closeDrawers(){ document.body.classList.remove("drawer-l","drawer-r"); }
  function openDrawer(side){
    // one at a time: two overlapping drawers on a 390px screen leaves no canvas at all
    document.body.classList.remove("drawer-l","drawer-r");
    document.body.classList.add(side==="l"?"drawer-l":"drawer-r");
  }
  // Tapping a node on a phone should SHOW you the node, not silently repaint a panel that is
  // off screen. Only on a narrow viewport, and only from a deliberate tap -- render() runs on
  // every edit and a drawer that reopened each time would be unusable.
  function revealInspector(){ if(isNarrow()) openDrawer("r"); }
  function toggleDrawer(side){
    var cls=(side==="l")?"drawer-l":"drawer-r";
    if(document.body.classList.contains(cls)) closeDrawers(); else openDrawer(side);
  }
  (function(){
    var rt=document.getElementById("railToggle"), it=document.getElementById("inspToggle"),
        sc=document.getElementById("drawerScrim"), cl=document.getElementById("drawerClose");
    if(rt) rt.onclick=function(){ toggleDrawer("l"); };
    if(it) it.onclick=function(){ toggleDrawer("r"); };
    if(sc) sc.onclick=closeDrawers;
    if(cl) cl.onclick=closeDrawers;
    // Escape is the fourth way out, and the one that works when a panel has somehow ended up
    // covering its own controls.
    document.addEventListener("keydown",function(ev){
      if(ev.key==="Escape"&&(document.body.classList.contains("drawer-l")
                             ||document.body.classList.contains("drawer-r"))){
        closeDrawers(); ev.stopPropagation();
      }
    },true);
    syncNarrow();
    window.addEventListener("resize",syncNarrow);
    window.addEventListener("orientationchange",syncNarrow);
  })();

  // ---- resizable side panels ---------------------------------------------------------------
  // The rail is a fixed 190px and the inspector 298px, which is right for a laptop and wrong at
  // both ends: on a wide screen the inspector truncates message types it has room for twice
  // over, and on a small one the two of them are half the window before any graph is drawn.
  // Widths live in CSS custom properties so the drag only writes ONE value each and the layout
  // reflows itself; nothing about node positions or edges is in viewport coordinates, so there
  // is nothing to recompute or redraw when a panel changes size.
  var PANEL_KEY="rosStudio.panelWidths";
  var RAIL_DEF=190, INSP_DEF=298, RAIL_MIN=150, INSP_MIN=220, CANVAS_MIN=320;
  var panelW={rail:RAIL_DEF,insp:INSP_DEF};
  function clampPanels(){
    var vw=viewportW();
    panelW.rail=Math.max(RAIL_MIN,Math.min(panelW.rail,Math.min(420,vw*0.35)));
    panelW.insp=Math.max(INSP_MIN,Math.min(panelW.insp,Math.min(560,vw*0.45)));
    // Neither panel may squeeze the canvas below CANVAS_MIN, however each was arrived at.
    // Taken off whichever is currently wider, so shrinking the window does not collapse the
    // panel you happen to have been resizing.
    var over=(panelW.rail+panelW.insp+CANVAS_MIN)-vw;
    while(over>0){
      var wide=(panelW.rail-RAIL_MIN)>=(panelW.insp-INSP_MIN)?"rail":"insp";
      var floor=wide==="rail"?RAIL_MIN:INSP_MIN;
      var give=Math.min(over,panelW[wide]-floor);
      if(give<=0) break;             // both at their floor: a viewport this small is body.narrow
      panelW[wide]-=give; over-=give;
    }
  }
  function applyPanels(){
    document.documentElement.style.setProperty("--rail-w",Math.round(panelW.rail)+"px");
    document.documentElement.style.setProperty("--insp-w",Math.round(panelW.insp)+"px");
    var r=document.getElementById("railResizer"), s=document.getElementById("inspResizer");
    if(r) r.setAttribute("aria-valuenow",String(Math.round(panelW.rail)));
    if(s) s.setAttribute("aria-valuenow",String(Math.round(panelW.insp)));
  }
  function savePanels(){
    try{ localStorage.setItem(PANEL_KEY,JSON.stringify({rail:Math.round(panelW.rail),insp:Math.round(panelW.insp)})); }catch(e){}
  }
  (function wireResizers(){
    try{
      var got=JSON.parse(localStorage.getItem(PANEL_KEY)||"{}");
      if(got&&typeof got.rail==="number") panelW.rail=got.rail;
      if(got&&typeof got.insp==="number") panelW.insp=got.insp;
    }catch(e){}
    clampPanels(); applyPanels();
    // the head script restored these unclamped to avoid a flash; a window narrower than the one
    // they were saved on has to be honoured now that there is one to measure.
    window.addEventListener("resize",function(){ clampPanels(); applyPanels(); });

    function drive(el,which,sign,defW){
      if(!el) return;
      el.setAttribute("aria-valuemin",String(which==="rail"?RAIL_MIN:INSP_MIN));
      var drag=null;
      el.addEventListener("pointerdown",function(ev){
        if(isNarrow()) return;                       // drawers: nothing beside them to resize
        ev.preventDefault();                          // or the pointer drag selects text instead
        drag={x:ev.clientX,w:panelW[which]};
        el.classList.add("dragging"); document.body.classList.add("resizing");
        try{ el.setPointerCapture(ev.pointerId); }catch(e){}
      });
      el.addEventListener("pointermove",function(ev){
        if(!drag) return;
        // sign: the rail grows as the pointer moves right, the inspector as it moves left.
        panelW[which]=drag.w+sign*(ev.clientX-drag.x);
        clampPanels(); applyPanels();
      });
      function end(){
        if(!drag) return;
        drag=null;
        el.classList.remove("dragging"); document.body.classList.remove("resizing");
        savePanels();
      }
      el.addEventListener("pointerup",end);
      el.addEventListener("pointercancel",end);      // the OS took the gesture mid-drag
      // Double-click a separator to put it back -- the standard gesture, and the only way out of
      // a width you dragged to somewhere unusable without hunting for a menu item.
      el.addEventListener("dblclick",function(){
        panelW[which]=defW; clampPanels(); applyPanels(); savePanels();
      });
      el.addEventListener("keydown",function(ev){
        var step=ev.shiftKey?48:16, moved=true;
        if(ev.key==="ArrowLeft") panelW[which]-=sign*step;
        else if(ev.key==="ArrowRight") panelW[which]+=sign*step;
        else if(ev.key==="Home") panelW[which]=defW;
        else moved=false;
        if(!moved) return;
        ev.preventDefault();
        clampPanels(); applyPanels(); savePanels();
      });
    }
    drive(document.getElementById("railResizer"),"rail",1,RAIL_DEF);
    drive(document.getElementById("inspResizer"),"insp",-1,INSP_DEF);
  })();

  // ---- pinch to zoom, two-finger pan -------------------------------------------------------
  // .canvas-wrap sets touch-action:none, which hands the browser's own pan/pinch to us -- so
  // without this a phone could pan and drag but had NO way to zoom at all (the desktop gesture
  // is ctrl/⌘+wheel, and the buttons step in fixed increments).
  //
  // Tracked on the wrap, not the canvas: the canvas is the element being transformed, and a
  // pointer that starts on a node still belongs to the gesture.
  var touches={}, pinch=null;
  canvasWrap.addEventListener("pointerdown",function(ev){
    if(ev.pointerType==="mouse") return;
    touches[ev.pointerId]={x:ev.clientX,y:ev.clientY};
    var ids=Object.keys(touches);
    if(ids.length===2){
      closeNodeIssuePopIfOpen();   // a second finger means pinch-zoom is starting
      // A second finger CANCELS whatever one finger had started -- otherwise the node under
      // the first finger is dragged across the canvas while the user is only zooming.
      if(dragState){
        if(dragState.group){
          dragState.group.forEach(function(g){ g.node.x=g.ox; g.node.y=g.oy; });
        } else if(dragState.n){ dragState.n.x=dragState.ox; dragState.n.y=dragState.oy; }
        else if(dragState.sub&&subPos[dragState.sub]){
          subPos[dragState.sub].x=dragState.ox; subPos[dragState.sub].y=dragState.oy;
        }
        else if(dragState.sys&&sysPos[dragState.sys]){
          sysPos[dragState.sys].x=dragState.ox; sysPos[dragState.sys].y=dragState.oy;
        }
        else if(dragState.pkg&&pkgPos[dragState.pkg]){
          pkgPos[dragState.pkg].x=dragState.ox; pkgPos[dragState.pkg].y=dragState.oy;
        }
        dragState=null; render();
      }
      panState=null; wire=null;
      canvasWrap.classList.remove("panning");
      var a=touches[ids[0]], b=touches[ids[1]];
      pinch={d:Math.hypot(b.x-a.x,b.y-a.y)||1,
             cx:(a.x+b.x)/2, cy:(a.y+b.y)/2, k:view.k, tx:view.tx, ty:view.ty};
      markMoving();
    }
  },{passive:false});
  canvasWrap.addEventListener("pointermove",function(ev){
    if(ev.pointerType==="mouse"||!touches[ev.pointerId]) return;
    touches[ev.pointerId]={x:ev.clientX,y:ev.clientY};
    if(!pinch) return;
    var ids=Object.keys(touches);
    if(ids.length<2) return;
    ev.preventDefault();
    var a=touches[ids[0]], b=touches[ids[1]];
    var d=Math.hypot(b.x-a.x,b.y-a.y)||1;
    var cx=(a.x+b.x)/2, cy=(a.y+b.y)/2;
    var r=canvasWrap.getBoundingClientRect();
    var k2=clampZ(pinch.k*(d/pinch.d));
    // Zoom about the pinch centre AND follow it, so a two-finger drag pans at the same time --
    // which is what every map does and therefore what a thumb expects.
    var px=pinch.cx-r.left, py=pinch.cy-r.top;
    view.k=k2;
    view.tx=(px-(px-pinch.tx)*(k2/pinch.k))+(cx-pinch.cx);
    view.ty=(py-(py-pinch.ty)*(k2/pinch.k))+(cy-pinch.cy);
    applyView(); markMoving();
  },{passive:false});
  function endTouch(ev){
    if(ev.pointerType==="mouse") return;
    delete touches[ev.pointerId];
    if(Object.keys(touches).length<2) pinch=null;
  }
  canvasWrap.addEventListener("pointerup",endTouch);
  canvasWrap.addEventListener("pointercancel",endTouch);

  // ============================ wheel: pan, ctrl/pinch: zoom ============================
  // Trackpad semantics, and the only ones that work for both input devices: a two-finger
  // scroll arrives as a plain wheel event and pans; a pinch arrives as ctrlKey+wheel and
  // zooms at the pointer, which is also what Ctrl+wheel means on a mouse. preventDefault is
  // required for the ctrl case or the browser page-zooms instead.
  canvasWrap.addEventListener("wheel",function(ev){
    ev.preventDefault();
    closeNodeIssuePopIfOpen();
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
  // The layering below is parameterised over (ids, edges, boxOf) rather than reading
  // project.nodes/connections directly, so ONE implementation serves three callers: the whole
  // canvas, a framed subsystem's internals laid out on their own, and the read-only drill-in
  // canvas. A clustered layout is then just this algorithm applied twice -- once inside each
  // cluster, once over a parent graph in which each cluster is a single oversized node -- which
  // is far less to get wrong than a hierarchy-aware layering written from scratch.
  function layeredPositions(){
    var edges=[];
    project.connections.forEach(function(c){ edges.push([c.from.n,c.to.n]); });
    return layoutGraph(project.nodes.map(function(n){return n.id;}), edges, nodeBox);
  }
  function layoutGraph(ids,edgeList,boxOf){
    var idx={}; ids.forEach(function(id,i){idx[id]=i;});
    var succ={}, pred={}, degree={};
    ids.forEach(function(id){succ[id]=[];pred[id]=[];degree[id]=0;});
    edgeList.forEach(function(e){
      var a=e[0], b=e[1];
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
      row.forEach(function(id,i){ h+=boxOf(id).h+(i?GAPY:0); });
      heights.push(h);
    });
    var tallest=0; heights.forEach(function(h){ if(h>tallest) tallest=h; });
    layers.forEach(function(row,li){
      var wmax=0;
      row.forEach(function(id){ wmax=Math.max(wmax,boxOf(id).w); });
      var y=Y0+(tallest-heights[li])/2;
      row.forEach(function(id){
        var b=boxOf(id);
        pos[id]={x:Math.round(colX+(wmax-b.w)/2), y:Math.round(y)};
        y+=b.h+GAPY;
      });
      colX+=wmax+GAPX;
    });
    return pos;
  }

  // ---- clustered layout -------------------------------------------------------------------
  // Answers the "a complex subsystem will not fit in a box" problem without a new algorithm:
  //   1. lay out each FRAMED subsystem's internals alone, with layoutGraph;
  //   2. take the resulting bounding box and treat the whole cluster as ONE oversized node;
  //   3. lay out the parent graph -- own nodes, collapsed boxes, cluster super-nodes -- with the
  //      same layoutGraph, mapping every edge endpoint that lands inside a subsystem onto that
  //      subsystem's id;
  //   4. translate each cluster's internal positions by where its super-node landed.
  // A subsystem that will not fit still will not fit; that is what drill-in is for.
  var SUBID="sub::";
  function subUnitOf(nodeId){
    var n=nodeById(nodeId);
    return (n&&n.backing==="sub"&&n.subRef)?(SUBID+n.subRef):nodeId;
  }
  function clusterLayout(){
    var refs=liveSubRefs(), framed=[], collapsed=[];
    refs.forEach(function(r){ (subState(r)==="framed"?framed:collapsed).push(r); });

    // 1 + 2: each framed cluster laid out on its own
    var inner={}, innerBox={}, FPAD=22, FTOP=26;
    framed.forEach(function(ref){
      var members=subMembers(ref);
      var ids=members.map(function(n){return n.id;});
      var idset={}; ids.forEach(function(i){idset[i]=1;});
      var edges=[];
      project.connections.forEach(function(c){
        if(idset[c.from.n]&&idset[c.to.n]) edges.push([c.from.n,c.to.n]);
      });
      var pos=layoutGraph(ids,edges,nodeBox);
      var x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;
      ids.forEach(function(id){
        var b=nodeBox(id), pt=pos[id]||{x:0,y:0};
        x0=Math.min(x0,pt.x); y0=Math.min(y0,pt.y);
        x1=Math.max(x1,pt.x+b.w); y1=Math.max(y1,pt.y+b.h);
      });
      if(x0>x1){ x0=y0=0; x1=200; y1=80; }
      inner[ref]={pos:pos,ox:x0,oy:y0};
      innerBox[ref]={w:(x1-x0)+2*FPAD, h:(y1-y0)+FTOP+FPAD};
    });

    // 3: the parent graph
    var ids=[], seen={};
    project.nodes.forEach(function(n){
      var u=subUnitOf(n.id);
      if(!seen[u]){seen[u]=1;ids.push(u);}
    });
    var edges=[];
    project.connections.forEach(function(c){
      edges.push([subUnitOf(c.from.n),subUnitOf(c.to.n)]);
    });
    function boxOf(id){
      if(id.indexOf(SUBID)!==0) return nodeBox(id);
      var ref=id.slice(SUBID.length);
      if(innerBox[ref]) return innerBox[ref];
      var el=canvas.querySelector('.node.subbox[data-sub="'+STUDIO.cssEsc(ref)+'"]');
      if(el&&el.offsetWidth) return {w:el.offsetWidth,h:el.offsetHeight};
      return {w:220,h:70+22*subPorts(ref).length};
    }
    var top=layoutGraph(ids,edges,boxOf);

    // 4: own nodes take their position directly; a framed cluster's members are translated
    var out={}, boxes={};
    project.nodes.forEach(function(n){
      if(n.backing==="sub"&&n.subRef) return;
      var pt=top[n.id];
      if(pt) out[n.id]=pt;
    });
    collapsed.forEach(function(ref){ boxes[ref]=top[SUBID+ref]||{x:60,y:60}; });
    framed.forEach(function(ref){
      var at=top[SUBID+ref]||{x:60,y:60}, inf=inner[ref];
      if(!inf) return;
      Object.keys(inf.pos).forEach(function(id){
        out[id]={x:Math.round(at.x+FPAD+(inf.pos[id].x-inf.ox)),
                 y:Math.round(at.y+FTOP+(inf.pos[id].y-inf.oy))};
      });
      boxes[ref]=at;
    });
    return {nodes:out, boxes:boxes};
  }
  // Re-place only the collapsed BOXES, leaving every node where the author left it. Called when
  // a subsystem is collapsed or expanded, because that changes what occupies the canvas without
  // being an edit to the model.
  function relayoutSubs(){
    var r=clusterLayout();
    Object.keys(r.boxes).forEach(function(ref){ subPos[ref]=r.boxes[ref]; });
  }
  function autoLayout(){
    // clusterLayout() degenerates to layeredPositions() when nothing is framed: with no
    // cluster, every unit is a plain node and the parent pass IS the flat pass.
    var r=clusterLayout(), pos=r.nodes;
    // pushUndo() FIRST. snapshot() calls syncViewState(), which reads the LIVE subPos/pkgPos --
    // so anything overwritten before this line is what gets recorded as the "before" state, and
    // undo restores the new positions onto themselves. Writing subPos above this call made
    // Ctrl+Z a no-op for exactly the boxes Auto layout had just moved, which is the half of
    // "Auto layout ate my arrangement" that survived the first attempt at fixing it.
    pushUndo();          // node x/y live in project.json, so a layout is an undoable EDIT
    Object.keys(r.boxes).forEach(function(ref){ subPos[ref]=r.boxes[ref]; });
    project.nodes.forEach(function(n){
      var p=pos[n.id];
      if(p){ n.x=p.x; n.y=p.y; }
    });
    // The deps-view package column is derived from where the nodes just landed (depsColumnX);
    // dropping any remembered drags here is the same call autoLayout already makes for every
    // node position and every subsystem box -- "arrange everything" includes them too. Same for
    // the System level's origin containers, which placeOriginBoxes() then re-lays in a row.
    pkgPos={}; sysPos={};
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
    // a node parameter appears in BOTH files, like an interface: the exposure in the
    // .rossystem and the declaration in the .ros2, with different text in each
    param:[["before","block above the exposure (.rossystem)"],
           ["line","trailing on the exposure"],
           ["ros2Before","block above the parameter (.ros2)"],
           ["ros2Line","trailing on the parameter (.ros2)"]],
    sysparam:[["before","block above the parameter (.rossystem)"],
              ["line","trailing on the parameter line"],
              ["type","trailing on type:"],["value","trailing on value:"],
              ["ns","trailing on ns:"]],
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
    var n=selNode&&nodeById(selNode);
    var curKey=selEdge?("e:"+selEdge):(n?("n:"+n.id):null);
    if(curKey&&curKey!==lastSelForTab) inspTab="sel";  // a fresh selection always wins the tab back
    lastSelForTab=curKey;
    if(!curKey) inspTab="proj";        // nothing selected: Selected has nothing to show
    if(inspTab==="proj") return fillSystemInspector();
    if(selEdge){ return fillEdgeInspector(); }
    inspector.className="inspector";
    if(mode!=="edit"){ return fillReadonlyNode(n); }
    // A subSystems: node belongs to the REFERENCED file. Editing it here would be a lie: its
    // label, from: and interfaces are never written by this project, and deleting it would strip
    // the connections that name it while the subSystems: line still claimed to provide it.
    if(n.backing==="sub"){ return fillSubsystemNode(n); }
    var cat=n.backing==="cat";
    var headBody='<div class="fld"><label>label (rossystem instance)</label><input id="f_label" data-undo="1" value="'+esc(n.label)+'"></div>'
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
      +'<div class="fld"><label>from: (derived)</label><div class="derived">"'+esc(n.pkg)+'.'+esc(n.node)+'"</div></div>';
    var ih=sec("node/head","node: "+esc(n.label),headBody);
    var ifBody='';
    // A catalogue node arrives with its whole interface set unexposed on purpose (exposing all
    // of it would write dozens of unwired lines), so "reuse this node, expose the four ports I
    // actually need" was one checkbox per interface with no way to start from the other end.
    // Only worth the row when there is more than one to act on.
    if(n.ifaces.length>1)
      ifBody+='<div class="bulkrow">expose'
        +'<button class="minibtn" id="expAll" title="expose every interface below">all</button>'
        +'<button class="minibtn" id="expNone" title="unexpose every interface below — a connected one stays exposed, it has to">none</button>'
        +'<span class="bulkcount">'+n.ifaces.filter(function(x){return x.exposed||ifaceConnected(n,x);}).length
        +' of '+n.ifaces.length+' exposed</span></div>';
    for(var j=0;j<n.ifaces.length;j++){var f=n.ifaces[j];
      var conn=ifaceConnected(n,f);
      // Kind is editable only while nothing depends on it yet: changing it out from under a
      // real connection would need to unwire that connection first, so the badge stays a
      // locked, static label the moment one exists -- same as it always has for a catalogue
      // node's interfaces, whose kind belongs to the vendored file, not this one.
      var kindEditable=!cat&&!conn;
      ifBody+='<div class="iedit'+(f.orphan?" orphan":"")+'" data-i="'+f.id+'">'
        +(kindEditable
          // The badge is 2.2em, so the option TEXT has to stay the abbreviation or the collapsed
          // select shows an ambiguous fragment ("Service server" and "Service client" both clip
          // to "Ser"). The full word goes in title= instead -- on the select for the current
          // kind, and on each option for the list -- so the abbreviations stop being something
          // you have to already know.
          ?'<select class="kd '+f.kind+'" data-kind="'+f.id+'" title="interface kind — '+esc(KIND_LABEL[f.kind]||f.kind)+'">'
            +KINDS.map(function(k){return '<option value="'+k+'" title="'+esc(KIND_LABEL[k]||k)+'"'+(k===f.kind?" selected":"")+'>'+k+'</option>';}).join("")+'</select>'
          :'<span class="kd '+f.kind+'" title="'+KIND_LABEL[f.kind]+(conn?" — connected, kind is locked":"")+'">'+f.kind+'</span>')
        +'<span class="grow">'
        +(cat
          // a catalogue artifact's names are its own -- this mirrors the same restriction the
          // canvas's inline editor already enforces (wireInline: "n.backing!=='hand'" returns).
          ?'<span class="inm2">'+esc(f.name)+'</span><br><span class="ity2">'+esc(f.type||"—")+' · "'+esc(n.artifact||"")+'::'+esc(f.name)+'"</span>'
          :'<input class="iname" data-undo="1" data-iname="'+f.id+'" value="'+esc(f.name)+'" placeholder="interface name">'
            +'<input class="itype" data-undo="1" data-itype="'+f.id+'" value="'+esc(f.type||"")+'" placeholder="type e.g. std_msgs/msg/String" autocomplete="off">'
            +'<div class="typestate" id="its_'+f.id+'"></div>'
            +'<span class="ity2 deriv">"'+esc(n.artifact||"")+'::'+esc(f.name)+'"</span>')
        +'<span class="lblrow"><input class="ilbl" data-undo="1" data-lbl="'+f.id+'" value="'+esc(f.label||"")+'" placeholder="'+esc(f.name)+'" title="exposure label — the key written into the .rossystem. Blank derives it from the interface name.">'
        +'<label class="expchk" title="'+(conn?"connected — always exposed":"write this interface into the .rossystem even with nothing wired to it")+'">'
        +'<input type="checkbox" data-exp="'+f.id+'"'+((f.exposed||conn)?" checked":"")+(conn?" disabled":"")+'>expose</label>'
        +'<span class="qtog'+(qosCount(f)?" set":"")+'" data-qtog="'+f.id+'" title="quality of service — written into the .ros2, not the .rossystem">qos'+(qosCount(f)?"·"+qosCount(f):"")+'</span>'
        +cmtChip(f,"i:"+f.id)
        +'</span></span>'
        +'<span class="del" data-del="'+f.id+'">✕</span></div>'
        +qosPanel(f)+cmtPanel(f,"iface","i:"+f.id);
    }
    // A blank interface appears the instant this is clicked -- no separate form to fill in
    // first and then commit; the row IS the form, and it is the same row an already-existing
    // interface edits through. Nothing here writes a name or type until the author does.
    if(!cat) ifBody+='<button class="minibtn addifacebtn" id="addIface">+ interface</button>';
    ih+=sec("node/interfaces","interfaces",ifBody,String(n.ifaces.length));
    // Two halves, shown as two lines, because they are two grammar slots and treating them as
    // one is what deleted every override on round-trip:
    //   .ros2   `name: / type: T / default: D`      the artifact DECLARES it
    //   .rossys `- "label": "artifact::name" / value: V`  this system EXPOSES and OVERRIDES it
    var pmBody='';
    for(var p=0;p<n.params.length;p++){var pp=n.params[p];
      var pt=String(pp.ptype||"").trim()||inferPtype(pp.sysValue!=null?pp.sysValue:pp.value);
      pmBody+='<div class="iedit'+(pp.orphan?" orphan":"")+'" data-p="'+pp.id+'">'
        +(cat
          ?'<span class="kd" style="background:var(--k-param)" title="'+esc(pt)+'">'+esc(pt.slice(0,3))+'</span>'
          :'<select class="kd ptypesel" data-ptype="'+pp.id+'" style="background:var(--k-param)" title="parameter type">'
            +PTYPES.map(function(o){return '<option value="'+o+'"'+(o===pt?" selected":"")+'>'+o+'</option>';}).join("")+'</select>')
        +'<span class="grow">'
        +(cat
          // a catalogue artifact's declared parameters are its own -- same restriction as its
          // interfaces, above.
          ?'<span class="inm2">'+esc(pp.name)+'</span> <span class="ity2">'+esc(pt)+(pp.value==null||pp.value===""?"":" default "+esc(String(pp.value)))+' · "'+esc(n.artifact||"")+'::'+esc(pp.name)+'"</span>'
          :'<input class="iname" data-undo="1" data-pname="'+pp.id+'" value="'+esc(pp.name)+'" placeholder="parameter name">'
            +'<input class="itype" data-undo="1" data-pval="'+pp.id+'" value="'+esc(pp.value==null?"":String(pp.value))+'" placeholder="default value">'
            +'<span class="ity2 deriv">"'+esc(n.artifact||"")+'::'+esc(pp.name)+'"</span>')
        +(pp.orphan?'<br><span class="hint w">the backing artifact declares no such parameter — '
          +'the arrow target will not resolve. Fix the name, or drop the exposure.</span>':"")
        +'<span class="lblrow">'
        +'<input class="ilbl" data-undo="1" data-plbl="'+pp.id+'" value="'+esc(pp.label||"")+'" placeholder="'+esc(pp.name)+'" title="exposure label — the key written into the .rossystem. Blank derives it from the parameter name.">'
        +'<input class="ilbl" data-undo="1" data-pover="'+pp.id+'" value="'+esc(pp.sysValue==null?"":String(pp.sysValue))+'" placeholder="override value" title="written into this node’s parameters: block as `value:` — it overrides the artifact default for THIS instance and does not change the .ros2.">'
        +'<label class="expchk" title="write this parameter into the .rossystem as an exposure with an override value">'
        +'<input type="checkbox" data-pexp="'+pp.id+'"'+(pp.exposed?" checked":"")+'>expose</label>'
        +cmtChip(pp,"p:"+pp.id)
        +'</span></span>'
        +'<span class="del" data-delp="'+pp.id+'">✕</span></div>'+cmtPanel(pp,"param","p:"+pp.id);
    }
    if(!cat) pmBody+='<button class="minibtn addparambtn" id="addParam">+ parameter</button>';
    ih+=sec("node/parameters","parameters",pmBody,String(n.params.length));
    // the node's own comments, always open by default: a leading block is the one an author
    // reaches for most and hiding it behind a chip would keep it out of sight in exactly the
    // file it documents.
    var cmBody=cmtRows(n,"node","n:"+n.id)
      +'<div class="hint">re-emitted at these positions on generate; everything else is '
      +'reported by <code>init</code> and dropped.</div>';
    ih+=sec("node/comments","comments",cmBody);
    ih+='<button class="delnode" id="delNode">Delete node</button>';
    inspector.innerHTML=tabStrip()+ih;
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
    var h='';
    // A message TYPE is the shape of the data going over a wire (its field list); it is a
    // different thing from a topic/service/action NAME, which just labels one wire carrying
    // that shape. Most of the time nothing belongs here at all -- only define one when the
    // interface uses a type this project itself introduces, not an existing ROS 2 one.
    h+='<div class="hint">A type here is the DATA SHAPE a publisher/subscriber/service/action '
      +'sends — its field list, like a struct. Only add one for a type your own nodes '
      +'introduce; an existing ROS 2 type (<code>std_msgs/msg/String</code>, '
      +'<code>sensor_msgs/msg/Image</code>, …) needs no entry here — it already has a .ros of '
      +'its own, either in the vendored catalogue or in a companion file listed below.</div>';
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
      h+='<div class="pkgrow" data-typekey="'+esc(key)+'"><div class="pn">'+esc(key)+'</div>';
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
    return sec("sys/types","message types (.ros)",h,keys.length?String(keys.length):"");
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
    inspector.querySelectorAll("[data-subview]").forEach(function(x){x.onchange=function(){
      // NOT pushUndo(): a view is not an edit to the model. Undo restores what the file will
      // say, and folding a presentation toggle into that history would make Ctrl-Z unusable.
      setSubState(x.dataset.subview,x.value); relayoutSubs(); noteViewChange(); render(); fillSystemInspector();};});
    inspector.querySelectorAll("[data-subopen]").forEach(function(x){x.onclick=function(){
      openDrill(x.dataset.subopen);};});
    // ---- what a wrapped subsystem exposes ---------------------------------------------------
    // no pushUndo() here -- see setSubExposure/setSubExposureAll, which snapshot only once they
    // know the change is actually going to happen
    inspector.querySelectorAll("[data-subexp]").forEach(function(x){x.onchange=function(){
      setSubExposure(x.dataset.subexp,x.dataset.subnode,x.dataset.subiface,x.checked);
      render(); fillSystemInspector();};});
    inspector.querySelectorAll("[data-subexpall]").forEach(function(x){x.onclick=function(){
      setSubExposureAll(x.dataset.subexpall,true); render(); fillSystemInspector();};});
    inspector.querySelectorAll("[data-subexpnone]").forEach(function(x){x.onclick=function(){
      setSubExposureAll(x.dataset.subexpnone,false); render(); fillSystemInspector();};});
    // ---- system-level parameters ----------------------------------------------------------
    function sysParamById(id){
      var l=project.params||[];
      for(var i=0;i<l.length;i++) if(l[i].id===id) return l[i];
      return null;
    }
    inspector.querySelectorAll("[data-spt]").forEach(function(x){x.onchange=function(){
      var sp=sysParamById(x.dataset.spt); if(!sp) return;
      pushUndo(); sp.ptype=x.value; fillSystemInspector(); render(); runIssues();};});
    inspector.querySelectorAll("[data-spd]").forEach(function(x){x.oninput=function(){
      var sp=sysParamById(x.dataset.spd); if(!sp) return;
      pushUndo("spd:"+sp.id);
      // `default:` belongs to the ParameterType and `value:` to the Parameter -- two slots, so
      // they get two boxes and neither writes into the other.
      sp["default"]=x.value.trim()||null; render();};});
    inspector.querySelectorAll("[data-spv]").forEach(function(x){x.oninput=function(){
      var sp=sysParamById(x.dataset.spv); if(!sp) return;
      pushUndo("spv:"+sp.id); sp.value=x.value.trim()||null; render();};});
    inspector.querySelectorAll("[data-spns]").forEach(function(x){x.onchange=function(){
      var sp=sysParamById(x.dataset.spns); if(!sp) return;
      pushUndo(); sp.ns=x.value||null; render();};});
    inspector.querySelectorAll("[data-spdel]").forEach(function(x){x.onclick=function(){
      pushUndo();
      project.params=(project.params||[]).filter(function(q){return q.id!==x.dataset.spdel;});
      fillSystemInspector(); render(); runIssues();};});
    var spAdd=document.getElementById("sp_add");
    if(spAdd) spAdd.onclick=function(){
      var nm=document.getElementById("sp_name").value.trim(); if(!nm) return;
      var t=document.getElementById("sp_type").value;
      var raw=document.getElementById("sp_val").value.trim();
      pushUndo();
      project.params=project.params||[];
      project.params.push({id:nid(),name:nm,ptype:t,"default":null,
                           value:raw||null,ns:null});
      fillSystemInspector(); render(); runIssues();};
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
    var out='', h='';
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
    out+=sec("sys/system","system",h);

    // What a WRAPPED subsystem offers the rest of the world. For a reference seeded from a file
    // this is not ours to edit -- that file says what it exposes and we only read it -- but an
    // invented entry's `content` is this project's own, so the one defect the corpus is full of
    // (a reused system that declares nothing, so nothing can wire to it) is fixable right here
    // instead of only after a Commit, a re-open of the generated file, and a re-import.
    //
    // Writes BOTH sides on purpose: `content` is what gets emitted as the subsystem's own file,
    // and the outer shadow carries the pinned label the cross-boundary endpoint resolves through
    // (see wrapNodesInSubsystem). They have to agree or the endpoint names nothing.
    function subExposeEditor(s){
      if(!s.invented||!s.content) return "";
      var rows='', total=0, on=0;
      (s.content.nodes||[]).forEach(function(cn){
        var inner='';
        (cn.ifaces||[]).forEach(function(cf){
          total++; if(cf.exposed) on++;
          inner+='<label class="expline" title="'+esc(KIND_LABEL[cf.kind]||cf.kind)+'">'
            +'<input type="checkbox" data-subexp="'+esc(s.ref)+'" data-subnode="'+esc(cn.id)+'" data-subiface="'+esc(cf.id)+'"'
            +(cf.exposed?" checked":"")+'>'
            +'<span class="kd '+cf.kind+'">'+cf.kind+'</span>'
            +'<span class="expname">'+esc(cf.label||cf.name)+'</span></label>';
        });
        if(inner) rows+='<div class="expnode">'+esc(cn.label)+'</div>'+inner;
      });
      if(!total) return "";
      return '<div class="expose'+(on?"":" none")+'">'
        +'<div class="bulkrow">exposes'
        +'<button class="minibtn" data-subexpall="'+esc(s.ref)+'" title="expose every interface this subsystem has">all</button>'
        +'<button class="minibtn" data-subexpnone="'+esc(s.ref)+'" title="expose none — anything a connection already uses stays exposed, it has to">none</button>'
        +'<span class="bulkcount">'+on+' of '+total+'</span></div>'
        +(on?'':'<div class="hint w">Nothing is exposed, so the .rossystem written for this on '
          +'Commit would declare no interfaces and no other system could ever wire to it.</div>')
        +rows+'</div>';
    }
    // subSystems: is otherwise reference-only -- an entry seeded from a file cannot be typed in
    // here by name, because a reference that resolves to nothing exposes nothing connectable
    // (RM091) and the studio has no way to check a name the author types. The one exception is
    // an entry THIS session invented by wrapping a selection of nodes (right-click a
    // multi-selection -> "Wrap in subsystem"): the studio built it, so it already knows it
    // resolves -- see wrapNodesInSubsystem and the "invented" flag it sets. Their comments ARE
    // editable: on the TurtleBot 3 example the single entry carries the line naming exactly
    // which catalogue file it resolves to and which nodes it brings in.
    var subs=project.subSystems||[];
    if(subs.length){
      h='';
      subs.forEach(function(s,i){
        var got=project.nodes.filter(function(n){return n.backing==="sub"&&n.subRef===s.ref;});
        var g=s.graph||null, st=subState(s.ref);
        h+='<div class="pkgrow" data-subref="'+esc(s.ref)+'"><div class="pn">"'+esc(s.ref)+'"</div>'
          +'<div class="roinfo">'+esc(s.file?("assets/rosmodelscatalog/"+s.file)
            :(s.localFile||(s.invented?"(new -- written on Commit)":"(not in the vendored catalogue)")))
          +'<br>'+got.length+' node(s) reached: '+esc(got.map(function(n){return n.label;}).join(", ")||"none")
          +(g?('<br>'+(g.connections||[]).length+' internal connection(s)'):'<br>no graph captured &mdash; cannot be opened')
          +'</div>'
          // How this reference is DRAWN. Presentation only: project.view is excluded from the
          // fact tree and tests/studio_parity.js emits under every state to prove the bytes do
          // not move.
          +'<div class="prow3">'
          +'<label class="mini">view</label>'
          +'<select data-subview="'+esc(s.ref)+'">'
          +'<option value="collapsed"'+(st==="collapsed"?" selected":"")+'>collapsed &mdash; one box</option>'
          +'<option value="framed"'+(st==="framed"?" selected":"")+'>framed &mdash; internals in a frame</option>'
          +'</select>'
          +(g?'<button class="minibtn" data-subopen="'+esc(s.ref)+'">open &#8599;</button>':"")
          +'</div>'
          +(got.length?"":'<div class="hint w">this reference resolved to no nodes, so it has '
            +'nothing to draw &mdash; a subsystem exposes only what the referenced file&rsquo;s own '
            +'<code>interfaces:</code> blocks declare (checkIfInterfaceInSystem).</div>')
          +(edit?subExposeEditor(s):"")
          +(edit?cmtRows(s,"sub","sub:"+i):"")+'</div>';
      });
      out+=sec("sys/subsystems","subsystems (reused compositions)",h,String(subs.length));
    }

    // The system-level `parameters:` block: a peer of nodes: and connections:, not a node and
    // not a member of one. It had no UI at all because it had no slot in the project -- five of
    // them on ur_robot.rossystem were read, dropped, and reported as phantom NODES.
    var sps=project.params||[];
    h='';
    if(!sps.length) h+='<div class="roinfo">None. A system parameter is declared once for the '
      +'whole composition (<code>name: / type: T</code>), unlike a node parameter, which '
      +'exposes and overrides one parameter of one artifact.</div>';
    sps.forEach(function(sp,i){
      var t=String(sp.ptype||"").trim()||inferPtype((sp["default"]!=null&&sp["default"]!=="")?sp["default"]:sp.value);
      if(edit){
        h+='<div class="pkgrow"><div class="pn">'+esc(sp.name)+'</div>'
          +'<div class="prow3">'
          +'<select data-spt="'+sp.id+'" data-undo="1">'
          +PTYPES.map(function(o){return '<option'+(o===t?" selected":"")+'>'+o+'</option>';}).join("")
          +'</select>'
          +'<input data-spd="'+sp.id+'" data-undo="1" value="'+esc(sp["default"]==null?"":sp["default"])+'" placeholder="default (of the type)">'
          +'<input data-spv="'+sp.id+'" data-undo="1" value="'+esc(sp.value==null?"":sp.value)+'" placeholder="value (of the parameter)">'
          +'<span class="del" data-spdel="'+sp.id+'">✕</span></div>'
          // `ns:` is a Namespace KEYWORD, not free text -- offering a text box here would invite
          // exactly the quoted string the real server rejects.
          +'<div class="prow3"><label class="mini">ns</label><select data-spns="'+sp.id+'" data-undo="1">'
          +["","GlobalNamespace","RelativeNamespace","PrivateNamespace"].map(function(o){
              return '<option value="'+o+'"'+((sp.ns||"")===o?" selected":"")+'>'+(o||"(none)")+'</option>';}).join("")
          +'</select><span class="hint">one of three keywords (Basics.xtext:13-32); RM044 notes zero corpus use</span></div>'
          +cmtRows(sp,"sysparam","sp:"+sp.id)+'</div>';
      }else{
        h+='<div class="pkgrow"><div class="pn">'+esc(sp.name)+'</div><div class="roinfo">'
          +'type: '+esc(t)
          +(sp.ns?('  · ns: '+esc(sp.ns)):"")
          +(sp["default"]!=null&&sp["default"]!==""?('<br>default: '+esc(String(sp["default"]))):"")
          +(sp.value!=null&&sp.value!==""?('<br>value: '+esc(String(sp.value))):"")
          +'</div></div>';
      }
    });
    if(edit) h+='<div class="addform"><input id="sp_name" placeholder="parameter name">'
      +'<select id="sp_type">'+PTYPES.map(function(o){return '<option>'+o+'</option>';}).join("")+'</select>'
      +'<input id="sp_val" placeholder="value (optional)">'
      +'<button class="minibtn" id="sp_add">+ add system parameter</button></div>';
    out+=sec("sys/params","system parameters",h,String(sps.length));

    h='';
    if(!pkgs.length) h+='<div class="roinfo">No hand-authored package yet — catalogue nodes '
      +'reference a vendored .ros2 and generate none.</div>';
    // New to ROS 2, this field is the one most likely to sit empty with no clue why: it has
    // no default, nothing derives it, and nothing in the model needs it to be filled in.
    else h+='<div class="hint">fromGitRepo is a note for later, not something this tool reads '
      +'back: the URL of the real repository this package\'s ROS 2 source code lives in (e.g. '
      +'<code>https://github.com/ros2/examples</code>), so a person opening the generated '
      +'.ros2 knows where to find the actual code behind it. It has no effect on validation or '
      +'on how the system runs — leave it blank if you don\'t know it or this package has no '
      +'real source yet.</div>';
    pkgs.forEach(function(p){
      // the package entry is derived from the nodes, so it may not exist yet -- and the .ros2
      // file header has nowhere else to hang.
      var entry=project.packages[p]=(project.packages[p]||{});
      var git=entry.fromGitRepo||"";
      h+='<div class="pkgrow"><div class="pn">'+esc(p)+'.ros2</div>'
        +(edit?'<input data-git="'+esc(p)+'" data-undo="1" value="'+esc(git)
               +'" placeholder="not set — e.g. https://github.com/org/repo">'
               +cmtRows(entry,"pkg","pkg:"+p)
              :'<div class="derived">'+esc(git||"(not set — optional, see hint above)")+'</div>')
        +'</div>';
    });
    out+=sec("sys/packages","packages (.ros2)",h,pkgs.length?String(pkgs.length):"")+typesSection(edit)
      +'<div class="hint" style="margin-top:.6rem">Select a node to '
      +(edit?'edit it, or add one from the rail':'inspect it')+'.</div>';
    inspector.innerHTML=tabStrip()+out;

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
    inspector.innerHTML=tabStrip()+sec("sub/head","node: "+esc(n.label),
        '<div class="roinfo">via subSystems: "'+esc(n.subRef||"")+'"'
        +((sub&&sub.file)?'<br>'+esc("assets/rosmodelscatalog/"+sub.file):'')
        +'<br>from: "'+esc(n.pkg)+'.'+esc(n.node)+'"</div>'
        +'<div class="hint">read-only: this node is declared in the referenced system, not here. '
        +'Edit it there, or drop the subSystems: entry and declare it under this file\'s own '
        +'nodes: instead — declaring it in both is RM090.</div>')
      +sec("sub/interfaces","interfaces (from the referenced system)",
        '<pre class="roinfo" style="white-space:pre-wrap">'+esc(rows)+'</pre>'
        +'<div class="hint">a connections: endpoint spells these names verbatim; they are not '
        +'re-labelled here.</div>',String(n.ifaces.length));
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
    inspector.innerHTML=tabStrip()+sec("ro/head","node: "+esc(n.label),
        '<div class="roinfo">from: "'+esc(n.pkg)+'.'+esc(n.node)+'"'
        +((n.namespace&&String(n.namespace).trim())?'<br>namespace: '+esc(n.namespace):'')
        +'<br>backing: '+n.backing+'<br>artifact: '+esc(n.artifact||"")+'</div>')
      +sec("ro/interfaces","interfaces",'<pre class="roinfo" style="white-space:pre-wrap">'+esc(rows)+'</pre>',String(n.ifaces.length))
      +sec("ro/parameters","parameters",'<pre class="roinfo" style="white-space:pre-wrap">'+esc(pr)+'</pre>',String(n.params.length))
      +(cm?sec("ro/comments","comments",'<pre class="roinfo" style="white-space:pre-wrap">'+esc(cm)+'</pre>'):'')
      +((DIAG[n.id]&&DIAG[n.id].length)?sec("ro/diagnostics","diagnostics",
          '<pre class="roinfo" style="white-space:pre-wrap;color:var(--dead)">'+esc(DIAG[n.id].join("\n"))+'</pre>',
          String(DIAG[n.id].length)):'');
  }
  function fillEdgeInspector(){
    var c=null; for(var i=0;i<project.connections.length;i++)if(project.connections[i].id===selEdge)c=project.connections[i];
    if(!c){selEdge=null;return fillInspector();}
    var a=ifaceById(nodeById(c.from.n),c.from.i), bb=ifaceById(nodeById(c.to.n),c.to.i);
    if(!a||!bb){selEdge=null;return fillInspector();}
    var pair=PAIR_TOPIC[a.kind]?"Topic (one-way)":"Service/Action (request ⇄ response)";
    inspector.className="inspector";
    var h=sec("conn/head","connection",
      '<div class="fld"><label>kind</label><div class="derived">'+pair+'</div></div>'
      +'<div class="fld"><label>from (server/publisher)</label><div class="derived">'+esc(nodeById(c.from.n).label)+' · '+esc(a.name)+' ('+a.kind+')</div></div>'
      +'<div class="fld"><label>to (client/subscriber)</label><div class="derived">'+esc(nodeById(c.to.n).label)+' · '+esc(bb.name)+' ('+bb.kind+')</div></div>');
    // a connection has no name of its own, so its comment is keyed by the LABEL PAIR both here
    // and in emit_rossystem -- which is why it has to be editable from the edge, not the node.
    if(mode==="edit") h+=sec("conn/comments","comments",cmtRows(c,"conn","c:"+c.id))
      +'<button class="delnode" id="delEdge">Delete connection</button>';
    inspector.innerHTML=tabStrip()+h;
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
    (function wireBulkExpose(){
      function setAll(v){
        pushUndo();
        // "none" cannot unexpose a WIRED interface: a connections: endpoint has to name
        // something the file declares, so the emitter exposes it regardless. Skipping it here
        // keeps the checkbox state and the emitted file telling the same story.
        (n.ifaces||[]).forEach(function(f){ if(v||!ifaceConnected(n,f)) f.exposed=v; });
        render(); fillInspector();
      }
      var a=document.getElementById("expAll"), z=document.getElementById("expNone");
      if(a) a.onclick=function(){ setAll(true); };
      if(z) z.onclick=function(){ setAll(false); };
    })();
    // The .rossystem half of a parameter. Editing the label or the override does NOT touch the
    // artifact's declared type or default -- those are the .ros2 half, edited below through
    // data-pname/data-pval/data-ptype directly on the row (for a hand-backed node).
    function paramById(id){
      for(var i=0;i<(n.params||[]).length;i++) if(n.params[i].id===id) return n.params[i];
      return null;
    }
    inspector.querySelectorAll("[data-plbl]").forEach(function(x){x.oninput=function(){
      var pp=paramById(x.dataset.plbl); if(!pp) return;
      pushUndo("plbl:"+pp.id);
      pp.label=x.value.trim()||null; render();};});
    inspector.querySelectorAll("[data-pover]").forEach(function(x){x.oninput=function(){
      var pp=paramById(x.dataset.pover); if(!pp) return;
      pushUndo("pover:"+pp.id);
      var v=x.value.trim();
      pp.sysValue=v||null;
      // an override with nothing exposing it would never be written, so typing one turns the
      // exposure on rather than silently discarding the edit
      if(v&&!pp.exposed){ pp.exposed=true; fillInspector(); }
      render();};});
    inspector.querySelectorAll("[data-pexp]").forEach(function(x){x.onchange=function(){
      var pp=paramById(x.dataset.pexp); if(!pp) return;
      pushUndo();
      pp.exposed=x.checked;
      // RosParameter has a MANDATORY `value:` (RosSystem.xtext:78-82), so an exposure with no
      // override cannot be emitted. Seed it from the artifact default rather than writing an
      // incomplete block.
      if(pp.exposed&&(pp.sysValue==null||pp.sysValue==="")) pp.sysValue=pp.value;
      render();fillInspector();};});
    // ---- interface name/type/kind, edited directly on the row (hand-authored nodes only) ----
    inspector.querySelectorAll("[data-iname]").forEach(function(x){x.oninput=function(){
      var f=ifaceById(n,x.dataset.iname); if(!f) return;
      pushUndo("iname:"+f.id);
      f.name=x.value;    // blank mid-edit is fine -- the instant checks flag it, same as any
      render();          // other required field; NOT fillInspector() here, or the caret is lost
    };});
    inspector.querySelectorAll("[data-itype]").forEach(function(x){
      wireTypeahead(x,TYPES);
      var tsEl=document.getElementById("its_"+x.dataset.itype);
      function updateTypeHint(){
        var v=x.value.trim(), pk=v.split("/")[0];
        if(!tsEl) return;
        if(!v){tsEl.textContent="";tsEl.className="typestate";}
        else if(TYPESET[v]){tsEl.textContent="✓ resolves in the type catalogue";tsEl.className="typestate ok";}
        else if(pk===n.pkg){tsEl.textContent="self-referencing — a companion .ros will be generated";tsEl.className="typestate warn";}
        else {tsEl.textContent="not in catalogue — you will need to define or vendor this type";tsEl.className="typestate warn";}
      }
      updateTypeHint();
      x.addEventListener("input",function(){
        var f=ifaceById(n,x.dataset.itype); if(!f) return;
        pushUndo("itype:"+f.id);
        f.type=x.value.trim()||null;
        updateTypeHint();
        render();
      });
      // Both of these wait for a COMMITTED value rather than firing per keystroke: a partial
      // string mid-type is browsing, not a choice. recordRecentType only keeps what resolves in
      // TYPESET anyway, but propagation writes to ANOTHER node -- from the first character
      // typed, if it ran on input, and never again after (see propagateInterfaceType).
      x.addEventListener("blur",function(){
        var v=x.value.trim();
        recordRecentType(v);
        var f=ifaceById(n,x.dataset.itype); if(!f) return;
        var filled=propagateInterfaceType(n,f);
        if(filled.length){ announceTypeFill(filled,v); render(); fillInspector(); }
      });
    });
    inspector.querySelectorAll("[data-kind]").forEach(function(x){x.onchange=function(){
      var f=ifaceById(n,x.dataset.kind); if(!f) return;
      pushUndo();
      f.kind=x.value;
      addKind=x.value;    // remembered as the default kind for the NEXT "+ interface"
      render();fillInspector();
    };});
    var addIface=document.getElementById("addIface");
    if(addIface) addIface.onclick=function(){
      pushUndo();
      var newId=nid();
      // blank on purpose: the row IS the form now, so there is nothing to validate here --
      // the instant checks flag a nameless/typeless interface exactly like they would if it
      // had been typed in and then cleared.
      n.ifaces.push({id:newId,name:"",kind:addKind||"pub",type:null,qos:null,label:null,exposed:true});
      render();fillInspector();
      var el=inspector.querySelector('[data-iname="'+newId+'"]');
      if(el) el.focus();
    };
    // ---- parameter name/default/type, edited directly on the row (hand-authored nodes only) ----
    inspector.querySelectorAll("[data-pname]").forEach(function(x){x.oninput=function(){
      var pp=paramById(x.dataset.pname); if(!pp) return;
      pushUndo("pname:"+pp.id);
      pp.name=x.value; render();
    };});
    inspector.querySelectorAll("[data-pval]").forEach(function(x){
      x.oninput=function(){
        var pp=paramById(x.dataset.pval); if(!pp) return;
        pushUndo("pval:"+pp.id);
        pp.value=x.value;    // raw while typing -- coercing every keystroke would fight "0.1"
        render();            // as it's being typed, one character at a time
      };
      x.addEventListener("blur",function(){
        var pp=paramById(x.dataset.pval); if(!pp) return;
        var t=String(pp.ptype||"").trim()||inferPtype(pp.value);
        var coerced=coerceParamValue(t,String(pp.value==null?"":pp.value).trim());
        if(coerced!==pp.value){ pushUndo(); pp.value=coerced; x.value=coerced; render(); }
      });
    });
    inspector.querySelectorAll("[data-ptype]").forEach(function(x){x.onchange=function(){
      var pp=paramById(x.dataset.ptype); if(!pp) return;
      pushUndo();
      pp.ptype=x.value;
      pp.value=coerceParamValue(x.value,String(pp.value==null?"":pp.value).trim());
      render();fillInspector();
    };});
    var addParam=document.getElementById("addParam");
    if(addParam) addParam.onclick=function(){
      pushUndo();
      var newId=nid();
      n.params.push({id:newId,name:"",ptype:"String",value:"",label:null,exposed:false,sysValue:null});
      render();fillInspector();
      var el=inspector.querySelector('[data-pname="'+newId+'"]');
      if(el) el.focus();
    };
    wireComments();
    var del=document.getElementById("delNode");
    if(del) del.onclick=function(){
      pushUndo();
      project.connections=project.connections.filter(function(c){return c.from.n!==n.id&&c.to.n!==n.id;});
      project.nodes=project.nodes.filter(function(x){return x.id!==n.id;});
      selNode=null;multiSel=Object.create(null);render();fillInspector();};
  }

  // ============================ rail ============================
  // A fresh card can run 200-280px wide and taller once interfaces are added, so jittering a
  // new node's position inside a window SMALLER than that used to mean sequential adds
  // routinely landed overlapping an existing card closely enough that a header control on the
  // one drawn on top -- a title, a badge, the warning icon -- silently ate a click or a
  // wire-drag meant for a port underneath it.
  //
  // A FIXED grid keyed off project.nodes.length looked like a fix but wasn't one: delete any
  // node but the last and the next add reuses the freed slot's neighbour exactly; a project
  // SEEDED from a file arrives with real positions typically clustered near the origin, so slot
  // 0 is already taken; a card the user dragged by hand is invisible to an index-keyed grid
  // either way. So this searches real geometry instead -- first slot, scanning outward, whose
  // rectangle doesn't intersect any node CURRENTLY on the canvas (measured off the rendered
  // card when one exists, so an oversized catalogue node with a dozen interfaces is accounted
  // for, not just the default footprint).
  function nextSpawnPos(){
    var DW=240, DH=130, GAP=24;
    var existing=project.nodes.map(function(n){
      var el=canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(n.id)+'"]');
      return {x:n.x, y:n.y, w:(el&&el.offsetWidth)||DW, h:(el&&el.offsetHeight)||DH};
    });
    function overlapsAny(x,y,w,h){
      return existing.some(function(e){
        return x<e.x+e.w+GAP && x+w+GAP>e.x && y<e.y+e.h+GAP && y+h+GAP>e.y;
      });
    }
    for(var row=0; row<60; row++){
      for(var col=0; col<10; col++){
        var x=80+col*(DW+GAP), y=80+row*(DH+GAP);
        if(!overlapsAny(x,y,DW,DH)) return {x:x+Math.random()*10, y:y+Math.random()*10};
      }
    }
    // 600 slots exhausted -- a pathological project; land somewhere rather than throw.
    return {x:80+Math.random()*200, y:80+existing.length*40+Math.random()*80};
  }
  document.getElementById("addNode").onclick=function(){
    pushUndo();
    var p=nextSpawnPos();
    var n={id:nid(),label:"new_node",backing:"hand",pkg:"new_package",node:"new_node",artifact:"new_node",
      catalogueFile:null,namespace:null,x:p.x,y:p.y,ifaces:[],params:[]};
    project.nodes.push(n); selNode=n.id; selEdge=null; multiSel=Object.create(null); render(); fillInspector();
    // otherwise a slot far from the current pan/zoom reads as "I clicked add and nothing
    // happened" -- centreOn brings the new card into view regardless of where it landed.
    centreOn(n.id);
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
    var p=nextSpawnPos();
    var n={id:nid(),label:node,backing:"cat",pkg:pkg,node:node,artifact:e.artifact||node,catalogueFile:e.file||null,
      namespace:null,x:p.x,y:p.y,
      // a catalogue node arrives with its FULL interface set; exposing all of it would write
      // dozens of unwired lines, so these start unexposed and surface as you connect them.
      ifaces:Object.keys(e.interfaces||{}).map(function(nm){return {id:nid(),name:nm,kind:e.interfaces[nm],type:tmap[nm]||null,qos:null,label:null,exposed:false};}),params:[]};
    project.nodes.push(n); selNode=n.id; catScrim.classList.remove("on"); multiSel=Object.create(null); render(); fillInspector();
    centreOn(n.id);
  }
  [].slice.call(document.querySelectorAll("[data-close]")).forEach(function(b){b.onclick=function(e){e.target.closest(".scrim").classList.remove("on");};});
  // #drawerScrim is deliberately NOT in here. It is the only scrim not driven by its own `on`
  // class -- the mobile drawers are opened and closed by body.drawer-l/drawer-r -- so the
  // generic handler would be a no-op on it. Worse, this loop runs AFTER wireDrawers assigned
  // `sc.onclick=closeDrawers` and, being an assignment rather than a listener, silently replaced
  // it: tapping the dimmed backdrop to dismiss a drawer, which is the gesture everyone tries
  // first, did nothing at all. The ✕ and Escape still worked, so it read as a quirk rather than
  // a bug and survived that way.
  [].slice.call(document.querySelectorAll(".scrim:not([data-locked]):not(#drawerScrim)"))
    .forEach(function(s){s.onclick=function(e){if(e.target===s)s.classList.remove("on");};});

  var KCOL={pub:"--k-pub",sub:"--k-sub",ss:"--k-ss",sc:"--k-sc",as:"--k-as",ac:"--k-ac"};
  (function(){
    var fb=document.getElementById("filterBox");
    KINDS.forEach(function(k){
      var l=document.createElement("label");
      l.innerHTML='<input type="checkbox" '+(kindShown[k]?"checked ":"")+'data-k="'+k+'"><span class="sw" style="background:var('+KCOL[k]+')"></span>'+k;
      l.querySelector("input").onchange=function(e){kindShown[k]=e.target.checked;saveHiddenKinds();noteViewChange();render();};
      fb.appendChild(l);
    });
    // `param` toggles a BAND, not ports: it hides no edge, because a parameter is not an
    // interaction. It is here because a node's parameters are often the bulkiest thing on its
    // card and reading the wiring is easier without them.
    var pl=document.createElement("label");
    pl.innerHTML='<input type="checkbox" '+(paramShown?"checked ":"")+'data-k="param"><span class="sw" style="background:var(--k-param)"></span>param';
    pl.querySelector("input").onchange=function(e){paramShown=e.target.checked;saveHiddenKinds();noteViewChange();render();};
    fb.appendChild(pl);
    updateFilterIndicator();
    var lg=document.getElementById("legend");
    [["pub → sub","Topic — one-way ▶"],["ss → sc","Service — request ⇄ response"],["as → ac","Action — request ⇄ response"]]
      .forEach(function(pair){var d=document.createElement("div");d.innerHTML='<b style="font-family:var(--mono);font-size:.66rem">'+pair[0]+'</b> — '+pair[1];lg.appendChild(d);});
    // Multi-select and everything gated behind it (group drag, "wrap in subsystem") were
    // reachable ONLY by knowing to hold a modifier -- nothing on screen said so, which makes a
    // feature that exists indistinguishable from one that does not.
    var g=document.createElement("div");
    g.className="editonly";
    g.style.cssText="margin-top:.35rem;padding-top:.35rem;border-top:1px solid var(--rule-soft)";
    g.innerHTML='<b style="font-family:var(--mono);font-size:.66rem">Ctrl/⌘+click</b> — select several nodes'
      +'<br><span style="color:var(--ink-3)">then drag to move them together, or right-click to wrap them in a subsystem</span>';
    lg.appendChild(g);
  })();

  // ============================ issues ============================
  // Transient "you clicked this" pointer -- distinct from .sel (the current selection, accent)
  // and .hasdiag (persistent, the server's own verdict from a prior Commit).
  function flashEl(el,sev){
    if(!el) return;
    el.classList.remove("flash","e"); void el.offsetWidth;
    el.classList.add("flash"); if(sev==="e") el.classList.add("e");
    setTimeout(function(){ el.classList.remove("flash","e"); },1400);
  }
  function focusField(id){
    var el=document.getElementById(id); if(!el) return false;
    el.scrollIntoView({block:"nearest"}); if(el.focus) el.focus(); if(el.select) el.select();
    return true;
  }
  // Routes a clicked issue to its source: selects/centres the node or connection it names,
  // flashes it, and -- in Edit mode, where the field actually exists -- focuses the exact
  // input. View mode still selects and centres; a click on a diagnostic never changes the
  // app's mode on its own.
  // STUDIO.cssEsc wraps CSS.escape(), which escapes for a bare IDENTIFIER (#foo, .bar) --
  // every other cssEsc call site in this file feeds it a plain alphanumeric id, so that never
  // showed. it.ftag/it.typekey are message-type KEYS ("pkg/msg/Name") and DO contain "/", which
  // CSS.escape() backslash-escapes character-by-character -- wrong inside an already-quoted
  // attribute value, where only the quote and backslash themselves need escaping. Selectors
  // built the cssEsc way against a slash-bearing string silently match nothing.
  function attrEsc(s){ return String(s).replace(/["\\]/g,"\\$&"); }
  function gotoIssue(it){
    closeDrawers();
    // Every routing target lives in the OUTER project, never inside a drilled-in subsystem's
    // own graph (that view is read-only and foreign anyway) -- so leave drill mode first, or
    // centreOn/flashEl below silently find nothing on a canvas that isn't drawing this project.
    if(drillRef){ drillRef=null; }
    if(it.action==="addnode"){ var ab=document.getElementById("addNode"); if(ab) ab.click(); return; }
    if(it.conn){
      var c=null; for(var i=0;i<project.connections.length;i++) if(project.connections[i].id===it.conn) c=project.connections[i];
      if(!c) return;
      selEdge=it.conn; selNode=null; multiSel=Object.create(null); render(); fillInspector();
      centreOn(c.from.n); flashEl(canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(c.from.n)+'"]'),it.sev);
      revealInspector(); return;
    }
    if(it.node){
      selNode=it.node; selEdge=null; multiSel=Object.create(null); render(); fillInspector();
      centreOn(it.node); flashEl(canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(it.node)+'"]'),it.sev);
      revealInspector();
      if(mode==="edit"){
        if(it.field){ focusField(it.field); return; }
        if(it.qos&&it.iface){ qosOpen[it.iface]=true; fillInspector();
          var qel=inspector.querySelector('[data-qi="'+STUDIO.cssEsc(it.iface)+'"][data-qk="'+it.qos+'"]');
          if(qel){ qel.scrollIntoView({block:"nearest"}); qel.focus(); } return; }
        if(it.iface) flashEl(inspector.querySelector('.iedit[data-i="'+STUDIO.cssEsc(it.iface)+'"]'),it.sev);
        else if(it.param) flashEl(inspector.querySelector('.iedit[data-p="'+STUDIO.cssEsc(it.param)+'"]'),it.sev);
      }
      return;
    }
    if(it.sub){
      // the subsystems panel is where both the diagnosis and (for a wrapped one) the fix live
      selNode=null; selEdge=null; selSub=it.sub; inspTab="proj"; multiSel=Object.create(null);
      expandSec("sys/subsystems");
      render(); fillInspector(); revealInspector();
      flashEl(inspector.querySelector('.pkgrow[data-subref="'+attrEsc(it.sub)+'"]'),it.sev);
      flashEl(canvas.querySelector('.node.subbox[data-sub="'+attrEsc(it.sub)+'"]'),it.sev);
      return;
    }
    if(it.sys){
      selNode=null; selEdge=null; inspTab="proj"; multiSel=Object.create(null); render(); fillInspector(); revealInspector();
      if(it.field){ focusField(it.field); return; }
      if(it.ftag){ expandSec("sys/types");
        var fel=inspector.querySelector('[data-ft="'+attrEsc(it.ftag)+'"]');
        if(fel){ fel.scrollIntoView({block:"nearest"}); fel.focus(); } return; }
      if(it.typekey){ expandSec("sys/types");
        flashEl(inspector.querySelector('.pkgrow[data-typekey="'+attrEsc(it.typekey)+'"]'),it.sev); }
    }
  }
  // Issues that repeat identically shaped across many nodes/interfaces (a namespace warning on
  // 14 nodes, say) share a groupKey and collapse to one row -- the flat per-node list used to
  // bury a real error under a wall of RM044 warnings. Ungrouped issues (groupKey absent) pass
  // through unchanged. Grouping is scoped by severity too: an "e" and a "w" never merge.
  function groupIssues(list){
    var buckets={}, order=[], loose=[];
    list.forEach(function(it){
      if(!it.groupKey){ loose.push(it); return; }
      var k=it.sev+":"+it.groupKey;
      if(!buckets[k]){ buckets[k]=[]; order.push(k); }
      buckets[k].push(it);
    });
    var out=[];
    order.forEach(function(k){
      var m=buckets[k];
      if(m.length===1){ out.push(m[0]); return; }
      out.push({sev:m[0].sev,code:m[0].code,msg:(m[0].groupLabel||m[0].msg)+" — "+m.length+" "+(m[0].groupUnit||"nodes"),group:m,groupKey:k});
    });
    return out.concat(loose);
  }
  var lastIssues=[], issuesExpanded=false, nodeIssueIndex={}, subIssueIndex={};
  // Every issue that names a node, keyed by that node's id -- read by renderNode() to paint the
  // per-node warning icon. Rebuilt fresh on every runIssues() call (which now runs at the TOP
  // of render(), before any node card exists) and node cards are always removed and rebuilt
  // from scratch, never patched -- so there is no code path where an icon can outlive the
  // problem it names, or fail to appear for one that just occurred.
  function indexIssuesByNode(list){
    var idx={};
    list.forEach(function(it){
      if(it.node) (idx[it.node]=idx[it.node]||[]).push(it);
      // a connection issue names no single node (its target for click-routing stays `conn`,
      // resolved via gotoIssue) but names TWO -- both endpoints should carry the icon, not
      // neither, since a type mismatch is exactly as much each node's problem as the wire's.
      if(it.nodes) it.nodes.forEach(function(nid2){ if(nid2) (idx[nid2]=idx[nid2]||[]).push(it); });
    });
    return idx;
  }
  // Same idea keyed by subSystems: ref, so a collapsed box can say on its own face that the
  // thing it stands for offers nothing -- an empty box and an unwired one look identical.
  function indexIssuesBySub(list){
    var idx=Object.create(null);
    list.forEach(function(it){ if(it.sub) (idx[it.sub]=idx[it.sub]||[]).push(it); });
    return idx;
  }
  function runIssues(){
    var issues=[];
    function pushIssue(sev,msg,opts){ var it={sev:sev,msg:msg}; if(opts) for(var k in opts) it[k]=opts[k]; issues.push(it); }
    // Object.create(null): these are keyed by user-supplied strings (a label, an interface
    // name), and a node genuinely named "constructor" or "__proto__" would otherwise collide
    // with Object.prototype and misreport as already-seen.
    var labelIds=Object.create(null);
    for(var i=0;i<project.nodes.length;i++){var n=project.nodes[i];
      (labelIds[n.label]=labelIds[n.label]||[]).push(n.id);
      if(n.backing==="hand" && /[A-Z]/.test(n.pkg))
        pushIssue("e",n.label+': package "'+n.pkg+'" has uppercase',{code:"RM010",node:n.id,field:"f_pkg",groupKey:"rm010",groupLabel:"package name has uppercase",
          fix:"ROS 2 package names must be lowercase — rename the package field."});
      // RM044: legal and the server accepts it, but 0 of 52 corpus files use it, so the linter
      // warns. Surface it here rather than letting Commit be the first mention.
      if(n.namespace&&String(n.namespace).trim())
        pushIssue("w",n.label+': namespace "'+n.namespace+'" has zero corpus support',{code:"RM044",node:n.id,field:"f_ns",groupKey:"rm044",groupLabel:"namespace has zero corpus support",
          fix:"Legal — the 3.1.0 server accepts it. Leave it if you need multi-robot scoping, or clear the field to silence the warning."});
      var seen=Object.create(null);
      for(var j=0;j<n.ifaces.length;j++){var f=n.ifaces[j];
        if(seen[f.name]) pushIssue("w",n.label+': duplicate interface name "'+f.name+'"',{node:n.id,iface:f.id,groupKey:"dupiface",groupLabel:"duplicate interface name",groupUnit:"interfaces",
          fix:"Rename one of the two — the emitted file can't tell interfaces apart by name."});
        seen[f.name]=1;
        // B2: a hand-authored interface with no type blocks generation (server can't resolve it)
        if(n.backing==="hand" && (!f.type||String(f.type).trim()===""))
          pushIssue("e",n.label+': interface "'+f.name+'" ('+f.kind+') has no message type',{node:n.id,iface:f.id,groupKey:"notype",groupLabel:"interface has no message type",groupUnit:"interfaces",
            fix:"Set a message type, e.g. std_msgs/msg/String, or reference a type you've defined under Message types (.ros)."});
        // RM035 on a QoS duration is a hard ERROR that would stop `generate` after the files
        // are already written; the panel has to say so while it is still editable.
        if(f.qos) (QOS.durations||[]).forEach(function(k){
          // qosDurationProblem fires on two DIFFERENT problems (not a bare integer, or one that
          // overflows int32) and already returns the exactly-right sentence for whichever one --
          // reuse it instead of a generic line that's simply wrong for the non-numeric case.
          var qp=qosDurationProblem(f.qos[k]);
          if(qp)
            pushIssue("e",n.label+': qos '+k+' "'+f.qos[k]+'" is rejected by CheckDuration',{code:"RM035",node:n.id,iface:f.id,qos:k,groupKey:"rm035",groupLabel:"qos duration rejected by CheckDuration",groupUnit:"interfaces",
              fix:qp});
        });
      }
      if(DIAG[n.id]) DIAG[n.id].forEach(function(m){pushIssue("e",n.label+": "+m,{node:n.id,groupKey:"diag",groupLabel:"flagged by the server",
        fix:"Reported by the real language server on the last Commit. Fix it here, then Commit again to re-check."});});
    }
    // one issue per colliding node, not one for the first only -- the user who just renamed
    // node B into a collision needs to see it on B, not discover it's actually pointing at A.
    for(var l in labelIds) if(labelIds[l].length>1) labelIds[l].forEach(function(nid2){
      pushIssue("e",'duplicate node label "'+l+'"',{code:"RM009",node:nid2,field:"f_label",groupKey:"rm009dup",groupLabel:"duplicate node label",
        fix:"Rename this node, or the other one sharing the label — instance labels must be unique within one system."});
    });
    // ---- subSystems: what a reused composition actually offers ---------------------------
    // The defect this catches is the most common one in the real corpus: a subSystems: entry
    // that RESOLVES (its nodes are here, drawn, countable) but exposes no interface at all, so
    // nothing in this system can be wired to it. Rendering all 87 corpus models found reused
    // nodes arriving with zero interfaces again and again -- and until now the studio drew that
    // silently, which is how it stayed invisible. It is the one thing a reader of the diagram
    // cannot deduce: an empty box looks the same as a box you simply have not wired yet.
    liveSubRefs().forEach(function(ref){
      var entry=subEntry(ref)||{}, members=subMembers(ref);
      var ifaceCount=0;
      members.forEach(function(m){ ifaceCount+=(m.ifaces||[]).length; });
      if(!ifaceCount){
        pushIssue("e",'subsystem "'+ref+'" exposes nothing — its '+members.length
          +' node(s) arrive with no interfaces',{sub:ref,groupKey:"subempty",groupLabel:"a subsystem exposes nothing connectable",groupUnit:"subsystems",
          fix:"The referenced file declares its nodes but no interfaces:, so no connection in this "
             +"system can name one of them. Fix it in that file (add the interfaces: its nodes "
             +"expose), or open it here, expose what you need and re-Commit it."});
        return;
      }
      // An invented (wrapped) subsystem is OUR file to fix -- so the test is what its own
      // content will DECLARE, and the fix is one click away in the subsystems panel.
      if(entry.invented&&entry.content){
        var declared=0, cc=entry.content;
        (cc.nodes||[]).forEach(function(cn){ (cn.ifaces||[]).forEach(function(cf){ if(cf.exposed) declared++; }); });
        (cc.connections||[]).forEach(function(){ declared++; });   // a wired interface is declared too
        if(!declared)
          pushIssue("w",'subsystem "'+ref+'" will be written with nothing exposed',{sub:ref,groupKey:"subnoexpose",groupLabel:"a wrapped subsystem exposes nothing",groupUnit:"subsystems",
            fix:"Commit writes it as its own .rossystem, and right now that file would declare no "
               +"interfaces — nothing could ever reuse it. Open the subsystems panel and tick the "
               +"interfaces it should offer."});
      }
    });
    // The grammar takes each subSystems: entry as a bare scalar on its own line, so two of them
    // produce a block that the Xtext parser accepts and a plain YAML reader does not -- and
    // rossdl, the live generator downstream of this, reads these files with yaml.safe_load.
    // One entry parses by accident (a scalar continuation); the second is the cliff.
    if((project.subSystems||[]).length>1)
      pushIssue("w",(project.subSystems.length)+" subSystems: entries — the emitted block is not readable as plain YAML",
        {sys:true,groupKey:"submulti",groupLabel:"multiple subSystems: entries",
         fix:"The Xtext grammar accepts it and rosmodel_lint passes it, but two bare entries under "
            +"one key is a YAML parse error, and the rossdl generator reads these files as YAML. "
            +"Keep it to one reference until the grammar gains a list form, or merge the two."});
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
          pushIssue("e",n.label+": "+f.name+" type '"+typ+"' is defined neither here nor in "
            +"the catalogue — define it under 'message types (.ros)'",{code:"RM081",node:n.id,iface:f.id,
            groupKey:"notresolved",groupLabel:"an interface type resolves nowhere",groupUnit:"interfaces",
            fix:"Define this type under Message types (.ros), or correct the spelling — it must match something defined here or in the catalogue."});
        });
      });
      Object.keys(project.types||{}).sort().forEach(function(key){
        var p=String(key).split("/"), block=(p.length===3)?SEGBLOCK[p[1]]:null;
        if(!block){pushIssue("e",key+" is not <package>/<msg|srv|action>/<Name>",{sys:true,typekey:key,
          fix:"Rename the key to <package>/msg/<Name> (or srv/action) — that's the only shape a spec's qualified name takes."});return;}
        if(CATPKG[p[0]]){pushIssue("e",key+": '"+p[0]+"' is a catalogue package — redeclaring it is RM009",{code:"RM009",sys:true,typekey:key,
          fix:"Rename the package — this name is already used by the vendored catalogue."});return;}
        (ROS.bodies[block]||[]).forEach(function(body){
          (((project.types[key]||{}).fields||{})[body]||[]).forEach(function(f,fi){
            var tn=rosTypeNote(f.type,known), nn=rosNameNote(f.name);
            var tag=key+"|"+body+"|"+fi;
            if(tn[0]) pushIssue(tn[0],key+" / "+body+": "+tn[1],{sys:true,ftag:tag,typekey:key});
            else if(nn[0]) pushIssue(nn[0],key+" / "+body+": "+nn[1],{sys:true,ftag:tag,typekey:key});
          });
        });
      });
    })();
    if(!project.nodes.length) pushIssue("e","system has no nodes — add one before generating (the server rejects an empty nodes: block)",{action:"addnode",
      fix:"Add at least one node from the rail."});
    // RM053. A warning, not an error: the current server ACCEPTS a system with no fromFile
    // (re-probed 2026-08-13, 0 errors / 0 warnings), so this must not be dressed up as a crash.
    if(!(project.system&&project.system.fromFile))
      pushIssue("w","no fromFile — rosmodel_lint warns (RM053); the 3.1.0 server accepts a system without it",{code:"RM053",sys:true,field:"f_fromfile",
        fix:"Optional. If you do set it, it must contain a \"/\" (e.g. pkg/launch/bringup.launch.py) — fromFileHelper errors on a bare filename."});
    // fromFileHelper (see the RM053 comment above) errors on a value with no "/" -- unlike an
    // ABSENT fromFile, which the server accepts outright, a PRESENT one that doesn't look like a
    // path is a real generation blocker the instant check should catch before Commit does.
    else if(String(project.system.fromFile).indexOf("/")<0)
      pushIssue("e","fromFile \""+project.system.fromFile+"\" has no \"/\" — the server's fromFileHelper errors on it",{sys:true,field:"f_fromfile",
        fix:"Write it as a path, e.g. pkg/launch/bringup.launch.py, or clear the field — omitting it entirely is accepted."});
    // B1: a drawn connection whose endpoints carry different types is rejected by the server
    for(var ci=0;ci<project.connections.length;ci++){var c=project.connections[ci];
      var fa=ifaceById(nodeById(c.from.n),c.from.i), ta=ifaceById(nodeById(c.to.n),c.to.i);
      if(fa&&ta&&fa.type&&ta.type&&String(fa.type).trim()&&String(ta.type).trim()&&fa.type!==ta.type)
        pushIssue("e","type mismatch: "+fa.name+" ("+fa.type+") ↔ "+ta.name+" ("+ta.type+") — endpoints must share one type",{conn:c.id,nodes:[c.from.n,c.to.n],
          fix:"Change one endpoint's type to match the other, or rewire the connection to an interface that shares the same type."});
    }
    // errors sort before warnings (stable within each) -- previously issues rendered in push
    // order and a silent .slice(0,10) could drop a real error under a stack of RM044 warnings.
    var grouped=groupIssues(issues).slice().sort(function(a,b){ return (a.sev==="e"?0:1)-(b.sev==="e"?0:1); });
    lastIssues=issues;
    nodeIssueIndex=indexIssuesByNode(issues);
    subIssueIndex=indexIssuesBySub(issues);
    var errs=grouped.filter(function(x){return x.sev==="e";}).length, wrns=grouped.length-errs;
    var ec=document.getElementById("errCnt"), wc=document.getElementById("wrnCnt");
    ec.textContent=errs; wc.textContent=wrns;
    var dot=document.getElementById("issDot");
    if(dot){ dot.hidden=!(errs||wrns); dot.className="secdot "+(errs?"e":"w"); }
    var il=document.getElementById("issueList"); il.innerHTML="";
    if(!grouped.length){ il.innerHTML='<div class="it ok">No issues from the instant checks.</div>'; }
    else{
      var shown=issuesExpanded?grouped:grouped.slice(0,10);
      shown.forEach(function(it){ il.appendChild(renderIssueRow(it)); });
      if(grouped.length>shown.length){
        var more=document.createElement("button"); more.type="button"; more.className="itmore";
        more.textContent="show all "+grouped.length;
        more.onclick=function(){ issuesExpanded=true; runIssues(); };
        il.appendChild(more);
      }
    }
    buildStatus(errs,wrns);
  }
  // #issueList is rebuilt from scratch on every render() -- including on every keystroke in an
  // unrelated field, since runIssues() now runs there too. Without this, an expanded group
  // re-collapsed on each one; tracked outside the DOM, by groupKey, it survives the rebuild.
  var expandedGroupKeys={};
  function renderIssueRow(it){
    if(it.group){
      // a collapsed run of identically-shaped issues (same code+severity, one per node or
      // interface) -- expands in place to the individual, still-routable rows.
      var wasOpen=!!expandedGroupKeys[it.groupKey];
      var wrap=document.createElement("div"); wrap.className="itgroup";
      var head=document.createElement("button"); head.type="button"; head.className="it"+(it.sev==="e"?" e":"")+" itgrouphead";
      var gtext=document.createElement("span"); gtext.className="ittext"; gtext.textContent=it.msg;
      // every member of a group shares one underlying problem shape, so they share one fix --
      // shown on the collapsed head too, not just after expanding to a member.
      var gfix=(it.group[0]&&it.group[0].fix)||null;
      if(gfix){ var gfd=document.createElement("div"); gfd.className="itfix"; gfd.textContent=gfix; gtext.appendChild(gfd); }
      head.appendChild(gtext);
      var caret=document.createElement("span"); caret.className="caret"; caret.textContent="▾"; head.appendChild(caret);
      if(it.code){ var gcd=document.createElement("span"); gcd.className="itcode"; gcd.textContent=it.code; head.appendChild(gcd); }
      var kids=document.createElement("div"); kids.className="itkids"; kids.hidden=!wasOpen;
      caret.style.transform=wasOpen?"":"rotate(-90deg)";
      it.group.forEach(function(child){ kids.appendChild(renderIssueRow(child)); });
      head.setAttribute("aria-expanded",wasOpen?"true":"false");
      head.onclick=function(){
        kids.hidden=!kids.hidden;
        head.setAttribute("aria-expanded",kids.hidden?"false":"true");
        caret.style.transform=kids.hidden?"rotate(-90deg)":"";
        if(kids.hidden) delete expandedGroupKeys[it.groupKey]; else expandedGroupKeys[it.groupKey]=true;
      };
      wrap.appendChild(head); wrap.appendChild(kids);
      return wrap;
    }
    var routable=!!(it.node||it.conn||it.sys||it.sub||it.action);
    var el=document.createElement(routable?"button":"div");
    if(routable) el.type="button";
    el.className="it"+(it.sev==="e"?" e":"")+(routable?"":" noref");
    var text=document.createElement("span"); text.className="ittext"; text.textContent=it.msg;
    if(it.fix){ var fd=document.createElement("div"); fd.className="itfix"; fd.textContent=it.fix; text.appendChild(fd); }
    el.appendChild(text);
    if(it.code){ var cd=document.createElement("span"); cd.className="itcode"; cd.textContent=it.code; el.appendChild(cd); }
    if(routable) el.onclick=function(){ gotoIssue(it); };
    if(it.action==="addnode"){
      var btn=document.createElement("span"); btn.className="itmini"; btn.textContent="+ node";
      btn.onclick=function(e){ e.stopPropagation(); gotoIssue(it); };
      el.appendChild(btn);
    }
    return el;
  }

  // ============================ status chip / popover ============================
  function popIssueRow(it){
    // a grouped row has no single target -- "See all" (below) is the path into it, so it
    // renders as plain text here rather than a click that would silently do nothing.
    var routable=!it.group;
    var fix=it.fix||(it.group&&it.group[0]&&it.group[0].fix)||null;
    var b=document.createElement(routable?"button":"div");
    if(routable) b.type="button";
    b.className="popissue"+(it.sev==="e"?" e":"")+(routable?"":" noref");
    b.textContent=it.msg;
    if(fix){ var fd=document.createElement("div"); fd.className="popfix"; fd.textContent=fix; b.appendChild(fd); }
    if(routable) b.onclick=function(){ var pop=document.getElementById("statusPop"); if(pop&&pop.hidePopover) pop.hidePopover(); gotoIssue(it); };
    return b;
  }
  function fillStatusPop(){
    var pop=document.getElementById("statusPop"); if(!pop) return;
    pop.innerHTML="";
    // popover="auto" gets light-dismiss (click outside) and Escape for free from the browser --
    // this button is a belt-and-braces explicit close, not a replacement for either.
    var closeBtn=document.createElement("button"); closeBtn.type="button"; closeBtn.className="popclose";
    closeBtn.setAttribute("aria-label","Close"); closeBtn.textContent="×";
    closeBtn.onclick=function(){ if(pop.hidePopover) pop.hidePopover(); };
    pop.appendChild(closeBtn);
    if(opNotice){
      var row=document.createElement("div"); row.className="poprow";
      var h=document.createElement("h5"); h.textContent=opNotice.title; row.appendChild(h);
      var body=document.createElement("div"); body.innerHTML=opNotice.html; row.appendChild(body);
      pop.appendChild(row);
    }
    var grouped=groupIssues(lastIssues).slice().sort(function(a,b){return (a.sev==="e"?0:1)-(b.sev==="e"?0:1);});
    var row2=document.createElement("div"); row2.className="poprow";
    var h2=document.createElement("h5"); h2.textContent=grouped.length?"Before you commit":"/ros-studio"; row2.appendChild(h2);
    if(grouped.length){
      grouped.slice(0,3).forEach(function(it){ row2.appendChild(popIssueRow(it)); });
      var foot=document.createElement("div"); foot.className="popfoot";
      var seeAll=document.createElement("button"); seeAll.type="button"; seeAll.className="itmore";
      seeAll.textContent="See all "+grouped.length+" in Issues";
      seeAll.onclick=function(){
        if(pop.hidePopover) pop.hidePopover();
        if(isNarrow()) openDrawer("l");
        else expandSec("rail/issues");
        var box=document.querySelector('.rail .insec[data-sec="rail/issues"]');
        if(box) box.scrollIntoView({block:"nearest"});
      };
      foot.appendChild(seeAll); row2.appendChild(foot);
    } else if(!opNotice){
      var p=document.createElement("div");
      p.innerHTML='author in the browser, then <b>Commit</b> to generate &amp; validate in the Python companion.';
      row2.appendChild(p);
    } else {
      var p2=document.createElement("div"); p2.textContent="No issues from the instant checks.";
      row2.appendChild(p2);
    }
    pop.appendChild(row2);
  }
  // The chip is a rollup of overall model health -- max(companion notice, live lint) -- so
  // there is exactly one place that answers "is this model okay", instead of a server-only
  // banner and a separate rail count that can disagree. "ok" is deliberately not styled with
  // --accent (see the CSS comment); a quiet resting state is the point.
  function buildStatus(errs,wrns){
    var chip=document.getElementById("statusChip"); if(!chip) return;
    var glyph=document.getElementById("chipGlyph"), cnt=document.getElementById("chipCount");
    var sev=(errs||(opNotice&&opNotice.sev==="err"))?"err":(wrns||(opNotice&&opNotice.sev==="warn"))?"warn":"ok";
    chip.className="statuschip "+sev;
    var label;
    if(sev==="err"){ glyph.textContent="⚠"; cnt.textContent=errs||""; label=errs?(errs+" error(s), "+wrns+" warning(s)"):"Generation failed"; }
    else if(sev==="warn"){ glyph.textContent="⚠"; cnt.textContent=wrns||""; label=wrns+" warning(s)"; }
    else{ glyph.textContent="ⓘ"; cnt.textContent=""; label="No issues"; }
    chip.title=label; chip.setAttribute("aria-label",label);
    var live=document.getElementById("statusLive"); if(live) live.textContent=label;
    var pop=document.getElementById("statusPop");
    if(pop&&pop.matches&&pop.matches(":popover-open")) fillStatusPop();  // never go stale while open
  }
  (function(){
    var pop=document.getElementById("statusPop");
    if(pop) pop.addEventListener("beforetoggle",function(e){
      if(e.newState!=="open") return;
      fillStatusPop();
      positionPop(pop,document.getElementById("statusChip"));
    });
  })();

  // ============================ per-node warning popover ============================
  // Which node's issues #nodeIssuePop is currently showing, or null when closed. Tracked (not
  // just read off the DOM) so refreshNodeIssuePopIfOpen() below knows what to re-check on every
  // render() without having to search the popover's own rendered content for it.
  var nodePopNodeId=null, nodePopSig=null;
  // A cheap fingerprint of an issue list's user-visible content, so refreshNodeIssuePopIfOpen()
  // can tell "still the same problems" from "actually changed" -- every inspector field re-
  // renders on every keystroke (deliberately, elsewhere in this file), and rebuilding the open
  // popover's DOM on each one would reset its scroll position and steal focus off whatever the
  // user had tabbed into inside it, for no reason if the content didn't change.
  function issueListSig(list){
    return JSON.stringify((list||[]).map(function(it){return [it.sev,it.code||"",it.msg,it.fix||""];}));
  }
  // Closing by any OTHER path than our own code -- native light-dismiss (click outside),
  // native Escape, or the explicit x button -- still has to clear this, or a later render()
  // would find a stale id and either refill a popover the user just closed back open, or hold a
  // reference that stops a future openNodeIssuePop() from recognising "same icon, toggle closed".
  (function(){
    var nip=document.getElementById("nodeIssuePop");
    if(nip) nip.addEventListener("toggle",function(e){ if(e.newState==="closed") nodePopNodeId=null; });
  })();
  // A dragged node, a pan, or a zoom all move the icon on screen without going through render()
  // (they mutate style.left/top or the view transform directly, for drag-frame performance), so
  // the popover -- positioned once, off the icon's rect at open/refresh time -- would silently
  // detach from it mid-gesture otherwise. Simplest correct answer: close it the instant such a
  // gesture starts, rather than trying to track every element/transform that could move it.
  function closeNodeIssuePopIfOpen(){
    var nip=document.getElementById("nodeIssuePop");
    if(nip&&nip.matches&&nip.matches(":popover-open")&&nip.hidePopover){ try{ nip.hidePopover(); }catch(e){} }
  }
  // A popover's real height isn't measurable until the browser has actually laid it out in the
  // top layer -- not yet at beforetoggle/pre-showPopover time, when its display is still `none`.
  // So position once with a same-tick best guess, then correct on the next frame once
  // getBoundingClientRect() reports something real. Node cards can be anywhere on a large
  // canvas (unlike the status chip, always in the topbar), so both matter: a card in the lower
  // half of the screen used to get a popover running off the bottom with nothing to scroll it
  // into view.
  function positionPop(pop,anchorEl){
    if(!anchorEl) return;
    var r=anchorEl.getBoundingClientRect();
    var w=Math.min(380,window.innerWidth-24);
    pop.style.width=w+"px";
    pop.style.left=Math.max(8,Math.min(r.left,window.innerWidth-w-8))+"px";
    pop.style.top=Math.min(r.bottom+6,window.innerHeight-40)+"px";
    requestAnimationFrame(function(){ clampPopVertical(pop,r); });
  }
  function clampPopVertical(pop,anchorRect){
    var h=pop.getBoundingClientRect().height; if(!h) return;
    var below=anchorRect.bottom+6, above=anchorRect.top-6-h, top;
    if(below+h<=window.innerHeight-8) top=below;         // fits below the anchor -- preferred
    else if(above>=8) top=above;                          // flip above it
    else top=Math.max(8,window.innerHeight-8-h);          // fits neither -- clamp into the viewport
    pop.style.top=top+"px";
  }
  function fillNodeIssuePop(nodeId){
    var pop=document.getElementById("nodeIssuePop"); if(!pop) return false;
    var n=nodeById(nodeId), list=nodeIssueIndex[nodeId]||[];
    if(!n||!list.length) return false;   // caller closes the popover in this case
    nodePopSig=issueListSig(list);
    pop.innerHTML="";
    var closeBtn=document.createElement("button"); closeBtn.type="button"; closeBtn.className="popclose";
    closeBtn.setAttribute("aria-label","Close"); closeBtn.textContent="×";
    closeBtn.onclick=function(){ if(pop.hidePopover) pop.hidePopover(); };
    pop.appendChild(closeBtn);
    var h=document.createElement("h5");
    h.textContent=n.label+" — "+list.length+(list.length===1?" issue":" issues");
    pop.appendChild(h);
    list.slice().sort(function(a,b){return (a.sev==="e"?0:1)-(b.sev==="e"?0:1);}).forEach(function(it){
      var wrap=document.createElement("div"); wrap.className="popissuewrap"+(it.sev==="e"?" e":"");
      var btn=document.createElement("button"); btn.type="button"; btn.className="popissue"+(it.sev==="e"?" e":"");
      btn.textContent=it.msg;
      btn.onclick=function(){ if(pop.hidePopover) pop.hidePopover(); gotoIssue(it); };
      wrap.appendChild(btn);
      if(it.fix){ var fx=document.createElement("div"); fx.className="popfix"; fx.textContent=it.fix; wrap.appendChild(fx); }
      pop.appendChild(wrap);
    });
    return true;
  }
  function openNodeIssuePop(nodeId,iconEl){
    var pop=document.getElementById("nodeIssuePop"); if(!pop) return;
    var wasOpenForThis=nodePopNodeId===nodeId && pop.matches && pop.matches(":popover-open");
    // showPopover() throws InvalidStateError on an already-open popover -- close whatever it was
    // last showing first (a different node's icon, most likely) so re-opening never races that.
    if(pop.matches&&pop.matches(":popover-open")&&pop.hidePopover){ try{ pop.hidePopover(); }catch(e){} }
    if(wasOpenForThis){ nodePopNodeId=null; return; }   // clicking the same icon again toggles it closed
    nodePopNodeId=nodeId;
    if(!fillNodeIssuePop(nodeId)){ nodePopNodeId=null; return; }   // nothing to show -- leave it closed
    positionPop(pop,iconEl);
    if(pop.showPopover){ try{ pop.showPopover(); iconEl.setAttribute("aria-expanded","true"); }catch(e){} }
  }
  // Called at the end of every render(), once nodes exist again: if the popover is open, either
  // the node it names still has issues -- refill (the list may itself have changed) and follow
  // the icon to wherever the fresh card landed -- or it doesn't any more, in which case the
  // popover closes itself. This is the other half of "no dangling icon": the icon disappearing
  // is necessary but not sufficient if its explanation is still on screen naming a problem that
  // no longer exists.
  function refreshNodeIssuePopIfOpen(){
    var pop=document.getElementById("nodeIssuePop");
    if(!pop||!pop.matches||!pop.matches(":popover-open")||!nodePopNodeId) return;
    var list=nodeIssueIndex[nodePopNodeId];
    if(!list||!list.length){ if(pop.hidePopover) pop.hidePopover(); nodePopNodeId=null; nodePopSig=null; return; }
    if(issueListSig(list)!==nodePopSig) fillNodeIssuePop(nodePopNodeId);   // only rebuild the DOM if the content actually changed
    var iconEl=canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(nodePopNodeId)+'"] .nwarn');
    if(iconEl) positionPop(pop,iconEl);
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
  // Normalizes a typed-in default to what its ptype actually needs -- "the True/int traps" the
  // old add-only form's placeholder warned about (value: True under type: Boolean parses as a
  // STRING; value: 10 under type: Double parses as an INTEGER). Applied on blur, not on every
  // keystroke, so typing "0.1" doesn't fight a half-finished "0." along the way.
  function coerceParamValue(t,raw){
    if(t==="Boolean") return /^(t|1|y|true)/i.test(raw)?"true":"false";
    if(t==="Integer") return String(parseInt(raw||"0",10)||0);
    if(t==="Double") return raw.indexOf(".")>=0?raw:String((parseFloat(raw||"0")||0).toFixed(1));
    return raw;
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
    syncViewState();     // what leaves the page has to carry the arrangement that is on screen
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
  // The one download primitive. A Blob behind an <a download> is the ONLY write this page has:
  // it is a file:// document with no network and no filesystem API, which is deliberate and
  // load-bearing, and it is also why nothing here can overwrite anything -- the browser's own
  // download UI is the confirmation step, and the user picks where the bytes land.
  function dlBlob(name,text,type){
    var blob=new Blob([text],{type:type||"text/plain"});
    var url=URL.createObjectURL(blob), a=document.createElement("a");
    a.href=url; a.download=name;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function(){URL.revokeObjectURL(url);},1000);
  }
  document.getElementById("dlJson").onclick=function(){
    dlBlob((document.getElementById("sysname").value||"project")+".project.json",
           genProjectJson(),"application/json");
    clearDirty();     // the project has left the page; the beforeunload guard stands down
  };
  // ---- Save all: the real generated files, without the manual Python round-trip -------------
  // The hand-off used to be: download project.json, leave the page, run `generate`, come back.
  // That is three steps and a context switch to obtain files the page can already produce
  // EXACTLY -- tests/studio_parity.js holds genSystem()/genRos2()/genRos() to the Python
  // emitter's bytes for every fixture, so "the browser's preview" and "what generate writes"
  // are the same string, not an approximation of it.
  //
  // So this writes them out directly: one browser download per file, the same Blob mechanism as
  // project.json, staggered because a burst of programmatic downloads is what makes a browser
  // stop honouring them (Chrome prompts once for "allow multiple downloads"; the stagger keeps
  // that to a single prompt rather than one per file).
  //
  // What this deliberately does NOT do, and the note in the modal says so: it does not lint, it
  // does not run the real language server, and it cannot stage a project-local `subSystems:`
  // target -- that file belongs to someone else's model and lives on a disk this page cannot
  // read. Save all is the fast path to the bytes; `generate` is still the path to the VERDICT.
  // The MODEL files, exactly the set and the names `generate` writes into generated/: one
  // <system>.rossystem, one <pkg>.ros2 per hand-authored package, one <pkg>.ros per package
  // whose types this project had to invent. Kept as a pure function -- no DOM beyond the system
  // name, no downloads -- so tests/studio_parity.js can call it and hold the whole manifest,
  // filenames included, against what the companion actually wrote. The naming is the part a
  // byte comparison of the previews could never catch: genSystem() being right does not make
  // "<system>.rossystem" the right thing to call it.
  function generatedFiles(){
    var sys=(document.getElementById("sysname").value||"system");
    var files=[[sys+".rossystem",genSystem(),"text/plain"]];
    handPkgNodes().order.forEach(function(p){ files.push([p+".ros2",genRos2(p),"text/plain"]); });
    Object.keys(companionTypes()).sort().forEach(function(p){ files.push([p+".ros",genRos(p),"text/plain"]); });
    return files;
  }
  function saveAllFiles(){
    var sys=(document.getElementById("sysname").value||"system");
    var files=generatedFiles();
    // last, so that if the browser does cut the burst short the model itself is not the casualty
    files.push([sys+".project.json",genProjectJson(),"application/json"]);
    files.forEach(function(f,i){ setTimeout(function(){
      dlBlob(f[0],f[1],f[2]);
      // Only once the LAST file has actually been handed over. clearDirty() used to run
      // synchronously, before the staggered sequence had started -- so if the browser cut the
      // burst short (the exact failure the stagger exists to mitigate) the unsaved-work guard
      // had already stood down on files that never left the page.
      if(i===files.length-1) clearDirty();
    },i*180); });
    return files.map(function(f){ return f[0]; });
  }
  document.getElementById("saveAll").onclick=function(){
    var names=saveAllFiles();
    var note=document.getElementById("saveAllNote");
    if(note) note.style.display="";
    if(note) note.innerHTML="Saved <b>"+names.length+" file(s)</b>: "+names.map(esc).join(" &middot; ")
      +'<br><span style="color:var(--ink-3)">Your browser may ask once to allow multiple '
      +'downloads. These are the same bytes <code>generate</code> writes &mdash; but only '
      +'<code>generate</code> lints them and asks the real language server.</span>';
  };
  document.getElementById("selJson").onclick=function(){var t=document.getElementById("copyBox");t.focus();t.select();
    // copy-to-clipboard is the other hand-off route to the companion, so it counts as committed
    try{if(document.execCommand("copy")) clearDirty();}catch(e){}};

  // ============================ seed from ROS 2 source ============================
  // The documented pipeline, and nothing but it. Every flag here comes from the two extractors'
  // own argparse and from skills/ros-model/SKILL.md's "Converting real source" block; the
  // executable ground truth is tests/extract_golden.py, which runs steps 1 and 2 exactly this
  // way. Nothing is invented -- a fabricated flag would fail at the shell, minutes later, in a
  // tool the user has no reason to distrust.
  //
  // The one coupling that is invisible from the flags: step 1's -o and step 2's --models must be
  // the SAME directory. ModelIndex does a flat os.listdir() of --models, and a wrong path fails
  // SILENTLY -- no local models, so every launch node resolves against the vendored catalogue or
  // is skipped with a # FLAG. That is why both are derived here from one field instead of being
  // asked for twice.
  var SRC_PH="<FILL-IN>";
  function shq(s){
    // POSIX single-quoting, so a path with a space or a bracket survives the copy. A value that
    // is still the placeholder is left BARE and unquoted -- quoting it would make it look like a
    // real answer, and the whole point is that the shell should fail loudly on it.
    s=String(s==null?"":s).trim();
    // An empty value, or one that is ALREADY the placeholder (a stem that could not be derived
    // because no launch file was given), comes out bare. Quoting it would both hide it from the
    // highlighter, which matches the raw token, and dress it up as a real answer.
    if(!s||s===SRC_PH) return SRC_PH;
    if(/^[A-Za-z0-9_@%+=:,.\/-]+$/.test(s)) return s;
    return "'"+s.replace(/'/g,"'\\''")+"'";
  }
  function srcCmds(){
    var repo=document.getElementById("srcRepo").value.trim();
    var launch=document.getElementById("srcLaunch").value.trim();
    var out=document.getElementById("srcOut").value.trim()||"ros_model";
    var name=document.getElementById("srcName").value.trim();
    var ctrl=document.getElementById("srcCtrl").value.trim();
    var missing=[];
    if(!repo) missing.push("the source tree");
    if(!launch) missing.push("the launch file");
    // The system name is optional to the TOOL (--system-name defaults to the launch file's
    // stem) but NOT to this panel: step 2's -o and step 3's input are both required paths that
    // have to be spelled concretely, and nothing derives them. Deriving the stem here from the
    // first launch file's basename is what the field's hint promises, so do exactly that rather
    // than emitting a <system> placeholder the status line then failed to mention -- a command
    // block containing an unfilled token while the panel reports nothing missing is the one
    // outcome worse than asking for the value.
    var stem=name;
    if(!stem&&launch){
      var first=launch.split(/\s+/)[0].replace(/\\/g,"/");
      stem=(first.split("/").pop()||"").replace(/\.(launch\.)?(py|xml|yaml|yml)$/i,"")
             .replace(/\.launch$/i,"");
    }
    if(!stem) stem="<FILL-IN>";

    var O=shq(out);
    // Several launch files are accepted (nargs="+"); split on whitespace and quote each.
    var launches=launch?launch.split(/\s+/).map(shq).join(" "):SRC_PH;
    // PY/PLUGIN follow the spelling every other doc in this repo uses. CLAUDE_PLUGIN_ROOT is set
    // when the plugin is installed; inside the repo it is not, and the paths are simply
    // scripts/... -- which SKILL.md says in as many words, so the note below says it too.
    var PY='"${ROSMODEL_PYTHON:-python3}"';
    var P='"${CLAUDE_PLUGIN_ROOT}/scripts';
    var l=[];
    l.push("# 1. ROS 2 source -> draft .ros2 node models (+ .ros for project-local message types)");
    l.push(PY+" "+P+'/extract_ros2_interfaces.py" '+shq(repo)+" \\");
    l.push("    -o "+O+"/rosnodes --emit-msgs "+O+"/msgs \\");
    l.push("    --json "+O+"/extraction_record.json");
    l.push("");
    l.push("# 2. launch file(s) + those .ros2 -> a draft .rossystem");
    l.push("#    --models MUST be step 1's -o directory: it is a flat listdir, and a wrong path");
    l.push("#    fails silently (every node then resolves to the catalogue, or is skipped).");
    var two=PY+" "+P+'/extract_rossystem.py" '+launches+" \\";
    l.push(two);
    l.push("    --models "+O+"/rosnodes \\");
    l.push("    -o "+O+"/"+shq(stem)+".rossystem \\");
    l.push("    --workspace "+shq(repo)+" \\");
    if(name) l.push("    --system-name "+shq(name)+" \\");
    if(ctrl) l.push("    --controllers-file "+shq(ctrl)+" \\");
    l.push("    --json "+O+"/system_record.json");
    l.push("");
    l.push("# 3. that .rossystem -> project.json (sibling .ros2/.ros are picked up automatically)");
    l.push(PY+" "+P+'/ros_studio.py" init '+O+"/"+shq(stem)+".rossystem \\");
    l.push("    --out "+O+"/project.json");
    return {text:l.join("\n"), missing:missing, stem:stem, out:out};
  }
  function renderSrcCmds(){
    var r=srcCmds();
    var box=document.getElementById("srcOutBox");
    box.textContent=r.text;
    // Highlight every placeholder so an unfilled field is impossible to copy by accident
    // without noticing. Done by re-walking the text, not by building HTML above, so the COPIED
    // string and the DISPLAYED string can never diverge.
    if(r.text.indexOf(SRC_PH)>=0){
      box.innerHTML=box.innerHTML
        .replace(/&lt;FILL-IN&gt;/g,'<span class="ph">&lt;FILL-IN&gt;</span>');
    }
    var st=document.getElementById("srcState");
    st.className="srcstate"+(r.missing.length?" bad":"");
    st.textContent=r.missing.length
      ? ("fill in "+r.missing.join(" and ")+" — the commands carry <FILL-IN> until you do")
      : "";
    document.getElementById("srcAfter").innerHTML=
      'Step 2 exits non-zero whenever it flags anything, and step 1 does on a lint ERROR &mdash; '
      +'that is normal here: <b>a partial model is a result, not a failure</b>, so read the '
      +'reports rather than stopping. Then <b>Open</b> <code>'+esc(r.out)+'/project.json</code> '
      +'in this page. If step 1 fails with "No such file or directory", '
      +'<code>${CLAUDE_PLUGIN_ROOT}</code> is unset because you are inside the plugin repo &mdash; '
      +'use plain <code>scripts/&hellip;</code> paths.';
  }
  (function(){
    var scrim=document.getElementById("srcScrim");
    var btn=document.getElementById("fromSrc");
    if(!btn||!scrim) return;
    btn.onclick=function(){ scrim.classList.add("on"); renderSrcCmds();
      var f=document.getElementById("srcRepo"); if(f) setTimeout(function(){f.focus();},0); };
    ["srcRepo","srcLaunch","srcOut","srcName","srcCtrl"].forEach(function(id){
      var el=document.getElementById(id); if(el) el.oninput=renderSrcCmds;
    });
    document.getElementById("srcCopy").onclick=function(){
      var t=document.getElementById("srcOutBox").textContent;
      var st=document.getElementById("srcState");
      function done(ok){ st.className="srcstate"+(ok?"":" bad");
        st.textContent=ok?"copied — run it in a terminal, or paste it to Claude Code"
                         :"could not copy; select the text above instead"; }
      // navigator.clipboard is unavailable on a file:// origin in some browsers, so the old
      // execCommand path is kept as the fallback rather than assumed dead.
      if(navigator.clipboard&&navigator.clipboard.writeText){
        navigator.clipboard.writeText(t).then(function(){done(true);},function(){done(false);});
        return;
      }
      try{
        var ta=document.createElement("textarea");
        ta.value=t; ta.style.position="fixed"; ta.style.opacity="0";
        document.body.appendChild(ta); ta.select();
        var ok=document.execCommand("copy");
        document.body.removeChild(ta); done(ok);
      }catch(e){ done(false); }
    };
  })();

  // ============================ mode / level ============================
  var modeSeg=document.getElementById("modeSeg"), levelSeg=document.getElementById("levelSeg");
  // Factored out of the click handler so restoreViewState() can reach it: a saved project.json
  // that was in View mode has to come back in View mode, and re-toggling the body classes by
  // hand in two places is exactly how the two drift.
  function setMode(m){
    mode=m;
    modeSeg.querySelectorAll("button").forEach(function(x){x.classList.toggle("on",x.dataset.mode===m);});
    // classList, NOT `className=`. A wholesale assignment here wiped every other class on
    // <body> -- which since the responsive layer moved onto `narrow`/`tiny`/`drawer-*` meant
    // that tapping View or Edit on a phone destroyed the layout and dropped the page back into
    // the desktop three-column form, mid-session, with a drawer possibly open.
    document.body.classList.toggle("mode-edit",mode==="edit");
    document.body.classList.toggle("mode-view",mode!=="edit");
  }
  modeSeg.querySelectorAll("button").forEach(function(b){b.onclick=function(){
    setMode(b.dataset.mode);
    selEdge=null; noteViewChange(); render(); fillInspector();
  };});
  levelSeg.querySelectorAll("button").forEach(function(b){b.onclick=function(){level=+b.dataset.lvl;setLevelButtons();noteViewChange();render();};});
  function setLevelButtons(){levelSeg.querySelectorAll("button").forEach(function(x){x.classList.toggle("on",+x.dataset.lvl===level);});}

  // ============================ collapsible sections ============================
  // Delegated once, at the container -- the inspector's whole innerHTML is replaced on every
  // selection change, so per-button listeners would need re-wiring in five separate builders.
  wireSecClicks(document.querySelector(".rail"));
  wireSecClicks(inspector);
  // The rail's four sections are static markup (only their contents get rebuilt), so unlike the
  // inspector -- which bakes `collapsed` into the string via sec() on every render -- they need
  // one explicit pass at startup to pick up persisted / default-closed state.
  applySecState(document.querySelector(".rail"));
  // Same delegation trick for the Selected/Project tab strip -- also rebuilt on every render.
  // NOT pushUndo(): switching tabs is presentation, and it deliberately leaves selNode/selEdge
  // alone, so Project is reachable without losing whatever was selected.
  inspector.addEventListener("click",function(e){
    var b=e.target.closest("[data-insptab]"); if(!b||b.disabled) return;
    inspTab=b.dataset.insptab; fillInspector();
  });

  // ============================ canvas controls ============================
  document.getElementById("autoLayout").onclick=autoLayout;
  // A VIEW preference. It rides in project["view"] now (so a saved arrangement comes back with
  // the port sides it was arranged with) and STILL in localStorage (so it stays a running
  // preference for a project that carries none). It never touches undo and never enters a fact
  // tree. The project's saved value wins on an explicit load; localStorage seeds the rest.
  function setAutoSides(b){
    autoSides=!!b;
    var box=document.getElementById("autoSides");
    if(box) box.checked=autoSides;
    try{ localStorage.setItem("rosStudio.autoSides",autoSides?"1":"0"); }catch(e){}
  }
  (function(){
    var box=document.getElementById("autoSides");
    if(!box) return;
    var pref=false;
    try{ pref=localStorage.getItem("rosStudio.autoSides")==="1"; }catch(e){}
    autoSides=pref; box.checked=autoSides;
    box.onchange=function(){
      setAutoSides(box.checked);
      noteViewChange();
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
    // A native popover already closes itself on Escape; without this bail the same keydown
    // goes on to clear the selection underneath it as an unrelated side effect.
    var _sp=document.getElementById("statusPop"), _nip=document.getElementById("nodeIssuePop");
    if(e.key==="Escape"&&((_sp&&_sp.matches&&_sp.matches(":popover-open"))||(_nip&&_nip.matches&&_nip.matches(":popover-open")))) return;
    if(e.key==="Escape"){[].slice.call(document.querySelectorAll(".scrim.on:not([data-locked])")).forEach(function(s){s.classList.remove("on");});selNode=null;selEdge=null;multiSel=Object.create(null);render();fillInspector();}
    if(e.key>="1" && e.key<="4" && !typing){level=+e.key;setLevelButtons();render();}
    if((e.key==="Delete"||e.key==="Backspace")&&mode==="edit"&&selNode&&!typing){
      // a subSystems: node is provided by the referenced file; deleting it here would strip the
      // connections that name it while the subSystems: line still claimed to provide them. The
      // inspector offers no Delete button for one either.
      var sn=nodeById(selNode); if(sn&&sn.backing==="sub") return;
      pushUndo();
      project.connections=project.connections.filter(function(c){return c.from.n!==selNode&&c.to.n!==selNode;});
      project.nodes=project.nodes.filter(function(x){return x.id!==selNode;});selNode=null;multiSel=Object.create(null);render();fillInspector();}
  });
  // ============================ the guided tutorial ============================
  // Somebody who has never opened this page is looking at a blank canvas, four abstraction
  // levels, a rail of filters and a Commit button, and nothing on screen says which of those is
  // the first move. The README explains it; the README is not in the page, and a reader who has
  // to leave the tool to learn the tool mostly does not come back.
  //
  // So this walks them through building one real system, in this editor, with their own hands:
  // tb3_teleop -- a keyboard teleop node driving a TurtleBot 3 base over /cmd_vel. Both nodes
  // are vendored catalogue entries (assets/rosmodelscatalog/robots/turtlebot3/), so every
  // interface name and every message type below is the one the real .ros2 file declares, not a
  // placeholder. It is the smallest thing in the catalogue that is genuinely a SYSTEM: two
  // nodes, one wire, one type that has to match on both ends.
  //
  // Deliberately NOT the catalogued `turtlebot` composition, which is the obvious candidate --
  // 3 nodes, 7 interfaces and, as the table in commands/ros-studio.md records, ZERO internal
  // connections. A first tutorial whose worked example cannot demonstrate wiring would teach
  // the one thing this editor exists for by not doing it.
  //
  // Three rules this thing keeps, all of which are the reason it is written the way it is:
  //
  //   1. It never edits the model. Every "done" test below READS project and nothing more; the
  //      only things it does on the reader's behalf are opening a collapsed rail section, a
  //      drawer, or centring the camera on a card -- all views. So there is no undo entry, no
  //      dirty flag, and no way for a walkthrough to appear in a diff.
  //   2. Its own state is not the project's. Which step you are on and whether you finished
  //      live under one localStorage key. It is a fact about the READER, not the model: a
  //      project.json handed to a colleague must not carry "Mae got as far as step 4", and the
  //      only way to guarantee that is for the state never to enter `project` at all -- which
  //      is a stronger guarantee than a project.view slot that both fact trees have to keep
  //      remembering to exclude. tests/studio_parity.js pins both halves of that.
  //   3. It never takes a click. No scrim, nothing modal, and the halo is pointer-events:none,
  //      because on most steps the click it is pointing at is the point of the step.
  var TOUR_KEY="rosStudio.tour";
  function tourLoad(){ try{ return JSON.parse(localStorage.getItem(TOUR_KEY)||"{}")||{}; }catch(e){ return {}; } }
  function tourStore(patch){
    var st=tourLoad(); Object.keys(patch).forEach(function(k){ st[k]=patch[k]; });
    try{ localStorage.setItem(TOUR_KEY,JSON.stringify(st)); }catch(e){}   // full/blocked storage: the tour just stops remembering
  }
  // The two nodes the walkthrough is about, by the `from:` halves the .rossystem will spell.
  // Looked up by package rather than by label so a reader who renames a card (which they are
  // encouraged to do -- the label is the instance name) does not fall out of the walkthrough.
  var TOUR_TELEOP="turtlebot3_teleop", TOUR_BASE="turtlebot3_node";
  function tourNode(pkg){
    for(var i=0;i<project.nodes.length;i++) if(project.nodes[i].pkg===pkg) return project.nodes[i];
    return null;
  }
  function tourIface(n,name){
    if(!n) return null;
    for(var i=0;i<n.ifaces.length;i++) if(n.ifaces[i].name===name) return n.ifaces[i];
    return null;
  }
  function tourNodeEl(pkg){
    var n=tourNode(pkg); return n?canvas.querySelector('.node[data-n="'+STUDIO.cssEsc(n.id)+'"]'):null;
  }
  function tourPortEl(pkg,ifname){
    var n=tourNode(pkg), f=tourIface(n,ifname);
    if(!n||!f) return null;
    return canvas.querySelector('.port[data-n="'+STUDIO.cssEsc(n.id)+'"][data-i="'+STUDIO.cssEsc(f.id)+'"]');
  }
  function tourScrimOn(id){ var s=document.getElementById(id); return !!(s&&s.classList.contains("on")); }
  // Auto layout is the one step whose result is not a durable model fact you can test for -- it
  // rewrites x/y that were already there, so "did it run?" cannot be answered by reading the
  // project. A capture-phase listener on document, live only while the tour is open, records
  // the click without any of the handlers it observes knowing this exists.
  var tourSaw={};
  function tourWatchClicks(ev){
    var t=ev.target&&ev.target.closest?ev.target.closest("button"):null;
    if(t&&t.id) tourSaw[t.id]=true;
  }
  function tourReachRail(){ expandSec("rail/add"); if(isNarrow()) openDrawer("l"); }
  function tourReachCanvas(pkg){ closeDrawers(); var n=tourNode(pkg); if(n) centreOn(n.id); }
  function tourReachInspector(){ if(isNarrow()) openDrawer("r"); }

  // Each step: what it is called, what it says, what it points at, and -- for a "do" step --
  // what has to become true in the real model before Next lights up. `wait` is the promise the
  // step makes about that test, in the reader's words; a step with no `done` is a read step and
  // Next is live immediately.
  var TOUR=[
  {id:"intro",title:"Build a real TurtleBot 3 system",
   body:["This walkthrough builds <code>tb3_teleop</code>: a keyboard teleop node driving a TurtleBot 3 base over <code>/cmd_vel</code>. Two nodes, one wire, and the real generated files at the end.",
         "Nothing here is invented for the tutorial. Both nodes are vendored catalogue entries, so every interface name and message type you are about to see is the one the real <code>.ros2</code> file declares.",
         "You drive — this panel follows and reacts to what you actually do. It never edits your model, and it never takes a click away from the thing it is pointing at."]},

  {id:"name",title:"Name the system",anchor:function(){return document.getElementById("sysname");},
   wait:"waiting for a system name",
   done:function(){ var v=((project.system&&project.system.name)||"").trim();
                    return v.length>0&&v!==tourEntryName; },
   enter:function(){ tourEntryName=((project.system&&project.system.name)||"").trim(); },
   body:["This is not a label. <code>generate</code> writes <code>&lt;name&gt;.rossystem</code> and the <code>RosSystem</code> declaration inside it, so the name here is the filename you will hand back to the companion.",
         "Type <code>tb3_teleop</code>."]},

  {id:"catopen",title:"Reuse a node instead of retyping it",anchor:function(){return document.getElementById("addCat");},
   enter:tourReachRail,
   wait:"waiting for the catalogue to open",
   done:function(){ return tourScrimOn("catScrim"); },
   body:["<b>From catalogue…</b> lists the artifacts vendored under <code>assets/rosmodelscatalog/</code> — real <code>.ros2</code> files, not stubs.",
         "Instantiating one copies its interface names <i>and</i> their message types. That second half is the part you would otherwise get wrong: a topic name is easy to remember, <code>geometry_msgs/msg/Twist</code> is not.",
         "Click it."]},

  {id:"teleop",title:"Add the keyboard teleop",anchor:function(){return document.getElementById("catSearch");},
   wait:"waiting for turtlebot3_teleop on the canvas",
   done:function(){ return !!tourNode(TOUR_TELEOP); },
   body:["Search <code>turtlebot3_teleop</code> and press <b>instantiate</b>. It publishes exactly one thing: <code>cmd_vel</code>, typed <code>geometry_msgs/msg/Twist</code>.",
         "It arrives with every interface <b>unexposed</b>, on purpose. A catalogue node can declare dozens, and exposing all of them would write dozens of unwired lines into your <code>.rossystem</code>. They surface as you wire them."]},

  {id:"readcard",title:"What the card is telling you",anchor:function(){return tourNodeEl(TOUR_TELEOP);},
   enter:function(){ tourReachCanvas(TOUR_TELEOP); },
   body:["<code>from: \"turtlebot3_teleop.teleop_keyboard\"</code> is the exact string the <code>.rossystem</code> will spell — the package, then the artifact inside it.",
         "The <b>catalogue</b> badge means this project does not own that <code>.ros2</code> and will not rewrite it; its names and types are greyed out in the inspector for the same reason.",
         "The coloured dot on the right is the port, and its colour is the interaction <i>kind</i> — <code>pub</code> here. That is a different axis from the per-source colour the rail's <b>Source systems</b> legend uses once a project has been merged from more than one file: a card can carry both, and they never compete for the same pixel."]},

  {id:"base",title:"Add the robot",anchor:function(){return document.getElementById("addCat");},
   enter:tourReachRail,
   wait:"waiting for turtlebot3_node on the canvas",
   done:function(){ return !!tourNode(TOUR_BASE); },
   body:["Open the catalogue again and instantiate <code>turtlebot3_node</code>.",
         "It subscribes <code>cmd_vel</code> (the same <code>geometry_msgs/msg/Twist</code>) and publishes <code>odom</code> (<code>nav_msgs/msg/Odometry</code>) and <code>tf</code> (<code>tf2_msgs/msg/TFMessage</code>)."]},

  {id:"wire",title:"Draw the wire",anchor:function(){return tourPortEl(TOUR_TELEOP,"cmd_vel")||tourNodeEl(TOUR_TELEOP);},
   enter:function(){ tourReachCanvas(TOUR_TELEOP); },
   wait:"waiting for a connection between the two nodes",
   done:function(){
     var a=tourNode(TOUR_TELEOP), b=tourNode(TOUR_BASE);
     if(!a||!b) return false;
     return project.connections.some(function(c){
       return (c.from.n===a.id&&c.to.n===b.id)||(c.from.n===b.id&&c.to.n===a.id); });
   },
   body:["Drag from this <code>pub</code> dot onto <code>turtlebot3_node</code>'s <code>cmd_vel</code> <code>sub</code> dot. Letting go anywhere on the target row counts — the dot is a 12px target and the row is not.",
         "The drop is refused unless the kinds are complementary <i>and</i> the types match. Both ends are <code>geometry_msgs/msg/Twist</code>, so this one is legal; try dropping it on <code>odom</code> instead and nothing happens.",
         "Wiring also exposes both ends. A <code>connections:</code> endpoint is a bare label resolved file-wide, so an endpoint that was not exposed would name something the file never declares.",
         "File-wide is also why both ends being called <code>cmd_vel</code> is not a problem: the emitter will write them as <code>cmd_vel_pub</code> and <code>cmd_vel_sub</code> rather than declare one key twice, which is RM009. You will see those names in the preview at the end."]},

  {id:"expose",title:"Expose something you did not wire",
   anchor:function(){
     var b=tourNode(TOUR_BASE), f=tourIface(b,"odom");
     return (f&&document.querySelector('#inspector input[data-exp="'+STUDIO.cssEsc(f.id)+'"]'))||tourNodeEl(TOUR_BASE);
   },
   enter:function(){ tourReachCanvas(TOUR_BASE); },
   wait:"waiting for odom to be exposed",
   done:function(){ var f=tourIface(tourNode(TOUR_BASE),"odom"); return !!(f&&f.exposed); },
   body:["Select the <code>turtlebot3_node</code> card, find <code>odom</code> under <b>interfaces</b> in the inspector, and tick <b>expose</b>.",
         "Connectivity is not the test for whether an interface belongs in the <code>.rossystem</code>. A model may declare one for documentation and deliberately leave it unwired — which is why <code>exposed</code> is stored per interface instead of being derived from the connection list, and why a round-trip does not quietly delete the ones you meant to keep."]},

  {id:"issues",title:"What the rail has been telling you",anchor:function(){return document.querySelector('.rail .insec.issues');},
   enter:function(){ expandSec("rail/issues"); if(isNarrow()) openDrawer("l"); },
   body:["Your system is complete now, so this is worth reading. The <b>Issues</b> rail is a third thing, next to the two checkers you will meet at the end: it is the instant, in-page subset, re-run on every edit, and every row is clickable — it selects and centres whatever it is about, and in Edit mode focuses the exact field.",
         "It should be showing one warning: <b>RM053</b>, no <code>fromFile:</code>. Nothing has told this model which launch file it came from, which is simply what a hand-built system looks like; the 3.1.0 server accepts one without it. Set it in the <b>Project</b> tab of the inspector if you want it gone."]},

  {id:"layout",title:"Let the layout follow the wiring",anchor:function(){return document.getElementById("autoLayout");},
   enter:function(){ closeDrawers(); },
   wait:"waiting for Auto layout",
   done:function(){ return !!tourSaw.autoLayout; },
   body:["<b>Auto layout</b> is a layered pass that follows connection direction: sources left, sinks right, four barycentre sweeps to cut crossings, isolated nodes in a trailing column. Node sizes are measured off the rendered cards, because a node's height is its interface count.",
         "Node <code>x</code>/<code>y</code> are model data, so this is a normal undoable edit — <code>Ctrl+Z</code> puts the old arrangement back, including the subsystem and package boxes the pass clears."]},

  {id:"levels",title:"Four ways to look at one model",anchor:function(){return document.getElementById("levelSeg");},
   body:["<b>Full</b> is what you have been editing. <b>Interfaces</b> drops the types, <b>System</b> drops the interface rows entirely, and <b>Deps</b> redraws the model as nodes against the packages they come from. Try them — <code>1</code>–<code>4</code> are the shortcuts.",
         "Everything you arrange — the level, Edit vs View, the kind filter, box positions, even where the camera is standing — is saved into <code>project.json</code> under <code>project.view</code>, so a picture you spent ten minutes building survives a reload.",
         "None of it can reach an emitted byte. Both fact trees are built from an allow-list of model keys, so a view key is excluded by construction rather than by being deleted, and <code>tests/studio_parity.js</code> re-emits under a deliberately populated view to prove it."]},

  {id:"commit",title:"See the files before you write them",anchor:function(){return document.getElementById("commit");},
   enter:function(){ closeDrawers(); },
   wait:"waiting for the Commit modal",
   done:function(){ return tourScrimOn("commitScrim"); },
   body:["Open <b>Commit</b>. The <code>.rossystem</code> / <code>.ros2</code> / <code>.ros</code> tabs are not an approximation of what the companion would emit: <code>tests/studio_parity.js</code> holds all three to the Python emitter byte for byte, for every fixture in the repo.",
         "The fourth tab, <b>changed since the seed</b>, is the same model-level report <code>ros_studio.py diff</code> prints in a terminal — computed live in the page as you edit."]},

  {id:"saveall",title:"Save all files",anchor:function(){return document.getElementById("saveAll");},
   body:["<b>Save all files</b> downloads the whole set — the <code>.rossystem</code>, every <code>.ros2</code>, every companion <code>.ros</code>, and the <code>project.json</code> — as one browser download each. This page is a <code>file://</code> document with no network and no filesystem API, so nothing is overwritten and the browser's own download UI is the confirmation step.",
         "Two things it deliberately does not do, and the modal says so: it does not lint, and it cannot stage a project-local <code>subSystems:</code> target — staging means copying someone else's file off a disk this page cannot read."]},

  {id:"verdict",title:"Only generate gives you a verdict",anchor:function(){return document.getElementById("genTabs");},
   body:["Run <code>ros_studio.py generate project.json</code> on what you just saved. It emits the files, runs <code>rosmodel_lint</code>, and — by default, not opt-in — asks the real Xtext language server.",
         "The server is the authority and the linter is a deliberate approximation of it: the standard example of what only the server catches is an action server declared with a <i>message</i> type instead of an action type.",
         "If the jar cannot run, you are told on stdout, on stderr, and in a <code>.notice.html</code> banner this page opens on load — naming the binary it found, why it is unusable and how to fix it. A half-validated run is never allowed to look like a clean one."]},

  {id:"fromsrc",title:"When you have source, not a model",anchor:function(){return document.getElementById("fromSrc");},
   enter:tourReachRail,
   body:["<b>From ROS 2 source…</b> is the other way in. This page cannot spawn a process, so it does not pretend to import a repository: you give it the source tree and the launch file, and it writes the exact, correctly ordered, correctly flagged extractor commands for you to run in a terminal — or to paste to Claude Code.",
         "It exists to get four things right that are easy to get wrong by hand. The worst of them: step 1's <code>-o</code> and step 2's <code>--models</code> have to be the same directory, and a wrong path there fails <i>silently</i> — there are simply no local models, so every launch node quietly resolves against the catalogue or is skipped."]},

  {id:"done",title:"That's the loop",
   body:["You built <code>tb3_teleop</code> out of two catalogued TurtleBot 3 nodes, wired the real <code>/cmd_vel</code> topic between them with the type checked on both ends, exposed one interface you deliberately left unwired, and previewed the exact bytes <code>generate</code> will write.",
         "From here: <b>Import</b> adds another <code>.rossystem</code> to this canvas, and the rail grows a <b>Source systems</b> legend that colours, counts and filters by where each node came from — at the <b>System</b> level each source becomes one box. Right-click a selection to wrap it into a <code>subSystems:</code> reference of its own.",
         "Reopen this walkthrough any time from <b>Tutorial</b> in the toolbar."]}
  ];

  var tourIdx=-1, tourEl=null, tourHalo=null, tourRaf=null, tourTimer=null,
      tourEntryName=null, tourWasDone=null;

  function tourBuild(){
    if(tourEl) return;
    tourEl=document.createElement("div");
    tourEl.className="tourcard";
    tourEl.id="tourCard";
    tourEl.setAttribute("role","region");
    tourEl.setAttribute("aria-label","Tutorial");
    tourEl.tabIndex=-1;
    // The live region is the INNER wrapper, built once and refilled per step. An aria-live
    // element that is itself replaced announces nothing -- the announcement comes from a
    // mutation inside a region that was already there when the screen reader started watching.
    tourEl.innerHTML='<div class="tlive" aria-live="polite"></div>'
      +'<div class="tourbar" aria-hidden="true"></div>'
      +'<div class="tfoot">'
      +'<button type="button" id="tourBack">&#8592; Back</button>'
      +'<button type="button" id="tourSkip">Skip</button>'
      +'<span class="grow"></span>'
      +'<button type="button" class="go" id="tourNext">Next &#8594;</button></div>';
    document.body.appendChild(tourEl);
    tourHalo=document.createElement("div");
    tourHalo.className="tourhalo pulse";
    document.body.appendChild(tourHalo);
    document.getElementById("tourBack").onclick=function(){ tourGo(tourIdx-1); };
    document.getElementById("tourNext").onclick=function(){ tourGo(tourIdx+1); };
    // Skip is not decoration. Every "done" test above is a guess about what the reader meant,
    // and a walkthrough that can wedge on a guess is a walkthrough people close.
    document.getElementById("tourSkip").onclick=function(){ tourGo(tourIdx+1); };
  }

  function tourGo(i){
    if(i<0) return;
    if(i>=TOUR.length){ tourStore({step:0,done:true,dismissed:true}); tourClose(); return; }
    tourIdx=i; tourWasDone=null;
    tourStore({step:i});
    var st=TOUR[i];
    if(st.enter){ try{ st.enter(); }catch(e){} }
    var live=tourEl.querySelector(".tlive");
    live.innerHTML='<div class="thead"><span class="tstep">step '+(i+1)+' of '+TOUR.length+'</span>'
      +'<h5>'+st.title+'</h5>'
      +'<button type="button" class="tclose" id="tourClose" aria-label="Close the tutorial">&#10005;</button></div>'
      +'<div class="tbody">'+st.body.map(function(p){return "<p>"+p+"</p>";}).join("")+'</div>'
      +(st.done?'<div class="twait" id="tourWait"></div>':'');
    document.getElementById("tourClose").onclick=function(){ tourStore({dismissed:true}); tourClose(); };
    var bar=tourEl.querySelector(".tourbar");
    bar.innerHTML=TOUR.map(function(_,j){return '<i'+(j<=i?' class="on"':'')+'></i>';}).join("");
    document.getElementById("tourBack").disabled=(i===0);
    document.getElementById("tourSkip").hidden=!st.done;
    var next=document.getElementById("tourNext");
    next.textContent=(i===TOUR.length-1)?"Finish":"Next →";
    tourCheck(true);
    tourPlace();
  }

  // Re-run this step's promise against the live model. Only touches the DOM when the answer
  // CHANGED -- this runs five times a second and rewriting the footer each time would fight
  // anything focused inside it.
  function tourCheck(force){
    var st=TOUR[tourIdx]; if(!st) return;
    var next=document.getElementById("tourNext");
    if(!st.done){ if(force){ next.disabled=false; } return; }
    var ok=false;
    try{ ok=!!st.done(); }catch(e){ ok=false; }
    if(!force&&ok===tourWasDone) return;
    tourWasDone=ok;
    next.disabled=!ok;
    var w=document.getElementById("tourWait");
    if(w){ w.className="twait"+(ok?" done":""); w.textContent=ok?"done ✓":(st.wait||"waiting…"); }
  }

  // Track the anchor every frame rather than on a timer: on the steps that point at a card on
  // the canvas the reader can drag it, and a ring that lags a drag by a fifth of a second reads
  // as a rendering bug. The DOM write is skipped whenever nothing moved.
  var tourLastBox="";
  function tourPlace(){
    var st=TOUR[tourIdx]; if(!st||!tourEl) return;
    var el=null;
    try{ el=st.anchor?st.anchor():null; }catch(e){ el=null; }
    var r=null;
    if(el&&el.getBoundingClientRect){
      var b=el.getBoundingClientRect();
      // Zero-sized means the anchor is inside a collapsed section or a closed drawer, and
      // off-viewport means it scrolled away. Either way there is nothing honest to point at,
      // so the ring is hidden and the card falls back to centre rather than ringing a corner.
      if(b.width>0&&b.height>0&&b.bottom>0&&b.right>0&&b.top<window.innerHeight&&b.left<window.innerWidth) r=b;
    }
    var key=r?[Math.round(r.left),Math.round(r.top),Math.round(r.width),Math.round(r.height),
               window.innerWidth,window.innerHeight,tourEl.offsetHeight].join(","):"none";
    if(key===tourLastBox) return;
    tourLastBox=key;
    if(r){
      tourHalo.hidden=false;
      tourHalo.style.left=(r.left-4)+"px"; tourHalo.style.top=(r.top-4)+"px";
      tourHalo.style.width=(r.width+8)+"px"; tourHalo.style.height=(r.height+8)+"px";
    } else tourHalo.hidden=true;
    // Docked (phone): the stylesheet owns left/top/bottom with !important, so writing them here
    // would just be dead inline styles that come back the moment the class stops applying.
    if(isNarrow()) return;
    var w=tourEl.offsetWidth, h=tourEl.offsetHeight, M=10;
    var left, top;
    if(r){
      left=r.left;
      top=r.bottom+M;
      if(top+h>window.innerHeight-M) top=r.top-h-M;      // no room below: flip above
      if(top<M){                                          // no room either way: sit beside it
        top=Math.max(M,Math.min(r.top,window.innerHeight-h-M));
        left=(r.right+M+w<window.innerWidth-M)?(r.right+M):(r.left-w-M);
      }
    } else {
      left=(window.innerWidth-w)/2; top=(window.innerHeight-h)/2;
    }
    tourEl.style.left=Math.max(M,Math.min(left,window.innerWidth-w-M))+"px";
    tourEl.style.top=Math.max(M,Math.min(top,window.innerHeight-h-M))+"px";
  }

  // TWO clocks, and the split is not cosmetic. Positioning is about painting, so it rides
  // requestAnimationFrame -- the steps that ring a port on a card let the reader drag that card,
  // and a ring lagging the drag by a fifth of a second reads as a rendering bug.
  //
  // "Has this step been done yet?" is about the MODEL, and rAF is throttled to a standstill
  // whenever the browser decides this tab is not painting -- occluded, backgrounded, in a
  // window that lost focus. Measured here: one frame in half a second. A walkthrough whose
  // "waiting for a connection" never turned into "done" because the reader had another window
  // in front is exactly the kind of failure that reads as the tutorial being broken. So the
  // check gets a plain interval, which browsers merely SLOW in the background rather than stop.
  // The interval also re-places the card, as a 4Hz floor for when rAF is asleep.
  function tourLoop(){
    if(tourIdx<0){ tourRaf=null; return; }
    tourPlace();
    tourRaf=requestAnimationFrame(tourLoop);
  }
  function tourTick(){
    if(tourIdx<0) return;
    tourPlace(); tourCheck(false);
  }

  function tourStart(i){
    tourBuild();
    tourSaw={}; tourLastBox="";
    // A fresh run clears `done`, or a second pass through could never be resumed: the reopen
    // rule below reads `done` as "there is no run in progress", and leaving it set from the
    // FIRST time through meant closing halfway through the second always restarted from step 1.
    tourStore({done:false});
    document.addEventListener("click",tourWatchClicks,true);
    // Unhidden BEFORE the first tourGo: tourGo places the card off its own offsetHeight, and a
    // re-open measures 0 for a card still carrying [hidden] from the last close.
    tourEl.hidden=false; tourHalo.hidden=false;
    tourGo(i);
    // Focus the card ONCE, on open, and never again on a step change: most steps ask for a
    // click or a keystroke somewhere else on the page, and a panel that grabbed focus back
    // every time it advanced would make its own walkthrough impossible to follow. Step changes
    // are announced through the aria-live region instead.
    tourEl.focus();
    if(tourRaf===null) tourRaf=requestAnimationFrame(tourLoop);
    if(tourTimer===null) tourTimer=setInterval(tourTick,250);
    document.getElementById("tourBtn").setAttribute("aria-expanded","true");
  }
  function tourClose(){
    tourIdx=-1;
    document.removeEventListener("click",tourWatchClicks,true);
    if(tourRaf!==null){ cancelAnimationFrame(tourRaf); tourRaf=null; }
    if(tourTimer!==null){ clearInterval(tourTimer); tourTimer=null; }
    if(tourEl) tourEl.hidden=true;
    if(tourHalo) tourHalo.hidden=true;
    var b=document.getElementById("tourBtn");
    if(b){ b.setAttribute("aria-expanded","false"); b.focus(); }
  }
  (function(){
    var b=document.getElementById("tourBtn");
    b.setAttribute("aria-expanded","false");
    b.onclick=function(){
      if(tourIdx>=0){ tourStore({dismissed:true}); tourClose(); return; }
      var st=tourLoad();
      // Reopening resumes where you stopped, unless you finished -- in which case asking for it
      // again means you want it again, from the top.
      var at=(!st.done&&typeof st.step==="number"&&st.step>0&&st.step<TOUR.length)?st.step:0;
      tourStart(at);
    };
  })();

  addEventListener("beforeunload",function(e){
    if(!dirty) return;                  // clean since the last Commit: never nag
    // The autosave is debounced by 800ms, so a close landing inside that window would drop the
    // last edits even though autosave is working. Flush first -- localStorage is synchronous,
    // so this completes before the page goes.
    if(saveTimer) saveNow();
    // Only NOW is a prompt honest. With a working autosave the work is already in this browser
    // and the restore prompt offers it back on the next load, so a native "Leave site?" dialog
    // asks about a loss that cannot happen -- and it was the second native dialog stacked on
    // top of this page's own custom recovery modal. When autosave is dead (quota exceeded ->
    // storage=null, see saveNow), closing really does lose the work, and the nag is the point.
    if(storage) return;
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
      applyState(JSON.stringify(saved.project),true);   // a whole session coming back, view and all
      scrim.classList.remove("on");
    };
    document.getElementById("doDiscard").onclick=function(){
      try{ storage.removeItem(SAVE_KEY); }catch(e){}
      savedAt=null; scrim.classList.remove("on"); updateHistoryUI();
    };
  })();

  // A collapsed subsystem box has no x/y of its own -- it stands for N nodes and its position
  // is a VIEW, not model data. Place them once before the first paint, or they all stack at the
  // default corner. render() is called twice on purpose: the first pass is what gives
  // clusterLayout() rendered cards to MEASURE (nodeBox reads offsetWidth/offsetHeight).
  // A project.json that was rendered back into a page carries the arrangement it was saved with,
  // so apply it BEFORE the first paint -- level and the kind filter both change what render()
  // even draws, and re-laying-out first would just discard the positions on the way past.
  var bootCamera=restoreViewState();
  var bootSubPos=Object.keys(subPos).length>0;
  render();
  if(!bootSubPos) relayoutSubs();   // saved box positions are the author's; do not re-place them
  render();
  fillInspector();      // the idle inspector is the SYSTEM panel (fromFile, fromGitRepo), not
  updateHistoryUI();    // a placeholder, so it has to be painted before anything is selected
  // Open at 100% when the system fits, and only zoom OUT when it does not: a three-node
  // project blown up to fill the viewport looks like a rendering bug, and the author's mental
  // model of "actual size" is the one the drag handles work in.
  (function(){
    if(bootCamera) return;      // the project says where the reader was standing; respect it
    var b=contentBox(), pad=44, W=canvasWrap.clientWidth, H=canvasWrap.clientHeight;
    if(W<=0||H<=0) return;
    if(b.w+2*pad<=W&&b.h+2*pad<=H){ view.k=1; view.tx=pad-b.x; view.ty=pad-b.y; applyView(); }
    else fitView();
  })();
  // A real generation/validation error from the companion is the one status worth interrupting
  // arrival for: open the popover on load (page load has no interaction to lose) and pulse the
  // chip briefly so its location sticks -- dismissing it does NOT clear the red state, which
  // stays until the next render() replaces DATA.banner's condition.
  // Any companion banner opens on arrival, not just an error one. "Real-server validation did
  // NOT run" is a WARNING -- the files are written and the lint is clean -- but it is precisely
  // the message that must not be quiet, because the whole defect being fixed is that a
  // half-validated run looked exactly like a fully validated one.
  if(opNotice&&DATA.banner){
    var _sp2=document.getElementById("statusPop"), _sc2=document.getElementById("statusChip");
    if(_sp2&&_sp2.showPopover){
      try{ _sp2.showPopover(); }catch(e){}
      if(_sc2){ _sc2.classList.add("pulse"); setTimeout(function(){ _sc2.classList.remove("pulse"); },2600); }
    }
  }
  // The tutorial offers itself exactly once, and only in the one situation where there is
  // nothing to interrupt: a BLANK canvas, on a page that has nothing more urgent to say. A
  // walkthrough that opened over someone's forty-node system, or on top of the companion's
  // "real-server validation did NOT run" banner, would be the second thing competing for
  // attention at the moment the first one matters -- and the reason that banner opens on load
  // at all is that page load has no interaction to lose. It cannot have two owners.
  //
  // Closing it (the ✕, or reaching the end) records `dismissed`, so this is a one-shot offer
  // and never a thing that reappears. The Tutorial button in the toolbar is the way back.
  (function(){
    var tst=tourLoad();
    if(tst.done||tst.dismissed) return;
    if(DATA.banner) return;                                 // the companion has the floor
    if(document.querySelector(".scrim.on")) return;          // the autosave restore prompt is up
    if((project.nodes||[]).length) return;                   // not a first look; leave real work alone
    tourStart(0);
  })();
})();
</script>
</body>
</html>
'''
