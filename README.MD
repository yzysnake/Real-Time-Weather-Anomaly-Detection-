# Hackathon Fall 2023 - By Group - Funny Mud Pee

## Requirement


### Install the dependencies
The code is running on python==3.11, and make sure the templates folder exists.
```bash
cd WeatherDataAnomalyDetection 
pip install -r requirements.txt
```


### Fill in Correct Pyensign Keys
Fill in your own Pyensign Keys in each code

Make sure each topic name is never being used before

### Run the codes by order

Run weighted_anomaly_score_subscriber_AND_dashboard.py
```bash
python weighted_anomaly_score_subscriber_AND_dashboard.py
```
A local host website's address will pop up, copy and paste it to your own browser.

If it mentions the port is being used, change the port number or kill the thread using it:
```python
socketio.run(app, port=5059, allow_unsafe_werkzeug=True)
```
Then run anomaly_score_subscriber_AND_weighted_anomaly_score_publisher.py
```bash
python anomaly_score_subscriber_AND_weighted_anomaly_score_publisher.py
```
Then run weather_subscriber_AND_anomaly_score_publisher.py
```bash
python weather_subscriber_AND_anomaly_score_publisher.py
```
Finally, run weather_publisher.py
```bash
python weather_publisher.py
```

Then the data points should pop up in the graphs on website

keep the code and website running. New weather data and weigheted score will update the plots every 1 hour.

Any questions please contact zzy5188@uchicago.edu

