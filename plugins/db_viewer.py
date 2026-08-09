# -*- coding: utf-8 -*-
import os
import sqlite3
import tkinter as tk
from urllib.parse import urlparse
import time


class Plugin:
    PLUGIN_ID = "DB_VIEWER"
    PLUGIN_NAME = "Database Viewer"

    def __init__(self):
        self.app_instance = None
        self.last_update_time = 0

    def init_ui(self, container_frame, app_instance):
        self.app_instance = app_instance
        self.load_database_records()

    def filter(self, category, message):
        return True

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

        domain_data = {}
        domain_sizes = {}

        for db_path in db_files:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()

                for table_row in tables:
                    table_name = table_row[0]
                    try:
                        cursor.execute(f"SELECT url, content FROM {table_name}")
                        rows = cursor.fetchall()
                    except Exception:
                        try:
                            cursor.execute(f"SELECT * FROM {table_name}")
                            rows = cursor.fetchall()
                            column_names = [description[0] for description in cursor.description]
                            for row in rows:
                                row_dict = dict(zip(column_names, row))
                                for k, v in row_dict.items():
                                    if v and isinstance(v, str) and (v.startswith("http://") or v.startswith("https://")) and len(v) < 300:
                                        parsed_url = urlparse(v)
                                        domain = parsed_url.netloc if parsed_url.netloc else "Unknown"
                                        if domain not in domain_data:
                                            domain_data[domain] = set()
                                            domain_sizes[domain] = 0
                                        domain_data[domain].add(v)
                                        domain_sizes[domain] += len(v.encode('utf-8'))
                            continue
                        except Exception:
                            continue

                    for row in rows:
                        url = row[0] if len(row) > 0 else ""
                        content = row[1] if len(row) > 1 else None

                        if url and isinstance(url, str) and (url.startswith("http://") or url.startswith("https://")) and len(url) < 300:
                            parsed_url = urlparse(url)
                            domain = parsed_url.netloc if parsed_url.netloc else "Unknown"

                            if domain not in domain_data:
                                domain_data[domain] = set()
                                domain_sizes[domain] = 0

                            domain_data[domain].add(url)

                            url_size = len(url.encode('utf-8'))
                            content_size = len(content) if content and isinstance(content, bytes) else (len(content.encode('utf-8')) if content and isinstance(content, str) else 0)
                            domain_sizes[domain] += (url_size + content_size)

                conn.close()
            except Exception as e:
                print(f"Error reading DB {db_path}: {e}")

        # إزالة سجلات البلجن القديمة من القائمة العامة لمنع تراكم الملفات وثقل الذاكرة
        self.app_instance.all_logs = [
            log for log in self.app_instance.all_logs if log.get("plugin_id") != "DB_VIEWER"
        ]

        new_plugin_logs = []

        # 1. علامة البداية
        start_list_text = "=== [ DOMAIN REGISTER ] ==="
        new_plugin_logs.append({
            "text": start_list_text,
            "category": "DB_RECORD",
            "plugin_id": "DB_VIEWER",
            "message": {"text": start_list_text},
        })

        # 2. إدراج الدومينات (تحديد أحدث 500 دومين فقط لمنع التهنيج إذا كانت القاعدة ضخمة جداً)
        sorted_domains = list(domain_data.items())[:500]
        for domain, urls in sorted_domains:
            total_bytes = domain_sizes.get(domain, 0)
            
            if total_bytes >= 1024 * 1024:
                size_str = f"{total_bytes / (1024 * 1024):.2f} MB"
            elif total_bytes >= 1024:
                size_str = f"{total_bytes / 1024:.2f} KB"
            else:
                size_str = f"{total_bytes} Bytes"

            log_text = f"[{size_str}] 🌐 {domain} (Total URLs: {len(urls)})"
            
            new_plugin_logs.append({
                "text": log_text,
                "category": "DB_RECORD",
                "plugin_id": "DB_VIEWER",
                "message": {"text": log_text, "size": size_str, "domain": domain, "urls": list(urls)},
            })

        # 3. علامة النهاية
        end_list_text = "=== [ End of Database Records List ] ==="
        new_plugin_logs.append({
            "text": end_list_text,
            "category": "DB_RECORD",
            "plugin_id": "DB_VIEWER",
            "message": {"text": end_list_text},
        })

        # دمج السجلات الجديدة بالذاكرة
        self.app_instance.all_logs.extend(new_plugin_logs)

        # تحديث الواجهة بحذر ودون تجميد (عبر إدخال دفعات سريعة)
        if hasattr(self.app_instance, "current_filter") and (self.app_instance.current_filter == "ALL" or self.app_instance.current_filter == "DB_VIEWER"):
            self.app_instance.listbox.delete(0, tk.END)
            # عرض السجلات المتوافقة مع الفلتر الحالي فقط وبدون إرهاق الواجهة
            filter_type = self.app_instance.current_filter
            display_items = [
                log["text"] for log in self.app_instance.all_logs 
                if filter_type == "ALL" or log.get("plugin_id") == filter_type
            ]
            
            # إدراج العناصر دفعة واحدة أو تقسيمها لو كانت ضخمة جداً
            for item in display_items:
                self.app_instance.listbox.insert(tk.END, item)
