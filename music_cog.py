import discord
from discord.ext import commands

import asyncio

import re
import os,sys

#reddit meme downloader
import praw
import random

reddit = praw.Reddit("bot")
print(f"[Reddit] Logged in as {reddit.user.me()}!")


from helper import guildOptions,SongsTempDir

#from spotdl.providers.lyrics.azlyrics import AzLyrics
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


"""patch to MusixMatch lyrics
    spotdl.provider.lyrics.musixmatch.py
    49:search_url = f"https://www.musixmatch.com/search/{query}/tracks"
"""


# TODO - Sanatize inputs ***Urgent
# TODO - Minimize the time it takes to find the song [maybe caching]

# TODO - make the client stream the music on disk style *****

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
# go     GuildsOptions       It contains the variables for each guild
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

    @commands.Cog.listener()
    async def on_guild_remove(self,guild):
        #our beloved bot has been deleted from a server . how dare them ugh
        print("our bot has been deleted from ",guild.name,",",guild.id)
        #deleting the guildOptions for it 
        self.go.pop(guild.id)
            
    @commands.Cog.listener()
    async def on_guild_join(self,guild):
        #bot has joined a new server
        self.go[guild.id] = guildOptions()
        print("our bot has been added to ",guild.name,",",guild.id)
        for channel in guild.text_channels:
            await channel.send("Holaaaa , The BlueBot is here , b1tches xD")
            

    async def search_spotdl(self, ctx, item):
        
        try:
            songs = spotdl.search([item])
            #get_download_urls takes multiple song names and returns multiple urls as well . hence JUST the first item 
            songUrl = spotdl.get_download_urls(songs)[0]
            songLyrics = spotdl.downloader.search_lyrics(songs[0])
            
            #print(songLyrics)
            return songUrl,songLyrics
        except Exception:
            await ctx.send("Spotdl shat the bed , trying yt-dlp directly. hold on boys")
            return None,None
        

    # searching the item on youtube
    async def get_song_yt(self, ctx, item,itemType):
        #itemType is gonna be either a url or a songName as the user inputs it
        
        guildOptions = self.go[ctx.author.guild.id]
        
        with YoutubeDL(guildOptions.YDL_OPTIONS) as ydl:
            try:
                
                if itemType == 'url':
                    info = ydl.extract_info(item, download=True)
                elif itemType == 'query':
                    #TODO . get the first match that you find fix it later
                    info = ydl.extract_info("ytsearch:%s" % item, download=True)["entries"][0]
                    
                # get only the audios - already sorted by worst to best so taking the last
                # format is gonna be enough . no need to sort or do anything else really
                # info["formats"] = [f for f in info["formats"] if f.get("audio_ext") != 'none' and f.get("acodec") == "opus"]

            except Exception:
                await ctx.send("yt-dlp shat the bed as well , Sorry boys . maybe a Full Youtube Link is gonna work")
                return None
            
        # Debug Statments
        print("Guild_Name: ", ctx.author.guild.name," ", 
              "yt-video ID: "       ,info["id"],"\n",
              "yt-video title: "    ,info["title"])
        # print("Guild_Name: ",ctx.author.guild.name," ","Chosen Format: ",info['formats'][-1])
        return {
            'source': os.path.join(SongsTempDir,info['id']+'.opus'),
            'title': info['title']
        }

    async def tryConnectVc(self,ctx):
        
        guildOptions = self.go[ctx.author.guild.id]
        
        # try to connect to voice channel if you are not already connected
        if guildOptions.vc == None or not guildOptions.vc.is_connected():
            guildOptions.vc = await guildOptions.current_song[1].connect()

            # in case we fail to connect
            if guildOptions.vc == None:
                await ctx.send("Could not connect to the voice channel")
                return
        else:
            await guildOptions.vc.move_to(guildOptions.current_song[1])
    
    def resetFlags(self,ctx):
        guildOptions                = self.go[ctx.author.guild.id]
        guildOptions.is_playing     = False
        guildOptions.is_paused      = False
        guildOptions.loop           = False
        guildOptions.current_song   = None
        
    # infinite loop checking
    async def play_music(self, ctx):
        
        guildOptions = self.go[ctx.author.guild.id]
        
        #deal with the skip
        if guildOptions.skip:
            #ignore the loop and choose a new song or exit then reset the skip Flag
            
            if len(guildOptions.music_queue) > 0:
                guildOptions.current_song = guildOptions.music_queue.pop(0)
            else:
                await ctx.send("Playlist is empty. please add some more music")
                #reset all of the flags
                self.resetFlags(ctx)
                
            guildOptions.skip=False
            
        
        if len(guildOptions.music_queue) > 0 or (guildOptions.loop and guildOptions.current_song):
            guildOptions.is_playing = True
            
            
            #Nand loop,current_song .. look up the truth table . this was annoying ngl xD
            if not (guildOptions.loop and guildOptions.current_song):
                guildOptions.current_song = guildOptions.music_queue.pop(0)
            
            await self.tryConnectVc(ctx)

            m_url = guildOptions.current_song[0]['source']
            loop = guildOptions.vc.loop

            await ctx.send("```INI\nsong=\""+guildOptions.current_song[0]['title']+"\" is playing\n```")
            guildOptions.vc.play(
                discord.FFmpegOpusAudio(
                    m_url, **guildOptions.FFMPEG_OPTIONS), 
                after=lambda e: asyncio.run_coroutine_threadsafe(self.play_music(ctx), loop)
                )
        else:
            self.resetFlags(ctx)

    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        
        guildOptions = self.go[ctx.author.guild.id]

        # if the first condition is None then python wouldn't even evaluate the second condition
        if ctx.author.voice and ctx.author.voice.channel:
            voice_channel = ctx.author.voice.channel

            if guildOptions.is_paused:
                guildOptions.vc.resume()
            else:
                query = " ".join(args).strip()
                if not query:
                    await ctx.send("you need to specify {SongName/SpotifyUrl/YoutubeUrl}")
                    return

                # TODO - this is just a workaround to get the bot to accept yt/ytMusic links
                # test ".p https://www.youtube.com/watch?v=EORgrmt2cR0"
                regex = '^((?:https?:)?\/\/)?((?:www|m|music)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$'
                youtubeUrlRegexMatch = re.search(regex, query)
                
                if not youtubeUrlRegexMatch:
                    songUrl,songLyrics = await self.search_spotdl(ctx, query)

                song = await self.get_song_yt(ctx, youtubeUrlRegexMatch.string if youtubeUrlRegexMatch else (songUrl or query) ,"url" if youtubeUrlRegexMatch else "query")
                song['lyrics'] = songLyrics
                
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
        
        guildOptions = self.go[ctx.author.guild.id]

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
        
        guildOptions = self.go[ctx.author.guild.id]

        if  guildOptions.is_paused:
            guildOptions.is_paused = False
            guildOptions.is_playing = True
            guildOptions.vc.resume()

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        
        guildOptions = self.go[ctx.author.guild.id]
        
        if guildOptions.vc:
            #if there's no song that's already playing then don't set the flag
            if  guildOptions.current_song:
                guildOptions.skip = True
                
            #that would invoke play_music anyway 
            guildOptions.vc.stop()
              
            
    def createQueueText(self,ctx):

        guildOptions = self.go[ctx.author.guild.id]
        
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
        
        guildOptions = self.go[ctx.author.guild.id]

        if guildOptions.vc != None and guildOptions.is_playing:
            guildOptions.vc.stop()
        guildOptions.music_queue    = []
        guildOptions.current_song   = None
        await ctx.send("Music queue cleared")

    @commands.command(name="disconnect", aliases=["leave", "d", "dc"], help="Kick the bot from VC")
    async def dc(self, ctx):
        
        guildOptions = self.go[ctx.author.guild.id]

        guildOptions.is_playing     = False
        guildOptions.is_paused      = False
        guildOptions.current_song   = None
        await guildOptions.vc.disconnect()

    @commands.command(name="speed")
    async def speed(self, ctx, speed):
        # guildOptions.FFMPEG_OPTIONS["options"] = "-vn -af atempo=" + str(speed)
        try:
            
            guildOptions = self.go[ctx.author.guild.id]
            
            # making sure that speed actually contains a float
            print("Guild_Name: ", ctx.author.guild.name, " ",
                  "type(speed)= ", type(speed), "float(speed)= ", float(speed))
            # making sure that speed is between a 0.5-100.0
            assert float(speed) >= 0.5 and float(speed) <= 100.0

            guildOptions.FFMPEG_OPTIONS["options"] = "-vn -af atempo=" + str(float(speed))
        except:
            print("Guild_Name: ", ctx.author.guild.name, " ",
                  "There has been an issue with the speed command")
            return
        
    @commands.command(name="loop",aliases=["l"])
    async def loop(self, ctx, value):
        
        guildOptions = self.go[ctx.author.guild.id]
        
        if value =='on':
            guildOptions.loop = True
        elif value =='off':
            guildOptions.loop = False
        else:
            guildOptions.loop= not guildOptions.loop
            
        await ctx.send("Loop is now "+ ("on" if guildOptions.loop==True else "off"))
        

    @commands.command(name="guild_opts",aliases=["g","debug"])
    async def guild_options(self, ctx):

        guildOptions = self.go[ctx.author.guild.id]
        
        retVal = "```"
        retVal += "Guild_name: "+       str(ctx.author.guild.name            )+'\n'
        retVal += "Guild_ID: "+         str(ctx.author.guild.id              )+'\n'
        retVal += "is_playing: " +      str(guildOptions.is_playing          )+"\n"
        retVal += "is_paused: " +       str(guildOptions.is_paused           )+"\n"
        retVal += "skip: " +            str(guildOptions.skip                )+"\n"
        retVal += "loop: " +            str(guildOptions.loop                )+"\n"
        retVal += "vc: " +              str(guildOptions.vc                  )+"\n"
        retVal += "avgLatency: " +      (str(int(guildOptions.vc.average_latency*1000))+"ms" if guildOptions.vc and guildOptions.vc.average_latency else "None")+"\n"
        retVal += "FFMPEG_OPTIONS: " +  str(guildOptions.FFMPEG_OPTIONS      )+"\n"
        # retVal += "\nYDL_OPTIONS: " +     str(guildOptions.YDL_OPTIONS)+"\n"
        retVal += "music_queue: " +     str("\n"+"\n".join(["\t" +line for line in self.createQueueText(ctx).split("\n")][:-1]))+"\n"
        # retVal += "current_song: " +    str(guildOptions.current_song[0]['title'] if guildOptions.current_song else None)
        retVal += "```"
        await ctx.send(retVal)
        
    @commands.command(name="randomMeme",aliases=["rm"])
    async def randomMeme(self,ctx):

        urls=[]

        for submission in reddit.subreddit("memes").hot(limit=50):
            ext=submission.url.split('.')
            if submission.selftext.strip()=="" or ext.lower() not in ['png','gif','jpeg','jpg']:
                urls.append(submission.url)
        #print("we've gotten %d urls"%len(urls))
        url = random.choice(urls)

        await ctx.send(url)

        '''
        file = discord.File(diskFilename, filename="image.png")
        embed = discord.Embed()
        embed.set_image(url="attachment://image.png")
        await ctx.send(file=file, embed=embed)
        '''
        
    @commands.command(name="lyrics",aliases=["ly"])
    async def lyrics(self,ctx):
        
        guildOptions = self.go[ctx.author.guild.id]
        
        # print("lyrics",guildOptions.current_song[0]['lyrics'])
        
        if guildOptions.current_song[0]['lyrics']:
            await ctx.send(guildOptions.current_song[0]['lyrics'][:1500])
        else:
            await ctx.send("We didn't find any lyrics for this song , dickhead")