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
# if ngrok tunnel error, use 78 - 80 to stop excess tunnels

import os
import sys
import json
import openai
import sqlite3
import hashlib
import logging
import platform
import requests
import pyperclip
from pyngrok import ngrok
from twilio.rest import Client
from flask import Flask, request


def get_config_key(_section_name=None, _secret_only=True, _key_name=None, _print=False):
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
    config.read("/Users/khallid/Documents/Coding/Python/CONFIG_APIS.ini")

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
            else:
                print(f"Key '{key_name}' not found in section '{section_name}'.")

        return config[section_name][key_name]


# OpenAI account information
openai.api_key = get_config_key("OPENAI")  # OpenAI API key

models = {"td3": "text-davinci-003",  # Large-scale text generation | high performance trained on internet text
          "td2": "text-davinci-002",  # Large-scale text generation | balance between performance and cost-effectiveness
          "cd2": "code-davinci-002",  # Code generation and programming language understanding
           "ta1": "text-ada-001",      # Text completion and answer generation  | trained on a diverse internet text and generating fluent human-like text
           "ccc": "curie",             # Text generation and question answering | focused on knowledge-based and conversational tasks
           "tc1": "text-curie-001",    # Text generation and language understanding | performs well on a wide range of natural language tasks
           "tb1": "text-babbage-001",  # Text generation and language modeling | more structured and technical text
           "cc1": "code-cushman-001",  # Code generation and completion | Balance between performance and cost-effectiveness
           "gpt": "gpt-3.5-turbo",
           "gpt1": "gpt-3.5-turbo-0301"}

question = None
while(question) != '':
    question = input("Ask away: ")

    if ':' not in question:
        model_set = "gpt"  # gpt-3.5-turbo-0301
    else:
        question, model_set = question.split(':')

    temp = 0.6
    max_tokens = 2000

    if model_set not in ["gpt", "gpt1"]:
        response = openai.Completion.create(n                   = 1,  # How many completions to generate for each prompt.
                                            user                = "0",
                                            stop                = None,  #
                                            top_p               = 1,
                                            # 0.1 means only the tokens comprising the top 10% probability mass are considered.
                                            prompt              = question,  #
                                            engine              = models[model_set],  #
                                            max_tokens          = max_tokens,
                                            # The maximum number of tokens to generate in the completion
                                            temperature         = temp,
                                            # Higher values, more risks. 1 very dynamic, 0 for well-defined static
                                            presence_penalty    = 0,
                                            # 0 and 2.0. Positive values penalize new tokens based on whether they appear in the text, increasing the model's likelihood to talk about new topics.
                                            frequency_penalty   = 0)  # 0 and 2.0. Positive values penalize new tokens based on existing frequency in text, decreasing the model's likelihood to repeat the same line verbatim.

        print(f'{model_set}: {response["choices"][0]["text"]}')
        print('*' * 50)

    elif model_set in ["gpt", "gpt1"]:
        response = openai.ChatCompletion.create(n                   = 1,  # How many completions to generate for each prompt.
                                                user                = "0",
                                                stop                = None,  #
                                                top_p               = 1,
                                                # 0.1 means only the tokens comprising the top 10% probability mass are considered.
                                                model               = models[model_set],  #
                                                max_tokens          = max_tokens,
                                                # The maximum number of tokens to generate in the completion
                                                temperature         = temp,
                                                # Higher values, more risks. 1 very dynamic, 0 for well-defined static
                                                presence_penalty    = 0,
                                                # 0 and 2.0. Positive values penalize new tokens based on whether they appear in the text, increasing the model's likelihood to talk about new topics.
                                                frequency_penalty   = 0,
                                                # logit_bias = {"506": 68},
                                                messages=[
                                                    {"role": "system", "content": "You are a helpful assistant."},
                                                    {"role": "user", "content": question}
                                                ]
        )

        print(f'{model_set}: {response.choices[0].message["content"]}')
        print('*' * 50)



