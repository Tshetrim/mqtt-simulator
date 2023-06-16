import time
import datetime
import json
import random
import threading
from abc import ABC, abstractmethod
import paho.mqtt.client as mqtt
from expression_evaluator import ExpressionEvaluator


class Topic(ABC):
    def __init__(self, broker_url, broker_port, topic_url, topic_data):
        self.broker_url = broker_url
        self.broker_port = broker_port
        self.topic_url = topic_url
        self.topic_data = topic_data
        self.client = None

    def connect(self):
        self.client = mqtt.Client(self.topic_url, clean_session=True, transport="tcp")
        self.client.on_publish = self.on_publish
        self.client.connect(self.broker_url, self.broker_port)
        self.client.loop_start()

    @abstractmethod
    def run(self):
        pass

    def disconnect(self):
        self.client.loop_end()
        self.client.disconnect()

    def on_publish(self, client, userdata, result):
        print(f'[{time.strftime("%H:%M:%S")}] Data published on: {self.topic_url}')


class TopicAuto(Topic, threading.Thread):
    def __init__(self, broker_url, broker_port, topic_url, topic_data, time_interval):
        Topic.__init__(self, broker_url, broker_port, topic_url, topic_data)
        threading.Thread.__init__(self, args=(), kwargs=None)
        self.time_interval = time_interval
        self.old_payload = None
        self.expression_evaluators = {}

    def run(self):
        self.connect()
        while True:
            payload = self.generate_payload()
            self.old_payload = payload
            self.client.publish(topic=self.topic_url, payload=json.dumps(payload), qos=2, retain=False)
            time.sleep(self.time_interval)

    def generate_initial_value(self, data):
        if "INITIAL_VALUE" in data:
            return data["INITIAL_VALUE"]
        elif data["TYPE"] == "int":
            return random.randint(data["MIN_VALUE"], data["MAX_VALUE"])
        elif data["TYPE"] == "float":
            return random.uniform(data["MIN_VALUE"], data["MAX_VALUE"])
        elif data["TYPE"] == "bool":
            return random.choice([True, False])
        elif data["TYPE"] == "math_expression":
            self.expression_evaluators[data["NAME"]] = ExpressionEvaluator(
                data["MATH_EXPRESSION"],
                data["INTERVAL_START"],
                data["INTERVAL_END"],
                data["MIN_DELTA"],
                data["MAX_DELTA"],
            )
            return self.expression_evaluators[data["NAME"]].get_current_expression_value()
        elif data["TYPE"] == "string":
            return random.choice(data["STRING_VALUES"])
        elif data["TYPE"] == "object" and data.get("COLLECTION_TYPE") == "array":
            initial_value = data.get("INITIAL_VALUE", 0)  # If "INITIAL_VALUE" does not exist, use 1 as default
            return [self.generate_payload(data["CHILDREN"]) for _ in range(initial_value)]
        elif data["TYPE"] == "object" and data.get("COLLECTION_TYPE") == "dictionary":
            return self.generate_payload(data["CHILDREN"])

    def generate_next_value(self, data, old_value):
        if "RESET_PROBABILITY" in data and random.random() < data["RESET_PROBABILITY"]:
            return self.generate_initial_value(data)
        if (
            "RESTART_ON_BOUNDARIES" in data
            and data["RESTART_ON_BOUNDARIES"]
            and (old_value == data["MIN_VALUE"] or old_value == data["MAX_VALUE"])
        ):
            return self.generate_initial_value(data)

        if "RETAIN_PROBABILITY" in data and random.random() < data["RETAIN_PROBABILITY"]:
            return old_value
        if data["TYPE"] == "bool":
            return not old_value
        elif data["TYPE"] == "math_expression":
            return self.expression_evaluators[data["NAME"]].evaluate_expression()
        elif data["TYPE"] == "string":  # added this block
            return random.choice(data["STRING_VALUES"])
        elif data["TYPE"] == "object" and data.get("COLLECTION_TYPE") == "array":
            return [self.generate_payload(data["CHILDREN"], value) for value in old_value]
        elif data["TYPE"] == "object" and data.get("COLLECTION_TYPE") == "dictionary":
            return self.generate_payload(data["CHILDREN"], old_value)
        elif data["TYPE"] == "timestamp":
            return datetime.datetime.now().isoformat()
        else:
            # generating value for int or float
            step = random.uniform(0, data["MAX_STEP"])
            step = round(step) if data["TYPE"] == "int" else step
            increase_probability = data["INCREASE_PROBABILITY"] if "INCREASE_PROBABILITY" in data else 0.5
            if random.random() < (1 - increase_probability):
                step *= -1
            return max(old_value + step, data["MIN_VALUE"]) if step < 0 else min(old_value + step, data["MAX_VALUE"])

    def generate_payload(self, topic_data=None, old_payload=None):
        if topic_data is None:
            topic_data = self.topic_data
        if old_payload is None:
            old_payload = self.old_payload
        payload = {}
        if old_payload is None:
            # generate initial data
            for data in topic_data:
                if data["NAME"] == "timestamp":
                    payload[data["NAME"]] = datetime.datetime.now().isoformat()
                else:
                    payload[data["NAME"]] = self.generate_initial_value(data)
        else:
            # generate next data
            for data in topic_data:
                old_value = (
                    old_payload.get(data["NAME"]) if isinstance(old_payload, dict) else old_payload
                )  # Check type of old_payload
                if data["NAME"] == "timestamp":
                    payload[data["NAME"]] = datetime.datetime.now().isoformat()
                elif data["TYPE"] == "object":
                    if data.get("COLLECTION_TYPE") == "array":
                        payload[data["NAME"]] = [
                            self.generate_next_value(child_data, old_value[i] if old_value else None)
                            for i, child_data in enumerate(data["CHILDREN"])
                        ]
                    else:
                        payload[data["NAME"]] = self.generate_next_value(data, old_value)
                else:
                    payload[data["NAME"]] = (
                        self.generate_next_value(data, old_value)
                        if old_value is not None
                        else self.generate_initial_value(data)
                    )
        return payload
