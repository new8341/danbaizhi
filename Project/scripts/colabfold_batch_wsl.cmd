@echo off
REM Windows entry for WSL ColabFold (used by run_colabfold_optional.py).
setlocal
set "ROOT=%~dp0.."
py -3 "%ROOT%\code\colabfold_batch_wsl.py" %*
