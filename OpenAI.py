# Makes a prompt request to Text_DaVinci-3 using Twilio, Ngrok and Flask

# https://console.twilio.com/us1/develop/phone-numbers/manage/incoming?frameUrl=%2Fconsole%2Fphone-numbers%2Fincoming%2FPN43550d505a24d5283e6b7b65f76b2333%3Fx-target-region%3Dus1
#      A message comes in, set webhook here, for individual phone numbers
# https://console.twilio.com/us1/service/sms/MG40c519a5b8acb936be5f0c92c3957808/sms-service-instance-configure?frameUrl=%2Fconsole%2Fsms%2Fservices%2FMG40c519a5b8acb936be5f0c92c3957808%3Fx-target-region%3Dus1
#      Set webhook for incoming messages, for messaging service
# https://www.toptal.com/developers/postbin/
# https://dashboard.ngrok.com/
# https://platform.openai.com/docs/api-reference/moderations/create
# https://platform.openai.com/tokenizer?view=bpe
# https://platform.openai.com/docs/api-reference/images/create

import os
import sys
import openai
import sqlite3
import hashlib
import logging
import platform
import pyperclip
from pyngrok import ngrok
from twilio.rest import Client
from flask import Flask, request

# Set up logging for pyngrok and twilio
# NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
# logging.basicConfig(filename='log.txt', level=logging.DEBUG, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.WARNING, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("pyngrok").setLevel(logging.WARNING)
logging.getLogger("twilio").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Redirect stderr to the log file
# sys.stderr = open('log.txt', 'w')

DIRS = {
    "Linux": "/home/ec2-user/Desktop/TextGPT",
    "Darwin": "/Users/khallid/PycharmProjects/TextGPT",
}

BASE_DIR = DIRS.get(platform.system(), "")

CONFIG_FILE = {
    DIRS["Linux"]: "/home/ec2-user/CONFIG_APIS.ini",
    DIRS["Darwin"]: "/Users/khallid/Documents/Coding/Python/CONFIG_APIS.ini",
}.get(BASE_DIR, "")

try:
    os.chdir(BASE_DIR)
    print(f"Success, current {os.getcwd()}")
except:
    print(f"{BASE_DIR} not found, currently in {os.getcwd()}")

print(f"Config directory:  {CONFIG_FILE}")

app = Flask(__name__)  # Start the Flask App

def get_config_key(_section_name = None, _secret_only = True, _key_name = None, _print = False):
    """
    Return the secret corresponding to the section selected

    :param _section_name: The section for which to ge the key
    :param _secret_only: Return the secret only
    :param _key_name: The name of the key to return
    :return: The key to return
    """

    import configparser
    # import logging

    # logger = logging.getLogger()
    #
    # # Set the logging levelS
    # if(not _print):
    #     logger.setLevel(logging.INFO)
    # else:
    #     logger.setLevel(logging.DEBUG)

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    sections = config.sections()
    section_name = _section_name

    while section_name not in sections:
        # Get the sections
        # Print the sections with numbers
        for i, section in enumerate(sections):
            print(f"{i + 1}. {section}")

        # Ask the user which section they would like to access
        section_number = int(input("Which section would you like to access? (Enter a number) "))

        # Check if the section number is valid
        if section_number > 0 and section_number <= len(sections):
            # Get the selected section name
            section_name = sections[section_number - 1]

        else:
            print(f"Invalid section number.")

    key_name = _key_name

    if _secret_only:
        logging.debug(f"Secret: {config[section_name]['SECRET']}")
        return config[section_name]['SECRET']

    else:
        while key_name is None:
            # Get the keys in the section
            keys = config[section_name]._options()
            print("Keys:", keys)

            # Ask the user which key they would like to access
            key_number = int(input("Which key would you like to access? "))

            # Check if the section number is valid
            if key_number > 0 and key_number <= len(keys):
                # Get the selected section name
                key_name = keys[key_number - 1]

            # Check if the key exists
            if key_name in keys:
                value = config[section_name][key_name]
                logging.debug(f"{key_name} = {value}")
            else:
                print(f"Key '{key_name}' not found in section '{section_name}'.")

        logging.debug(f"{key_name}: {config[section_name][key_name]}")
        return config[section_name][key_name]


def create_database():
    """
    Creates SQL database with relevant columns

    :return: None
    """

    conn = sqlite3.connect("program_data.db")

    # Create a cursor object to execute SQL statements
    cursor = conn.cursor()

    table_name = "responses"

    column1 = ("question", "TEXT")
    column2 = ("message_response", "TEXT")
    column3 = ("temperature", "REAL")
    column4 = ("model", "TEXT")
    column5 = ("max_tokens", "INTEGER")
    column6 = ("completion_tokens", "INTEGER")
    column7 = ("prompt_tokens", "INTEGER")
    column8 = ("total_tokens", "INTEGER")
    column9 = ("user_hash", "TEXT")
    column10 = ("timestamp", "INTEGER")
    column11 = ("response_id", "TEXT")
    column12 = ("finish_reason", "TEXT")
    column13 = ("sender_hash", "TEXT")

    # Create the "responses" table if it doesn't exist
    cursor.execute(f'''CREATE TABLE IF NOT EXISTS {table_name}(
                        {column1[0]} {column1[1]} NOT NULL,
                        {column2[0]} {column2[1]} NOT NULL,
                        {column3[0]} {column3[1]} NOT NULL,
                        {column4[0]} {column4[1]} NOT NULL,
                        {column5[0]} {column5[1]} NOT NULL,
                        {column6[0]} {column6[1]} NOT NULL,
                        {column7[0]} {column7[1]} NOT NULL,
                        {column8[0]} {column8[1]} NOT NULL,
                        {column9[0]} {column9[1]} NOT NULL,
                        {column10[0]} {column10[1]} NOT NULL,
                        {column11[0]} {column11[1]} NOT NULL,
                        {column12[0]} {column12[1]} NOT NULL,
                        {column13[0]} {column13[1]} NOT NULL
                    )''')

    conn.commit()
    conn.close()


@app.route("/sms", methods=['POST'])
def handle_incoming():
    """
    User text messages received from Twilio are routed to Text-Davinci-003 and response is sent back to user

    # :param request: The question to be asked of OpenAI model
    :return: The message.sid value
    """

    # Get message from Twilio request
    question = request.values.get('Body', None)
    sender = request.values.get('From', None)

    # for k,v in request.values.items():
    #     print(k, v)

    # print(f"Message: {message}\nSender: {sender}")

    user = request.values["From"]  # This should be hashed for privacy and security
    user_hash = hashlib.sha256(user.encode()).hexdigest()
    sender_hash = hashlib.sha256(sender.encode()).hexdigest()

    # Extract temperature and max tokens from message, if they exist
    temperature = 0.5
    max_tokens = 200

    import time
    time.perf_counter()

    print("Message received from", request.values["From"])

    if "@@" in question:
        import requests

        question = question.replace("@@", "")

        # Define the API endpoint
        endpoint = "https://api.openai.com/v1/images/generations"

        # Define the text description of the image you want to generate
        description = question

        # Define the API key to use for authentication

        # Define the headers to send with the API request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openai.api_key}"
        }

        # Define the data to send with the API request
        data = {
            "model": "image-alpha-001",
            "prompt": description
        }

        # Make the API request
        response = requests.post(endpoint, headers=headers, json=data)

        # Check if the API request was successful
        if response.status_code == 200:
            # Get the URL of the generated image
            image_url = response.json()["data"][0]["url"]

            # Send response back to user's phone number via Twilio
            response_message = client.messages.create(messaging_service_sid=messaging_sid,
                                                      body=image_url,
                                                      from_=from_number,
                                                      to=sender)

        else:
            pass

        return "sid"
    # ...

    elif "!!" in question:
        # Ask ChatGPT
        pass

    else:
        if "::" in question:
            params = question.split("::")[1]

            if ' ' in params:
                params = params.replace(' ', '')

            parameters = params.split(":")
            temperature = float(parameters[0])

            try:
                max_tokens = int(parameters[1])
                question = question.split("::")[0]
            except:
                print("No second parameter")

        # Send message to OpenAI API
        response = openai.Completion.create(n=1,  # How many completions to generate for each prompt.
                                            user=user_hash,  # string representing a user
                                            stop=None,  #
                                            top_p=1,
                                            # 0.1 means only the tokens comprising the top 10% probability mass are considered.
                                            prompt=question,  #
                                            engine=models["td2"],  #
                                            max_tokens=max_tokens,
                                            # The maximum number of tokens to generate in the completion
                                            temperature=temperature,
                                            # Higher values, more risks. 1 very dynamic, 0 for well-defined static
                                            presence_penalty=0,
                                            # 0 and 2.0. Positive values penalize new tokens based on whether they appear in the text, increasing the model's likelihood to talk about new topics.
                                            frequency_penalty=0)  # 0 and 2.0. Positive values penalize new tokens based on existing frequency in text, decreasing the model's likelihood to repeat the same line verbatim.

        # Get the message response
        message_response = response["choices"][0]["text"].removeprefix('?').lstrip()  # + f"[{params}]"

        # if message_response.startswith('?'):
        #     message_response = message_response.removeprefix('?')

        # message_response.l

        """
        sample openAI response object

        {'choices': [{'finish_reason': 'length',
                      'index': 0,
                      'logprobs': None,
                      'text': 'Blah blah blah'}],
         'created': 1675849159,
         'id'     : 'cmpl-6hbD5CbVwYJsWMFNBs0gAj7IWSCLV',
         'model'  : 'text-davinci-003',
         'object' : 'text_completion',
         'usage'  : {'completion_tokens': 40,
                     'prompt_tokens': 2,
                     'total_tokens': 42}}
        """

        # Send response back to user's phone number via Twilio
        response_message = client.messages.create(messaging_service_sid=messaging_sid,
                                                  body=message_response,
                                                  from_=from_number,
                                                  to=sender)

        # Extract data from response object
        finish_reason = response['choices'][0]['finish_reason']
        response_id   = response['id']
        token_data    = response["usage"]

        # Insert these values into db: user_id, prompt, response, temperature, max_tokens, timestamp, model, finish_reason, sender, id
        database_values = [question, message_response, temperature, response["model"],
                           max_tokens, int(token_data["completion_tokens"]), int(token_data["prompt_tokens"]),
                           int(token_data["total_tokens"]), user_hash, int(response["created"]), response_id,
                           finish_reason, sender_hash]

        # for x in database_dict:
        #     print(x[0])
        #     print(x[1])
        #     print(type(x[1]))
        #     print("#########################################")

        #####################################################################################################################

        create_database()

        # Connect to the database file or create it if it doesn't exist
        conn = sqlite3.connect("program_data.db")

        # Create a cursor object to execute SQL statements
        cursor = conn.cursor()

        # Insert the values of database_values into the "responses" table
        cursor.execute('''INSERT INTO responses(question, message_response, temperature, model, max_tokens, completion_tokens,
                          prompt_tokens, total_tokens, user_hash, timestamp, response_id, finish_reason, sender_hash)
                          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', database_values)

        conn.commit()
        conn.close()

        return response_message.sid


def ask_test_question():
    """

    :return:
    """

    def respond(_question, _model, _temperature=0, _pr_pen=0, _freq_pen=0, _max_tokens=200):
        """
        Creates and retrieves response from openAI model

        :param _question: question to be asked
        :param _model: Which GPT model to use
        :param _temperature: Creativity of the model
        :param _pr_pen: increases likelihood of new topics
        :param _freq_pen: decrease his likelihood of lines repeating
        :param _max_tokens: maximum tokens to be used in total for this request,

        :return: The openai response to the question
        """

        response = openai.Completion.create(n=1, prompt=_question, engine=models[_model],
                                            temperature=_temperature, presence_penalty=_pr_pen,
                                            frequency_penalty=_freq_pen, max_tokens=_max_tokens)

        return response["choices"][0]["text"].removeprefix('?').lstrip()

    def make_qlist(_text=None):
        """
        Takes a list of question (one per line) and creates a list, one per line

        :param _text: The questions (one per line) to make into a list
        :return: The questions as a list
        """

        # _text =

        lines = _text.split('\n')
        if len(lines[-1]) < 2:
            lines = lines[:-1]

        return lines

    new_qs = make_qlist(pyperclip.paste())

    model_answers = {x: {} for x in new_qs}
    limit = 1

    for number, question in enumerate(new_qs[:limit]):
        for key in models.keys():
            try:
                answer = respond(question, key)
            except:
                answer = f"Error using model{models[key]}"

            model_answers[question][key] = answer

        print(f"{number + 1} of {limit}")

    for i in model_answers[new_qs[0]]:
        print(f"####################{i}]####################")
        print(model_answers[new_qs[0]][i])
        print("\n\n\n###############################################")

    # List to file
    with open(f'{BASE_DIR}/chatgpt_questions.txt', 'w') as file:
        for q in new_qs:
            file.write(q + '\n')

    # File to list
    with open(f'{BASE_DIR}/chatgpt_questions.txt', 'r') as file:
        strings = file.readlines()


# from twilio.twiml.messaging_response import MessagingResponse

# https://github.com/settings/personal-access-tokens/new
# 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
# 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


# OpenAI account information
openai.api_key = get_config_key("OPENAI")  # OpenAI API key

# Ngrok tunnel start
# ngrok.kill()
# ngrok.disconnect()

ngrok.set_auth_token(get_config_key("NGROK"))
ngrok_tunnel_url = ngrok.connect(5000).public_url
print(f"Tunnel Created at {ngrok_tunnel_url}")

# Twilio account information
from_number   = get_config_key("TWILIO", False, "TWILIO_PHONE_NUMBER")  # Twilio phone number
messaging_sid = get_config_key("TWILIO", False, "MESSAGING_SID")
to_number     = get_config_key("TWILIO", False, "CELL_NUMBER")  # Your phone number
auth_token    = get_config_key("TWILIO", False, "SECRET")
account_sid   = get_config_key("TWILIO", False, "SID")

client = Client(account_sid, auth_token)
# don't think I need this since I am updating the webhook 3 lines down
# client.incoming_phone_numbers.list(phone_number = from_number)[0].update(sms_url = ngrok_tunnel_url)

messaging_service = client.messaging.services(messaging_sid).fetch()
messaging_service.update(inbound_request_url=ngrok_tunnel_url + "/sms", inbound_method="POST")

# openai.util.logging.getLogger().setLevel(logging.WARNING)

models = {"td3": "text-davinci-003",    # Large-scale text generation
                                        #      high performance trained on internet text
          "td2": "text-davinci-002",    # Large-scale text generation
                                        #      balance between performance and cost-effectiveness
          "cd2": "code-davinci-002",    # Code generation and programming language understanding
          # "ta2": "text-ada-002",      # Text completion and answer generation
          #                             #      high-quality and persuasive text
          "ta1": "text-ada-001",        # Text completion and answer generation
                                        #      trained on a diverse internet text and generating fluent human-like text
          "ccc": "curie",               # Text generation and question answering
          #      focused on knowledge-based and conversational tasks
          # "tc3": "text-curie-003",    # Text generation and language understanding
          #                             #      provides additional fine-tuning capabilities
          # "tc2": "text-curie-002",    # Text generation and language understanding
          #                             #      more diverse and in-depth content generation
          "tc1": "text-curie-001",      # Text generation and language understanding
                                        #      performs well on a wide range of natural language tasks
          # "tb3": "text-babbage-003",  # Text generation and language modeling
          #                             #      specific use cases such as summarization and data-to-text
          # "tb2": "text-babbage-002",  # Text generation and language modeling
          #                             #      text for specific domains
          "tb1": "text-babbage-001",    # Text generation and language modeling
                                        #      more structured and technical text
          "cc1": "code-cushman-001"}    # Code generation and completion
                                        #      balance between performance and cost-effectiveness

if __name__ == "__main__":
    # if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    #     start_ngrok(ngrok_url)

    # Create database
    # create_database()

    # Setting this to True makes Ngrok use more than one tunnel and breaks free version
    app.debug = False
    app.run(debug = False)

# # Makes a prompt request to Text_DaVinci-3 using Twilio, Ngrok and Flask
#
# ##################################################################################################################################################
# # HELPFUL LINKS
# # https://console.twilio.com/us1/develop/phone-numbers/manage/incoming?frameUrl=%2Fconsole%2Fphone-numbers%2Fincoming%2FPN43550d505a24d5283e6b7b65f76b2333%3Fx-target-region%3Dus1
# # A message comes in, set webhook here, for individual phone numbers
#
# # https://console.twilio.com/us1/service/sms/MG40c519a5b8acb936be5f0c92c3957808/sms-service-instance-configure?frameUrl=%2Fconsole%2Fsms%2Fservices%2FMG40c519a5b8acb936be5f0c92c3957808%3Fx-target-region%3Dus1
# # Set webhook for incoming messages, for messaging service
#
# # https://www.toptal.com/developers/postbin/
#
# # https://dashboard.ngrok.com/
# ##################################################################################################################################################
#
# import os
# import fxs
# import twilio
# import openai
# from pyngrok import ngrok
# from twilio.rest import Client
# from flask import Flask, request, redirect
# from twilio.twiml.messaging_response import MessagingResponse
#
# # OpenAI account information
# openai.api_key = fxs.get_config_key("OPENAI")  # OpenAI API key
#
# # Ngrok tunnel start
# ngrok.set_auth_token(fxs.get_config_key("NGROK"))
# ngrok_tunnel_url = ngrok.connect(5000).public_url
# print(f"Tunnel Created at {ngrok_tunnel_url}")
#
# # Twilio account information
# from_number = fxs.get_config_key("TWILIO", False, "TWILIO_PHONE_NUMBER")  # Twilio phone number
# messaging_sid = fxs.get_config_key("TWILIO", False, "MESSAGING_SID")
# to_number = fxs.get_config_key("TWILIO", False, "CELL_NUMBER")  # Your phone number
# auth_token = fxs.get_config_key("TWILIO", False, "SECRET")
# account_sid = fxs.get_config_key("TWILIO", False, "SID")
#
# client = Client(account_sid, auth_token)
# # don't think I need this since I am updating the webhook 3 lines down
# # client.incoming_phone_numbers.list(phone_number = from_number)[0].update(sms_url = ngrok_tunnel_url)
#
# messaging_service = client.messaging.services(messaging_sid).fetch()
# messaging_service.update(inbound_request_url=ngrok_tunnel_url + "/sms", inbound_method="POST")
#
# # Start the Flask App
# app = Flask(__name__)
#
#
# @app.route("/")
# def root():
#     """
#     The function that will be called when the root directory is reached.
#     :param :
#     :return: A string containing text displaying the Ngrok tunnel url
#     """
#
#     return f"LANDING! prints to browser @ {ngrok_tunnel_url}"
#
#
# # go to sms to see this function at work
# @app.route("/sms")
# def sms():
#     """
#     The function that will be called when the SMS directory is reached
#     :param :
#     :return: A string containing text saying the function is working
#     """
#
#     return "This is your Twilio App Working!"
#
#
# @app.route("/sms", methods=['POST'])
# def handle_incoming():
#     """
#     Handles incoming sms messages and responds with Davinci's response
#     :param request: The question to be asked of Text-Davinci-3
#     :return: The message.sid value
#     """
#
#     # Get message from Twilio request
#     message = request.values.get('Body', None)
#     sender = request.values.get('From', None)
#
#     #     for k,v in request.values.items():
#     #         print(k, v)
#
#     print(f"Message: {message}\nSender: {sender}")
#
#     # Send message to OpenAI API
#     response = openai.Completion.create(engine="text-davinci-003",
#                                         prompt=f"{message}",
#                                         max_tokens=2048,
#                                         n=1,
#                                         stop=None,
#                                         temperature=0.5)
#
#     # Get the message response
#     message_response = response["choices"][0]["text"]
#
#     # Send response back to user's phone number via Twilio
#     message = client.messages.create(messaging_service_sid=messaging_sid,
#                                      body=message_response,
#                                      from_=from_number,
#                                      to=sender)
#
#     return message.sid
#
#
# if __name__ == "__main__":
#     # if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
#     #     start_ngrok(ngrok_url)
#
#     app.run(debug=False)
