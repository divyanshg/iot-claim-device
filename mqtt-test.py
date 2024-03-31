from mqtt import Mqtt
import random
import time

mqtt = Mqtt()
mqtt.connect()

while not mqtt.isConnected:
    time.sleep(1)

while mqtt.isConnected:
    mqtt.publish_data("af14/temperature", {
        "value": random.randrange(20, 50, 3)
    }, 1)
    time.sleep(2)