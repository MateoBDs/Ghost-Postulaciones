import discord
import json
from datetime import datetime
import os

LOGS_FILE = './data/history.json'

def log_application(user_id, user_name, answers):
    if not os.path.exists('./data'):
        os.makedirs('./data')
    
    history = []
    if os.path.exists(LOGS_FILE):
        with open(LOGS_FILE, 'r', encoding='utf-8') as f:
            try:
                history = json.load(f)
            except json.JSONDecodeError:
                history = []

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "user_name": user_name,
        "answers": answers
    }
    history.append(log_entry)

    with open(LOGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

async def send_log_embed(bot, config, title, description, color=None):
    log_channel_id = config['channels'].get('logs')
    if not log_channel_id:
        return

    channel = bot.get_channel(log_channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color or config['embeds']['success_color'],
        timestamp=datetime.now()
    )
    await channel.send(embed=embed)
