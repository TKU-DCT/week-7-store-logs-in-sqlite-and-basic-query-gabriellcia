import psutil
from datetime import datetime
import sqlite3
import os
import time
import subprocess
import platform
import re
import pandas as pd   # <— untuk export CSV

DB_NAME = "log.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            cpu REAL,
            memory REAL,
            disk REAL,
            ping_status TEXT,
            ping_ms REAL
        )
    """)
    conn.commit()
    conn.close()

def get_system_info():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    ping_status, ping_ms = ping_host("8.8.8.8")
    return (now, cpu, memory, disk, ping_status, ping_ms)

def ping_host(host):
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        out = subprocess.check_output(
            ["ping", param, "1", host],
            stderr=subprocess.DEVNULL
        ).decode(errors="ignore")
        ms = parse_ping_time(out)
        return ("UP", ms if ms is not None else -1.0)
    except Exception:
        return ("DOWN", -1.0)

_time_re = re.compile(r"time[=<]\s*([0-9]*\.?[0-9]+)\s*ms", re.IGNORECASE)

def parse_ping_time(output: str):
    """Linux/macOS: 'time=17.2 ms'; Windows: 'time<1ms' / 'time=2ms'."""
    m = _time_re.search(output)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None

def insert_log(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO system_log (timestamp, cpu, memory, disk, ping_status, ping_ms)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        data,
    )
    conn.commit()
    conn.close()

def show_last_entries(limit=5):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_log ORDER BY id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()[::-1]
    print("\n... Last {} entries:".format(min(limit, len(rows))))
    for row in rows:
        print(row)
    cursor.execute("SELECT COUNT(*) FROM system_log")
    total = cursor.fetchone()[0]
    print(f"\nTotal records in database: {total}")
    conn.close()


def show_down_entries():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM system_log WHERE ping_status='DOWN'")
    rows = cursor.fetchall()
    print("\n=== Entries with DOWN ping status ===")
    if not rows:
        print("No DOWN entries found.")
    else:
        for row in rows:
            print(row)
    conn.close()


def export_to_csv(csv_path="log.csv"):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM system_log ORDER BY id ASC", conn)
    df.to_csv(csv_path, index=False)
    conn.close()
    print(f"\n✅ Exported {len(df)} rows to {csv_path}")

if __name__ == "__main__":
    init_db()
    for _ in range(5):
        row = get_system_info()
        insert_log(row)
        print("Logged:", row)
        time.sleep(10)
    show_last_entries()
    show_down_entries()  
    export_to_csv("log.csv")  
