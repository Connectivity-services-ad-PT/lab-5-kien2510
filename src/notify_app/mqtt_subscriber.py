import json
import logging
import os
import threading
import ssl
import paho.mqtt.client as mqtt
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MQTT_BROKER = os.getenv("MQTT_BROKER", "f6f78e87db4a4c189dd3d706745a5e93.s1.eu.hivemq.cloud")
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "DVKN_IOT_2026")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "ThaiBao12A@")
MQTT_TOPICS = [
    "smart-campus/events/sensor",
    "smart-campus/events/access",
]
NOTIFY_URL = os.getenv("NOTIFY_URL", "http://localhost:8007/api/notifications")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "local-dev-token")


def handle_sensor_event(payload: dict):
    event_id = payload.get("event_id", "")
    
    if event_id and event_id in PROCESSED_EVENTS:
        logger.info(f"Duplicate event {event_id}, skipping")
        return
    
    alert_level = payload.get("alert_level", "none")
    status = payload.get("status", "")
    
    if alert_level not in ("high", "critical") and status != "danger":
        return
    
    location = payload.get("location") or payload.get("device_id", "unknown")
    temp = payload.get("temperature_c", "?")
    reason = payload.get("reason", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    severity = "CRITICAL" if alert_level == "critical" else "HIGH"
    
    message = (
        f"🚨 SYSTEM ALERT [{severity}]\n"
        f"📋 Loại: HIGH_TEMPERATURE\n"
        f"📍 Vị trí: {location}\n"
        f"🌡️ Nhiệt độ: {temp}°C\n"
        f"⚠️ Lý do: {reason}\n"
        f"⏰ {timestamp}"
    )
    
    requests.post(
        NOTIFY_URL,
        json={
            "user_id": "system",
            "title": f"[{severity}] HIGH_TEMPERATURE Alert",
            "message": message,
            "channel": "inapp",
        },
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        timeout=5,
    )
    
    if event_id:
        PROCESSED_EVENTS.add(event_id)
    
    logger.info(f"Sent HIGH_TEMPERATURE notification for {location}")


def handle_access_event(payload: dict):
    event_id = payload.get("event_id", "")
    
    if event_id and event_id in PROCESSED_EVENTS:
        logger.info(f"Duplicate event {event_id}, skipping")
        return
    
    access_result = payload.get("access_result", "")
    if access_result != "denied":
        return
    
    name = payload.get("full_name") or "Unknown"
    uid = payload.get("uid", "unknown")
    door = payload.get("door_id", "unknown")
    reason = payload.get("reason", "unknown")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    message = (
        f"🚫 SYSTEM ALERT [HIGH]\n"
        f"📋 Loại: ACCESS_DENIED\n"
        f"🚪 Cổng: {door}\n"
        f"👤 Người dùng: {name} (UID: {uid})\n"
        f"⚠️ Lý do: {reason}\n"
        f"⏰ {timestamp}"
    )
    
    requests.post(
        NOTIFY_URL,
        json={
            "user_id": "system",
            "title": "[HIGH] ACCESS_DENIED Alert",
            "message": message,
            "channel": "inapp",
        },
        headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
        timeout=5,
    )
    
    if event_id:
        PROCESSED_EVENTS.add(event_id)
    
    logger.info(f"Sent ACCESS_DENIED notification for {name} at {door}")


def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        logger.info("Connected to HiveMQ broker")
        for topic in MQTT_TOPICS:
            client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")
    else:
        logger.error(f"Failed to connect, reason code: {reason_code}")


def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        logger.info(f"Received message on {msg.topic}: {payload}")
        if msg.topic == "smart-campus/events/sensor":
            handle_sensor_event(payload)
        elif msg.topic == "smart-campus/events/access":
            handle_access_event(payload)
    except Exception as e:
        logger.error(f"Error processing message: {e}")


def start_mqtt_subscriber():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
    client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    thread = threading.Thread(target=client.loop_forever, daemon=True)
    thread.start()
    logger.info("MQTT subscriber started in background")