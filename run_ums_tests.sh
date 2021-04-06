#!/bin/bash
./install/install_pylibs.sh
python3 -m pytest tests/ums.py
