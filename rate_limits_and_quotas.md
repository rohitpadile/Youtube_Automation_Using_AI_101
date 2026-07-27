# Google AI Studio API — Rate Limits & Quotas Reference Guide

This document explains why Google AI Studio API rate limits occur, how the quota reset window works, and how our studio automation keeps your requests 100% safe.

---

## 1. Why Do Rate Limits (429 RESOURCE_EXHAUSTED) Happen?

Google AI Studio API enforces rate limits at the **Google Cloud Project level**. 

When using a **Free Tier API Key**, Google imposes three main quota boundaries:

| Quota Metric | Free Tier Limit | What Triggers a `429` Rate Limit |
| :--- | :--- | :--- |
| **RPM (Requests Per Minute)** | **15 Requests / Min** | Sending more than 1 request every 4 seconds in a burst. |
| **TPM (Tokens Per Minute)** | **1,000,000 Tokens / Min** | Sending or generating massive text inputs within 60 seconds. |
| **RPD (Requests Per Day)** | **1,500 Requests / Day** | Making more than 1,500 API calls in 24 hours. |
| **Imagen 3 Image Rate Limit** | **~10 Images / Min** | Requesting 16:9 images faster than 1 image every 6 seconds. |

---

## 2. How the Quota Reset Windows Work

1. **RPM (Requests Per Minute) Window**:
   - Measured on a **60-Second Rolling Clock**.
   - If you make 15 requests in 10 seconds, the API locks for the remaining 50 seconds of that minute.
   - **Reset Time**: 15 to 60 seconds.

2. **RPD (Requests Per Day) Window**:
   - Resets daily at **12:00 AM Pacific Time (Midnight PT)**.

---

## 3. Free Tier vs. Paid Tier (Tier 1) Comparison

| Feature | Free Tier (Your Current Key) | Tier 1 (Pay-As-You-Go) |
| :--- | :--- | :--- |
| **Cost** | **$0.00 / month** | Pay per 1M tokens (~$0.07 / 1M tokens for Flash) |
| **RPM (Requests/Min)** | 15 RPM | **1,000 RPM** |
| **TPM (Tokens/Min)** | 1,000,000 TPM | **4,000,000 TPM** |
| **RPD (Requests/Day)** | 1,500 RPD | **Unlimited** |

---

## 4. Our Studio's Built-in Safeguards ("Zero-Hurry Gentle Mode")

To ensure your automated studio runs smoothly overnight without ever failing:

1. **Image Generation Pacing (12s Pause)**:
   - The studio pauses **12 seconds** between each 16:9 scene image generation.
   - This caps image requests at **5 images/minute** (well below the 15 RPM limit).

2. **Overnight Batch Rest Window (60s Pause)**:
   - Between each complete video in your overnight batch, the studio pauses for **60 seconds**.
   - This allows Google AI Studio's 60-second rolling RPM window to reset 100%.

3. **Automatic Exponential Retry Backoff (20s - 40s)**:
   - If a `429 RESOURCE_EXHAUSTED` error occurs, the script automatically pauses for **20 seconds** and retries up to 3 times without crashing.
