import board
import busio as io
i2c = io.I2C(board.SCL, board.SDA)
import adafruit_ht16k33.segments
display = adafruit_ht16k33.segments.Seg14x4(i2c)
display.auto_write=False
display.fill(0)
display.show()
display[0]='T'
display.print('Test')
display.brightness=0.1
display.blink_rate=3
display.show()