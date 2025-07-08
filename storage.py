import os
import json

def get_data_path():
    return os.path.join(os.path.dirname(__file__), 'projects.json')

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
