#!/usr/bin/env python3
"""Local-network prompt bridge. Printing stays in the original AppleScript."""
import socketserver
import http.server, json, os, secrets, subprocess, sys, threading, time, urllib.parse
from pathlib import Path
STATE = Path.home() / 'Library/Application Support/HP117wMobile'
PORT = 8717

def write(name, value):
    tmp = STATE / (name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False))
    os.replace(tmp, STATE / name)

def read(name, default=None):
    try: return json.loads((STATE / name).read_text())
    except (FileNotFoundError, ValueError): return default

PAGE = r"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Duplex Print"><title>HP 117w Mobile Control</title>
<style>body{font:17px -apple-system,sans-serif;background:#f2f5f8;color:#182635;margin:0;padding:24px}main{max-width:560px;margin:auto}h1{font-size:27px}section{background:white;padding:24px;border-radius:20px;box-shadow:0 6px 30px #1726350b}#message{white-space:pre-wrap;line-height:1.65;overflow-wrap:anywhere}button,textarea{font:inherit;box-sizing:border-box;width:100%;padding:16px;border-radius:12px;margin-top:12px}button{background:#1265da;color:white;border:0;cursor:pointer}button.secondary{background:#edf1f6;color:#24374a}button:disabled{opacity:.45}textarea{border:1px solid #ccd5df;min-height:110px}small{color:#637389}#error{color:#b3261e}</style>
<main><small>MAC ↔ iPHONE · Same Wi-Fi</small><h1>HP 117w Manual Duplex</h1><section><details style="margin-bottom:20px"><summary>Connect your iPhone (one-time setup)</summary><p>Scan with your iPhone camera, then choose Share → Add to Home Screen in Safari. Next time, tap Duplex Print on your Home Screen—no need to scan again. Keep your iPhone and Mac on the same Wi-Fi:</p><img src="qr.png" width="230" height="230" style="image-rendering:pixelated;max-width:100%"><p id="address" style="overflow-wrap:anywhere;font-size:13px"></p></details><div id="message">Connecting to your Mac…</div><textarea id="note" placeholder="Print note (optional)" hidden maxlength="4000"></textarea><div id="buttons"></div><p id="error"></p></section><p><small>For quick access, choose Share → Add to Home Screen in Safari. Keep your Mac awake. Reload paper using the orientation you previously tested. Cancel stops subsequent steps; manage already submitted jobs in Print Center.</small></p></main>
<script>
document.querySelector('#address').textContent=location.href; if(innerWidth>700)document.querySelector('details').open=true;
let current='',busy=false;const labels={'Cancel':'Cancel remaining steps','Continue':'Paper reloaded — print back sides','Print First Side':'Print front sides','Check Again':'Check print status','Skip Note':'Skip note','Save Record':'Save record','Not Now':'Done','Open Excel':'Open Excel on Mac','OK':'OK'};
async function poll(){try{let r=await fetch(location.pathname+'state',{cache:'no-store'});if(!r.ok)throw Error('Connection failed');let s=await r.json();if(s.id!==current){current=s.id;document.querySelector('#message').textContent=s.message;document.querySelector('#note').hidden=!s.note;document.querySelector('#note').value='';let box=document.querySelector('#buttons');box.replaceChildren();for(let b of s.buttons||[]){let el=document.createElement('button');el.textContent=labels[b]||b;if(b==='Cancel'||b==='Skip Note'||b==='Not Now')el.className='secondary';el.onclick=()=>answer(s.id,b);box.append(el)}}document.querySelector('#error').textContent='';}catch(e){document.querySelector('#error').textContent='Cannot reach your Mac. Check that both devices are on the same Wi-Fi. Reconnecting automatically…'}}
async function answer(id,button){if(busy)return;busy=true;document.querySelectorAll('button').forEach(b=>b.disabled=true);try{let r=await fetch(location.pathname+'answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,button,note:document.querySelector('#note').value})});if(!r.ok)throw Error();await poll();}catch(e){document.querySelector('#error').textContent='Your action was not confirmed. Wait for the page to refresh, then try again.';}finally{busy=false;document.querySelectorAll('button').forEach(b=>b.disabled=false)}}
poll();setInterval(poll,1200);
</script></html>"""

def serve(token):
    class Server(http.server.ThreadingHTTPServer):
        def server_bind(self):
            socketserver.TCPServer.server_bind(self)
            self.server_name='HP117w'
            self.server_port=self.server_address[1]
    lock=threading.Lock()
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def respond(self,status,data,kind='application/json'):
            data=data.encode() if isinstance(data,str) else data;self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Referrer-Policy','no-referrer');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
        def do_GET(self):
            path=urllib.parse.urlsplit(self.path).path
            if path=='/'+token+'/': return self.respond(200,PAGE,'text/html')
            if path=='/'+token+'/qr.png' and (STATE/'qr.png').exists(): return self.respond(200,(STATE/'qr.png').read_bytes(),'image/png')
            if path=='/'+token+'/state':
                with lock: state=read('prompt.json',{'id':'idle','message':'Waiting for a PDF from the print menu on your Mac.','buttons':[]})
                return self.respond(200,json.dumps(state,ensure_ascii=False))
            self.respond(404,'{}')
        def do_POST(self):
            if self.path!='/'+token+'/answer': return self.respond(404,'{}')
            origin=self.headers.get('Origin')
            if origin and origin!='http://'+self.headers.get('Host',''): return self.respond(403,'{}')
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=20000: raise ValueError()
                data=json.loads(self.rfile.read(size))
                if not isinstance(data.get('note',''),str) or len(data.get('note',''))>4000: raise ValueError()
            except (ValueError,TypeError): return self.respond(400,'{}')
            with lock:
                state=read('prompt.json',{})
                if data.get('id')!=state.get('id') or data.get('button') not in state.get('buttons',[]): return self.respond(409,'{}')
                write('prompt.json',{'id':secrets.token_hex(12),'message':'Processing, please wait…','buttons':[]})
                write('answer.json',data)
            self.respond(200,'{}')
    server=Server(('127.0.0.1',PORT),Handler)
    server.daemon_threads=True
    if not os.environ.get('HP117W_TEST'):
        # Bind the LAN interface separately: loopback remains reachable for health checks.
        for interface in ('en0','en1'):
            address=subprocess.run(['/usr/sbin/ipconfig','getifaddr',interface],capture_output=True,text=True).stdout.strip()
            if address:
                lan=Server((address,PORT),Handler)
                lan.daemon_threads=True
                threading.Thread(target=lan.serve_forever,daemon=True).start()
    server.serve_forever()

def main():
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(STATE,0o700)
    if not (STATE/'token').exists():
        fd=os.open(STATE/'token',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as f:f.write(secrets.token_urlsafe(24))
    token=(STATE/'token').read_text()
    cmd=sys.argv[1]
    if cmd=='serve': return serve(token)
    if cmd=='start':
        import urllib.request
        def ready():
            try:
                with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:%d/%s/state'%(PORT,token),timeout=1) as r:return r.status==200
            except Exception:return False
        if not ready():
            log=open(STATE/'server.log','a')
            subprocess.Popen([sys.executable,__file__,'serve'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
            for _ in range(30):
                if ready():break
                time.sleep(.1)
            else: raise RuntimeError('The mobile control service could not start. Check port 8717.')
        host=subprocess.check_output(['/usr/sbin/scutil','--get','LocalHostName'],text=True).strip()+'.local'
        url='http://%s:%d/%s/'%(host,PORT,token)
        subprocess.run(['/usr/bin/osascript','-l','JavaScript',str(Path(__file__).with_name('duplex.js')),'--qr',url,str(STATE/'qr.png')],check=True,stdout=subprocess.DEVNULL)
        print(url);return
    if cmd=='ask':
        ident=secrets.token_hex(16)
        write('prompt.json',{'id':ident,'message':sys.argv[2],'note':sys.argv[3]=='note','buttons':sys.argv[4:]})
        while True:
            result=read('answer.json',{})
            if result.get('id')==ident:
                print(result.get('button','')+'\n'+result.get('note',''));return
            time.sleep(.25)
    if cmd=='finish':
        write('prompt.json',{'id':secrets.token_hex(12),'message':'This session has ended. Send the next file from the PDF print menu on your Mac.','buttons':[]})

if __name__=='__main__': main()
