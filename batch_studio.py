import os
import json
import time
from generate_studio import run_pipeline, is_project_complete, find_existing_project_folder

QUEUE_FILE = "weekly_queue.json"

def run_approved_batch(selected_ideas=None, voice="F4", speed=0.90):
    print("=" * 65)
    print("  🌙 MR. NOBODY STUDIO - OVERNIGHT APPROVED BATCH GENERATOR")
    print("  (Zero-Hurry Gentle Mode: 60s Rest Window Between Videos)")
    print("=" * 65)

    if selected_ideas and isinstance(selected_ideas, list) and len(selected_ideas) > 0:
        queue = selected_ideas
    else:
        if not os.path.exists(QUEUE_FILE):
            print("[-] Error: weekly_queue.json not found. Please add items to queue in Dashboard first.")
            return

        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        queue = data if isinstance(data, list) else data.get("queue", [])
        
    if not queue:
        print("[-] Weekly queue is empty. Add ideas to queue on Dashboard first.")
        return

    print(f"  [+] Loaded {len(queue)} EXPLICITLY APPROVED user ideas for this batch.\n")
    print(f"🚀 Starting batch generation of {len(queue)} videos for this week...\n")

    completed_count = 0

    for idx, item in enumerate(queue, 1):
        ca = item.get("concept_a")
        cb = item.get("concept_b")
        target_dur = item.get("target_duration", 1.5)

        print("=" * 60)
        print(f" 🎬 VIDEO {idx}/{len(queue)}: [{ca} × {cb}] (Target: {target_dur} mins)")
        print("=" * 60)

        existing_folder = find_existing_project_folder(ca, cb)
        if existing_folder and is_project_complete(existing_folder):
            print(f"    ✅ Video {idx} ALREADY COMPLETED in /output/{os.path.basename(existing_folder)}! (Skipping)")
            completed_count += 1
            continue

        try:
            proj = run_pipeline(
                concept_a=ca,
                concept_b=cb,
                voice=voice,
                speed=speed,
                enable_images=False,
                target_duration=target_dur
            )
            completed_count += 1
            print(f"\n    ✅ Video {idx} complete! Saved in /output/{proj['folder_name']}")
        except Exception as e:
            print(f"\n    ❌ Error generating Video {idx}: {e}")

        if idx < len(queue):
            print("\n    ⏳ Gentle Rest Mode: Pausing 60 seconds to reset rolling quota window...\n")
            time.sleep(60)

    print("\n" + "=" * 65)
    if completed_count == len(queue):
        print(f"🎉 ALL BATCH VIDEOS ALREADY COMPLETED ({completed_count}/{len(queue)})! Select new topics from the AI Brainstormer to start fresh.")
    else:
        print(f"✨ BATCH GENERATION FINISHED! ({completed_count}/{len(queue)} completed)")
    print("=" * 65)

# Alias for backward compatibility with app.py imports
run_overnight_batch = run_approved_batch

if __name__ == "__main__":
    run_approved_batch()
