import os
import telebot
from telebot import types
import stripe
import subprocess
import requests
import json
import logging
import telebot
import requests
import time

# additional imports
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

API_TOKEN = os.getenv('API_TOKEN')
STRIPE_API_KEY = os.getenv('STRIPE_API_KEY')
FLASK_WRAPPER_URL = os.getenv('FLASK_WRAPPER_URL')

bot = telebot.TeleBot(API_TOKEN)
stripe.api_key = STRIPE_API_KEY

# comfyUI prompt endpoint
PROMPT_URL = os.getenv('PROMPT_URL')
COMFY_OUTPUT_DIR = os.getenv('COMFY_OUTPUT_DIR')

# start command
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

# image command
@bot.message_handler(commands=['image'])
def request_image_prompt(message):
    msg = bot.send_message(message.chat.id, "Please send me a prompt for the image.")
    bot.register_next_step_handler(msg, generate_and_send_image)

# generate image
def generate_and_send_image(message):
    prompt = message.text
    image_path = generate_image(prompt)

    if image_path:
        try:
            with open(image_path, 'rb') as image_file:
                bot.send_photo(message.chat.id, photo=image_file)
        except FileNotFoundError:
            bot.send_message(message.chat.id, "Couldn't find image")
        except Exception as e:
            bot.send.message(message.chat.id, f"An error occurred: {str(e)}")
    else:
        bot.send_message(message.chat.id, "Sorry, I couldn't generate an image right now.")


# get latest image
def get_latest_image(folder):
	files = os.listdir(folder)
	image_files = [f for f in files if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
	image_files.sort(key=lambda x: os.path.getmtime(os.path.join(folder, x)))
	latest_image = os.path.join(folder, image_files[-1] if image_files else None)
	return latest_image

# start queue
def start_queue(prompt_workflow):
	p = {"prompt": prompt_workflow}
	queue_data = json.dumps(p).encode('utf-8')
	requests.post(PROMPT_URL, data=queue_data)

# generate image using workflow
def generate_image(user_prompt):
    with open("utils/workflow.json", "r") as workflow_config:
        workflow_prompt = json.load(workflow_config)

    # Generate a unique seed for each image generation
    unique_seed = int(time.time() * 1000) # Using current timestamp in milliseconds

    # Modify the workflow_prompt to include the unique_seed
    workflow_prompt['3']['inputs']['seed'] = unique_seed

    final_prompt = "miranowhere (green eyes) (a woman) " + user_prompt

    # add custom user prompt
    workflow_prompt['6']['inputs']['text'] = final_prompt

    # check for any previously generated image
    prev_image = get_latest_image(COMFY_OUTPUT_DIR)

    start_queue(workflow_prompt)

    while True:
        latest_image = get_latest_image(COMFY_OUTPUT_DIR)
        if latest_image != prev_image:
            return latest_image

        time.sleep(1)
    
# call command
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
    print("Bot started...")
    bot.infinity_polling()
