import json
import asyncio
from datetime import datetime
from pyensign.ensign import Ensign
from pyensign.api.v1beta1.ensign_pb2 import Nack
from pyensign.events import Event
import pandas as pd
import numpy as np


class Anomaly_Score_Subscriber_AND_Weighted_Anomaly_Score_Publisher():

    def __init__(self, sub_topic="score_data", pub_topic='weighted_score_data'):
        self.sub_topic = sub_topic
        self.pub_topic = pub_topic
        self.datatype = "application/json"
        self.ensign = Ensign()
        self.weather_history = pd.DataFrame(columns=['start', 'score', 'data_created_time'])

    async def print_ack(self, ack):
        ts = datetime.fromtimestamp(ack.committed.seconds + ack.committed.nanos / 1e9)
        print(f"Event committed at {ts}")

    async def print_nack(self, nack):
        print(f"Event was not committed with error {nack.code}: {nack.error}")

    def run(self):
        asyncio.get_event_loop().run_until_complete(self.subscribe())

    def exponential_decay_weighting_score(self, sub_weather_history):
        denomin = 0
        numer = 0

        for index, row in sub_weather_history.iterrows():
            forecast_time = pd.to_datetime(row['start'])
            forecast_create_time = pd.to_datetime(row['data_created_time'])
            hours_gap = abs(int((forecast_time - forecast_create_time).total_seconds() / 3600))
            denomin += np.exp(-0.02 * hours_gap)
            numer += np.exp(-0.02 * hours_gap) * float(row['score'])

        return numer / denomin

    async def handle_event(self, event):
        origin_data = json.loads(event.data)

        filtered_data = {key: origin_data[key] for key in
                         ['start', 'score', 'data_created_time']}

        start_time = filtered_data["start"]

        # Store the data in dataframe to yield out weighted score
        self.weather_history = pd.concat([self.weather_history, pd.DataFrame([filtered_data])], ignore_index=True)

        # Get a subset of weather history which has the same start value
        sub_weather_history = pd.DataFrame(columns=['start', 'score', 'data_created_time'])
        sub_weather_history = self.weather_history[self.weather_history["start"] == start_time]

        # Get the weighted score
        weighted_score = self.exponential_decay_weighting_score(sub_weather_history)

        # Delete original score and update a weighted score
        del origin_data['score']
        origin_data['weighted_score'] = weighted_score

        print(origin_data)
        new_event = Event(json.dumps(origin_data).encode("utf-8"), mimetype=self.datatype)

        await event.ack()
        await self.ensign.publish(self.pub_topic, new_event, on_ack=self.print_ack, on_nack=self.print_nack)

    async def subscribe(self):
        # ensure that the topic exists or create it if it doesn't
        await self.ensign.ensure_topic_exists(self.sub_topic)

        async for event in self.ensign.subscribe(self.sub_topic):
            await self.handle_event(event)


if __name__ == "__main__":
    subscriber = Anomaly_Score_Subscriber_AND_Weighted_Anomaly_Score_Publisher()
    subscriber.run()
