from flask import Flask, render_template, url_for
from dronewx import *
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/briefing', methods=['GET','POST'])
def briefing():
    API_KEY = os.getenv('FORECAST_API_KEY')
    location = (39.1,-121.436389)
    distance = 10

    nearby_tfrs = tfr_search(location, distance)
    nearby_airports = nearby_airports_finder(location, distance)
    response = forecastio.load_forecast(API_KEY, location[0], location[1])

    weather = Weather(response)

    return render_template('briefing.html', distance=distance, airports=nearby_airports, tfrs = nearby_tfrs, weather = weather)


if __name__=='__main__':
    app.run(debug=True)
