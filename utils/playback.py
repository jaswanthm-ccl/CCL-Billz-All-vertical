"""Live playback control for headed Playwright runs.

Gated behind env PLAYBACK_UI=1. Injects a fixed control bar into every page
and auto-wraps Playwright action methods so each action honors pause / speed /
step. Buttons talk to the driver via window.__pbPending (polled) — no network,
so it works on https staging without mixed-content blocking.

NOTE: live "rewind" is impossible (actions mutate app state). The history
panel is view-only navigation, not state rollback. Use Trace Viewer for true
post-run rewind.
"""
from __future__ import annotations

import os
import threading
import time

from playwright.sync_api import Browser


class PlaybackControl:
    def __init__(self) -> None:
        self.delay = 0.0          # seconds to wait before each action
        self.paused = False
        self.step_mode = False     # block before each action until "next"
        self.history: list[str] = []
        self.cursor = -1
        self.test_name = ""
        self._local = threading.local()
        self._step = threading.Event()
        self._lock = threading.Lock()
        self._patched = False

    # -- command handling -------------------------------------------------
    def _apply(self, cmd: str) -> None:
        if cmd == "pause":
            self.paused = True
        elif cmd == "resume":
            self.paused = False
            self._step.set()
        elif cmd == "slow":
            self.delay = min(self.delay + 0.5, 5.0)
        elif cmd == "fast":
            self.delay = max(self.delay - 0.5, 0.0)
        elif cmd == "run":
            self.paused = False
            self.step_mode = False
            self.delay = 0.0
            self._step.set()
        elif cmd == "step":
            self.step_mode = True
            self.paused = True
        elif cmd == "next":
            self._step.set()
        elif cmd == "prev":
            with self._lock:
                self.cursor = max(0, self.cursor - 1)
        elif cmd == "nexth":
            with self._lock:
                self.cursor = min(len(self.history) - 1, self.cursor + 1)

    def _drain_pending(self, page) -> None:
        try:
            cmd = page.evaluate(
                "() => { const v = window.__pbPending; window.__pbPending = null; return v; }"
            )
        except Exception:
            return
        if cmd:
            self._apply(cmd)

    def _status(self) -> str:
        if self.paused:
            return "PAUSED"
        if self.step_mode:
            return "STEP"
        return "RUNNING"

    def _push(self, label: str) -> None:
        with self._lock:
            self.history.append(label)
            self.cursor = len(self.history) - 1

    def before_action(self, page, label: str) -> None:
        self._push(label)
        if self.step_mode:
            self._step.wait()
            self._step.clear()
        while self.paused:
            self._drain_pending(page)
            self._update(page, label)
            time.sleep(0.1)
        self._drain_pending(page)
        if self.delay > 0:
            try:
                page.wait_for_timeout(int(self.delay * 1000))
            except Exception:
                time.sleep(self.delay)
        self._update(page, label)

    def _update(self, page, label: str = "") -> None:
        try:
            with self._lock:
                hist = list(self.history[-60:])
                cursor = self.cursor
                test_name = self.test_name
            page.evaluate(
                "(a) => window.__pbUpdate && window.__pbUpdate(a.status, a.speed, a.hist, a.cursor, a.label, a.test_name)",
                {"status": self._status(), "speed": f"{self.delay:.1f}s",
                 "hist": hist, "cursor": cursor, "label": label, "test_name": test_name},
            )
        except Exception:
            pass

    # -- overlay ----------------------------------------------------------
    def overlay_script(self) -> str:
        return (
            "(function(){"
            "if (window.__pbReady) return; window.__pbReady = true;"
            "var PENDING=null;"
            "window.__pbPending=null;"
            "function cmd(c){ window.__pbPending=c; if(window.__pbUpdate) window.__pbUpdate(); }"
            
            # Outer draggable container
            "var bar=document.createElement('div');"
            "bar.id='playback-panel';"
            "bar.style.cssText='position:fixed;width:350px;z-index:2147483647;"
            "background:rgba(17,26,34,0.95);color:#0f0;font:12px monospace;border:1px solid #333;"
            "border-radius:8px;box-shadow:0 4px 16px rgba(0,0,0,0.5);backdrop-filter:blur(4px);"
            "display:flex;flex-direction:column;overflow:hidden;box-sizing:border-box;';"
            "var savedLeft=sessionStorage.getItem('pb-left');"
            "var savedTop=sessionStorage.getItem('pb-top');"
            "if(savedLeft && savedTop){"
            "  bar.style.left=savedLeft; bar.style.top=savedTop;"
            "}else{"
            "  bar.style.bottom='20px'; bar.style.left='20px';"
            "}"
            
            # Drag handle header
            "var header=document.createElement('div');"
            "header.style.cssText='background:#222;padding:8px 12px;cursor:move;display:flex;"
            "justify-content:space-between;align-items:center;border-bottom:1px solid #333;"
            "user-select:none;box-sizing:border-box;';"
            "header.innerHTML=\"<b style='color:#ff0;margin-right:4px;'>PLAYBACK</b>"
            "<span id='pb-title' style='color:#ffeb3b;font-weight:bold;font-size:11px;"
            "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:240px;'></span>\";"
            "bar.appendChild(header);"
            
            # Panel body
            "var body=document.createElement('div');"
            "body.style.cssText='padding:10px;display:flex;flex-direction:column;gap:8px;box-sizing:border-box;';"
            "bar.appendChild(body);"
            
            # Status and Speed info
            "var infoRow=document.createElement('div');"
            "infoRow.style.cssText='display:flex;justify-content:space-between;font-size:11px;color:#aaa;box-sizing:border-box;';"
            "infoRow.innerHTML=\"<span>Status: <span id='pb-status' style='color:#0ff;font-weight:bold;'>RUNNING</span></span>"
            "<span>Speed: <span id='pb-speed' style='color:#0f0;'>0.0s</span></span>\";"
            "body.appendChild(infoRow);"
            
            # Controls button grid
            "var controls=document.createElement('div');"
            "controls.style.cssText='display:flex;flex-wrap:wrap;gap:4px;box-sizing:border-box;';"
            "body.appendChild(controls);"
            
            "function B(t,c){"
            "  var b=document.createElement('button');b.textContent=t;"
            "  b.style.cssText='cursor:pointer;background:#222;color:#0f0;border:1px solid #0f0;"
            "  border-radius:4px;padding:3px 8px;font-size:11px;font-family:monospace;"
            "  flex:1 1 auto;text-align:center;box-sizing:border-box;';"
            "  b.onclick=function(){cmd(c)};"
            "  controls.appendChild(b);return b;"
            "}"
            "B('Pause','pause');B('Resume','resume');B('Step','step');B('Next ▶','next');"
            "B('🐢 Slow','slow');B('⚡ Fast','fast');B('▶▶ Run','run');"
            
            # Navigation & History row
            "var navRow=document.createElement('div');"
            "navRow.style.cssText='display:flex;gap:4px;box-sizing:border-box;';"
            "body.appendChild(navRow);"
            
            "function B2(t,c,parent){"
            "  var b=document.createElement('button');b.textContent=t;"
            "  b.style.cssText='cursor:pointer;background:#222;color:#0f0;border:1px solid #0f0;"
            "  border-radius:4px;padding:3px 8px;font-size:11px;font-family:monospace;"
            "  flex:1;text-align:center;box-sizing:border-box;';"
            "  b.onclick=function(){cmd(c)};"
            "  parent.appendChild(b);return b;"
            "}"
            "B2('◀ Prev','prev',navRow);B2('Next ▶','nexth',navRow);"
            
            # History log list
            "var hist=document.createElement('div');hist.id='pb-hist';"
            "hist.style.cssText='max-height:150px;overflow:auto;background:#000d;color:#aaa;"
            "font:10px monospace;border-top:1px solid #333;padding:6px;display:none;box-sizing:border-box;';"
            "bar.appendChild(hist);"
            
            # History toggle button
            "var ht=document.createElement('button');ht.textContent='History';"
            "ht.style.cssText='cursor:pointer;background:#222;color:#0f0;border:1px solid #0f0;"
            "border-radius:4px;padding:3px 8px;font-size:11px;font-family:monospace;"
            "flex:1;text-align:center;box-sizing:border-box;';"
            "ht.onclick=function(){hist.style.display=hist.style.display==='none'?'block':'none'};"
            "navRow.appendChild(ht);"
            
            # Dragging mechanics
            "var isDragging=false;var startX,startY,initialLeft,initialTop;"
            "header.addEventListener('mousedown',function(e){"
            "  if(e.target.tagName==='BUTTON')return;"
            "  isDragging=true;startX=e.clientX;startY=e.clientY;"
            "  var rect=bar.getBoundingClientRect();"
            "  initialLeft=rect.left;initialTop=rect.top;"
            "  bar.style.right='auto';bar.style.bottom='auto';"
            "  bar.style.left=initialLeft+'px';bar.style.top=initialTop+'px';"
            "  document.addEventListener('mousemove',dragMove);"
            "  document.addEventListener('mouseup',dragEnd);"
            "});"
            "function dragMove(e){"
            "  if(!isDragging)return;"
            "  var dx=e.clientX-startX;var dy=e.clientY-startY;"
            "  bar.style.left=(initialLeft+dx)+'px';bar.style.top=(initialTop+dy)+'px';"
            "}"
            "function dragEnd(){"
            "  isDragging=false;"
            "  document.removeEventListener('mousemove',dragMove);"
            "  document.removeEventListener('mouseup',dragEnd);"
            "  sessionStorage.setItem('pb-left',bar.style.left);"
            "  sessionStorage.setItem('pb-top',bar.style.top);"
            "}"
            
            # Updates hook
            "window.__pbUpdate=function(st,sp,h,c,l,t){"
            "  if(t!==undefined){"
            "    var el=document.getElementById('pb-title');"
            "    if(el) el.textContent=' - '+t;"
            "  }"
            "  var statusEl=document.getElementById('pb-status');"
            "  if(statusEl) statusEl.textContent=st||'';"
            "  var speedEl=document.getElementById('pb-speed');"
            "  if(speedEl) speedEl.textContent=sp||'';"
            "  var histEl=document.getElementById('pb-hist');"
            "  if(h && histEl){var html='';for(var i=0;i<h.length;i++){var line=(i+1)+'. '+(h[i]||'');"
            "    if(i===c){html+='<div style=\"color:#ff0;background:#222;padding:2px 4px;\">▶ '+line+'</div>';}"
            "    else{html+='<div style=\"padding:2px 4px;\">'+line+'</div>';}}"
            "    histEl.innerHTML=html;"
            "    histEl.scrollTop=histEl.scrollHeight;"
            "  }"
            "};"
            
            # Safe initialization with MutationObserver
            "function initPlaybackPanel(){"
            "  if(document.getElementById('playback-panel')) return;"
            "  if(!document.body){"
            "    document.addEventListener('DOMContentLoaded', initPlaybackPanel);"
            "    return;"
            "  }"
            "  document.body.appendChild(bar);"
            "  window.__pbUpdate();"
            "  var observer=new MutationObserver(function(mutations){"
            "    if(!document.getElementById('playback-panel') && document.body){"
            "      document.body.appendChild(bar);"
            "    }"
            "  });"
            "  observer.observe(document.documentElement,{childList:true,subtree:true});"
            "}"
            "initPlaybackPanel();"
            "})();"
        )

    # -- install ----------------------------------------------------------
    def start(self) -> None:
        if self._patched:
            return
        self._patch_api()
        self._patched = True

    def stop(self) -> None:
        self.paused = False
        self.step_mode = False

    def _patch_api(self) -> None:
        from playwright.sync_api import Locator, Page, Frame  # noqa

        targets = [Locator, Page, Frame]
        methods = [
            "click", "dblclick", "fill", "press", "check", "uncheck",
            "select_option", "hover", "focus", "type", "press_sequentially",
            "drag_to", "set_checked", "scroll_into_view_if_needed", "goto",
            "wait_for",
        ]

        def _page_of(obj):
            for attr in ("page", "_page", "_frame"):
                v = getattr(obj, attr, None)
                if v is not None:
                    if hasattr(v, "page"):
                        return v.page
                    return v
            return None

        for cls in targets:
            for m in methods:
                orig = getattr(cls, m, None)
                if orig is None:
                    continue

                def maker(orig, m):
                    def patched(self, *args, **kwargs):
                        # Re-entry guard to prevent recursion if a patched method internally calls another
                        if getattr(playback._local, "in_action", False):
                            return orig(self, *args, **kwargs)
                        
                        playback._local.in_action = True
                        try:
                            page = _page_of(self)
                            label = m
                            sel = getattr(self, "_selector", None)
                            if sel:
                                label = f"{m} {sel}"
                            if page is not None:
                                playback.before_action(page, label)
                            return orig(self, *args, **kwargs)
                        finally:
                            playback._local.in_action = False
                    return patched

                try:
                    setattr(cls, m, maker(orig, m))
                except Exception:
                    pass

        # Inject overlay into every new context automatically.
        orig_nc = Browser.new_context

        def patched_nc(self, *args, **kwargs):
            ctx = orig_nc(self, *args, **kwargs)
            try:
                ctx.add_init_script(playback.overlay_script())
                
                # Listen to page creation and bind load event listeners to auto-update the overlay state
                def on_page(p):
                    p.on("domcontentloaded", lambda page: playback._update(page))
                    p.on("load", lambda page: playback._update(page))
                ctx.on("page", on_page)
            except Exception:
                pass
            return ctx

        Browser.new_context = patched_nc


playback = PlaybackControl()
