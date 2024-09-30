import network
import time
from umqtt.simple import MQTTClient
from machine import RTC, ADC
import ujson  
import dht
from machine import Pin

# Wifi Config
SSID = 'bi2sb2te3'  # กำหนด SSID Wifi
PASSWORD = '94dda6f6'  # กำหนด Password Wifi

# MQTT config
mqtt_host = "www.somha-iot.com" #กำหนด HOST Broker MQTT
mqtt_username = "ajbear" # กำหนด Username MQTT
mqtt_password = "ajbear1969" # กำหนด Password MQTT
mqtt_publish_topic = "ajbear/bar" # กำหนด Plublish Topic ที่ต้องการส่งข้อมูล
mqtt_client_id = "beariot_smart_sensor"

# Beariot config
SITE_ID = "KMe45f01d94cbf"
DEVICE_ID = 3
CONNECTION = "MQTT"
LABEL = "temp"

# สร้าง Payload เตรียมส่งข้อมูล
def generate_payload(value):
    rtc = RTC()
    current_time = rtc.datetime()
    iso_format = '{}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:06d}+00:00'.format(
        current_time[0], current_time[1], current_time[2],
        current_time[4], current_time[5], current_time[6], current_time[7])
    print(iso_format)
    
    return {
        "siteID": SITE_ID,
        "deviceID": DEVICE_ID,
        "date": iso_format,
        "offset": -420, 
        "connection": CONNECTION,
        "tagObj": [{
            "status": True,
            "label": LABEL,
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
    wlan.connect(ssid, password)

    while not wlan.isconnected():
        time.sleep(1)
        print("Connecting to Wi-Fi...")
    print("Connected to Wi-Fi:", wlan.ifconfig())

# เชื่อมต่อ MQTT
def connect_mqtt():
    mqtt_client = MQTTClient(
        client_id=mqtt_client_id,
        server=mqtt_host,
        user=mqtt_username,
        password=mqtt_password
    )
    mqtt_client.connect()
    return mqtt_client

# ส่งข้อมูลไปยัง MQTT Broker
def publish_data(mqtt_client, topic, payload):
    payload_str = ujson.dumps(payload) 
    mqtt_client.publish(topic, payload_str.encode('utf-8'))
    print(f"Data sent successfully: {payload['tagObj'][0]['value']}")
    
    
#อ่านค่าอุณหภูมิ
def read_temperature():
    sensor = dht.DHT22(Pin(15))
    sensor.measure() 
    temp_value = sensor.temperature()
    return temp_value

# ฟังก์ชั่นหลัก
def main():
    print("Starting BeaRiOt MQTT Test")
    print(f"Sending data to: {mqtt_host}")
    
    connect_wifi(SSID, PASSWORD)
    mqtt_client = connect_mqtt()
    
    try:
        while True:
            temp_value = read_temperature()
            payload = generate_payload(temp_value)  
            publish_data(mqtt_client, mqtt_publish_topic, payload) 
            time.sleep(3)  
    except KeyboardInterrupt:
        print("Test stopped by user")
        
if __name__ == "__main__":
    main()
