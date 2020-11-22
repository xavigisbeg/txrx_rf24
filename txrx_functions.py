import time
import os
from RF24 import *
import RPi.GPIO as GPIO
import math
import zlib


STATE_FINAL = 0
STATE_INIT  = 1
STATE_COMPRESS_NM = 2


def readGPIOS():
    switch()
    return switches


def run_st_init():
    readGPIOs()
    state = "next_state"
    return state


def run_st_Rx_Listen():
    package = listen()
    state = "next_state"
    return state, package