from datetime import datetime

# veri tutucu (sürekli güncellenen)
labels = []
energy_values = []
cost_values = []
co2_values = []

def update_chart_data(total_energy, total_cost, total_co2):
    """App.py'den gelen gerçek enerji verilerini grafiğe ekler"""
    global labels, energy_values, cost_values, co2_values

    minute = len(labels) + 1  # kaçıncı dakika
    labels.append(str(minute))
    energy_values.append(total_energy)
    cost_values.append(total_cost)
    co2_values.append(total_co2)

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
