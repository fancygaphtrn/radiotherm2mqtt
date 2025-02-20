import requests
from datetime import datetime
from time import sleep
import paho.mqtt.client as mqtt
import logging
import signal
import sys
import json
from configparser import ConfigParser
import argparse

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

logging.info("Starting ...")

ERROR_DELAY=5
TIMEOUT=3
MAX_RETRIES=5

DEVICE_NAME = ""
TSTAT_IP = ""
ID = ""
MQTT_ID = ""
BROKER = ""
PORT = ""
USERNAME = ""
PASSWORD = ""

parser = argparse.ArgumentParser(description='Example script using configparser')
parser.add_argument('-c', '--config', required=True, type=str, help='Path to configuration file')
parser.add_argument('-d', '--device', required=True, type=str, help='Device section in configuration file')
args = parser.parse_args()

logging.info(f"Loading configuration file: {args.config}")
logging.info(f"Device: {args.device}")

config = ConfigParser()
config.read(args.config)

DEVICE_NAME = config.get(args.device, 'DEVICE_NAME')
TSTAT_IP = config.get(args.device, 'TSTAT_IP')
ID = config.get(args.device, 'ID')
MQTT_ID = config.get(args.device, 'MQTT_ID')
BROKER = config.get(args.device, 'BROKER')
PORT = config.get(args.device, 'PORT')
USERNAME = config.get(args.device, 'USERNAME')
PASSWORD = config.get(args.device, 'PASSWORD')

logging.info(f"DEVICE_NAME: {DEVICE_NAME}")
logging.info(f"TSTAT_IP:    {TSTAT_IP}")
logging.info(f"ID:          {ID}")
logging.info(f"MQTT_ID:     {MQTT_ID}")
logging.info(f"BROKER:      {BROKER}")
logging.info(f"PORT:        {PORT}")
logging.info(f"USERNAME:    {USERNAME}")
logging.info(f"PASSWORD:    {PASSWORD}")

STATUS_TOPIC       = f"climate/stat/{DEVICE_NAME}/status"
HVAC_ACTION_TOPIC  = f"climate/stat/{DEVICE_NAME}/hvac_action"
CURRENT_TEMP_TOPIC = f"climate/stat/{DEVICE_NAME}/current_temperature"
TARGET_TEMP_TOPIC  = f"climate/stat/{DEVICE_NAME}/target_temperature"
FAN_TOPIC          = f"climate/stat/{DEVICE_NAME}/fan"
FAN_MODE_TOPIC     = f"climate/stat/{DEVICE_NAME}/fan_mode"
MODE_TOPIC         = f"climate/stat/{DEVICE_NAME}/mode"
HOLD_TOPIC         = f"climate/stat/{DEVICE_NAME}/hold"
SET_TEMP           = f"climate/cmnd/{DEVICE_NAME}/settemp"
SET_MODE           = f"climate/cmnd/{DEVICE_NAME}/setmode"
SET_FAN            = f"climate/cmnd/{DEVICE_NAME}/setfan"
SET_HOLD           = f"climate/cmnd/{DEVICE_NAME}/sethold"
AVAILABLE_TOPIC    = f"climate/tele/{DEVICE_NAME}/available"


class CT50:

    CODE_TO_TEMP_MODE = {
        0: "off",
        1: "heat",
        2: "cool",
        3: "auto",
    }

    TEMP_MODE_TO_CODE = {v: k for k, v in CODE_TO_TEMP_MODE.items()}

    CODE_TO_FAN_MODE = {
        0: "auto",
        1: "circulate",
        2: "on"
    }
    FAN_MODE_TO_CODE = {v: k for k, v in CODE_TO_FAN_MODE.items()}

    CODE_TO_TEMP_STATE = {0: "off", 1: "heat", 2: "cool"}
    CODE_TO_FAN_STATE = {0: "off", 1: "on"}

    CODE_TO_HOLD_MODE = {0: "program", 1: "hold"}
    HOLD_MODE_TO_CODE = {v: k for k, v in CODE_TO_HOLD_MODE.items()}

    def __init__(self, therm_address, error_delay=ERROR_DELAY, max_retries=MAX_RETRIES, timeout=TIMEOUT):
        self.address = therm_address
        self.base_url = f"http://{therm_address}/"
        self.error_delay = error_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self.set_clock()
        self.update_status()

    def api_get(self, cmd):
        retries = 0
        while retries < self.max_retries:
            try:
                r = requests.get(self.base_url + cmd, timeout=self.timeout)
                if r.status_code == 200:
                    return r
                else:
                    logging.info(f"Thermostat get {cmd} responded with error {r.status_code} {r.text} Retrying...")
            except Exception as ex:
                logging.info(f"Exception with API get call: {cmd} {retries}")
                logging.info(f"{repr(ex)}")
                retries += 1
                sleep(self.error_delay)
        
        logging.info(F"API get call {cmd} max retries exceeded. Failed to make the request.")
        return None

    def api_post(self, cmd, json):
        retries = 0
        while retries < self.max_retries:
            try:
                r = requests.post(self.base_url + cmd, json=json, timeout=self.timeout)
                if r.status_code == 200:
                    return r
                else:
                    logging.info(f"Thermostat post {cmd} responded with error {r.status_code} {r.text} Retrying...")
            except Exception as ex:
                logging.info(f"Exception with API post call: {cmd} {retries}")
                logging.info(f"{repr(ex)}")
                retries += 1
                sleep(self.error_delay)
        
        logging.info(F"API post call {cmd} max retries exceeded. Failed to make the request.")
        return None

    def update_status(self):
        r = self.api_get("tstat")
        if r: 
            stat = r.json()

            try:
                stat["mode"] = self.CODE_TO_TEMP_MODE[stat["tmode"]]
                stat["hvac_status"] = self.CODE_TO_TEMP_STATE[stat["tstate"]]
                stat["fan_mode"] = self.CODE_TO_FAN_MODE[stat["fmode"]]
                stat["fan_state"] = self.CODE_TO_FAN_STATE[stat["fstate"]]
                stat["hold_mode"] = self.CODE_TO_HOLD_MODE[stat["hold"]]
    
                if stat["mode"] == "off":
                    stat["target_temp"] = ''
                elif stat["mode"] == "heat":
                    stat["target_temp"] = stat["t_heat"]
                    del stat["t_heat"]
                elif stat["mode"] == "cool":
                    stat["target_temp"] = stat["t_cool"]
                    del stat["t_cool"]
                
                if stat["hvac_status"] == "cool":
                    stat["hvac_action"] = "cooling"
                elif stat["hvac_status"] == "heat":
                    stat["hvac_action"] = "heating"
                elif stat["hvac_status"] == "off" and stat["fan_state"] == "off":
                    stat["hvac_action"] = "idle"
                elif stat["hvac_status"] == "off" and stat["fan_state"] == "on":
                    stat["hvac_action"] = "idle"
    
                del stat["tmode"]
                del stat["tstate"]
                del stat["fmode"]
                del stat["fstate"]
                del stat["hold"]
                del stat["t_type_post"]
    
                self.current_stat = stat
                return stat
            except Exception as ex:
                logging.info("Error updating status, retry...",)
                logging.info(f"{repr(ex)}")
                return None
        else:
            return None

    def set_temp(self, new_temp):
        temp = float(new_temp)
        logging.info(f"Setting target temp to {temp}")
        if self.current_stat["mode"] == "heat":
            r = self.api_post("tstat", json={"t_heat": temp})
        elif self.current_stat["mode"] == "cool":
            r = self.api_post("tstat", json={"t_cool": temp})
        else:
            r == None
        if r == None:
           logging.info(f"Thermostat set temp failed")

    def set_mode(self, new_mode):
        logging.info(f"Setting HVAC mode to {new_mode}")
        new_code = self.TEMP_MODE_TO_CODE[new_mode]
        r = self.api_post("tstat", json={"tmode": new_code})
        if r == None:
           logging.info(f"Thermostat set mode failed")

    def set_fan(self, new_fan_mode):
        logging.info(f"Setting fan to {new_fan_mode}")
        new_code = self.FAN_MODE_TO_CODE[new_fan_mode]
        r = self.api_post("tstat", json={"fmode": new_code})
        if r == None:
           logging.info(f"Thermostat set fan failed")

    def set_hold(self, new_hold_mode):
        logging.info(f"Setting hold mode to {new_hold_mode}")
        new_code = self.HOLD_MODE_TO_CODE[new_hold_mode]
        r = self.api_post("tstat", json={"hold": new_code})
        if r == None:
           logging.info(f"Thermostat set hold failed")
 
    def set_clock(self):
        logging.info(f"Setting clock")
        n = datetime.now()
        d = {
            "day": n.weekday(),
            "hour": n.hour,
            "minute": n.minute
        }
        r = self.api_post("tstat", json={"time": d})
        if r == None:
           logging.info(f"Thermostat set clock failed")

def end_well(signum, stackframe):
    logging.info("Stopping MQTT loop...")
    client.publish(AVAILABLE_TOPIC, "offline", retain=False)
    client.disconnect()
    client.loop_stop()
    logging.info("Stopped MQTT loop...")

    global run
    logging.info("Stopping Main loop...")
    run = False

def on_log(client, userdata, level, buf):
    logging.info("mqtt: ", buf, level)

def on_connect(client, userdata, flags, rc):
    client.subscribe(SET_TEMP)
    client.subscribe(SET_MODE)
    client.subscribe(SET_FAN)
    client.subscribe(SET_HOLD)
    client.message_callback_add(SET_TEMP, on_set_temp)
    client.message_callback_add(SET_MODE, on_set_mode)
    client.message_callback_add(SET_FAN, on_set_fan)
    client.message_callback_add(SET_HOLD, on_set_hold)

def on_set_temp(client, userdata, msg):
    client.publish(TARGET_TEMP_TOPIC, msg.payload.decode(), retain=False)
    tstat.set_temp(msg.payload.decode())

def on_set_mode(client, userdata, msg):
    client.publish(MODE_TOPIC, msg.payload.decode(), retain=False)
    tstat.set_mode(msg.payload.decode())

def on_set_fan(client, userdata, msg):
    client.publish(FAN_MODE_TOPIC, msg.payload.decode(), retain=False)
    tstat.set_fan(msg.payload.decode())

def on_set_hold(client, userdata, msg):
    client.publish(HOLD_TOPIC, msg.payload.decode(), retain=False)
    tstat.set_hold(msg.payload.decode())

#############################################
###### MAIN ######
#############################################

signal.signal(signal.SIGINT, end_well)
signal.signal(signal.SIGTERM, end_well)


client = mqtt.Client(client_id=MQTT_ID)
#client.on_log = on_log
client.username_pw_set(USERNAME, PASSWORD)
client.will_set(AVAILABLE_TOPIC, "offline")
client.on_connect = on_connect
client.connect(BROKER, port=int(PORT))
client.loop_start()

tstat = CT50(therm_address = TSTAT_IP)
run = True
previous_status = ""

while run:

    client.publish(AVAILABLE_TOPIC, "online", retain=False)

    if tstat.update_status():
        # will send updates every minute because of the time changing minimum.
        # Otherwise will update every time relevent tstat data changes.
        if json.dumps(tstat.current_stat) != previous_status:
            client.publish(STATUS_TOPIC, json.dumps(tstat.current_stat), retain=False)
            previous_status = json.dumps(tstat.current_stat)
    
            logging.info(f"Status: {repr(tstat.current_stat)}")
    
            client.publish(HVAC_ACTION_TOPIC, tstat.current_stat['hvac_action'], retain=False)
            client.publish(CURRENT_TEMP_TOPIC, tstat.current_stat['temp'], retain=False)
            client.publish(TARGET_TEMP_TOPIC, tstat.current_stat['target_temp'], retain=False)
            client.publish(FAN_TOPIC, tstat.current_stat['fan_state'], retain=False)
            client.publish(FAN_MODE_TOPIC, tstat.current_stat['fan_mode'], retain=False)
            client.publish(MODE_TOPIC, tstat.current_stat['mode'], retain=False)
            client.publish(HOLD_TOPIC, tstat.current_stat['hold_mode'], retain=False)
    else:
        logging.info("Update status failed")

    sleep(10)

logging.info("Exiting....")
quit()

