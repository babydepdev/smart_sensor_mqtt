import network
import time
from umqtt.simple import MQTTClient
from machine import RTC, Pin
import ujson  
import dht

# Wifi Config
SSID = 'babydev'  
PASSWORD = 'weangkom'  

# MQTT config
MQTT_HOST = "172.20.10.2"
MQTT_PORT = 1883
MQTT_USERNAME = "orangepi"
MQTT_PASSWORD = "orangepi"
MQTT_PUBLISH_TOPIC = "beariot/temp"
MQTT_CLIENT_ID = "beariot_smart_sensor"

# Beariot config
SITE_ID = "KMac23a1e6aa8b"
DEVICE_ID = 3
CONNECTION = "MQTT"
LABEL_TEMP = "temperature_mqtt"
LABEL_HUMID = "humidity_mqtt"
MAX_WIFI_RETRIES = 10

# Function to create the payload for MQTT
def generate_payload(value_temp, value_humid):
    rtc = RTC()
    current_time = rtc.datetime()
    iso_format = '{}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:06d}+00:00'.format(
        current_time[0], current_time[1], current_time[2],
        current_time[4], current_time[5], current_time[6], current_time[7]
    )
    
    return {
        "siteID": SITE_ID,
        "deviceID": DEVICE_ID,
        "date": iso_format,
        "offset": -420, 
        "connection": CONNECTION,
        "tagObj": [
            {"status": True, "label": LABEL_TEMP, "value": value_temp},
            {"status": True, "label": LABEL_HUMID, "value": value_humid}
        ]
    }

# Connect to Wi-Fi with exponential backoff
def connect_wifi(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    retry_count = 0
    wait_time = 1  # Start with 1 second
    while retry_count < MAX_WIFI_RETRIES:
        if not wlan.isconnected():
            print(f"Connecting to Wi-Fi... (Retry {retry_count + 1})")
            wlan.connect(ssid, password)
            
            for _ in range(10):
                if wlan.isconnected():
                    print("Connected to Wi-Fi:", wlan.ifconfig())
                    return True
                time.sleep(1)
            retry_count += 1
            time.sleep(wait_time)
            wait_time *= 2  # Exponential backoff
        else:
            print("Already connected to Wi-Fi:", wlan.ifconfig())
            return True

    print("Failed to connect to Wi-Fi after retries.")
    return False

# Connect to MQTT broker and return the client
def connect_mqtt():
    mqtt_client = MQTTClient(
        client_id=MQTT_CLIENT_ID,
        server=MQTT_HOST,
        port=MQTT_PORT,  
        user=MQTT_USERNAME,
        password=MQTT_PASSWORD)
    mqtt_client.connect()
    print("Connected to MQTT Broker")
    return mqtt_client

# Publish data to MQTT broker
def publish_data(mqtt_client, topic, payload):
    payload_str = ujson.dumps(payload)
    print(payload_str)
    mqtt_client.publish(topic, payload_str.encode('utf-8'))
    print(f"Data sent successfully: Temp: {payload['tagObj'][0]['value']} Humid: {payload['tagObj'][1]['value']}")

# Read DHT22 sensor data
def read_dht22():
    sensor = dht.DHT22(Pin(15))
    sensor.measure() 
    value_temp = sensor.temperature()
    value_humid = sensor.humidity()
    return {"value_temp": value_temp, "value_humid": value_humid}

# Main function
def main():
    print("Starting BeaRiOt MQTT Test")
    
    # Connect to Wi-Fi
    if not connect_wifi(SSID, PASSWORD):
        print("Wi-Fi connection failed. Exiting...")
        return
    
    # Connect to MQTT broker
    mqtt_client = connect_mqtt()
    
    # Send data every 1 second
    wlan = network.WLAN(network.STA_IF)
    while True:
        # Check Wi-Fi connection
        if not wlan.isconnected():
            print("Wi-Fi disconnected! Reconnecting...")
            if not connect_wifi(SSID, PASSWORD):
                print("Failed to reconnect Wi-Fi. Retrying...")
                time.sleep(5)
                continue
        
        try:
            # Read sensor data
            dht22 = read_dht22()
            
            # Generate payload
            payload = generate_payload(dht22["value_temp"], dht22["value_humid"])
            
            # Publish data
            publish_data(mqtt_client, MQTT_PUBLISH_TOPIC, payload)
        except Exception as e:
            print(f"Error occurred: {e}")
        
        # Wait for 1 second before sending the next data
        time.sleep(2)

# Run the main function
main()

