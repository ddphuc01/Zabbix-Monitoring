#!/usr/bin/env python3
"""
Quick script to get bot information and test message handling
"""
import os
import asyncio
from telegram import Bot

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '8018250055:AAGc0cdXIrIwtoSI94aAWe-xrBR11H-NC1E')

async def get_bot_info():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Get bot information
    me = await bot.get_me()
    print(f"🤖 Bot Information:")
    print(f"   ID: {me.id}")
    print(f"   Username: @{me.username}")
    print(f"   Name: {me.first_name}")
    print(f"   Can Read All Group Messages: {me.can_read_all_group_messages}")
    print(f"   Supports Inline Queries: {me.supports_inline_queries}")
    
    # Get recent updates
    print(f"\n📨 Recent Updates (last 5):")
    updates = await bot.get_updates(limit=5)
    
    if not updates:
        print("   No recent updates")
    else:
        for update in updates:
            print(f"\n   Update ID: {update.update_id}")
            if update.message:
                msg = update.message
                print(f"   From: {msg.from_user.first_name} (@{msg.from_user.username})")
                print(f"   Chat Type: {msg.chat.type}")
                print(f"   Text: {msg.text}")
                if msg.entities:
                    print(f"   Entities: {[e.type for e in msg.entities]}")

if __name__ == '__main__':
    asyncio.run(get_bot_info())
