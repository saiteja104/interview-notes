import asyncio
import logging
from datetime import datetime, timezone

import httpx

log = logging.getLogger("api_client")


class ApiClient:
    def __init__(self, base_url: str, interview_id: str):
        self.base_url        = base_url.rstrip("/")
        self.interview_id    = interview_id
        self._status_url     = f"{self.base_url}/internal/interviews/{interview_id}/status"
        self._transcript_url = f"{self.base_url}/internal/interviews/{interview_id}/transcript"
        self._speaker_url    = f"{self.base_url}/internal/interviews/{interview_id}/speaker"

    async def update_status(self, status: str, error: str | None = None):
        payload = {"status": status}
        if error:
            payload["error"] = error
        await self._post(self._status_url, payload)
        log.info(f"Status → {status}")

    async def send_transcript(self, text, speaker_id, words, is_final):
        await self._post(self._transcript_url, {
            "text": text,
            "speaker_id": speaker_id,
            "words": words,
            "is_final": is_final,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def send_speaker_event(self, name: str, timestamp_ms: int):
        await self._post(self._speaker_url, {
            "name": name,
            "timestamp_ms": timestamp_ms,
        })

    async def _post(self, url: str, payload: dict):
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(url, json=payload)
                    r.raise_for_status()
                    return
            except Exception as e:
                if attempt == 2:
                    log.error(f"Failed POST to {url}: {e}")
                else:
                    await asyncio.sleep(attempt + 1)