import asyncio
import logging
import re

from playwright.async_api import async_playwright

log = logging.getLogger("zoom_joiner")

WAITING_ROOM_TIMEOUT = 300


class ZoomJoiner:
    def __init__(self, bot_name: str, api):
        self.bot_name = bot_name
        self.api      = api
        self._browser = None
        self._context = None
        self._page    = None

    async def run(self, meeting_url: str, stop_event: asyncio.Event):
        async with async_playwright() as pw:
            await self._launch_browser(pw)
            await self._join_meeting(meeting_url)
            await self._wait_for_meeting_end(stop_event)

    async def _launch_browser(self, pw):
        log.info("Launching Chrome...")
        self._browser = await pw.chromium.launch(
            headless=False,
            args=[
                "--display=:99",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--use-fake-ui-for-media-stream",
                "--use-fake-device-for-media-stream",
                "--autoplay-policy=no-user-gesture-required",
                "--disable-features=AudioServiceOutOfProcess", # <--- ADD THIS FLAG
                "--alsa-output-device=pulse",
                "--alsa-input-device=pulse",
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--disable-extensions",
                "--window-size=1280,720",
                "--disable-notifications",
            ]
        )

        self._context = await self._browser.new_context(
            permissions=["microphone", "camera"],
            user_agent=(
                "Mozilla/5.0 (X11; Linux x86_64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 720},
        )

        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    { name: 'Chrome PDF Plugin' },
                    { name: 'Chrome PDF Viewer' },
                    { name: 'Native Client' },
                ]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

        self._page = await self._context.new_page()
        log.info("Chrome launched")

    async def _join_meeting(self, meeting_url: str):
        log.info(f"Navigating to: {meeting_url}")
        web_url = self._to_web_client_url(meeting_url)
        log.info(f"Web client URL: {web_url}")

        await self._page.goto(web_url, wait_until="domcontentloaded", timeout=60000)
        await self._screenshot("01_loaded")

        # Wait for name input
        log.info("Waiting for name input...")
        try:
            name_input = await self._page.wait_for_selector(
                '#input-for-name',
                timeout=40000
            )
            await name_input.click()
            await asyncio.sleep(0.5)
            await name_input.fill(self.bot_name)
            log.info(f"Entered name: {self.bot_name}")
        except Exception as e:
            log.warning(f"Name input not found: {e}")
            await self._screenshot("01_name_not_found")
            return

        await self._screenshot("02_name_entered")

        # Join button becomes enabled AFTER name is typed
        await asyncio.sleep(1)
        log.info("Waiting for Join button to be enabled...")
        try:
            await self._page.wait_for_selector(
                'button.preview-join-button:not(.zm-btn--disabled)',
                timeout=10000
            )
            await self._page.click('button.preview-join-button')
            log.info("Clicked Join button")
        except Exception as e:
            log.warning(f"Join button error: {e}")
            await self._screenshot("03_join_failed")
            return

        await self._screenshot("03_join_clicked")

        # 1. Wait to be admitted FIRST
        await self._handle_waiting_room()

        # WAKE UP THE AUDIO: Click randomly on the screen to unlock Chrome's Web Audio API
        log.info("Clicking the screen to unlock Zoom audio...")
        await self._page.mouse.click(200, 200)

        # 2. Handle audio dialog AFTER entering meeting
        await asyncio.sleep(5)
        log.info("Checking audio connection status...")
        try:
            # Check 1: Is it already connected? (Looks for Mute/Unmute)
            connected = await self._page.query_selector('button:has-text("Unmute"), button:has-text("Mute")')
            if connected:
                log.info("Audio is already connected!")
            else:
                # Check 2: Click the bottom-left toolbar icon first if the modal isn't open
                toolbar_audio = await self._page.query_selector('button[aria-label^="Join Audio"]')
                if toolbar_audio:
                    log.info("Clicking toolbar Join Audio icon...")
                    await toolbar_audio.click()
                    await asyncio.sleep(1)

                # Check 3: Click the big blue button in the modal
                log.info("Looking for the Join Audio popup...")
                audio_btn = await self._page.wait_for_selector(
                    '.join-audio-by-voip__join-btn, button:has-text("Join Audio by Computer"), button:has-text("Computer Audio")',
                    timeout=10000
                )
                await audio_btn.click()
                log.info("Clicked Join Audio successfully")
                await self._screenshot("05_audio_success")
                
        except Exception as e:
            log.warning(f"Audio dialog fail: {e}")
            await self._screenshot("05_audio_failed")
            
    async def _handle_waiting_room(self):
        log.info("Waiting to be admitted...")
        await self.api.update_status("waiting_room")
        start = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start
            if elapsed > WAITING_ROOM_TIMEOUT:
                raise TimeoutError("Bot was never admitted")

            in_meeting = await self._page.query_selector(
                '.meeting-app, #wc-container-left, .video-avatar__avatar'
            )
            if in_meeting:
                log.info("Inside the meeting")
                await self._screenshot("04_in_meeting")
                await self.api.update_status("active")
                return

            log.info(f"Still waiting... ({int(elapsed)}s)")
            await asyncio.sleep(3)

    async def _inject_speaker_watcher(self):
        await self._page.evaluate("""
            window.__speakerEvents = [];
            const observer = new MutationObserver(() => {
                const selectors = [
                    '.speaker-active-container .participants-item__display-name',
                    '.video-avatar__avatar--active .video-avatar__avatar-name',
                    '[class*="active-speaker"] [class*="display-name"]',
                ];
                for (const sel of selectors) {
                    const el = document.querySelector(sel);
                    if (el) {
                        const name = el.textContent.trim();
                        if (name) {
                            window.__speakerEvents.push({ name, timestamp: Date.now() });
                        }
                        break;
                    }
                }
            });
            observer.observe(document.body, {
                childList: true, subtree: true,
                attributes: true, attributeFilter: ['class']
            });
        """)
        log.info("Speaker watcher injected")

    async def _wait_for_meeting_end(self, stop_event: asyncio.Event):
        await self._inject_speaker_watcher()
        log.info("Waiting for meeting to end...")

        while not stop_event.is_set():
            ended = await self._page.query_selector(
                '[class*="meeting-ended"], :has-text("This meeting has been ended")'
            )
            if ended:
                log.info("Meeting ended")
                stop_event.set()
                break

            events = await self._page.evaluate("window.__speakerEvents.splice(0)")
            for event in events:
                await self.api.send_speaker_event(
                    name=event["name"],
                    timestamp_ms=event["timestamp"],
                )
            await asyncio.sleep(1)

    def _to_web_client_url(self, meeting_url: str) -> str:
        """
        Handles all Zoom URL formats:
        zoom.us/j/123?pwd=xxx
        app.zoom.us/wc/123/start
        → zoom.us/wc/join/123?pwd=xxx
        """
        match = re.search(r'/(?:j|wc)/(\d+)', meeting_url)
        if not match:
            raise ValueError(f"Cannot extract meeting ID from: {meeting_url}")

        meeting_id = match.group(1)
        pwd_match  = re.search(r'pwd=([^&]+)', meeting_url)
        pwd_param  = f"?pwd={pwd_match.group(1)}" if pwd_match else ""

        return f"https://zoom.us/wc/join/{meeting_id}{pwd_param}"

    async def _screenshot(self, name: str):
            try:
                # Give it 8 seconds to render the heavy Zoom UI, and disable animations
                await self._page.screenshot(
                    path=f"/app/screenshots/bot_{name}.png", 
                    timeout=8000,
                    animations="disabled"
                )
                log.info(f"Successfully saved screenshot: {name}")
            except Exception as e:
                # Now it will explicitly tell us if/why a picture failed
                log.warning(f"Screenshot {name} failed: {e}")

    async def close(self):
        if self._browser:
            await self._browser.close()