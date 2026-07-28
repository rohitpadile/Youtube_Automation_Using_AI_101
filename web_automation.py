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
CHROME_USER_DATA_DIR = os.path.expanduser("~") + r"\AppData\Local\Google\Chrome\User Data"
PROFILE_DIRECTORY = os.environ.get("CHROME_PROFILE", "Default")
WEB_UI_URL = "https://gemini.google.com/app"

MAX_VIDEOS_PER_RUN = 2       # Cap at exactly 2 complete video packages per run
LAPTOP_COOLING_PAUSE = 10   # Seconds pause between scene generations

def find_incomplete_projects(output_dir="output"):
    """
    Groups missing scenes by video project.
    Returns a list of project dictionaries that have ungenerated/missing scene images.
    """
    incomplete_projects = []
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

        # Find missing scenes for this project
        missing_scenes = []
        for s in scenes:
            num_val = s.get("scene_num", 1)
            num_str = str(num_val).zfill(2)
            img_path = os.path.join(folder, f"scene_{num_str}.png")

            if not os.path.exists(img_path) or os.path.getsize(img_path) < 5000:
                prompt_to_send = s.get("full_prompt") or s.get("visual_prompt", "")
                missing_scenes.append({
                    "scene_num": num_val,
                    "scene_str": num_str,
                    "img_path": img_path,
                    "prompt": prompt_to_send
                })

        if missing_scenes:
            incomplete_projects.append({
                "folder": folder,
                "folder_name": os.path.basename(folder),
                "ref_image": ref_image,
                "total_scenes": len(scenes),
                "missing_scenes": missing_scenes
            })

    return incomplete_projects

def run_web_image_automation(max_videos=MAX_VIDEOS_PER_RUN):
    """
    Launches Chrome via Playwright with persistent AI Pro login.
    Processes up to max_videos complete video packages per run.
    Starts a fresh Gemini chat session for every video.
    """
    incomplete_projects = find_incomplete_projects()

    if not incomplete_projects:
        print("\n✅ All video projects in /output already have 100% complete scene images!")
        return {"status": "complete", "processed_videos": 0, "remaining_videos": 0}

    target_projects = incomplete_projects[:max_videos]

    print("=" * 70)
    print(f"🚀 PLAYWRIGHT WEB AUTOMATION (Google AI Pro - Nano Banana)")
    print(f"📁 Incomplete video projects in pipeline: {len(incomplete_projects)}")
    print(f"🎯 Target videos for this run: {len(target_projects)} complete videos")
    print(f"💬 Fresh Chat Thread per Video: ENABLED")
    print(f"🌐 Chrome Profile: {PROFILE_DIRECTORY}")
    print("=" * 70)

    total_images_rendered = 0
    quota_reached = False

    with sync_playwright() as p:
        print(f"[*] Launching Chrome with persistent profile ({PROFILE_DIRECTORY})...")
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=CHROME_USER_DATA_DIR,
                channel="chrome",
                headless=False,
                args=[
                    f"--profile-directory={PROFILE_DIRECTORY}",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
        except Exception as e:
            print(f"\n❌ Could not launch Chrome. Please make sure Google Chrome is closed!")
            print(f"   Error details: {e}")
            return {"status": "error", "message": "Please close Google Chrome browser before running automation."}

        page = context.pages[0] if context.pages else context.new_page()
        page.bring_to_front()
        time.sleep(1)

        # -------------------------------------------------------------
        # PROCESS EACH VIDEO PACKAGE (UP TO 2 VIDEOS PER RUN)
        # -------------------------------------------------------------
        for proj_idx, proj in enumerate(target_projects, 1):
            if quota_reached:
                break

            folder_name = proj["folder_name"]
            ref_img = proj["ref_image"]
            ref_img_path = os.path.abspath(ref_img)
            if not os.path.exists(ref_img_path):
                ref_img_path = os.path.abspath("female.png")

            missing_scenes = proj["missing_scenes"]

            print(f"\n" + "─" * 60)
            print(f"🎬 VIDEO {proj_idx}/{len(target_projects)}: {folder_name}")
            print(f"📊 Processing {len(missing_scenes)} missing scenes (Total scenes: {proj['total_scenes']})")
            print(f"─" * 60)

            # STEP A: START A FRESH CHAT SESSION FOR THIS VIDEO
            print(f"  [🌐] Navigating to fresh Gemini chat for {folder_name}...")
            try:
                page.goto(WEB_UI_URL, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(2000)

                # Click 'New chat' button if page was already on an existing thread
                new_chat_btn = page.locator("a[aria-label='New chat'], button[aria-label='New chat'], .new-chat-button").first
                if new_chat_btn.is_visible(timeout=3000):
                    new_chat_btn.click()
                    page.wait_for_timeout(2000)
            except Exception as e:
                print(f"  [!] Navigation warning: {e}")

            # STEP B: PROCESS ALL SCENES FOR THIS VIDEO
            for scene_item in missing_scenes:
                scene_num = scene_item["scene_num"]
                scene_str = scene_item["scene_str"]
                prompt_text = scene_item["prompt"]
                img_path = scene_item["img_path"]

                print(f"\n  [Scene {scene_str}/{proj['total_scenes']}] Generating image...")

                try:
                    # 1. Attach female.png character reference
                    if os.path.exists(ref_img_path):
                        file_input = page.locator("input[type='file']").first
                        if file_input.is_attached():
                            file_input.set_input_files(ref_img_path)
                            print(f"    [+] Attached character reference: {os.path.basename(ref_img_path)}")
                            page.wait_for_timeout(1500)

                    # 2. Instant Text Paste (10ms Clipboard Injection)
                    input_box = page.locator("div[contenteditable='true'], textarea#prompt-input, .input-area").first
                    input_box.focus()
                    page.keyboard.insert_text(prompt_text)
                    page.wait_for_timeout(500)

                    # Submit Prompt
                    page.keyboard.press("Enter")
                    print("    [>] Submitted prompt to Nano Banana Pro. Rendering...")

                    # 3. Dynamic Smart Wait
                    try:
                        page.wait_for_selector(
                            ".loading-spinner, .generating-indicator, button[aria-label='Stop generating']",
                            state="detached",
                            timeout=120000
                        )
                    except Exception:
                        page.wait_for_timeout(15000)

                    page.wait_for_timeout(2000)

                    # Check for rate limit / quota warning on page
                    body_text = page.locator("body").inner_text()
                    if "quota exceeded" in body_text.lower() or "limit reached" in body_text.lower() or "try again later" in body_text.lower():
                        print(f"\n⚠️ Rate limit hit on web UI. Stopping cleanly!")
                        quota_reached = True
                        break

                    # 4. Download / Extract High-Res Master Image
                    latest_img = page.locator("img[src*='blob:'], img[src*='googleusercontent']").last
                    if latest_img.is_visible():
                        img_url = latest_img.get_attribute("src") or ""

                        if "googleusercontent.com" in img_url:
                            img_url = re.sub(r'=s\d+', '=s0', img_url)
                            img_url = re.sub(r'=w\d+', '=w3840', img_url)

                        if img_url.startswith("http"):
                            img_response = page.request.get(img_url)
                            with open(img_path, "wb") as img_file:
                                img_file.write(img_response.body())
                            print(f"    [✓] Saved High-Res Image: {os.path.basename(img_path)}")
                            total_images_rendered += 1

                        elif img_url.startswith("blob:"):
                            base64_data = page.evaluate("""async (blobUrl) => {
                                const response = await fetch(blobUrl);
                                const blob = await response.blob();
                                return new Promise((resolve) => {
                                    const reader = new FileReader();
                                    reader.onloadend = () => resolve(reader.result.split(',')[1]);
                                    reader.readAsDataURL(blob);
                                });
                            }""", img_url)
                            import base64
                            with open(img_path, "wb") as img_file:
                                img_file.write(base64.b64decode(base64_data))
                            print(f"    [✓] Extracted Full-Res Blob Image: {os.path.basename(img_path)}")
                            total_images_rendered += 1
                        else:
                            latest_img.screenshot(path=img_path)
                            print(f"    [✓] Captured Frame: {os.path.basename(img_path)}")
                            total_images_rendered += 1
                    else:
                        print("    [!] Warning: Image element not found in response.")

                    # 5. Laptop Cooling Pause
                    print(f"    [☕] Laptop cooling pause: Sleeping {LAPTOP_COOLING_PAUSE}s...")
                    time.sleep(LAPTOP_COOLING_PAUSE)

                except Exception as e:
                    print(f"    [!] Error generating scene {scene_str}: {e}")
                    time.sleep(3)

        print("\n" + "=" * 70)
        print(f"🎉 BATCH EXECUTION COMPLETED:")
        print(f"   - Total Images Rendered: {total_images_rendered}")
        remaining = len(incomplete_projects) - len(target_projects)
        print(f"   - Remaining Incomplete Videos: {remaining}")
        print("=" * 70)

        context.close()
        return {
            "status": "success",
            "images_rendered": total_images_rendered,
            "processed_videos": len(target_projects),
            "remaining_videos": remaining
        }

if __name__ == "__main__":
    run_web_image_automation()
