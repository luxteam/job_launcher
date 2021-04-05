#!/bin/bash
python -m pip install -r install/requirements.txt
python -m pytest tests/ums.py
