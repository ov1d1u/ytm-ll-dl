from pathlib import Path
import re

from sh import cd, ErrorReturnCode
from ytmusicapi import YTMusic

from slugify import slugify
from constants import DATA_DIRECTORY
from index_helpers import index_add, index_has
from bash import bash


# Create data directory
bash(f"mkdir -p {DATA_DIRECTORY}")

auth_headers = Path("./headers_auth.json")

if not auth_headers.exists():
    YTMusic.setup(filepath=str(auth_headers))

ytm = YTMusic(str(auth_headers))

print("Getting liked music...")
tracks = ytm.get_liked_songs(9999)["tracks"]

print(f"Got {len(tracks)} tracks")
print("")

i = 0
for track in reversed(tracks):
    i += 1
    with cd(DATA_DIRECTORY):
        prefix = f"[{i}/{len(tracks)}] "
        log = lambda x: print(prefix + str(x))
        
        id = track['videoId']
        
        artist = track['artists'][0]['name']
        title = track['title']
        album = track['album']['name'] if track['album'] else None
        
        mp3 = f"{slugify(artist)}, {slugify(title)}.mp3"
        mp3_tmp = ".tmp.mp3"
        mp3_tmp2 = ".tmp2.mp3"
        
        if index_has(id):
            log(f"Video {mp3} already in index, skipping...")
            continue
        else:
            log(f"Downloading {mp3}...")
            
        bash(f"rm -f '{mp3}' '{mp3_tmp}' '{mp3_tmp2}'")
        
        try:
            output = bash(
                "yt-dlp "
                f"https://www.youtube.com/watch?v={id} "
                f"-x -o '{mp3_tmp}'"
            )
        except ErrorReturnCode as e:
            log("yt-dlp failed")
            log(e)
            continue
    

        for line in output.splitlines():
            tag = "[ExtractAudio] Destination: "
            if line.startswith(tag):
                new_dest = line[len(tag):]
                bash(f"ffmpeg -i '{new_dest}' '{mp3_tmp}'")
                bash(f"rm '{new_dest}'")
                break
        
        thumbnail = "current.png"
        bash(f"curl '{track['thumbnails'][-1]['url']}' -o {thumbnail}")
        
        title = re.sub('\"', '\\"', title)
        artist = re.sub('\"', '\\"', artist)
        album = re.sub('\"', '\\"', album) if album else None
        
        title = re.sub('`', '\\`', title)
        artist = re.sub('`', '\\`', artist)
        album = re.sub('`', '\\`', album) if album else None
        
        
        a = (
            f"ffmpeg -y -i '{mp3_tmp}' -i {thumbnail} " +
            "-map 0:0 -map 1:0 -c copy -id3v2_version 3 -metadata:s:v " +
            "title=\"Album cover\" -metadata:s:v comment=\"Cover (front)\" " +
            f"-metadata title=\"{title}\" " + 
            f"-metadata artist=\"{artist}\" " + 
            (f"-metadata album=\"{album}\" " if album else " ") +
            f"-c:a libmp3lame {mp3_tmp2}"
        )
        print(a)
        bash(a)
        bash(f"rm '{thumbnail}'")
        bash(f"mv {mp3_tmp2} '{mp3}'")
        
        index_add(id)