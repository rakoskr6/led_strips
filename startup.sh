# Add the following to crontab -e: @reboot /home/pi/led_strips/startup.sh
SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin 

sleep 5

jack_control start
alsactl --file /usr/share/doc/audioInjector/asound.state.RCA.thru.test restore

#@reboot ./home/pi/led_strips/start_from_server.sh
sh /home/pi/led_strips/start_from_server.sh
