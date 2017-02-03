# DroneWx
This project is no longer live.

There are three pieces of information being delivered.

- Weather from the forecast.io api.
- Flight restriction information scraped from the FAA's site.
- Nearby airports from the NASR subscription.

The user location is gathered either from the browser, or the google client side api. The distance is measured from all airports, with the direction and distance of nearby ones returned. The flight restrictions are checked my drawing a circle around the user location, and checking for intersection with charted flight restrictions.
