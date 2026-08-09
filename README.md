# IntraSocks ⚡

<p align="center">
  <img src="https://github.com/user-attachments/assets/43f1fc8b-acbc-4877-af74-d180f2e29208" alt="Redmo Logo" width="300">
</p>




**IntraSocks** is an innovative local proxy and MitM system that caches web content locally in a database for offline browsing. It features a fully draggable floating UI to track network traffic and analyze page assets in real-time with ultimate flexibility.

---

<p align="center">

<img width="602" height="638" alt="image" src="https://github.com/user-attachments/assets/a36e1a1a-3fab-433c-ba69-a8f4a77421e1" />
</p>

## 🚀 Features

* **Local Caching & Offline Browsing:** Automatically saves web content (HTML, images, scripts) into a high-performance SQLite database.
* **HTTPS Support (MitM):** Dynamically generates local Root CA and site certificates to intercept and cache secure HTTPS traffic.
* **Draggable Floating UI (`Logs Menu`):** A sleek, fixed-size floating button that moves freely across the screen (both horizontally and vertically) with position persistence (`localStorage`).
* **Real-time Activity Logs:** Live tracking of resource loading, asset names, and statuses via a bottom status bar and a detailed logs modal.
* **Integrated Proxy Server:** Easily start and stop a local proxy server with control over the Host and Port.
* **Certificate Generation & Export:** A dedicated (`Generate Cert`) button to create and export digital security certificates directly to any chosen location with a single click.
* **Cohesive Dark Theme:** A modern and unified design (`#0f172a` and `#1e293b`) covering buttons, dropdown menus, and control elements.
* **Live Statistics Dashboard:** Direct tracking of unique domains, total data size, downloads, errors, and total requests.
* **Flexible Plugins System:** Dynamic loading of custom functionality, enabling seamless extensibility without modifying the core codebase.

---

## 🛠️ Requirements & Prerequisites

* Python 3.x
* OpenSSL (required for generating local Root CA and HTTPS certificates)

---

## ⚙️ Installation & Running

1. **Clone or download the project files.**
2. **Open your terminal** in the project directory.
3. **Run the script:**
   ```bash
   python3 main.py
   ```
4. **Configure your browser or system** to use the local proxy:
   * **Host:** `127.0.0.1`
   * **Port:** `8080`
5. **Trust the Root CA:** Install and trust the generated `ca.crt` file in your system/browser certificate store to seamlessly inspect HTTPS traffic without warnings.

---

## 📦 Project Structure

```text
IntraSocks/
│
├── main.py              # Main GUI entry point, server management, and UI logic
├── socks.py             # Proxy server backend, connection handling, and injection logic
├── crt.py               # Security certificate (CA) generation and management
├── db.py                # SQLite database management for caching and logging
├── errorweb.py          # HTML error page templates
├── inject.py            # Scripts for web content injection
├── app_settings.json    # Persistent user settings (theme, window geometry, etc.)
│
├── images/
│   └── 1.png            # Application logo and fixed-dimension assets
│
└── plugins/             # Extensible plugin architecture
    ├── db_dir.py        # Database directory management and handling plugin
    ├── db_viewer.py     # Database records and content viewer interface plugin
    ├── filter_browser.py# Browser request filtering and handling plugin
    ├── filter_download.py# Download progress and file transfer filtering plugin
    └── filter_site.py   # Domain/site filtering and routing control plugin
```


## 🛡️ License

This project is open-source and available for educational and developmental purposes.


---

**Made with ❤️ by BayLak (Egypt <img src="https://github.com/user-attachments/assets/637a365d-98e8-4a47-814c-11965370d212" width="35" height="15" alt="Egypt flag"/>)**


