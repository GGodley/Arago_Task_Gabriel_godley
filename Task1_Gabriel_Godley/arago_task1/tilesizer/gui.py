"""The simple interface: a local page in your web browser.

    python TileSizer.py          (or double-click the launcher for your system)

It starts a small web server on this computer only (127.0.0.1) and opens the page.
Nothing is sent over the internet. On the page you:
    1. give the matrix dimensions, pick an example trace, or upload your own trace
    2. choose the optimisation: speed or hardware
    3. press Run
The page then shows the ticks taken, the hardware used and the graphs, and every
file is saved in results/run_NNN/. Close the terminal window to stop the server.
"""

from __future__ import annotations

import http.server
import json
import mimetypes
import os
import re
import socket
import subprocess
import sys
import threading
import traceback
import webbrowser
from pathlib import Path
from urllib.parse import unquote, urlparse

from .run import OPTIMISATIONS, RESULTS, ROOT, run

EXAMPLES = ROOT / "example" / "traces"
UPLOADS = RESULTS / "uploads"
_lock = threading.Lock()  # one run at a time, so run numbers stay in order


def _examples() -> list[str]:
    return sorted((p.name for p in EXAMPLES.iterdir() if p.suffix in (".csv", ".json")),
                  key=lambda s: (len(s), s)) if EXAMPLES.exists() else []


def _open_folder(path: Path) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the terminal for run messages
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def do_GET(self):  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path in ("/", "/index.html"):
            return self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        if path == "/examples":
            return self._json({"examples": _examples(), "results": str(RESULTS)})
        if path.startswith("/results/"):
            f = (RESULTS / path[len("/results/"):]).resolve()
            if RESULTS.resolve() in f.parents and f.is_file():
                return self._send(200, f.read_bytes(), mimetypes.guess_type(f.name)[0] or "application/octet-stream")
        self._send(404, b"not found", "text/plain")

    def do_POST(self):  # noqa: N802
        path = urlparse(self.path).path
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            if path == "/run":
                return self._json(self._run(req))
            if path == "/open":
                folder = RESULTS / req.get("run", "")
                _open_folder(folder if folder.is_dir() else RESULTS)
                return self._json({"ok": True})
        except Exception as e:  # shown on the page, in plain words
            traceback.print_exc()
            return self._json({"error": str(e) or e.__class__.__name__}, 400)
        self._send(404, b"not found", "text/plain")

    def _run(self, req: dict) -> dict:
        opt = req.get("opt", "target")
        mode = req.get("mode", "dims")
        dims = trace = None
        if mode == "dims":
            dims = [int(req["dims"][i]) for i in range(3)]
        elif mode == "example":
            name = Path(req["example"]).name
            trace = EXAMPLES / name
            if not trace.is_file():
                raise ValueError(f"no example trace called {name}")
        elif mode == "upload":
            name = re.sub(r"[^A-Za-z0-9_.-]", "_", Path(req.get("trace_name") or "trace.csv").name)
            if not name.lower().endswith((".csv", ".json")):
                raise ValueError("a trace must be a .csv or .json file")
            UPLOADS.mkdir(parents=True, exist_ok=True)
            trace = UPLOADS / name
            trace.write_text(req.get("trace_text", ""))
        else:
            raise ValueError(f"unknown input {mode}")
        with _lock:
            return run(dims=dims, trace=trace, opt=opt)


def _free_port(start: int = 8765) -> int:
    for port in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit("no free port between 8765 and 8815")


def main(open_browser: bool = True, port: int | None = None) -> None:
    port = port or _free_port()
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print("Tile Sizer is running.")
    print(f"  Page:     {url}  (opens in your browser; paste it there if it does not)")
    print(f"  Results:  {RESULTS}{os.sep}run_NNN")
    print("  To stop:  close this window (or press Ctrl+C).\n")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("stopped")


_OPT_LABELS = {
    "target": ("Timing target", "Fewest units that meet the fast target (the report's rule; 8/20/256 for 2048^3)"),
    "speed": ("Speed", "Fastest the work allows (preset max, compact memory)"),
    "hw": ("Hardware", "Least hardware that runs it (preset steady, tiny memory)"),
}
OPT_HTML = "".join(
    f'<label class="opt"><input type="radio" name="opt" value="{k}"{" checked" if k == "target" else ""}>'
    f"<span><b>{_OPT_LABELS[k][0]}</b><small>{_OPT_LABELS[k][1]}</small></span></label>"
    for k in OPTIMISATIONS)

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tile Sizer</title>
<style>
:root{--bg:#fcfcfb;--card:#fff;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--accent:#2a78d6;--err:#c0392b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1000px;margin:0 auto;padding:24px 16px 60px}h1{font-size:24px;margin:0 0 4px}p.sub{color:var(--ink2);margin:0 0 20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px;margin-bottom:16px}
h2{font-size:15px;margin:0 0 12px;text-transform:uppercase;letter-spacing:.04em;color:var(--ink2)}
.tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}.tabs button{border:1px solid var(--line);background:#f4f3f0;border-radius:6px;padding:6px 12px;cursor:pointer;font:inherit}
.tabs button.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:end}label.f{display:flex;flex-direction:column;font-size:13px;color:var(--ink2)}
input[type=number],select{font:inherit;padding:6px 8px;border:1px solid var(--line);border-radius:6px;width:120px}select{width:260px}
.opt{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--line);border-radius:8px;padding:10px 12px;cursor:pointer;flex:1;min-width:240px}
.opt small{display:block;color:var(--ink2)}.opts{display:flex;gap:10px;flex-wrap:wrap}
button.run{background:var(--accent);color:#fff;border:0;border-radius:8px;padding:10px 26px;font:inherit;font-weight:600;cursor:pointer}
button.run:disabled{opacity:.5;cursor:wait}button.link{background:none;border:1px solid var(--line);border-radius:8px;padding:8px 14px;cursor:pointer;font:inherit}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin:6px 0 14px}
.stat{border:1px solid var(--line);border-radius:8px;padding:10px 12px}.stat b{display:block;font-size:22px}.stat span{color:var(--ink2);font-size:13px}
pre{background:#f4f3f0;padding:12px;border-radius:8px;overflow:auto;font-size:13px}img{max-width:100%;border:1px solid var(--line);border-radius:6px;margin:6px 0 14px}
.err{color:var(--err);font-weight:600}.hidden{display:none}.muted{color:var(--ink2);font-size:13px}
</style></head><body><main>
<h1>Tile Sizer</h1>
<p class="sub">Performance model and hardware optimiser for a 64 &times; 64 tiled matmul on DMA units, matrix units and local memory.</p>

<div class="card"><h2>1. Workload</h2>
<div class="tabs"><button data-m="dims" class="on">Matrix dimensions</button><button data-m="example">Example trace</button><button data-m="upload">Upload a trace</button></div>
<div id="m-dims" class="row">
 <label class="f">M (rows of A)<input id="M" type="number" min="1" value="512"></label>
 <label class="f">K (shared)<input id="K" type="number" min="1" value="512"></label>
 <label class="f">N (columns of B)<input id="N" type="number" min="1" value="512"></label>
 <span class="muted">C (M&times;N) = A (M&times;K) &times; B (K&times;N)</span></div>
<div id="m-example" class="row hidden"><label class="f">Trace in the example folder<select id="ex"></select></label></div>
<div id="m-upload" class="row hidden"><label class="f">Trace file (.csv or .json)<input id="file" type="file" accept=".csv,.json"></label></div>
</div>

<div class="card"><h2>2. Optimisation</h2><div class="opts">__OPTS__</div></div>

<div class="row" style="margin-bottom:16px"><button class="run" id="go">Run</button><span id="status" class="muted"></span></div>

<div id="out" class="card hidden"><h2 id="runname">Result</h2>
<div class="stats" id="stats"></div>
<div class="row" style="margin-bottom:10px"><button class="link" id="openf">Open the results folder</button><span class="muted" id="where"></span></div>
<pre id="summary"></pre><div id="imgs"></div></div>
</main>
<script>
let mode="dims",last=null;
const $=id=>document.getElementById(id);
document.querySelectorAll(".tabs button").forEach(b=>b.onclick=()=>{mode=b.dataset.m;
 document.querySelectorAll(".tabs button").forEach(x=>x.classList.toggle("on",x===b));
 ["dims","example","upload"].forEach(m=>$("m-"+m).classList.toggle("hidden",m!==mode));});
fetch("/examples").then(r=>r.json()).then(j=>{$("ex").innerHTML=j.examples.map(e=>`<option>${e}</option>`).join("");
 const d=j.examples.indexOf("mm_512x512x512.json");if(d>=0)$("ex").selectedIndex=d;});
const fmt=n=>Number(n).toLocaleString();
$("go").onclick=async()=>{
 const req={mode,opt:document.querySelector("input[name=opt]:checked").value};
 if(mode==="dims")req.dims=["M","K","N"].map(i=>parseInt($(i).value,10));
 if(mode==="example")req.example=$("ex").value;
 if(mode==="upload"){const f=$("file").files[0];if(!f){$("status").innerHTML='<span class="err">Choose a trace file first.</span>';return;}
  req.trace_name=f.name;req.trace_text=await f.text();}
 $("go").disabled=true;$("status").textContent="Running the model and drawing the graphs (about 10 seconds)...";
 try{const r=await fetch("/run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(req)});
  const j=await r.json();if(j.error)throw new Error(j.error);last=j;show(j);$("status").textContent="";}
 catch(e){$("status").innerHTML='<span class="err">'+e.message+'</span>';}
 finally{$("go").disabled=false;}};
function show(j){const h=j.hardware;$("out").classList.remove("hidden");
 $("runname").textContent=`Result: ${j.run}`;
 $("stats").innerHTML=[[fmt(j.ticks),"ticks taken"],[fmt(j.cycles),"cycles (1 tick = 128)"],[h.Nd,"DMA units"],[fmt(h.Nm),"matrix units"],[fmt(h.S),"tiles of local memory"],[j.limiter,"limited by"]]
  .map(([v,l])=>`<div class="stat"><b>${v}</b><span>${l}</span></div>`).join("");
 $("where").textContent="Saved in "+j.folder;$("summary").textContent=j.summary;
 $("imgs").innerHTML=j.files.filter(f=>f.endsWith(".png")).map(f=>`<div class="muted">${f}</div><img src="/results/${j.run}/${f}?t=${Date.now()}" alt="${f}">`).join("");
 $("out").scrollIntoView({behavior:"smooth"});}
$("openf").onclick=()=>fetch("/open",{method:"POST",body:JSON.stringify({run:last?last.run:""})});
</script></body></html>""".replace("__OPTS__", OPT_HTML)
