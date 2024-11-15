import os
import telebot
import logging
from pymongo import MongoClient
from datetime import datetime, timedelta
import subprocess
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# Telegram bot token and MongoDB URI
TOKEN = '7889670543:AAE2CpKPg_CsbkmmAB3Wrk4434JmHofZVNM'
MONGO_URI = 'mongodb+srv://Soul:JYAuvlizhw7wqLOb@soul.tsga4.mongodb.net'
CHANNEL_ID = 1002292224661
ERROR_CHANNEL_ID = 1002292224661

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

client = MongoClient(MONGO_URI)
db = client['soul']
users_collection = db.users

bot = telebot.TeleBot(TOKEN)

# Blocked ports list
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]

# Admin IDs (this list can be modified to include multiple admin IDs)
admin_ids = [6207079474]  # Replace this with the actual admin's user ID(s)

# Function to check if user is an admin
def is_user_admin(user_id):
    return user_id in admin_ids

# Admin command to approve/disapprove user
@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Check if the user is an admin
    if not is_user_admin(user_id):
        bot.send_message(chat_id, "*You are not authorized to use this command.*", parse_mode='Markdown')
        return

    cmd_parts = message.text.split()

    if len(cmd_parts) < 4:
        bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days>*", parse_mode='Markdown')
        return

    try:
        target_user_id = int(cmd_parts[1])
        plan = int(cmd_parts[2])
        days = int(cmd_parts[3])
    except ValueError:
        bot.send_message(chat_id, "*Invalid input. Please make sure user_id, plan, and days are numbers.*", parse_mode='Markdown')
        return

    # Calculate the expiration date
    valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()

    if message.text.startswith('/approve'):
        # Update the user's plan and validity in the database
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        # Send confirmation message to the admin
        admin_msg = f"*User {target_user_id} has been approved with Plan {plan} for {days} day(s).*"
        bot.send_message(chat_id, admin_msg, parse_mode='Markdown')

        # Send message to the approved user
        user_msg = f"Hello! You have been approved with Plan {plan} for {days} day(s). Your access is valid until {valid_until}.\n\nEnjoy your time!"
        try:
            bot.send_message(target_user_id, user_msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(chat_id, f"Failed to notify user {target_user_id}: {e}")
    
    elif message.text.startswith('/disapprove'):
        # Remove or disapprove the user (reset their plan and validity)
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        # Send confirmation message to the admin
        admin_msg = f"*User {target_user_id} has been disapproved and reverted to free access.*"
        bot.send_message(chat_id, admin_msg, parse_mode='Markdown')

        # Send message to the disapproved user
        user_msg = f"Your access has been revoked. You are now reverted to free access. Please contact the admin for further details."
        try:
            bot.send_message(target_user_id, user_msg, parse_mode='Markdown')
        except Exception as e:
            bot.send_message(chat_id, f"Failed to notify user {target_user_id}: {e}")

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
            bot.send_message(chat_id, "Your VIP Plan 💥 is currently not available due to limit reached.")
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

        # Simulate the attack here (you can replace this with the actual logic for launching the attack)
        bot.send_message(message.chat.id, f"Attack started on {target_ip}:{target_port} for {duration_minutes} minutes.")
        
        # Here you can run your actual attack logic (instead of the simulation)
        # Example: subprocess.Popen(f"./sam {target_ip} {target_port} {duration_minutes}", shell=True)
        bot.send_message(message.chat.id, f"Attack on {target_ip}:{target_port} for {duration_minutes} minutes has completed.")

    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")

# Welcome message with keyboard
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    # Check user's plan and validity
    user_data = users_collection.find_one({"user_id": user_id})
    
    if user_data and user_data.get("plan") > 0:
        plan = user_data["plan"]
        valid_until = user_data["valid_until"]
        
        # Check if the user's plan is still valid
        if datetime.strptime(valid_until, "%Y-%m-%d") >= datetime.now():
            # Create the reply keyboard with two buttons: VIP Plan and /attack
            markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
            btn_vip_plan = KeyboardButton("VIP Plan 💥")  # VIP Plan button
            btn_attack = KeyboardButton("/attack")  # /attack button

            markup.add(btn_vip_plan, btn_attack)

            bot.send_message(user_id, f"Welcome back! Your plan is {plan} and it's valid until {valid_until}.", reply_markup=markup)

            # If VIP Plan 💥 selected, send a congratulatory message
            if plan == 2:
                bot.send_message(user_id, "Congratulations on selecting VIP Plan 💥! You now have priority access and additional features.", parse_mode="Markdown")
        else:
            bot.send_message(user_id, "Your plan has expired. Please contact the admin to renew your plan.")
    else:
        bot.send_message(user_id, "You have not been approved yet. Please contact the admin for approval @SAMY784.")

# Start polling
if __name__ == "__main__":
    logging.info("Starting bot...")
    bot.polling(none_stop=True)
        
