@echo off
cd /d "%~dp0"
start "FeesDefender" python -m streamlit run streamlit_app.py
