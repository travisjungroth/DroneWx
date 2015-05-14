# -*- coding: utf-8 -*-
from math import *
from bs4 import BeautifulSoup
from shapely.geometry import Polygon
import requests, pickle, os, time, datetime, re, forecastio
import xml.etree.ElementTree as ET

class Weather(object):
    def __init__(self, response):
        self.current = WeatherBlockCurrent(response.currently())

        self.hourlySummary = response.hourly().summary

        self.dailySummary = response.daily().summary

        self.hourly = []
        i = 0
        # Limited to 8 hours, and only the one in the future.
        for hour in response.hourly().data:
            if 0 < i < 9:
                self.hourly.append(WeatherBlockHour(hour))
            i += 1

        self.daily = []
        for day in response.daily().data:
            self.daily.append(WeatherBlockDay(day))

class WeatherBlock(object):
    def __init__(self, block):
        try:
            self.time = block.time.strftime('%a, %b %d at %H:%M')
        except AttributeError:
            self.time = 'Unknown'

        if hasattr(block, 'windSpeed'):
            if block.windSpeed == 0:
                self.wind = 'Calm'
            elif block.windSpeed:
                try:
                    self.wind = '{:03}° at {}kts'.format(block.windBearing,round(block.windSpeed*0.87))
                except AttributeError:
                    self.wind = '{}kts'.format(round(block.windSpeed*0.87))

        try:
            self.temperature = '{}°F'.format(round(block.temperature))
        except AttributeError:
            self.temperature = 'Unknown'

        try:
            self.dewPoint = '{}°F'.format(round(block.dewPoint))
        except AttributeError:
            self.dewPoint = 'Unknown'

        try:
            self.cloudBase = '{} ft AGL'.format(int(round((block.temperature - block.dewPoint) * 227.27, -2)))
        except AttributeError:
            self.cloudBase = 'Unknown'

        try:
            self.cloudCover = '{}'.format(cloud_cover(block.cloudCover))
        except AttributeError:
            self.cloudCover = 'Unknown'

        try:
            self.precipProbability = '{}%'.format(int(block.precipProbability * 100))
        except AttributeError:
            self.precipProbability = 'Unknown'

        try:
            # Vis maxes out at ten, this changes that to 10+
            if block.visibility == 10:
                self.visibility = '{}+ miles'.format(block.visibility)
            else:
                self.visibility = '{} miles'.format(block.visibility)
        except AttributeError:
            self.visibility = 'Unknown'

class WeatherBlockCurrent(WeatherBlock) :
    def __init__(self, block):
        super().__init__(block)

        try:
            self.time = block.time.strftime('%a, %b %d at %H:%M')
        except AttributeError:
            self.time = 'Unknown'

class WeatherBlockHour(WeatherBlock) :
    def __init__(self, block):
        super().__init__(block)

        try:
            self.time = block.time.strftime('%a, %b %d at %H:%M')
        except AttributeError:
            self.time = 'Unknown'

class WeatherBlockDay(WeatherBlock) :
    def __init__(self, block):
        super().__init__(block)

        try:
            self.time = block.time.strftime('%a, %b %d')
        except AttributeError:
            self.time = 'Unknown'

        try:
            self.temperatureMin = '{}°F'.format(round(block.temperatureMin))
        except AttributeError:
            self.temperatureMin = 'Unknown'

        try:
            self.temperatureMax = '{}°F'.format(round(block.temperatureMax))
        except AttributeError:
            self.temperatureMax = 'Unknown'

        try:
            self.sunriseTime = block.sunriseTime.strftime('%H:%M')
        except AttributeError:
            self.sunriseTime = 'Unknown'

        try:
            self.sunsetTime = block.sunsetTime.strftime('%H:%M')
        except AttributeError:
            self.sunsetTime = 'Unknown'

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

    with open('files/APT.txt', 'r', encoding="latin1") as airports_file :
        for line in airports_file :
            if line[0:3] == 'APT' :
                airports.append(Airport(line))
    return airports

def airports_saver() :
    airports = airports_txt_parser()
    with open('files/airports.pickle', 'wb') as f :
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
        return 'North'
    if 22.5 < deg <= 67.5 :
        return 'Northeast'
    if 67.5 < deg <= 112.5 :
        return 'East'
    if 112.5 < deg <= 157.5 :
        return 'Southeast'
    if 157.5 < deg <= 202.5 :
        return 'South'
    if 202.5 < deg <= 247.5 :
        return 'Southwest'
    if 247.5 < deg <= 292.5 :
        return 'West'
    if 292.5 < deg <= 337.5 :
        return 'Northwest'

def nearby_airports_finder(location, radius) :
    #TODO add logic to update the airports pickle file
    #airports_saver()
    with open('files/airports.pickle', 'rb') as f :
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
        try:
            self.city = root.find('.//txtNameCity').text
        except AttributeError:
            self.city = 'Unknown'
        try:
            self.state = root.find('.//txtNameUSState').text
        except AttributeError:
            self.city = 'Unknown'
        self.text = root.find('.//txtDescrTraditional').text
        self.issued_time = notam_time_converter(root.find('.//dateIssued').text)
        try:
            self.effective = notam_time_converter(root.find('.//dateEffective').text)
            self.expire = notam_time_converter(root.find('.//dateExpire').text)
        except AttributeError :
            self.effective = 'Unknown'
            self.expire = 'Unknown'

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
        self.effective = notam_time_converter(tfr_area_group.find('.//dateEffective').text)
        self.expire = notam_time_converter(tfr_area_group.find('.//dateEffective').text)
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
    # so lazy. just uncomment to clear the tfr cache.
    #tfrs = {}
    # Tfrs without location data get ignored and saved to this list.
    with open('files/tfr_ignore_list.pickle', 'rb') as f :
        tfr_ignore_list = pickle.load(f)

    for tfr_id in tfr_list :
        if tfr_id not in tfrs :
            url = 'http://tfr.faa.gov/save_pages/detail_' + tfr_id + '.xml'
            r = requests.get('http://tfr.faa.gov/save_pages/detail_' + tfr_id + '.xml')
            r.encoding = 'UTF-8'
            xml = r.text
            #<Avx is the location data. Without this, they're impossible to auto map.
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


def notam_time_converter(time_string) :
    date_time = datetime.datetime.strptime(time_string, "%Y-%m-%dT%H:%M:%S")
    date_string = date_time.strftime('%B %d, %Y at %H:%M UTC')
    return date_string

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

if __name__=="__main__":
    main()

os.chdir(os.path.dirname(__file__))
