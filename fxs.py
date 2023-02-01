# A library of functions to handle personal repetitive tasks.

def get():
    """

    :param url:
    :return:
    """

    import pyperclip, requests

    url = str(pyperclip.paste())

    if "&fmt=json" not in url:
        url += "&fmt=json"

    r = requests.get(url)

    return r.text


def get(url):
    """

    :param url:
    :return:
    """

    import requests

    if "&fmt=json" not in url:
        url += "&fmt=json"

    r = requests.get(url)

    return r.text


def letterize(string):
    """
    Turns string into a number, a = 1, z = 26. Each number is the one's place added to the tens place. A = 1, z = 8
    :param string: The string to be turned into a number
    :return: The final number. Number of digits is equal to length of original string
    """

    key = "abcdefghijklmnopqrstuvwxyz"
    array = []

    for i in string:
        index = key.find(i) + 1

        array.append(index % 10 + index // 10)
        print(array[-1], end = " ")

    return array


def bookmark(string, copy = False, sep = ','):
    """
    Turns a series of words into a string of words separated by a comma. For Firefox bookmarks
    :param copy: copies to clipboard if copy = True
    :param string: The string made of words separated by spaces
    :return: A string of words separated by a comma
    """

    import pyperclip

    string = string.replace(" ", sep)

    if copy:
        pyperclip.copy()

    return string


def removeMoney(df):
    """
    Removes $ and , from a dataframe column string
    :param df: The dataframe to clean up
    :return: The original dataframe with $ and , removed
    """

    df = df.apply(lambda x: x.replace("$", ""))
    df = df.apply(lambda x: float(x.replace(",", "")))

    return df

def ocr(filepath):
    import cv2
    import pytesseract
    import PIL.ImageOps
    from PIL import Image, ImageEnhance

    filepath2 = ""

    i1 = cv2.imread(filepath)
    i1 = cv2.cvtColor(i1, cv2.COLOR_BGR2GRAY)

    cv2.imwrite("/Desktop/Screen.png", i1)

    img = Image.open(filepath2)
    factor = 5
    result = PIL.ImageOps.invert(img)
    result = ImageEnhance.Sharpness(result).enhance(factor)

    imageText = pytesseract.image_to_string(result)

def downloadYT(url):
    import os
    from pytube import YouTube
    from pytube.cli import on_progress

    dl_location = "/Users/khallid/Documents/Videos"

    try:
        yt = YouTube(url, on_progress_callback = on_progress)
        print("Video found.")

        try:
            stream = yt.streams.filter(progressive=True, resolution="1440p")[0]
            print("Using 1440p.")
        except:
            try:
                stream = yt.streams.filter(progressive=True, resolution="1080p")[0]
                print("Using 1080p.")
            except:
                stream = yt.streams.filter(progressive=True, resolution="720")[0]
                print("Using 720p.")

    except:
        print("Error getting video, exit:")

    os.chdir(dl_location)
    stream.download()


def unlock_pdf(files):
    """


    :param files:
    :return:
    """

    import pikepdf

    for i in files:
        pdf = pikepdf.open(i)
        pdf.save(f"x_{i}")

def get_config_key(_section_name = None, _secret_only = True, _key_name = None, _print = False):
    """
    Return the secret corresponding to the section selected

    :param _section_name: The section for which to ge the key
    :param _secret_only: Return the secret only
    :param _key_name: The name of the key to return
    :return: The key to return
    """

    import configparser
    import logging

    logger = logging.getLogger()

    # Set the logging levelS
    if(not _print):
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)

    config = configparser.ConfigParser()
    config.read('')

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

if __name__ == "__main__":
    print("Welcome")