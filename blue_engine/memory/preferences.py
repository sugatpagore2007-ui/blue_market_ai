from __future__ import annotations
import json, os
FILE='blue_preferences.json'

def load_preferences():
    if not os.path.exists(FILE): return {}
    try:
        with open(FILE,'r',encoding='utf-8') as f: return json.load(f)
    except Exception: return {}

def save_preference(key, value):
    data=load_preferences(); data[key]=value
    with open(FILE,'w',encoding='utf-8') as f: json.dump(data,f,indent=2)
    return data

def preference_summary():
    data=load_preferences()
    if not data: return 'No saved preferences yet.'
    return ', '.join(f'{k}: {v}' for k,v in data.items())
