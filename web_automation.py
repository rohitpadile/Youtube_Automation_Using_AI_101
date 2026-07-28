import os
import re
import json
import time
import glob
from pathlib import Path
from playwright.sync_api import sync_playwright

# =====================================================================
# CONFIGURATION
# =====================================================================
# Chrome User Data directory for persistent AI Pro login session
CHROME_USER_DATA_DIR = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"
PROFILE_DIRECTORY = os.environ.get("CHROME_PROFILE", "Default")  # "Default", "Profile 1", "Profile 2", etc.
WEB_UI_URL = "https://gemini.google.com/app"

# Cool-down & Batch Limit Controls
MAX_IMAGES_PER_RUN = 30     # Max image limit per batch run to respect daily web quota
LAPTOP_COOLING_PAUSE = 10   # Seconds to sleep between generations to prevent laptop overheating

def find_missing_scenes(output_dir="output"):
    """
    Scans all project folders in /output for missing scene_XX.png files.
    Returns a list of missing scene items across all projects in chronological order.
    """
    missing_items = []
    project_folders = sorted(glob.glob(os.path.join(output_dir, "video_*")))

    for folder in project_folders:
        meta_path = os.path.join(folder, "metadata.json")
        guide_path = os.path.join(folder, "prompts_guide.txt")

        scenes = []
        ref_image = "female.png"

        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    scenes = data.get("scenes", [])
                    ref_image = data.get("character_ref", "female.png")
            except Exception:
                pass

        if not scenes and os.path.exists(guide_path):
            # Parse scenes from prompts_guide.txt if metadata is incomplete
            try:
                with open(guide_path, "r", encoding="utf-8") as f:
                    content = f.read()
                blocks = content.split("============================================================")
                for idx, b in enumerate(blocks, 1):
                    if "Prompt" in b:
                        parts = b.split("Prompt")
                        ptext = parts[-1].strip()
                        scenes.append({
                            "scene_num": idx,
                            "full_prompt": ptext
                        })
            except Exception:
                pass

        # Check for missing scene_XX.png files
        for s in scenes:
            num_val = s.get("scene_num", 1)
            num_str = str(num_val).zfill(2)
            img_path = os.path.join(folder, f"scene_{num_str}.png")

            # Missing if file doesn't exist or is smaller than 5KB (corrupted download)
            if not os.path.exists(img_path) or os.path.getsize(img_path) < 5000:
                prompt_to_send = s.get("full_prompt") or s.get("visual_prompt", "")
                missing_items.append({
                    "folder": folder,
                    "folder_name": os.path.basename(folder),
                    "scene_num": num_val,
                    "scene_str": num_str,
                    "img_path": img_path,
                    "prompt": prompt_to_send,
                    "ref_image": ref_image
                })

    return missing_items

def run_web_image_automation(max_limit=MAX_IMAGES_PER_RUN):
    """
    Launches Chrome via Playwright with persistent AI Pro login context.
    Iterates through missing scenes across projects up to max_limit or until rate limit error.
    """
    missing_items = find_missing_scenes()

    if not missing_items:
        print("\n✅ All projects in /output already have 100% complete scene images! Nothing to generate.")
        return {"status": "complete", "generated_count": 0, "remaining_count": 0}

    print("=" * 70)
    print(f"🚀 SMART PLAYWRIGHT IMAGE GENERATOR (Google AI Pro)")
    print(f"📊 Total missing scenes across pipeline: {len(missing_items)}")
    print(f"🎯 Target limit for this run: {min(len(missing_items), max_limit)} images")
    print(f"🌐 Chrome Profile: {PROFILE_DIRECTORY}")
    print("=" * 70)

    generated_count = 0
    quota_reached = False

    with sync_playwright() as p:
        print(f"[*] Launching Chrome browser with persistent profile ({PROFILE_DIRECTORY})...")
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=CHROME_USER_DATA_DIR,
                channel="chrome",
                headless=False,  # Set False so you can watch execution
                args=[f"--profile-directory={PROFILE_DIRECTORY}"]
            )
        except Exception as e:
            print(f"\n❌ Failed to launch Chrome. Please close Chrome if it is currently open!")
            print(f"   Error details: {e}")
            return {"status": "error", "message": "Close Chrome browser before running automation."}

        page = context.new_page()
        print(f"[*] Navigating to {WEB_UI_URL}...")
        page.goto(WEB_UI_URL)
        page.wait_for_load_state("networkidle")

        print("🌐 Connected to Web UI. Starting image generation loop...\n")

        for item in missing_items:
            if generated_count >= max_limit:
                print(f"\n🛑 Reached batch target limit of {max_limit} images for this run.")
                print(f"   Remaining missing scenes will be generated on your next run!")
                break

            folder_name = item["folder_name"]
            scene_str = item["scene_str"]
            prompt_text = item["prompt"]
            img_path = item["img_path"]
            ref_img = item["ref_image"]
            ref_img_path = os.path.abspath(ref_img)
            if not os.path.exists(ref_img_path):
                ref_img_path = os.path.abspath("female.png")

            print(f"[{generated_count + 1}/{max_limit}] 🎬 {folder_name} -> Scene {scene_str}")

            try:
                # -------------------------------------------------------------
                # 1. ATTACH CHARACTER REFERENCE IMAGE (female.png)
                # -------------------------------------------------------------
                if os.path.exists(ref_img_path):
                    file_input = page.locator("input[type='file']").first
                    if file_input.is_attached():
                        file_input.set_input_files(ref_img_path)
                        print(f"  [+] Attached character reference: {os.path.basename(ref_img_path)}")
                        page.wait_for_timeout(1500)

                # -------------------------------------------------------------
                # 2. INSTANT TEXT PASTE (10ms Clipboard Injection)
                # -------------------------------------------------------------
                input_box = page.locator("div[contenteditable='true'], textarea#prompt-input, .input-area").first
                input_box.focus()
                page.keyboard.insert_text(prompt_text)
                page.wait_for_timeout(500)

                # Submit Prompt
                page.keyboard.press("Enter")
                print("  [>] Submitted prompt to Nano Banana Pro. Waiting for generation...")

                # -------------------------------------------------------------
                # 3. DYNAMIC SMART WAIT (Wait for indicator to detach)
                # -------------------------------------------------------------
                try:
                    page.wait_for_selector(
                        ".loading-spinner, .generating-indicator, button[aria-label='Stop generating']",
                        state="detached",
                        timeout=120000
                    )
                except Exception:
                    page.wait_for_timeout(15000)

                page.wait_for_timeout(2000)

                # Check for rate limit / quota error messages on page
                body_text = page.locator("body").inner_text()
                if "quota exceeded" in body_text.lower() or "limit reached" in body_text.lower() or "try again later" in body_text.lower():
                    print(f"\n⚠️ Rate limit detected on web UI. Stopping cleanly!")
                    quota_reached = True
                    break

                # -------------------------------------------------------------
                # 4. DOWNLOAD / EXTRACT HIGH-RES IMAGE
                # -------------------------------------------------------------
                latest_img = page.locator("img[src*='blob:'], img[src*='googleusercontent']").last
                if latest_img.is_visible():
                    img_url = latest_img.get_attribute("src")

                    if img_url and img_url.startswith("http"):
                        img_response = page.request.get(img_url)
                        with open(img_path, "wb") as img_file:
                            img_file.write(img_response.body())
                        print(f"  [✓] Successfully saved high-res: {img_path}")
                        generated_count += 1
                    else:
                        latest_img.screenshot(path=img_path)
                        print(f"  [✓] Captured element frame: {img_path}")
                        generated_count += 1
                else:
                    print("  [!] Warning: Image element not found in chat response.")

                # -------------------------------------------------------------
                # 5. LAPTOP COOLING PAUSE
                # -------------------------------------------------------------
                print(f"  [☕] Laptop cooling pause: Sleeping {LAPTOP_COOLING_PAUSE}s...")
                time.sleep(LAPTOP_COOLING_PAUSE)

            except Exception as e:
                print(f"  [!] Error processing scene: {e}")
                time.sleep(3)

        print("\n" + "=" * 70)
        print(f"🎉 BATCH RUN SUMMARY:")
        print(f"   - Images Generated This Run: {generated_count}")
        remaining = len(missing_items) - generated_count
        print(f"   - Remaining Missing Scenes: {remaining}")
        if quota_reached:
            print("   - Status: Quota Limit Hit (Resume later)")
        elif remaining > 0:
            print("   - Status: Target Limit Hit (Run again later to resume remaining)")
        else:
            print("   - Status: 100% All Scenes Complete!")
        print("=" * 70)

        context.close()
        return {
            "status": "success",
            "generated_count": generated_count,
            "remaining_count": remaining,
            "quota_reached": quota_reached
        }

if __name__ == "__main__":
    run_web_image_automation()
