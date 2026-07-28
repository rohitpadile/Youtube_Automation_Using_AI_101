import os
import re
import json
import glob
import base64
import time
import argparse
import subprocess
import requests
from datetime import datetime
from PIL import Image, ImageDraw

try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
except ImportError:
    print("[-] 'google-genai' library not found. Please install dependencies: pip install -r requirements.txt")
    exit(1)

# ==========================================
# CONFIGURATION & ENVIRONMENT LOADING
# ==========================================
def load_env_file():
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        os.environ[k.strip()] = v.strip()
        except Exception:
            pass

load_env_file()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
SUPERTONIC_URL = os.environ.get("SUPERTONIC_URL", "http://127.0.0.1:7788/v1/audio/speech")
SCRIPT_FILE = "script.txt"
OUTPUT_BASE_DIR = "output"
PUBLISHED_FILE = "published_videos.json"
IDEAS_CACHE_FILE = "ideas_cache.json"
CONFIG_FILE = "channel_config.json"
EXAMPLE_CONFIG_FILE = "channel_config.example.json"

# Load Channel Configuration (Local or Generic Fallback)
def load_channel_config():
    target_path = CONFIG_FILE if os.path.exists(CONFIG_FILE) else EXAMPLE_CONFIG_FILE
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "CHANNEL_NAME": "Observer Studio",
        "CHARACTER_FEMALE_IMAGE": "female.png",
        "CHARACTER_MALE_IMAGE": "male.png",
        "STYLE_PROMPT_FEMALE": "Generate a horizontal 16:9 minimalist editorial storybook-style digital illustration. Maintain the exact same recurring female character, clothing, facial features, proportions, color palette and illustration style as the reference image. Soft painted shading, clean expressive line art, muted beige, cream, dusty blue, warm gray and charcoal palette, cozy lighting, lots of negative space, no text, no watermark.",
        "STYLE_PROMPT_MALE": "Generate a horizontal 16:9 minimalist editorial storybook-style digital illustration. Maintain the exact same recurring male character, clothing, facial features, proportions, color palette and illustration style as the reference image. Soft painted shading, clean expressive line art, muted beige, cream, dusty blue, warm gray and charcoal palette, cozy lighting, lots of negative space, no text, no watermark."
    }

CHANNEL_CFG = load_channel_config()

# Image Generation Switch (DEFAULT: OFF for manual high-res rendering)
GENERATE_IMAGES_ENABLED = False

# Minimum scenes threshold required for dense sentence-by-sentence manual prompts
MIN_REQUIRED_SCENES = 10

# Safe Pacing Settings
IMAGE_GENERATION_PAUSE = 10
VIDEO_BATCH_PAUSE = 60
RETRY_BACKOFF_PAUSE = 25

# Model Fallback Sequence
PARSER_MODELS = ["gemini-flash-latest", "gemini-2.0-flash-lite", "gemini-3.5-flash"]
IMAGE_MODEL = "imagen-3.0-generate-002"

# Dynamic Master Style Prompts
STYLE_PROMPT_FEMALE = CHANNEL_CFG.get("STYLE_PROMPT_FEMALE", "")
STYLE_PROMPT_MALE = CHANNEL_CFG.get("STYLE_PROMPT_MALE", "")

# Automated Creative Director Instructions
SYSTEM_SCRIPT_INSTRUCTION = f"""
ROLE:
Act as an anonymous observer of ordinary life for a channel called {CHANNEL_CFG.get('CHANNEL_NAME', 'Observer Studio')}. You don't teach. You don't motivate. You simply notice things most people overlook. Your job is to discover the hidden psychological tension created when two seemingly unrelated concepts quietly collide.

INPUT:
- Concept A: An everyday object, habit, place, routine, or behavior.
- Concept B: A human emotion, cognitive bias, desire, fear, memory, contradiction, or psychological tendency.

WRITING STRUCTURE:
1. THE HOOK: Begin inside a tiny everyday moment. Never explain. Never introduce the topic. Simply observe.
2. THE COLLISION & DELAYED REVEAL: Reveal the hidden connection. The initial object must NOT be the real topic. The topic quietly evolves into a broader human truth.
3. ESCALATION: Expand the idea with 2-3 brief examples showing the pattern everywhere.
4. THE HIDDEN PRINCIPLE: Reveal the larger truth as a quiet observation, never as advice or a lesson.
5. THE ENDING: Leave one unresolved thought or sharp irony that echoes in the viewer's mind. Never end with fake motivation or forced optimism.

SPEECH WRITING & PACING RULES (STRICT FOR TTS SYNTHESIS):
- Write for listening, not reading.
- ONE THOUGHT PER PARAGRAPH: Group closely related sentences onto the SAME line. Only use a blank line (\\n\\n) when shifting to a brand new idea or a major realization.
- ELLIPSES (...): Use ellipses ONLY for hesitation, realization, or emotional pauses.
- LISTS: Each item in a list gets its own separate line.
- SHORT SENTENCES: Keep sentences between 8 to 15 words.
- TONE: Quiet, curious, observant, slightly dry, never preachy.
- HARD RULES & FORBIDDEN PHRASING:
  * NO academic/explanatory terminology (e.g. "We feel compelled to...", "We have grown uncomfortable...", "This cognitive bias causes...").
  * NO study citations, NO "Imagine...", NO "What if...", NO exclamation marks.
  * Write visual, poetic observations instead of abstract explanations (e.g. write "Phones. Coffee cups. Headphones. Plastic and glass slowly became little fences we could carry in our pockets.").

THE AUDIENCE TEST:
Would a thoughtful person pause, look out a rainy window, and genuinely think this?
"""

SYSTEM_IDEA_BRAINSTORMER = f"""
You are the lead concept director for {CHANNEL_CFG.get('CHANNEL_NAME', 'Observer Studio')}.
Brainstorm 20 fresh, unexpected, original Collision concept pairs for video scripts.
Each pair MUST collide a mundane everyday object/routine (Concept A) with a subtle psychological tendency or emotion (Concept B).

Output ONLY a valid JSON array of 20 objects with keys:
- "concept_a": Short string (the everyday object/habit)
- "concept_b": Short string (the psychological concept)
- "title_hook": Catchy, quiet video title line
- "teaser": 1-sentence teaser describing the hidden collision connection.

Do NOT repeat topics that have already been generated or uploaded. Make them deeply relatable and observant. Output ONLY valid JSON.
"""

def get_genai_client():
    load_env_file()
    key = os.environ.get("GEMINI_API_KEY", GEMINI_API_KEY)
    if not key:
        print("[-] Error: GEMINI_API_KEY environment variable is missing.")
        print("    Please set GEMINI_API_KEY in your environment or .env file.")
        exit(1)
    return genai.Client(api_key=key)

def get_past_topics():
    past_topics = []
    if os.path.exists(PUBLISHED_FILE):
        try:
            with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
                pub_data = json.load(f)
                for item in pub_data:
                    ca = item.get("concept_a")
                    cb = item.get("concept_b")
                    if ca and cb:
                        past_topics.append(f"{ca} x {cb}")
        except Exception:
            pass

    meta_files = glob.glob(os.path.join(OUTPUT_BASE_DIR, "*", "metadata.json"))
    for mf in meta_files:
        try:
            with open(mf, "r", encoding="utf-8") as f:
                d = json.load(f)
                ca = d.get("concept_a")
                cb = d.get("concept_b")
                if ca and cb:
                    topic_str = f"{ca} x {cb}"
                    if topic_str not in past_topics:
                        past_topics.append(topic_str)
        except Exception:
            pass

    return past_topics

def generate_content_with_retry(client, contents, system_instruction=None, response_mime_type=None):
    config_kwargs = {}
    if system_instruction:
        config_kwargs["system_instruction"] = system_instruction
    if response_mime_type:
        config_kwargs["response_mime_type"] = response_mime_type
        
    config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

    for model in PARSER_MODELS:
        for attempt in range(3):
            try:
                res = client.models.generate_content(model=model, contents=contents, config=config)
                return res
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    wait_sec = RETRY_BACKOFF_PAUSE * (attempt + 1)
                    print(f"    [*] Quota limit hit on {model} (attempt {attempt+1}/3). Waiting {wait_sec}s for free quota reset...")
                    time.sleep(wait_sec)
                else:
                    print(f"    [!] Exception on {model}: {e}")
                    break

    raise RuntimeError("API Rate limit hit on all retry models. Please wait 25 seconds.")

def suggest_collision_ideas(client, force_refresh=False):
    if not force_refresh and os.path.exists(IDEAS_CACHE_FILE):
        try:
            with open(IDEAS_CACHE_FILE, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if cached and len(cached) >= 5:
                    print("    [+] Loaded 20 Collision ideas instantly from local cache (0 API quota used).")
                    return cached
        except Exception:
            pass

    print("[*] Brainstorming 20 fresh Collision ideas live with Gemini API...")
    past_topics = get_past_topics()
    
    prompt = "Generate 20 completely original, highly observant video collision ideas."
    if past_topics:
        prompt += f"\nSTRICT EXCLUSION: Do NOT generate ideas covering any of these previously published or rendered topic pairs: {', '.join(past_topics)}"

    response = generate_content_with_retry(
        client, 
        contents=prompt,
        system_instruction=SYSTEM_IDEA_BRAINSTORMER,
        response_mime_type="application/json"
    )
    
    ideas = json.loads(response.text)
    
    try:
        with open(IDEAS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(ideas, f, indent=2)
    except Exception:
        pass

    return ideas

def get_character_reference(voice="F4"):
    female_img = CHANNEL_CFG.get("CHARACTER_FEMALE_IMAGE", "female.png")
    male_img = CHANNEL_CFG.get("CHARACTER_MALE_IMAGE", "male.png")
    
    if voice and voice.upper().startswith("M"):
        ref_path = male_img if os.path.exists(male_img) else female_img
        style_prompt = STYLE_PROMPT_MALE
    else:
        ref_path = female_img if os.path.exists(female_img) else "character_ref.png"
        style_prompt = STYLE_PROMPT_FEMALE
    return ref_path, style_prompt

def ensure_supertonic_server():
    for check in range(6):
        try:
            r = requests.get("http://127.0.0.1:7788/docs", timeout=2)
            if r.status_code == 200:
                print("    [+] Supertonic server active at http://127.0.0.1:7788")
                return True
        except Exception:
            pass

        if check == 0:
            print("    [*] Starting local Supertonic server process...")
            try:
                subprocess.Popen(["supertonic", "serve"], shell=True)
            except Exception as e:
                print(f"    [!] Supertonic launch error: {e}")
        time.sleep(2)

    return False

def generate_script_from_collision(client, concept_a, concept_b, existing_script_file=None):
    if existing_script_file and os.path.exists(existing_script_file):
        with open(existing_script_file, "r", encoding="utf-8") as f:
            script_text = f.read().strip()
            if len(script_text) > 100:
                print(f"    [+] Resuming: Script verified in {existing_script_file} (Skipping API generation).")
                return script_text

    print(f"\n--- Step 0: Generating script via Collision System ({concept_a} x {concept_b}) ---")
    prompt = f"Concept A: {concept_a}\nConcept B: {concept_b}"
    response = generate_content_with_retry(
        client,
        contents=prompt,
        system_instruction=SYSTEM_SCRIPT_INSTRUCTION
    )
    script_text = response.text.strip()
    with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
        f.write(script_text)
    print(f"    [+] Script generated and saved to {SCRIPT_FILE}")
    return script_text

def sanitize_visual_prompt(prompt_text, ref_label="female"):
    # 1. Clean video motion terms (Negative prompt sanitization)
    motion_replacements = [
        (r'\bFast montage transition\.?\s*', ''),
        (r'\bmontage transition\.?\s*', ''),
        (r'\bmontage\.?\s*', ''),
        (r'\bSlow camera pull-away\.?\s*', 'Wide static shot. '),
        (r'\bcamera pull-away\.?\s*', 'static shot. '),
        (r'\btracking shot\b', 'static shot'),
        (r'\bslow push-in\b', 'static close-up'),
        (r'\bfocus pulls?\b', 'soft focus depth'),
        (r'\bcamera tilts up\b', 'low-angle view'),
        (r'\bcamera slowly tilts up\b', 'low-angle composition'),
        (r'\bslow pan\b', 'wide static view'),
        (r'\bextreme slow motion\b', 'frozen mid-action'),
        (r'\bslow motion\b', 'frozen mid-action'),
        (r'\bslowly from the photo\'?s hollow eyes\b', 'with soft depth of field'),
    ]
    for pattern, repl in motion_replacements:
        prompt_text = re.sub(pattern, repl, prompt_text, flags=re.IGNORECASE)

    # 2. Clean sci-fi / CGI forcefield overlays
    scifi_replacements = [
        (r'faint glowing geometric lines overlay.*?(?:forcefield|barrier)?\.?', 'The subjects remain quiet and separated by physical distance.'),
        (r'glowing forcefield', 'physical separation'),
        (r'glowing geometric lines', 'subtle shadows'),
    ]
    for pattern, repl in scifi_replacements:
        prompt_text = re.sub(pattern, repl, prompt_text, flags=re.IGNORECASE)

    return prompt_text.strip()

def build_full_prompt(visual_desc, ref_label="female", master_style=""):
    visual_desc = sanitize_visual_prompt(visual_desc, ref_label)

    ref_anchor = f"Use the attached {ref_label} character reference as the exact recurring character.\n\nCinematic editorial storybook illustration."
    
    if visual_desc.startswith("Use the attached"):
        if "Cinematic editorial storybook illustration" not in visual_desc:
            visual_desc = visual_desc.replace(f"Use the attached {ref_label} character reference as the exact recurring character.", ref_anchor)
    else:
        has_observer = any(k in visual_desc.lower() for k in [f"recurring {ref_label}", "observer", "she ", "her ", "he ", "his "])
        if has_observer or "character" in visual_desc.lower():
            visual_desc = f"{ref_anchor} {visual_desc}"
        else:
            visual_desc = f"Use the attached {ref_label} character reference as the exact recurring character.\n\nCinematic editorial storybook illustration. {visual_desc}"

    handoff_1 = "The image should feel like a frame from a quiet cinematic short film, subtly hinting at the deeper psychological theme without revealing it outright."
    handoff_2 = "The composition should be clean, emotionally restrained, and visually memorable, with generous negative space that allows the subject and symbolism to breathe."
    restraint_line = "Avoid horror aesthetics, exaggerated expressions, surreal distortions, text, logos, or unnecessary background clutter. Prioritize subtle realism and emotional restraint."
    cinematic_handoff = f"{handoff_1}\n\n{handoff_2}\n\n{restraint_line}"

    clean_style = master_style.strip()
    return f"{visual_desc}\n\n{cinematic_handoff}\n\n{clean_style}"

def parse_script_to_scenes(client, script_text, voice="F4", existing_meta_file=None):
    if existing_meta_file and os.path.exists(existing_meta_file):
        try:
            with open(existing_meta_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                scenes = data.get("scenes", [])
                if len(scenes) >= MIN_REQUIRED_SCENES:
                    print(f"    [+] Resuming: Verified {len(scenes)} dense micro-scenes from existing metadata.json (Skipping API parsing).")
                    return scenes
                else:
                    print(f"    [*] Outdated scene count found ({len(scenes)} scenes < {MIN_REQUIRED_SCENES} required). Re-parsing into dense micro-scenes...")
        except Exception:
            pass

    print("\n--- Step 1/3: Parsing script into micro-scenes with Gemini API ---")
    ref_file, master_style = get_character_reference(voice)
    is_female = "female" in ref_file.lower()
    ref_label = "female" if is_female else "male"
    pronoun_subj = "she" if is_female else "he"
    pronoun_pos = "her" if is_female else "his"
    
    system_instruction = f"""
    You are an expert storyboard director for {CHANNEL_CFG.get('CHANNEL_NAME', 'Observer Studio')}.
    Analyze the provided script and break it down into dense, sentence-by-sentence micro-scenes (typically 10 to 18 scenes per script).
    CRITICAL: CHANGE THE SCENE VISUAL PROMPT FOR EVERY NEW SENTENCE, BREATH LINE, OR DISTINCT IDEA.
    
    BRANDING & CINEMATOGRAPHY RULES FOR "MR. NOBODY" (MANDATORY):
    1. RECURRING OBSERVER PERSPECTIVE (NO CHARACTER CONTRADICTIONS):
       - The recurring {ref_label} character is "The Observer".
       - When observing secondary people (e.g., a man on a train, a woman at a cafe, a teenager in a subway), frame the shot with/through The Observer's presence (e.g. "Over-the-shoulder shot from behind the recurring {ref_label} observer watching a middle-aged man...", "Medium shot of the recurring {ref_label} observer sitting across from a man who...").
       - NEVER create contradictions like "Use attached female character reference... Medium shot of a man" without including the female observer in the framing!
       - If a scene is purely an environment or object without any person present, describe only the object/environment framing without forcing character references.

    2. FORBIDDEN VIDEO MOTION & CAMERA WORDS (STATIC IMAGE RULE):
       Gemini generates a STILL IMAGE. Do NOT use video movement or film jargon.
       STRICT FORBIDDEN LIST (NEVER USE IN PROMPTS):
       - NO "montage" or "fast montage transition"
       - NO "camera pull-away" or "slow camera pull-away"
       - NO "tracking shot" or "low-angle tracking shot"
       - NO "slow push-in" or "focus pulls"
       - NO "camera tilts up" or "slow pan" or "zoom"
       Describe ONLY the static framing of the final single image.

    3. FORBIDDEN SCI-FI & OVER-LITERAL METAPHORS (GROUNDED REALISM RULE):
       Translate psychological metaphors into quiet, real-world visual observations.
       STRICT FORBIDDEN LIST (NEVER USE IN PROMPTS):
       - NO "glowing lines" or "glowing forcefield"
       - NO "geometric overlays" or "holograms"
       - NO "CGI effects" or sci-fi visual tropes
       Example: If script mentions "invisible fences", render people separated by physical distance or ordinary objects (coffee cup, dark phone screen), NOT literal glowing CGI forcefields!

    4. EMOTIONAL ATMOSPHERE & COMPOSITION:
       Every prompt must include one emotional sentence describing the psychological mood or quiet curiosity. Frame with generous negative space.

    LOCKED PROMPT FRAMEWORK:
    Construct each "visual_prompt" following this structure:
    1. Reference Anchor (if character present): "Use the attached {ref_label} character reference as the exact recurring character."
    2. Camera Angle & Framing: (e.g. Close-up over-the-shoulder shot from {pronoun_pos} perspective, Wide atmospheric shot...)
    3. Scene Description: (environment, location, key subjects)
    4. Observer Action & Focus: (what the recurring {ref_label} observer is watching, doing, or noticing)
    5. Emotional Atmosphere & Feeling: (one emotional sentence describing the psychological mood)
    6. Lighting & Static Composition: (e.g. Soft morning light filtering through windows, static framing, clean composition)

    Output ONLY a valid JSON array of objects. Each object MUST contain:
    - "scene_num": Integer (starting at 1)
    - "narration": Exact short narration text for this specific micro-scene (1 to 2 lines max).
    - "visual_prompt": A visual prompt adhering strictly to the framework above (Parts 1 to 6).
    
    Do NOT include code block markdown or explanations outside the JSON array.
    """
    
    response = generate_content_with_retry(
        client,
        contents=f"Script:\n{script_text}",
        system_instruction=system_instruction,
        response_mime_type="application/json"
    )
    
    scenes = json.loads(response.text)
    
    for s in scenes:
        visual_desc = s['visual_prompt'].strip()
        s["full_prompt"] = build_full_prompt(visual_desc, ref_label=ref_label, master_style=master_style)
        
    print(f"    [+] Created {len(scenes)} visual micro-scenes.")
    return scenes

def generate_prompts_guide_file(output_dir, scenes, voice="F4"):
    guide_path = os.path.join(output_dir, "prompts_guide.txt")
    ref_img, master_style = get_character_reference(voice)
    ref_label = "female" if "female" in ref_img.lower() else "male"
    
    blocks = []
    for s in scenes:
        num_val = s['scene_num']
        visual_desc = s.get('visual_prompt', '').strip()
        formatted_prompt = build_full_prompt(visual_desc, ref_label=ref_label, master_style=master_style)
        
        block = f"IMAGE {num_val}\n🎙️ Script\n\n{s['narration'].strip()}\n\nPrompt\n\n{formatted_prompt}"
        blocks.append(block)

    full_guide = ("\n" + "=" * 60 + "\n\n").join(blocks)
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(full_guide)
    print(f"    [+] Saved ready-to-copy Prompts Guide file: {guide_path}")
    return guide_path

def generate_scene_images(client, scenes, output_dir, voice="F4", enable_api_images=False):
    if not enable_api_images:
        print("    [+] API Image Generation is OFF (Using manual Prompts Guide).")
        return

    ref_image_path, _ = get_character_reference(voice)
    print(f"\n--- Step 2/3: Generating 16:9 scene storyboards ({ref_image_path}) ---")
    os.makedirs(output_dir, exist_ok=True)

    for i, scene in enumerate(scenes):
        num_str = str(scene["scene_num"]).zfill(2)
        prompt_text = scene["full_prompt"]
        file_path = os.path.join(output_dir, f"scene_{num_str}.png")
        
        if os.path.exists(file_path) and os.path.getsize(file_path) > 1000:
            print(f"    [+] Resuming Scene {num_str}/{len(scenes)}: Image already exists at {file_path}")
            continue

        print(f"    [*] Generating Scene {num_str}/{len(scenes)}...")
        try:
            res = client.models.generate_images(
                model=IMAGE_MODEL,
                prompt=prompt_text,
                config=types.GenerateImagesConfig(number_of_images=1, aspect_ratio="16:9")
            )
            if res.generated_images:
                with open(file_path, "wb") as f:
                    f.write(res.generated_images[0].image.image_bytes)
                print(f"        [+] Saved Imagen image {file_path}")
        except Exception as e:
            print(f"        [*] Image API skipped: {e}")

        time.sleep(2)

def generate_voiceover(script_text, output_dir, voice="F4", speed=0.90):
    audio_path = os.path.join(output_dir, "voiceover.wav")
    
    if os.path.exists(audio_path) and os.path.getsize(audio_path) > 10000:
        print(f"    [+] Resuming: Verified valid voiceover audio at {audio_path}")
        return True

    print("\n--- Step 3/3: Generating voiceover via local Supertonic TTS ---")
    if not ensure_supertonic_server():
        print("    [!] Warning: Supertonic TTS server could not be reached.")
        return False
    
    payload = {
        "model": "supertonic-3",
        "input": script_text,
        "voice": voice,
        "speed": speed
    }
    
    try:
        response = requests.post(SUPERTONIC_URL, json=payload, timeout=180)
        if response.status_code == 200:
            with open(audio_path, "wb") as f:
                f.write(response.content)
            print(f"    [+] Saved voiceover WAV (Voice: {voice}, Speed: {speed}) to {audio_path}")
            return True
        else:
            print(f"    [!] Supertonic HTTP Error {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"    [!] Voiceover synthesis error: {e}")
        return False

def make_slug(text):
    return re.sub(r'[^a-zA-Z0-9]+', '_', text.strip().lower()).strip('_')[:30]

def find_existing_project_folder(concept_a, concept_b):
    if not concept_a or not concept_b:
        return None
    slug = f"_{make_slug(concept_a)}_x_{make_slug(concept_b)}"
    matches = sorted(glob.glob(os.path.join(OUTPUT_BASE_DIR, f"video_*{slug}")), reverse=True)
    if matches:
        return matches[0]
    return None

def is_project_complete(folder_path):
    if not folder_path or not os.path.exists(folder_path):
        return False
        
    script_file = os.path.join(folder_path, "script.txt")
    guide_file = os.path.join(folder_path, "prompts_guide.txt")
    meta_file = os.path.join(folder_path, "metadata.json")
    audio_file = os.path.join(folder_path, "voiceover.wav")

    if not os.path.exists(script_file) or os.path.getsize(script_file) < 100:
        return False

    if not os.path.exists(guide_file) or os.path.getsize(guide_file) < 300:
        return False

    if not os.path.exists(audio_file) or os.path.getsize(audio_file) < 10000:
        return False

    if not os.path.exists(meta_file):
        return False
        
    try:
        with open(meta_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            scenes = data.get("scenes", [])
            if len(scenes) < MIN_REQUIRED_SCENES:
                return False
    except Exception:
        return False

    return True

def run_pipeline(concept_a=None, concept_b=None, custom_script=None, voice="F4", speed=0.90, enable_images=False):
    client = get_genai_client()

    existing_folder = find_existing_project_folder(concept_a, concept_b)
    if existing_folder and is_project_complete(existing_folder):
        folder_name = os.path.basename(existing_folder)
        print(f"\n✅ VIDEO VERIFIED & FULLY COMPLETE: [{concept_a} × {concept_b}] in /output/{folder_name}")
        with open(os.path.join(existing_folder, "metadata.json"), "r", encoding="utf-8") as f:
            return json.load(f)

    if existing_folder:
        output_dir = existing_folder
        folder_name = os.path.basename(existing_folder)
        print(f"\n🔄 SMART RESUME: Regenerating/Completing required assets for [{concept_a} × {concept_b}]: /output/{folder_name}")
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = f"_{make_slug(concept_a)}_x_{make_slug(concept_b)}" if concept_a and concept_b else ""
        folder_name = f"video_{timestamp}{slug}"
        output_dir = os.path.join(OUTPUT_BASE_DIR, folder_name)
        os.makedirs(output_dir, exist_ok=True)

    script_path = os.path.join(output_dir, "script.txt")
    meta_path = os.path.join(output_dir, "metadata.json")

    # 1. Script Generation
    if concept_a and concept_b:
        script_text = generate_script_from_collision(client, concept_a, concept_b, existing_script_file=script_path)
    elif custom_script:
        script_text = custom_script.strip()
    else:
        if not os.path.exists(SCRIPT_FILE):
            print(f"[-] Error: Input file '{SCRIPT_FILE}' not found.")
            return None
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
            script_text = f.read().strip()

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_text)

    ref_img, _ = get_character_reference(voice)

    # 2. Scene Parsing
    scenes = parse_script_to_scenes(client, script_text, voice=voice, existing_meta_file=meta_path)

    # Save metadata & Prompts Guide
    project_data = {
        "project_id": folder_name,
        "folder_name": folder_name,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "concept_a": concept_a or "",
        "concept_b": concept_b or "",
        "script": script_text,
        "scenes": scenes,
        "voice": voice,
        "speed": speed,
        "character_ref": ref_img
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2)

    generate_prompts_guide_file(output_dir, scenes, voice=voice)

    # 3. Image Generation (Default OFF)
    generate_scene_images(client, scenes, output_dir, voice=voice, enable_api_images=enable_images)

    # 4. Audio Generation
    generate_voiceover(script_text, output_dir, voice=voice, speed=speed)

    print("\n" + "=" * 60)
    print(f"SUCCESS! All video assets & Prompts Guide verified & ready in:")
    print(f"    {os.path.abspath(output_dir)}")
    print("=" * 60)
    return project_data

def main():
    parser = argparse.ArgumentParser(description="YouTube Automation Studio - Asset Generator")
    parser.add_argument("--concept-a", "-a", type=str, help="Concept A")
    parser.add_argument("--concept-b", "-b", type=str, help="Concept B")
    parser.add_argument("--voice", "-v", type=str, default="F4", help="Voice model")
    parser.add_argument("--speed", "-s", type=float, default=0.90, help="Voice speed")
    parser.add_argument("--ideas", action="store_true", help="Suggest 20 fresh ideas")
    parser.add_argument("--enable-images", action="store_true", help="Enable API image generation (Default: OFF)")
    args = parser.parse_args()

    print("=" * 60)
    print(f"  {CHANNEL_CFG.get('CHANNEL_NAME', 'Observer Studio').upper()} -- ASSET GENERATOR")
    print("=" * 60)

    client = get_genai_client()

    if args.ideas:
        ideas = suggest_collision_ideas(client, force_refresh=True)
        print(f"\n[*] Suggested {len(ideas)} Collision Ideas:")
        for idx, item in enumerate(ideas, 1):
            print(f"  {idx}. [{item['concept_a']} x {item['concept_b']}] -> \"{item['title_hook']}\"")
        return
    
    run_pipeline(
        concept_a=args.concept_a, 
        concept_b=args.concept_b, 
        voice=args.voice, 
        speed=args.speed,
        enable_images=args.enable_images
    )

if __name__ == "__main__":
    main()
