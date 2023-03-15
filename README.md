# BlueBot

- Steps to run the Bot in your environment
* assumes that you're running Linux or a Unix like system
+ assumes that you created a bot on the Discord dev portal
- and a client APP on the spotify dev portal as well
* most of all .. just HAVE FUN xD


```bash
# Install venv ; Make a new virtual environment ; Use it
python3 -m pip install venv
python3 -m venv BlueBotVenv
source ./BlueBotVenv/bin/activate

# Adding the environment variables necessary for the bot to work
# You'll need a Discord token from the Discord dev portal
# and a Spotify client ID and secret from the Spotify dev portal

export SPOTIPY_CLIENT_ID="xxx"
export SPOTIPY_CLIENT_SECRET="xxx"
export DiscordBotToken="xxx"

python3 -m pip install -r requirements.txt
python3 main.py
```
