# -*- coding: utf-8 -*-
"""
Created on Tue Oct 25 14:59:23 2022

@author: ameimand
"""

import requests
URL = 'https://raw.githubusercontent.com/arunponnusamy/object-detection-opencv/master/yolov3.txt'
response = requests.get(URL)
open('yolov3.txt', 'wb').write(response.content)

URL = 'https://pjreddie.com/media/files/yolov3.weights'
response = requests.get(URL)
open('yolov3.weights', 'wb').write(response.content)

URL = 'https://raw.githubusercontent.com/pjreddie/darknet/master/cfg/yolov3.cfg'
response = requests.get(URL)
open('yolov3.cfg', 'wb').write(response.content)