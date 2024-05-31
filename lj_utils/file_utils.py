
import os

# from tildagon os launcher/app.py
def file_exists(path):
    try:
        return (os.stat(path)[0] & 0x8000) != 0
    except OSError:
        return False

def folder_exists(path):
    try:
        return (os.stat(path)[0] & 0x4000) != 0
    except OSError:
        return False