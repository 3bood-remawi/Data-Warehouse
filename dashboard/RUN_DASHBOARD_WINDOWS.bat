@echo off
echo Installing dashboard requirements...
pip install -r dashboard\requirements.txt

echo Starting Streamlit dashboard...
streamlit run dashboard\app.py
pause
