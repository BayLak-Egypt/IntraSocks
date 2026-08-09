# -*- coding: utf-8 -*-
import datetime
import importlib.util
import json
import os
import sqlite3
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlparse

from PIL import Image, ImageTk

from crt import generate_ca, get_site_cert
from db import get_from_cache, init_db, save_to_cache
from errorweb import ERROR_HTML_TEMPLATE
from inject import INJECTED_TAG, UI_SCRIPT
import socks


CONFIG_FILE = "app_settings.json"


class ProxyApp:

    def __init__(self, root):
        self.root = root
        self.root.title("IntraSocks")
        
        # استرجاع آخر حجم وموضع تم حفظهما مسبقاً أو استخدام الافتراضي
        self.settings = self.load_settings()
        geometry = self.settings.get("geometry", "750x720")
        self.root.geometry(geometry)
        
        self.root.minsize(600, 600)
        self.root.configure(bg="#0f172a")

        # المتغيرات الإحصائية الحية
        self.total_domains = set()
        self.total_size_bytes = 0
        self.downloads_count = 0
        self.errors_count = 0
        self.requests_count = 0

        # ضبط وزن النافذة الرئيسية لتتجاوب مع التكبير والتصغير
        self.root.rowconfigure(3, weight=1)
        self.root.columnconfigure(0, weight=1)

        # --- Top Image Container (صورة ثابتة تماماً مع زيادة إضافية في الطول) ---
        self.image_frame = tk.Frame(root, bg="#0f172a")
        self.image_frame.pack(pady=8, fill=tk.X)

        self.img_label = tk.Label(self.image_frame, bg="#0f172a")
        self.img_label.pack(anchor=tk.CENTER)

        # تحميل الصورة بأبعاد ثابتة مع طول أكبر
        self.load_strictly_fixed_image("images/1.png")

        # Top Control Frame
        top_frame = tk.Frame(root, bg="#0f172a")
        top_frame.pack(pady=5, fill=tk.X, padx=10)

        tk.Label(top_frame, text="Host:", font=("Arial", 10, "bold"), fg="#e2e8f0", bg="#0f172a").pack(
            side=tk.LEFT, padx=2
        )
        self.host_entry = tk.Entry(
            top_frame, font=("Arial", 10), width=10, justify="center", bg="#1e293b", fg="white", insertbackground="white"
        )
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.pack(side=tk.LEFT, padx=3)

        tk.Label(top_frame, text="Port:", font=("Arial", 10, "bold"), fg="#e2e8f0", bg="#0f172a").pack(
            side=tk.LEFT, padx=2
        )
        self.port_entry = tk.Entry(
            top_frame, font=("Arial", 10), width=5, justify="center", bg="#1e293b", fg="white", insertbackground="white"
        )
        self.port_entry.insert(0, "8080")
        self.port_entry.pack(side=tk.LEFT, padx=3)

        self.start_btn = tk.Button(
            top_frame,
            text="Start Proxy",
            bg="#10b981",
            fg="white",
            font=("Arial", 9, "bold"),
            width=11,
            relief=tk.FLAT,
            command=self.toggle_proxy,
        )
        self.start_btn.pack(side=tk.LEFT, padx=8)

        # زر توليد وتصدير شهادة الأمان الجديد
        self.cert_btn = tk.Button(
            top_frame,
            text="Generate Cert",
            bg="#0284c7",
            fg="white",
            font=("Arial", 9, "bold"),
            width=12,
            relief=tk.FLAT,
            command=self.generate_and_export_cert,
        )
        self.cert_btn.pack(side=tk.LEFT, padx=4)

        self.status_label = tk.Label(
            top_frame, text="Stopped", fg="#ef4444", bg="#0f172a", font=("Arial", 10, "bold")
        )
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # --- Live Statistics Dashboard Frame ---
        stats_frame = tk.LabelFrame(
            root, text=" Live Statistics Dashboard ", font=("Arial", 9, "bold"), fg="#38bdf8", bg="#0f172a"
        )
        stats_frame.pack(pady=5, fill=tk.X, padx=10)

        row1_frame = tk.Frame(stats_frame, bg="#0f172a")
        row1_frame.pack(fill=tk.X, padx=5, pady=2)
        
        self.lbl_domains = tk.Label(row1_frame, text="Domains: 0", font=("Arial", 9, "bold"), fg="#60a5fa", bg="#0f172a")
        self.lbl_domains.pack(side=tk.LEFT, padx=8)

        self.lbl_size = tk.Label(row1_frame, text="Size: 0 KB", font=("Arial", 9, "bold"), fg="#c084fc", bg="#0f172a")
        self.lbl_size.pack(side=tk.LEFT, padx=8)

        self.lbl_downloads = tk.Label(row1_frame, text="Downloads: 0", font=("Arial", 9, "bold"), fg="#4ade80", bg="#0f172a")
        self.lbl_downloads.pack(side=tk.LEFT, padx=8)

        row2_frame = tk.Frame(stats_frame, bg="#0f172a")
        row2_frame.pack(fill=tk.X, padx=5, pady=2)

        self.lbl_errors = tk.Label(row2_frame, text="Errors: 0", font=("Arial", 9, "bold"), fg="#f87171", bg="#0f172a")
        self.lbl_errors.pack(side=tk.LEFT, padx=8)

        self.lbl_requests = tk.Label(row2_frame, text="Requests: 0", font=("Arial", 9, "bold"), fg="#fb923c", bg="#0f172a")
        self.lbl_requests.pack(side=tk.LEFT, padx=8)

        # --- Navigation & Plugins Frame ---
        self.nav_frame = tk.LabelFrame(
            root, text=" Navigation & Plugins ", font=("Arial", 9, "bold"), fg="#38bdf8", bg="#0f172a"
        )
        self.nav_frame.pack(pady=5, fill=tk.X, padx=10)

        self.nav_inner_frame = tk.Frame(self.nav_frame, bg="#0f172a")
        self.nav_inner_frame.pack(fill=tk.X, padx=5, pady=5)

        self.btn_all = tk.Button(
            self.nav_inner_frame,
            text="View All",
            bg="#22c55e",
            fg="white",
            font=("Arial", 9, "bold"),
            relief=tk.FLAT,
            command=lambda: self.filter_logs("ALL"),
        )
        self.btn_all.grid(row=0, column=0, padx=4, pady=3, sticky="w")

        # Container Frame
        self.container_frame = tk.Frame(root, bg="#0f172a")
        self.container_frame.pack(pady=5, fill=tk.BOTH, expand=True, padx=10)

        # Listbox Frame for Logs/Outputs
        list_frame = tk.Frame(self.container_frame, bg="#0f172a")
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 9),
            bg="#0b0f19",
            fg="#e2e8f0",
            selectbackground="#1e3a8a",
            selectforeground="white",
            relief=tk.FLAT,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scrollbar.set)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Context Menu
        self.context_menu = tk.Menu(self.listbox, tearoff=0, bg="#1e293b", fg="white")
        self.context_menu.add_command(
            label="Copy Selected", command=self.copy_selected_log
        )
        self.context_menu.add_command(label="Copy All", command=self.copy_all_logs)
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="Save to File...", command=self.save_logs_to_file
        )

        self.listbox.bind("<Button-3>", self.show_context_menu)

        self.plugins = {}
        self.plugin_buttons = {}
        self.current_filter = "ALL"
        self.all_logs = []

        self.server_thread = None
        self.is_running = False

        self.load_plugins()
        self.scan_databases_for_stats()

        last_filter = self.settings.get("last_filter", "ALL")
        if last_filter == "ALL" or last_filter in self.plugins:
            self.filter_logs(last_filter)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save_settings(self):
        try:
            current_geometry = self.root.geometry()
            self.settings["geometry"] = current_geometry
            self.settings["last_filter"] = self.current_filter
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def on_closing(self):
        self.save_settings()
        self.root.destroy()

    def load_strictly_fixed_image(self, path):
        """تحميل الصورة بأبعاد ثابتة مع زيادة الطول أكثر بناءً على طلبك"""
        try:
            if os.path.exists(path):
                img = Image.open(path)
                target_width = 210
                target_height = 68
                resized = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
                self.tk_img = ImageTk.PhotoImage(resized)
                self.img_label.config(image=self.tk_img)
        except Exception as e:
            print(f"Error loading strictly fixed image: {e}")

    def generate_and_export_cert(self):
        """دالة زر إنشاء وتصدير شهادة الأمان CA"""
        try:
            generate_ca()
            # البحث عن ملف الشهادة الافتراضي الذي تولده مكتبة crt (عادة ca.crt أو ما شابه)
            cert_filename = "ca.crt" # أو حسب المسمى المعتمد في مكتبة crt لديك
            if not os.path.exists(cert_filename):
                # فحص ملفات بديلة محتملة
                for f in os.listdir("."):
                    if f.endswith(".crt") or f.endswith(".pem"):
                        cert_filename = f
                        break

            if os.path.exists(cert_filename):
                dest_path = filedialog.asksaveasfilename(
                    defaultextension=".crt",
                    filetypes=[("Certificate Files", "*.crt"), ("PEM Files", "*.pem"), ("All Files", "*.*")],
                    initialfile="ca.crt",
                    title="Save CA Certificate"
                )
                if dest_path:
                    with open(cert_filename, "rb") as src, open(dest_path, "wb") as dst:
                        dst.write(src.read())
                    messagebox.showinfo("Success", f"CA Certificate successfully exported to:\n{dest_path}")
            else:
                messagebox.showwarning("Notice", "Certificate generated, but file path could not be automatically located for export.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate or export certificate: {e}")

    def scan_databases_for_stats(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        parent_dir = os.path.dirname(current_dir)

        db_files = []
        for d in [current_dir, parent_dir]:
            if os.path.exists(d):
                for f in os.listdir(d):
                    if f.endswith(".db"):
                        db_files.append(os.path.join(d, f))

        for db_path in db_files:
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()

                for table_row in tables:
                    table_name = table_row[0]
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
                                    self.total_domains.add(domain)
                                    self.total_size_bytes += len(v.encode('utf-8'))
                    except Exception:
                        continue
                conn.close()
            except Exception as e:
                print(f"Error scanning DB {db_path}: {e}")

        if self.total_size_bytes >= 1024 * 1024:
            size_formatted = f"{self.total_size_bytes / (1024 * 1024):.2f} MB"
        elif self.total_size_bytes >= 1024:
            size_formatted = f"{self.total_size_bytes / 1024:.2f} KB"
        else:
            size_formatted = f"{self.total_size_bytes} Bytes"

        self.lbl_domains.config(text=f"Domains: {len(self.total_domains)}")
        self.lbl_size.config(text=f"Size: {size_formatted}")

    def load_plugins(self):
        plugins_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "plugins"
        )
        if not os.path.exists(plugins_dir):
            os.makedirs(plugins_dir)

        col_index = 1
        row_index = 0

        for filename in os.listdir(plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                mod_name = filename[:-3]
                file_path = os.path.join(plugins_dir, filename)
                try:
                    spec = importlib.util.spec_from_file_location(mod_name, file_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)

                    if hasattr(mod, "Plugin"):
                        plugin_instance = mod.Plugin()
                        if hasattr(plugin_instance, "init_ui"):
                            plugin_instance.init_ui(self.container_frame, self)

                        p_id = getattr(plugin_instance, "PLUGIN_ID", mod_name.upper())
                        p_name = getattr(plugin_instance, "PLUGIN_NAME", mod_name)
                        self.plugins[p_id] = plugin_instance

                        btn = tk.Button(
                            self.nav_inner_frame,
                            text=p_name,
                            bg="#334155",
                            fg="white",
                            font=("Arial", 9),
                            relief=tk.FLAT,
                            command=lambda p=p_id: self.filter_logs(p),
                        )
                        
                        if col_index > 4:
                            col_index = 0
                            row_index += 1

                        btn.grid(row=row_index, column=col_index, padx=4, pady=3, sticky="w")
                        self.plugin_buttons[p_id] = btn
                        col_index += 1

                except Exception as e:
                    print(f"Error loading plugin {filename}: {e}")

    def update_live_stats(self, event_type, data):
        self.requests_count += 1

        if event_type in ["ERROR", "ERR"] or "error" in str(event_type).lower():
            self.errors_count += 1

        if event_type == "DOWNLOAD_PROGRESS":
            self.downloads_count += 1

        url_candidate = None
        content_size = 0

        if isinstance(data, dict):
            if "url" in data and data["url"]:
                url_candidate = data["url"]
            elif "text" in data and isinstance(data["text"], str):
                text_str = data["text"]
                if "http://" in text_str or "https://" in text_str:
                    for word in text_str.split():
                        if word.startswith("http://") or word.startswith("https://"):
                            url_candidate = word
                            break
            if "size" in data and isinstance(data["size"], (int, float)):
                content_size = data["size"]
        elif isinstance(data, str):
            if "http://" in data or "https://" in data:
                for word in data.split():
                    if word.startswith("http://") or word.startswith("https://"):
                        url_candidate = word
                        break

        if url_candidate:
            try:
                parsed = urlparse(url_candidate)
                if parsed.netloc:
                    self.total_domains.add(parsed.netloc)
            except:
                pass

        if content_size > 0:
            self.total_size_bytes += content_size
        elif url_candidate:
            self.total_size_bytes += len(url_candidate.encode("utf-8"))

        if self.total_size_bytes >= 1024 * 1024:
            size_formatted = f"{self.total_size_bytes / (1024 * 1024):.2f} MB"
        elif self.total_size_bytes >= 1024:
            size_formatted = f"{self.total_size_bytes / 1024:.2f} KB"
        else:
            size_formatted = f"{self.total_size_bytes} Bytes"

        self.lbl_domains.config(text=f"Domains: {len(self.total_domains)}")
        self.lbl_size.config(text=f"Size: {size_formatted}")
        self.lbl_downloads.config(text=f"Downloads: {self.downloads_count}")
        self.lbl_errors.config(text=f"Errors: {self.errors_count}")
        self.lbl_requests.config(text=f"Requests: {self.requests_count}")

    def filter_logs(self, filter_type):
        self.current_filter = filter_type

        if filter_type == "ALL":
            self.btn_all.config(bg="#22c55e", fg="white", font=("Arial", 9, "bold"))
        else:
            self.btn_all.config(bg="#334155", fg="white", font=("Arial", 9))

        for pid, btn in self.plugin_buttons.items():
            if pid == filter_type:
                btn.config(bg="#22c55e", fg="white", font=("Arial", 9, "bold"))
            else:
                btn.config(bg="#334155", fg="white", font=("Arial", 9))

        self.listbox.delete(0, tk.END)
        for log in self.all_logs:
            if filter_type == "ALL" or log.get("plugin_id") == filter_type:
                self.listbox.insert(tk.END, log["text"])

    def handle_event(self, event_type, timestamp, data):
        self.update_live_stats(event_type, data)

        if event_type == "DOWNLOAD_PROGRESS":
            for plugin in self.plugins.values():
                if hasattr(plugin, "on_event"):
                    plugin.on_event(event_type, timestamp, data)
            return

        for p_id, plugin in self.plugins.items():
            if hasattr(plugin, "filter") and hasattr(plugin, "on_event"):
                import copy
                data_copy = copy.deepcopy(data)
                
                if plugin.filter(event_type, data_copy):
                    plugin.on_event(event_type, timestamp, data_copy)
                    
                    if isinstance(data_copy, dict) and data_copy.get("text"):
                        text_val = data_copy["text"]
                        if f"[{event_type}]" in text_val:
                            log_text = f"[{timestamp}] {text_val}"
                        else:
                            log_text = f"[{timestamp}] [{event_type}] {text_val}"
                    else:
                        continue

                    log_entry = {
                        "text": log_text,
                        "category": event_type,
                        "plugin_id": p_id,
                        "message": data_copy,
                    }
                    self.all_logs.append(log_entry)

                    if self.current_filter == "ALL" or self.current_filter == p_id:
                        self.listbox.insert(tk.END, log_text)
                        self.listbox.see(tk.END)

    def show_context_menu(self, event):
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def copy_selected_log(self):
        try:
            selected_idx = self.listbox.curselection()
            if selected_idx:
                log_text = self.listbox.get(selected_idx[0])
                self.root.clipboard_clear()
                self.root.clipboard_append(log_text)
                messagebox.showinfo("Success", "Selected log copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy: {e}")

    def copy_all_logs(self):
        try:
            all_items = self.listbox.get(0, tk.END)
            if all_items:
                combined_text = "\n".join(all_items)
                self.root.clipboard_clear()
                self.root.clipboard_append(combined_text)
                messagebox.showinfo("Success", "All logs copied to clipboard!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy all: {e}")

    def save_logs_to_file(self):
        try:
            all_items = self.listbox.get(0, tk.END)
            if not all_items:
                messagebox.showwarning("Warning", "No logs to save!")
                return

            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
                title="Save Logs As",
            )

            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(all_items))
                messagebox.showinfo(
                    "Success", f"Logs successfully saved to:\n{file_path}"
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")

    def toggle_proxy(self):
        if not self.is_running:
            host = self.host_entry.get()
            try:
                port = int(self.port_entry.get())
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid port number!")
                return

            try:
                generate_ca()
                init_db()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to init DB/Cert: {e}")
                return

            has_plugins = len(self.plugins) > 0

            socks.configure_proxy({
                "save_cache": save_to_cache,
                "get_cache": get_from_cache,
                "get_cert": get_site_cert,
                "injected_tag": INJECTED_TAG,
                "ui_script": UI_SCRIPT,
                "error_template": ERROR_HTML_TEMPLATE,
                "event_callback": self.handle_event,
                "enable_plugins": has_plugins,
            })

            init_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            startup_msg = f"Proxy started successfully on http://{host}:{port}"
            self.handle_event("SERVER", init_time, startup_msg)

            self.server_thread = threading.Thread(
                target=socks.start_proxy_server, args=(host, port), daemon=True
            )
            self.server_thread.start()

            self.status_label.config(text="Running", fg="#4ade80")
            self.start_btn.config(text="Stop Proxy", bg="#ef4444")
            self.host_entry.config(state="disabled")
            self.port_entry.config(state="disabled")
            self.is_running = True
        else:
            socks.stop_proxy_server()
            stop_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.handle_event("SERVER", stop_time, "Proxy server stopped.")

            self.status_label.config(text="Stopped", fg="#ef4444")
            self.start_btn.config(text="Start Proxy", bg="#10b981")
            self.host_entry.config(state="normal")
            self.port_entry.config(state="normal")
            self.is_running = False


if __name__ == "__main__":
    root = tk.Tk()
    app = ProxyApp(root)
    root.mainloop()
