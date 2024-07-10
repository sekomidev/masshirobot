import telebot
import logging
import signal
import sys
import os
import re
from yt_dlp import YoutubeDL
from pytube import YouTube
from telebot.types import Message
from telebot.util import extract_arguments
from config import TELEGRAM_API_TOKEN, songs_path
from typing import Optional

# NOTE: not that useful right now, but it's better to set up logging now
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s"
)

bot = telebot.TeleBot(TELEGRAM_API_TOKEN)
users_currently_downloading = {}


# remove music file from {songs_path} directory
def cleanup(video_id: str, song_extension: str) -> None:
    os.remove(f"{songs_path}{video_id}.{song_extension}")


def parse_download_args(message_text: str) -> Optional[dict]:
    # FIXME: what the fuck????
    pattern = (
        r"(?P<link>.*?)(\s+title:\s*(?P<title>.*?))?(\s+artist:\s*(?P<artist>.*?))?$"
    )
    match = re.search(pattern, message_text)

    if match:
        link = match.group("link")
        title = match.group("title")
        artist = match.group("artist")
        return {"link": link, "title": title, "artist": artist}
    else:
        return None


def can_download_video(url, message: Message) -> bool:
    try:
        yt = YouTube(url)
        yt.check_availability()
    except Exception as e:
        print(e)
        bot.reply_to(message, "sorry, the video is unavailiable.")
        return False

    if yt.length > 3600:
        bot.reply_to(
            message,
            "sorry, the video is too long. i can't download large files because of size limits.",
        )
        return False
    if users_currently_downloading.get(message.from_user.id) is True:
        bot.reply_to(
            message, "hey, please wait until the previous download finishes! ><"
        )
        return False

    return True


@bot.message_handler(commands=["start"])
def start_command(message: Message) -> None:
    start_text = "this bot can download (almost) any song from youtube :3"
    bot.reply_to(message, start_text)


@bot.message_handler(commands=["help"])
def help_command(message: Message):
    help_text = (
        "Usage: /download (link) title: (title) artist: (artist)\n\n"
        "Example: /download https://www.youtube.com/watch?v=vKhpQTYOpUU title: Masshiro Na Yuki artist: Halozy\n\n"
        "or simply /d https://www.youtube.com/watch?v=vKhpQTYOpUU"
    )
    bot.reply_to(message, help_text)


@bot.message_handler(commands=["d", "download"])
def download_command(message: Message) -> None:
    user_input = parse_download_args(extract_arguments(message.text))
    url = user_input["link"]

    if not url:
        bot.reply_to(message, "please provide a link.")
        return

    print(user_input)

    if not can_download_video(url, message=message):
        return

    yt = YouTube(url)
    bot_is_downloading_message = bot.reply_to(message, "downloading, please wait...")
    extension = "mp3"
    song_format = f"{songs_path}{yt.video_id}"
    song_path = f"{songs_path}{yt.video_id}.{extension}"

    options = {
        "outtmpl": song_format,
        "quiet": True,
        "noplaylist": True,
        "writethumbnail": True,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": extension,
                "preferredquality": "192",
            },
            {
                "key": "FFmpegMetadata",
                "add_metadata": True,
            },
            {
                "key": "EmbedThumbnail",
                "already_have_thumbnail": False,
            },
        ],
    }

    users_currently_downloading[message.from_user.id] = True
    try:
        with YoutubeDL(options) as ydl:
            ydl.download(url)

        title = user_input["title"]
        if not title:
            title = yt.title
        artist = user_input["artist"]
        if not artist:
            artist = yt.author
        with open(song_path, "rb") as audio_file:
            bot.send_audio(
                message.chat.id, audio_file, title=title, performer=artist, timeout=600
            )
    except Exception as err:
        bot.reply_to(message, f"sowwy, cant process it: {err}")
    users_currently_downloading[message.from_user.id] = False
    bot.delete_message(
        chat_id=bot_is_downloading_message.chat.id,
        message_id=bot_is_downloading_message.id,
    )
    cleanup(yt.video_id, song_extension=extension)


def interrupt_handler(signal, frame):
    logging.info("shutting down :3")
    sys.exit(0)


signal.signal(signal.SIGINT, interrupt_handler)


def main():
    while True:
        try:
            bot.polling(non_stop=True, interval=0)
        except Exception as e:
            logging.warn(e)


if __name__ == "__main__":
    main()
