"""
PyInstaller hook for tiktoken.

This hook collects tiktoken's data files (encoding tables) for bundling.
"""
from PyInstaller.utils.hooks import collect_data_files

# Collect all data files from tiktoken package
datas = collect_data_files('tiktoken')
