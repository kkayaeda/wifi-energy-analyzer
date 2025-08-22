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
