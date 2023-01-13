import discord
from discord.ext import commands
from help_cog import help_cog
from music_cog import music_cog
import asyncio
import os,sys

class MyBot(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        
try:
    print("DiscordBotToken is: ",os.environ['DiscordBotToken'])
except:
    print("Need to specify DiscordBotToken using an Environment Variable \n"+
          "On linux that can be achieved like this\n"+
          "export DiscordBotToken=\"xxxx\""
          )
    sys.exit(1)


intents = discord.Intents.default()
intents.message_content = True

loop = asyncio.get_event_loop()

bot = MyBot(command_prefix=".",intents=intents)

#remove the original help command which actually is pretty nice
bot.remove_command('help')
loop.run_until_complete(bot.add_cog(help_cog(bot)))
loop.run_until_complete(bot.add_cog(music_cog(bot)))

bot.run(os.environ["DiscordBotToken"])
