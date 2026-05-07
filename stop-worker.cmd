@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop-worker.ps1" %*
