import cv2
import subprocess
# import requests
import time
import json
import os

BASE_URL = "192.168.1.4"

CONFIG_FILE='config.json'
client_config = None

# Check if the file exists
if os.path.exists(CONFIG_FILE):
    # Open the JSON file
    with open(CONFIG_FILE, "r") as json_file:
        # Read the content of the file
        json_content = json_file.read()

        # Check if the file is not empty and is valid JSON
        if json_content:
            try:
                # Parse the JSON data
                client_config = json.loads(json_content)
            except json.JSONDecodeError:
                print("Error: CONFIG JSON file is not valid JSON.")
        else:
            print("Error: CONFIG JSON file is empty.")
else:
    print("Error: CONFIG JSON file does not exist.")

# Access the client_config outside of the conditions
if client_config is None:
    print("No CONFIG data available.")

class Synth:
    def __init__(self, cameraFeed):
        self.cameraFeed = cameraFeed
        self.roomId = client_config["clientId"]
        
        self.rtmp_url = f"rtmp://{BASE_URL}:1935/live/{self.roomId}"
        # self.api_url = f"http://{BASE_URL}:3000/rooms/{roomId}/property/update?key={apiKey}"

        fps = int(self.cameraFeed.get(cv2.CAP_PROP_FPS))
        width = int(self.cameraFeed.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(self.cameraFeed.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.command =  ['ffmpeg',
           '-y',
           '-f', 'rawvideo',
           '-vcodec', 'rawvideo',
           '-pix_fmt', 'bgr24',
           '-s', "{}x{}".format(640, 360),
           '-r', str(30),
           '-i', '-',
           '-c:v', 'libx264',
           '-pix_fmt', 'yuv420p',
           '-preset', 'ultrafast',
           '-tune', 'zerolatency',  # Zero latency encoding
           '-f', 'flv',
           self.rtmp_url]
        
        self.stream_pipe = subprocess.Popen(self.command, stdin=subprocess.PIPE)
    
    def publish_frame(self, frame):
        if self.stream_pipe:
            self.stream_pipe.stdin.write(frame.tobytes())

    def close(self):
        if self.stream_pipe:
            self.stream_pipe.stdin.close()
    
    def is_connected(self):
        return self.stream_pipe.poll() is None if self.stream_pipe else False

    def reconnect(self):
        self.close()
        self.init_stream()

    def wait_until_connected(self, timeout=30):
        start_time = time.time()
        while not self.is_connected():
            if time.time() - start_time > timeout:
                raise TimeoutError("Connection timeout reached")
            time.sleep(1)

    # def publish_data(self, property, value):
    #     try:
    #         response = requests.get(f"{self.api_url}&name={property}&value={value}")
    #         print(response.json()["message"])
    #     except Exception as e:
    #         print(f"Error publishing data to server: {e}")
