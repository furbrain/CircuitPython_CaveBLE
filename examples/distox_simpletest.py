# SPDX-FileCopyrightText: 2022 Phil Underwood
#
# SPDX-License-Identifier: Unlicense
"""
example that reads from the cdc data serial port in groups of four and prints
to the console. The USB CDC data serial port will need enabling. This can be done
by copying examples/usb_cdc_boot.py to boot.py in the CIRCUITPY directory

Meanwhile a simple counter counts up every second and also prints
to the console.
"""
import time

import board
import keypad
from adafruit_ble import BLERadio
from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
import distox
ble = BLERadio()
ble.name = "DistoX"
print(ble.name)
disto = distox.DistoXService()
advertisement = ProvideServicesAdvertisement(disto)
ble.start_advertising(advertisement)



KEY_PINS = (board.D5, board.D9)
keys = keypad.Keys(KEY_PINS, value_when_pressed=False, pull=True)

compass = 0
clino = 0
distance = 5
while True:
    event = keys.events.get()
    if event:
        key_number = event.key_number
        if event.pressed:
            if key_number == 0:
                # change the values to send
                compass = (compass + 10.5) % 360
                clino += 5.5
                if clino > 90:
                    clino -= 180
                distance = (distance + 3.4) % 10000
                print(compass, clino, distance)
            if key_number == 1:
                disto.send_data(compass, clino, distance)
                print("Data sent")
    message = disto.poll()
    if message:
        print(f"Message received: {message}")
    time.sleep(0.03)


