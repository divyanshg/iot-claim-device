import subprocess
from mqtt import Mqtt
import time

mqtt = Mqtt()
mqtt.connect()

# Flag to keep track of whether the command has been executed
command_executed = False

while not mqtt.isConnected:
    time.sleep(1)

if not command_executed:  # Check if the command has not been executed yet
    print("Starting Detection service")
    mqtt.disconnect()
    
    subprocess.call(["aai", "app", "start"])
    command_executed = True  # Set the flag to True after executing the command

print("Exiting script")