# -*- coding: utf-8 -*-

from txrx_utils import *
from txrx_functions import *
import time


# ------------ Main Function ------------ #

def main():
    print("Test on Receiver")
    # Initialization of variables
    state = STATE_RX_TRANSMISSION_INIT

    tx_list_of_frames = [bytearray(b"")]
    tx_frame_num = 0

    rx_previous_cnt = -1
    rx_list_received_payload = list()

    init_time = time.time()

    put_error = 0
    get_time = False
    init_wait_time = time.time()

    while True:
        # At any time we should return to the init state if the start switch is turned off
        if state != STATE_INIT:
            state = run_st_read_start_switch(state)

        # Common states
        if state == STATE_FINAL:
            pass  # In the final state, we are stuck (unless the start switch if turned OFF)

        elif state == STATE_INIT:
            state = run_st_read_start_switch(state)

        elif state == STATE_READ_SWITCHES:
            state = run_st_read_switches()

        # Transmitter states
        elif state == STATE_TX_MOUNT_USB:
            # stuck here until the USB is detected and mounted
            state = run_st_tx_mount_usb()

        elif state == STATE_TX_COPY_FROM_USB:
            state = run_st_tx_copy_from_usb()

        elif state == STATE_TX_COMPRESS:
            state = run_st_tx_compress()

        elif state == STATE_TX_CREATE_FRAMES_TO_SEND:
            state, tx_list_of_frames = run_st_tx_create_frames()
            print(f"Number of messages: {len(tx_list_of_frames)}")

        elif state == STATE_TX_TRANSMISSION_INIT:
            state, tx_frame_num = run_st_tx_transmission_init()

        elif state == STATE_TX_TRANSMISSION_SEND_MSG:
            state, tx_frame_num = run_st_tx_transmission_send_msg(tx_list_of_frames, tx_frame_num)

        elif state == STATE_TX_TRANSMISSION_SEND_EOT:
            state = run_st_tx_transmission_send_eot()

        # Receiver states
        elif state == STATE_RX_TRANSMISSION_INIT:
            state, rx_list_received_payload, rx_previous_cnt = run_st_rx_transmission_init()

        elif state == STATE_RX_TRANSMISSION_RECEIVE_MSG:
            state, rx_previous_cnt, rx_list_received_payload = \
                run_st_rx_transmission_receive_msg(rx_previous_cnt, rx_list_received_payload)

        elif state == STATE_RX_DECOMPRESS:
            if put_error < 2:  # we put twice an error in the decompression
                print("We put an error")
                rx_list_received_payload = rx_list_received_payload[:4] + rx_list_received_payload[5:]
                put_error += 1
            state = run_st_rx_decompress(rx_list_received_payload)

        elif state == STATE_RX_TRANSMISSION_SEND_NOK_ACK:
            state, rx_list_received_payload, rx_previous_cnt = run_st_rx_transmission_send_nok_ack()

        elif state == STATE_RX_TRANSMISSION_SEND_OK_ACK:
            state = run_st_rx_transmission_send_ok_ack()

            if not get_time:  # a counter to stop after 10 seconds
                init_wait_time = time.time()
                get_time = True
            if time.time() - init_wait_time > 10:  # Creation of the report
                print("\nReception done!!")
                print(f"in {time.time() - init_time:.2f} seconds")
                time.sleep(1)
                RADIO.stopListening()
                print(f"{len(rx_list_received_payload)} messages received.")

                num = 0
                name_of_file = "report_rx_"
                while os.path.exists(name_of_file + str(num) + ".csv"):
                    num += 1
                name_of_file = name_of_file + str(num) + ".csv"

                csv = "Number of received message; Received payload; Integer message\n"
                for i in range(len(rx_list_received_payload)):
                    csv += str(i) + "; " + str(rx_list_received_payload[i]) \
                           + "; " + str(int(rx_list_received_payload[i].hex(), 16)) + "\n"
                with open(name_of_file, "w") as f:
                    f.write(csv)
                exit(0)

        elif state == STATE_RX_MOUNT_USB:
            # stuck here until the USB is detected and mounted
            state = run_st_rx_mount_usb()

        elif state == STATE_RX_COPY_TO_USB:
            state = run_st_rx_copy_to_usb()

        # Network Mode states
        elif state == STATE_NM:
            state = run_st_network_mode()


if __name__ == "__main__":
    main()
