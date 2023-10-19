from flask import Flask, render_template
from flask_socketio import SocketIO
from pyensign.ensign import Ensign
import json
import asyncio

app = Flask(__name__)
socketio = SocketIO(app)


class WeightedAnomalyScoreSubscriberDashboard:

    def __init__(self, sub_topic="weighted_score_data"):
        self.sub_topic = sub_topic
        self.ensign = self.ensign = Ensign()

    async def pull_weighted_score(self, event):
        origin_data = json.loads(event.data)

        # Emit the data to the frontend via WebSockets
        socketio.emit('update_data', origin_data)

        await event.ack()

    async def subscribe(self):
        await self.ensign.ensure_topic_exists(self.sub_topic)
        async for event in self.ensign.subscribe(self.sub_topic):
            await self.pull_weighted_score(event)

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.subscribe())


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    subscriber = WeightedAnomalyScoreSubscriberDashboard()
    # Start the subscriber and Flask server in parallel
    socketio.start_background_task(target=subscriber.run)
    # Use a port that is not occupied
    socketio.run(app, port=5059, allow_unsafe_werkzeug=True)
