# -*- coding: utf-8 -*-
import os
import base64
import json

# قراءة الصور تنازلياً (3, ثم 2, ثم 1)
frames_base64 = []
for i in [3, 2, 1]:
    image_path = f"images/{i}.png"
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            encoded = base64.b64encode(img_file.read()).decode('utf-8')
            frames_base64.append(f"data:image/png;base64,{encoded}")

frames_json = json.dumps(frames_base64)

ERROR_HTML_TEMPLATE = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Connection Error - Network Unavailable</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}

        .error-card {{
            background-color: #1e293b;
            border: 1px solid #334155;
            padding: 50px 40px;
            border-radius: 20px;
            box-shadow: 0 20px 35px -5px rgba(0, 0, 0, 0.6);
            max-width: 480px;
            width: 100%;
            text-align: center;
            box-sizing: border-box;
            margin-left: 155px; 
        }}

        .icon-container img {{
            width: 96px;
            height: 96px;
            object-fit: contain;
            margin-bottom: 24px;
        }}

        h1 {{
            color: #f8fafc;
            font-size: 24px;
            margin-bottom: 15px;
            font-weight: 600;
        }}

        p {{
            color: #94a3b8;
            font-size: 15px;
            line-height: 1.6;
            margin-bottom: 30px;
        }}

        .btn {{
            background-color: #38bdf8;
            color: #0f172a;
            padding: 12px 28px;
            border: none;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            display: inline-block;
            transition: background-color 0.2s;
        }}

        .btn:hover {{
            background-color: #0ea5e9;
        }}
    </style>
</head>
<body>
    <div class="error-card">
        <div class="icon-container">
            <img id="error-icon" src="" alt="Error Icon">
        </div>
        <h1>Page Not Found or Offline</h1>
        <p>The requested page could not be loaded. Please ensure you have an active connection to the intranet or local network to proceed.</p>
        <button class="btn" onclick="location.reload();">Try Again</button>
    </div>

    <script>
        const frames = {frames_json};
        
        if (frames.length > 0) {{
            let currentIndex = 0;
            const imgElement = document.getElementById('error-icon');
            
            imgElement.src = frames[0];
            
            if (frames.length > 1) {{
                // حركة ثابتة وبطيئة (كل 900 ملي ثانية يتغير الفريم بانتظام)
                setInterval(() => {{
                    currentIndex = (currentIndex + 1) % frames.length;
                    imgElement.src = frames[currentIndex];
                }}, 900);
            }}
        }}
    </script>
</body>
</html>
"""
