# -*- coding: utf-8 -*-
import os
import sqlite3
import tkinter as tk
from urllib.parse import urlparse
import time

class Plugin:
    PLUGIN_ID = "DB_DIR"
    PLUGIN_NAME = "Database DIR"

    def __init__(self):
        self.app_instance = None
        self.last_update_time = 0

    def init_ui(self, container_frame, app_instance):
        self.app_instance = app_instance
        self.load_database_records()

    def filter(self, category, message):
        return category == "DB_RECORD"

    def on_event(self, event_type, timestamp, data):
        current_time = time.time()
        if self.app_instance and (current_time - self.last_update_time > 5):
            self.last_update_time = current_time
            self.load_database_records()

    def load_database_records(self):
        if not self.app_instance:
            return

        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)

        db_files = []
        for d in [current_dir, parent_dir]:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.endswith(".db"):
                        db_files.append(os.path.join(d, f))

        domain_data = {}        # لتخزين الروابط وحجم كل رابط منفرد
        domain_total_sizes = {} # لتخزين المساحة الإجمالية للشجرة كلها

        for db_path in db_files:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()

                for table_row in tables:
                    table_name = table_row[0]
                    try:
                        cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = [col[1] for col in cursor.fetchall()]
                        
                        url_col = next((c for c in columns if 'url' in c.lower()), columns[0] if columns else None)
                        content_col = next((c for c in columns if 'content' in c.lower() or 'data' in c.lower() or 'body' in c.lower()), None)
                        
                        if not url_col:
                            continue

                        if content_col:
                            cursor.execute(f"SELECT {url_col}, {content_col} FROM {table_name}")
                        else:
                            cursor.execute(f"SELECT {url_col} FROM {table_name}")
                            
                        rows = cursor.fetchall()
                    except Exception:
                        continue

                    for row in rows:
                        url = row[0] if len(row) > 0 else ""
                        content = row[1] if len(row) > 1 else None
                        
                        if url and isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")) and len(url) < 300:
                            parsed_url = urlparse(url)
                            domain = parsed_url.netloc if parsed_url.netloc else "Unknown"

                            if domain not in domain_data:
                                domain_data[domain] = {}
                                domain_total_sizes[domain] = 0

                            # حساب حجم هذا الرابط وحده مع محتواه
                            url_size = len(url.encode('utf-8'))
                            content_size = 0
                            if content:
                                if isinstance(content, bytes):
                                    content_size = len(content)
                                elif isinstance(content, str):
                                    content_size = len(content.encode('utf-8'))
                            
                            single_url_size = url_size + content_size
                            
                            # تخزين حجم كل رابط على حدة
                            domain_data[domain][url] = single_url_size
                            # جمع الحجم الإجمالي للدومين
                            domain_total_sizes[domain] += single_url_size

                conn.close()
            except Exception as e:
                print(f"Error reading DB {db_path}: {e}")

        # تنظيف السجلات القديمة لمنع التراكم
        self.app_instance.all_logs = [
            log for log in self.app_instance.all_logs if log.get("plugin_id") != "DB_DIR"
        ]

        new_plugin_logs = []

        # 1. علامة البداية
        start_list_text = "=== [ DOMAIN DIR REGISTER ] ==="
        new_plugin_logs.append({
            "text": start_list_text,
            "category": "DB_RECORD",
            "plugin_id": "DB_DIR",
            "message": {"text": start_list_text},
        })

        sorted_domains = list(domain_data.items())[:300]

        for domain, urls_dict in sorted_domains:
            total_bytes = domain_total_sizes.get(domain, 0)
            
            # تنسيق الحجم الإجمالي للدومين
            if total_bytes >= 1024 * 1024:
                domain_size_str = f"{total_bytes / (1024 * 1024):.2f} MB"
            elif total_bytes >= 1024:
                domain_size_str = f"{total_bytes / 1024:.2f} KB"
            else:
                domain_size_str = f"{total_bytes} Bytes"

            # رأس الشجرة يظهر المجموع الكلي للدومين
            header_text = f"[{domain_size_str}] 🌐 {domain} (Total Tree URLs: {len(urls_dict)})"
            new_plugin_logs.append({
                "text": header_text,
                "category": "DB_RECORD",
                "plugin_id": "DB_DIR",
                "message": {"text": header_text},
            })

            # فروع الشجرة: كل صفحة تعرض حجمها الحقيقي الخاص بها فقط
            sorted_urls = sorted(urls_dict.items(), key=lambda x: x[1], reverse=True)[:25]
            for url, u_size in sorted_urls:
                if u_size >= 1024 * 1024:
                    u_size_str = f"{u_size / (1024 * 1024):.2f} MB"
                elif u_size >= 1024:
                    u_size_str = f"{u_size / 1024:.2f} KB"
                else:
                    u_size_str = f"{u_size} Bytes"

                branch_text = f"    [{u_size_str}] ├── {url}"
                new_plugin_logs.append({
                    "text": branch_text,
                    "category": "DB_RECORD",
                    "plugin_id": "DB_DIR",
                    "message": {"text": branch_text},
                })

        # 2. علامة النهاية
        end_list_text = "=== [ End of Database Records List ] ==="
        new_plugin_logs.append({
            "text": end_list_text,
            "category": "DB_RECORD",
            "plugin_id": "DB_DIR",
            "message": {"text": end_list_text},
        })

        self.app_instance.all_logs.extend(new_plugin_logs)

        if hasattr(self.app_instance, "current_filter") and (self.app_instance.current_filter == "ALL" or self.app_instance.current_filter == "DB_DIR"):
            self.app_instance.listbox.delete(0, tk.END)
            filter_type = self.app_instance.current_filter
            display_items = [
                log["text"] for log in self.app_instance.all_logs 
                if filter_type == "ALL" or log.get("plugin_id") == filter_type
            ]
            
            for item in display_items:
                self.app_instance.listbox.insert(tk.END, item)
