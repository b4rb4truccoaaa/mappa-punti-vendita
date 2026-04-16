#!/usr/bin/env bash
set -e
pip install -r requirements.txt
python seed_db.py
