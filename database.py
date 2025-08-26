# database.py
import sqlite3
from datetime import datetime

DB_NAME = "database.db"

def insert_energy(total_energy, cost, co2):
    """
    Var olan 'energy' tablosuna yeni satır ekler.
    Tablo sütunları: total_energy, cost, co2, date
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO energy (total_energy, cost, co2, date)
            VALUES (?, ?, ?, ?)
        """, (
            total_energy,
            cost,
            co2,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

        conn.commit()
        print(f"Inserted: energy={total_energy}, cost={cost}, co2={co2}")
    except Exception as err:
        print("DB insert error:", err)
    finally:
        conn.close()


def upsert_devices(ip, mac, device_name, energy):
    """
    Var olan 'devices' tablosuna yeni satır ekler veya günceller.
    Tablo sütunları: ip, mac, device_name, connection_time, energy, date
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        now = datetime.now()

        # Daha önce eklenmiş mi diye kontrol et
        cursor.execute("SELECT id, connection_time, energy, date FROM devices WHERE ip=? OR mac=?", (ip, mac))
        row = cursor.fetchone()

        if row:
            # row: id, connection_time, energy, date
            prev_time_str = row[3]
            prev_time = datetime.strptime(prev_time_str, "%Y-%m-%d %H:%M:%S")

            # Varsayılan değerler
            total_energy = energy  # yeni eklenen satır için energy
            
            # Geçen dakikayı hesapla
            minutes_passed = int((now - prev_time).total_seconds())
            total_seconds = minutes_passed
            total_minutes = (total_seconds / 60)

            if minutes_passed > 0:
                prev_minutes = int(row[1].replace(" min", ""))
                total_minutes = prev_minutes + minutes_passed
                total_energy = row[2] + energy

            cursor.execute("""
                UPDATE devices
                SET connection_time=?, energy=?, date=?
                WHERE id=?
            """, (f"{total_minutes} min", total_energy, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), row[0]))
        else:
            # Yoksa yeni satır ekle
            cursor.execute("""
                INSERT INTO devices (ip, mac, device_name, connection_time, energy, date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (ip, mac, device_name, f"{minutes_passed} min", energy, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        print(f"Upserted: ip={ip}, mac={mac}, device_name={device_name}, connection_time={total_minutes}, energy={energy}")

    except Exception as err:
        print("DB upsert device error:", err)
    finally:
        conn.close()
