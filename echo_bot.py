import os
import telebot
from telebot import types
import stripe
import subprocess
import requests
import json
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#Running Your Telegram Bot Script:
import telebot
import requests
# Other import statements...
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
FLASK_WRAPPER_URL = os.getenv('FLASK_WRAPPER_URL')

bot = telebot.TeleBot(API_TOKEN)
stripe.api_key = STRIPE_API_KEY

# Handling the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = ("Welcome to Mira AI!\n\n"
                    "You can chat, receive audio messages, call, and get 🔥 pics from Mira.\n\n"
                    "Use /image to generate an image, use /call to call Mira, and use /subscribe to start chatting with Mira\n\n"
                    "Say “Hey” to get started!")
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['payments', 'deposit'])
def handle_payments(message):
    # Define your Stripe product IDs here
    product_ids = {
        '2': 'price_1OnRPkSDPH8n3uDEY2gZGOIi',
        '8': 'price_1OnRQkSDPH8n3uDEpzONyfCp',
        '20': 'price_1OnRR7SDPH8n3uDEiKuLkrvu',
        '50': 'price_1OnRSASDPH8n3uDES16z8diB',
        '100': 'price_1OnRSXSDPH8n3uDETO89ZHhw',
        '200': 'price_1OnRSxSDPH8n3uDEdWQi43oq',
    }

    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    
    for label, price_id in product_ids.items():
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{'price': price_id, 'quantity': 1}],
            mode='payment',
            success_url='https://your-success-url.com/',
            cancel_url='https://your-cancel-url.com/',
        )
        button = types.InlineKeyboardButton(f'{label} Credits', url=session.url)
        buttons.append(button)

    # Split buttons into rows of 3
    while buttons:
        markup.add(*buttons[:3])
        buttons = buttons[3:]

    # Send the message with multiple payment options
    bot.send_message(
        message.chat.id,
        "Add credits to generate images and phone calls! 😉😈\n\n"
        "Payments are securely powered. Please select a deposit amount:\n\n"
        "(1 SFW Image = 1 Credit, 1 NSFW = 2 Credits)\n"
        "1 min = 1 Credit (☎️)",
        reply_markup=markup
    )
@bot.message_handler(commands=['image'])
def request_image_prompt(message):
    msg = bot.send_message(message.chat.id, "Please send me a prompt for the image.")
    bot.register_next_step_handler(msg, generate_and_send_image)

def generate_and_send_image(message):
    prompt = message.text
    image_data = generate_image_with_fooocus(prompt)
    
    if image_data:
        # Assuming the API returns a direct URL to the generated image
        # You might need to adjust this if your API returns base64-encoded image data
        image_url = image_data.get("url")  # Adjust according to your API response structure
        bot.send_photo(message.chat.id, photo=image_url)
    else:
        bot.send_message(message.chat.id, "Sorry, I couldn't generate an image right now.")
        
def generate_image_with_fooocus(prompt):
    response = requests.post(FLASK_WRAPPER_URL, json={"prompt": prompt}, headers={'Content-Type': 'application/json'})
    if response.status_code == 200:
        response_json = response.json()
        # Assuming the API returns the path or filename in a key 'image_filename'
        image_filename = response_json.get('image_path')  # Adjust 'image_path' to match the key from your API response
        return image_filename
    else:
        logging.error(f"Fooocus API request failed with status code {response.status_code}")
        return None

def generate_and_send_image(message):
    prompt = message.text
    image_filename = generate_image_with_fooocus(prompt)
    if image_filename:
        # Assuming images are saved in a specific directory; adjust the path as needed.
        image_path = f"/full/path/to/images/{image_filename}"  # Adjust this path to where Fooocus saves images
        try:
            with open(image_path, 'rb') as image_file:
                bot.send_photo(message.chat.id, photo=image_file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "The image was not found.")
        except Exception as e:
            bot.send_message(message.chat.id, f"An error occurred: {str(e)}")
    else:
        bot.send_message(message.chat.id, "Sorry, I couldn't generate an image right now.")

    
    # Add this near your other command handlers
@bot.message_handler(commands=['call'])
def start_call_process(message):
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(types.KeyboardButton('Send Phone Number', request_contact=True))
    msg = bot.reply_to(message, 'Please provide your phone number to initiate the call.', reply_markup=markup)
    bot.register_next_step_handler(msg, process_phone_number)

def process_phone_number(message):
    if not message.contact:
        bot.reply_to(message, "Please send your phone number using the Telegram contact feature.")
        return

    phone_number = message.contact.phone_number
    user_id = message.from_user.id
    
    # Here, check if the user has enough credits
    # For demonstration, let's say each call costs 1 credit.
    # You would retrieve and check the user's credit balance from your database
    user_credits = check_user_credits(user_id)  # Implement this function
    if user_credits < 1:
        bot.reply_to(message, "You do not have enough credits to make a call.")
        return
    
    # If they have credits, initiate the call
    initiate_call_with_twilio(phone_number, user_id)


if __name__ == '__main__':
    bot.infinity_polling()
