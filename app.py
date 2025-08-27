from flask import Flask, jsonify, render_template
from flask_cors import CORS
import subprocess
import re
import socket
import time
from datetime import datetime
from database import insert_energy, upsert_devices 
from chart import update_chart_data
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
CORS(app)


# Cihaz listesi cache
devices_cache = []
last_updated = None  # Son güncelleme zamanı

# Energy history (grafik için)
energy_history = []
cost_history = []
co2_history = []
time_labels = []

def get_wifi_ip_base():
    try:
        output = subprocess.check_output("netsh wlan show interfaces", shell=True, text=True)
        match = re.search(r"IPv4 Address.*?:\s*(\d+\.\d+\.\d+)\.\d+", output)
        if match:
            return match.group(1)
    except Exception as e:
        print("get_wifi_ip_base error:", e)
    return "192.168.137" 

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

def is_alive(ip):
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", ip],  # Windows
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return result.returncode == 0
    except Exception:
        return False

def scan_devices():
    global devices_cache, last_updated
    new_devices = []

    base_ip = get_wifi_ip_base()
    ping_sweep(base_ip)

    try:
        output = subprocess.check_output("arp -a", shell=True, text=True)
        current_macs = set()  # Bu taramada görülen MAC'ler

        for line in output.splitlines():
            match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([\w-]+)\s+(\w+)", line)
            if match:
                ip = match.group(1)
                mac = match.group(2)

                # Gateway IP'yi atla
                if ip == f"{base_ip}.1":
                    continue

                if is_valid_device(ip, mac, base_ip):
                    alive = is_alive(ip)
                    if not alive:
                        continue  # Ping yoksa listeden düş

                    current_macs.add(mac)
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
                        "energy": round(energy_kwh, 6),          # float olarak sakla
                        "energy_str": f"{energy_kwh} kWh",       # string gösterim
                        "status": "Online"
                    })
                    try:
                        upsert_devices(ip, mac, resolve_hostname(ip), f"{energy_kwh} kWh")
                    except Exception as e:
                        print(f"DB upsert error for {ip} / {mac}:", e)


    except Exception as e:
        print("Scan error:", e)

    devices_cache = new_devices
    last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Energy history güncelle
    total_energy = sum(d["energy"] for d in devices_cache)
    energy_history.append(total_energy)
    cost_history.append(round(total_energy * 2.6, 2))
    co2_history.append(round(total_energy * 0.475, 3))
    time_labels.append(datetime.now().strftime("%H:%M"))
    total_cost = round(total_energy * 2.6, 2)
    total_co2 = round(total_energy * 0.475, 3)


    update_chart_data(total_energy, total_cost, total_co2)
    insert_energy(total_energy, total_cost, total_co2)
    


@app.route("/devices", methods=["GET"])
def get_devices():
    return jsonify({
        "devices": devices_cache,
        "count": len(devices_cache),
        "last_updated": last_updated
    })

@app.route("/scan", methods=["POST"])
def start_scan():
    scan_devices()
    return jsonify({
        "devices": devices_cache,
        "count": len(devices_cache),
        "last_updated": last_updated
    })

@app.route("/energy_data", methods=["GET"])
def energy_data():
    # Son 60 dakika verisini gönder
    return jsonify({
        "labels": time_labels[-60:],
        "energy": energy_history[-60:],
        "cost": cost_history[-60:],
        "co2": co2_history[-60:]
    })

@app.route("/")
def index():
    global last_updated
    if last_updated is None:
        scan_devices()
    return render_template("index.html",
                           device_count=len(devices_cache),
                           last_updated=last_updated)

# Devices tablosundaki verileri çek (History için)
DB_NAME = "database.db"

@app.route("/api/devices", methods=["GET"])
def api_devices():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT ip, mac, device_name, connection_time, energy, date FROM devices")
        rows = cursor.fetchall()
        conn.close()

        devices = [
            {
                "ip": row[0],
                "mac": row[1],
                "device_name": row[2],
                "connection_time": row[3],
                "energy": row[4],
                "date": row[5]
            } for row in rows
        ]
        return jsonify(devices)
    except Exception as e:
        return jsonify({"error": str(e)})

# Energy tablosundaki verileri çek (History için)
@app.route("/api/energy", methods=["GET"])
def api_energy():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT total_energy, cost, co2, date FROM energy")
        rows = cursor.fetchall()
        conn.close()

        energy = [
            {
                "total_energy": row[0],
                "cost": row[1],
                "co2": row[2],
                "date": row[3]
            } for row in rows
        ]
        return jsonify(energy)
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
