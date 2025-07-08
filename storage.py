import os
import json


import sys
def get_base_path():
    # Use the folder of the .exe if frozen, else the script directory
    if hasattr(sys, '_MEIPASS'):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    return os.path.join(get_base_path(), 'projects.json')

def load_projects():
    path = get_data_path()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_projects(projects):
    path = get_data_path()
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(projects, f, indent=2, ensure_ascii=False)
