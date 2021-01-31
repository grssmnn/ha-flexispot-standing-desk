import network
import json
import machine
import time
from machine import UART, Pin
from umqttsimple import MQTTClient

class Flexispot:
    WIFI_SSID = "<YOUR SSID>"
    WIFI_PASS = "<YOUR PASS>"

    MQTT_CLIENT_ID = "flexispot"
    MQTT_SERVER = "<MQTT SERVER>"
    MQTT_TOPIC_DISCOVERY = "homeassistant/sensor/standingdesk/config"
    MQTT_TOPIC_STATE = "homeassistant/sensor/standingdesk/state"

    UART_ID = 2

    def __init__(self):
        print("Connecting to WLAN")
        self.wlan = self.connect_to_wlan()
        print("waiting for wlan connection")
        while not self.wlan.isconnected():
            time.sleep(1)
        
        print("Connecting to MQTT")
        self.client = self.connect_to_mqtt()

        print("Setup UART")
        self.serial = UART(self.UART_ID, baudrate=9600, timeout=500)
    
    def connect_to_wlan(self):
        wlan = network.WLAN(network.STA_IF) 
        wlan.active(True)
        wlan.connect(self.WIFI_SSID, self.WIFI_PASS)
        return wlan
    
    def connect_to_mqtt(self):
        client = MQTTClient(self.MQTT_CLIENT_ID, self.MQTT_SERVER)
        client.connect()
        discovery = {
            "name": "standingdesk",
            "state_topic": self.MQTT_TOPIC_STATE,
            "unit_of_measurement": "cm"
        }
        client.publish(self.MQTT_TOPIC_DISCOVERY, json.dumps(discovery))
        return client
    
    def decode_digit(self, b):
        s = bytearray(8)
        for i in range(8):
            h = 0x01 << i
            s[i] = (b & h) == h
                
        if s[0] and s[1] and s[2] and s[3] and s[4] and s[5] and not s[6]:
            return 0
        elif not s[0] and s[1] and s[2] and not s[3] and not s[4] and not s[5] and not s[6]:
            return 1
        elif s[0] and s[1] and not s[2] and s[3] and s[4] and not s[5] and s[6]:
            return 2
        elif s[0] and s[1] and s[2] and s[3] and not s[4] and not s[5] and s[6]:
            return 3
        elif not s[0] and s[1] and s[2] and not s[3] and not s[4] and s[5] and s[6]:
            return 4
        elif s[0] and not s[1] and s[2] and s[3] and not s[4] and s[5] and s[6]:
            return 5
        elif s[0] and not s[1] and s[2] and s[3] and s[4] and s[5] and s[6]:
            return 6
        elif s[0] and s[1] and s[2] and not s[3] and not s[4] and not s[5] and not s[6]:
            return 7
        elif s[0] and s[1] and s[2] and s[3] and s[4] and s[5] and s[6]:
            return 8
        elif s[0] and s[1] and s[2] and s[3] and not s[4] and s[5] and s[6]:
            return 9
    
    def has_decimal_point(self, b):
        return (b & 0x80) == 0x80

    def read_height(self):
        print("Waiting for display")
        
        while(True):
            s = self.serial.read(1)
            if s != None:
                try:
                    while s != None and s[0] != 0x9b:
                        s = self.serial.read(1)
                    
                    msg_len = int.from_bytes(self.serial.read(1), "little")
                    msg = self.serial.read(msg_len)
                    
                    if msg[0] == 0x12:
                        height = self.decode_digit(msg[1]) * 100 + self.decode_digit(msg[2]) * 10 + self.decode_digit(msg[3])
                        if self.has_decimal_point(msg[2]):
                            height = height / 10.0
                        print(height)
                        self.publish_height(height)
                except TypeError:
                    print("Display went off")
    
    # State won't be published more than once per second
    def publish_height(self, height):
        if not hasattr(self, "last_ticks"):
            self.last_ticks = 0

        current_ticks = time.ticks_ms()
        if current_ticks - self.last_ticks > 1000:
            self.client.publish(self.MQTT_TOPIC_STATE, str(height))
            self.last_ticks = time.ticks_ms()