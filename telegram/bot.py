#!/usr/bin/env python3
"""Telegram bot — sends photos to the OCR API and returns extracted text."""

import logging
import os
import tempfile

import aiohttp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OCR_API_URL = os.getenv("OCR_API_URL", "http://localhost:8067/ocr/upload")
OCR_API_KEY = os.getenv("OCR_API_KEY", "")

if not all((BOT_TOKEN, OCR_API_URL, OCR_API_KEY)):
    raise RuntimeError(
        "Set TELEGRAM_BOT_TOKEN, OCR_API_URL, and OCR_API_KEY environment variables."
    )

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("telegram.bot")

WELCOME = (
    "👋 Welcome to *OCR Bot*!\n\n"
    "Send me a photo of a document, receipt, or handwritten note "
    "and I'll extract the text for you.\n\n"
    "Commands:\n"
    "/start — show this message\n"
    "/help — usage tips"
)

HELP_TEXT = (
    "📷 *How to use OCR Bot*\n\n"
    "1. Send a clear photo (not a compressed thumbnail if possible)\n"
    "2. Wait a few seconds while Gemini processes the image\n"
    "3. Receive the extracted text in Markdown format\n\n"
    "Supports 100+ languages including Hebrew and Arabic (RTL)."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(WELCOME, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    photo = update.message.photo[-1]
    tg_file = await photo.get_file()

    suffix = ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        local_path = tmp.name

    try:
        await tg_file.download_to_drive(custom_path=local_path)
        logger.info("Downloaded photo to %s", local_path)

        async with aiohttp.ClientSession() as session:
            form = aiohttp.FormData()
            with open(local_path, "rb") as image_file:
                form.add_field(
                    "file",
                    image_file,
                    filename=os.path.basename(local_path),
                    content_type="image/jpeg",
                )
                form.add_field("format_type", "markdown")

                headers = {"Authorization": f"Bearer {OCR_API_KEY}"}

                async with session.post(OCR_API_URL, data=form, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        ocr_text = result.get("raw_text", "").strip()
                        if ocr_text:
                            # Telegram message limit is 4096 chars
                            if len(ocr_text) > 4000:
                                ocr_text = ocr_text[:4000] + "\n\n…(truncated)"
                            await update.message.reply_text(ocr_text)
                        else:
                            await update.message.reply_text(
                                "No text found in that image. Try a clearer photo."
                            )
                    elif resp.status == 403:
                        await update.message.reply_text(
                            "You're out of OCR credits. Contact the administrator."
                        )
                    elif resp.status == 401:
                        await update.message.reply_text(
                            "Authentication failed. The bot needs a valid API token."
                        )
                    else:
                        body = await resp.text()
                        logger.warning("OCR API error %s: %s", resp.status, body)
                        await update.message.reply_text(
                            f"OCR service error ({resp.status}). Please try again later."
                        )
    except aiohttp.ClientError:
        logger.exception("Network error calling OCR API")
        await update.message.reply_text(
            "Could not reach the OCR service. Please try again later."
        )
    except Exception:
        logger.exception("Unexpected error during OCR")
        await update.message.reply_text("Something went wrong. Please try again later.")
    finally:
        try:
            os.remove(local_path)
        except OSError:
            pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled exception", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "An unexpected error occurred. Please try again."
        )


def main() -> None:
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_error_handler(error_handler)

    logger.info("Starting Telegram bot…")
    app.run_polling()


if __name__ == "__main__":
    main()
