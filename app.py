from edgeiq import ObjectDetection, Engine, markup_image
from time import sleep
from Synth import Synth
import subprocess
import threading
import time
import random
from mqtt import Mqtt
from cv2 import VideoCapture

person_count = 0  # Initialize count outside the loop
prev_person_count = 0

obj_detect = ObjectDetection("alwaysai/mobilenet_ssd")
obj_detect.load(engine=Engine.DNN)

cap = VideoCapture('http://192.168.1.7:8080/video')
# cap = VideoCapture(0)
synth = Synth(cap)
mqtt = Mqtt()

mqtt.connect()

while not mqtt.isConnected:
    time.sleep(1)

while mqtt.isConnected:
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("frame read failed")
            break
        results = obj_detect.detect_objects(frame, confidence_level=.5)
        frame = markup_image(frame, results.predictions, colors=obj_detect.colors)

        for prediction in results.predictions:
            if prediction.label == 'person':
                person_count += 1  # Increment count if "person" detected

        # Publish data only if person_count changes
        if person_count != prev_person_count:
            try:
                mqtt.publish_data("occupants", {
                    "value": person_count
                }, 1)
            except Exception as e:
                print(f"Error in publishing : {e}")
            prev_person_count = person_count

        try:
            synth.publish_frame(frame)
        except Exception as e:
            print(f"Error in publishing : {e}")

        if not synth.is_connected():
            print("Connection to RTMP server lost. Reattempting connection...")
            try:
                sleep(10)
                synth.reconnect()
                print("Reconnection successful.")
            except Exception as e:
                print(f"Reconnection failed: {e}")

        person_count = 0  # Reset count after publishing

cap.release()
mqtt.disconnect()