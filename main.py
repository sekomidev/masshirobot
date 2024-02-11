import telebot
import subprocess
import os
import re
from yt_dlp import YoutubeDL
from pytube import YouTube
from telebot.types import Message
from telebot.util import extract_arguments
from config import TELEGRAM_API_TOKEN, songs_path

bot = telebot.TeleBot(TELEGRAM_API_TOKEN)
users_running_download_command = {} # the list of users where their download requests are being processed


# remove song and metadata files from {songs_path} directory
def cleanup(video_id: str, song_extension: str) -> None:
    os.remove(f"{songs_path}{video_id}.{song_extension}")
    os.remove(f"{songs_path}{video_id}.info.json")


def parse_download_command(message_text: str) -> dict or None:
    pattern = r"/download\s+(?P<link>.*?)(\s+title:\s*(?P<title>.*?))?(\s+artist:\s*(?P<artist>.*?))?$"
    match = re.search(pattern, message_text)
    
    if match: 
        link = match.group('link')
        title = match.group('title')
        artist = match.group('artist')
        
        return {'link': link, 'title': title, 'artist': artist}
    else:
        return None    


@bot.message_handler(commands=['start'])
def start_command(message: Message) -> None:
    instructions = "this bot can download (almost) any song from youtube <3"
    bot.reply_to(message, instructions)


@bot.message_handler(commands=['download'])
def download_command(message: Message) -> None:
    user_id = message.from_user.id
    user_input = parse_download_command(message.text)
    if user_input is None:
        bot.reply_to(message, "please provide a link.")
        return
    url = user_input['link']
    try:
        yt = YouTube(url)
        yt.check_availability()
    except Exception:
        bot.reply_to(message, "sorry, the video is unavailiable:")
        return

    if yt.length > 3600:
        bot.reply_to(message, "sorry, the video is too long. i can't download large files because of size limits.")
        return
    if users_running_download_command.get(user_id) is True:
        bot.reply_to(message, "hey, please wait until the previous download finishes! ><")
        return

    bot_is_downloading_message = bot.reply_to(message, "downloading, please wait...")
    print(f"downloading {url}")

    extension = "mp3"
    song_format = f"{songs_path}{yt.video_id}"
    song_path = f"{songs_path}{yt.video_id}.{extension}"

    options = {
        'outtmpl': song_format,
        'quiet': True,
        'noplaylist': True,
        'writethumbnail': True,
        'format': 'bestaudio/best',
        'writethumbnail': 'true',
        'postprocessors': [

            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': extension,
                'preferredquality': '192',
            }, {  
                'key': 'FFmpegMetadata', 
                'add_metadata': True, 
            }, { 
                'key': 'EmbedThumbnail', 
                'already_have_thumbnail': False, 
            }
        ],
    }

    users_running_download_command[user_id] = True

    with YoutubeDL(options) as ydl:
        ydl.download(url)
    
    title = user_input['title']
    artist = user_input['artist']
    with open(song_path, 'rb') as audio_file:
        bot.send_audio(message.chat.id, audio_file, title=title, performer=artist)

    users_running_download_command[user_id] = False
    bot.delete_message(chat_id=bot_is_downloading_message.chat.id, message_id=bot_is_downloading_message.id)
    cleanup(yt.video_id, song_extension=extension)


if __name__ == "__main__":
    bot.polling(none_stop=True, interval=0)