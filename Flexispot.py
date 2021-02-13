import network
import json
import machine
import time
from machine import UART, Pin
from umqttsimple import MQTTClient

class ControlPanel:
    WIFI_SSID = "<YOUR SSID>"
    WIFI_PASS = "<YOUR PASS>"

    MQTT_CLIENT_ID = "flexispot"
    MQTT_SERVER = "<MQTT SERVER>"
    MQTT_TOPIC_DISCOVERY = "homeassistant/sensor/standingdesk/config"
    MQTT_TOPIC_STATE = "homeassistant/sensor/standingdesk/state"
    MQTT_TOPIC_CMD = "homeassistant/sensor/standingdesk/set"

    UART_ID = 2
    READ_PIN_ID = 18

    def __init__(self, publish_discovery = True, debug = False):
        self.debug = debug

        self.log("Init...")
        system_led = Pin(2, Pin.OUT)
        system_led.value(1)

        self.log("Connecting to WLAN")
        self.wlan = self.connect_to_wlan()
        self.log("waiting for wlan connection")
        while not self.wlan.isconnected():
            time.sleep(1)
        
        self.log("Connecting to MQTT")
        self.mqtt = self.connect_to_mqtt(publish_discovery)

        self.log("Setup UART")
        self.serial = UART(self.UART_ID, baudrate=9600, timeout=500)

        self.read_pin = Pin(self.READ_PIN_ID, Pin.OUT)
        self.read_pin.value(1)
    
    def connect_to_wlan(self):
        wlan = network.WLAN(network.STA_IF) 
        wlan.active(True)
        wlan.connect(self.WIFI_SSID, self.WIFI_PASS)
        return wlan
    
    def connect_to_mqtt(self, publish_discovery):
        client = MQTTClient(self.MQTT_CLIENT_ID, self.MQTT_SERVER)
        client.connect()

        client.set_callback(self.on_mqtt_msg)
        client.subscribe(self.MQTT_TOPIC_CMD)

        if publish_discovery:
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
        
        raise ValueError("unknown digit")
    
    def has_decimal_point(self, b):
        return (b & 0x80) == 0x80
    
    def query_height(self):        
        while(True):
            self.cmd_no_button()
            s = self.serial.read(1)
            if s != None:
                while s != None and s[0] != 0x9b:
                    s = self.serial.read(1)

                msg_len = int.from_bytes(self.serial.read(1), "little")

                msg = self.serial.read(msg_len)
                msg_id = msg[0]

                if msg_id == 0x12:
                    try:
                        height = self.decode_digit(msg[1]) * 100 + self.decode_digit(msg[2]) * 10 + self.decode_digit(msg[3])
                        if self.has_decimal_point(msg[2]):
                            height = height / 10.0
                        self.log("sending")
                        self.mqtt.publish(self.MQTT_TOPIC_STATE, str(height))
                        return height
                    except ValueError:
                        print("error")
                        print(msg)
                else:
                    self.log("not height response")
            else:
                self.log("didn't receive bytes")
    
    def listen_mqtt(self):
        self.log("Start listening to mqtt commands")
        while True:
            self.mqtt.wait_msg()

    def on_mqtt_msg(self, topic, msg):
        if topic == b''+self.MQTT_TOPIC_CMD:
            if msg == b'up':
                self.cmd_up()
            elif msg == b'down':
                self.cmd_down()
            elif msg == b'pos1':
                self.cmd_pos1()
            elif msg == b'pos2':
                self.cmd_pos2()
            elif msg == b'pos3':
                self.cmd_pos3()
            elif msg == b'm':
                self.cmd_m()
            else:
                self.log("unknown message")

        else:
            self.log("unknown topic")
            self.log(topic)
    
    def cmd_no_button(self):
        self.log("sending cmd no button pressed")
        cmd = bytearray(b'\x9b\x06\x02\x00\x00\x6c\xa1\x9d')
        self.serial.write(cmd)

    def cmd_up(self):
        self.log("sending cmd up button")
        cmd = bytearray(b'\x9b\x06\x02\x01\x00\xfc\xa0\x9d')
        self.serial.write(cmd)
    
    def cmd_down(self):
        self.log("sending cmd down button")
        cmd = bytearray(b'\x9b\x06\x02\x02\x00\x0c\xa0\x9d')
        self.serial.write(cmd)
    
    def cmd_pos1(self):
        self.log("sending cmd pos 1 button")
        cmd = bytearray(b'\x9b\x06\x02\x04\x00\xac\xa3\x9d')
        self.serial.write(cmd)
    
    def cmd_pos2(self):
        self.log("sending cmd pos 2 button")
        cmd = bytearray(b'\x9b\x06\x02\x08\x00\xac\xa6\x9d')
        self.serial.write(cmd)
    
    def cmd_pos3(self):
        self.log("sending cmd pos 3 button")
        cmd = bytearray(b'\x9b\x06\x02\x10\x00\xac\xac\x9d')
        self.serial.write(cmd)
    
    def cmd_m(self):
        self.log("sending cmd m button")
        cmd = bytearray(b'\x9b\x06\x02\x20\x00\xac\xb8\x9d')
        self.serial.write(cmd)
    
    def deepsleep(self, seconds):
        self.log("going to deep sleep")
        self.read_pin.value(0)
        machine.deepsleep(seconds)

    def log(self, msg):
        if self.debug:
            print(msg)
