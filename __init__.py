from flask import Flask, render_template, url_for, request
import os, sys, forecastio
sys.path.append('/home/jungroth/webapps/dronewx/drone')
import dronewx
from dronewx import Weather
app = Flask(__name__)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/briefing')
def briefing():
    if request.args:
        try:
            location = (float(request.args['latitude']), float(request.args['longitude']))

            API_KEY = os.getenv('FORECAST_API_KEY')
            distance = 10

            nearby_tfrs = dronewx.tfr_search(location, distance)
            nearby_airports = dronewx.nearby_airports_finder(location, distance)
            response = forecastio.load_forecast(API_KEY, location[0], location[1])

            weather = Weather(response)

            return render_template('briefing.html', distance=distance, airports=nearby_airports, tfrs = nearby_tfrs, weather = weather)
        except ValueError:
            return render_template('index.html')
    else:
        return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')        
if __name__=='__main__':
    app.run(debug=True)
