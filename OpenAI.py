# Connects to a user to Text-Davinci-3 through Twilio and OpenAi to ask a question and receive an answer

# https://platform.openai.com/docs/models/gpt-3-5?utm_medium=email&_hsmi=248356722&utm_content=248356722&utm_source=hs_email

# https://console.twilio.com/us1/develop/phone-numbers/manage/incoming?frameUrl=%2Fconsole%2Fphone-numbers%2Fincoming%2FPN43550d505a24d5283e6b7b65f76b2333%3Fx-target-region%3Dus1
#      A message comes in, set webhook here, for individual phone numbers
# https://console.twilio.com/us1/service/sms/MG40c519a5b8acb936be5f0c92c3957808/sms-service-instance-configure?frameUrl=%2Fconsole%2Fsms%2Fservices%2FMG40c519a5b8acb936be5f0c92c3957808%3Fx-target-region%3Dus1
#      Set webhook for incoming messages, for messaging service
# https://www.toptal.com/developers/postbin/
# https://dashboard.ngrok.com/
# https://platform.openai.com/docs/api-reference/moderations/create
# https://platform.openai.com/tokenizer?view=bpe
# https://platform.openai.com/docs/api-reference/images/create


# TO-DO
# If an invalid model is processed in line 294, no text messages is sent the user, set q default
# 253
#     take advanced parameters in any order
# make into a class
# add image generation to database with url
# if ngrok tunnel error, use 86 - 88 to stop excess tunnels
# Add text editing functionality
#   https://platform.openai.com/docs/api-reference/edits/create
# If error causes request not be sent, save request and send again successfully.
# Prompt injection

import os
import sys
import json
import openai
import sqlite3
import hashlib
import logging
import platform
import requests
import tiktoken
import pyperclip
from pyngrok import ngrok
from twilio.rest import Client
from flask import Flask, request
from transformers import GPT2TokenizerFast


class TextGPT:
    def __init__(self):
        # Set up logging for pyngrok and twilio
        # NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL
        # logging.basicConfig(filename='log.txt', level=logging.DEBUG, filemode='w', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.app = Flask(__name__)
        self.first_run = True
        self.message_log = {}

        logging.basicConfig(level=logging.WARNING, filemode='w',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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

        self.CONFIG_FILE = {
            DIRS["Linux"]: "/home/ec2-user/CONFIG_APIS.ini",
            DIRS["Darwin"]: "/Users/khallid/Documents/Coding/Python/CONFIG_APIS.ini",
        }.get(BASE_DIR, "")

        try:
            os.chdir(BASE_DIR)
            print(f"Success, current {os.getcwd()}")
        except:
            print(f"{BASE_DIR} not found, currently in {os.getcwd()}")

        print(f"Config directory:  {self.CONFIG_FILE}")

        # OpenAI account information
        openai.api_key = self.get_config_key("OPENAI")  # OpenAI API key

        # Ngrok tunnel start
        ngrok.set_auth_token(self.get_config_key("NGROK"))
        ngrok_tunnel_url = ngrok.connect(5000).public_url
        print(f"Tunnel Created at {ngrok_tunnel_url}")

        # The below won't work due to free tier limitation on number instances that can be actively run
        # try:
        #     ngrok_tunnel_url = ngrok.connect(5000).public_url
        # except:
        #     ngrok.kill()
        #     ngrok.disconnect(ngrok_tunnel_url)
        #     ngrok_tunnel_url = ngrok.connect(5000).public_url
        # finally:
        #     pass

        # Twilio account information
        self.from_number = self.get_config_key("TWILIO", False, "TWILIO_PHONE_NUMBER")  # Twilio phone number
        self.messaging_sid = self.get_config_key("TWILIO", False, "MESSAGING_SID")
        auth_token = self.get_config_key("TWILIO", False, "SECRET")
        account_sid = self.get_config_key("TWILIO", False, "SID")

        self.client = Client(account_sid, auth_token)

        self.messaging_service = self.client.messaging.services(self.messaging_sid).fetch()
        self.messaging_service.update(inbound_request_url=ngrok_tunnel_url + "/sms", inbound_method="POST")

        self.models = {"td3": "text-davinci-003",  # Large-scale text generation | high performance trained on internet text
                       "td2": "text-davinci-002",  # Large-scale text generation | balance between performance and cost-effectiveness
                       # "cd2": "code-davinci-002",  # Code generation and programming language understanding !!! Discontinued
                       "ta1": "text-ada-001",      # Text completion and answer generation  | trained on a diverse internet text and generating fluent human-like text
                       "ccc": "curie",             # Text generation and question answering | focused on knowledge-based and conversational tasks
                       "tc1": "text-curie-001",    # Text generation and language understanding | performs well on a wide range of natural language tasks
                       "tb1": "text-babbage-001"}  # Text generation and language modeling | more structured and technical text
                       # "cc1": "code-cushman-001"}  # Code generation and completion | Balance between performance and cost-effectiveness  !!! Discontinued


        @self.app.route("/sms", methods=['POST'])
        def handle_incoming():
            """
            User text messages received from Twilio are routed to Text-Davinci-003 and response is sent back to user

            # :param request: The question to be asked of OpenAI model
            :return: The message.sid value
            """

            # Get message from Twilio request
            question = request.values.get('Body', None)
            sender = request.values.get('From', None)
            user = request.values["From"]  # This should be hashed for privacy and security
            user_hash = hashlib.sha256(user.encode()).hexdigest()
            sender_hash = hashlib.sha256(sender.encode()).hexdigest()

            # Extract temperature and max tokens from message, if they exist
            temperature = 0.5
            max_tokens = 200
            model_set = "td3"

            # request.values.items()
            # {
            #     "ToCountry": "US",
            #     "ToState": "NJ",
            #     "SmsMessageSid": "SM7f93b4c435808e381abc763c79059d4d",
            #     "NumMedia": "0",
            #     "ToCity": "NEWARK",
            #     "FromZip": "92506",
            #     "SmsSid": "SM7f93b4c435808e381abc763c79059d4d",
            #     "FromState": "CA",
            #     "SmsStatus": "received",
            #     "FromCity": "RIVERSIDE",
            #     "Body": "When was GPT 1.5 released?",
            #     "FromCountry": "US",
            #     "To": "+19737918518",
            #     "MessagingServiceSid": "MG40c519a5b8acb936be5f0c92c3957808",
            #     "ToZip": "07105",
            #     "NumSegments": "1",
            #     "MessageSid": "SM7f93b4c435808e381abc763c79059d4d",
            #     "AccountSid": "AC35cf8442aefc62b1f2fc53985841ae7e",
            #     "From": "+19512339033",
            #     "ApiVersion": "2010-04-01",
            # }

            # print(f"Message: {message}\nSender: {sender}")

            print("Message received from", request.values["From"])

            tapback_filters = ["Loved \"",
                               "Liked \"",
                               "Disliked \""
                               "Laughed at \"",
                               "Emphasized \"",
                               "Questioned \"", ]

            for tapback in tapback_filters:
                # Do not do anything
                pass

            if (question.startswith("$$")):
                help_message = "::temp:max_tokens | @@ for image | $$ for help | !! for ChatGPT | Else TextDavinci3"

                response_message = self.client.messages.create(messaging_service_sid=self.messaging_sid,
                                                               body=help_message,
                                                               from_=self.from_number,
                                                               to=sender)

            if (question.startswith("!!")):
                model_set = "gpt-3.5-turbo"

                # user_prompt_general = {"role":  "user", "content": None}

                prompt_message = {"role": "system", "content": "You are a very knowledgeable and helpful friend, many people will ask you for help and advice "
                                                               "because you explain complicated concepts simply"}
                user_next_prompt = {"role": "user", "content": question[2:]}

                # message_log = [prompt_message, user_next_prompt]

                if self.first_run:
                    self.message_log = [prompt_message, user_next_prompt]
                    self.first_run = False

                else:
                    if self.message_log is {}:
                        print("Error with message log in post first run       ")
                    else:
                        self.message_log += [user_next_prompt]

                response = openai.ChatCompletion.create(model=model_set,  # models[model_set],
                                                        max_tokens=100,
                                                        messages=self.message_log
                                                        )

                assistant_response = dict(response.choices[0].message)
                self.message_log += [assistant_response]

                print(f'{model_set}: {assistant_response["content"]}\n\n')

                for x in self.message_log:
                    print(f'[{x["role"]}]')
                    print(x["content"])
                    print('*' * 10)

                print('*' * 50)

                first_run = False

                response_message = self.client.messages.create(messaging_service_sid=self.messaging_sid,
                                                               body=assistant_response["content"],
                                                               from_=self.from_number,
                                                               to=sender)


                return "sid"

            if "@@" in question:
                import requests

                question = question.replace("@@", "")

                ##########################################################################################################

                # Define the API endpoint
                endpoint = "https://api.openai.com/v1/images/generations"

                # Define the text description of the image you want to generate
                description = question

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

                    ##########################################################################################################

                    response_message = self.client.messages.create(messaging_service_sid=self.messaging_sid,
                                                                   body=image_url,
                                                                   from_=self.from_number,
                                                                   to=sender)

                else:
                    pass

                return "sid"

            else:
                if "::" in question:
                    params = question.split("::")[1]
                    question = question.split("::")[0]

                    if ' ' in params:
                        params = params.replace(' ', '')

                    parameters = params.split(":")
                    temperature = float(parameters[0])

                    try:
                        model_set = str(parameters[1])

                        try:
                            max_tokens = int(parameters[2])
                        except:
                            print("No third parameter")
                    except:
                        print("No second parameter")

                print(f"{temperature} | {model_set} | {max_tokens}")

                print(question)
                # Send message to OpenAI API
                response = openai.Completion.create(n=1,  # How many completions to generate for each prompt.
                                                    user=user_hash,  # string representing a user
                                                    stop=None,  #
                                                    top_p=1,
                                                    # 0.1 means only the tokens comprising the top 10% probability mass are considered.
                                                    prompt=question,  #
                                                    engine=self.models[model_set],  #
                                                    max_tokens=max_tokens,
                                                    # The maximum number of tokens to generate in the completion
                                                    temperature=temperature,
                                                    # Higher values, more risks. 1 very dynamic, 0 for well-defined static
                                                    presence_penalty=0,
                                                    # 0 and 2.0. Positive values penalize new tokens based on whether they appear in the text, increasing the model's likelihood to talk about new topics.
                                                    frequency_penalty=0)  # 0 and 2.0. Positive values penalize new tokens based on existing frequency in text, decreasing the model's likelihood to repeat the same line verbatim.

                # Get the message response
                try:  # for 3.9
                    message_response = response["choices"][0]["text"].removeprefix('?').lstrip()  # + f"[{params}]"
                except:  # for 3.7
                    message_response = response["choices"][0]["text"].lstrip('?').lstrip()  # + f"[{params}]"

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
                response_message = self.client.messages.create(messaging_service_sid=self.messaging_sid,
                                                               body=message_response,
                                                               from_=self.from_number,
                                                               to=sender)

                # Extract data from response object
                finish_reason = response['choices'][0]['finish_reason']
                response_id = response['id']
                token_data = response["usage"]

                # Insert these values into db: user_id, prompt, response, temperature, max_tokens, timestamp, model, finish_reason, sender, id
                database_values = [question, message_response, temperature, response["model"],
                                   max_tokens, int(token_data["completion_tokens"]), int(token_data["prompt_tokens"]),
                                   int(token_data["total_tokens"]), user_hash, int(response["created"]), response_id,
                                   finish_reason, sender_hash]

                self.create_database()

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

    def get_tokenID(word):
        """
        Gets the token id for string to be tokenized, used with the logit_bias parameter

        :param word: Word to be tokenized
        :return: Integers representing the token id
        """

        # https://huggingface.co/docs/transformers/model_doc/gpt2#transformers.GPT2TokenizerFast

        tokenizer = GPT2TokenizerFast.from_pretrained("gpt2")
        id = tokenizer(word)["input_ids"][0]

        return id


    def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
        """
        Returns the number of tokens used by a list of messages

        :param messages: List of json objects containing the chat message log
        :param model: the model being used for the conversation
        :return: Number of tokens used by conversation
        """

        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")

        if model == "gpt-3.5-turbo":  # note: future models may deviate from this
            num_tokens = 0

            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n

                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))

                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token

            num_tokens += 2  # every reply is primed with <im_start>assistant

            return num_tokens

        else:
            raise NotImplementedError(f"""num_tokens_from_messages() is not available for model {model}. See
                                          https://github.com/openai/openai-python/blob/main/chatml.md for
                                          information on how messages are converted to tokens.""")


    def get_config_key(self, _section_name=None, _secret_only=True, _key_name=None, _print=False):
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
        config.read(self.CONFIG_FILE)

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


    def create_database(self):
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


    def get_twilio_balance(self):
        sid = self.get_config_key("TWILIO", False, "SID")
        auth = self.get_config_key("TWILIO")
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Balance.json"
        balance = json.loads(requests.get(url, auth=(sid, auth)).content)["balance"]

        return balance


    def run(self):
        """

        :return:
        """
        self.app.run()


#from TextGPT import TextGPT

if __name__ == "__main__":
    # Start the Flask App

    # Setting this to True makes Ngrok use more than one tunnel and breaks free version
    # app.debug = False
    instance = TextGPT()
    instance.run()

"""
I wrote an application where users can send text messages and receive an automated response, also as a text message.

The application is built but now I want to create a website. I would the website to have text message animation in the background showing different examples of the conversations people have had. For example, there will be a text message bubble that pops up (containing the user's question) and then another bubble will appear underneath the previous one (containing the response text) and both text bubbles will move up. I have also create two bubble images, one for the user and one for the program's response.

How can I create this animation on my website?

"""

"""
Message received from +19512339033
0.5 | td3 | 200
What is gpt-6?
2023-03-27 09:25:56,498 - OpenAI - ERROR - Exception on /sms [POST]
Traceback (most recent call last):
  File "/home/ec2-user/.local/lib/python3.7/site-packages/flask/app.py", line 2525, in wsgi_app
    response = self.full_dispatch_request()
  File "/home/ec2-user/.local/lib/python3.7/site-packages/flask/app.py", line 1822, in full_dispatch_request
    rv = self.handle_user_exception(e)
  File "/home/ec2-user/.local/lib/python3.7/site-packages/flask/app.py", line 1820, in full_dispatch_request
    rv = self.dispatch_request()
  File "/home/ec2-user/.local/lib/python3.7/site-packages/flask/app.py", line 1796, in dispatch_request
    return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)
  File "/home/ec2-user/Desktop/TextGPT/OpenAI.py", line 360, in handle_incoming
    frequency_penalty=0)  # 0 and 2.0. Positive values penalize new tokens based on existing frequency in text, decreasing the model's likelihood to repeat the same line verbatim.
  File "/home/ec2-user/.local/lib/python3.7/site-packages/openai/api_resources/completion.py", line 25, in create
    return super().create(*args, **kwargs)
  File "/home/ec2-user/.local/lib/python3.7/site-packages/openai/api_resources/abstract/engine_api_resource.py", line 160, in create
    request_timeout=request_timeout,
  File "/home/ec2-user/.local/lib/python3.7/site-packages/openai/api_requestor.py", line 227, in request
    resp, got_stream = self._interpret_response(result, stream)
  File "/home/ec2-user/.local/lib/python3.7/site-packages/openai/api_requestor.py", line 624, in _interpret_response
    stream=False,
  File "/home/ec2-user/.local/lib/python3.7/site-packages/openai/api_requestor.py", line 681, in _interpret_response_line
    rbody, rcode, resp.data, rheaders, stream_error=stream_error
openai.error.RateLimitError: The server had an error while processing your request. Sorry about that!
"""