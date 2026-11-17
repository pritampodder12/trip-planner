import logging

import client
import formatter
import sessions
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Key used in context.user_data to track when we're waiting for edit feedback
AWAITING_FEEDBACK = "awaiting_feedback"


def _approval_keyboard() -> InlineKeyboardMarkup:
    """The two buttons shown under the itinerary."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Approve", callback_data="approve"),
                InlineKeyboardButton("✏️ Request Changes", callback_data="edit"),
            ]
        ]
    )


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start command — resets everything and greets the user."""
    chat_id = update.effective_chat.id
    sessions.clear_thread(chat_id)
    context.user_data.clear()
    await update.message.reply_text(
        "👋 *Welcome to Trip Planner!*\n\n"
        "Tell me where you'd like to go and I'll build a detailed itinerary for you.\n\n"
        "Example:\n"
        "_5 days in Jaipur and Udaipur, budget 40000 INR, 2 people, love food and forts_",
        parse_mode="Markdown",
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles any plain text message — three cases below."""
    chat_id = update.effective_chat.id
    text = update.message.text.strip()

    # ── Case 1: User just replied with feedback after tapping "Request Changes" ──
    if context.user_data.get(AWAITING_FEEDBACK):
        context.user_data[AWAITING_FEEDBACK] = False
        thread_id = sessions.get_thread(chat_id)
        if not thread_id:
            await update.message.reply_text(
                "Something went wrong. Send /start to begin again."
            )
            return

        wait_msg = await update.message.reply_text(
            "✏️ Revising your plan, please wait..."
        )
        try:
            data = await client.approve_trip(thread_id, approved=False, feedback=text)
            await wait_msg.delete()
            await _handle_response(update, chat_id, context, data)
        except Exception as e:
            logger.error("Error revising trip for chat_id=%s: %s", chat_id, e)
            await wait_msg.edit_text(
                "❌ Something went wrong. Send /start to try again."
            )
        return

    # ── Case 2: No active trip → start a brand new one ──
    if not sessions.has_thread(chat_id):
        wait_msg = await update.message.reply_text(
            "⏳ Planning your trip... this takes about 30–60 seconds, hang tight!"
        )
        try:
            data = await client.create_trip(text, user_id=str(chat_id))
            sessions.set_thread(chat_id, data["thread_id"])
            await wait_msg.delete()
            await _handle_response(update, chat_id, context, data)
        except Exception as e:
            logger.error("Error creating trip for chat_id=%s: %s", chat_id, e)
            await wait_msg.edit_text(
                "❌ Something went wrong. Send /start to try again."
            )
        return

    # ── Case 3: Active trip + user is answering a clarification question ──
    thread_id = sessions.get_thread(chat_id)
    wait_msg = await update.message.reply_text("⏳ Got it, continuing the plan...")
    try:
        data = await client.resume_trip(thread_id, answer=text)
        await wait_msg.delete()
        await _handle_response(update, chat_id, context, data)
    except Exception as e:
        logger.error("Error resuming trip for chat_id=%s: %s", chat_id, e)
        await wait_msg.edit_text("❌ Something went wrong. Send /start to try again.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the ✅ Approve and ✏️ Request Changes button taps."""
    query = update.callback_query
    await query.answer()  # removes the spinner on the button

    chat_id = update.effective_chat.id
    thread_id = sessions.get_thread(chat_id)

    if not thread_id:
        await query.edit_message_text("Session expired. Send /start to begin again.")
        return

    if query.data == "approve":
        await query.edit_message_text("⏳ Confirming your trip...")
        try:
            data = await client.approve_trip(thread_id, approved=True)
            await _handle_response(update, chat_id, context, data)
        except Exception as e:
            logger.error("Error approving trip for chat_id=%s: %s", chat_id, e)
            await query.edit_message_text(
                "❌ Something went wrong. Send /start to try again."
            )

    elif query.data == "edit":
        # Flag that the NEXT message from this user is their edit feedback
        context.user_data[AWAITING_FEEDBACK] = True
        await query.edit_message_text("✏️ What would you like to change about the plan?")


async def _handle_response(
    update: Update,
    chat_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    data: dict,
) -> None:
    """Central dispatcher — reads status and sends the right message."""
    status = data.get("status")

    if status == "needs_input":
        text = formatter.format_questions(data)
        await update.effective_message.reply_text(text)

    elif status == "awaiting_approval":
        text = formatter.format_itinerary(data)
        await update.effective_message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=_approval_keyboard(),
        )

    elif status == "complete":
        # First show the final approved itinerary (without approval buttons this time)
        if data.get("itinerary"):
            itinerary_text = formatter.format_itinerary(data)
            await update.effective_message.reply_text(
                itinerary_text,
                parse_mode="Markdown",
                # No reply_markup here — no buttons, just the final plan
            )
        # Then send the confirmation message
        await update.effective_message.reply_text(
            "✅ *Trip confirmed!* Have an amazing journey 🌍\n\n"
            "Send /start anytime to plan a new trip.",
            parse_mode="Markdown",
        )
        sessions.clear_thread(chat_id)
        context.user_data.clear()

    elif status == "incomplete":
        await update.effective_message.reply_text(
            "❌ I couldn't gather enough information to complete this trip.\n\n"
            "Send /start and try again with more details (cities, days, budget)."
        )
        sessions.clear_thread(chat_id)
        context.user_data.clear()
