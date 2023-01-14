import discord
from discord.ext import commands
from helper import guildOptions

import re
import os,sys
import traceback

from spotdl import Spotdl

# Instaintiate spotdl . make sure the credentials are working
try:
    spotdl = Spotdl(
        client_id=os.getenv('SPOTIPY_CLIENT_ID',None).strip(),
        client_secret=os.getenv('SPOTIPY_CLIENT_SECRET',None).strip()
    )
except Exception:
    print("Need to specify Spotify Credintials (SPOTIPY_CLIENT_ID,SPOTIPY_CLIENT_SECRET)\n" +
          "using an Environment Variable \n" +
          "On linux that can be achieved like this\n" +
          "export SPOTIPY_CLIENT_ID=\"xxxx\"\n" +
          "export SPOTIPY_CLIENT_SECRET=\"xxxx\""
          )
    sys.exit(1)


# TODO - Sanatize inputs ***Urgent
# TODO - Lyrics

# TODO - use the song metadata , show it to the users preferably using embeds

# TODO - permissions to use the functions [Guild->member->permissions]
# TODO - benchmark [profile] the FFmpegPCM function and replace it with opus if necessary
# TODO - create a single thread or instance of FFmpeg for each guild . don't restart the process with each song
# TODO - Download YT-files to disk and make a list of all files here to not download twice and faster seek
# TODO - Logging
# TODO - make a dislike command that can help identify problems with the output of spotdl [Japanese songs are one example]
# TODO - create a DB of songName->YtMusic Link and couple it with the file cache
# TODO - figure out a way to create some sort of a mixer [default presets maybe] --Zach
# TODO - Song guessing game ******* [ranking] --Zach
# TODO - keep track of each user prefernces and old tracks [User profile/Playlists/Songs]


# some weirda$$ variable names that you might encounter so a bit of a headsup [any help in refactoring this mess would be appreciated]
# GO     GuildOptions        It contains the variables for each guild
# gID    Author guild ID     pretty self explanatory :p it is the author(the one issuing the command)'s guild(current guild)'s ID

from yt_dlp import YoutubeDL


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # state variables
        self.go = {}
        for guild in self.bot.guilds:
            # Guild_Options
            self.go[guild.id] = guildOptions()
            

    async def search_spotdl(self, ctx, item):
        # print("Guild_Name: ",ctx.author.guild.name," ",item)
        songs = spotdl.search([item])
        # print("Guild_Name: ",ctx.author.guild.name," ",[song.artist for song in songs])
        try:
            #get_download_urls takes multiple song names and returns multiple urls as well . hence JUST the first item 
            songUrl = spotdl.get_download_urls(songs)[0]
            return songUrl
        except IndexError:
            await ctx.send("Spotdl shat the bed , trying yt-dlp directly. hold on boys")
            return None
        

    # searching the item on youtube

    async def get_song_yt(self, ctx, item,itemType):
        #itemType is gonna be either a url or a songName as the user inputs it
        
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]
        
        with YoutubeDL(guildOptions.YDL_OPTIONS) as ydl:
            try:
                
                if itemType == 'url':
                    info = ydl.extract_info(item, download=False)
                elif itemType == 'query':
                    #TODO . get the first match that you find fix it later
                    info = ydl.extract_info("ytsearch:%s" % item, download=False)["entries"][0]
                    
                # get only the audios - already sorted by worst to best so taking the last
                # format is gonna be enough . no need to sort or do anything else really
                info["formats"] = [f for f in info["formats"] if f.get("audio_ext") != 'none']

            except Exception:
                traceback.print_exc()
                await ctx.send("yt-dlp shat the bed as well , Sorry boys . maybe a Full Youtube Link is gonna work")
                return None
            
        # Debug Statments
        print("Guild_Name: ", ctx.author.guild.name," ", 
              "yt-video ID: "       ,info["id"],"\n",
              "yt-video title: "    ,info["title"])
        # print("Guild_Name: ",ctx.author.guild.name," ","Chosen Format: ",info['formats'][-1])
        return {
            'source': info['formats'][-1]['url'],
            'title': info['title']
        }

    async def tryConnectVc(self,ctx):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]
        
        # try to connect to voice channel if you are not already connected
        if guildOptions.vc == None or not guildOptions.vc.is_connected():
            guildOptions.vc = await guildOptions.current_song[1].connect()

            # in case we fail to connect
            if guildOptions.vc == None:
                await ctx.send("Could not connect to the voice channel")
                return
        else:
            await guildOptions.vc.move_to(guildOptions.current_song[1])
    
    def play_next(self, ctx):
        #sync version of play_music without the VC connect abilities
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]
        
        if len(guildOptions.music_queue) > 0 or (guildOptions.loop and guildOptions.current_song):
            guildOptions.is_playing = True

            if not (guildOptions.loop and guildOptions.current_song):
                guildOptions.current_song = guildOptions.music_queue.pop(0)
                
            m_url = guildOptions.current_song[0]['source']
              
            
            # await ctx.send("Starting to play ```css\n\'",guildOptions.current_song[0]['title']+"\'")
            guildOptions.vc.play(discord.FFmpegPCMAudio(
                m_url, **guildOptions.FFMPEG_OPTIONS), 
                after=lambda e: self.play_next(ctx))
            
        else:
            guildOptions.is_playing = False
            guildOptions.current_song=None
    
    # infinite loop checking
    async def play_music(self, ctx):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]
        
        if len(guildOptions.music_queue) > 0 or (guildOptions.loop and guildOptions.current_song):
            guildOptions.is_playing = True
            
            
            #Nand loop,current_song .. look up the truth table . this was annoying ngl xD
            if not (guildOptions.loop and guildOptions.current_song):
                guildOptions.current_song = guildOptions.music_queue.pop(0)
            
            await self.tryConnectVc(ctx)

            m_url = guildOptions.current_song[0]['source']
            
            await ctx.send("Starting to play \n```css\n["+guildOptions.current_song[0]['title']+"]\n```")
            guildOptions.vc.play(discord.FFmpegPCMAudio(
                m_url, **guildOptions.FFMPEG_OPTIONS), 
                after=lambda e: self.play_next(ctx))
        else:
            guildOptions.is_playing = False
            guildOptions.current_song=None

    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]

        # if the first condition is None then python wouldn't even evaluate the second condition
        if ctx.author.voice and ctx.author.voice.channel:
            voice_channel = ctx.author.voice.channel

            if guildOptions.is_paused:
                guildOptions.vc.resume()
            else:
                query = " ".join(args)

                # TODO - this is just a workaround to get the bot to accept yt/ytMusic links
                # test ".p https://www.youtube.com/watch?v=EORgrmt2cR0"
                regex = '^((?:https?:)?\/\/)?((?:www|m|music)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$'
                x = re.search(regex, query.strip())
                
                if not x:
                    songUrl = await self.search_spotdl(ctx, query)

                song = await self.get_song_yt(ctx, x.string if x else (songUrl or query) ,"url" if x else "query")
                            
                if not song:
                    await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
                else:
                    await ctx.send("Song added to the queue")
                    guildOptions.music_queue.append([song, voice_channel])

                    if guildOptions.is_playing == False:
                        await self.play_music(ctx)
        else:
            await ctx.send("Connect to a voice channel!")

    @commands.command(name="pause", aliases=["pa"], help="Pauses the current song being played")
    async def pause(self, ctx):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]

        if      guildOptions.is_playing:
                guildOptions.is_playing    = False
                guildOptions.is_paused     = True
                guildOptions.vc.pause()
        elif    guildOptions.is_paused:
                guildOptions.is_paused     = False
                guildOptions.is_playing    = True
                guildOptions.vc.resume()

    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]

        if  guildOptions.is_paused:
            guildOptions.is_paused = False
            guildOptions.is_playing = True
            guildOptions.vc.resume()

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]

        if guildOptions.vc:
            #skip the current_song
            if (guildOptions.loop and guildOptions.current_song):
                guildOptions.current_song = guildOptions.music_queue.pop(0)
                
            guildOptions.vc.stop()
            # try to play next in the queue if it exists
            await self.play_music(ctx)


    def createQueueText(self,ctx):
        
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]
        
        #if there's a current song . show it in the queue
        retval = guildOptions.current_song[0]['title'] if guildOptions.current_song else ""
        
        #if the current song is looped add in an infinity sign . if not add in a left arrow sign
        retval += u" \t\u221E\n" if (guildOptions.loop and guildOptions.current_song) else ""
        retval += u" \t\u2190\n" if ((not guildOptions.loop) and guildOptions.current_song) else ""
        
        for i in range(0, len(guildOptions.music_queue)):
            # display a max of 5 songs in the current queue
            if (i > 4):
                break
            retval += guildOptions.music_queue[i][0]['title'] + "\n"
            
        return retval
        
    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        
        retval = self.createQueueText(ctx)
       
        if retval:
            await ctx.send(retval)
        else:
            await ctx.send("No music in queue")
            
        return retval

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]

        if guildOptions.vc != None and guildOptions.is_playing:
            guildOptions.vc.stop()
        guildOptions.music_queue = []
        guildOptions.current_song = None
        await ctx.send("Music queue cleared")

    @commands.command(name="disconnect", aliases=["leave", "d", "dc"], help="Kick the bot from VC")
    async def dc(self, ctx):
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]

        guildOptions.is_playing = False
        guildOptions.is_paused = False
        guildOptions.current_song=None
        await guildOptions.vc.disconnect()

    @commands.command(name="speed")
    async def speed(self, ctx, speed):
        # guildOptions.FFMPEG_OPTIONS["options"] = "-vn -af atempo=" + str(speed)
        try:
            gID = ctx.author.guild.id
            guildOptions = self.go[gID]
            
            # making sure that speed actually contains a float
            print("Guild_Name: ", ctx.author.guild.name, " ",
                  "type(speed)= ", type(speed), "float(speed)= ", float(speed))
            # making sure that speed is between a 0.5-100.0
            assert float(speed) >= 0.5 and float(speed) <= 100.0

            guildOptions.FFMPEG_OPTIONS["options"] = "-vn -af atempo=" + \
                str(float(speed))
        except:
            print("Guild_Name: ", ctx.author.guild.name, " ",
                  "There has been an issue with the speed command")
            return
        
    @commands.command(name="loop",aliases=["l"])
    async def loop(self, ctx, value='on'):
        
        gID = ctx.author.guild.id
        guildOptions = self.go[gID]
        
        if value =='on':
            guildOptions.loop = True
        elif value =='off':
            guildOptions.loop = False
        else:
            guildOptions.loop= not guildOptions.loop
        

    @commands.command(name="guild_options")
    async def guild_options(self, ctx):

        gID = ctx.author.guild.id
        guildOptions = self.go[gID]
        
        retVal = ""
        retVal += "Guild_name"+         str(ctx.author.guild.name)+'\n'
        retVal += "Guild_ID"+           str(ctx.author.guild.id)+'\n'
        retVal += "is_playing: " +      str(guildOptions.is_playing)+"\n"
        retVal += "is_paused: " +       str(guildOptions.is_paused)+"\n"
        retVal += "music_queue: " +     str("\n"+"\n".join(["\t" +line for line in self.createQueueText(ctx).split("\n")][:-1]))+"\n"
        retVal += "loop: " +            str(guildOptions.loop)+"\n"
        retVal += "vc: " +              str(guildOptions.vc)+"\n"
        # retVal += "\nYDL_OPTIONS: " +     str(guildOptions.YDL_OPTIONS)+"\n"
        retVal += "FFMPEG_OPTIONS: " +  str(guildOptions.FFMPEG_OPTIONS)+"\n"
        retVal += "current_song: " +    str(guildOptions.current_song[0]['title'] if guildOptions.current_song else None)

        await ctx.send(retVal)