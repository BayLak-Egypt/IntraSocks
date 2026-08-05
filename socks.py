import http.server
import socket
import threading
import sqlite3
import urllib.request
import zlib
import ssl
import os
import sys

PROXY_HOST = "127.0.0.1"
PROXY_PORT = 8080
DB_NAME = "https_cache_proxy.db"
CERTS_DIR = "certs"
CA_CERT = "ca.crt"
CA_KEY = "ca.key"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            url TEXT PRIMARY KEY,
            content BLOB,
            content_type TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON cache (url);')
    conn.commit()
    conn.close()

def save_to_cache(url, content, content_type):
    try:
        if not content:
            return
        compressed_content = zlib.compress(content, level=4)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (url, content, content_type) VALUES (?, ?, ?)", 
            (url, compressed_content, content_type)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_from_cache(url):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT content, content_type FROM cache WHERE url = ?", (url,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            compressed_content, content_type = row
            try:
                content = zlib.decompress(compressed_content)
                return content, content_type
            except:
                return compressed_content, content_type
    except:
        pass
    return None

def generate_ca():
    if os.path.exists(CA_CERT) and os.path.exists(CA_KEY):
        return
    print("[*] Generating Root CA...")
    ext_file = "ca.ext"
    with open(ext_file, "w") as f:
        f.write("basicConstraints = critical, CA:TRUE\n")
        f.write("keyUsage = critical, keyCertSign, cRLSign\n")

    os.system(f"openssl genrsa -out {CA_KEY} 2048 2>/dev/null")
    os.system(f"openssl req -x509 -new -nodes -key {CA_KEY} -sha256 -days 3650 -out {CA_CERT} -subj '/CN=Local Custom CA' 2>/dev/null")
    os.system(f"openssl x509 -in {CA_CERT} -days 3650 -sha256 -req -signkey {CA_KEY} -extfile {ext_file} -out {CA_CERT} 2>/dev/null")
    if os.path.exists(ext_file):
        os.remove(ext_file)
    print("[*] Root CA generated successfully!")

def get_site_cert(hostname):
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)
        
    cert_file = os.path.join(CERTS_DIR, f"{hostname}.crt")
    key_file = os.path.join(CERTS_DIR, f"{hostname}.key")
    csr_file = os.path.join(CERTS_DIR, f"{hostname}.csr")
    ext_file = os.path.join(CERTS_DIR, f"{hostname}.ext")
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        return cert_file, key_file

    os.system(f"openssl genrsa -out {key_file} 2048 2>/dev/null")
    os.system(f"openssl req -new -key {key_file} -out {csr_file} -subj '/CN={hostname}' 2>/dev/null")
    
    with open(ext_file, "w") as f:
        f.write(f"authorityKeyIdentifier=keyid,issuer\n")
        f.write(f"basicConstraints=CA:FALSE\n")
        f.write(f"keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment\n")
        f.write(f"subjectAltName = DNS:{hostname}\n")

    os.system(f"openssl x509 -req -in {csr_file} -CA {CA_CERT} -CAkey {CA_KEY} -CAcreateserial -out {cert_file} -days 365 -sha256 -extfile {ext_file} 2>/dev/null")
    
    for f in [csr_file, ext_file, f"{CA_CERT}.srl"]:
        if os.path.exists(f):
            os.remove(f)
            
    return cert_file, key_file

INJECTED_UI = """
<style>
#proxy-bottom-bar {
    position: fixed !important; bottom: 0 !important; left: 0 !important; right: 0 !important;
    height: 38px !important; background: rgba(15, 23, 42, 0.96) !important;
    backdrop-filter: blur(8px) !important; color: #f8fafc !important;
    border-top: 1px solid #334155 !important; z-index: 2147483646 !important;
    display: none; flex-direction: column !important; justify-content: center !important;
    padding: 0 15px !important; font-family: monospace !important; font-size: 11px !important;
    box-shadow: 0 -4px 20px rgba(0,0,0,0.4) !important; transition: opacity 0.3s ease !important;
    opacity: 0;
}
.ps-info-row { display: flex !important; justify-content: space-between !important; align-items: center !important; margin-bottom: 3px !important; }
.ps-url { white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; color: #38bdf8 !important; font-weight: 600 !important; max-width: 85% !important; }
.ps-status { color: #22c55e !important; font-size: 10px !important; }
.ps-track { background: #334155 !important; height: 3px !important; border-radius: 2px !important; overflow: hidden !important; width: 100% !important; }
.ps-fill { background: linear-gradient(90deg, #38bdf8, #6366f1) !important; height: 100% !important; width: 100% !important; }

#proxy-floating-btn {
    position: fixed !important; top: 20px !important; right: 20px !important;
    background: #0284c7 !important; color: white !important; border: none !important;
    border-radius: 25px !important; padding: 8px 16px !important; font-size: 11px !important;
    font-weight: bold !important; cursor: grab !important; box-shadow: 0 4px 15px rgba(0,0,0,0.4) !important;
    align-items: center !important; gap: 6px !important; border: 1px solid #38bdf8 !important;
    z-index: 2147483647 !important; font-family: monospace !important; user-select: none !important;
    touch-action: none !important; white-space: nowrap !important; display: inline-flex !important;
    width: 110px !important; height: 32px !important; min-width: 110px !important; max-width: 110px !important;
    min-height: 32px !important; max-height: 32px !important; flex: 0 0 110px !important;
    flex-grow: 0 !important; flex-shrink: 0 !important; box-sizing: border-box !important;
    justify-content: center !important; overflow: hidden !important; text-overflow: ellipsis !important;
    transform: none !important; bottom: auto !important;
}
#proxy-floating-btn:active { cursor: grabbing !important; }

#proxy-logs-modal {
    position: fixed !important; top: 50% !important; left: 50% !important; transform: translate(-50%, -50%) !important;
    width: 550px !important; height: 350px !important; background: rgba(15, 23, 42, 0.98) !important;
    backdrop-filter: blur(10px) !important; border: 1px solid #334155 !important; border-radius: 8px !important;
    z-index: 2147483647 !important; display: none; flex-direction: column !important; box-shadow: 0 15px 40px rgba(0,0,0,0.8) !important;
    font-family: monospace !important; color: #f8fafc !important; overflow: hidden !important;
}
.plm-header { display: flex !important; justify-content: space-between !important; align-items: center !important; padding: 8px 12px !important; background: #1e293b !important; border-bottom: 1px solid #334155 !important; font-weight: bold !important; font-size: 11px !important; color: #38bdf8 !important; }
.plm-close { background: #ef4444 !important; color: white !important; border: none !important; border-radius: 3px !important; padding: 2px 6px !important; cursor: pointer !important; font-family: monospace !important; font-weight: bold !important; }
.plm-body { padding: 8px 12px !important; overflow-y: auto !important; flex-grow: 1 !important; display: flex !important; flex-direction: column !important; gap: 3px !important; font-size: 10px !important; }
.plm-row { display: flex !important; justify-content: space-between !important; border-bottom: 1px solid rgba(255,255,255,0.04) !important; padding: 3px 0 !important; gap: 8px !important; }
.plm-url { color: #cbd5e1 !important; white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important; }
.plm-status-ok { color: #22c55e !important; font-weight: bold !important; }
</style>

<div id="proxy-bottom-bar">
    <div class="ps-info-row">
        <span class="ps-url" id="proxy-bar-url">Ready</span>
        <span class="ps-status" id="proxy-bar-status">Loaded</span>
    </div>
    <div class="ps-track"><div class="ps-fill" id="proxy-bar-fill"></div></div>
</div>

<button id="proxy-floating-btn">⚡ Logs Menu</button>

<div id="proxy-logs-modal">
    <div class="plm-header">
        <span>📜 Page Activity Logs</span>
        <button class="plm-close" id="proxy-close-logs">✕ Close</button>
    </div>
    <div class="plm-body" id="proxy-logs-container"></div>
</div>

<script>
(function() {
    if (window.__proxy_ui_injected) return;
    window.__proxy_ui_injected = true;

    let allLogs = [];
    let hideTimer = null;
    const floatBtn = document.getElementById('proxy-floating-btn');
    const modal = document.getElementById('proxy-logs-modal');
    const bottomBar = document.getElementById('proxy-bottom-bar');
    
    const savedX = localStorage.getItem('proxy_btn_x');
    const savedY = localStorage.getItem('proxy_btn_y');
    if (savedX !== null && savedY !== null) {
        floatBtn.style.left = savedX + 'px';
        floatBtn.style.top = savedY + 'px';
        floatBtn.style.right = 'auto';
        floatBtn.style.bottom = 'auto';
    }

    let isDragging = false, startX, startY, initialX, initialY, hasMoved = false;
    
    floatBtn.addEventListener('pointerdown', (e) => {
        isDragging = true;
        hasMoved = false;
        startX = e.clientX;
        startY = e.clientY;
        const rect = floatBtn.getBoundingClientRect();
        initialX = rect.left;
        initialY = rect.top;
        floatBtn.style.right = 'auto';
        floatBtn.style.bottom = 'auto';
        floatBtn.style.left = initialX + 'px';
        floatBtn.style.top = initialY + 'px';
        floatBtn.setPointerCapture(e.pointerId);
    });

    floatBtn.addEventListener('pointermove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        if (Math.abs(dx) > 3 || Math.abs(dy) > 3) hasMoved = true;
        
        let newX = initialX + dx;
        let newY = initialY + dy;
        
        const maxX = window.innerWidth - floatBtn.offsetWidth;
        const maxY = window.innerHeight - floatBtn.offsetHeight;
        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));

        floatBtn.style.left = newX + 'px';
        floatBtn.style.top = newY + 'px';
    });

    floatBtn.addEventListener('pointerup', (e) => {
        if (isDragging) {
            isDragging = false;
            try { floatBtn.releasePointerCapture(e.pointerId); } catch(err) {}
            localStorage.setItem('proxy_btn_x', parseInt(floatBtn.style.left));
            localStorage.setItem('proxy_btn_y', parseInt(floatBtn.style.top));
        }
    });

    const openLogs = () => { modal.style.display = 'flex'; };
    floatBtn.onclick = () => { if (!hasMoved) openLogs(); };
    document.getElementById('proxy-close-logs').onclick = () => { modal.style.display = 'none'; };

    function addLog(url, status) {
        const time = new Date().toLocaleTimeString();
        allLogs.unshift({ time, url, status });
        if (allLogs.length > 50) allLogs.pop();
        const c = document.getElementById('proxy-logs-container');
        if (c) {
            c.innerHTML = allLogs.map(l => `
                <div class="plm-row">
                    <span style="color:#64748b; min-width:60px;">[${l.time}]</span>
                    <span class="plm-url" title="${l.url}">${l.url}</span>
                    <span class="plm-status-ok">${l.status}</span>
                </div>
            `).join('');
        }
    }

    const barUrl = document.getElementById('proxy-bar-url');
    const barFill = document.getElementById('proxy-bar-fill');

    if (window.PerformanceObserver) {
        try {
            const observer = new PerformanceObserver((list) => {
                const entries = list.getEntries();
                if (entries.length === 0) return;
                const entry = entries[entries.length - 1];
                const assetUrl = entry.name;
                
                if (!assetUrl || assetUrl.startsWith('data:') || assetUrl.startsWith('chrome-extension:')) return;

                const fileName = assetUrl.split('/').pop().split('?')[0] || assetUrl;
                barUrl.textContent = fileName;
                barUrl.title = assetUrl;
                
                bottomBar.style.display = 'flex';
                setTimeout(() => { bottomBar.style.opacity = '1'; }, 10);
                barFill.style.width = '100%';

                addLog(assetUrl, 'Loaded');

                if (hideTimer) clearTimeout(hideTimer);
                hideTimer = setTimeout(() => {
                    bottomBar.style.opacity = '0';
                    setTimeout(() => {
                        bottomBar.style.display = 'none';
                    }, 300);
                }, 800);
            });
            observer.observe({ entryTypes: ['resource'] });
        } catch(e) {}
    }
})();
</script>
"""

class HTTPSMitMHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_CONNECT(self):
        host, port = self.path.split(':')
        port = int(port)
        self.send_response(200, "Connection Established")
        self.end_headers()

        try:
            cert_file, key_file = get_site_cert(host)
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            context.load_cert_chain(certfile=cert_file, keyfile=key_file)
            
            with context.wrap_socket(self.connection, server_side=True) as secure_sock:
                data = secure_sock.recv(65536)
                if not data:
                    return
                
                request_line = data.decode('utf-8', errors='ignore').split('\r\n')[0]
                parts = request_line.split(' ')
                if len(parts) < 2:
                    return
                
                method, path = parts[0], parts[1]
                full_url = f"https://{host}{path}"
                
                cached = get_from_cache(full_url)
                if cached:
                    content, content_type = cached
                    try:
                        response_data = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\nConnection: close\r\n\r\n".encode() + content
                        secure_sock.sendall(response_data)
                    except:
                        pass
                    return

                try:
                    req = urllib.request.Request(full_url, headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept-Encoding": "identity"
                    })
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        content = resp.read()
                        content_type = str(resp.headers.get("Content-Type", "text/html; charset=utf-8"))
                        
                        if content_type and "text/html" in content_type.lower():
                            ui_bytes = INJECTED_UI.encode('utf-8')
                            if b"<head>" in content.lower():
                                content = content.replace(b"<head>", b"<head>" + ui_bytes, 1)
                            elif b"<html>" in content.lower():
                                content = content.replace(b"<html>", b"<html>" + ui_bytes, 1)
                            else:
                                content = ui_bytes + content

                        threading.Thread(target=save_to_cache, args=(full_url, content, content_type)).start()
                        
                        response_data = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\nContent-Length: {len(content)}\r\nConnection: close\r\n\r\n".encode() + content
                        secure_sock.sendall(response_data)
                except Exception as e:
                    try:
                        err_msg = f"Proxy Error: {e}".encode()
                        secure_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: " + str(len(err_msg)).encode() + b"\r\n\r\n" + err_msg)
                    except:
                        pass
        except Exception:
            pass

    def do_GET(self):
        url = self.path
        if url.startswith("http://"):
            url = url[7:]
        full_url = f"http://{url}"

        cached = get_from_cache(full_url)
        if cached:
            content, content_type = cached
            try:
                self.send_response(200)
                if content_type:
                    self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(content)
            except:
                pass
            return

        try:
            req = urllib.request.Request(full_url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Encoding": "identity"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                content = resp.read()
                content_type = str(resp.headers.get("Content-Type", "text/html; charset=utf-8"))
                
                if content_type and "text/html" in content_type.lower():
                    ui_bytes = INJECTED_UI.encode('utf-8')
                    if b"<head>" in content.lower():
                        content = content.replace(b"<head>", b"<head>" + ui_bytes, 1)
                    elif b"<html>" in content.lower():
                        content = content.replace(b"<html>", b"<html>" + ui_bytes, 1)
                    else:
                        content = ui_bytes + content

                threading.Thread(target=save_to_cache, args=(full_url, content, content_type)).start()
                try:
                    self.send_response(200)
                    self.send_header("Content-Type", content_type)
                    self.end_headers()
                    self.wfile.write(content)
                except:
                    pass
        except Exception:
            try:
                self.send_response(502)
                self.end_headers()
            except:
                pass

if __name__ == "__main__":
    generate_ca()
    init_db()
    httpd = http.server.HTTPServer((PROXY_HOST, PROXY_PORT), HTTPSMitMHandler)
    print(f"[*] Proxy running on http://{PROXY_HOST}:{PROXY_PORT}\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
