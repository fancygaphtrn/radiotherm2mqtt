from myradiotherm import CT50
import paho.mqtt.client as mqtt
import signal
import sys
from time import sleep
import json

DEVICE_NAME="kitchen_tstat"
TSTAT_IP = "kitchen-tstat.lan"
ID="kitchen_tstat"

MQTT_ID = "kitchen_tstat"
BROKER = "192.168.5.200"
PORT = 1883
USERNAME = "<<mqtt_username>>"
PASSWORD = "<<mqtt_password>>"


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



def end_well(signum, stackframe):
    global run
    print("Stopping MQTT loop...", flush=True)
    client.publish(AVAILABLE_TOPIC, "offline", retain=False)
    client.disconnect()
    client.loop_stop()
    run = False


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
client.connect(BROKER, port=PORT)
client.loop_start()

tstat = CT50(therm_address = TSTAT_IP)

client.publish(AVAILABLE_TOPIC, "online", retain=True)

run = True
while run:

    
    tstat.update_status()

    client.publish(STATUS_TOPIC, json.dumps(tstat.current_stat), retain=False)
    client.publish(HVAC_ACTION_TOPIC, tstat.current_stat['hvac_action'], retain=False)
    client.publish(CURRENT_TEMP_TOPIC, tstat.current_stat['temp'], retain=False)
    client.publish(TARGET_TEMP_TOPIC, tstat.current_stat['target_temp'], retain=False)
    client.publish(FAN_TOPIC, tstat.current_stat['fan_state'], retain=False)
    client.publish(FAN_MODE_TOPIC, tstat.current_stat['fan_mode'], retain=False)
    client.publish(MODE_TOPIC, tstat.current_stat['mode'], retain=False)
    client.publish(HOLD_TOPIC, tstat.current_stat['hold_mode'], retain=False)
    sleep(10)
