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
def delete_music_file(video_id: str) -> None:
    os.remove(f"{songs_path}{video_id}.mp3")


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
        logging.info(f"match not found in {message_text}")
        return None


def can_download_video(url, message: Message) -> bool:
    try:
        yt = YouTube(url)
        yt.check_availability()
    except Exception as e:
        logging.info(e)
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
    start_text = "hello! check out the /help command for instructions :3"
    bot.reply_to(message, start_text)


@bot.message_handler(commands=["help"])
def help_command(message: Message):
    help_text = (
        "usage: /download (link) [title: ...] [artist: ...]\n\n"
        "example: /download https://www.youtube.com/watch?v=vKhpQTYOpUU title: Masshiro Na Yuki artist: Halozy\n\n"
        "or simply /d https://www.youtube.com/watch?v=vKhpQTYOpUU"
    )
    bot.reply_to(message, help_text)


@bot.message_handler(commands=["d", "download"])
def download_command(message: Message) -> None:
    user_input = parse_download_args(extract_arguments(message.text))
    url = user_input["link"]

    # if url is not found the first time, check if it's possible
    # to find one in the replied message (if one exists)
    if not url:
        if message.reply_to_message:
            user_input["link"] = message.reply_to_message.text
            url = user_input["link"]

    if not url:
        bot.reply_to(message, "please provide a link.")
        return

    logging.info(user_input)

    if not can_download_video(url, message=message):
        return

    yt = YouTube(url)
    bot_is_downloading_message = bot.reply_to(message, "downloading, please wait...")
    song_format = f"{songs_path}{yt.video_id}"
    song_path = f"{songs_path}{yt.video_id}.mp3"

    options = {
        "outtmpl": song_format,
        "quiet": True,
        "noplaylist": True,
        "writethumbnail": False,
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
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
        bot.reply_to(message, f"sowwy, cant process it: {err} :3")
    users_currently_downloading[message.from_user.id] = False
    bot.delete_message(
        chat_id=bot_is_downloading_message.chat.id,
        message_id=bot_is_downloading_message.id,
    )
    delete_music_file(yt.video_id)


@bot.message_handler(commands=["kolxoz"])
def windows_command(message: Message) -> None:
    bot.reply_to(
        message,
        "debloated windows 11 is faster than arch linux, boots faster and more power efficient, also looks modern and consistent, and alway from ANIMAL LINUX WORLD 😅 but linux is good too, it is good for kolxoz, when they wanna explore bash and waste years (fun fact: if he uses open source his WIFE gotta be open source too 😂)",
    )


def interrupt_handler(signal, frame):
    logging.info("shutting down :3")
    sys.exit(0)


signal.signal(signal.SIGINT, interrupt_handler)


def main():
    while True:
        try:
            bot.polling(non_stop=True, interval=0)
        except Exception as e:
            logging.warning(e)


if __name__ == "__main__":
    main()
