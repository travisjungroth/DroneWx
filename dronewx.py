from math import *
from bs4 import BeautifulSoup
from shapely.geometry import Polygon
import requests, pickle, os, time, datetime, re, forecastio
import xml.etree.ElementTree as ET

def main() :
    API_KEY = os.getenv('FORECAST_API_KEY')
    location = (39.1,-121.436389)
    radius = 10
    distance = 10

    nearby_tfrs = tfr_search(location, distance)
    nearby_airports = nearby_airports_finder(location, radius)

    forecast = forecastio.load_forecast(API_KEY, location[0], location[1])
    current = forecast.currently()

    print('Current Weather')
    print('---------------')
    print('Wind: {} at {}kts'.format(current.windBearing,round(current.windSpeed*0.87)))
    print('Temperature: {}F'.format(round(current.temperature)))
    print('Dew point: {}F'.format(round(current.dewPoint)))
    print('Clouds: {}'.format(cloud_cover(current.cloudCover)))
    print('Est. Cloud Base: {} ft AGL'.format(int(round((current.temperature - current.dewPoint) * 227.27, -2))))
    print('Chance of Rain: {}%'.format(current.precipProbability * 100))

    for nearby_airport in nearby_airports :
        print ('{} Distance: {} mi {}'.format(nearby_airport.airport.name, nearby_airport.distance, nearby_airport.direction))

    for nearby_tfr in nearby_tfrs :
        print (nearby_tfr.id)

class Airport(object):
    def __init__(self, line) :
        self.name = line[133:183].strip()
        self.identifier = line[27:31].strip()
        self.facility_type = line[14:27].strip()
        self.lat = float(line[538:549].strip()) / 3600
        self.lon = 0 - float(line[565:576].strip()) / 3600
        self.phone_number = line[507:523].strip()

class NearbyAirport(Airport) :
    def __init__(self, airport, distance, direction):
        self.airport = airport
        self.distance = distance
        self.direction = direction

def airports_txt_parser() :
    airports = []

    with open('briefing/files/APT.txt', 'r', encoding="latin1") as airports_file :
        for line in airports_file :
            if line[0:3] == 'APT' :
                airports.append(Airport(line))
    return airports

def airports_saver() :
    airports = airports_txt_parser()
    with open('briefing/files/airports.pickle', 'wb') as f :
        pickle.dump(airports, f, pickle.HIGHEST_PROTOCOL)

def haversine(lat1, lon1, lat2, lon2) :
    #Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    #Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    radius = 3963.16
    distance = round(radius * c, 1)
    return distance

def direction_finder(lat1, lon1, lat2, lon2) :
    #Find the heading to the airport, using an equirectangular projection
    deg = (90 - degrees(atan2(lat2-lat1, lon2-lon1))) % 360
    #Convert the degrees to orthogonal
    if deg <= 22.5 or 337.5 < deg:
        return 'N'
    if 22.5 < deg <= 67.5 :
        return 'NE'
    if 67.5 < deg <= 112.5 :
        return 'E'
    if 112.5 < deg <= 157.5 :
        return 'SE'
    if 157.5 < deg <= 202.5 :
        return 'SE'
    if 202.5 < deg <= 247.5 :
        return 'SE'
    if 247.5 < deg <= 292.5 :
        return 'SE'
    if 292.5 < deg <= 337.5 :
        return 'SE'

def nearby_airports_finder(location, radius) :
    #TODO add logic to update the airports pickle file

    with open('briefing/files/airports.pickle', 'rb') as f :
        airports = pickle.load(f)
    nearby_airports = []
    for airport in airports :
            distance = haversine(location[0], location[1], airport.lat, airport.lon)
            if distance < radius :
                direction = direction_finder(location[0], location[1], airport.lat, airport.lon)
                nearby_airports.append(NearbyAirport(airport, distance, direction))
    #Sort them by distance
    nearby_airports.sort(key=lambda nearby_airport: nearby_airport.distance)
    return nearby_airports

class Tfr(object) :
    def __init__(self, xml, tfr_id):
        self.id = tfr_id
        root = ET.fromstring(xml)
        self.time_zone_start = root.find('.//codeTimeZone').text
        self.time_zone_end = root.find('.//codeExpirationTimeZone').text
        self.city = root.find('.//txtNameCity').text
        self.state = root.find('.//txtNameUSState').text
        self.text = root.find('.//txtDescrTraditional').text
        self.issued_time = notam_time_to_timestamp(root.find('.//dateIssued').text)

        instructions = []
        for instruction in root.findall('.//txtInstr') :
            instructions.append(instruction.text)
        self.instructions = instructions

        zones = []
        for tfr_area_group in root.findall('.//TFRAreaGroup') :
            zone = TfrZone(tfr_area_group)
            zones.append(zone)
        self.zones = zones


class TfrZone(object) :
    def __init__(self, tfr_area_group) :
        #Timestamps of the start and end time.
        self.effective = notam_time_to_timestamp(tfr_area_group.find('.//dateEffective').text)
        self.expire = notam_time_to_timestamp(tfr_area_group.find('.//dateEffective').text)
        #A list of (x,y)
        points = []
        for avx in tfr_area_group.findall('./abdMergedArea/Avx') :
            lat = degrees_string_to_float(avx.find('geoLat').text)
            lon = degrees_string_to_float(avx.find('geoLong').text)
            #lat, lon reversed to become x,y
            points.append((lon,lat))
        self.points = points
        #Could add vertical data here. Not going to now, just going to warn pilots of all TFR footprints.

def lon_distance(lat) :
    lon_distance = cos(radians(lat)) * 69
    return lon_distance

def user_rectangle_points(location, distance) :
    """Converts the distance to a degree difference, then draws a box with length
    twice the distance around the user point."""

    lat, lon = location
    lat_difference = distance / 69
    lon_difference = distance / lon_distance(lat)

    user_rectangle = ([lon + lon_difference, lat + lat_difference],
        [lon - lon_difference, lat + lat_difference],
        [lon - lon_difference, lat - lat_difference],
        [lon + lon_difference, lat - lat_difference])
    return user_rectangle

def tfr_search(location, distance) :
    tfrs = tfr_loader(tfr_list_loader())
    nearby_tfrs = []

    user_rectangle = Polygon(user_rectangle_points(location, distance))

    for tfr_id in tfrs :
        tfr = tfrs[tfr_id]
        zone_match = False
        for zone in tfr.zones :
            zone_shape = Polygon(zone.points)
            if user_rectangle.intersects(zone_shape) :
                zone_match = True
        if zone_match :
            nearby_tfrs.append(tfr)

    return nearby_tfrs

def tfr_loader(tfr_list) :
    with open('files/tfrs.pickle', 'rb') as f :
        tfrs = pickle.load(f)

    #Tfrs without location data get ignored and saved to this list.
    with open('files/tfr_ignore_list.pickle', 'rb') as f :
        tfr_ignore_list = pickle.load(f)

    for tfr_id in tfr_list :
        if tfr_id not in tfrs :
            url = 'http://tfr.faa.gov/save_pages/detail_' + tfr_id + '.xml'
            r = requests.get('http://tfr.faa.gov/save_pages/detail_' + tfr_id + '.xml')
            r.encoding = 'UTF-8'
            xml = r.text
            #<Avx is the loaction data. Without this, they're impossible to auto map.
            #May also be a national TFR.
            if '<Avx>' not in xml :
                tfr_ignore_list.append(tfr_id)
                with open('files/tfr_ignore_list.pickle', 'wb') as f :
                    pickle.dump(tfr_ignore_list, f, pickle.HIGHEST_PROTOCOL)
                break
            tfrs[tfr_id] = Tfr(xml, tfr_id)
            #Will almost never have to save more than one.
            #Might as well save tfrs in the loop instead of adding logic.
            with open('files/tfrs.pickle', 'wb') as f :
                pickle.dump(tfrs, f, pickle.HIGHEST_PROTOCOL)

    #Delete all the TFRs not on the TFR list
    old_tfrs = []
    for tfr in tfrs :
        if tfr not in tfr_list :
            old_tfrs.append(tfr)

    for old_tfr in old_tfrs :
        tfrs.pop(old_tfr, None)
        with open('files/tfrs.pickle', 'wb') as f :
                pickle.dump(tfrs, f, pickle.HIGHEST_PROTOCOL)

    return tfrs

def tfr_list_loader() :
    #time in seconds to check tfr list again
    max_age = 300
    tfr_list_age = time.time() - os.path.getmtime('files/tfr_list.pickle')

    if tfr_list_age > max_age :
        html = requests.get('http://tfr.faa.gov/tfr2/list.html').text
        tfr_list = tfr_list_parser(html)
        with open('files/tfr_list.pickle', 'wb') as f :
            pickle.dump(tfr_list, f, pickle.HIGHEST_PROTOCOL)
    else :
        with open('files/tfr_list.pickle', 'rb') as f :
            tfr_list = pickle.load(f)

    return tfr_list

def tfr_list_parser(html) :
    soup = BeautifulSoup(html)
    tfr_list = []
    for link in soup.find_all("a") :
        url = link.get("href")
        if url :
            if 'save_pages' in url :
                #Ex: '5_1234' First number is last digit of year.
                tfr_id = url[21:27]
                if tfr_id not in tfr_list:
                    tfr_list.append(tfr_id)
    return tfr_list


def notam_time_to_timestamp(time_string) :
    #Takes the timestamp in the notam xml and returns a float timestamp
    timestamp = time.mktime(datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S").timetuple())
    return timestamp

def degrees_string_to_float(string) :
    """Converts a degree string with an orthogonal letter to a signed float.
    Defaults to NW."""
    degrees = float(re.sub('[^0-9\\.]', '', string))
    if 'N' not in string or 'W' in string:
        degrees = 0 - degrees
    return degrees

def cloud_cover(cloud_float) :
    if cloud_float <= 0.0625 :
        cloud_cover = 'Clear'
    if 0.0625 < cloud_float <= 0.3125 :
        cloud_cover = 'Few'
    if 0.3125 < cloud_float <= 0.5  :
        cloud_cover = 'Scattered'
    if 0.5 < cloud_float <= 0.9375   :
        cloud_cover = 'Broken'
    if 0.9375 < cloud_float :
        cloud_cover = 'Overcast'

    return cloud_cover
