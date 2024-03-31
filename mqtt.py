import time
import paho.mqtt.client as pmqtt
import ssl
import json
import os
import shutil
import subprocess

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

mqtt_host = "192.168.1.4"

CA_CERT=client_config["ca"]
CERT_FILE=client_config["cert"]
KEY_FILE=client_config["key"]

certFile = "./claim-new-cert.crt"
keyFile = "./claim-new-key.pem"

FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60

def del_claim_certs():
    try:
        shutil.rmtree("./certs")
        print(f"Directory 'certs' and its contents have been successfully deleted.")
    except Exception as e:
        print(f"Error occurred while deleting directory 'certs': {e}")


def on_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode('utf-8')

    if topic == "$CLAIM_PROVISION/" + client_config["clientId"]:
        provisionDetails = json.loads(payload)
        if provisionDetails["status"] == "provisioned":
            # Save received certificate and key to files
            write_data_to_file(certFile, provisionDetails["certs"]["certificate"])
            write_data_to_file(keyFile, provisionDetails["certs"]["private_key"])
            
            # Update clientId in ids.json
            update_client_id_in_ids_json(provisionDetails["clientId"])
            #delete the claim certificates
            del_claim_certs()
            
            print("Provisioned successfully")
            print("clientId:", provisionDetails["clientId"])
            print("RESTARTING THE DEVICE")
            # Restart the device
            subprocess.call(["sudo", "reboot", "-h", "now"])
            

def write_data_to_file(filename, data):
    with open(filename, "w") as file:
        file.write(data)

def update_client_id_in_ids_json(clientId):
    data = {"claimCertId": "", "clientId": clientId, "key": keyFile, "cert": certFile, "ca": "./root-ca.crt"}
    with open('./config.json', 'w') as json_file:
        json.dump(data, json_file)


class Mqtt:
    def __init__(self):
        self.clientId = client_config["clientId"]
        self.isConnected = False
        self.client = pmqtt.Client(client_id=self.clientId, clean_session=True, transport="tcp", callback_api_version=pmqtt.CallbackAPIVersion.VERSION2) 
        
        self.setupTLS()

    def setupTLS(self):
        self.client.tls_set(ca_certs=CA_CERT, certfile=CERT_FILE, keyfile=KEY_FILE, tls_version=ssl.PROTOCOL_SSLv23)
        self.client.tls_insecure_set(True)

    def connect(self):
        print("Connecting...")
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = on_message
        self.client.on_publish = self.on_publish
        self.client.connect(mqtt_host, 8883, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc, properties):
        if rc == 0:
            print("Connected to MQTT Broker!")
            if len(client_config["claimCertId"]) > 0 or self.clientId.split("_")[0] == "claim":
                self.init_claim_sequence()
            else:
                self.isConnected = True

        else:
            print("Failed to connect, return code", rc)
    
    def on_publish(self, *args):
        print("Data published")

    def publish_data(self, topic, data, qos=0, retain=False):
        self.client.publish(client_config["clientId"]+"/"+topic, json.dumps(data), qos, retain)
    
    def init_claim_sequence(self):
        print("Initializing claim sequence")
        self.client.subscribe("$CLAIM_PROVISION/" + client_config["clientId"], qos=1)
        self.client.publish("$CLAIM/" + client_config["clientId"], self.clientId, 1, False)
    
    def on_disconnect(self, *args):
        if self.isConnected == True:
            print("Disconnected")
            self.reconnect()
    def disconnect(self):
        print("Disconnecting...")
        self.isConnected = False
        self.client.loop_stop()
        self.client.disconnect()

    def reconnect(self):
        reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            print("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                self.client.reconnect()
                print("Reconnected successfully!")
                return
            except Exception as err:
                print("%s. Reconnect failed. Retrying...", err)

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1
