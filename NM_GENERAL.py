# -*- coding: utf-8 -*-

##########################################################################
# -----------------------   LIBRARIES IMPORT    ------------------------ #
##########################################################################
import time
import os
import math
import numpy

from RF24 import *
from txrx_utils import *

###############################################################################
# ------------------------   INITIALISATION BLOCK    ------------------------ #
###############################################################################

# ----------- Radio set-up ----------- #
RADIO = RF24(22, 0)  # 22: CE GPIO, 0: CSN GPIO, (SPI speed: 10 MHz)

# ----------- NETWORK MODE ----------- #
NODE_ID = 1  # 1 and 5 --------------------------------------- to change
# NODE_ID = 5  # 1 and 5 --------------------------------------- to change
DATA_SIZE = 30  # Real payload data size
HEADERS_SIZE = 2  # Headers size
ADDRESS = 0xC2_C2_C2_C2_C2
TIME_SLOT_SIZE = 1.75
NUMBER_OF_NODES = 8
MINIMUM_TIME_TRANSMISSION = 50  # ms taken to transmit each packet (minimum period)
NAME_OF_INPUT_FILE = "MTP-F20-NM-TX.txt"
NAME_OF_OUTPUT_FILE = "MTP-F20-NM-RX.txt"


####################################################################
# ------------------------   FUNCTIONS    ------------------------ #
####################################################################

# ------ NRF24 INITIALISATION FUNCTION ------ #
def nm_initialisation_nrf24():
    """PRIVATE
    INITIALISATION nrf24 parameters. For your library!"""
    RADIO.begin()

    RADIO.setPALevel(RF24_PA_LOW)  # RF24_PA_MIN, RF24_PA_LOW, RF24_PA_HIGH and RF24_PA_MAX
    RADIO.setDataRate(RF24_250KBPS)  # RF24_250KBPS for 250kbs, RF24_1MBPS for 1Mbps, or RF24_2MBPS for 2Mbps
    RADIO.setRetries(0, 0)  # 1 -> delay from 0 up to 15 [(delay+1)*250 µs] (1-> 500µs),
    #                         15 -> retries number from 0 (no retries) up to 15
    RADIO.setAutoAck(False)  # Enable auto-acknowledgement
    RADIO.enableDynamicPayloads()  # Enable dynamic-sized payloads
    RADIO.setChannel(1)  # RF channel to communicate on: 0-125
    RADIO.setCRCLength(RF24_CRC_16)  # RF24_CRC_8 for 8-bit or RF24_CRC_16 for 16-bit

    RADIO.setAddressWidth(5)
    RADIO.openWritingPipe(ADDRESS)
    RADIO.openReadingPipe(1, ADDRESS)


####################################################################################
# ------------------------ DIRECTORIES AND PATH DISCOVERY ------------------------ #
####################################################################################

# ------ READ FROM USB FUNCTION ------ #
def nm_read_from_usb():
    """PRIVATE
    Reads a file from the path passed as parameter."""
    for file in os.listdir(USB_FOLDER):
        if os.path.splitext(file)[1] == ".txt":
            with open(os.path.join(USB_FOLDER, file), "rb") as f:
                contents = f.read()
            break
    return contents  # returns the contents read from the path


def nm_read_from_folder():
    for file in os.listdir():
        if os.path.splitext(file)[1] == ".txt" and not file.startswith("Local_out_"):
            with open(file, "rb") as f:
                contents = f.read()
            break
    return contents  # returns the contents read from the path


# ------ WRITE FUNCTION ------ #
def nm_write(file_name, contents):
    """PRIVATE
    Creates or/and writes to a file passed as parameter"""
    with open(file_name, "wb") as f:
        f.write(contents)


def nm_copy_to_usb(result_file, file_on_usb):
    """PRIVATE
    Copy the result file to the USB"""
    cmd = "sudo cp " + result_file + " " + os.path.join(USB_FOLDER, file_on_usb)
    subprocess.call(cmd, shell=True)


# ------ END COMMS RX, TX ------ #
def nm_end_comms():  # Ends the communication once the Tx-Rx is performed
    """ PRIVATE
    Function to stop code"""
    RADIO.stopListening()
    exit(0)  # Closes the programme to reduce unuseful consumption


################################################################################
# ------------------------   NETWORK_MODE FUNCTIONS   ------------------------ #
################################################################################

################################
# ------  TRANSMISSION  ------ #
################################
def nm_transmit(buffer):
    """PRIVATE
    This function transmits a bytearray of 32 bytes and transmits it through the NRF,
    buffer is a bytearray of 32 bytes"""
    RADIO.write(buffer)


#############################
# ------  RECEPTION  ------ #
#############################
def nm_receive():
    """ PRIVATE
    This function receives a bytearray of 32 bytes returns it."""
    received_payload = RADIO.read(32)
    return received_payload


###################################
# ------  SYNCHRONIZATION  ------ #
###################################
def nm_synchronize(node_id_received, synchronized):
    """ PUBLIC!
    This function establishes time synchronization.
    Computes the remaining time until the time slot to transmit starts (according to its NODE_ID)"""
    if not synchronized:
        print("STATE : synchronized")
    synchronized = True
    syncro_time = time.monotonic() * 1000  # Time of synchronization
    if (NODE_ID - node_id_received) > 0:
        time_slot = syncro_time + (NODE_ID - node_id_received) * TIME_SLOT_SIZE * 1000
    else:
        time_slot = syncro_time + (NUMBER_OF_NODES + NODE_ID - node_id_received) * TIME_SLOT_SIZE * 1000
    return time_slot, synchronized


###############################
# ------  NM FUNCTION  ------ #
###############################
def nm_network_mode():
    """ PUBLIC WITH REQUIRED MODIFICATIONS!
    This function must be introduced in the main. It is the main function for the network mode operation """
    print("Mode NM")
    print("STATE: SILENCED")

    number_packets_total = 35  # Number of packets in case the file is bigger than expected
    file_received = bytearray(number_packets_total * DATA_SIZE)  # Where we put the data received
    file_to_transmit = bytearray(number_packets_total * (DATA_SIZE + HEADERS_SIZE))  # Where we put the data to transmit (with flags)
    time_slot = 0  # Time to start to transmit
    synchronized = False  # Boolean to indicate if I am synchronized

    # ------  FLAGS INITIALIZATION  ------ #
    started = False
    all_received = False

    # Vector of 1s and 0s to indicate if the packet has been received
    buffered_packets = numpy.zeros((number_packets_total, 1))

    while True:
        RADIO.startListening()

        # ------------------  ALL PACKETS RECEIVED  ------------------ #
        aux = numpy.ones((number_packets_total, 1))
        if (buffered_packets == aux).all() and (not all_received):
            all_received = True

        # ------------------  RECEPTION PART  ------------------ #
        if RADIO.available():  # TEAMS
            buffer = nm_receive()
            # ------  HEADERS PROCESSING  ------ #
            control_byte_integer_1 = int.from_bytes(buffer[0:1], "big")  # Pass to int value the control byte
            node_id_received = (control_byte_integer_1 & 0xE0) >> 5  # Masked by 11100000
            packet_id_received = control_byte_integer_1 & 0x1F  # Masked by 00011111)
            control_byte_integer_2 = int.from_bytes(buffer[1:2], "big")
            last_packet_received = (control_byte_integer_2 & 0x80) >> 7  # Masked by 10000000
            payload_size_received = (control_byte_integer_2 & 0x7C) >> 2  # Masked by 01111100

            print(f"Received message from {node_id_received}: {packet_id_received}")

            # ------  SYNCHRONIZATION  ------ #
            if packet_id_received == 0:  # If first packet, synchronize()
                print(f"Received sync message from {node_id_received}")
                time_slot, synchronized = nm_synchronize(node_id_received, synchronized)
                # now_to_print = time.monotonic()
                # print("Packet 0 received. Time: " + str(now_to_print))

            # ------  DATA RECEPTION  ------ #
            if buffered_packets[packet_id_received] == 0:
                started = True

                # To indicate in further iterations that we have already received the packet
                buffered_packets[packet_id_received] = 1

                # ------  DATA PREPARATION  ------ #
                # TO BE PRINTED IN TXT FILE
                file_received[packet_id_received * DATA_SIZE:packet_id_received * DATA_SIZE + payload_size_received] = buffer[2:payload_size_received + 2]

                # TO BE TRANSMITTED INTO THE NEXT TIME_SLOTS OF THIS NODE_ID
                control_byte_integer_1 = (NODE_ID << 5) + packet_id_received
                empty_data = b'~' * (DATA_SIZE - payload_size_received)  # Add redundant data to get 32 byte payload
                buffer = bytes([control_byte_integer_1]) + bytes([control_byte_integer_2]) + buffer[2:payload_size_received + 2] + empty_data
                file_to_transmit[packet_id_received*(DATA_SIZE + HEADERS_SIZE): (packet_id_received + 1) * (DATA_SIZE + HEADERS_SIZE)] = buffer

                # ------  NETWORK CONFIGURATION UPDATE  ------ #
                if last_packet_received:
                    number_packets_total = packet_id_received + 1

                    # buffered_packets_aux = numpy.zeros((number_packets_total, 1))
                    buffered_packets_aux = buffered_packets[0:number_packets_total]
                    buffered_packets = buffered_packets_aux

                    # file_received_aux = bytearray((number_packets_total-1) * DATA_SIZE + payload_size_received)
                    file_received_aux = file_received[0:(number_packets_total - 1) * DATA_SIZE + payload_size_received]
                    file_received = file_received_aux

        # ------------------  FIRST TRANSMITTER  ------------------ #
        # At this point, the first transmitter switches from SILENCED to SYNCHRONIZED
        # and transmits in his time_slot (FIRST TRANSMITTER)
        if I_FACE.sw.en_transmission.is_on() and not started:  # TODO: TO VERIFY

            # ------  READ DATA FROM USB  ------ #
            if check_mounted_usb():
                file_received = nm_read_from_usb()  # All info saved in file_received
                # file_received = nm_read_from_folder()  # All info saved in file_received

                number_packets_total = math.ceil(len(file_received) / DATA_SIZE)

                buffered_packets = numpy.ones((number_packets_total, 1))

                # ------  TRANSMISSION FILE PREPARATION  ------ #
                # Brief explanation:
                # Prepares the data for future transmissions.
                # The last packet is fulled with empty bytes until the 32 bytes are full
                packet_id_received = 0
                while packet_id_received < number_packets_total:
                    control_byte_integer_1 = (NODE_ID << 5) + packet_id_received
                    if packet_id_received == number_packets_total - 1:
                        last_packet_received = 1
                        payload_size_received = len(file_received) - packet_id_received * DATA_SIZE
                    else:
                        last_packet_received = 0
                        payload_size_received = DATA_SIZE

                    control_byte_integer_2 = (last_packet_received << 7) + (payload_size_received << 2)
                    empty_data = b'~' * (DATA_SIZE - payload_size_received)  # Add redundant data to get 32 byte payload
                    buffer = bytes([control_byte_integer_1]) + bytes([control_byte_integer_2]) + file_received[packet_id_received * DATA_SIZE:packet_id_received * DATA_SIZE + payload_size_received] + empty_data
                    file_to_transmit[packet_id_received * (DATA_SIZE + HEADERS_SIZE):(packet_id_received + 1) * (DATA_SIZE + HEADERS_SIZE)] = buffer
                    packet_id_received = packet_id_received + 1

                started = True  # The communication has started!
                print("STATE: synchronized")
                synchronized = True  # This node is synchronized (first node)
                current_time = time.monotonic() * 1000  # Current time
                time_slot = current_time

        # ------------------  TRANSMISSION PART  ------------------ #
        # Here the node transmits only if the current time corresponds to its time slot
        current_time = time.monotonic() * 1000  # Current time
        if ((current_time - time_slot) > 0) and ((current_time - time_slot) < 750) and synchronized:
            RADIO.stopListening()
            # Update of the new time to transmit for the next slot
            time_slot, synchronized = nm_synchronize(NODE_ID, synchronized)
            # print("Transmitting in Network Mode")
            # print("Current time: "+str(current_time/1000))
            # print("Next time slot: "+str(time_slot))
            size = len(buffered_packets)
            i = 0
            if all([buffered_packets[i] == 1 for i in range(size)]):
                print("We have all messages")
            while i < size:
                if buffered_packets[i] == 1:
                    now = time.monotonic() * 1000  # Current time
                    buffer_to_tx = file_to_transmit[i * (DATA_SIZE + HEADERS_SIZE): (i + 1) * (DATA_SIZE + HEADERS_SIZE)]  # 32 bytes to transmit
                    print("Sending message", i)
                    nm_transmit(buffer_to_tx)
                    wait_time = MINIMUM_TIME_TRANSMISSION - (time.monotonic() * 1000 - now)
                    if wait_time > 0:
                        time.sleep(wait_time / 1000)
                i = i + 1
            RADIO.startListening()

        # ------------------  END COMMUNICATIONS  ------------------ #
        # The output file is generated using the variable file_received, which contains all the received data
        if I_FACE.sw.en_transmission.is_off() and started:  # TODO: TO VERIFY
            print("End Comms")
            nm_write("Local_" + NAME_OF_OUTPUT_FILE, file_received)

            if check_mounted_usb():
                nm_copy_to_usb("Local_" + NAME_OF_OUTPUT_FILE, NAME_OF_OUTPUT_FILE)

            nm_end_comms()


if __name__ == "__main__":
    nm_initialisation_nrf24()
    nm_network_mode()
