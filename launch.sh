#!/bin/bash
cd "$HOME/minimal-screen-recorder" || exit 1
source env/bin/activate
python app.py
