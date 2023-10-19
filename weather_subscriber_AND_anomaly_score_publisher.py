import json
import asyncio
from datetime import datetime

from pyensign.ensign import Ensign
from pyensign.api.v1beta1.ensign_pb2 import Nack
from pyensign.events import Event

from river import anomaly, compose, feature_extraction, preprocessing


class WeatherSubscriberANDAnomalyScorePublisher:

    def __init__(self, sub_topic="weather_data", pub_topic="score_data"):

        self.topic = sub_topic
        self.pub_topic = pub_topic
        self.datatype = "application/json"
        self.ensign = Ensign()

        self.newest_data_time = None
        self.current_time = None

    async def print_ack(self, ack):

        ts = datetime.fromtimestamp(ack.committed.seconds + ack.committed.nanos / 1e9)
        print(f"Event committed at {ts}")

    async def print_nack(self, nack):

        print(f"Event was not committed with error {nack.code}: {nack.error}")

    def run(self):

        try:
            asyncio.run(self.subscribe())
        except Exception as e:
            print(f"Error while running subscriber: {e}")

    def lda_process(self, origin_data):
        # Convert 'daytime' value from True/False to 1/0
        origin_data['daytime'] = 1 if origin_data['daytime'] else 0

        # Convert windSpeed to a numerical value
        origin_data['windSpeed'] = int(origin_data['windSpeed'].split()[0])

        # Extracting only the keys you need
        filtered_data = {key: origin_data[key] for key in
                         ['summary', 'temperature', 'daytime', 'dewpoint', 'probabilityOfPrecipitation',
                          'relativeHumidity', 'windSpeed']}

        # LDA the summary column and replace the origin categorical summary with two components
        transformed_summary = self.LDA.transform_one(filtered_data['summary'])

        # Rename the keys
        renamed_output = {
            'LDA_component_1': transformed_summary[0],
            'LDA_component_2': transformed_summary[1]
        }

        # Merge the renamed output with the original data
        filtered_data.update(renamed_output)

        # Drop the original 'summary' field
        filtered_data.pop('summary', None)

        return filtered_data

    def min_max_scale(self, origin_data):

        return self.scaler.learn_one(origin_data).transform_one(origin_data)

    def halfspacetrees_train(self, origin_data):

        return self.hst.learn_one(origin_data).score_one(origin_data)

    def reset_all_process(self):
        print('Reset model')
        # We assume there are 168 coming data to train the model
        self.LDA = compose.Pipeline(
            (feature_extraction.BagOfWords()),
            (preprocessing.LDA(n_components=2, number_of_documents=168))
        )
        self.scaler = preprocessing.MinMaxScaler()

        #
        self.hst = anomaly.HalfSpaceTrees(n_trees=25, height=6, window_size=2)

    def check_whether_reset_model(self, data):
        # Extract and parse the 'start' date from the weather report
        start_date_str = data['start'].split('T')[0]  # Extract the date part
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

        # Check and compare
        if self.newest_data_time is None or (start_date < self.newest_data_time):
            self.newest_data_time = start_date
            self.current_time = data['start']
            return True
        else:
            self.newest_data_time = start_date
            return False

    async def handle_event(self, event):

        origin_data = json.loads(event.data)

        # Check whether the data duplicate (Another 7*24 data coming, we need to reset model)
        if self.check_whether_reset_model(origin_data):
            self.reset_all_process()

        print("New weather report received:", origin_data)
        # LDA process
        LDA_data = self.lda_process(origin_data)
        # Min_Max scale
        min_max_scaled_data = self.min_max_scale(LDA_data)
        # Apply HalfSpaceTrees model
        score = self.halfspacetrees_train(min_max_scaled_data)
        print(score)
        # Add current time and score to the end of data
        origin_data["data_created_time"] = self.current_time
        origin_data["score"] = score
        new_event = Event(json.dumps(origin_data).encode("utf-8"), mimetype=self.datatype)

        await event.ack()
        await self.ensign.publish(self.pub_topic, new_event, on_ack=self.print_ack, on_nack=self.print_nack)

    async def subscribe(self):

        id = await self.ensign.topic_id(self.topic)
        async for event in self.ensign.subscribe(id):
            await self.handle_event(event)


if __name__ == "__main__":
    subscriber = WeatherSubscriberANDAnomalyScorePublisher()
    subscriber.run()
