import os
import asyncio
import tempfile
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from shazamio import Shazam
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

bot = AsyncTeleBot(BOT_TOKEN)
shazam = Shazam()


async def recognize_audio(file_path: str) -> str:
    """Recognize the song and return a formatted English response"""
    try:
        result = await shazam.recognize(file_path)

        if not result or "track" not in result:
            return "❌ Sorry, I couldn't recognize the song."

        track = result["track"]
        title = track.get("title", "Unknown")
        artist = track.get("subtitle", "Unknown Artist")

        # Collect streaming links
        links = []
        if "hub" in track and "providers" in track["hub"]:
            for provider in track["hub"]["providers"]:
                if provider.get("type") == "SPOTIFY":
                    for action in provider.get("actions", []):
                        if action.get("type") == "uri":
                            links.append(f"🟢 Spotify: {action.get('uri')}")
                if provider.get("type") == "APPLE_MUSIC":
                    for action in provider.get("actions", []):
                        if action.get("type") == "uri":
                            links.append(f"🍎 Apple Music: {action.get('uri')}")

        # Shazam link
        shazam_url = track.get("url", "")
        if shazam_url:
            links.append(f"🔗 Shazam: {shazam_url}")

        reply = f"🎵 **Song Found!**\n\n"
        reply += f"**Title:** {title}\n"
        reply += f"**Artist:** {artist}\n\n"

        if links:
            reply += "\n".join(links)
        else:
            reply += "No streaming links available."

        return reply

    except Exception as e:
        return f"❌ An error occurred: {str(e)}"


@bot.message_handler(commands=["start", "help"])
async def start_handler(message: types.Message):
    text = (
        "👋 Hello!\n\n"
        "I am a **Music Recognition Bot**.\n"
        "Send me any **voice message** or **audio file**, "
        "and I will identify the song for you.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )
    await bot.reply_to(message, text)


@bot.message_handler(content_types=["voice", "audio"])
async def handle_audio(message: types.Message):
    status = await bot.reply_to(message, "🔍 Searching for the song... Please wait...")

    try:
        # Download the file
        if message.voice:
            file_info = await bot.get_file(message.voice.file_id)
        else:
            file_info = await bot.get_file(message.audio.file_id)

        downloaded_file = await bot.download_file(file_info.file_path)

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_file.write(downloaded_file)
            temp_path = temp_file.name

        # Recognize the song
        result_text = await recognize_audio(temp_path)

        # Delete temporary file
        os.unlink(temp_path)

        await bot.edit_message_text(
            result_text,
            chat_id=message.chat.id,
            message_id=status.message_id,
            parse_mode="Markdown"
        )

    except Exception as e:
        await bot.edit_message_text(
            f"❌ Something went wrong: {str(e)}",
            chat_id=message.chat.id,
            message_id=status.message_id
        )


async def main():
    print("Bot is running...")
    await bot.infinity_polling()


if __name__ == "__main__":
    asyncio.run(main())
