"""
Telegram Bot Integration
Connects the Honeypot Orchestrator to Telegram for real-time scam baiting.
"""

import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

from app.config import get_settings
from app.orchestrator.honeypot_orchestrator import get_orchestrator
from app.agents.state_machine import get_state_machine

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

settings = get_settings()
orchestrator = get_orchestrator()
state_machine = get_state_machine()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🍯 Agentic Honeypot Active.\nForward scam messages here to begin engagement."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming messages"""
    if not update.message or not update.message.text:
        return

    chat_id = update.effective_chat.id
    user_text = update.message.text
    
    # Map Telegram Chat ID to Conversation ID
    conversation_id = f"tg_{chat_id}"
    
    logger.info(f"Received message from {chat_id}: {user_text[:50]}...")
    
    try:
        # Check if conversation exists
        existing_context = state_machine.get_context(conversation_id)
        
        if not existing_context:
            # New Engagement
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            result = await orchestrator.start_engagement(
                initial_message=user_text,
                scammer_identifier=str(chat_id),
                context={"source": "telegram", "username": update.effective_user.username}
            )
        else:
            # Continue Engagement
            if existing_context.is_terminated:
                await context.bot.send_message(chat_id=chat_id, text="[Engagement Terminated]")
                return

            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            
            result = await orchestrator.continue_engagement(
                conversation_id=conversation_id,
                scammer_message=user_text
            )
            
        # Send Honeypot Response
        if result.response:
            await context.bot.send_message(chat_id=chat_id, text=result.response)
            
        # Log Safety Warnings
        if result.safety_warnings:
            logger.warning(f"Safety warnings for {chat_id}: {result.safety_warnings}")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        await context.bot.send_message(chat_id=chat_id, text="[System Error] Could not process message.")

def run_telegram_bot():
    """Run the bot"""
    if not settings.telegram_bot_token or settings.telegram_bot_token == "your-token-here":
        logger.error("TELEGRAM_BOT_TOKEN not set in .env. Exiting.")
        return

    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    logger.info("🤖 Telegram Bot Started. Polling...")
    application.run_polling()

if __name__ == "__main__":
    run_telegram_bot()
