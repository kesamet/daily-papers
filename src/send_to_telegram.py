import asyncio
import json
import os
import re
from datetime import datetime

from loguru import logger
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

CHANNEL_ID = os.environ["TELEGRAM_CHANNEL_ID"]
bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])


async def main():
    today_date = datetime.now().strftime("%Y-%m-%d")
    year, month, _ = today_date.split("-")
    try:
        with open(f"archive/{year}/{month}/{today_date}.json", "r") as f:
            papers = json.load(f)
    except FileNotFoundError as e:
        logger.error(e)
        return

    # Send the summary of first paper
    paper = papers[0]
    title = paper["title"]
    link = paper["link"]
    summary = paper.get("summary", "None")
    await send_text_summary(title, link, summary)


def escape_markdown(text):
    """
    Escape special characters for Markdown V2 formatting.
    """
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


async def send_text_summary(title, link, summary):
    """
    Sends a text summary to the specified Telegram channel.

    Args:
    - title (str): The title of the paper.
    - link (str): The arXiv link of the paper.
    - summary (str): The summary of the paper.
    """
    title = escape_markdown(title)
    summary = escape_markdown(summary)
    link = escape_markdown(link)

    message = f"*{title}*\n[arXiv]({link})\n\n{summary}"
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        logger.info("Text summary sent successfully.")
    except TelegramError as e:
        logger.error(f"Failed to send text summary: {e}")


if __name__ == "__main__":
    asyncio.run(main())
