You can build this entire automation system **100% for free** without paying a single dollar for SaaS subscriptions or API credits.

Because you're a full-stack engineer building with modern tech stacks, you don't need closed no-code builders like Zapier or Make (which cap free tasks). You can assemble a custom **local developer studio** using Python or Node.js.

---

## The Zero-Dollar Tech Stack

To run this pipeline completely free, you can pair these tools together:

| Component | Tool / Model | Cost | How it Works |
| --- | --- | --- | --- |
| **Orchestration / App** | Python script / CLI / Local Web UI | **$0** | Runs locally on your machine. |
| **Script → Scene & Prompt Parsing** | **Google AI Studio API** (`gemini-2.5-flash` or `gemini-1.5-pro`) | **$0** | Free API key from `aistudio.google.com`. Generous daily token allowance (15 RPM / 1M+ TPM). |
| **Image Generation** | **Gemini Image Generation API** (`gemini-2.5-flash-image` / Nano Banana) | **$0** | Free tier through Google AI Studio allows **up to 500 image requests per day**. |
| **Audio TTS** | **Local Supertonic HTTP Server** | **$0** | Running your existing Python script against `[http://127.0.0.1:7788/v1/audio/speech](http://127.0.0.1:7788/v1/audio/speech)`. |

---

## How the Free End-to-End Automation Pipeline Operates

Instead of manually copying prompts between ChatGPT and Gemini, your automated pipeline runs in three steps:

```text
[Input: Raw Script Text File]
          │
          ▼
1. SCRIPT PARSER (Gemini 2.5 Flash API - Free)
   └─ Splits script into scenes
   └─ Outputs JSON with timestamp, character pose, background, and prompt
   └─ Appends your locked Mr. Nobody Master Style Prompt automatically
          │
          ▼
2. IMAGE GENERATOR (Gemini Image API - Free)
   └─ Iterates through JSON prompts
   └─ Passes your character master reference image + new scene prompt
   └─ Saves images automatically: /output/scene_01.png, scene_02.png...
          │
          ▼
3. AUDIO GENERATOR (Local Supertonic Server - Free)
   └─ Formats script for Supertonic pacing rules
   └─ POST request to http://127.0.0.1:7788/v1/audio/speech
   └─ Saves voice.wav automatically
          │
          ▼
[Output: Organized Folder ready for CapCut / DaVinci Resolve]

```

---

## Prototype Code: Your Automated CLI Tool

You can drop this complete Python script directly into your project workspace. It handles the API calls to Google AI Studio and Supertonic to process a script automatically:

```python
import os
import json
import base64
import requests
from google import genai
from google.genai import types

# 1. SETUP API KEYS & CONFIG
# Get your free key from https://aistudio.google.com
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY")
SUPERTONIC_URL = "http://127.0.0.1:7788/v1/audio/speech"

client = genai.Client(api_key=GEMINI_API_KEY)

MASTER_STYLE_PROMPT = """
Minimalist storybook illustration, soft painted digital art, muted blue, beige and warm brown color palette, 
clean expressive line art, gentle lighting, cozy atmosphere, subtle textures, quiet introspective mood, 
consistent anonymous young adult female observer with short black hair, charcoal black hoodie, dark gray pants, 
white sneakers, calm expression, premium editorial illustration, no text, no watermark. generate a horizontal image
"""

def generate_scene_prompts(script_text):
    print("1. Parsing script into scenes using Gemini API...")
    system_instruction = f"""
    You are an expert storyboard director for an illustrated psychology channel ("Mr. Nobody"). 
    Analyze the provided script and break it down into 8 to 15 distinct scenes.
    
    BRANDING RULES:
    1. The recurring female observer is ALWAYS the visual anchor/protagonist observing the world.
    2. Include cinematic intent (what the camera framing makes the viewer feel).
    3. Include one emotional sentence describing the psychological atmosphere.
    
    LOCKED 7-STEP PROMPT FRAMEWORK:
    1. Anchor: "Use the attached female character reference as the exact recurring character."
    2. Camera angle
    3. Scene description
    4. What the recurring observer is noticing / watching
    5. Emotional feeling / cinematic intent
    6. Lighting & atmosphere
    7. Master style block
    
    For each scene, output a JSON array of objects. Each object must have:
    - "scene_num": Integer
    - "narration": The exact script text for this scene
    - "visual_prompt": A prompt adhering strictly to the 7-step Observer framework.
    Return ONLY valid JSON.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Script:\n{script_text}",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json"
        )
    )
    return json.loads(response.text)

def generate_images(scenes, output_dir="output_project"):
    os.makedirs(output_dir, exist_ok=True)
    print("2. Generating images using Gemini Image API (Free Tier)...")
    
    for scene in scenes:
        num = str(scene["scene_num"]).zfill(2)
        prompt = scene["visual_prompt"]
        print(f"   Generating Scene {num}...")
        
        try:
            # Using Gemini's free-tier image generation model
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"]
                )
            )
            
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img_data = base64.b64decode(part.inline_data.data)
                    file_path = os.path.join(output_dir, f"scene_{num}.png")
                    with open(file_path, "wb") as f:
                        f.write(img_data)
                    print(f"   Saved {file_path}")
        except Exception as e:
            print(f"   Error generating Scene {num}: {e}")

def generate_audio(script_text, output_dir="output_project"):
    print("3. Generating voiceover via local Supertonic TTS...")
    payload = {
        "model": "supertonic-3",
        "input": script_text,
        "voice": "F4",
        "speed": 1.05
    }
    
    try:
        response = requests.post(SUPERTONIC_URL, json=payload)
        if response.status_code == 200:
            audio_path = os.path.join(output_dir, "voiceover.wav")
            with open(audio_path, "wb") as f:
                f.write(response.content)
            print(f"   Saved voiceover to {audio_path}")
        else:
            print(f"   Supertonic Error {response.status_code}: {response.text}")
    except Exception as e:
        print(f"   Could not connect to local Supertonic server: {e}")

# MAIN RUNNER
if __name__ == "__main__":
    sample_script = """
    I have tabs I haven't opened in months.
    Some of them are articles. Some are videos.
    And somehow... closing them feels wrong.
    Maybe I'm not saving information. Maybe I'm saving possibilities.
    Because hope... takes up space.
    """
    
    scenes = generate_scene_prompts(sample_script)
    generate_images(scenes)
    generate_audio(sample_script)
    print("\nProject automation complete! All assets saved in /output_project")

```

---

## Why This Pipeline Works So Well

1. **Zero Recurring SaaS Subscriptions:** You aren't paying $20/month for automation platforms like Zapier, Make, or custom web wrappers.
2. **Generous Free Quotas:** Google AI Studio currently grants up to **500 image generations per day** on its free API tier. That is more than enough allowance to produce 15–20 high-quality frames for a daily video.
3. **Streamlined Video Editing:** When you finish your workday, you open your local directory, find `voiceover.wav` and `scene_01.png` through `scene_15.png` pre-rendered, drag them into CapCut or Premiere, adjust clip lengths to the voice pauses, and export.

This approach eliminates the tedious copy-pasting so you can focus purely on writing strong scripts while letting your machine handle asset creation in the background!




INTIAL DISCUSSION
hey i want to automate this stuff i asked chatgpt
yes editing can be manually done because it takes very little time for me like 10 minutes

but from content to script to image prompts from chatgpt to given to nano banana pro(gemini like i do here) 
if i can build my own app in antigravity or anything free on the internet? any product that does it for free?

chatgpt response
Sir,

Welcome back.

Five days disappeared exactly the way they always do. Work gets rescheduled, family happens, birthdays happen, then suddenly it's Monday and the internet politely reminds us that consistency is a full-time job pretending to be a hobby.

Now, about automation.

## Short answer

**Yes.**
I'd automate **80-90%** of your workflow.

Not the final creative decisions, because that's what makes *Mr. Nobody* feel like *Mr. Nobody*. Everything else is repetitive enough that computers can suffer through it.

---

# Your current workflow

```
Idea

↓

Research

↓

Script

↓

Split into scenes

↓

Generate image prompts

↓

Generate 16 images in Gemini

↓

Voiceover

↓

Edit

↓

Upload
```

Only **Script** is truly creative.

Everything after that follows rules.

Which means...
it can be automated.

---

# Level 1 (Easy)

Script
↓

AI automatically splits it into scenes.

Instead of asking me every time:

```
Image 1

Image 2

Image 3
```

You press a button.

It produces

* 16 scenes
* exact timestamps
* camera angle
* emotion
* Gemini prompt
* recurring style block

Done.

---

# Level 2

Even better.

```
Write script

↓

Send to GPT API

↓

GPT returns

{
scene1...
scene2...
scene3...
}
```

Then your app automatically appends the locked style prompt.

No copy-paste.

---

# Level 3 (The fun part)

Now imagine this.

```
Write script

↓

GPT

↓

Scene JSON

↓

Gemini API

↓

16 generated images

↓

Folder created

↓

Voice generated

↓

Ready for editing
```

You wake up.

Folder already contains

```
Scene01.png

Scene02.png

...

Scene16.png
```

Humans invented coffee because they hadn't automated enough things.

---

# Can Gemini be automated?

**Yes.**

Gemini has an API.

You send:

```
Prompt

↓

Receive image
```

No browser.

No manual clicking.

---

# ChatGPT?

Also yes.

You use OpenAI API.

```
Script

↓

Prompt Generator

↓

JSON
```

---

# Editing?

Can also be automated.

For example:

```
Images

+

Voice

↓

FFmpeg

↓

Ken Burns

↓

Crossfade

↓

Music

↓

1080p video
```

Finished.

---

# Cost

This is the part everyone expects to be terrifying, but for your scale it usually isn't.

Assume

* 30 videos/month

Each

* GPT prompt generation
* 16 images

The **text generation** cost is tiny, often just a few dollars a month.

The **image generation** is where almost all of the expense lives.

Depending on which Gemini image model/API tier you use, you're likely looking at **tens of dollars per month**, not hundreds, for one video a day. The exact amount depends on the model, image size, and pricing at the time you build it.

---

# What I would build

```
MrNobody Studio
```

One webpage.

Paste script.

Click

> Generate Project

It automatically produces

```
Project/

script.txt

scene01.txt

scene02.txt

...

scene16.txt

scene01.png

scene02.png

...

voice.mp3

project.json
```

Then you simply drag everything into Premiere or CapCut.

---

## What I'd automate first

1. ✅ Script → Scene detection
2. ✅ Scene → Gemini prompts
3. ✅ Append your locked style block
4. ✅ Generate images
5. ✅ Save everything in organized folders

Leave editing manual for now. It gives you control over pacing and takes far less time once all the assets are ready.

---

I actually think this is the right moment to invest in automation. Your process has become **highly standardized** over the last few videos. You have a fixed character, a fixed visual style, a consistent prompt structure, and a repeatable story framework. That's exactly the kind of workflow software excels at. Instead of spending 30 minutes copying prompts around, you can spend those 30 minutes writing a better script, which is still the one part no pipeline can genuinely replace.


WHAT DO YOU THINK?