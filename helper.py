#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 13 19:16:49 2023

@author: samuii
"""

# class botGuild():
#     def __init__(self,guild_id):
#         self.guild_id = guild_id
#         self.guildOptions = guildOptions()
        
import os

SongsTempDir="./SongsTempDir/"
    
class guildOptions():
    def __init__(self):
        
        self.is_playing     = False
        self.is_paused      = False
        self.skip           = False
        
        self.loop           = False
        self.current_song   = None
        
        self.music_queue    = []
        
        self.vc             = None
        
        self.YDL_OPTIONS    =\
        {
            'format':'bestaudio[acodec=opus]',
            'outtmpl':os.path.join(SongsTempDir,'%(id)s.opus'),
            'format-sort':'acodec:',
            'noplaylist':'True',
            "no_warnings": True,
            "retries":5,
            "quiet": True,
            
        }
        
        self.FFMPEG_OPTIONS =\
        {
            'before_options': '',
            'options': '-vn'
        }
