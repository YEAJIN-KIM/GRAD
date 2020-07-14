# -*- coding: utf-8 -*-
#for tts
from __future__ import print_function
import time
import paho.mqtt.client as paho
import board
import neopixel
import threading
import json
import RPi.GPIO as GPIO
import serial
from pyowm import OWM
import geocoder
import requests

#for tts
import grpc
import gigagenieRPC_pb2
import gigagenieRPC_pb2_grpc
import MicrophoneStream as MS
import user_auth as UA
import os
from ctypes import *
HOST = 'gate.gigagenie.ai'
PORT = 4080
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)

def py_error_handler(filename, line, function, err, fmt):
  dummy_var = 0
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
asound = cdll.LoadLibrary('libasound.so')
asound.snd_lib_error_set_handler(c_error_handler)

# TTS : getText2VoiceStream
def getText2VoiceStream(inText,inFileName):
	channel = grpc.secure_channel('{}:{}'.format(HOST, PORT), UA.getCredentials())
	stub = gigagenieRPC_pb2_grpc.GigagenieStub(channel)
	message = gigagenieRPC_pb2.reqText()
	message.lang=0
	message.mode=0
	message.text=inText
	writeFile=open(inFileName,'wb')
	for response in stub.getText2VoiceStream(message):
		if response.HasField("resOptions"):
			print ("\n\nResVoiceResult: %d" %(response.resOptions.resultCd))
		if response.HasField("audioContent"):
			print ("Audio Stream\n\n")
			writeFile.write(response.audioContent)
	writeFile.close()
	return response.resOptions.resultCd


#�Ƶ��̳�� ��� ��Ʈ Ȯ��
port = "/dev/ttyUSB0"
serialFromArduino = serial.Serial(port, 9600)
serialFromArduino.flushInput()

#mqtt ���Ŀ �� ��������
broker="101.101.164.197"
pubTopic = "moodlight/onTopic/"
subTopic = "moodlight/inTopic/"

#�ش� ����̽��� ���̵�!!
deviceId = "123"

#���� ��û ����
weatherState = False

#�׿��ȼ� �� �� �ʱ�ȭ
pixel_pin = board.D12
pixels = neopixel.NeoPixel(pixel_pin, 12, brightness=0.2, auto_write=False, pixel_order=neopixel.GRB)

# mqtt �޼��� ���Ž� ����Ǵ� �ݹ��Լ�
def on_message(client, userdata, message):
    time.sleep(1)
    print("received message =",str(message.payload.decode("utf-8")))
    str_m = str(message.payload.decode("utf-8"))
    if len(str_m) < 2:
        actWeatherData()
        return
    dict = json.loads(str(message.payload.decode("utf-8")))
    actNeoPixel(dict['r'],dict['g'],dict['b'])

# �׿��ȼ� rgb led����
def actNeoPixel(r, g, b):
    print("act pixel")
    pixels.fill((r, g, b))
    pixels.show()

# �Ƶ��̳뿡�� ���� ���� �����͸� ������ ����
def publishSensorData(input):
    client.publish(pubTopic + deviceId, input)
    if "{" in str(input):
        dict = json.loads(str(input))
        sendDustAlarm(dict['dust'])

# �̼����� ��ġ�� ���� ���� �̻��� ��� ������ Ǫ�þ˶� ��û
def sendDustAlarm(dust):
    print("json dust : ")
    print(dust)
    if dust >= 0.5: #�̼����� ��� ���� 100
        url = "http://101.101.164.197/insert_dust_data.php"
        url += "?deviceId="
        url += deviceId
        url += "&dust="
        url += str(dust)
        r = requests.get(url)


# ���� ��Ÿ���� ��ȣ ���� �� �۵�
def actWeatherData():
    print("actWeather")
    output_file = "test.wav"
    getText2VoiceStream(getWeatherData(), output_file)
    MS.play_file(output_file)
    print( output_file + "�� �����Ǿ����� ������ Ȯ�ιٶ��ϴ�. \n\n\n")

# �� ��ġ�� �������� �޾Ƴ���
def getWeatherData():
    #��Ʈ��ũ �� �� ��ġ ����
    geo = geocoder.ip('me')
    latlng = geo.latlng
    state = geo.state
    print(state)
    # open weather map apiȰ�� -> �д� 60ȸ �� ����
    owm = OWM('4cef2e1e7c19f03b36ed971bac0be5fc')
    obs = owm.weather_at_coords(latlng[0], latlng[1])
    location = obs.get_location()
    print(location.get_name())
    w = obs.get_weather()
    print(w.get_status())
    result = "���� ������ " + getWeatherStatus(str(w.get_status())) + "�Դϴ�."
    result += ("�����" + str(w.get_temperature(unit='celsius')['temp']) + ", ")
    result += "������" + str(w.get_humidity()) + "�̸� "
    result += "ǳ����" + str(w.get_wind()['speed']) + "�Դϴ�."
    neopixelTemp(w.get_temperature(unit='celsius')['temp'])
    print(result)
    return result

def getWeatherStatus(status):
    if status in "Thunderstorm":
        return "õ��"
    elif status in "Drizzle":
        return "�̽���"
    elif status in "Rain":
        return "��"
    elif status in "Snow":
        return "��"
    elif status in "Mist":
        return "�Ȱ�"
    elif status in "Smoke":
        return "����"
    elif status in "Haze":
        return "����"
    elif status in "Dust":
        return "�̼�����"
    elif status in "Fog":
        return "�Ȱ�"
    elif status in "Sand":
        return "Ȳ��"
    elif status in "Ash":
        return "��"
    elif status in "Squall":
        return "��ǳ"
    elif status in "Cloud":
        return "�帲"
    else:
        return "����"

def neopixelTemp(temp):
    if temp >= 20:
        actNeoPixel(255,0,0)
    else:
        actNeoPixel(0,255,0);

# mqtt ���� �� ����
client= paho.Client("client-001")
client.on_message=on_message
print("connecting to broker ",broker)
client.connect(broker)
client.loop_start()
print("subscribing ")
client.subscribe(subTopic + deviceId)
time.sleep(2)
print("publishing start")

while(True):
    # �Ƶ��̳�� ���� ���������� ���� ��
    if(serialFromArduino.inWaiting() > 0):
        input = serialFromArduino.readline().decode("utf-8")
        print(input)
        publishSensorData(input)

#client.disconnect() #disconnect
#client.loop_stop() #stop loop