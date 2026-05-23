#!/usr/bin/env bash
set -e
pip install -r dashboard/requirements.txt
streamlit run dashboard/app.py
