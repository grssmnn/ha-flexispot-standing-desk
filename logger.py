# I used this logger for debugging the communication.
# You don't need to put this file on you ESP32 unless
# you also want to debug.

import network
import json
import machine
import time
from machine import UART, Pin
import ubinascii

class Logger:
    UART_ID = 2

    def __init__(self):
        print("Setup UART")
        self.serial = UART(self.UART_ID, baudrate=9600, timeout=500)

    def read(self):
        print("Waiting for display")
        p18 = Pin(18, Pin.OUT)
        p18.value(1)
        time.sleep(1)
        p18.value(0)

        
        while(True):
            s = self.serial.read(1)
            if s != None:
                try:
                    # Wait for next message start
                    while s != None and s[0] != 0x9b:
                        s = self.serial.read(1)
                        print("skip")
                    
                    msg = ubinascii.hexlify(s)

                    msg_len_raw = self.serial.read(1)
                    msg_len = int.from_bytes(msg_len_raw, "little")
                    msg += ubinascii.hexlify(msg_len_raw)

                    payload = self.serial.read(msg_len)
                    msg += ubinascii.hexlify(payload)

                    print(msg)

                except TypeError as err:
                    print(err)