from flask import Flask, render_template
from dronewx import *
app = Flask(__name__)

@app.route('/')
def index():
    return 'Index'

@app.route('/briefing', methods=['GET','POST'])
def briefing():
    location = (39.1,-121.436389)
    radius = 10
    nearby_airports = nearby_airports_finder(location, radius)
    return render_template('briefing.html',airports=nearby_airports)

if __name__=='__main__':
    app.run(debug=True)
