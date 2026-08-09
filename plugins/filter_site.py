# -*- coding: utf-8 -*-
import tkinter as tk


class Plugin:
  PLUGIN_ID = "SITES"
  PLUGIN_NAME = "Site Requests"

  def __init__(self):
    pass

  def init_ui(self, container_frame, app_instance):
    pass

  def filter(self, category, message):
    return category in ["CONNECT", "GET"]

  def on_event(self, event_type, timestamp, data):
    if not isinstance(data, dict):
      return

    # إذا تم تعيين النص مسبقاً، لا تقم بإعادة تعيينه
    if "text" in data:
      return

    if event_type == "CONNECT":
      # البحث الشامل عن الهوست
      host = (
          data.get("host")
          or data.get("Host")
          or data.get("HOSTNAME")
          or data.get("domain")
      )

      if not host and "headers" in data and isinstance(data["headers"], dict):
        headers = data["headers"]
        host = headers.get("Host") or headers.get("host")
        if host and ":" in host:
          host = host.split(":")[0]

      if not host:
        for val in data.values():
          if isinstance(val, str) and ("." in val or ":" in val):
            host = val
            break

      if not host:
        host = "Unknown Host"

      port = data.get("port", 443)
      # نص صافي بدون تكرار كلمة CONNECT
      data["text"] = f"Host: {host} | Port: {port}"

    elif event_type == "GET":
      url = data.get("url") or data.get("URL")
      if not url and "headers" in data and isinstance(data["headers"], dict):
        url = data["headers"].get("Host", "Unknown URL")
      data["text"] = f"URL: {url}"
