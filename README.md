# radiotherm2mqtt
Radiotherm ct50 thermostat to MQTT

I moved to this from the Home assistant integration because HA didn't retry and would go unavailable constantly.


## HA Thermostat configs

### Hold switch
```
mqtt:
  switch:
    - name: Kitchen_hold
      unique_id: kitchen_hold
      availability:
        - topic: "climate/tele/kitchen_tstat/available"
      state_topic: "climate/stat/kitchen_tstat/hold"
      command_topic: "climate/cmnd/kitchen_tstat/sethold"
      payload_on: "hold"
      payload_off: "program"
```
### Thermostat
```
  climate:
    - name: Kitchen
      unique_id: kitchen_tstat
      modes:
        - "off"
        - "cool"
        - "heat"
        - "auto"
      fan_modes:
        - "on"
        - "auto"
      availability:
        - topic: "climate/tele/kitchen_tstat/available"
      action_topic: "climate/stat/kitchen_tstat/hvac_action"
      mode_command_topic: "climate/cmnd/kitchen_tstat/setmode"
      mode_state_topic: "climate/stat/kitchen_tstat/mode"
      temperature_command_topic: "climate/cmnd/kitchen_tstat/settemp"
      current_temperature_topic: "climate/stat/kitchen_tstat/current_temperature"
      temperature_state_topic: "climate/stat/kitchen_tstat/target_temperature"
      fan_mode_command_topic: "climate/cmnd/kitchen_tstat/setfan"
      fan_mode_state_topic: "climate/stat/kitchen_tstat/fan_mode"
      precision: 0.5
```
### systemd
~~~
[Unit]
Description=Python script to recieve data from Radiotherm thermostate and publish to mqtt
After=syslog.target network.target

[Service]
User=htrn
WorkingDirectory=/usr/src/radiotherm2mqtt
ExecStart=/usr/bin/python3 /usr/src/radiotherm2mqtt/radiotherm2mqtt_kitchen.py

Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```
