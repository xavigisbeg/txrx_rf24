# -*- coding: utf-8 -*-


# ------------ States Definition ------------ #

STATE_FINAL         = 0
STATE_INIT          = 1
STATE_READ_SWITCHES = 2

STATE_TX_MOUNT_USB                    = 3
STATE_TX_COPY_FROM_USB                = 4
STATE_TX_COMPRESS                     = 5
STATE_TX_CREATE_FRAMES_TO_SEND        = 6
STATE_TX_TRANSMISSION_INIT            = 7
STATE_TX_TRANSMISSION_SEND_MSG        = 8
STATE_TX_TRANSMISSION_SEND_EOT        = 9

STATE_RX_TRANSMISSION_INIT        = 10
STATE_RX_TRANSMISSION_RECEIVE_MSG = 11
STATE_RX_DECOMPRESS               = 12
STATE_RX_MOUNT_USB                = 13
STATE_RX_COPY_TO_USB              = 14

STATE_NM = 15
