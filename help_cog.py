from discord.ext import commands

class help_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.help_message = """
```
General commands:
    .help   [h]                 - displays all the available commands
    .play   [p] {keyword|url}   - finds the song on youtube and plays it in your current channel.
    .queue  [q]                 - displays the current music queue
    .skip   [s]                 - skips the current song being played
    .clear  [c]                 - Stops the music and clears the queue
    .leave  [l]                 - Disconnected the bot from the voice channel
    .pause  [pa]                - pauses the current song being played or resumes if already paused
    .resume [r]                 - resumes playing the current song
    .speed      {0.1>float<2.0} - changes the speed of the audio
```
"""
        self.text_channel_list = []

    #some debug info so that we know the bot has started    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                self.text_channel_list.append(channel)

        await self.send_to_all(self.help_message)        

    @commands.command(name="help",aliases=["h"], help="Displays all the available commands")
    async def help(self, ctx):
        await ctx.send(self.help_message)

    async def send_to_all(self, msg):
        for text_channel in self.text_channel_list:
            await text_channel.send(msg)