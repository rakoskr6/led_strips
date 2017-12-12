from flask import Flask
from led_ping import ping_red
app = Flask(__name__)

#ping_red()
@app.route('/')
def hello_world():
	#execfile("led_ping.py")
	os.system("python led_ping.py")
	return "success"


