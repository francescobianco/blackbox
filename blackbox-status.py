#!/usr/bin/env python3
# Blackbox status panel: read-only, shows disk power state and usage of every user's Blackbox.
# Runs as root (CHECK POWER MODE needs it). Never touches the disks: hdparm -C does not
# spin them up, statvfs reads in-memory counters.
import glob, json, os, re, subprocess, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.environ.get('BLACKBOX_STATUS_PORT', 6680))
activity = {}  # disk -> (diskstats io counters, time they last changed)


def users():
    for env in sorted(glob.glob('/etc/blackbox/users/*/env')):
        conf = dict(re.findall(r'^(\w+)="?(.*?)"?$', open(env).read(), re.M))
        share = open(os.path.dirname(env) + '/share.conf').readline().strip().strip('[]')
        yield os.path.basename(os.path.dirname(env)), share, conf.get('BLACKBOX_DIR', '')


def disk_of(path):
    src = subprocess.run(['findmnt', '-nvo', 'SOURCE', '-T', path], capture_output=True, text=True).stdout.strip()
    parent = subprocess.run(['lsblk', '-ndo', 'PKNAME', src], capture_output=True, text=True).stdout.strip()
    return parent or os.path.basename(src)


def disk_info(disk):
    out = subprocess.run(['hdparm', '-C', '/dev/' + disk], capture_output=True, text=True).stdout
    state = out.rsplit(':', 1)[-1].strip() if 'drive state' in out else 'unknown'
    io = None
    for line in open('/proc/diskstats'):
        f = line.split()
        if f[2] == disk:
            io = (f[3], f[7])  # reads and writes completed
    now = time.time()
    if disk not in activity or activity[disk][0] != io:
        activity[disk] = (io, now)
    model = open(f'/sys/block/{disk}/device/model').read().strip() if os.path.exists(f'/sys/block/{disk}/device/model') else ''
    rotational = open(f'/sys/block/{disk}/queue/rotational').read().strip() == '1'
    return {'disk': disk, 'model': model, 'rotational': rotational, 'state': state,
            'standby': state == 'standby', 'quiet_seconds': int(now - activity[disk][1])}


def status():
    shares, disks = [], {}
    for user, share, path in users():
        if not os.path.isdir(path):
            shares.append({'user': user, 'share': share, 'path': path, 'error': 'missing'})
            continue
        st = os.statvfs(path)
        disk = disk_of(path)
        disks.setdefault(disk, None)
        shares.append({'user': user, 'share': share, 'path': path, 'disk': disk,
                       'size': st.f_blocks * st.f_frsize, 'free': st.f_bavail * st.f_frsize,
                       'used': (st.f_blocks - st.f_bfree) * st.f_frsize})
    return {'host': os.uname().nodename, 'time': int(time.time()),
            'disks': [disk_info(d) for d in disks], 'shares': shares}


PAGE = '''<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Blackbox status</title>
<style>
:root{--bg:#fafaf9;--fg:#1c1917;--mute:#78716c;--card:#fff;--line:#e7e5e4;--ok:#15803d;--warn:#b45309;--bar:#57534e}
@media (prefers-color-scheme:dark){:root{--bg:#1c1917;--fg:#f5f5f4;--mute:#a8a29e;--card:#292524;--line:#44403c;--ok:#4ade80;--warn:#fbbf24;--bar:#d6d3d1}}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif}
main{max-width:640px;margin:0 auto;padding:24px 16px}h1{font-size:20px;margin:0 0 4px}
.mute{color:var(--mute);font-size:13px}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.row{display:flex;justify-content:space-between;gap:12px;align-items:baseline}.state{font-weight:600}
.standby{color:var(--ok)}.active{color:var(--warn)}.bar{height:8px;background:var(--line);border-radius:4px;overflow:hidden;margin:8px 0 4px}
.bar i{display:block;height:100%;background:var(--bar)}
</style></head><body><main><h1 id="host">Blackbox</h1><div class="mute" id="upd">&nbsp;</div>
<h2 class="mute">Dischi</h2><div id="disks"></div><h2 class="mute">Spazio</h2><div id="shares"></div></main>
<script>
const gb=b=>(b/1e9).toFixed(b<1e10?1:0)+' GB',dur=s=>s<60?s+' s':s<3600?Math.floor(s/60)+' min':Math.floor(s/3600)+' h '+Math.floor(s%3600/60)+' min';
async function tick(){try{const s=await(await fetch('status.json',{cache:'no-store'})).json();
host.textContent=s.host;upd.textContent='Aggiornato '+new Date(s.time*1000).toLocaleTimeString();
disks.innerHTML=s.disks.map(d=>`<div class="card"><div class="row"><b>${d.disk} <span class="mute">${d.model}</span></b>
<span class="state ${d.standby?'standby':'active'}">${d.standby?'In standby (fermo)':'Attivo ('+d.state+')'}</span></div>
<div class="mute">Nessun accesso da ${dur(d.quiet_seconds)}</div></div>`).join('');
shares.innerHTML=s.shares.map(x=>x.error?`<div class="card"><b>${x.share}</b> <span class="mute">${x.path}: cartella mancante</span></div>`:
`<div class="card"><div class="row"><b>${x.share}</b><span class="mute">${x.path}</span></div>
<div class="bar"><i style="width:${(100*x.used/x.size).toFixed(1)}%"></i></div>
<div class="row mute"><span>${gb(x.used)} usati di ${gb(x.size)}</span><span>${gb(x.free)} liberi</span></div></div>`).join('');
}catch(e){upd.textContent='Non raggiungibile'}}
tick();setInterval(tick,2000);
</script></body></html>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            body, kind = PAGE.encode(), 'text/html; charset=utf-8'
        elif self.path == '/status.json':
            body, kind = json.dumps(status()).encode(), 'application/json'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


ThreadingHTTPServer(('', PORT), Handler).serve_forever()
