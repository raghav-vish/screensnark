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
SCREENSHOT_INTERVAL = 5  # how often to take screenshots
SUMMARY_INTERVAL = 30     # how often to send them to Gemini

def take_screenshot():
    return pyautogui.screenshot()

def image_to_input(image: Image.Image):
    with io.BytesIO() as buf:
        image.save(buf, format="PNG")
        return buf.getvalue()

def get_sarcastic_summary(images: list[Image.Image], duration: int):
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
                f"You are a sarcastic commentator addressing the USER personally. "
                f"You just watched their screen for the last {duration} minutes. "
                f"Look at the screenshots for clues about what they were doing. "
                f"Your job is to roast, tease, or make snide remarks about the USER "
                f"as if you were watching them work (or procrastinate). "
                f"Make it a short, witty summary — just a couple of lines at most."
            )
        )
    )
    return response.text.strip()

def speak(text: str, voice: str = "Daniel", rate: int = 200):
    try:
        subprocess.run(["say", "-v", voice, "-r", str(rate), text], check=True)
    except Exception as e:
        print(f"(Could not speak: {e})")

def notify(text: str, title: str = "ScreenSnark"):
    try:
        safe_text = (
            text.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", " ")
        )
        safe_title = (
            title.replace("\\", "\\\\")
                 .replace('"', '\\"')
                 .replace("\n", " ")
        )
        Notifier.notify(safe_text, title=safe_title)
    except Exception as e:
        print(f"(Could not send notification: {e})")

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
            comment = get_sarcastic_summary(screenshots, SUMMARY_INTERVAL)
            print(f"[Gemini]: {comment}\n\n")
            notify(comment)
            # speak(comment)
            screenshots.clear()
            last_summary_time = now

        time.sleep(SCREENSHOT_INTERVAL * 60)

if __name__ == "__main__":
    time.sleep(2)
    main()
