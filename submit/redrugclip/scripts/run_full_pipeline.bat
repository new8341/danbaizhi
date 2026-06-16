@echo off
cd /d "%~dp0.."
py -3 scripts\run_agent.py %*
