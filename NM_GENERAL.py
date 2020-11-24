###############################################################################
#########################   LIBRARIES IMPORT    ###############################
###############################################################################
import time
import board
import os
import digitalio as dio
from gpiozero import LED,Button
import struct
import zlib
import math
import numpy
import logging
from circuitpython_nrf24l01.rf24 import RF24
from glob import glob # To search
from subprocess import check_output, CalledProcessError
import RPi.GPIO as GPIO
from RF24 import *



###############################################################################
#########################   INIZIALIZATION BLOCK    ###########################
###############################################################################

# ----------- Radio set-up ----------- #
RADIO = RF24(22, 0)  # 22: CE GPIO, 0: CSN GPIO, (SPI speed: 10 MHz)


######## NETWORK MODE #######
node_id = 2 # 2 and 3
data_size = 30 # Real payload data size
data_headers = 2 # Real payload data size
address = 0xC2C2C2
TIME_SLOT_SIZE = 1.75
time_slot = 0 #Time to start to transmit
synchronized = False #Boolean to indicate if I am synchronized
started = False
number_of_nodes = 8
MINIMUM_TIME_TRANSMISSION = 50 # ms taken to transmit each packet (minimum period)

###############################################################################
#################################   FUNCTIONS    ##############################
###############################################################################

################## NRF24 INIZIALIZATION FUNCTION ##############
"""PRIVATE
INIZIALIZATION nrf24 parameters. For your library!"""
def inizialization_nrf24(): #---------------------------------------------------------------------- TO BE DEFINED
    RADIO.begin()

    RADIO.setPALevel(RF24_PA_HIGH)  # RF24_PA_MIN, RF24_PA_LOW, RF24_PA_HIGH and RF24_PA_MAX
    RADIO.setDataRate(RF24_250KBPS)  # RF24_250KBPS for 250kbs, RF24_1MBPS for 1Mbps, or RF24_2MBPS for 2Mbps
    RADIO.setRetries(1, 0)  # 1 -> delay from 0 up to 15 [(delay+1)*250 µs] (1-> 500µs),
    #                         15 -> retries number from 0 (no retries) up to 15
    RADIO.setAutoAck(False)  # Enable auto-acknowledgement
    RADIO.disableDynamicPayloads()  # Enable dynamic-sized payloads
    RADIO.setChannel(1)  # RF channel to communicate on: 0-125
    RADIO.setCRCLength(RF24_CRC_16)  # RF24_CRC_8 for 8-bit or RF24_CRC_16 for 16-bit





#######################################################
############ DIRECTORIES AND PATH DISCOVERY ###########
#######################################################

################## DIRECTORI FUNCTION ##############
"""PRIVATE
Returns the path of a specific directory to use llegir() and escriure() afterwards."""
def directori(mode, S_path):
    return(path) # returns the path

################## LLEGIR FUNCTION ##############
"""PRIVATE
Reads a file from the path passed as parameter."""
def llegir(mode, path, S_file):
    return(contents) # returns the contents read from the path

################## ESCRIURE FUNCTION ##############
"""PRIVATE
Creates or/and writes to a file passed as parameter on the path, also passed as parameter"""
def escriure(path, S_file, contents):
    with open(S_file, "wb") as f:
        f.write(contents)

#######################################################
##################### USB FUNTCIONS ###################
#######################################################

""" PRIVATE
Returns path of the USB directory"""
def get_mount_points(devices=None): #Detects the mounted USB devices

########### END COMMS RX, TX #########
""" PRIVATE
Function to stop code"""
def end_comms(): #Ends the communication once the Tx-Rx is performed
    RADIO.stopListening()
    exit() #Closes the programme to reduce unuseful consumption



###############################################################################
#######################   NETWORK_MODE FUNCTION   #############################
###############################################################################

#######################################################
##################### TRANSMITTION ###################
#######################################################
"""PRIVATE
This function transmits a bytearray of 32 bytes and transmits it through the NRF, buffer is a bytearray of 32 bytes"""
def transmit(buffer): #----------------------------------------------------------------------FUNCTION TO BE DEFINED
    RADIO.write(buffer)

#######################################################
##################### RECEPTION ######################
#######################################################
""" PRIVATE
This function receives a bytearray of 32 bytes returns it."""
def receive():
    received_payload = RADIO.read(32)
    return received_payload


#######################################################
##################### SYNCHRONIZATION #################
#######################################################

""" PUBLIC!
This function stablishes time synchronization. Computes the remaining time until the time slot to transmit starts (according to its node_id)"""
def synchronize(node_id_received, synchronized):
    if  not synchronized:
        print("STATE : synchronized")
    synchronized = True
    syncro_time = time.monotonic()*1000 #Time of synchronization
    time_slot = 0
    if (node_id - node_id_received) > 0:
        time_slot = syncro_time + (node_id - node_id_received)*TIME_SLOT_SIZE*1000
    else:
        time_slot = syncro_time + (number_of_nodes + node_id - node_id_received)*TIME_SLOT_SIZE*1000
    return time_slot, synchronized

#######################################################
##################### NM FUNCTION#### #################
#######################################################
""" PUBLIC WITH REQUIRED MODIFICATIONS!
This function must be introduced in the main. It is the main function for the network mode operation """
def network_mode():
    print("Mode NM")
    print("STATE: SILENCED")
    RADIO.setAddressWidth(3)
    RADIO.openWritingPipe(address)
    RADIO.openReadingPipe(1, address)
    number_packets_total = 35 #Number of packets in case the file is bigger than expected
    file_received = bytearray(number_packets_total*data_size) #Where we put the data received
    file_to_transmit = bytearray(number_packets_total*(data_size+data_headers)) #Where we put the data to transmit (with flags)
    time_slot = 0 #Initiate variable
    synchronized = False

    ########## FLAGS INITIALIZATION ##########
    node_id_received = 0
    packet_id_received = 0
    last_packet_received = 0
    payload_size_received = 0
    started = False
    all_received = False

    buffered_packets = numpy.zeros((number_packets_total, 1)) #Vector of 1s and 0s to indicate if the packet has been received

    while True:
        RADIO.startListening()

        ############# ALL PACKETS RECEIVED ###########
        aux =  numpy.ones((number_packets_total, 1))
        if (buffered_packets == aux).all() and (not all_received):
            all_received = True
            
        ################### RECEPTION PART #############################
        if RADIO.available(): #TEAMS
            buffer = receive()
            ############# HEADERS PROCESSING ###########
            control_byte_integer_1 = int.from_bytes(buffer[0 : 1], "big") #Pass to int value the control byte
            node_id_received = (control_byte_integer_1 & (0xE0))>>5 #Masked by 11100000
            packet_id_received = control_byte_integer_1 & (0x1F) #Masked by 00011111)
            control_byte_integer_2 = int.from_bytes(buffer[1 : 2], "big")
            last_packet_received = (control_byte_integer_2 & (0x80))>>7 #Masked by 10000000
            payload_size_received = (control_byte_integer_2 & (0x7C))>>2 # Masked by 01111100

            ############# SYNCHRONIZATION ###########
            if packet_id_received == 0: # If first packet, synchronize()
                time_slot, synchronized = synchronize(node_id_received, synchronized)
                #now_to_print = time.monotonic()
                #print("Packet 0 received. Time: " + str(now_to_print))

            ############# DATA RECEPTION ###########
            if buffered_packets[packet_id_received] == 0:
                started = True

                buffered_packets[packet_id_received] = 1 # To indicate in further iterations that we have already received the packet

                ############# DATA PREPARATION ###########
                #TO BE PRINTED IN TXT FILE
                file_received[packet_id_received*data_size : packet_id_received*data_size + payload_size_received] = buffer[2:payload_size_received+2]

                #TO BE TRANSMITED INTO THE NEXT TIME_SLOTS OF THIS NODE_ID
                control_byte_integer_1 = (node_id<<5) + packet_id_received
                empty_data = b'~'*(data_size - payload_size_received) #Add redundant data to get 32 byte payload
                buffer = bytes([control_byte_integer_1]) + bytes([control_byte_integer_2]) + buffer[2:payload_size_received + 2] + empty_data
                file_to_transmit[packet_id_received*(data_size + data_headers) : (packet_id_received + 1)*(data_size + data_headers)] = buffer

                ############# NETWORK CONFIGURATION UPDATE ###########
                if last_packet_received:
                    number_packets_total = packet_id_received + 1

                    buffered_packets_aux = numpy.zeros((number_packets_total, 1))
                    buffered_packets_aux = buffered_packets[0 : number_packets_total]
                    buffered_packets = buffered_packets_aux

                    file_received_aux = bytearray((number_packets_total-1)*data_size+payload_size_received)
                    file_received_aux = file_received[0 : (number_packets_total-1)*data_size+payload_size_received]
                    file_received = file_received_aux


        ################### FIRST TRANSMITER #############################
        """ At this point the first transmitter switches from SILENCED to SYNCHRONIZED and transmits in his time_slot (FIRST TRANSMITER) """
        if False: #-----if button_1.is_pressed and not started:------------------------------------------TO BE MODFIFIED

            ############# READ DATA FROM USB ########### #----------------------------------------------------------------------TO BE MODFIFIED
            if len(get_mount_points()) != 0:#----------------------------------------------------------------------TO BE MODFIFIED
                path = directori("pen", 0) #----------------------------------------------------------------------TO BE MODFIFIED
                file_received = llegir("auto", path, 0) #All info saved in file_received  #----------------------------------------------------------------------TO BE MODFIFIED

                number_packets_total = math.ceil(len(file_received)/data_size) #

                buffered_packets = numpy.ones((number_packets_total, 1))

            ############# TRANSMITION FILE PREPARATION ###########
            # Brief explanation: Prepares the data for future transmitions. The last packet is fulled with empty bytes until the 32 bytes are full
                packet_id_received = 0
                while packet_id_received < number_packets_total:
                    control_byte_integer_1 = (node_id<<5) + packet_id_received
                    if (packet_id_received == number_packets_total - 1):
                        last_packet_received = 1
                        payload_size_received = len(file_received) - packet_id_received*data_size
                    else:
                        last_packet_received = 0
                        payload_size_received = data_size

                    control_byte_integer_2 = (last_packet_received<<7) + (payload_size_received<<2)
                    empty_data = b'~'*(data_size - payload_size_received) #Add redundant data to get 32 byte payload
                    buffer = bytes([control_byte_integer_1]) + bytes([control_byte_integer_2]) + file_received[packet_id_received*data_size:packet_id_received*data_size + payload_size_received] + empty_data
                    file_to_transmit[packet_id_received*(data_size + data_headers) : (packet_id_received + 1)*(data_size + data_headers)] = buffer
                    packet_id_received = packet_id_received + 1

                started = True # The communication has started!
                print("STATE: synchronized")
                synchronized = True # This node is synchronized (first node)
                current_time = time.monotonic()*1000 #Current time
                time_slot = current_time


        ################### TRANSMISSION PART #############################
        """ Here the node transmits only if the current time corresponds to its time slot """
        current_time = time.monotonic()*1000 #Current time
        if ((current_time - time_slot) > 0) and ((current_time - time_slot) < 750) & (synchronized):
            RADIO.stopListening()
            time_slot, synchronized = synchronize(node_id, synchronized)  #Update of the new time to transmit for the next slot
            #print("Transmitting in Network Mode")
            #print("Current time: "+str(current_time/1000))
            #print("Next time slot: "+str(time_slot))
            size = len(buffered_packets)
            i = 0
            while i < size:
                if buffered_packets[i] == 1:
                    now = time.monotonic()*1000 #Current time
                    buffer_to_Tx = file_to_transmit[i*(data_size + data_headers) : (i + 1)*(data_size+data_headers)] #32 bytes to transmit
                    transmit(buffer_to_Tx)
                    wait_time = MINIMUM_TIME_TRANSMISSION - (time.monotonic()*1000 - now)
                    if wait_time > 0:
                        time.sleep(wait_time/1000)
                i = i + 1
            RADIO.startListening()


        ################### END COMMUNICATIONS #############################
        """The output file is generated using the variable file_received, which contains all the received data """
        if button_2.is_pressed and started: #----------------------------------------------------------------------TO BE MODIFIED
            print("End Comms")
            path = directori("root", "Outputs")
            escriure(path, "Local_out_TEAM_B.txt", file_received)
            report = "Empty"
            escriure(path, "ReportNM_TEAM_B.txt", bytes(report, 'utf-8'))

            if len(get_mount_points()) != 0: #If bypass=1 --> path is local; if bypass=0 --> path is USB mounted device
                path = directori("pen", "Outputs")
                escriure(path, "out_TEAM_B.txt", file_received)
                escriure(path, "ReportNM.txt", bytes(report, 'utf-8'))

            end_comms()



###############################################################################
####################################   MAIN    ################################
###############################################################################

"""While true of all your main functions. Here we only considered the case of the NM, but you might also have SRI and buttons functions/states."""
"""This is an EXAMPLE to execute NM code."""
while True:
    state = "NM"
############# NETWORK Mode PROCESS  ###########
    if state == "NM":
        inizialization_nrf24()
        network_mode()
    else:
        print("Error")
