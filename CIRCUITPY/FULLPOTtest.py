# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import os
import ssl
import time

import socketpool
import wifi

from random import randint
import board
import adafruit_sht4x
import adafruit_sgp40
import adafruit_ht16k33.segments
import adafruit_vcnl4020
import adafruit_ds3502
import digitalio
import analogio
import neopixel

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

# Add settings.toml to your filesystem CIRCUITPY_WIFI_SSID and CIRCUITPY_WIFI_PASSWORD keys
# with your WiFi credentials. DO NOT share that file or commit it into Git or other
# source control.

# Set your Adafruit IO Username, Key and Port in settings.toml
# (visit io.adafruit.com if you need to create an account,
# or if you need your Adafruit IO key.)
aio_username = os.getenv("ADAFRUIT_AIO_USERNAME")
aio_key = os.getenv("ADAFRUIT_AIO_KEY")

while (not wifi.radio.connected):
    print(f"Connecting to {os.getenv('CIRCUITPY_WIFI_SSID')}")
    wifi.radio.connect(os.getenv("CIRCUITPY_WIFI_SSID"),
                   os.getenv("CIRCUITPY_WIFI_PASSWORD"))

print(f"Connected as {wifi.radio.addresses[0]}")

### Hardware ###

i2c = board.I2C()
spi = board.SPI()
# Initialize VCNL4020
prox = adafruit_vcnl4020.Adafruit_VCNL4020(i2c)
#print("Found VCNL4024 with serial number", hex(prox.serial_number))
# Initialize SHT41
sht = adafruit_sht4x.SHT4x(i2c)
print("Found SHT4x with serial number", hex(sht.serial_number))
sht.mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
# Can also set the mode to enable heater
# sht.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
print(" Current mode is: ", adafruit_sht4x.Mode.string[sht.mode])
# Initialize Red Quad Alphanumeric PID:3130
display = adafruit_ht16k33.segments.Seg14x4(i2c)
#print("Found HT16K33 with serial number", hex(display.serial_number))
# Initialize SGP40 MOX gass sensor
sgp = adafruit_sgp40.SGP40(i2c)
#print("Found SGP40 with serial number", hex(sgp.serial_number))
# Initialize DS3502 potentiometer
pot = adafruit_ds3502.DS3502(i2c)
#print("Found DS3502 with serial number", hex(pot.serial_number))
wiper_output = analogio.AnalogIn(board.A2)

# Latching Mini Relay FeatherWing PID:2923
setpin = digitalio.DigitalInOut(board.D26)
setpin.direction = digitalio.Direction.OUTPUT
setpin.value = False
unsetpin = digitalio.DigitalInOut(board.D25)
unsetpin.direction = digitalio.Direction.OUTPUT
unsetpin.value = False
relay_open = True

def open_relay(setpin, unsetpin):
    global relay_open
    setpin.value = False
    unsetpin.value = True
    time.sleep(0.1)
    unsetpin.value = False
    relay_open = True

def close_relay(setpin, unsetpin):
    global relay_open
    unsetpin.value = False
    setpin.value = True
    time.sleep(0.1)
    setpin.value = False
    relay_open = False

### Feeds ###

onoff_feed = 'cat-vent.onoff'
speed_feed = 'cat-vent.speed'
temp_feed = 'cat-vent.temperature'
humidity_feed = 'cat-vent.humidity'
vocindex_feed = 'cat-vent.vocindex'
proximity_feed = 'cat-vent.proximity'
illuminance_feed = 'cat-vent.illuminance'

### Code ###

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    print("Connected to Adafruit IO!  Listening for {speed_feed} changes...")
    # Subscribe to changes on a feed named DemoFeed.
    client.subscribe(speed_feed)
    print("                           Listening for {onoff_feed} changes...")
    # Subscribe to changes on a feed named DemoFeed.
    client.subscribe(onoff_feed)

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    print("Unsubscribed from {0} with PID {1}".format(topic, pid))

# pylint: disable=unused-argument
def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    print("Disconnected from Adafruit IO!")

# pylint: disable=unused-argument
def publish(client, userdata, topic, pid):
    """This method is called when the client publishes data to a feed."""
    print(f"Published to {topic} with PID {pid}")
    if userdata is not None:
        print("Published User data: ", end="")
        print(userdata)

# pylint: disable=unused-argument
def message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    print("Feed {0} received new value: {1}".format(feed_id, payload))
    if (feed_id == onoff_feed):
        if (payload == "On" or payload == "ON" or payload is True):
            close_relay(setpin, unsetpin)
        if (payload == "Off" or payload == "OFF" or payload is False):
            open_relay(setpin, unsetpin)
    if (feed_id == speed_feed):
        pot.wiper = int(payload)


# Create a socket pool
pool = socketpool.SocketPool(wifi.radio)
ssl_context = ssl.create_default_context()

# If you need to use certificate/key pair authentication (e.g. X.509), you can load them in the
# ssl context by uncommenting the lines below and adding the following keys to your settings.toml:
# "device_cert_path" - Path to the Device Certificate
# "device_key_path" - Path to the RSA Private Key
# ssl_context.load_cert_chain(
#     certfile=os.getenv("device_cert_path"), keyfile=os.getenv("device_key_path")
# )

# Set up a MiniMQTT Client
mqtt_client = MQTT.MQTT(
    broker="io.adafruit.com",
    port=1883,
    username=aio_username,
    password=aio_key,
    socket_pool=pool,
    ssl_context=ssl_context,
)

# Initialize an Adafruit IO MQTT Client
io = IO_MQTT(mqtt_client)

# Setup the callback methods above
io.on_connect = connected
io.on_disconnect = disconnected
io.on_subscribe = subscribe
io.on_unsubscribe = unsubscribe
io.on_message = message
io.on_publish = publish

# Connect the client to the MQTT broker.
print("Connecting to Adafruit IO...")
io.connect()

display_counter = 0

while True:
    # Poll the message queue
    io.loop(timeout=1)

    temperature, relative_humidity = sht.measurements
    print("Temperature: %0.1f C" % temperature)
    io.publish(temp_feed, temperature)
    print("Humidity: %0.1f %%" % relative_humidity)
    io.publish(humidity_feed, relative_humidity)
    print("Measurement: ", sgp.raw)
    voc_index = sgp.measure_index(temperature=temperature,
                    relative_humidity=relative_humidity)
    print("VOC Index:", voc_index)
    io.publish(vocindex_feed, voc_index)
    print(f"Proximity is: {prox.proximity}")
    io.publish(proximity_feed, prox.proximity)
    print(f"Ambient is: {prox.lux}")
    io.publish(illuminance_feed, prox.lux)
    print("Wiper set: %d" % pot.wiper)
    print(f"Relay Open: {relay_open}")
    print("")
    display_counter = (display_counter + 1) % 3
    if (display_counter == 0):
        display.print("%0.1fC" % temperature)
    elif (display_counter == 1):
        display.print("%0.1f%%" % relative_humidity)
    elif (display_counter == 2):
        display.print("%04d" % voc_index)
    display.show()
    time.sleep(5)