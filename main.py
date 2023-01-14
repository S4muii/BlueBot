import discord
from discord.ext import commands
from help_cog import help_cog
from music_cog import music_cog
import asyncio
import os,sys

class MyBot(commands.Bot):
    
    
    async def on_ready(self):
        print(f'Logged on as {self.user}!')
        
    async def on_guild_join(self,guild):
        print('Bot has been added to a new server',guild.name)
        
''' 
       
#this is just an event . another way to do this would be like this 
@bot.event
async def on_ready():
    print('Ready!')
    
@bot.event
async def on_guild_join(guild):
    print('Bot has been added to a new server',guild.name)
    
'''

        
DiscordBotToken = os.getenv('DiscordBotToken',None).strip()
print("DiscordBotToken is: ",DiscordBotToken)

if not DiscordBotToken:    
    print("Need to specify DiscordBotToken using an Environment Variable \n"+
          "On linux that can be achieved like this\n"+
          "export DiscordBotToken=\"xxxx\""
          )
    sys.exit(1)


intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

loop = asyncio.get_event_loop()

bot = MyBot(command_prefix=".",intents=intents)

#remove the original help command which actually is pretty nice
bot.remove_command('help')
loop.run_until_complete(bot.add_cog(help_cog(bot)))
loop.run_until_complete(bot.add_cog(music_cog(bot)))
   

bot.run(DiscordBotToken)
