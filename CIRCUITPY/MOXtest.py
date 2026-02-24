import time
import os
from random import randint
import board
import adafruit_sht4x
import adafruit_sgp40
import adafruit_ht16k33.segments
import board
from digitalio import DigitalInOut
import adafruit_connection_manager
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import neopixel
import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

i2c = board.I2C()   # uses board.SCL and board.SDA
spi = board.SPI()

sht = adafruit_sht4x.SHT4x(i2c)
display = adafruit_ht16k33.segments.Seg14x4(i2c)
sgp = adafruit_sgp40.SGP40(i2c)
print("Found SHT4x with serial number", hex(sht.serial_number))

sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
# Can also set the mode to enable heater
# sht.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
print("Current mode is: ", adafruit_sht4x.Mode.string[sht.mode])

while True:
    temperature, relative_humidity = sht.measurements
    print("Temperature: %0.1f C" % temperature)
    print("Humidity: %0.1f %%" % relative_humidity)
    print("Measurement: ", sgp.raw)
    voc_index = sgp.measure_index(temperature=temperature, relative_humidity=relative_humidity)
    print("VOC Index:", voc_index)
    print("")
    display.print("%0.1fC" % temperature)
    display.show()
    time.sleep(0.5)
    display.print("%0.1f%%" % relative_humidity)
    display.show()
    time.sleep(0.5)
