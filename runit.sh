#!/bin/bash

# Clone the private Git repository using an access token
ACCESS_TOKEN="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"

REPO_URL="https://github.com/DJKC/TextGPT.git"
LOCAL_DIR="/home/ec2-user/Desktop/TextGPT"
FILE_TO_PULL="OpenAI.py"

# Clone the Git repository if it doesn't exist
if [ ! -d "$LOCAL_DIR" ]; then
    git clone https://${ACCESS_TOKEN}@${REPO_URL#https://} --branch master --single-branch "$LOCAL_DIR" -q
    if [ $? -ne 0 ]; then
        echo "Error: Git clone failed. Exiting..."
        exit 1
    fi
fi

# Pull and checkout the latest version of the specified file
cd "$LOCAL_DIR"
git pull origin master
git checkout origin/master -- "$FILE_TO_PULL"
if [ $? -ne 0 ]; then
    echo "Error: Git checkout failed. Exiting..."
    exit 1
fi

# Check if the specified file exists
if [ ! -f "$LOCAL_DIR/$FILE_TO_PULL" ]; then
    echo "Error: The specified file ($FILE_TO_PULL) was not found in $LOCAL_DIR. Exiting..."
    exit 1
fi

# Run the Python script
python3 "$LOCAL_DIR/OpenAI.py"
