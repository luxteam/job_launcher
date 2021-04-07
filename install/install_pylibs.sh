#!/bin/bash
# sudo apt install gcc python-dev python3.9.5-dev python-pip
# sudo apt install python3.9-numpy python3.9-scipy
# apt install gcc python-dev
python3.9 get-pip.py
python3.9 -m pip install --upgrade pip wheel setuptools
python3.9 -m pip install --user -r requirements.txt
