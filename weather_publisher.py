import json
import asyncio
from datetime import datetime

import requests
from pyensign.events import Event
from pyensign.ensign import Ensign

# The code is based on Data Ground by Rational Labs

# replace with your information
ME = "(weather_anomaly_detection, zzy5188@uchicago.edu)"

# Insert the location and its latitude and longitude correspondingly
# Using Hawaii as an example
LOCS = {"Hawaii": {"lat": "19.7019", "long": "-155.0895"}}

class WeatherPublisher:

    def __init__(self, topic="weather_data", interval=3600, locations=LOCS, user=ME):

        self.topic = topic
        self.interval = interval
        self.locations = locations
        self.url = "https://api.weather.gov/points/"
        self.user = {"User-Agent": user}
        self.datatype = "application/json"
        self.ensign = Ensign()

    async def print_ack(self, ack):

        ts = datetime.fromtimestamp(ack.committed.seconds + ack.committed.nanos / 1e9)
        print(f"Event committed at {ts}")

    async def print_nack(self, nack):

        print(f"Event was not committed with error {nack.code}: {nack.error}")

    def compose_query(self, location):

        lat = location.get("lat", None)
        long = location.get("long", None)
        if lat is None or long is None:
            raise Exception("unable to parse latitude/longitude from location")

        return self.url + lat + "," + long

    def run(self):

        asyncio.run(self.recv_and_publish())

    async def recv_and_publish(self):

        await self.ensign.ensure_topic_exists(self.topic)

        while True:
            for location in self.locations.values():
                query = self.compose_query(location)
                response = requests.get(query).json()
                forecast_url = self.parse_forecast_link(response)
                forecast = requests.get(forecast_url).json()
                events = self.unpack_noaa_response(forecast)
                for event in events:
                    await self.ensign.publish(
                        self.topic,
                        event,
                        on_ack=self.print_ack,
                        on_nack=self.print_nack,
                    )
            await asyncio.sleep(self.interval)

    def parse_forecast_link(self, message):

        properties = message.get("properties", None)
        if properties is None:
            raise Exception("unexpected response from api call, no properties")

        forecast_link = properties.get("forecastHourly", None)
        if forecast_link is None:
            raise Exception("unexpected response from api call, no forecast")

        return forecast_link

    def unpack_noaa_response(self, message):

        properties = message.get("properties", None)
        if properties is None:
            raise Exception("unexpected response from forecast request, no properties")

        periods = properties.get("periods", None)
        if periods is None:
            raise Exception("unexpected response from forecast request, no periods")

        for period in periods:
            data = {
                "location": next(iter(LOCS.keys())),
                "latitude": next(iter(LOCS.values()))['lat'],
                "longitude": next(iter(LOCS.values()))['long'],
                "summary": period.get("shortForecast", None),
                "temperature": period.get("temperature", None),
                "units": period.get("temperatureUnit", None),
                "daytime": period.get("isDaytime", None),
                "dewpoint": period.get("dewpoint", None).get("value", None),
                "probabilityOfPrecipitation": period.get("probabilityOfPrecipitation", None).get("value", None),
                "relativeHumidity": period.get("relativeHumidity", None).get("value", None),
                "windSpeed":period.get("windSpeed", None),
                "start": period.get("startTime", None),
                "end": period.get("endTime", None),
            }

            yield Event(json.dumps(data).encode("utf-8"), mimetype=self.datatype)


if __name__ == "__main__":
    publisher = WeatherPublisher()
    publisher.run()
