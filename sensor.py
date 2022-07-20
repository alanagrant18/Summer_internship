#sensor

#!/usr/bin/python
import os
import sys
import time
from random import randint
from datetime import date, datetime
import spidev
from sound_log import Logger
import pygame
from time import sleep
import ordergenerator

pygame.mixer.init()
current_time = datetime.now()
sys.excepthook = sys.__excepthook__

##################

dict = ordergenerator.getDictionary()

mediafile = 'none'

# TODO: combine with the pingtimer..
mediaUpdateTimer = datetime.now()

#Used to choose 1 of 3 audio samples at random
def rand():
    value = randint(1,3)
    
    if value == 1:
        return 1
    if value == 2:
        return 2
    if value == 3:
        return 3


# Spidev used to connect to and read the sensors
spi = spidev.SpiDev()
spi.open(0,0)
spi.max_speed_hz=1000000
 
def read_channel(channel):
  val = spi.xfer2([1,(8+channel)<<4,0])
  data = ((val[1]&3) << 8) + val[2]
  return data

def get_volts(channel=0):
    v=(read_channel(channel)/1023.0)*3.3
    print("Channel ", channel, " : %.2f V" % v)
    dist = 16.2537 * v**4 - 129.893 * v**3 + 382.268 * v**2 - 512.611 * v + 301.439
    print("Distance: %.2f cm" % dist)
    return v

def is_in_range(v, i):
    # Threshold for every sensor: probably depends on the location 
    # and have to be tested and adjusted - CURRENTLY SET TO GO OFF 2M-3M
    # 0cm = 1.4v
    # 30-50cm = 3.1v
    # 1.5m = 2.8v
    # 2m = 2.1v
    # 3m = 1.7v
    if i == 0 and v > 1.7 and v < 2.1:
        return True
    #elif i == 0 and v > 0.00:
    #    return True
    else:
       return False
 

# Update local log file
def update_log(logger, start=False, end=False, sensors_active=[]):
    now = datetime.now()
    timestr = now.strftime("%Y-%m-%d %H:%M:%S")
    data = [timestr, start, end] + sensors_active + mediafile
    logger.log_local(data)


def update_mediafile(logger):
  print('Main','Checking date for switchin media')
  # today must be in '2022-01-01' format: datetime.date.fromisoformat(today)
  today = date.today().isoformat()

  datesDict = ordergenerator.getDictionary()

  if today in datesDict:
    media = datesDict[today]

  if mediafile != media:
    logger.log_system_status('Main', 'Media change: from {} to {}.'.format(globals.mediafile, media))
    print('Main','Media change: from {} to {}.'.format(globals.mediafile, media))
    mediafile = media

  
if __name__ == "__main__":
    print(os.getpid())
    status_in_range = False
    playing = False
    paused = False
    is_playing = False
    channel_indices = [0]
    logger = Logger()
    prev_alive_time = datetime.now()
    logger.log_alive()
    filename = "libcamera-jpeg -o 1.jpg -t 1"
    count = 1

    while True:
        
        now = datetime.now()
        diff = (now - prev_alive_time).total_seconds() / 60.0
        # ping alive every hour
        if diff > 60:
            print('Log alive!', diff)
            logger.log_alive()
            prev_alive_time = now

        if (datetime.now() - mediaUpdateTimer).total_seconds() / 60 > 20: 
              # check every 20 minutes
              update_mediafile(logger)
              mediaUpdateTimer = datetime.now()           


        # online logging intitated separate from sensor readings, so that if the quota is passed and data accumulated 
        # only locally, the waiting records will be logged as soon as possible whether there is activity going on
        # or not
        logger.log_drive(now)
        sensors_in_range = [is_in_range(get_volts(i), i) for i in channel_indices]
        new_in_range = any(sensors_in_range)


        # Require two consecutive sensor readings before
        # triggering play to prevent random activations
        if new_in_range and status_in_range:
            
            print("IN RANGE")
            
            #Take photo
            os.system(filename)
            print(filename)
            
            count += 1
            filename = list(filename)
            filename[18] = str(count)
            filename = "".join(filename)
            
            if mediafile == 'hum':
                # record start of sound play for logging
                start = True

                
                random_val = rand()
            
                if random_val == 1:
                    pygame.mixer.music.load("/home/pi/internship/humming/hum1.mp3")
                    pygame.mixer.music.play()
                    update_log(logger, start=start, sensors_active=sensors_in_range)
                    time.sleep(10)
                
                if random_val == 2:
                    pygame.mixer.music.load("/home/pi/internship/humming/hum2.mp3")
                    pygame.mixer.music.play()
                    update_log(logger, start=start, sensors_active=sensors_in_range)
                    time.sleep(10)
                
                if random_val == 3:
                    pygame.mixer.music.load("/home/pi/internship/humming/hum3.mp3")
                    pygame.mixer.music.play()
                    update_log(logger, start=start, sensors_active=sensors_in_range)
                    time.sleep(10)
                    
                playing = True

            
            if mediafile == 'white':
                pygame.mixer.music.load("/home/pi/internship/humming/whitenoise.mp3")
                pygame.mixer.music.play()
                update_log(logger, start=start, sensors_active=sensors_in_range)
                time.sleep(10)


            if mediafile == 'none':
                update_log(logger, start=start, sensors_active=sensors_in_range)
                time.sleep(10)
    
            
            
        if pygame.mixer.get_busy() == True and not new_in_range:
            pygame.mixer.music.pause()
            paused = True
            playing = False
            update_log(logger, end=True, sensors_active=sensors_in_range)
        status_in_range = new_in_range
        time.sleep(0.5)

