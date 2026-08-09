# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk


class Plugin:
    PLUGIN_ID = "DOWNLOADS"
    PLUGIN_NAME = "Downloads"

    def __init__(self):
        self.progress_label = None
        self.progress_bar = None
        self.active_downloads = {}

    def init_ui(self, container_frame, app_instance):
        progress_frame = tk.LabelFrame(
            container_frame, 
            text=" Download Progress ", 
            font=("Arial", 9, "bold"),
            fg="#38bdf8",
            bg="#0f172a",
            bd=1,
            relief=tk.GROOVE
        )
        progress_frame.pack(
            pady=5, fill=tk.X, padx=5, before=app_instance.listbox.master
        )

        self.progress_label = tk.Label(
            progress_frame,
            text="No active downloads",
            font=("Arial", 9, "bold"),
            fg="#60a5fa",
            bg="#0f172a",
            anchor="w",
        )
        self.progress_label.pack(fill=tk.X, padx=5, pady=2)

        # تخصيص مظهر شريط التقدم ليتطابق مع الثيم الداكن
        style = ttk.Style()
        style.theme_use('default')
        style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor='#1e293b',
            background='#0284c7',
            darkcolor='#0284c7',
            lightcolor='#38bdf8',
            bordercolor='#0f172a'
        )

        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient="horizontal", 
            mode="determinate", 
            length=700,
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

    def filter(self, category, message):
        return category == "DOWNLOAD_END"

    def on_event(self, event_type, timestamp, data):
        if not isinstance(data, dict):
            return

        dl_id = data.get("id")

        if event_type == "DOWNLOAD_START":
            self.active_downloads[dl_id] = {
                "filename": data.get("filename", "Unknown"),
                "total_size": data.get("total_size", 0),
            }

            filename = data.get("filename", "Unknown")
            total_size = data.get("total_size", 0)
            size_str = (
                f"{total_size / 1024:.2f} KB" if total_size > 0 else "Unknown Size"
            )

            def _start_ui():
                if self.progress_label and self.progress_label.winfo_exists():
                    self.progress_label.config(text=f"File: {filename} | Size: {size_str}", fg="#38bdf8")
                    if total_size > 0:
                        self.progress_bar.config(
                            maximum=total_size, value=0, mode="determinate"
                        )
                    else:
                        self.progress_bar.config(mode="indeterminate")
                        self.progress_bar.start(10)

            if self.progress_label:
                self.progress_label.after(0, _start_ui)

        elif event_type == "DOWNLOAD_PROGRESS":
            downloaded = data.get("downloaded", 0)
            if dl_id in self.active_downloads:
                self.active_downloads[dl_id]["downloaded"] = downloaded

            def _prog_ui():
                total_size = self.active_downloads.get(dl_id, {}).get("total_size", 0)
                if total_size > 0 and self.progress_bar:
                    self.progress_bar.config(value=downloaded)

            if self.progress_bar:
                self.progress_bar.after(0, _prog_ui)

        elif event_type == "DOWNLOAD_END":
            dl_info = self.active_downloads.get(
                dl_id, {"filename": data.get("filename", "Unknown"), "total_size": 0}
            )
            filename = dl_info["filename"]
            total_size = dl_info["total_size"]
            size_str = (
                f"{total_size / 1024:.2f} KB" if total_size > 0 else "Unknown Size"
            )

            def _end_ui():
                if self.progress_bar and self.progress_bar.winfo_exists():
                    self.progress_bar.stop()
                    if "error" in data:
                        self.progress_label.config(text=f"Download Failed: {filename}", fg="#f87171")
                    else:
                        self.progress_bar.config(
                            mode="determinate", value=self.progress_bar["maximum"]
                        )
                        self.progress_label.config(
                            text=f"File: {filename} | Size: {size_str} - [Completed]", fg="#4ade80"
                        )

            if self.progress_label:
                self.progress_label.after(0, _end_ui)

            if "error" in data:
                error_msg = data.get("error")
                formatted_text = f"[FAILED] File: {filename} | Reason: {error_msg}"
            else:
                formatted_text = f"[SUCCESS] File: {filename} | Size: {size_str}"

            data.clear()
            data.update({"text": formatted_text})

            if dl_id in self.active_downloads:
                del self.active_downloads[dl_id]
