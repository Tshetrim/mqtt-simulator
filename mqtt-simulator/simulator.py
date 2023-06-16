import json
from topic import TopicAuto


class Simulator:
    def __init__(self, settings_file):
        self.broker_url = None
        self.broker_port = None
        self.topics = []
        self.load_settings(settings_file)

    def load_settings(self, settings_file):
        with open(settings_file) as json_file:
            config = json.load(json_file)
            self.broker_url = config["BROKER_URL"]
            self.broker_port = config["BROKER_PORT"]
            # read each configured topic
            for topic in config["TOPICS"]:
                topic_data = topic["DATA"]
                topic_time_interval = topic["TIME_INTERVAL"]
                topic_suffix = topic.get("SUFFIX", "")  # Here we add the suffix if it exists
                if topic["TYPE"] == "single":
                    # create single topic with format: /{PREFIX}
                    topic_url = topic["PREFIX"]
                    topic_url += "/" + topic_suffix if topic_suffix else ""  # Append suffix if present
                    self.topics.append(
                        TopicAuto(self.broker_url, self.broker_port, topic_url, topic_data, topic_time_interval)
                    )
                elif topic["TYPE"] == "multiple":
                    # create multiple topics with format: /{PREFIX}/{id}
                    for id in range(topic["RANGE_START"], topic["RANGE_END"] + 1):
                        topic_url = topic["PREFIX"] + str(id)
                        topic_url += "/" + topic_suffix if topic_suffix else ""  # Append suffix if present
                        self.topics.append(
                            TopicAuto(self.broker_url, self.broker_port, topic_url, topic_data, topic_time_interval)
                        )
                elif topic["TYPE"] == "list":
                    # create multiple topics with format: /{PREFIX}/{item}
                    for item in topic["LIST"]:
                        topic_url = topic["PREFIX"] + str(item)
                        topic_url += "/" + topic_suffix if topic_suffix else ""  # Append suffix if present
                        self.topics.append(
                            TopicAuto(self.broker_url, self.broker_port, topic_url, topic_data, topic_time_interval)
                        )

    def run(self):
        for topic in self.topics:
            print(f"Starting: {topic.topic_url} ...")
            topic.start()

    def stop(self):
        for topic in self.topics:
            print(f"Stopping: {topic.topic_url} ...")
            topic.stop()
