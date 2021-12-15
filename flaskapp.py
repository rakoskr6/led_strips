#!/usr/bin/env python

from flask import Flask
from ping import ping_red
app = Flask(__name__)

#ping_red()
@app.route('/')
def hello_world():
	#execfile("led_ping.py")
	os.system("python ping.py")
	return "success"


