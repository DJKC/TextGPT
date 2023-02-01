import os
import openai
from configparser import ConfigParser

config = ConfigParser()

openai.api_key = config["OPENAI"]["KEY"]

prompt = input("Prompt: ")

models = ["text-davinci-003",
          "text-babbage-001",
          "text-curie-001",
          "text-ada-001",
          "text-davinci-003",
          "text-davinci-003",
          "text-davinci-003",
          "text-davinci-003",
          "text-davinci-003",
          "code-davinci-002",
          "code-cushman-001",

]

response = openai.Completion.create(
  model             = "text-davinci-003",
  top_p             = 1,
  prompt            = "",
  temperature       = 0.7, # Randomness 0 - 1, approaching 0 gives repetitive results
  max_tokens        = 256,
  presence_penalty  = 0,
  frequency_penalty = 0
)
