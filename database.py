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
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        now = datetime.now()

        # Daha önce eklenmiş mi diye kontrol et
        cursor.execute("SELECT id, connection_time, energy, date FROM devices WHERE ip=? OR mac=?", (ip, mac))
        row = cursor.fetchone()

        if row:
            if isinstance(energy, str):
                energy = float(energy.replace(" kWh", ""))
            try:
                prev_minutes = int(row[1].replace(" min", "")) 
            except:
                prev_minutes = 0

            try:
                prev_energy = float(row[2])
            except:
                prev_energy = 0

            # total_energy güncellemesi
            total_energy = round(prev_energy + energy, 4)

            added_minutes = 1 
            total_minutes = prev_minutes + added_minutes

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
            """, (ip, mac, device_name, f"{total_minutes} min", float(energy), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        print(f"Upserted: ip={ip}, mac={mac}, device_name={device_name}, connection_time={total_minutes}, energy={energy}")

    except Exception as err:
        print("DB upsert device error:", err)
    finally:
        conn.close()
