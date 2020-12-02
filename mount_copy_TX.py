#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import subprocess

def mount_USB(p_dir):
    list_usb = os.listdir(p_dir)
    if len(list_usb) != 0:
        print("USB mounted")
        p_mounted = 1
        p_dir = p_dir + '/' + list_usb[0]
        for file in os.listdir(p_dir):
            if not file.startswith('.'):
                if os.path.splitext(file)[1] == ".txt":
                    p_file_dir = p_dir + '/' + file
    else:
        print("No USB mounted")
        p_mounted = 0
        p_file_dir = ''

    return p_mounted, p_file_dir


def copy_file_TX(p_file_dir, p_home_dir, p_file_name):
    os.system('sudo cp ' + p_file_dir + ' ' + p_home_dir + '/' + p_file_name)
    print("File copied at: " + p_home_dir + '/' + p_file_name )



def main():
    dir = '/media/pi'
    home_dir = '/home/pi/Desktop'
    file_name = 'send_file_USB.txt'
    mounted = 0
    while mounted == 0:
        mounted, file_dir = mount_USB(dir)
        time.sleep(1)
    copy_file_TX(file_dir, home_dir, file_name)

if __name__ == '__main__':
    main()
