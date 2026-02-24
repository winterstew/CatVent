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
import adafruit_vcnl4200
import adafruit_ds3502
import digitalio
import analogio
import neopixel

import adafruit_minimqtt.adafruit_minimqtt as MQTT
from adafruit_io.adafruit_io import IO_MQTT

debug = 0

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
# Initialize VCNL4200 and VCNL4020
prox = (adafruit_vcnl4200.Adafruit_VCNL4200(i2c),False,
        adafruit_vcnl4020.Adafruit_VCNL4020(i2c))
# Initialize SHT41
sht = (adafruit_sht4x.SHT4x(i2c),False)
print("Found SHT4x with serial number", hex(sht[0].serial_number))
sht[0].mode = adafruit_sht4x.Mode.NOHEAT_HIGHPRECISION
# Can also set the mode to enable heater
# shtone.mode = adafruit_sht4x.Mode.LOWHEAT_100MS
print(" Current mode is: ", adafruit_sht4x.Mode.string[sht[0].mode])
# Initialize Red Quad Alphanumeric PID:3130
display = adafruit_ht16k33.segments.Seg14x4(i2c)
display.brightness = 0.1
# Initialize SGP40 MOX gass sensor
sgp = (adafruit_sgp40.SGP40(i2c), False)
#print("Found SGP40 with serial number", hex(sgp.serial_number))

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
temperature_feed = ('cat-vent.temperature-1', 'cat-vent.temperature-2')
humidity_feed = ('cat-vent.humidity-1','cat-vent.humidity-2') 
vocindex_feed = ('cat-vent.vocindex-1', 'cat-vent.vocindex-2')
proximity_feed = ('cat-vent.proximity-1', 'cat-vent.proximity-2', 
                                          'cat-vent.proximity-3')
illuminance_feed = ('cat-vent.illuminance-1', 'cat-vent.illuminance-2', 
                                          'cat-vent.illuminance-3')

### Code ###

# Define callback functions which will be called when certain events happen.
# pylint: disable=unused-argument
def connected(client):
    # Connected function will be called when the client is connected to Adafruit IO.
    # This is a good place to subscribe to feed changes.  The client parameter
    # passed to this function is the Adafruit IO MQTT client so you can make
    # calls against it easily.
    if debug > 1: print("                           Listening for {onoff_feed} changes...")
    # Subscribe to changes on a feed named DemoFeed.
    client.subscribe(onoff_feed)

def subscribe(client, userdata, topic, granted_qos):
    # This method is called when the client subscribes to a new feed.
    if debug > 1: print("Subscribed to {0} with QOS level {1}".format(topic, granted_qos))

def unsubscribe(client, userdata, topic, pid):
    # This method is called when the client unsubscribes from a feed.
    if debug > 1: print("Unsubscribed from {0} with PID {1}".format(topic, pid))

# pylint: disable=unused-argument
def disconnected(client):
    # Disconnected function will be called when the client disconnects.
    if debug > 1: print("Disconnected from Adafruit IO!")

# pylint: disable=unused-argument
def publish(client, userdata, topic, pid):
    """This method is called when the client publishes data to a feed."""
    if debug > 1: 
        print(f"Published to {topic} with PID {pid}")
        if userdata is not None:
            print("Published User data: ", end="")
            print(userdata)

# pylint: disable=unused-argument
def message(client, feed_id, payload):
    # Message function will be called when a subscribed feed has a new value.
    # The feed_id parameter identifies the feed, and the payload parameter has
    # the new value.
    if debug > 0: print("Feed {0} received new value: {1}".format(feed_id, payload))
    if (feed_id == onoff_feed):
        if (payload == "On" or payload == "ON" or payload is True):
            close_relay(setpin, unsetpin)
        if (payload == "Off" or payload == "OFF" or payload is False):
            open_relay(setpin, unsetpin)


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

display_rate = 5.0
display_modes = 5
display_counter = 0
lastdisplay = 0
boxdisplay = 0
publish_rate = 20.0
measured_loop = 1
lastpublish = 0
vocindex_rate = 1.0
lastvocindex = 0
lastrelay_open = False
loop_rate = 0.0
temperature = [0, 0]
humidity = [0, 0]
voc_index = [50, 50]
proximity = [0, 0, 0]
illuminance = [0, 0, 0]
proximity_limit = 7
vocindex_hi = 150
vocindex_low = 100


open_relay(setpin, unsetpin)
io.publish(onoff_feed, "Off")

while True:
    # Poll the message queue
    io.loop(timeout=1)
    proximity[2] = prox[2].proximity
    illuminance[2] = prox[2].lux
    if debug > 2:
        print(f"Proximity 3 is: {proximity[2]}")
        print(f"Ambient Illuminance 3 is: {illuminance[2]}")
    for box in (0,1):
        if sht[box]:
            temperature[box], humidity[box] = sht[box].measurements
            if debug > 2:
                print("Temperature in %1d: %0.1f C" % (box+1,temperature[box]))
                print("Humidity in %1d: %0.1f%%" % (box+1,humidity[box]))
            if sgp[box]:
                if (time.monotonic() - lastvocindex) >= vocindex_rate:    
                    if debug > 2: print("Measurement in %1d: %d" % (box+1,sgp[box].raw))
                    voc_index[box] = sgp[box].measure_index(temperature=temperature[box],
                                                         relative_humidity=humidity[box])
                    if debug > 2: print("VOC Index in %1d: %d" % (box+1,voc_index[box]))
                if box == 0: lastvocindex = time.monotonic()
        if prox[box]:
            proximity[box] = prox[box].proximity
            illuminance[box] = prox[box].lux
            if debug > 2:
                print(f"Proximity {box+1} is: {proximity[box]}")
                print(f"Ambient Illuminance {box+1} is: {illuminance[box]}")
        if (voc_index[box] > vocindex_hi  and relay_open and 
            proximity[0] < proximity_limit and proximity[1] < proximity_limit):
            close_relay(setpin, unsetpin)
            io.publish(onoff_feed, "On")
        if (voc_index[0] < vocindex_low and voc_index[1] < vocindex_low and not relay_open):
            open_relay(setpin, unsetpin)
            io.publish(onoff_feed, "Off")
    if debug > 2:
        print(f"Relay Open: {relay_open}")
        print("")
    if (time.monotonic() - lastdisplay) >= display_rate:
        display_counter = (display_counter + 1) % display_modes
        display.fill(0)
        if (display_counter == 0):
            display.print("box%1d" % (boxdisplay+1))
        elif (display_counter == 1):
            display.print("%0.1fC" % temperature[boxdisplay])
        elif (display_counter == 2):
            display.print("%0.1f%%" % humidity[boxdisplay])
        elif (display_counter == 3):
            display.print("%04d" % voc_index[boxdisplay])
        elif (display_counter == 4):
            display.print("%0.1fHz" % loop_rate)
        display.show()
        lastdisplay = time.monotonic()
    if (time.monotonic() - lastpublish) >= publish_rate:
        io.publish(temperature_feed[boxdisplay], temperature[boxdisplay])
        io.publish(humidity_feed[boxdisplay], humidity[boxdisplay])
        io.publish(vocindex_feed[boxdisplay], voc_index[boxdisplay])
        io.publish(proximity_feed[boxdisplay], proximity[boxdisplay])
        io.publish(illuminance_feed[boxdisplay], illuminance[boxdisplay])
        io.publish(proximity_feed[2], proximity[2])
        io.publish(illuminance_feed[2], illuminance[2])
        if measured_loop > 0:
            loop_rate = measured_loop/(time.monotonic() - lastpublish)
        if debug > 0:
            print("loop rate %0.1fHz" % loop_rate)
        lastpublish = time.monotonic()
        measured_loop = 0
    measured_loop += 1
    # increment the boxdisplay number
    boxdisplay = (boxdisplay + 1) % 2
    time.sleep(0.01)