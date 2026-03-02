import asyncio
import logging
import os
import signal
import sys

from zoom_joiner import ZoomJoiner
from audio_pipeline import AudioPipeline
from api_client import ApiClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger("bot")

MEETING_URL      = os.environ["MEETING_URL"]
INTERVIEW_ID     = os.environ["INTERVIEW_ID"]
BOT_NAME         = os.environ.get("BOT_NAME", "Interview Assistant")
API_BASE_URL     = os.environ["API_BASE_URL"]
DEEPGRAM_API_KEY = os.environ["DEEPGRAM_API_KEY"]


async def main():
    log.info(f"Bot starting | interview={INTERVIEW_ID} | meeting={MEETING_URL}")

    api    = ApiClient(base_url=API_BASE_URL, interview_id=INTERVIEW_ID)
    joiner = ZoomJoiner(bot_name=BOT_NAME, api=api)
    audio  = AudioPipeline(
        deepgram_api_key=DEEPGRAM_API_KEY,
        interview_id=INTERVIEW_ID,
        api=api,
    )

    def handle_shutdown(sig, frame):
        log.info("Shutdown signal received")
        asyncio.create_task(shutdown(joiner, audio, api))

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT,  handle_shutdown)

    try:
        await api.update_status("joining")
        stop_event = asyncio.Event()
        await asyncio.gather(
            joiner.run(meeting_url=MEETING_URL, stop_event=stop_event),
            audio.run(stop_event=stop_event),
        )
    except Exception as e:
        log.error(f"Bot crashed: {e}", exc_info=True)
        await api.update_status("failed", error=str(e))
        sys.exit(1)
    finally:
        log.info("Bot finished")
        await api.update_status("completed")


async def shutdown(joiner, audio, api):
    await joiner.close()
    await audio.stop()
    await api.update_status("completed")


if __name__ == "__main__":
    asyncio.run(main())