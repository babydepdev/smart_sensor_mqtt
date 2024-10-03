import network
import time
from umqtt.simple import MQTTClient
from machine import RTC, ADC, Pin
import ujson  # For JSON serialization
import dht

SSID = 'bi2sb2te3'  # กำหนด SSID Wifi
PASSWORD = '94dda6f6'  # กำหนด Password Wifi

mqtt_host = "www.somha-iot.com"
mqtt_username = "ajbear"
mqtt_password = "ajbear1969"
mqtt_publish_topic = "ajbear/bar"
mqtt_client_id = "beariot_smart_sensor"

mqtt_client = None

# สร้าง Payload เตรียมส่งข้อมูล
def generate_payload(value):
    rtc = RTC()
    current_time = rtc.datetime()
    iso_format = '{}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:06d}+00:00'.format(
        current_time[0], current_time[1], current_time[2],
        current_time[4], current_time[5], current_time[6], current_time[7])
    print(iso_format)
    
    return {
        "siteID": 'KMe45f01d94cbf',
        "deviceID": 3,
        "date": iso_format,
        "offset": -420,
        "connection": 'MQTT',
        "tagObj": [{
            "status": True,
            "label": 'temp',
            "value": value,
        },{
            "status": True,
            "label": 'test',
            "value": 0,
        }]
    }

# เชื่อมต่อ WIFI
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(ssid, password)

    while not wlan.isconnected():
        time.sleep(1)
        print("Waiting for connection...")
    
    print("Connected to Wi-Fi:", wlan.ifconfig())

# ตรวจสอบและเชื่อมต่อใหม่ถ้า Wi-Fi หลุด
def ensure_wifi_connected(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    
    if not wlan.isconnected():
        print("Wi-Fi disconnected, reconnecting...")
        wlan.disconnect()  # Ensure disconnection before reconnecting
        connect_wifi(ssid, password)

# เชื่อมต่อ MQTT
def connect_mqtt():
    global mqtt_client
    mqtt_client = MQTTClient(
        client_id=mqtt_client_id,
        server=mqtt_host,
        user=mqtt_username,
        password=mqtt_password
    )
    mqtt_client.connect()

# ตรวจสอบและเชื่อมต่อใหม่ถ้า MQTT หลุด
def ensure_mqtt_connected():
    global mqtt_client
    try:
        mqtt_client.ping()  # Check MQTT connection with a ping
    except:
        print("MQTT disconnected, reconnecting...")
        connect_mqtt()

# ส่งข้อมูลไปยัง MQTT Broker
def publish_data(mqtt_client, topic, payload):
    payload_str = ujson.dumps(payload)  # Convert the payload to JSON string
    print(payload_str)
    mqtt_client.publish(topic, payload_str.encode('utf-8'))  # Send as bytes

# Main execution
connect_wifi(SSID, PASSWORD)
connect_mqtt()

while True:
    ensure_wifi_connected(SSID, PASSWORD)  # ตรวจสอบ Wi-Fi ทุกลูป
    ensure_mqtt_connected()  # ตรวจสอบ MQTT ทุกลูป

    try:
        sensor = dht.DHT22(Pin(15))
        sensor.measure()
        temp_value = sensor.temperature()
        payload = generate_payload(temp_value)  # Generate new payload
        publish_data(mqtt_client, mqtt_publish_topic, payload)  # Publish the data
    except OSError as e:
        print("Error reading sensor:", e)

    time.sleep(3)  # Wait for 3 seconds before the next iteration
