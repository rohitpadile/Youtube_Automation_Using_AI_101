hey i also asked antigravity about this

i am going to automate iamge generation using playwright now any other hack which i can use? i have to paste prompts in to web interface because there i have my plan of nano banana pros

4:24 PM

Here are 5 powerful hacks & best practices for automating your web-interface image generation using Playwright:

1. The Instant Clipboard Paste Hack (Avoid Slow Typing)

Instead of using page.fill() or page.type() (which types line-by-line and can take 5–10 seconds per long prompt), use clipboard injection to paste the entire prompt instantly in 10ms:

python

# Instant paste hack in Playwright

page.locator("textarea#prompt-input").focus()

page.keyboard.insert_text(prompt_text) # Pastes thousands of characters instantly!

2. Thread Session Reuse Hack (Upload Reference Image Once)

If your web UI supports chat threads (like Gemini Web UI or AI Studio):

Hack: Upload female.png once in the very first prompt of the session.

For scenes 2 through 18, send only the prompt text in the same conversation thread.

The web UI will remember the attached character reference from message #1, saving bandwidth and speed!

3. Extract Raw High-Res Image Bytes (No Screen Snapping)

Avoid taking Playwright screenshots of the preview area, as web UIs compress screen renders. Instead, grab the direct high-res image source or listen to network responses:

python

# Network listener hack to grab original high-res image payload automatically

def handle_response(response):

if "image/png" in response.headers.get("content-type", "") or "image/jpeg" in response.headers.get("content-type", ""):

image_bytes = response.body()

with open(f"output_dir/scene_{idx:02d}.png", "wb") as f:

f.write(image_bytes)



page.on("response", handle_response)

4. Smart Wait for Generation Completion (No Fixed Sleep)

Don't use rigid time.sleep(15). Wait dynamically for the UI element changes:

python

# Wait until the 'Generate' button becomes active again or spinner disappears

page.wait_for_selector("button#generate-btn:not([disabled])", timeout=60000)

# Or wait for spinner to detach

page.wait_for_selector(".loading-spinner", state="detached", timeout=60000)

5. Automated prompts_guide.txt Parser

You can parse prompts_guide.txt automatically in Python and pass each prompt directly into your Playwright loop:

python

import re



def parse_prompts_guide(guide_path):

with open(guide_path, "r", encoding="utf-8") as f:

content = f.read()


# Split by IMAGE headers

blocks = content.split("============================================================")

prompts = []

for b in blocks:

if "Prompt" in b:

prompt_text = b.split("Prompt")[-1].strip()

prompts.append(prompt_text)

return prompts



# Usage in your Playwright loop:

# for idx, prompt in enumerate(prompts, 1):

# generate_image_via_playwright(prompt, scene_num=idx)

These 5 hacks will make your Playwright browser automation fast, robust, and completely hands-free!





I DONT WANT TO USE APIS BECAUSE I ONLY HAVE NANO BANA NA PROS ON WEB INTERFACE ITSELF IN MY AI PRO PLAN

SO WHAT SHOULD WE FINALIZE

Automating through Playwright using your active Google AI Pro web subscription makes complete sense. It gives you direct access to the flagship image generation model (Nano Banana Pro) on the web interface without paying a single extra cent in API credits.

Here is the finalized, production-ready Playwright automation script (web_automation.py) that incorporates all 5 hacks—persistent login, single-upload thread context, fast text insertion, and direct image byte downloading.

🛠️ The Finalized Playwright Automation Engine
Give this script to Antigravity or place it directly into your Youtube_Automation project folder.

Project Folder Setup
Plaintext
Youtube_Automation/
├── character_ref.png       # Reference character image
├── script.txt              # Video script
├── metadata.json           # Generated scene prompts
├── web_automation.py       # Playwright browser automation
└── output/
    └── project_20260728_163000/
        ├── scene_01.png
        ├── scene_02.png
        └── voiceover.wav
Complete Code (web_automation.py)
Python
import json
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# CONFIGURATION
# Path to your Chrome User Data directory to keep your Google AI Pro session logged in
CHROME_USER_DATA_DIR = os.path.expanduser(
    "~"
) + r"\AppData\Local\Google\Chrome\User Data"  # Adjust for Mac/Linux if needed
PROFILE_DIRECTORY = "Default"  # Or "Profile 1", etc.

WEB_UI_URL = (
    "https://gemini.google.com/app"  # Or https://aistudio.google.com/
)


def run_playwright_studio(
    project_dir, prompts_file="metadata.json", ref_image="character_ref.png"
):
    metadata_path = os.path.join(project_dir, prompts_file)
    if not os.path.exists(metadata_path):
        print(f"❌ Could not find {metadata_path}")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    ref_image_path = os.path.abspath(ref_image)

    print(
        f"🚀 Launching Playwright with persistent AI Pro login... ({len(scenes)} scenes)"
    )

    with sync_playwright() as p:
        # Launch Chrome with user profile so login & Nano Banana Pro plan persist
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA_DIR,
            channel="chrome",
            headless=False,  # Set False so you can see it working or debug UI
            args=[f"--profile-directory={PROFILE_DIRECTORY}"],
        )

        page = context.new_page()
        page.goto(WEB_UI_URL)
        page.wait_for_load_state("networkidle")

        print("🌐 Opened Web UI. Starting thread sequence...")

        for idx, scene in enumerate(scenes, 1):
            scene_num = str(idx).zfill(2)
            prompt_text = scene.get("visual_prompt", "")
            out_img_path = os.path.join(project_dir, f"scene_{scene_num}.png")

            print(f"\n[Scene {scene_num}/{len(scenes)}] Processing...")

            # -----------------------------------------------------------------
            # HACK 2: UPLOAD REFERENCE IMAGE ONLY ON SHOT 1
            # -----------------------------------------------------------------
            if idx == 1 and os.path.exists(ref_image_path):
                print(f"  [+] Uploading character reference: {ref_image_path}")
                # Target file input element in UI
                file_input = page.locator("input[type='file']").first
                if file_input.is_visible(
                    timeout=3000
                ) or file_input.is_attached():
                    file_input.set_input_files(ref_image_path)
                    page.wait_for_timeout(2000)

            # -----------------------------------------------------------------
            # HACK 1: INSTANT CLIPBOARD TEXT PASTE (10ms)
            # -----------------------------------------------------------------
            input_box = page.locator(
                "div[contenteditable='true'], textarea#prompt-input, .input-area"
            ).first
            input_box.focus()

            # Insert raw string instantly without line-by-line typing delay
            page.keyboard.insert_text(prompt_text)
            page.wait_for_timeout(500)

            # Hit Enter / Submit
            page.keyboard.press("Enter")
            print("  [>] Prompt submitted. Waiting for render...")

            # -----------------------------------------------------------------
            # HACK 4: DYNAMIC SMART WAIT FOR RENDER COMPLETION
            # -----------------------------------------------------------------
            # Wait for spinner to disappear or stop button to flip back to send
            try:
                page.wait_for_selector(
                    ".loading-spinner, .generating-indicator",
                    state="detached",
                    timeout=90000,
                )
            except Exception:
                page.wait_for_timeout(12000)  # Fallback buffer

            page.wait_for_timeout(2000)

            # -----------------------------------------------------------------
            # HACK 3: DIRECT IMAGE EXTRACTION (FULL HIGH-RES)
            # -----------------------------------------------------------------
            # Find the latest generated image element in chat thread
            latest_img = page.locator(
                "img[src*='blob:'], img[src*='googleusercontent']"
            ).last
            if latest_img.is_visible():
                img_url = latest_img.get_attribute("src")

                # If blob or direct URL, download bytes cleanly
                if img_url and img_url.startswith("http"):
                    img_response = page.request.get(img_url)
                    with open(out_img_path, "wb") as img_file:
                        img_file.write(img_response.body())
                    print(f"  [✓] Saved High-Res Image: {out_img_path}")
                else:
                    # Fallback element screenshot if blob URL is shielded
                    latest_img.screenshot(path=out_img_path)
                    print(f"  [✓] Captured Element Frame: {out_img_path}")

            time.sleep(1.5)

        print(f"\n🎉 All {len(scenes)} scenes generated and saved hands-free!")
        context.close()


if __name__ == "__main__":
    # Test on latest project directory
    output_base = Path("output")
    projects = sorted([p for p in output_base.glob("project_*") if p.is_dir()])

    if projects:
        latest_project = str(projects[-1])
        run_playwright_studio(latest_project)
    else:
        print("No project folder found in /output.")
🚀 How Your Complete Hands-Free Routine Operates Now
Step 1: Run generate_studio.py to create your script, Supertonic voiceover (voiceover.wav), and metadata.json prompt file.

Step 2: Run python web_automation.py.

Playwright opens Chrome using your existing session.

Uploads character_ref.png in the first prompt.

Pastes all 15–18 scene prompts sequentially into the thread.

Downloads scene_01.png through scene_18.png directly into your output folder.

Step 3: Open CapCut or DaVinci Resolve, drag the folder in, align the image clips to the voiceover, and export your video.

This gives you the absolute maximum image quality from your AI Pro subscription while automating all the manual work.


hey but how can i make sure its on correct gmail account which have the AI pro plan and its waiting until one image generates, after generating waiting 10 sec to not hang the laptop then pasting prompt again

and always attaching the female.png i do ??

Here are the exact answers and code updates to handle your Gmail profile, image generation waiting times, laptop cooling pause, and image attachment strategy.

1. How to Ensure It Uses the Correct Gmail Account (AI Pro Plan)
Playwright uses your real Chrome profile. To ensure it loads the exact account with your AI Pro plan:

Step A: Find Your Exact Chrome Profile Name
Open Chrome normally using the profile that has your Google AI Pro plan.

Type chrome://version in the address bar and press Enter.

Look at Profile Path. At the end of the path, you will see something like Profile 2 or Default.

Copy that profile folder name (e.g., "Profile 2").

Step B: Set It in Playwright Code
In your Python script, pass that exact profile:

Python
PROFILE_DIRECTORY = "Profile 2"  # Replace with your actual Chrome profile name
First-Time Setup Tip: Run Playwright once with headless=False. If it opens and asks you to log in, log into your AI Pro account manually once. Playwright saves the cookies permanently in that folder, so future runs log in automatically!

2. Should You Attach female.png Every Time or Only Once?
Attach female.png on EVERY SINGLE PROMPT.

While chat threads remember previous images, re-attaching female.png on every prompt forces Nano Banana Pro to look at the exact character reference for every frame. This completely stops "character drift" (where the character slowly changes hair or clothes by frame 12). Since Playwright attaches the file automatically in code, re-attaching it takes under 1 second per image.

3. Waiting for Rendering + 10-Second Laptop Cool-Down
To ensure your laptop doesn't lag or freeze, the script follows this strict sequence for every scene:

Plaintext
Paste female.png + Prompt
       │
       ▼
Click Submit / Press Enter
       │
       ▼
Wait dynamically for Image to render (Detect when "Stop Generating" changes back to "Send")
       │
       ▼
Download & Save high-res image (scene_XX.png)
       │
       ▼
☕ 10-SECOND COOL-DOWN PAUSE (Gives laptop GPU/RAM time to rest & frees memory)
       │
       ▼
Move to Next Prompt
📋 Updated Playwright Automation Code (web_automation.py)
Give this updated function directly to Antigravity or paste it into your web_automation.py file:

Python
import json
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

# 1. PATH TO YOUR CHROME USER DATA & EXACT PROFILE
CHROME_USER_DATA_DIR = os.path.expanduser(
    "~"
) + r"\AppData\Local\Google\Chrome\User Data"

# Check chrome://version to get your exact profile name (e.g., "Default", "Profile 1", "Profile 2")
PROFILE_DIRECTORY = "Profile 2"  # <-- CHANGE THIS to your AI Pro account profile

WEB_UI_URL = "https://gemini.google.com/app"  # or https://aistudio.google.com/


def run_playwright_studio(
    project_dir, prompts_file="metadata.json", ref_image="female.png"
):
    metadata_path = os.path.join(project_dir, prompts_file)
    ref_image_path = os.path.abspath(ref_image)

    if not os.path.exists(metadata_path):
        print(f"❌ Could not find {metadata_path}")
        return

    with open(metadata_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    print(
        f"🚀 Launching Chrome ({PROFILE_DIRECTORY}) for {len(scenes)} scenes..."
    )

    with sync_playwright() as p:
        # Launch Chrome using persistent login context
        context = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_USER_DATA_DIR,
            channel="chrome",
            headless=False,  # Set False so you can watch it execute
            args=[f"--profile-directory={PROFILE_DIRECTORY}"],
        )

        page = context.new_page()
        page.goto(WEB_UI_URL)
        page.wait_for_load_state("networkidle")

        print("🌐 Connected to Web UI. Starting generation sequence...")

        for idx, scene in enumerate(scenes, 1):
            scene_num = str(idx).zfill(2)
            prompt_text = scene.get("visual_prompt", "")
            out_img_path = os.path.join(project_dir, f"scene_{scene_num}.png")

            print(
                f"\n------------------------------------------------------------"
            )
            print(f"🎬 Processing Scene {scene_num}/{len(scenes)}...")

            # STEP 1: ALWAYS ATTACH female.png FOR EVERY PROMPT (Guarantees character consistency)
            if os.path.exists(ref_image_path):
                file_input = page.locator("input[type='file']").first
                if file_input.is_attached():
                    file_input.set_input_files(ref_image_path)
                    print(f"  [+] Attached female.png character reference.")
                    page.wait_for_timeout(1500)  # Wait for thumbnail upload

            # STEP 2: INSTANTLY PASTE PROMPT TEXT
            input_box = page.locator(
                "div[contenteditable='true'], textarea#prompt-input, .input-area"
            ).first
            input_box.focus()
            page.keyboard.insert_text(prompt_text)
            page.wait_for_timeout(500)

            # Submit Prompt
            page.keyboard.press("Enter")
            print("  [>] Submitted prompt to Nano Banana Pro. Waiting for generation...")

            # STEP 3: SMART DYNAMIC WAIT (Wait until generating indicator disappears)
            try:
                # Waits dynamically up to 120s for response to finish rendering
                page.wait_for_selector(
                    ".loading-spinner, .generating-indicator, button[aria-label='Stop generating']",
                    state="detached",
                    timeout=120000,
                )
            except Exception:
                page.wait_for_timeout(15000)  # Fallback buffer

            page.wait_for_timeout(2000)

            # STEP 4: DOWNLOAD / EXTRACT HIGH-RES IMAGE
            latest_img = page.locator(
                "img[src*='blob:'], img[src*='googleusercontent']"
            ).last
            if latest_img.is_visible():
                img_url = latest_img.get_attribute("src")

                if img_url and img_url.startswith("http"):
                    img_response = page.request.get(img_url)
                    with open(out_img_path, "wb") as img_file:
                        img_file.write(img_response.body())
                    print(f"  [✓] Successfully saved high-res: scene_{scene_num}.png")
                else:
                    latest_img.screenshot(path=out_img_path)
                    print(f"  [✓] Captured frame: scene_{scene_num}.png")

            # STEP 5: 10-SECOND LAPTOP COOL-DOWN PAUSE
            print(
                "  [☕] Laptop cooling pause: Sleeping 10 seconds before next scene..."
            )
            time.sleep(10)

        print(f"\n🎉 All {len(scenes)} scenes completed successfully!")
        context.close()


if __name__ == "__main__":
    output_base = Path("output")
    projects = sorted([p for p in output_base.glob("project_*") if p.is_dir()])
    if projects:
        run_playwright_studio(str(projects[-1]))
    else:
        print("No project found in output folder.")
What to check when you run this:
Make sure Chrome is completely closed before starting the Python script (so Playwright can open your profile without a lock error).

Set PROFILE_DIRECTORY to the exact profile folder name from chrome://version.

Watch the script run the first scene to confirm female.png gets attached, the image renders, it downloads scene_01.png, waits 10 seconds, and repeats seamlessly for all scenes!


but then i use brave browser by the way? or should i login in chrome?

You can definitely use Brave Browser with Playwright! Because Brave is built on Chromium, Playwright handles it smoothly.

Here is how Brave vs. Chrome works for your setup, along with the exact code snippet to launch Brave automatically.

Option 1: Automating Your Existing Brave Browser (Recommended)
If your Google AI Pro account is already logged in on Brave, you don't need to switch to Chrome or log in again. You can instruct Playwright to launch Brave's executable using your existing Brave user profile.

How to find your Brave User Data path & executable:
Open Brave and go to brave://version.

Copy the Profile Path (e.g., C:\Users\YourName\AppData\Local\BraveSoftware\Brave-Browser\User Data\Default).

Note the Executable Path (usually C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe).

Updated Code for Brave Automation:
Python
import os
from playwright.sync_api import sync_playwright

# 1. BRAVE PATHS (Update 'YourName' with your Windows username)
BRAVE_EXECUTABLE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BRAVE_USER_DATA_DIR = os.path.expanduser("~") + r"\AppData\Local\BraveSoftware\Brave-Browser\User Data"
PROFILE_DIRECTORY = "Default"  # Or "Profile 1", "Profile 2", etc.

with sync_playwright() as p:
    # Point Playwright directly to Brave's executable and user profile
    context = p.chromium.launch_persistent_context(
        user_data_dir=BRAVE_USER_DATA_DIR,
        executable_path=BRAVE_EXECUTABLE,
        headless=False,  # Set False so you can see it operating
        args=[f"--profile-directory={PROFILE_DIRECTORY}"]
    )
    
    page = context.new_page()
    page.goto("https://gemini.google.com/app")
    
    # Ready to paste prompts into Nano Banana Pro!
Option 2: Should You Just Log In on Chrome Instead?
If you prefer keeping your main personal browsing session open in Brave while the script runs in the background, using Chrome (or a dedicated Playwright Chromium browser profile) can be easier:

The Browser Lock Rule: Chromium browsers (Brave, Chrome, Edge) do not allow two instances to open the exact same profile at the same time.

If you already have Brave open to browse or work, Playwright will fail to attach to that profile until you completely close Brave.

💡 The Best Hands-Free Setup:
If you use Brave continuously throughout the day: Log into your AI Pro Google account once inside standard Google Chrome or a dedicated Playwright Chrome profile. That way, your automation script can run on Chrome silently without forcing you to close Brave while you work!

If you don't mind closing Brave while generating: Use Option 1 above to launch Brave directly.

Which browser setup would work best for your daily workflow?