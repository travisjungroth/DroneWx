import forecastio, os

API_KEY = os.getenv('FORECAST_API_KEY')
response = forecastio.load_forecast(API_KEY, 38.2889, -122.4589)

if(int(response.http_headers['X-Forecast-API-Calls']) > 38):
    with open('kill', 'w') as f:
        pass
