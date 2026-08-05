# IntraSocks ⚡

**IntraSocks** is an innovative local proxy and MitM system that caches web content locally in a database for offline browsing. It features a fully draggable floating UI to track network traffic and analyze page assets in real-time with ultimate flexibility.

---

## 🚀 Features

* **Local Caching & Offline Browsing:** Automatically saves web content (HTML, images, scripts) into a high-performance SQLite database.
* **HTTPS Support (MitM):** Dynamically generates local Root CA and site certificates to intercept and cache secure HTTPS traffic.
* **Draggable Floating UI (`Logs Menu`):** A sleek, fixed-size floating button that moves freely across the screen (both horizontally and vertically) with position persistence (`localStorage`).
* **Real-time Activity Logs:** Live tracking of resource loading, asset names, and statuses via a bottom status bar and a detailed logs modal.

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
   python3 socks.py
   ```
4. **Configure your browser or system** to use the local proxy:
   * **Host:** `127.0.0.1`
   * **Port:** `8080`
5. **Trust the Root CA:** Install and trust the generated `ca.crt` file in your system/browser certificate store to seamlessly inspect HTTPS traffic without warnings.

---

## 📦 Project Structure

* `socks.py` - Main Python script containing the HTTP/HTTPS proxy server, database handler, and injected UI script.
* `https_cache_proxy.db` - SQLite database for storing compressed web pages and assets.
* `certs/` - Directory containing dynamically generated local SSL/TLS certificates.

---

## 🛡️ License

This project is open-source and available for educational and developmental purposes.
