"""
SharkonAI Telegram Handler — Enhanced v2
Manages all Telegram interactions using aiogram v3.

Key improvements:
  • Multi-step tool chaining (auto-continuation up to MAX_CHAIN_STEPS)
  • Rich status messages with progress tracking
  • Voice message support
  • Inline keyboard for confirmations
  • Better error handling and user feedback
"""

import os
import asyncio
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, FSInputFile
from aiogram.client.default import DefaultBotProperties

from config import CONFIG
from logger import log
from memory import Memory
from brain import Brain
from tools import dispatch_tool, transcribe_audio

# ── Setup ───────────────────────────────────────────────────────────────────

router = Router()

# These will be injected at startup
_memory: Memory = None
_brain: Brain = None


def init_handler(memory: Memory, brain: Brain):
    """Inject dependencies into the handler module."""
    global _memory, _brain
    _memory = memory
    _brain = brain
    log.info("Telegram handler initialized with memory and brain.")


# ── Authorization ───────────────────────────────────────────────────────────

def is_authorized(user_id: int) -> bool:
    """Check if the user is the authorized operator."""
    return user_id == CONFIG.AUTHORIZED_USER_ID


# ── Message Splitting ──────────────────────────────────────────────────────

def split_message(text: str, max_length: int = 4096) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_length:
        return [text]

    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Try to split at a newline
        split_pos = text[:max_length].rfind("\n")
        if split_pos == -1 or split_pos < max_length // 2:
            # Try splitting at a space
            split_pos = text[:max_length].rfind(" ")
            if split_pos == -1 or split_pos < max_length // 2:
                split_pos = max_length
        chunks.append(text[:split_pos])
        text = text[split_pos:].lstrip("\n")
    return chunks


# ── Safe Reply ──────────────────────────────────────────────────────────────

async def safe_reply(message: Message, text: str):
    """Send a reply, handling Telegram parse errors gracefully."""
    if not text or not text.strip():
        text = "✅ Done."

    chunks = split_message(text)
    for chunk in chunks:
        try:
            await message.reply(chunk)
        except Exception:
            try:
                await message.reply(chunk, parse_mode=None)
            except Exception as e:
                log.error(f"Failed to send message chunk: {e}")


async def safe_edit(message: Message, text: str):
    """Safely edit a message."""
    try:
        if len(text) > 4096:
            text = text[:4090] + "..."
        await message.edit_text(text)
    except Exception:
        try:
            await message.edit_text(text, parse_mode=None)
        except Exception as e:
            log.error(f"Failed to edit message: {e}")


async def send_image_to_chat(message: Message, image_path: str, caption: str = ""):
    """Send a local image file as a photo to the Telegram chat."""
    try:
        if not os.path.exists(image_path):
            log.error(f"Image file not found: {image_path}")
            await message.reply(f"⚠️ Image file not found: {image_path}")
            return False

        # Check file size — Telegram limit is 10MB for photos, 50MB for documents
        file_size = os.path.getsize(image_path)

        photo_file = FSInputFile(image_path)

        if file_size > 10 * 1024 * 1024:
            # Too large for photo, send as document
            await message.reply_document(
                document=photo_file,
                caption=caption[:1024] if caption else None,
            )
        else:
            await message.reply_photo(
                photo=photo_file,
                caption=caption[:1024] if caption else None,
            )

        log.info(f"Sent image to chat: {image_path} ({file_size} bytes)")
        return True

    except Exception as e:
        log.error(f"Failed to send image: {e}")
        try:
            await message.reply(f"⚠️ Failed to send image: {e}")
        except Exception:
            pass
        return False


async def send_file_to_chat(message: Message, file_path: str, caption: str = ""):
    """Send a local file as a document to the Telegram chat."""
    try:
        if not os.path.exists(file_path):
            log.error(f"File not found: {file_path}")
            await message.reply(f"⚠️ File not found: {file_path}")
            return False

        file_size = os.path.getsize(file_path)
        if file_size > 50 * 1024 * 1024:
            await message.reply(f"⚠️ File too large for Telegram ({file_size / (1024*1024):.1f} MB, limit 50 MB).")
            return False

        doc_file = FSInputFile(file_path)
        await message.reply_document(
            document=doc_file,
            caption=caption[:1024] if caption else None,
        )

        log.info(f"Sent file to chat: {file_path} ({file_size} bytes)")
        return True

    except Exception as e:
        log.error(f"Failed to send file: {e}")
        try:
            await message.reply(f"⚠️ Failed to send file: {e}")
        except Exception:
            pass
        return False


# ── Tool Chain Executor ─────────────────────────────────────────────────────

async def execute_tool_chain(message: Message, user_text: str, initial_decision: dict):
    """
    Execute a potentially multi-step tool chain.
    The AI can request continuation by setting "continue" to true.
    Each step executes one tool, feeds the result back, and checks for more steps.
    """
    decision = initial_decision
    chain_context = []
    step = 0
    status_msg = None
    final_response = decision.get("response", "")

    while step < CONFIG.MAX_CHAIN_STEPS:
        action = decision.get("action", "none")
        parameters = decision.get("parameters", {})
        should_continue = decision.get("continue", False)

        if action and action != "none":
            step += 1
            log.info(f"Chain step {step}: {action} with params: {parameters}")

            # Send or update status message
            status_text = f"🔧 Step {step}: Executing {action}..."
            try:
                if status_msg:
                    await safe_edit(status_msg, status_text)
                else:
                    status_msg = await message.reply(status_text)
            except Exception:
                pass

            # Execute the tool
            tool_result = await dispatch_tool(action, parameters)

            # Track in chain context
            chain_context.append({
                "step": step,
                "action": action,
                "parameters": parameters,
                "success": tool_result.success,
                "output": (tool_result.stdout or tool_result.stderr)[:500],
            })

            # Store action in memory
            await _memory.store_action(
                action_type=action,
                parameters=parameters,
                result=tool_result.stdout or tool_result.stderr,
                success=tool_result.success,
                thought=decision.get("thought", ""),
                response=decision.get("response", ""),
            )

            # If the tool produced an image, send it as a photo
            if tool_result.image_path and tool_result.success:
                caption = decision.get("response", "")
                await send_image_to_chat(message, tool_result.image_path, caption)

            # If the tool produced a file, send it as a document
            if tool_result.file_path and tool_result.success:
                caption = decision.get("response", "")
                await send_file_to_chat(message, tool_result.file_path, caption)

            # Get AI's analysis of the result (and possible next step)
            follow_decision = await _brain.process_tool_result(decision, tool_result)

            final_response = follow_decision.get("response", final_response)

            # Check if the AI wants to continue with another tool
            next_action = follow_decision.get("action", "none")
            next_continue = follow_decision.get("continue", False)

            if next_action and next_action != "none" and (next_continue or should_continue):
                # AI wants to execute another tool — loop again
                decision = follow_decision
                decision["_original_message"] = user_text
                continue
            else:
                # Done — we have the final response
                break
        else:
            # No tool action — just a conversational response
            break

    # Clean up status message
    if status_msg:
        try:
            await status_msg.delete()
        except Exception:
            pass

    return final_response, chain_context


# ── Message Handler ─────────────────────────────────────────────────────────

@router.message(F.text)
async def handle_text_message(message: Message):
    """Handle incoming text messages with multi-step tool chaining."""
    user_id = message.from_user.id

    # Authorization check
    if not is_authorized(user_id):
        log.warning(f"Unauthorized access attempt from user {user_id}")
        await message.reply("⛔ Access denied. You are not authorized to use SharkonAI.")
        return

    user_text = message.text.strip()
    if not user_text:
        return

    log.info(f"Message from authorized user: {user_text[:100]}...")

    # Store user message in memory
    await _memory.store_message(
        role="user",
        content=user_text,
        user_id=user_id,
        message_id=message.message_id,
    )

    # Show typing indicator
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        # Get AI decision
        decision = await _brain.think(user_text)
        decision["_original_message"] = user_text

        action = decision.get("action", "none")

        if action and action != "none":
            # Execute tool chain (may be multi-step)
            final_response, chain_context = await execute_tool_chain(
                message, user_text, decision
            )

            # If multi-step, add a summary suffix
            if len(chain_context) > 1:
                steps_summary = f"\n\n📋 Completed {len(chain_context)} steps"
                success_count = sum(1 for s in chain_context if s["success"])
                if success_count == len(chain_context):
                    steps_summary += " — all successful ✅"
                else:
                    steps_summary += f" — {success_count}/{len(chain_context)} successful"
                final_response += steps_summary

        else:
            # Pure conversational response
            final_response = decision.get("response", "")

        # Store assistant response in memory
        await _memory.store_message(role="assistant", content=final_response)

        # Send the response safely
        await safe_reply(message, final_response)

    except Exception as e:
        log.error(f"Error handling message: {e}", exc_info=True)
        error_msg = f"⚠️ An error occurred: {str(e)[:300]}"
        try:
            await message.reply(error_msg, parse_mode=None)
        except Exception:
            pass


# ── Document Handler ────────────────────────────────────────────────────────

@router.message(F.document)
async def handle_document(message: Message):
    """Handle incoming file uploads."""
    user_id = message.from_user.id

    if not is_authorized(user_id):
        await message.reply("⛔ Access denied.")
        return

    doc = message.document
    log.info(f"Received file: {doc.file_name} ({doc.file_size} bytes)")

    # Download the file
    downloads_dir = CONFIG.DOWNLOADS_DIR
    os.makedirs(downloads_dir, exist_ok=True)
    file_path = os.path.join(downloads_dir, doc.file_name)

    try:
        file = await message.bot.get_file(doc.file_id)
        await message.bot.download_file(file.file_path, destination=file_path)

        await _memory.store_message(
            role="user",
            content=f"[File uploaded: {doc.file_name}, size: {doc.file_size} bytes, saved to: {file_path}]",
            user_id=user_id,
            message_id=message.message_id,
        )

        caption = message.caption or ""
        file_msg = (
            f"The user uploaded a file: {doc.file_name} "
            f"(size: {doc.file_size} bytes). "
            f"It has been saved to: {file_path}. "
            f"Caption: {caption}. "
            "Analyze the file if relevant, or tell the user it's been saved."
        )

        decision = await _brain.think(file_msg)
        decision["_original_message"] = file_msg

        action = decision.get("action", "none")
        if action and action != "none":
            final_response, _ = await execute_tool_chain(message, file_msg, decision)
        else:
            final_response = decision.get("response", f"✅ File {doc.file_name} received and saved.")

        await _memory.store_message(role="assistant", content=final_response)
        await safe_reply(message, final_response)

    except Exception as e:
        log.error(f"Error handling document: {e}", exc_info=True)
        await message.reply(f"⚠️ Error saving file: {e}")


# ── Photo Handler ──────────────────────────────────────────────────────────

@router.message(F.photo)
async def handle_photo(message: Message):
    """Handle incoming photo messages."""
    user_id = message.from_user.id

    if not is_authorized(user_id):
        await message.reply("⛔ Access denied.")
        return

    photo = message.photo[-1]  # Highest resolution
    log.info(f"Received photo: {photo.file_id}")

    downloads_dir = CONFIG.DOWNLOADS_DIR
    os.makedirs(downloads_dir, exist_ok=True)
    file_path = os.path.join(downloads_dir, f"photo_{photo.file_unique_id}.jpg")

    try:
        file = await message.bot.get_file(photo.file_id)
        await message.bot.download_file(file.file_path, destination=file_path)

        await _memory.store_message(
            role="user",
            content=f"[Photo received, saved to: {file_path}]",
            user_id=user_id,
            message_id=message.message_id,
        )

        caption = message.caption or ""
        photo_msg = (
            f"The user sent a photo. Saved to: {file_path}. "
            f"Caption: {caption}"
        )

        decision = await _brain.think(photo_msg)
        response_text = decision.get("response", "📸 Photo received and saved.")

        await _memory.store_message(role="assistant", content=response_text)
        await safe_reply(message, response_text)

    except Exception as e:
        log.error(f"Error handling photo: {e}", exc_info=True)
        await message.reply(f"⚠️ Error saving photo: {e}")


# ── Voice Handler (NEW) ────────────────────────────────────────────────────

@router.message(F.voice)
async def handle_voice(message: Message):
    """Handle voice messages — auto-transcribe and process as text."""
    user_id = message.from_user.id

    if not is_authorized(user_id):
        await message.reply("⛔ Access denied.")
        return

    voice = message.voice
    log.info(f"Received voice message: duration={voice.duration}s")

    downloads_dir = CONFIG.DOWNLOADS_DIR
    os.makedirs(downloads_dir, exist_ok=True)
    file_path = os.path.join(downloads_dir, f"voice_{voice.file_unique_id}.ogg")

    try:
        # Show status
        status_msg = await message.reply("🎤 Listening to your voice message...")

        # Download the voice file
        file = await message.bot.get_file(voice.file_id)
        await message.bot.download_file(file.file_path, destination=file_path)

        # Transcribe the audio
        await safe_edit(status_msg, "🎤 Transcribing your voice...")
        transcription_result = await transcribe_audio(file_path, language="en-US")

        if transcription_result.success:
            # Extract the transcribed text
            transcribed_text = transcription_result.stdout.replace("🎤 Transcription:\n", "").strip()
            log.info(f"Voice transcription: {transcribed_text[:100]}...")

            # Update status with what was heard
            await safe_edit(status_msg, f"🎤 Heard: \"{transcribed_text}\"\n\n⏳ Processing...")

            # Store the transcribed message in memory (as if user typed it)
            await _memory.store_message(
                role="user",
                content=f"[Voice message] {transcribed_text}",
                user_id=user_id,
                message_id=message.message_id,
                metadata={"type": "voice", "duration": voice.duration, "audio_path": file_path},
            )

            # Process the transcribed text through the brain (same as text handler)
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
            decision = await _brain.think(transcribed_text)
            decision["_original_message"] = transcribed_text

            action = decision.get("action", "none")

            if action and action != "none":
                # Execute tool chain
                # Delete status msg before tool chain creates its own
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                status_msg = None

                final_response, chain_context = await execute_tool_chain(
                    message, transcribed_text, decision
                )

                if len(chain_context) > 1:
                    steps_summary = f"\n\n📋 Completed {len(chain_context)} steps"
                    success_count = sum(1 for s in chain_context if s["success"])
                    if success_count == len(chain_context):
                        steps_summary += " — all successful ✅"
                    else:
                        steps_summary += f" — {success_count}/{len(chain_context)} successful"
                    final_response += steps_summary
            else:
                final_response = decision.get("response", "")

            # Clean up status message if still exists
            if status_msg:
                try:
                    await status_msg.delete()
                except Exception:
                    pass

            # Store and send response
            await _memory.store_message(role="assistant", content=final_response)
            await safe_reply(message, final_response)

        else:
            # Transcription failed — notify user, still pass to brain with context
            log.warning(f"Voice transcription failed: {transcription_result.stderr}")
            await safe_edit(status_msg, "⚠️ Couldn't recognize speech clearly, but saved the audio.")

            await _memory.store_message(
                role="user",
                content=f"[Voice message, duration: {voice.duration}s, transcription failed, saved to: {file_path}]",
                user_id=user_id,
                message_id=message.message_id,
            )

            voice_msg = (
                f"The user sent a voice message ({voice.duration} seconds) but transcription failed. "
                f"Audio saved to: {file_path}. "
                "Let the user know you received their voice but couldn't understand it clearly, "
                "and ask them to try again or type their message."
            )

            decision = await _brain.think(voice_msg)
            response_text = decision.get(
                "response",
                "🎤 I received your voice message but couldn't understand it clearly. "
                "Could you try again or type your message?"
            )

            await _memory.store_message(role="assistant", content=response_text)
            await safe_reply(message, response_text)

    except Exception as e:
        log.error(f"Error handling voice: {e}", exc_info=True)
        await message.reply(f"⚠️ Error processing voice message: {e}")


# ── Bot Factory ─────────────────────────────────────────────────────────────

def create_bot_and_dispatcher() -> tuple[Bot, Dispatcher]:
    """Create and configure the aiogram Bot and Dispatcher."""
    bot = Bot(
        token=CONFIG.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(),
    )
    dp = Dispatcher()
    dp.include_router(router)
    log.info("Bot and dispatcher created.")
    return bot, dp
