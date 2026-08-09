# -*- coding: utf-8 -*-
import datetime
import http.server
import os
import re
import socket
import ssl
import threading
import urllib.parse
import urllib.request

_config = {
    "save_cache": None,
    "get_cache": None,
    "get_cert": None,
    "injected_tag": None,
    "ui_script": None,
    "error_template": None,
    "event_callback": None,
    "enable_plugins": False,
}

_httpd_server = None
_download_counter = 0
_enable_tracking = False


def configure_proxy(options: dict):
  global _config, _enable_tracking
  _config.update(options)
  if options.get("enable_plugins"):
    _enable_tracking = True


def emit_event(event_type, data):
  if not _enable_tracking:
    return
  timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  callback = _config.get("event_callback")
  if callback:
    callback(event_type, timestamp, data)


def fetch_resource(full_url, download_id):
  try:
    req = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Encoding": "identity",
        },
    )

    parsed_url = urllib.parse.urlparse(full_url)
    filename = os.path.basename(parsed_url.path)
    if not filename or filename == "":
      filename = parsed_url.netloc + "_index.html"

    with urllib.request.urlopen(req, timeout=15) as resp:
      content_type = str(
          resp.headers.get("Content-Type", "text/html; charset=utf-8")
      )
      total_size = int(resp.headers.get("Content-Length", 0))

      emit_event(
          "DOWNLOAD_START",
          {
              "id": download_id,
              "filename": filename,
              "total_size": total_size,
              "url": full_url,
          },
      )

      chunks = []
      downloaded = 0
      chunk_size = 8192

      while True:
        chunk = resp.read(chunk_size)
        if not chunk:
          break
        chunks.append(chunk)
        downloaded += len(chunk)

        emit_event(
            "DOWNLOAD_PROGRESS",
            {
                "id": download_id,
                "downloaded": downloaded,
                "total_size": total_size,
            },
        )

      content = b"".join(chunks)
      emit_event(
          "DOWNLOAD_END", {"id": download_id, "filename": filename}
      )

      return content, content_type
  except Exception as e:
    emit_event("DOWNLOAD_END", {"id": download_id, "error": str(e)})
    raise e


class HTTPSMitMHandler(http.server.BaseHTTPRequestHandler):

  def log_message(self, format, *args):
    return

  def do_CONNECT(self):
    global _download_counter
    host, port = self.path.split(":")
    port = int(port)

    emit_event("CONNECT", {"host": host, "port": port, "headers": dict(self.headers)})

    self.send_response(200, "Connection Established")
    self.end_headers()

    try:
      get_cert_func = _config.get("get_cert")
      cert_file, key_file = get_cert_func(host)
      context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
      context.load_cert_chain(certfile=cert_file, keyfile=key_file)

      with context.wrap_socket(self.connection, server_side=True) as secure_sock:
        buffer = bytearray()
        secure_sock.settimeout(5.0)
        try:
          while b"\r\n\r\n" not in buffer:
            chunk = secure_sock.recv(4096)
            if not chunk:
              break
            buffer.extend(chunk)
        except socket.timeout:
          pass

        if not buffer:
          return

        header_data = bytes(buffer)
        request_line = (
            header_data.decode("utf-8", errors="ignore").split("\r\n")[0]
        )
        parts = request_line.split(" ")
        if len(parts) < 2:
          return

        method, path = parts[0], parts[1]

        if path == "__proxy_ui.js":
          ui_script = _config.get("ui_script", "")
          script_bytes = ui_script.encode("utf-8")
          header = (
              b"HTTP/1.1 200 OK\r\nContent-Type: application/javascript;"
              b" charset=utf-8\r\nContent-Length: "
              + str(len(script_bytes)).encode()
              + b"\r\nConnection: close\r\n\r\n"
          )
          secure_sock.sendall(header + script_bytes)
          return

        full_url = f"https://{host}{path}"
        get_cache_func = _config.get("get_cache")
        if get_cache_func:
          cached = get_cache_func(full_url)
          if cached:
            content, content_type = cached
            try:
              response_data = (
                  b"HTTP/1.1 200 OK\r\nContent-Type: "
                  + content_type.encode()
                  + b"\r\nContent-Length: "
                  + str(len(content)).encode()
                  + b"\r\nConnection: close\r\n\r\n"
                  + content
              )
              secure_sock.sendall(response_data)
            except:
              pass
            return

        _download_counter += 1
        dl_id = _download_counter

        try:
          content, content_type = fetch_resource(full_url, dl_id)

          injected_tag = _config.get("injected_tag", b"")
          if content_type and "text/html" in content_type.lower():
            match = re.search(b"<head[^>]*>", content, re.IGNORECASE)
            if match:
              pos = match.end()
              content = content[:pos] + injected_tag + content[pos:]
            elif b"<html>" in content.lower():
              content = content.replace(b"<html>", b"<html>" + injected_tag, 1)
            else:
              content = injected_tag + content

          save_cache_func = _config.get("save_cache")
          if save_cache_func:
            threading.Thread(
                target=save_cache_func, args=(full_url, content, content_type)
            ).start()

          response_data = (
              b"HTTP/1.1 200 OK\r\nContent-Type: "
              + content_type.encode()
              + b"\r\nContent-Length: "
              + str(len(content)).encode()
              + b"\r\nConnection: close\r\n\r\n"
              + content
          )
          secure_sock.sendall(response_data)
        except Exception:
          try:
            error_template = _config.get("error_template", "")
            err_content = error_template.encode("utf-8")
            response_data = (
                b"HTTP/1.1 200 OK\r\nContent-Type: text/html;"
                b" charset=utf-8\r\nContent-Length: "
                + str(len(err_content)).encode()
                + b"\r\nConnection: close\r\n\r\n"
                + err_content
            )
            secure_sock.sendall(response_data)
          except:
            pass
    except Exception:
      pass

  def do_GET(self):
    global _download_counter
    url = self.path

    emit_event("GET", {"url": url, "headers": dict(self.headers)})

    if "__proxy_ui.js" in url:
      ui_script = _config.get("ui_script", "")
      script_bytes = ui_script.encode("utf-8")
      try:
        self.send_response(200)
        self.send_header(
            "Content-Type", "application/javascript; charset=utf-8"
        )
        self.send_header("Content-Length", str(len(script_bytes)))
        self.end_headers()
        self.wfile.write(script_bytes)
      except:
        pass
      return

    if url.startswith("http://"):
      url = url[7:]
    full_url = f"http://{url}"

    get_cache_func = _config.get("get_cache")
    if get_cache_func:
      cached = get_cache_func(full_url)
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

    _download_counter += 1
    dl_id = _download_counter

    try:
      content, content_type = fetch_resource(full_url, dl_id)

      injected_tag = _config.get("injected_tag", b"")
      if content_type and "text/html" in content_type.lower():
        match = re.search(b"<head[^>]*>", content, re.IGNORECASE)
        if match:
          pos = match.end()
          content = content[:pos] + injected_tag + content[pos:]
        elif b"<html>" in content.lower():
          content = content.replace(b"<html>", b"<html>" + injected_tag, 1)
        else:
          content = injected_tag + content

      save_cache_func = _config.get("save_cache")
      if save_cache_func:
        threading.Thread(
            target=save_cache_func, args=(full_url, content, content_type)
        ).start()
      try:
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(content)
      except:
        pass
    except Exception:
      try:
        error_template = _config.get("error_template", "")
        err_content = error_template.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(err_content)))
        self.end_headers()
        self.wfile.write(err_content)
      except:
        pass


def start_proxy_server(host, port):
  global _httpd_server
  try:
    _httpd_server = http.server.HTTPServer((host, port), HTTPSMitMHandler)
    emit_event("SERVER", f"Proxy running on http://{host}:{port}")
    _httpd_server.serve_forever()
  except Exception:
    pass


def stop_proxy_server():
  global _httpd_server
  if _httpd_server:
    try:
      _httpd_server.server_close()
      _httpd_server = None
    except Exception:
      pass
