# -*- coding: utf-8 -*-
import tkinter as tk


class Plugin:
  PLUGIN_ID = "BROWSERS"
  PLUGIN_NAME = "Browser Filter"

  def __init__(self):
    pass

  def init_ui(self, container_frame, app_instance):
    pass

  def filter(self, category, message):
    # مراقبة الطلبات التي تحتوي على معلومات الهيدرز أو التصفح
    return category in ["GET", "POST", "CONNECT"]

  def on_event(self, event_type, timestamp, data):
    if not isinstance(data, dict):
      return

    # البحث عن الـ User-Agent في الهيدرز لمعرفة المتصفح المستخدم
    headers = data.get("headers")
    if not isinstance(headers, dict):
      return

    user_agent = headers.get("User-Agent") or headers.get("user-agent")
    if not user_agent:
      return

    # تبسيط اسم المتصفح ليظهر بشكل جميل وواضح
    browser_name = "Unknown Browser"
    ua_lower = user_agent.lower()

    if "firefox" in ua_lower:
      browser_name = "Firefox"
    elif "chrome" in ua_lower and "edge" not in ua_lower:
      browser_name = "Chrome"
    elif "safari" in ua_lower and "chrome" not in ua_lower:
      browser_name = "Safari"
    elif "edge" in ua_lower:
      browser_name = "MS Edge"
    elif "curl" in ua_lower:
      browser_name = "cURL"
    elif "python" in ua_lower:
      browser_name = "Python Script"
    else:
      # إذا لم يتعرف عليه، يأخذ أول جزئية من الـ User-Agent
      browser_name = user_agent.split("/")[0]

    # تعيين النص المختصر والنظيف للواجهة
    data["text"] = f"Browser: {browser_name}"
