import sqlite3
import zlib

DB_NAME = "cache_proxy.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA synchronous = OFF;")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            url TEXT PRIMARY KEY,
            content BLOB,
            content_type TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_url ON cache (url);')
    conn.commit()
    conn.close()

def save_to_cache(url, content, content_type):
    try:
        if not content:
            return
        compressed_content = zlib.compress(content, level=4)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO cache (url, content, content_type) VALUES (?, ?, ?)", 
            (url, compressed_content, content_type)
        )
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_from_cache(url):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT content, content_type FROM cache WHERE url = ?", (url,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            compressed_content, content_type = row
            try:
                content = zlib.decompress(compressed_content)
                return content, content_type
            except:
                return compressed_content, content_type
    except:
        pass
    return None
