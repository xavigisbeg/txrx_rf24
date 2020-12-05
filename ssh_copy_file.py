#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
import os
import shutil

# Putty session     (user: pi, password: raspberry)
# SESSION = "home_wifi_rpi0_box"    # -------------------------- set it to the name of your Putty session
# SESSION = "home_wifi_rpi0_unbox"  # -------------------------- set it to the name of your Putty session

SESSION = "phone_rpi0_box"    # -------------------------- set it to the name of your Putty session
# SESSION = "phone_rpi0_unbox"  # -------------------------- set it to the name of your Putty session


def call(cmd):
    print("\t > " + cmd)
    subprocess.call(cmd, shell=True)


def plink_call(cmd):
    call("plink -l pi -pw raspberry -batch " + SESSION + " \"" + cmd + "\"")


def pscp_call(scp, directory=False):
    call("pscp -l pi -pw raspberry " + directory * "-r " + scp)


def execute_python_file(path, file_name):
    plink_call("chmod +x " + path + "/" + file_name)

    # cmd = "cd " + path + " && python3 -u " + file_name
    # plink_call(cmd)


def create_dirs():
    plink_call("sudo rm -rf temp && mkdir temp")  # force removing the temp file to start from scratch


def change_nm_id():
    with open("NM_GENERAL.py", "r") as f:
        lines = f.readlines()
    num_line = 21
    if lines[num_line].startswith("NODE_ID = 1"):
        lines[num_line] = "# " + lines[num_line]
    elif lines[num_line].startswith("# NODE_ID = 1"):
        lines[num_line] = lines[num_line][2:]
    num_line += 1
    if lines[num_line].startswith("# NODE_ID = 5"):
        lines[num_line] = lines[num_line][2:]
    elif lines[num_line].startswith("NODE_ID = 5"):
        lines[num_line] = "# " + lines[num_line]
    f.close()
    with open("NM_GENERAL.py", "w") as f:
        f.writelines(lines)


def copy_files():
    # pscp_call("\"txrx_utils.py\" " + SESSION + ":\"temp/txrx_utils.py\"")
    if SESSION.endswith("unbox"):
        change_nm_id()
    for file in os.listdir():  # find text files inside the input folder
        if (os.path.splitext(file)[1] == ".py" or os.path.splitext(file)[1] == ".txt") and not file.startswith("ssh_"):
            pscp_call("\"" + file + "\" " + SESSION + ":\"temp/" + file + "\"")
    if SESSION.endswith("unbox"):
        change_nm_id()


def execute_python_test():
    execute_python_file("temp", "txrx_state.py")


def copy_back_temp():
    if os.path.exists("temp_" + SESSION):
        shutil.rmtree("temp_" + SESSION)
    pscp_call(SESSION + ":temp temp_" + SESSION, directory=True)


def main():
    create_dirs()
    copy_files()
    execute_python_test()
    # copy_back_temp()


if __name__ == "__main__":
    main()  # used to copy your python files and the .txt file to the Raspberry Pi
    # copy_back_temp()  # used to copy back the directory on the Raspberry Pi to your local directory
