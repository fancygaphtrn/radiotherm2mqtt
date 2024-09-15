import requests
from time import sleep
from datetime import datetime


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

    def __init__(self, therm_address, error_delay=5, timeout=10):
        self.address = therm_address
        self.base_url = f"http://{therm_address}/"
        self.error_delay = error_delay
        self.timeout = timeout
        self.set_clock()
        self.update_status()

    def api_get(self, cmd):
        try:
            r = requests.get(self.base_url + cmd, timeout=self.timeout)
            return r
        except Exception as ex:
            print("Exception with api call: " + cmd, flush=True)
            print(repr(ex), flush=True)
            raise

    def api_post(self, cmd, json):
        try:
            r = requests.post(self.base_url + cmd, json=json,
                              timeout=self.timeout)
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
                break
            except Exception as e:
                print("Error setting temp, trying again...", flush=True)
                print(repr(e), flush=True)
                sleep(self.error_delay)
        if r.status_code != 200:
            print(f"Thermostat set temp responed with error {r.text}", flush=True)

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
