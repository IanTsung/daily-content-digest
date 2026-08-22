"""Summarize a transcript using OpenAI GPT-4o.

Structured extraction from transcript into a Chinese markdown brief.
"""
import os

from openai import OpenAI


SUMMARY_PROMPT = """以下是每日內容的 transcript。請結構化總結（用中文，除非原文明顯是英文）：

1. **核心觀點**（3-5 個要點）
2. **關鍵數據 / 位置**（若是 TA：support / resistance / target；其他類型：關鍵引用 / 數字）
3. **提到的 pattern / framework**
4. **風險提示 / 反面觀點**
5. **一句話 today's edge / takeaway**

Transcript：
{transcript}"""


def summarize(source_id: str, item, transcript: str) -> str:
    """Call GPT-4o to produce a structured summary.

    - transcript truncated at 120K chars to keep well within 128K context
      window even after tokenization overhead
    - model: gpt-4o balances quality and cost for structured extraction.
      Swap to gpt-4o-mini (~15x cheaper) if you want to stress-test cost first.
    """
    client = OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": SUMMARY_PROMPT.format(transcript=transcript[:120_000]),
            }
        ],
    )
    return resp.choices[0].message.content or ""
