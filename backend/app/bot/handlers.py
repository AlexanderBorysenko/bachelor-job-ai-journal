from datetime import date, datetime

from aiogram import Dispatcher, types, F
from aiogram.filters import CommandStart, Command

from app.models.user import User
from app.models.raw_message import RawMessage, SourceType, MessageStatus
from app.models.audio_job import AudioJob, AudioJobStatus
from app.services.classification import classify_date
from app.services.transcription import process_audio_job
from app.services.bake import bake_messages
from app.core.events import event_bus


def register_handlers(dp: Dispatcher):
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(cmd_bake, Command("bake"))
    dp.message.register(cmd_web, Command("web"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(handle_voice, F.voice)
    dp.message.register(handle_text, F.text)


async def cmd_start(message: types.Message):
    """Register user and send welcome message."""
    user = await User.find_one({"telegram_id": message.from_user.id})
    if not user:
        user = User(
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            display_name=message.from_user.full_name,
        )
        await user.insert()

    await message.answer(
        f"Привіт, {user.display_name}! 👋\n\n"
        "Я — твій AI-щоденник. Просто пиши або надсилай голосові "
        "повідомлення протягом дня, а коли будеш готовий — "
        "набери /bake щоб перетворити їх на запис у щоденнику.\n\n"
        "Команди:\n"
        "/bake — запікти повідомлення в запис\n"
        "/web — відкрити веб-інтерфейс\n"
        "/help — довідка"
    )


async def cmd_bake(message: types.Message):
    """Trigger the bake process."""
    user = await _get_user(message)
    if not user:
        return

    # Check for processing audio
    processing_count = await AudioJob.find(
        {
            "user_id": user.id,
            "status": {"$in": [AudioJobStatus.DOWNLOADING, AudioJobStatus.TRANSCRIBING]},
        }
    ).count()

    if processing_count > 0:
        await message.answer(
            f"⏳ Є {processing_count} повідомлень в процесі транскрибації. "
            "Зачекай завершення і спробуй знову."
        )
        return

    pending_count = await RawMessage.find(
        {"user_id": user.id, "status": MessageStatus.PENDING}
    ).count()

    if pending_count == 0:
        await message.answer("Буфер порожній — нічого запікати 🤷")
        return

    await message.answer(f"🔥 Запікаю {pending_count} повідомлень...")

    # Get all pending messages
    pending = await RawMessage.find(
        {"user_id": user.id, "status": MessageStatus.PENDING}
    ).to_list()

    user_id_str = str(user.id)
    try:
        entries = await bake_messages(user.id, pending)
        await event_bus.publish(user_id_str, "bake:complete", {
            "entries_created": len(entries),
            "entries": [
                {"id": str(e.id), "date": e.date.isoformat(), "preview": e.content[:200]}
                for e in entries
            ],
        })
        dates_str = ", ".join(e.date.strftime("%d.%m") for e in entries)
        await message.answer(
            f"✅ Готово! Створено {len(entries)} запис(ів) за дати: {dates_str}"
        )
    except Exception as exc:
        await event_bus.publish(user_id_str, "bake:error", {"detail": str(exc)[:300]})
        await message.answer(f"❌ Помилка запікання: {str(exc)[:200]}")


async def cmd_web(message: types.Message):
    """Send link to web interface."""
    # TODO: generate auth link
    await message.answer("🌐 Веб-інтерфейс: (посилання буде додано після деплою)")


async def cmd_help(message: types.Message):
    """Show help message."""
    await message.answer(
        "📖 Як користуватись:\n\n"
        "Надсилай мені текстові або голосові повідомлення "
        "протягом дня — я збережу їх у буфер.\n\n"
        "Коли будеш готовий, набери /bake — і я перетворю "
        "все на літературний запис у щоденнику.\n\n"
        "Команди:\n"
        "/bake — запікти повідомлення\n"
        "/web — відкрити веб-інтерфейс\n"
        "/help — ця довідка"
    )


async def handle_voice(message: types.Message):
    """Handle incoming voice message — create audio job for async processing."""
    user = await _get_user(message)
    if not user:
        return

    voice = message.voice
    job = AudioJob(
        user_id=user.id,
        telegram_message_id=message.message_id,
        file_id=voice.file_id,
        duration=voice.duration,
        status=AudioJobStatus.PENDING,
    )
    await job.insert()
    await event_bus.publish(str(user.id), "buffer:update")

    await message.answer(f"🎙️ Отримано голосове ({voice.duration}с). Транскрибую...")

    # Process transcription in background
    import asyncio
    from app.core.config import settings as app_settings

    asyncio.create_task(_process_voice(job, app_settings.telegram_bot_token, message))


async def handle_text(message: types.Message):
    """Handle incoming text message — classify date and add to buffer."""
    user = await _get_user(message)
    if not user:
        return

    # Classify date via Claude API
    send_dt = message.date or datetime.utcnow()
    try:
        classified = await classify_date(message.text, send_dt)
    except Exception:
        # Fallback to message date on any unexpected error
        classified = send_dt.date()

    raw_msg = RawMessage(
        user_id=user.id,
        source_type=SourceType.TEXT,
        content=message.text,
        telegram_message_id=message.message_id,
        classified_date=classified,
        status=MessageStatus.PENDING,
    )
    await raw_msg.insert()
    await event_bus.publish(str(user.id), "buffer:update")

    await message.answer("✅ Записано!")


async def _get_user(message: types.Message) -> User | None:
    """Get or prompt user to register."""
    user = await User.find_one({"telegram_id": message.from_user.id})
    if not user:
        await message.answer("Спершу набери /start для реєстрації.")
        return None
    return user


async def _process_voice(job: AudioJob, bot_token: str, message: types.Message):
    """Background task: transcribe voice and notify user."""
    user_id = str(job.user_id)
    try:
        await process_audio_job(job, bot_token)
        await event_bus.publish(user_id, "buffer:update")
        await message.answer("✅ Голосове транскрибовано та записано!")
    except Exception as exc:
        await event_bus.publish(user_id, "buffer:update")
        await message.answer(f"❌ Помилка транскрибації: {str(exc)[:200]}")
