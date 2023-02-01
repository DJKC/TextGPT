# Makes a prompt request to Text_DaVinci-3 using Twilio, Ngrok and Flask

##################################################################################################################################################
# HELPFUL LINKS
# https://console.twilio.com/us1/develop/phone-numbers/manage/incoming?frameUrl=%2Fconsole%2Fphone-numbers%2Fincoming%2FPN43550d505a24d5283e6b7b65f76b2333%3Fx-target-region%3Dus1
# A message comes in, set webhook here, for individual phone numbers

# https://console.twilio.com/us1/service/sms/MG40c519a5b8acb936be5f0c92c3957808/sms-service-instance-configure?frameUrl=%2Fconsole%2Fsms%2Fservices%2FMG40c519a5b8acb936be5f0c92c3957808%3Fx-target-region%3Dus1
# Set webhook for incoming messages, for messaging service

# https://www.toptal.com/developers/postbin/

# https://dashboard.ngrok.com/
##################################################################################################################################################

import os
import fxs
import twilio
import openai
from pyngrok import ngrok
from twilio.rest import Client
from flask import Flask, request, redirect
from twilio.twiml.messaging_response import MessagingResponse

# OpenAI account information
openai.api_key = fxs.get_config_key("OPENAI") # OpenAI API key

# Ngrok tunnel start
ngrok.set_auth_token(fxs.get_config_key("NGROK"))
ngrok_tunnel_url = ngrok.connect(5000).public_url
print(f"Tunnel Created at {ngrok_tunnel_url}")

# Twilio account information
from_number   = fxs.get_config_key("TWILIO", False, "TWILIO_PHONE_NUMBER") # Twilio phone number
messaging_sid = fxs.get_config_key("TWILIO", False, "MESSAGING_SID")
to_number     = fxs.get_config_key("TWILIO", False, "CELL_NUMBER") # Your phone number
auth_token    = fxs.get_config_key("TWILIO", False, "SECRET")
account_sid   = fxs.get_config_key("TWILIO", False, "SID")

client        = Client(account_sid, auth_token)
# don't think I need this since I am updating the webhook 3 lines down
# client.incoming_phone_numbers.list(phone_number = from_number)[0].update(sms_url = ngrok_tunnel_url)

messaging_service = client.messaging.services(messaging_sid).fetch()
messaging_service.update(inbound_request_url = ngrok_tunnel_url + "/sms", inbound_method = "POST")

# Start the Flask App
app = Flask(__name__)


@app.route("/")
def root():
    """
    The function that will be called when the root directory is reached.

    :param :
    :return: A string containing text displaying the Ngrok tunnel url
    """

    return f"LANDING! prints to browser @ {ngrok_tunnel_url}"


# go to sms to see this function at work
@app.route("/sms")
def sms():
    """
    The function that will be called when the SMS directory is reached

    :param : 
    :return: A string containing text saying the function is working
    """
    
    return "This is your Twilio App Working!"


@app.route("/sms", methods = ['POST'])
def handle_incoming():
    """
    Handles incoming sms messages and responds with Davinci's response

    :param request: The question to be asked of Text-Davinci-3
    :return: The message.sid value
    """

    # Get message from Twilio request
    message = request.values.get('Body', None)
    sender  = request.values.get('From', None)

#     for k,v in request.values.items():
#         print(k, v)

    print(f"Message: {message}\nSender: {sender}")

    # Send message to OpenAI API
    response = openai.Completion.create(engine      = "text-davinci-003",
                                        prompt      = f"{message}",
                                        max_tokens  = 2048,
                                        n           = 1,
                                        stop        = None,
                                        temperature = 0.5)

    # Get the message response
    message_response = response["choices"][0]["text"]

    # Send response back to user's phone number via Twilio
    message   = client.messages.create(messaging_service_sid = messaging_sid,
                                       body                  = message_response,
                                       from_                 = from_number,
                                       to                    = sender)

    return message.sid


if __name__ == "__main__":
    # if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
    #     start_ngrok(ngrok_url)

    app.run(debug = False)
