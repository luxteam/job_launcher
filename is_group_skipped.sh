#!/bin/bash
GPU="$1"
OS="$2"
ENGINE="$3"
TESTS_PATH="$4"

python3.9 core/isGroupSkipped.py --gpu $GPU --os $OS --engine $ENGINE --tests_path $TESTS_PATH
