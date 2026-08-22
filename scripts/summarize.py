"""Summarize a transcript using the Claude API.

Uses Opus 4.7 with adaptive thinking + medium effort — balances quality and
cost for structured extraction. See Anthropic docs for effort/thinking tuning.
"""
import os

from anthropic import Anthropic


SUMMARY_PROMPT = """以下是每日內容的 transcript。請結構化總結（用中文，除非原文明顯是英文）：

1. **核心觀點**（3-5 個要點）
2. **關鍵數據 / 位置**（若是 TA：support / resistance / target；其他類型：關鍵引用 / 數字）
3. **提到的 pattern / framework**
4. **風險提示 / 反面觀點**
5. **一句話 today's edge / takeaway**

Transcript：
{transcript}"""


def summarize(source_id: str, item, transcript: str) -> str:
    """Call Claude to produce a structured summary.

    - transcript truncated at 120K chars to keep well within 1M context window
      even after tokenization overhead
    - thinking: adaptive so the model decides how much reasoning is needed
    - effort: medium — good quality/cost balance for daily automated jobs
    """
    client = Anthropic()
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2000,
        thinking={"type": "adaptive"},
        output_config={"effort": "medium"},
        messages=[
            {
                "role": "user",
                "content": SUMMARY_PROMPT.format(transcript=transcript[:120_000]),
            }
        ],
    )
    # response.content is a list of blocks (thinking + text). Extract text only.
    for block in response.content:
        if block.type == "text":
            return block.text
    return ""
