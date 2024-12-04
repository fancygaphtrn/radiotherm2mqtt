import requests
from time import sleep
from datetime import datetime
import paho.mqtt.client as mqtt
import signal
import sys
from time import sleep
import json
from configparser import ConfigParser
import argparse

DEVICE_NAME="familyroom_tstat"
TSTAT_IP = "fr-tstat.lan"
ID="familyroom_tstat"

MQTT_ID = "familyroom_tstat"
BROKER = "192.168.5.200"
PORT = 1883
USERNAME = "<<mqtt_username>>"
PASSWORD = "<<mqtt_password>>"

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
print("Loading configuration file: " + args.config, flush=True)
print("Device: " + args.device, flush=True)

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

print("DEVICE_NAME: " + DEVICE_NAME, flush=True)
print("TSTAT_IP:    " + TSTAT_IP, flush=True)
print("ID:          " + ID, flush=True)
print("MQTT_ID:     " + MQTT_ID, flush=True)
print("BROKER:      " + BROKER, flush=True)
print("PORT:        " + PORT, flush=True)
print("USERNAME:    " + USERNAME, flush=True)
print("PASSWORD:    " + PASSWORD, flush=True)

STATUS_TOPIC = "climate/stat/{0}/status".format(DEVICE_NAME)
HVAC_ACTION_TOPIC = "climate/stat/{0}/hvac_action".format(DEVICE_NAME)
CURRENT_TEMP_TOPIC = "climate/stat/{0}/current_temperature".format(DEVICE_NAME)
TARGET_TEMP_TOPIC = "climate/stat/{0}/target_temperature".format(DEVICE_NAME)
FAN_TOPIC = "climate/stat/{0}/fan".format(DEVICE_NAME)
FAN_MODE_TOPIC = "climate/stat/{0}/fan_mode".format(DEVICE_NAME)
MODE_TOPIC = "climate/stat/{0}/mode".format(DEVICE_NAME)
HOLD_TOPIC = "climate/stat/{0}/hold".format(DEVICE_NAME)
SET_TEMP = "climate/cmnd/{0}/settemp".format(DEVICE_NAME)
SET_MODE = "climate/cmnd/{0}/setmode".format(DEVICE_NAME)
SET_FAN = "climate/cmnd/{0}/setfan".format(DEVICE_NAME)
SET_HOLD = "climate/cmnd/{0}/sethold".format(DEVICE_NAME)
AVAILABLE_TOPIC = "climate/tele/{0}/available".format(DEVICE_NAME)


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

    def __init__(self, therm_address, error_delay=5, timeout=5):
        self.address = therm_address
        self.base_url = f"http://{therm_address}/"
        self.error_delay = error_delay
        self.timeout = timeout
        self.set_clock()
        self.update_status()

    def api_get(self, cmd):
        try:
            r = requests.get(self.base_url + cmd, timeout=self.timeout)
            if r.status_code != 200:
                print(f"Thermostat responed with error {r.text}", flush=True)
                raise
            return r
        except Exception as ex:
            print("Exception with api call: " + cmd, flush=True)
            print(repr(ex), flush=True)
            raise

    def api_post(self, cmd, json):
        try:
            r = requests.post(self.base_url + cmd, json=json,
                              timeout=self.timeout)
            if r.status_code != 200:
                print(f"Thermostat responed with error {r.text}", flush=True)
                raise
            return r
        except Exception as ex:
            print("Exception with api call: " + cmd, flush=True)
            print(repr(ex), flush=True)
            raise

    def update_status(self):
        while True:
            while True:
                try:
                    r = self.api_get("tstat")
                    break
                except:
                    sleep(self.error_delay)
            if r.status_code != 200:
                print(f"Thermostat responed with error {r.text}", flush=True)
                return r.json

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
                # print(repr(stat), flush=True)
                break
            except Exception as ex:
                print("Error updating status, retry...", flush=True)
                print(repr(ex), flush=True)
                sleep(self.error_delay)

        self.current_stat = stat
        print(repr(self.current_stat), flush=True)
        return stat

    def set_temp(self, new_temp):
        temp = float(new_temp)
        print(f"Setting target temp to {temp}", flush=True)

        while True:
            try:
                if self.current_stat["mode"] == "heat":
                    r = self.api_post("tstat", json={"t_heat": temp})
                elif self.current_stat["mode"] == "cool":
                    r = self.api_post("tstat", json={"t_cool": temp})
                if r.status_code != 200:
                  print(f"Thermostat set temp responed with error {r.text}", flush=True)
                break
            except Exception as e:
                print("Error setting temp, trying again...", flush=True)
                print(repr(e), flush=True)
                sleep(self.error_delay)
        return self.update_status()

    def set_mode(self, new_mode):
        print(f"Setting HVAC mode to {new_mode}", flush=True)
        new_code = self.TEMP_MODE_TO_CODE[new_mode]
        while True:
            try:
                r = self.api_post("tstat", json={"tmode": new_code})
                break
            except Exception as e:
                print("Error setting HVAC mode, trying again...", flush=True)
                print(repr(e), flush=True)
                sleep(self.error_delay)

        if r.status_code != 200:
            print(f"Thermostat set mode responed with error {r.text}", flush=True)

        return self.update_status()

    def set_fan(self, new_fan_mode):
        print(f"Setting fan to {new_fan_mode}", flush=True)
        new_code = self.FAN_MODE_TO_CODE[new_fan_mode]
        while True:
            try:
                r = self.api_post("tstat", json={"fmode": new_code})
                break
            except Exception as e:
                print("Error setting fan mode, trying again...", flush=True)
                print(repr(e), flush=True)
                sleep(self.error_delay)

        if r.status_code != 200:
            print(f"Thermostat set fan responed with error {r.text}", flush=True)

        return self.update_status()

    def set_hold(self, new_hold_mode):
        print(f"Setting hold mode to {new_hold_mode}", flush=True)
        new_code = self.HOLD_MODE_TO_CODE[new_hold_mode]
        while True:
            try:
                r = self.api_post("tstat", json={"hold": new_code})
                break
            except Exception as e:
                print("Error setting hold mode, trying again...", flush=True)
                print(repr(e), flush=True)
                sleep(self.error_delay)

        if r.status_code != 200:
            print(f"Thermostat set hold responed with error {r.text}", flush=True)

        return self.update_status()

    def set_clock(self):
        n = datetime.now()
        d = {
            "day": n.weekday(),
            "hour": n.hour,
            "minute": n.minute
        }
        while True:
            try:
                r = self.api_post("tstat", json={"time": d})
                break
            except Exception as e:
                print("Error setting time, trying again...", flush=True)
                print(repr(e), flush=True)
                sleep(self.error_delay)

        if r.status_code != 200:
            print(f"Thermostat set time responed with error {r.text}", flush=True)

def end_well(signum, stackframe):
    global run
    print("Stopping MQTT loop...", flush=True)
    client.publish(AVAILABLE_TOPIC, "offline", retain=False)
    client.disconnect()
    client.loop_stop()
    quit()

def on_log(client, userdata, level, buf):
    print("mqtt: ", buf, level, flush=True)

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
    print(repr(tstat.current_stat), flush=True)

def on_set_mode(client, userdata, msg):
    client.publish(MODE_TOPIC, msg.payload.decode(), retain=False)
    tstat.set_mode(msg.payload.decode())
    print(repr(tstat.current_stat), flush=True)

def on_set_fan(client, userdata, msg):
    client.publish(FAN_MODE_TOPIC, msg.payload.decode(), retain=False)
    tstat.set_fan(msg.payload.decode())
    print(repr(tstat.current_stat), flush=True)

def on_set_hold(client, userdata, msg):
    client.publish(HOLD_TOPIC, msg.payload.decode(), retain=False)
    tstat.set_hold(msg.payload.decode())
    print(repr(tstat.current_stat), flush=True)

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

while True:

    tstat.update_status()
    print(repr(tstat.current_stat), flush=True)

    client.publish(AVAILABLE_TOPIC, "online", retain=False)

    client.publish(STATUS_TOPIC, json.dumps(tstat.current_stat), retain=False)
    client.publish(HVAC_ACTION_TOPIC, tstat.current_stat['hvac_action'], retain=False)
    client.publish(CURRENT_TEMP_TOPIC, tstat.current_stat['temp'], retain=False)
    client.publish(TARGET_TEMP_TOPIC, tstat.current_stat['target_temp'], retain=False)
    client.publish(FAN_TOPIC, tstat.current_stat['fan_state'], retain=False)
    client.publish(FAN_MODE_TOPIC, tstat.current_stat['fan_mode'], retain=False)
    client.publish(MODE_TOPIC, tstat.current_stat['mode'], retain=False)
    client.publish(HOLD_TOPIC, tstat.current_stat['hold_mode'], retain=False)
    sleep(10)

