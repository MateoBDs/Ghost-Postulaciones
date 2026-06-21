import json
import os

CONFIG_PATH = './config.json'
QUESTIONS_PATH = './questions.json'

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

def load_questions():
    if not os.path.exists(QUESTIONS_PATH):
        return []
    with open(QUESTIONS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def update_config_value(key, value):
    config = load_config()
    config[key] = value
    save_config(config)

def update_nested_config_value(category, key, value):
    config = load_config()
    if category in config:
        config[category][key] = value
        save_config(config)
