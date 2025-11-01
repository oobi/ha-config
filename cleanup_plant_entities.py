#!/usr/bin/env python3
import json, shutil, os

ENTITY_FILE = "/config/.storage/core.entity_registry"
DEVICE_FILE = "/config/.storage/core.device_registry"

def backup_file(path):
    backup_path = f"{path}.backup"
    shutil.copy(path, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

print("🌿 Cleaning up old plant sensor entities and devices...")

# --- Backup ---
backup_file(ENTITY_FILE)
backup_file(DEVICE_FILE)

# --- Load data ---
entities_data = load_json(ENTITY_FILE)
devices_data = load_json(DEVICE_FILE)

entities = entities_data["data"]["entities"]
devices = devices_data["data"]["devices"]

# --- Identify plant-related entities ---
plant_entities = [e for e in entities if e["entity_id"].startswith("sensor.plant_")]
plant_device_ids = {e["device_id"] for e in plant_entities if e.get("device_id")}

print(f"🔍 Found {len(plant_entities)} plant entities linked to {len(plant_device_ids)} devices.")

# --- Filter out plant entities ---
entities_data["data"]["entities"] = [
    e for e in entities if e["entity_id"] not in [pe["entity_id"] for pe in plant_entities]
]

# --- Filter out devices associated with those entities ---
devices_data["data"]["devices"] = [
    d for d in devices if d["id"] not in plant_device_ids
]

# --- Save cleaned versions ---
save_json(ENTITY_FILE, entities_data)
save_json(DEVICE_FILE, devices_data)

print(f"✅ Removed {len(plant_entities)} entities and {len(plant_device_ids)} devices.")
print("⚠️ Restart Home Assistant Core to let it rebuild from clean state.")
print("💡 Backups were made before modification.")