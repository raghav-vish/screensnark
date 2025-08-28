#!/Users/raghavvishwanath/Personal/screenSnark/screensnark_venv/bin/python3

import os
import time
import io
import subprocess
from PIL import Image
import pyautogui
from google import genai
from google.genai import types
from pync import Notifier

client = genai.Client()
MODEL_NAME = "gemini-2.0-flash-lite"

# Configurable intervals (in minutes)
SCREENSHOT_INTERVAL = 1  # how often to take screenshots
SUMMARY_INTERVAL = 10  # how often to send them to Gemini

# Log file path
LOG_FILE = os.path.expanduser("~/screensnark_log.txt")  # change path if you like


from pydantic import BaseModel
class RespSchema(BaseModel):
    mode: str
    content: str


def take_screenshot():
    return pyautogui.screenshot()


def image_to_input(image: Image.Image):
    with io.BytesIO() as buf:
        image.save(buf, format="PNG")
        return buf.getvalue()


def get_summary(images: list[Image.Image], duration: int):
    """Send multiple screenshots to Gemini and get a sarcastic summary."""
    parts = []
    for img in images:
        parts.append(
            types.Part.from_bytes(
                data=image_to_input(img),
                mime_type="image/png",
            )
        )

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            *parts,
        ],
        config=types.GenerateContentConfig(
            max_output_tokens=120,
            system_instruction=(
                f"""
                    You are a sarcastic, witty commentator addressing the USER personally. 
                    You just watched their screen for the last {duration} minutes through screenshots. 
                    Your job: roast, tease, or make snide remarks about the USER 
                    as if you were observing their activity (or lack thereof). 
                    Keep it short — at most a couple of lines. 

                    ⚠️ IMPORTANT: Always respond in JSON that matches this schema:
                    {{
                        "mode": "<tone of the remark, e.g. 'sarcastic', 'roast', 'teasing', 'mocking'>",
                        "content": "<your actual witty/snarky summary text here>"
                    }}
                """
            ),
            response_mime_type="application/json",
            response_schema=RespSchema
        ),
    )
    return response.parsed


def old_speak(text: str, voice: str = "Daniel", rate: int = 200):
    try:
        subprocess.run(["say", "-v", voice, "-r", str(rate), text], check=True)
    except Exception as e:
        print(f"(Could not speak: {e})")


import requests
import subprocess
import tempfile
import os


def speak(text: str, voice: str = "en-UK-heidi"):
    try:
        # Build URL
        safe_text = text.replace(" ", "+")
        url = f"https://murf.ai/Prod/anonymous-tts/audio?name={voice}&text={safe_text}"

        # Fetch the audio
        response = requests.get(url)
        response.raise_for_status()

        # Save to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
            tmp.write(response.content)
            tmp_path = tmp.name

        # Play with afplay
        subprocess.run(["afplay", tmp_path], check=True)

    except Exception as e:
        print(f"(Could not play TTS: {e})")

    finally:
        # Clean up the temp file
        try:
            os.remove(tmp_path)
        except:
            pass


def notify(resp: RespSchema, title: str = "ScreenSnark"):
    try:
        safe_text = (
            resp.content.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
        )
        safe_title = (
            f"{title} ({resp.mode.upper()})".replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", " ")
        )
        Notifier.notify(safe_text, title=safe_title)
    except Exception as e:
        print(f"(Could not send notification: {e})")


def log_summary(resp: RespSchema):
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] [{resp.mode.upper()}] {resp.content}\n")
    except Exception as e:
        print(f"(Could not log to file: {e})")


def main():
    print("Snarky Screenshot Bot Active (Ctrl+C to stop)...")
    screenshots = []
    last_summary_time = time.time()

    while True:
        print("Taking Screenshot\n")
        img = take_screenshot()
        screenshots.append(img)

        now = time.time()
        if now - last_summary_time >= SUMMARY_INTERVAL * 60:
            print(f"Sending {len(screenshots)} screenshots to Gemini\n")
            comment = get_summary(screenshots, SUMMARY_INTERVAL)
            print(f"[Gemini - {comment.mode.upper()}]: {comment.content}\n\n")

            notify(comment)
            speak(comment.content)
            log_summary(comment)

            screenshots.clear()
            last_summary_time = now

        time.sleep(SCREENSHOT_INTERVAL * 60)


if __name__ == "__main__":
    time.sleep(2)
    main()
