from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_cors import CORS
import subprocess
import re
import socket
import time
import sqlite3

# MAC vendor lookup için
try:
    from mac_vendor_lookup import MacLookup
    mac_lookup = MacLookup()
    mac_lookup.update_vendors()  # ilk çalışmada OUI veritabanını indir
except Exception as e:
    print("mac-vendor-lookup import error:", e)
    mac_lookup = None

app = Flask(__name__)
app.secret_key = "supersecretkey"  # session için gerekli
CORS(app)

# Cihaz listesi cache
devices_cache = []
last_updated = None  # Son güncelleme zamanını tutacak

def get_wifi_ip_base():
    try:
        output = subprocess.check_output("netsh wlan show interfaces", shell=True, text=True)
        match = re.search(r"IPv4 Address.*?:\s*(\d+\.\d+\.\d+)\.\d+", output)
        if match:
            return match.group(1)
    except Exception as e:
        print("get_wifi_ip_base error:", e)
    return "192.168.137"  # fallback

def ping_sweep(base_ip):
    for i in range(1, 10):
        ip = f"{base_ip}.{i}"
        try:
            subprocess.Popen(f"ping -n 1 -w 100 {ip}", shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

def resolve_hostname(ip):
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return "-"

def is_valid_device(ip, mac, base_ip):
    if not ip.startswith(base_ip):
        return False
    if ip.startswith("224.") or ip.startswith("239.") or ip.startswith("255."):
        return False
    if mac.lower() == "ff-ff-ff-ff-ff-ff":
        return False
    if mac.lower().startswith("01-00-5e"):
        return False
    if mac == "---":
        return False
    return True

def calculate_energy(minutes):
    per_minute_energy = 0.000667  # kWh/dk
    return round(minutes * per_minute_energy, 6)

def get_vendor(mac):
    if not mac_lookup:
        return "-"
    try:
        return mac_lookup.lookup(mac)
    except:
        return "-"

def scan_devices():
    global devices_cache, last_updated
    new_devices = []

    base_ip = get_wifi_ip_base()
    ping_sweep(base_ip)

    try:
        output = subprocess.check_output("arp -a", shell=True, text=True)
        for line in output.splitlines():
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]+)\s+(\w+)", line)
            if match:
                ip = match.group(1)
                mac = match.group(2)
                if is_valid_device(ip, mac, base_ip):
                    existing = next((d for d in devices_cache if d["mac"] == mac), None)
                    connected_since = existing["connected_since"] if existing else time.time()
                    connected_minutes = int((time.time() - connected_since) / 60)
                    energy_kwh = calculate_energy(connected_minutes)
                    vendor = get_vendor(mac)

                    new_devices.append({
                        "ip": ip,
                        "mac": mac,
                        "hostname": resolve_hostname(ip),
                        "vendor": vendor,
                        "connected_since": connected_since,
                        "connectiontime": f"{connected_minutes} min",
                        "energy": f"{energy_kwh} kWh"
                    })
    except Exception as e:
        print("Scan error:", e)

    devices_cache = new_devices
    last_updated = time.strftime("%Y-%m-%d %H:%M:%S")

@app.route("/devices", methods=["GET"])
def get_devices():
    return jsonify({
        "devices": devices_cache,
        "count": len(devices_cache),
        "last_updated": last_updated
    })

@app.route("/scan", methods=["POST"])
def start_scan():
    if "username" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    scan_devices()
    return jsonify({
        "status": "scanning started",
        "count": len(devices_cache),
        "last_updated": last_updated
    })

@app.route("/")
def index():
    global last_updated
    logged_in = "username" in session
    if last_updated is None and logged_in:
        scan_devices()
    return render_template("index.html",
                           device_count=len(devices_cache),
                           last_updated=last_updated,
                           logged_in=logged_in)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        session["username"] = username
        return redirect(url_for("index"))
    else:
        return "Invalid credentials, please try again."

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
