#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_studio_common.py -- shared HTML/CSS/JS primitives + emit vocabulary for ros_plot.py (the
self-contained, read-only /ros-plot viewer) and ros_studio.py (the deterministic generation
and validation engine, imported directly by CoreSense Studio).

ros_plot.py is a single vanilla-JS document with no network access; its visual language (the
`:root` palette + seven interaction-kind colours), the SVG arrowhead markers, the bezier edge
path, the pointer-capture drag, the theme toggle and the deterministic grid layout live here
so a future second viewer could not drift from it. ros_studio.py's generator also reuses the
emit vocabulary that mirrors rosmodel_lint's constants (KIND_TO_BLOCK, TYPE_SEG_TO_ROS_BLOCK),
so the emitter and the checker can never disagree.

Nothing here imports the rest of the plugin, so it is safe for both scripts to import.
"""

# ----------------------------------------------------------------------------------------
# Interaction kinds (shared with rosmodel_lint.ARROW_KIND_ORDER; `param` is a viewer-only
# pseudo-kind for the parameter band / filter).
# ----------------------------------------------------------------------------------------
KIND_ORDER = ["pub", "sub", "ss", "sc", "as", "ac", "param"]
KIND_LABELS = {
    "pub": "Publisher", "sub": "Subscriber",
    "ss": "Service server", "sc": "Service client",
    "as": "Action server", "ac": "Action client",
    "param": "Parameter",
}

# .ros2 spec-block keyword per arrow kind (RosSystem/Ros2 grammar). One source of truth for
# both the emitter (kind -> block) and the seed parser (block -> kind).
KIND_TO_BLOCK = {
    "pub": "publishers", "sub": "subscribers",
    "ss": "serviceservers", "sc": "serviceclients",
    "as": "actionservers", "ac": "actionclients",
}
BLOCK_TO_KIND = {v: k for k, v in KIND_TO_BLOCK.items()}

# The `.msg`/`.srv`/`.action` middle segment -> the .ros spec block that defines it.
TYPE_SEG_TO_ROS_BLOCK = {"msg": "msgs", "srv": "srvs", "action": "actions"}


# ----------------------------------------------------------------------------------------
# A user's explicit light/dark choice (wireTheme, below) is persisted to localStorage --
# but reading it back inside wireTheme itself, which only runs from a <script> down in the
# BODY, would paint the page in the OS theme first and then visibly flip it. This runs
# synchronously in <head>, before the <style> block below is even parsed, so the
# data-theme attribute -- and therefore which half of PALETTE_CSS applies -- is already
# decided by the time anything paints. Shared here so a future second file://-origin page
# sharing this localStorage bucket would agree with /ros-plot rather than drift from it.
THEME_BOOT_JS = r"""try{
  var t=localStorage.getItem("rosStudio.theme");
  if(t==="light"||t==="dark") document.documentElement.setAttribute("data-theme",t);
}catch(e){}"""

# CSS: the shared palette. This is the exact `:root` block ros_plot has always shipped
# (light default + prefers-color-scheme dark + manual data-theme overrides), plus a couple
# of editor-only tokens (--glow, --dim) that are harmless in the viewer. Everything after
# this block in either page is layout-specific and stays with that page.
# ----------------------------------------------------------------------------------------
PALETTE_CSS = r"""  :root{
    --paper:#F2F5F4; --surface:#FBFCFC; --surface-2:#E8EDEB; --rule:#D2DAD7; --rule-soft:#E1E7E5;
    --ink:#101917; --ink-2:#3B4744; --ink-3:#66756F;
    --accent:#12806A; --accent-2:#0C5F4E; --accent-wash:#DCEDE7;
    --warn:#B4841F; --warn-wash:#F7EAD0; --dead:#A63A46; --dead-wash:#F5DEE0;
    --edge:#7E8F89; --edge-hot:#12806A; --glow:#12806A; --dim:.22;
    /* interaction-kind palette (light) */
    --k-pub:#12806A; --k-pub-bg:#DCEDE7;
    --k-sub:#37588C; --k-sub-bg:#D9E2F2;
    --k-ss:#B4841F;  --k-ss-bg:#F7EAD0;
    --k-sc:#8C5A2B;  --k-sc-bg:#F0E1D2;
    --k-as:#6E4BB0;  --k-as-bg:#E5DCF3;
    --k-ac:#A63A46;  --k-ac-bg:#F5DEE0;
    --k-param:#5E8069; --k-param-bg:#DDE8E0;
    /* origin-system palette (light): WHICH SOURCE .rossystem a node was merged or imported
       from. A different axis from the interaction kinds above -- a node has both -- so these
       are used as a card border + tint while the kinds stay on the ports, and the two never
       compete for the same pixel. Eight hues separated in the Okabe-Ito spirit: blue, orange,
       green, purple, magenta, gold, teal, slate. No pair of ADJACENT indices is a red/green
       pair, so the common colour-vision deficiencies never have to carry the distinction
       alone -- and the legend labels every colour with its system name regardless, because
       colour is the affordance here, never the only channel. */
    --s0:#1F5FA8; --s0-bg:#DEE9F7;
    --s1:#C2551A; --s1-bg:#F7E4D8;
    --s2:#3F7D20; --s2-bg:#E2EFDA;
    --s3:#7B4FA8; --s3-bg:#EBE1F5;
    --s4:#B0157F; --s4-bg:#F7DCEC;
    --s5:#8A6A00; --s5-bg:#F2EAD2;
    --s6:#00776E; --s6-bg:#D8EDEA;
    --s7:#5A6570; --s7-bg:#E4E8EB;
    --shadow:0 1px 2px rgba(16,25,23,.05),0 8px 24px -12px rgba(16,25,23,.18);
    --shadow-lift:0 2px 6px rgba(16,25,23,.10),0 14px 32px -14px rgba(16,25,23,.32);
    --display:"Palatino Linotype","Book Antiqua",Palatino,"Iowan Old Style",Georgia,serif;
    --body:"Segoe UI",system-ui,-apple-system,"Helvetica Neue",Arial,sans-serif;
    --mono:Consolas,"Cascadia Mono",ui-monospace,"SF Mono",Menlo,monospace;
    color-scheme: light dark;
  }
  @media (prefers-color-scheme: dark){ :root{
    --paper:#0E1414; --surface:#141C1B; --surface-2:#1B2523; --rule:#2A3835; --rule-soft:#212D2B;
    --ink:#E8EFEC; --ink-2:#B0BFBA; --ink-3:#7E8F89;
    --accent:#4FBFA1; --accent-2:#7FD6BE; --accent-wash:#15302A;
    --warn:#D9A94A; --warn-wash:#33290F; --dead:#D9707C; --dead-wash:#35181C;
    --edge:#6C7B76; --edge-hot:#4FBFA1; --glow:#4FBFA1;
    --k-pub:#4FBFA1; --k-pub-bg:#0A2A24;
    --k-sub:#7C9BD1; --k-sub-bg:#16233A;
    --k-ss:#D9A94A;  --k-ss-bg:#33290F;
    --k-sc:#C79362;  --k-sc-bg:#2E2214;
    --k-as:#A78BE0;  --k-as-bg:#241B39;
    --k-ac:#D9707C;  --k-ac-bg:#35181C;
    --k-param:#8FB39B; --k-param-bg:#17251D;
    --s0:#79ADE8; --s0-bg:#14243A;
    --s1:#E9976A; --s1-bg:#33200F;
    --s2:#93C97A; --s2-bg:#1B2A14;
    --s3:#B99BE0; --s3-bg:#241B39;
    --s4:#E48ABF; --s4-bg:#331428;
    --s5:#CBAE55; --s5-bg:#2E2710;
    --s6:#5FC0B4; --s6-bg:#0D2A27;
    --s7:#A3AEB8; --s7-bg:#1E252B;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -12px rgba(0,0,0,.7);
    --shadow-lift:0 2px 8px rgba(0,0,0,.5),0 16px 34px -14px rgba(0,0,0,.85);
  }}
  :root[data-theme="dark"]{
    --paper:#0E1414; --surface:#141C1B; --surface-2:#1B2523; --rule:#2A3835; --rule-soft:#212D2B;
    --ink:#E8EFEC; --ink-2:#B0BFBA; --ink-3:#7E8F89;
    --accent:#4FBFA1; --accent-2:#7FD6BE; --accent-wash:#15302A;
    --warn:#D9A94A; --warn-wash:#33290F; --dead:#D9707C; --dead-wash:#35181C;
    --edge:#6C7B76; --edge-hot:#4FBFA1; --glow:#4FBFA1;
    --k-pub:#4FBFA1; --k-pub-bg:#0A2A24; --k-sub:#7C9BD1; --k-sub-bg:#16233A;
    --k-ss:#D9A94A; --k-ss-bg:#33290F; --k-sc:#C79362; --k-sc-bg:#2E2214;
    --k-as:#A78BE0; --k-as-bg:#241B39; --k-ac:#D9707C; --k-ac-bg:#35181C;
    --k-param:#8FB39B; --k-param-bg:#17251D;
    --s0:#79ADE8; --s0-bg:#14243A;
    --s1:#E9976A; --s1-bg:#33200F;
    --s2:#93C97A; --s2-bg:#1B2A14;
    --s3:#B99BE0; --s3-bg:#241B39;
    --s4:#E48ABF; --s4-bg:#331428;
    --s5:#CBAE55; --s5-bg:#2E2710;
    --s6:#5FC0B4; --s6-bg:#0D2A27;
    --s7:#A3AEB8; --s7-bg:#1E252B;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 8px 24px -12px rgba(0,0,0,.7);
    --shadow-lift:0 2px 8px rgba(0,0,0,.5),0 16px 34px -14px rgba(0,0,0,.85);
  }
  :root[data-theme="light"]{
    --paper:#F2F5F4; --surface:#FBFCFC; --surface-2:#E8EDEB; --rule:#D2DAD7; --rule-soft:#E1E7E5;
    --ink:#101917; --ink-2:#3B4744; --ink-3:#66756F;
    --accent:#12806A; --accent-2:#0C5F4E; --accent-wash:#DCEDE7;
    --warn:#B4841F; --warn-wash:#F7EAD0; --dead:#A63A46; --dead-wash:#F5DEE0;
    --edge:#7E8F89; --edge-hot:#12806A; --glow:#12806A;
    --k-pub:#12806A; --k-pub-bg:#DCEDE7; --k-sub:#37588C; --k-sub-bg:#D9E2F2;
    --k-ss:#B4841F; --k-ss-bg:#F7EAD0; --k-sc:#8C5A2B; --k-sc-bg:#F0E1D2;
    --k-as:#6E4BB0; --k-as-bg:#E5DCF3; --k-ac:#A63A46; --k-ac-bg:#F5DEE0;
    --k-param:#5E8069; --k-param-bg:#DDE8E0;
    --s0:#1F5FA8; --s0-bg:#DEE9F7;
    --s1:#C2551A; --s1-bg:#F7E4D8;
    --s2:#3F7D20; --s2-bg:#E2EFDA;
    --s3:#7B4FA8; --s3-bg:#EBE1F5;
    --s4:#B0157F; --s4-bg:#F7DCEC;
    --s5:#8A6A00; --s5-bg:#F2EAD2;
    --s6:#00776E; --s6-bg:#D8EDEA;
    --s7:#5A6570; --s7-bg:#E4E8EB;
    --shadow:0 1px 2px rgba(16,25,23,.05),0 8px 24px -12px rgba(16,25,23,.18);
    --shadow-lift:0 2px 6px rgba(16,25,23,.10),0 14px 32px -14px rgba(16,25,23,.32);
  }"""


# ----------------------------------------------------------------------------------------
# JS: the shared primitive library. Injected once, at top level of each page's <script>
# (before that page's own IIFE), it defines a `STUDIO` global. The only namespace used is
# the SVG namespace URI -- the one allowed non-local reference in a self-contained page.
# ----------------------------------------------------------------------------------------
JS_PRIMITIVES = r"""var STUDIO = (function(){
  var NS = "http://www.w3.org/2000/svg";
  function el(tag, cls){ var e=document.createElement(tag); if(cls) e.className=cls; return e; }
  function svgEl(tag){ return document.createElementNS(NS, tag); }
  function txt(parent, cls, s){ var e=el("span",cls); e.textContent=s; parent.appendChild(e); return e; }
  function esc(s){ return (""+s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
  function cssEsc(s){ return (window.CSS&&CSS.escape)?CSS.escape(s):(""+s).replace(/["\\]/g,"\\$&"); }

  // Append the two edge markers (filled arrowhead + open chevron for the request<->response
  // back-arrow of services/actions) to an <svg>, id-suffixed so multiple graphs coexist.
  function makeArrowMarkers(svg, suffix){
    var defs=svgEl("defs");
    var mk=svgEl("marker");
    mk.setAttribute("id","ah"+suffix); mk.setAttribute("viewBox","0 0 10 10");
    mk.setAttribute("refX","9"); mk.setAttribute("refY","5");
    mk.setAttribute("markerWidth","7"); mk.setAttribute("markerHeight","7");
    mk.setAttribute("orient","auto-start-reverse");
    var mp=svgEl("path"); mp.setAttribute("d","M0,1 L9,5 L0,9 z"); mp.setAttribute("fill","context-stroke");
    mk.appendChild(mp); defs.appendChild(mk);
    var mo=svgEl("marker");
    mo.setAttribute("id","ahOpen"+suffix); mo.setAttribute("viewBox","0 0 10 10");
    mo.setAttribute("refX","1"); mo.setAttribute("refY","5");
    mo.setAttribute("markerWidth","7"); mo.setAttribute("markerHeight","7");
    mo.setAttribute("orient","auto-start-reverse");
    var op=svgEl("path"); op.setAttribute("d","M9,1 L1,5 L9,9"); op.setAttribute("fill","none");
    op.setAttribute("stroke","context-stroke"); op.setAttribute("stroke-width","1.6");
    mo.appendChild(op); defs.appendChild(mo);
    svg.insertBefore(defs, svg.firstChild);
    return {filled:"ah"+suffix, open:"ahOpen"+suffix};
  }

  // Cubic bezier "d" between two points, bowing horizontally by 40% of |dx| (min 40px).
  function bezier(x1,y1,x2,y2){
    var dx=x2-x1, off=Math.max(40, Math.abs(dx)*0.4);
    return "M"+x1+","+y1+" C"+(x1+off)+","+y1+" "+(x2-off)+","+y2+" "+x2+","+y2;
  }

  // Pointer-capture drag on `elm`. opts: getPos()->{x,y}, onStart(ev), onMove(x,y),
  // onEnd(wasClick,ev), clickThreshold (px, default 5). Distinguishes a click from a drag.
  function makeDraggable(elm, opts){
    var d=null;
    elm.addEventListener("pointerdown",function(ev){
      if(opts.filter && !opts.filter(ev)) return;
      var p=opts.getPos();
      d={px:ev.clientX,py:ev.clientY,ox:p.x,oy:p.y,moved:0};
      try{ elm.setPointerCapture(ev.pointerId); }catch(e){}
      if(opts.onStart) opts.onStart(ev);
    });
    elm.addEventListener("pointermove",function(ev){
      if(!d) return;
      var ddx=ev.clientX-d.px, ddy=ev.clientY-d.py;
      d.moved=Math.max(d.moved, Math.abs(ddx)+Math.abs(ddy));
      if(opts.onMove) opts.onMove(d.ox+ddx, d.oy+ddy);
    });
    elm.addEventListener("pointerup",function(ev){
      if(!d) return;
      var wasClick = d.moved < (opts.clickThreshold||5);
      d=null;
      try{ elm.releasePointerCapture(ev.pointerId); }catch(e){}
      if(opts.onEnd) opts.onEnd(wasClick, ev);
    });
  }

  // Manual light/dark toggle for a standalone file (no host stamps data-theme). THREE
  // states, not two, and persisted: auto (follows the OS) -> light -> dark -> auto -> ...
  // A plain two-way toggle plus persistence would opt the user OUT of "follow my OS"
  // permanently the moment they clicked once, with no way back short of clearing storage.
  // THEME_BOOT_JS (in <head>) is what makes an explicit choice actually stick on reload
  // without a flash of the wrong theme; this only owns the write half.
  function wireTheme(btn){
    var root=document.documentElement;
    btn.addEventListener("click",function(){
      var cur=root.getAttribute("data-theme");
      var next=cur==="light"?"dark":(cur==="dark"?null:"light");
      if(next) root.setAttribute("data-theme",next); else root.removeAttribute("data-theme");
      try{ if(next) localStorage.setItem("rosStudio.theme",next); else localStorage.removeItem("rosStudio.theme"); }catch(e){}
    });
  }

  // Deterministic near-square grid. Returns n positions {x,y} left-to-right, top-to-bottom.
  function gridPositions(n, o){
    o=o||{};
    var padx=o.padx!=null?o.padx:30, pady=o.pady!=null?o.pady:40;
    var nw=o.nw!=null?o.nw:196, gapx=o.gapx!=null?o.gapx:64;
    var rowh=o.rowh!=null?o.rowh:220, gapy=o.gapy!=null?o.gapy:52;
    var cols=Math.max(1, Math.ceil(Math.sqrt(Math.max(1,n))));
    var out=[];
    for(var i=0;i<n;i++){
      var c=i%cols, r=Math.floor(i/cols);
      out.push({x:padx+c*(nw+gapx), y:pady+r*(rowh+gapy)});
    }
    return out;
  }

  return {NS:NS, el:el, svgEl:svgEl, txt:txt, esc:esc, cssEsc:cssEsc,
          makeArrowMarkers:makeArrowMarkers, bezier:bezier,
          makeDraggable:makeDraggable, wireTheme:wireTheme, gridPositions:gridPositions};
})();"""


# ----------------------------------------------------------------------------------------
# Emit vocabulary (Python side). Kept here so ros_studio's generator reads one table; the
# authoritative grammar constants still live in rosmodel_lint and ros_studio imports those
# too (ARROW_FROM_TO, ARROW_KIND_ORDER, RE_NEEDS_QUOTING, PARAM_TYPES_*). This module only
# adds the block/type mappings above and the two quoting helpers below, which delegate to
# the linter's regex when it is importable.
# ----------------------------------------------------------------------------------------

def needs_quoting(name, needs_quoting_re=None):
    """A name needs quoting when it contains a char Xtext's ID terminal forbids
    (`.` `/` `::` `-` whitespace) or is empty. `needs_quoting_re` is
    rosmodel_lint.RE_NEEDS_QUOTING when available; a conservative fallback is used
    otherwise so this module never hard-depends on the linter."""
    if needs_quoting_re is not None:
        return bool(name == "" or needs_quoting_re.search(name))
    import re as _re
    return bool(_re.search(r"[./:\-\s]|^$", name))


def quote(name, double=True, needs_quoting_re=None):
    """Quote `name` for emission, escaping embedded quotes/backslashes. Backslash escaping in
    a double-quoted scalar (\\\\, \\") is accepted by both the YAML composer and the Xtext
    STRING terminal. A single quote or backslash inside a would-be single-quoted scalar forces
    the double-quoted form, because YAML's '' doubling and Xtext's \\' escaping are mutually
    incompatible in single quotes."""
    s = str(name)
    if not double and ("'" in s or "\\" in s):
        double = True
    if double:
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return "'" + s + "'"
