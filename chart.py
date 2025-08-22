# chart.py
from datetime import datetime, timedelta
import random
from database import insert_energy   # ✅ veritabanı fonksiyonu eklendi

# Örnek veri tutucu (sürekli güncellenen)
labels = []
energy_values = []
cost_values = []
co2_values = []

COST_PER_KWH = 2.6
CO2_PER_KWH = 0.475

def generate_minute_data():
    """Dakikalık veri üretir ve listelere ekler"""
    global labels, energy_values, cost_values, co2_values

    minute = len(labels) + 1
    energy = round(random.uniform(0.01, 0.05), 4)  # kWh
    cost = round(energy * COST_PER_KWH, 2)
    co2 = round(energy * CO2_PER_KWH, 3)

    labels.append(str(minute))
    energy_values.append(energy)
    cost_values.append(cost)
    co2_values.append(co2)

    insert_energy(energy, cost, co2)

    # Son 60 dakikayı sakla
    if len(labels) > 60:
        labels.pop(0)
        energy_values.pop(0)
        cost_values.pop(0)
        co2_values.pop(0)

def get_chart_data():
    """Chart.js için JSON formatında veri döndürür"""
    return {
        "labels": labels,
        "energy": energy_values,
        "cost": cost_values,
        "co2": co2_values
    }

