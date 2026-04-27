@echo off
"%~dp0..\python.exe" -c "from pymasking.cli.main import _download_entry; _download_entry()" %*
