import discord
from discord.ext import commands

import re,os,traceback

from spotdl import Spotdl

#Instaintiate spotdl . make sure the credentials are working
try:
    spotdl = Spotdl(
        client_id       = os.environ['SPOTIPY_CLIENT_ID'],
        client_secret   = os.environ['SPOTIPY_CLIENT_SECRET']
        )
except Exception:
    print("Need to specify Spotify Credintials (SPOTIPY_CLIENT_ID,SPOTIPY_CLIENT_SECRET)\n"+
          "using an Environment Variable \n"+
          "On linux that can be achieved like this\n"+
          "export SPOTIPY_CLIENT_ID=\"xxxx\"\n"+
          "export SPOTIPY_CLIENT_SECRET=\"xxxx\""
       )


#TODO - scale it to multiple servers

from yt_dlp import YoutubeDL


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
        #state variable
        self.is_playing = False
        self.is_paused = False

        # 2d array containing [song, channel]
        self.music_queue = []
        self.YDL_OPTIONS = {
            'format':'bestaudio',
            'noplaylist':'True',
            "no_warnings": True,
            "retries":5,
            "quiet": True
            }
        self.FFMPEG_OPTIONS = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -af atempo=2.5'
            }
        
        self.vc = None
        
    def search_spotdl(self,item):
        # print(item)
        songs = spotdl.search([item])
        # print([song.artist for song in songs])

        songs_urls = spotdl.get_download_urls(songs)
        # print(songs_urls)
        return self.get_song_yt(songs_urls[0])

     #searching the item on youtube
    def get_song_yt(self, url):
        with YoutubeDL(self.YDL_OPTIONS) as ydl:
            try: 
                info = ydl.extract_info(url, download=False)
                
                #get only the audios - already sorted by worst to best so taking the last
                #format is gonna be enough . no need to sort or do anything else really
                info["formats"] = [f for f in info["formats"] if f.get("audio_ext")!='none']

       
            except Exception:
                traceback.print_exc()
                return False
        #Debug Statments
        print("yt-video ID: ",info["id"])
        # print("Chosen Format: ",info['formats'][-1])
        return {'source': info['formats'][-1]['url'], 'title': info['title']}


    def play_next(self):
        if len(self.music_queue) > 0:
            self.is_playing = True

            #get the first url
            m_url = self.music_queue[0][0]['source']

            #remove the first element as you are currently playing it
            self.music_queue.pop(0)
            # print(m_url)
            self.vc.play(discord.FFmpegOpusAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False

    # infinite loop checking 
    async def play_music(self, ctx):
        if len(self.music_queue) > 0:
            self.is_playing = True

            m_url = self.music_queue[0][0]['source']
            
            #try to connect to voice channel if you are not already connected
            if self.vc == None or not self.vc.is_connected():
                self.vc = await self.music_queue[0][1].connect()

                #in case we fail to connect
                if self.vc == None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await self.vc.move_to(self.music_queue[0][1])
            
            #remove the first element as you are currently playing it
            self.music_queue.pop(0)
            self.vc.play(discord.FFmpegPCMAudio(m_url, **self.FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.is_playing = False

    @commands.command(name="play", aliases=["p","playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        
        
        if ctx.author.voice:
            voice_channel = ctx.author.voice.channel or None
   
            if voice_channel is None:
                #you need to be connected so that the bot knows where to go
                await ctx.send("Connect to a voice channel!")
            elif self.is_paused:
                self.vc.resume()
            else:
                query = " ".join(args)
                
                #TODO - this is just a workaround to get the bot to accept yt/ytMusic links
                #test ".p https://www.youtube.com/watch?v=EORgrmt2cR0"
                regex = '^((?:https?:)?\/\/)?((?:www|m|music)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$'
                x = re.search(regex, query)
                if x:
                    song = self.get_song_yt(x.string)
                else:
                    song = self.search_spotdl(query)
                    
                    
                if type(song) == type(True):
                    await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
                else:
                    await ctx.send("Song added to the queue")
                    self.music_queue.append([song, voice_channel])
                    
                    if self.is_playing == False:
                        await self.play_music(ctx)
        else:
            await ctx.send("Connect to a voice channel!")

    @commands.command(name="pause",aliases=["pa"], help="Pauses the current song being played")
    async def pause(self, ctx, *args):
        if self.is_playing:
            self.is_playing = False
            self.is_paused = True
            self.vc.pause()
        elif self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()

    @commands.command(name = "resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx, *args):
        if self.is_paused:
            self.is_paused = False
            self.is_playing = True
            self.vc.resume()

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        if self.vc != None and self.vc:
            self.vc.stop()
            #try to play next in the queue if it exists
            await self.play_music(ctx)


    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        retval = ""
        for i in range(0, len(self.music_queue)):
            # display a max of 5 songs in the current queue
            if (i > 4): break
            retval += self.music_queue[i][0]['title'] + "\n"

        if retval != "":
            await ctx.send(retval)
        else:
            await ctx.send("No music in queue")

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        if self.vc != None and self.is_playing:
            self.vc.stop()
        self.music_queue = []
        await ctx.send("Music queue cleared")

    @commands.command(name="leave", aliases=["disconnect", "l", "d"], help="Kick the bot from VC")
    async def dc(self, ctx):
        self.is_playing = False
        self.is_paused = False
        await self.vc.disconnect()
        
    #TODO - ZACHY's idea  -- we need to hotswap this bitch xD
    @commands.command(name="speed")
    async def speed(self, ctx , speed):
       self.FFMPEG_OPTIONS["options"] = "-vn -af atempo=" + str(speed)
       
