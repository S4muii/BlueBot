import discord
from discord.ext import commands
from helper import guildOptions

import re
import os
import traceback

from spotdl import Spotdl

# Instaintiate spotdl . make sure the credentials are working
try:
    spotdl = Spotdl(
        client_id=os.environ['SPOTIPY_CLIENT_ID'],
        client_secret=os.environ['SPOTIPY_CLIENT_SECRET']
    )
except Exception:
    print("Need to specify Spotify Credintials (SPOTIPY_CLIENT_ID,SPOTIPY_CLIENT_SECRET)\n" +
          "using an Environment Variable \n" +
          "On linux that can be achieved like this\n" +
          "export SPOTIPY_CLIENT_ID=\"xxxx\"\n" +
          "export SPOTIPY_CLIENT_SECRET=\"xxxx\""
          )


# TODO - Sanatize inputs ***Urgent
#TODO - Lyrics

# TODO - use the song metadata , show it to the users preferably using embeds

# TODO - permissions to use the functions [Guild->member->permissions]
# TODO - benchmark [profile] the FFmpegPCM function and replace it with opus if necessary
# TODO - create a single thread or instance of FFmpeg for each guild . don't restart the process with each song
# TODO - Download YT-files to disk and make a list of all files here to not download twice and faster seek
#TODO - Logging
# TODO - make a dislike command that can help identify problems with the output of spotdl [Japanese songs are one example]
# TODO - create a DB of songName->YtMusic Link and couple it with the file cache
# TODO - figure out a way to create some sort of a mixer [default presets maybe] --Zach
# TODO - Song guessing game ******* [ranking] --Zach
# TODO - keep track of each user prefernces and old tracks [User profile/Playlists/Songs]


# some weirda$$ variable names that you might encounter so a bit of a headsup [any help in refactoring this mess would be appreciated]
# GO     GuildOptions        It contains the variables for each guild
# AGID   Author guild ID     pretty self explanatory :p it is the author(the one issuing the command)'s guild(current guild)'s ID

from yt_dlp import YoutubeDL


class music_cog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # state variables
        self.GO = {}
        for guild in self.bot.guilds:
            # Guild_Options
            self.GO[guild.id] = guildOptions()

    def search_spotdl(self, ctx, item):
        # print("Guild_Name: ",ctx.author.guild.name," ",item)
        songs = spotdl.search([item])
        # print("Guild_Name: ",ctx.author.guild.name," ",[song.artist for song in songs])

        songs_urls = spotdl.get_download_urls(songs)
        # print("Guild_Name: ",ctx.author.guild.name," ",songs_urls)
        return self.get_song_yt(ctx, songs_urls[0])

    # searching the item on youtube

    def get_song_yt(self, ctx, url):
        AGID = ctx.author.guild.id
        with YoutubeDL(self.GO[AGID].YDL_OPTIONS) as ydl:
            try:
                info = ydl.extract_info(url, download=False)

                # get only the audios - already sorted by worst to best so taking the last
                # format is gonna be enough . no need to sort or do anything else really
                info["formats"] = [f for f in info["formats"]
                                   if f.get("audio_ext") != 'none']

            except Exception:
                traceback.print_exc()
                return None
        # Debug Statments
        print("Guild_Name: ", ctx.author.guild.name,
              " ", "yt-video ID: ", info["id"])
        # print("Guild_Name: ",ctx.author.guild.name," ","Chosen Format: ",info['formats'][-1])
        return {
            'source': info['formats'][-1]['url'],
            'title': info['title']
        }

    def play_next(self, ctx):
        AGID = ctx.author.guild.id
        if len(self.GO[AGID].music_queue) > 0:
            self.GO[AGID].is_playing = True

            # get the first url
            m_url = self.GO[AGID].music_queue[0][0]['source']

            # remove the first element as you are currently playing it
            self.GO[AGID].music_queue.pop(0)
            # print("Guild_Name: ",ctx.author.guild.name," ",m_url)
            self.GO[AGID].vc.play(discord.FFmpegOpusAudio(
                m_url, **self.GO[AGID].FFMPEG_OPTIONS), after=lambda e: self.play_next())
        else:
            self.GO[AGID].is_playing = False

    # infinite loop checking
    async def play_music(self, ctx):
        AGID = ctx.author.guild.id
        if len(self.GO[AGID].music_queue) > 0:
            self.GO[AGID].is_playing = True

            m_url = self.GO[AGID].music_queue[0][0]['source']

            # try to connect to voice channel if you are not already connected
            if self.GO[AGID].vc == None or not self.GO[AGID].vc.is_connected():
                self.GO[AGID].vc = await self.GO[AGID].music_queue[0][1].connect()

                # in case we fail to connect
                if self.GO[AGID].vc == None:
                    await ctx.send("Could not connect to the voice channel")
                    return
            else:
                await self.GO[AGID].vc.move_to(self.GO[AGID].music_queue[0][1])

            # remove the first element as you are currently playing it
            self.GO[AGID].music_queue.pop(0)
            self.GO[AGID].vc.play(discord.FFmpegPCMAudio(
                m_url, **self.GO[AGID].FFMPEG_OPTIONS), after=lambda e: self.play_next(ctx))
        else:
            self.GO[AGID].is_playing = False

    @commands.command(name="play", aliases=["p", "playing"], help="Plays a selected song from youtube")
    async def play(self, ctx, *args):
        AGID = ctx.author.guild.id

        # if the first condition is None then python wouldn't even evaluate the second condition
        if ctx.author.voice and ctx.author.voice.channel:
            voice_channel = ctx.author.voice.channel

            # if voice_channel is None:
            #     #you need to be connected so that the bot knows where to go
            #     await ctx.send("Connect to a voice channel!")
            if self.GO[AGID].is_paused:
                self.GO[AGID].vc.resume()
            else:
                query = " ".join(args)

                # TODO - this is just a workaround to get the bot to accept yt/ytMusic links
                # test ".p https://www.youtube.com/watch?v=EORgrmt2cR0"
                regex = '^((?:https?:)?\/\/)?((?:www|m|music)\.)?((?:youtube(-nocookie)?\.com|youtu.be))(\/(?:[\w\-]+\?v=|embed\/|v\/)?)([\w\-]+)(\S+)?$'
                x = re.search(regex, query)
                if x:
                    song = self.get_song_yt(ctx, x.string)
                else:
                    song = self.search_spotdl(ctx, query)

                if type(song) == type(True):
                    await ctx.send("Could not download the song. Incorrect format try another keyword. This could be due to playlist or a livestream format.")
                else:
                    await ctx.send("Song added to the queue")
                    self.GO[AGID].music_queue.append([song, voice_channel])

                    if self.GO[AGID].is_playing == False:
                        await self.play_music(ctx)
        else:
            await ctx.send("Connect to a voice channel!")

    @commands.command(name="pause", aliases=["pa"], help="Pauses the current song being played")
    async def pause(self, ctx, *args):
        AGID = ctx.author.guild.id

        if self.GO[AGID].is_playing:
            self.GO[AGID].is_playing = False
            self.GO[AGID].is_paused = True
            self.GO[AGID].vc.pause()
        elif self.GO[AGID].is_paused:
            self.GO[AGID].is_paused = False
            self.GO[AGID].is_playing = True
            self.GO[AGID].vc.resume()

    @commands.command(name="resume", aliases=["r"], help="Resumes playing with the discord bot")
    async def resume(self, ctx, *args):
        AGID = ctx.author.guild.id

        if self.GO[AGID].is_paused:
            self.GO[AGID].is_paused = False
            self.GO[AGID].is_playing = True
            self.GO[AGID].vc.resume()

    @commands.command(name="skip", aliases=["s"], help="Skips the current song being played")
    async def skip(self, ctx):
        AGID = ctx.author.guild.id

        if self.GO[AGID].vc != None and self.GO[AGID].vc:
            self.GO[AGID].vc.stop()
            # try to play next in the queue if it exists
            await self.play_music(ctx)

    @commands.command(name="queue", aliases=["q"], help="Displays the current songs in queue")
    async def queue(self, ctx):
        AGID = ctx.author.guild.id

        retval = ""
        for i in range(0, len(self.GO[AGID].music_queue)):
            # display a max of 5 songs in the current queue
            if (i > 4):
                break
            retval += self.GO[AGID].music_queue[i][0]['title'] + "\n"

        if retval != "":
            await ctx.send(retval)
        else:
            await ctx.send("No music in queue")

    @commands.command(name="clear", aliases=["c", "bin"], help="Stops the music and clears the queue")
    async def clear(self, ctx):
        AGID = ctx.author.guild.id

        if self.GO[AGID].vc != None and self.GO[AGID].is_playing:
            self.GO[AGID].vc.stop()
        self.GO[AGID].music_queue = []
        await ctx.send("Music queue cleared")

    @commands.command(name="leave", aliases=["disconnect", "l", "d", "dc"], help="Kick the bot from VC")
    async def dc(self, ctx):
        AGID = ctx.author.guild.id

        self.GO[AGID].is_playing = False
        self.GO[AGID].is_paused = False
        await self.GO[AGID].vc.disconnect()

    @commands.command(name="speed")
    async def speed(self, ctx, speed):
        # self.GO[AGID].FFMPEG_OPTIONS["options"] = "-vn -af atempo=" + str(speed)
        try:
            AGID = ctx.author.guild.id
            # making sure that speed actually contains a float
            print("Guild_Name: ", ctx.author.guild.name, " ",
                  "type(speed)= ", type(speed), "float(speed)= ", float(speed))
            # making sure that speed is between a 0.1-2.0
            assert float(speed) >= 0.1 and float(speed) <= 2.0

            self.GO[AGID].FFMPEG_OPTIONS["options"] = "-vn -af atempo=" + \
                str(float(speed))
        except:
            print("Guild_Name: ", ctx.author.guild.name, " ",
                  "There has been an issue with the speed command")
            return

    @commands.command(name="guild_options")
    async def guild_options(self, ctx):

        AGID = ctx.author.guild.id
        retVal = ""
        retVal += "\nis_playing: " +      str(self.GO[AGID].is_playing)
        retVal += "\nis_paused: " +       str(self.GO[AGID].is_paused)
        retVal += "\nmusic_queue: " +     str(self.GO[AGID].music_queue)
        retVal += "\nvc: " +              str(self.GO[AGID].vc)
        retVal += "\nYDL_OPTIONS: " +     str(self.GO[AGID].YDL_OPTIONS)
        retVal += "\nFFMPEG_OPTIONS: " +  str(self.GO[AGID].FFMPEG_OPTIONS)

        await ctx.send(retVal)