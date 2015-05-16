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

            #Failsafe to kill the app if it gets too popular (paying for API calls)
            if(os.path.exists('kill')):
                return render_template('index.html')

            nearby_tfrs = dronewx.tfr_search(location, distance)
            nearby_airports = dronewx.nearby_airports_finder(location, distance)
            response = forecastio.load_forecast(API_KEY, location[0], location[1])

            max_calls_per_day = 20000
            if(int(response.http_headers['X-Forecast-API-Calls']) > max_calls_per_day):
                with open('kill', 'w') as f:
                    pass
            weather = Weather(response)

            return render_template('briefing.html', distance=distance, airports=nearby_airports, tfrs = nearby_tfrs, weather = weather)
        except ValueError:
            return render_template('index.html')
    else:
        return render_template('index.html')

if __name__=='__main__':
    app.run(debug=True)
