import forecastio, os

API_KEY = os.getenv('FORECAST_API_KEY')
response = forecastio.load_forecast(API_KEY, 38.2889, -122.4589)

print(response.offset())
