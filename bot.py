import os
import asyncio
import tempfile
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from shazamio import Shazam
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

bot = AsyncTeleBot(BOT_TOKEN)
shazam = Shazam()

CHANNEL_USERNAME = "loot_dells"
CHANNEL_LINK = "https://t.me/loot_dells"


async def is_user_joined(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False


async def send_force_join_message(message: types.Message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Join Channel", url=CHANNEL_LINK))
    markup.add(types.InlineKeyboardButton("I have joined ✅", callback_data="check_join"))

    text = (
        "⚠️ **Access Restricted**\n\n"
        "To use this bot, you must first join our channel:\n"
        f"👉 {CHANNEL_LINK}\n\n"
        "After joining, click the button below."
    )
    await bot.reply_to(message, text, reply_markup=markup, parse_mode="Markdown")


@bot.callback_query_handler(func=lambda call: call.data == "check_join")
async def check_join_callback(call: types.CallbackQuery):
    if await is_user_joined(call.from_user.id):
        await bot.answer_callback_query(call.id, "Thank you! You can now use the bot.")
        await bot.send_message(
            call.message.chat.id,
            "✅ You have successfully joined the channel.\n\n"
            "Now send me a **voice message** or **audio file**."
        )
    else:
        await bot.answer_callback_query(
            call.id,
            "You still haven't joined the channel. Please join first.",
            show_alert=True
        )


async def recognize_audio(file_path: str):
    try:
        result = await shazam.recognize(file_path)

        if not result or "track" not in result:
            return None, None, None, "❌ Sorry, I couldn't recognize the song."

        track = result["track"]
        title = track.get("title", "Unknown")
        artist = track.get("subtitle", "Unknown Artist")
        shazam_url = track.get("url", "")

        return title, artist, shazam_url, None

    except Exception as e:
        return None, None, None, f"❌ Recognition error: {str(e)}"


@bot.message_handler(commands=["start", "help"])
async def start_handler(message: types.Message):
    if not await is_user_joined(message.from_user.id):
        await send_force_join_message(message)
        return

    text = (
        "👋 Hello!\n\n"
        "I am a **Music Recognition Bot**.\n\n"
        "Send me any **voice message** or **audio file**, "
        "and I will identify the song for you.\n\n"
        "Commands:\n"
        "/start - Start the bot\n"
        "/help - Show this help message"
    )
    await bot.reply_to(message, text, parse_mode="Markdown")


@bot.message_handler(content_types=["voice", "audio"])
async def handle_audio(message: types.Message):
    if not await is_user_joined(message.from_user.id):
        await send_force_join_message(message)
        return

    status = await bot.reply_to(message, "🔍 Recognizing the song... Please wait...")

    try:
        if message.voice:
            file_info = await bot.get_file(message.voice.file_id)
        else:
            file_info = await bot.get_file(message.audio.file_id)

        downloaded_file = await bot.download_file(file_info.file_path)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as temp_file:
            temp_file.write(downloaded_file)
            temp_path = temp_file.name

        title, artist, shazam_url, error = await recognize_audio(temp_path)
        os.unlink(temp_path)

        if error:
            await bot.edit_message_text(error, chat_id=message.chat.id, message_id=status.message_id)
            return

        # Create useful links
        youtube_search = f"https://www.youtube.com/results?search_query={quote(title + ' ' + artist)}"
        spotify_search = f"https://open.spotify.com/search/{quote(title + ' ' + artist)}"

        final_text = (
            f"🎵 **Song Found!**\n\n"
            f"**Title:** {title}\n"
            f"**Artist:** {artist}\n\n"
            f"🔗 **Listen here:**\n"
            f"▶️ [YouTube Search]({youtube_search})\n"
            f"🟢 [Spotify Search]({spotify_search})\n"
        )

        if shazam_url:
            final_text += f"🔗 [Shazam]({shazam_url})"

        await bot.edit_message_text(
            final_text,
            chat_id=message.chat.id,
            message_id=status.message_id,
            parse_mode="Markdown",
            disable_web_page_preview=True
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
