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
def connect_wifi(ssid, password, max_retries=10):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    # พยายามเชื่อมต่อ Wi-Fi
    retry_count = 0
    if not wlan.isconnected():
        print("Connecting to Wi-Fi...")
        wlan.connect(ssid, password)

    # ลองเชื่อมต่อหลายครั้งจนสำเร็จหรือเกินจำนวนครั้งที่กำหนด
    while not wlan.isconnected() and retry_count < max_retries:
        time.sleep(2)
        retry_count += 1
        print(f"Waiting for connection... ({retry_count}/{max_retries})")
    
    if wlan.isconnected():
        print("Connected to Wi-Fi:", wlan.ifconfig())
        return True
    else:
        print("Failed to connect to Wi-Fi.")
        return False

# ตรวจสอบการเชื่อมต่อ WIFI และเชื่อมต่อใหม่ถ้าหลุด
def ensure_wifi_connected(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    
    if not wlan.isconnected():
        print("Wi-Fi disconnected, reconnecting...")
        wlan.active(False)
        time.sleep(2)
        wlan.active(True)
        
        # ลองเชื่อมต่อใหม่
        success = connect_wifi(ssid, password)
        
        if not success:
            print("Wi-Fi reconnect failed. Retrying after delay...")
            time.sleep(5)  # รอซักครู่ก่อนลองอีกครั้ง
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
    except OSError:
        print("MQTT disconnected, reconnecting...")
        connect_mqtt()

# ส่งข้อมูลไปยัง MQTT Broker
def publish_data(mqtt_client, topic, payload):
    payload_str = ujson.dumps(payload)  # Convert the payload to JSON string
    print(payload_str)
    mqtt_client.publish(topic, payload_str.encode('utf-8'))  # Send as bytes

# Main execution
def main():
    print("Starting BeaRiOt Smart Sensor MQTT")
    print(f"Sending data to: {mqtt_host}")
    
    if not connect_wifi(SSID, PASSWORD):
        print("Initial Wi-Fi connection failed. Exiting...")
        return
    
    connect_mqtt()  # Ensure MQTT is connected initially
    
    sensor = dht.DHT22(Pin(15))  # Initialize the sensor
    
    try:
        while True:
            ensure_wifi_connected(SSID, PASSWORD)  # ตรวจสอบ Wi-Fi ทุกลูป
            ensure_mqtt_connected()  # ตรวจสอบ MQTT ทุกลูป

            sensor.measure()
            temp_value = sensor.temperature()  # Read temperature
            payload = generate_payload(temp_value)  # Generate new payload
            publish_data(mqtt_client, mqtt_publish_topic, payload)  # Publish the data
            
            time.sleep(3)  # Wait for 3 seconds before the next iteration
            
    except OSError as e:
        print("Error reading sensor:", e)

if __name__ == "__main__":
    main()