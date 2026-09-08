import os
import json
import base64
import hashlib
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

FAKE_VISION = os.getenv("MEDDECK_FAKE_VISION") == "1"
vision_calls = 0  # how many times the model was actually invoked

_client = None


def _get_client() -> OpenAI:
    """Build the OpenRouter client lazily so importing this module needs no key."""
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )
    return _client

_FAKE_BANK = [
    ("Most common cause of community-acquired pneumonia?", "Streptococcus pneumoniae."),
    ("First-line treatment for anaphylaxis?", "Intramuscular epinephrine."),
    ("Antidote for acetaminophen overdose?", "N-acetylcysteine."),
    ("Clotting factor deficient in hemophilia A?", "Factor VIII."),
    ("Acid-base disturbance from prolonged vomiting?", "Metabolic alkalosis."),
    ("Most common type of kidney stone?", "Calcium oxalate."),
]


def _fake_card(image_base64: str) -> dict:
    idx = int(hashlib.sha256(image_base64.encode()).hexdigest(), 16) % len(_FAKE_BANK)
    front, back = _FAKE_BANK[idx]
    return {
        "is_question": True,
        "question": front,
        "correct_answer": back,
        "explanation": back,
        "anki_front": front,
        "anki_back": back,
    }


def generate_anki_card(image_base64: str) -> dict:
    global vision_calls
    vision_calls += 1
    if FAKE_VISION:
        return _fake_card(image_base64)

    prompt = """This is a screenshot the user took.
First, determine if this is a medical exam/study question with a clear correct answer.

If it IS a medical question, return JSON only, no markdown:
{
  "is_question": true,
  "question": "the full question text, preserved verbatim with all clinical details (patient age, sex, symptoms, vitals, lab values, history). Do not summarize or paraphrase.",
  "correct_answer": "the correct answer option letter and full text exactly as written",
  "explanation": "the full explanation from the question bank, preserving clinical reasoning and key details. Do not over-condense.",
  "anki_front": "the question as written, keeping the clinical vignette intact. Include the patient presentation, key findings, and the actual question being asked. Do not collapse the vignette into a single short sentence.",
  "anki_back": "the correct answer with the full clinical reasoning. Include why this answer is correct AND briefly why the other key distractors are wrong if mentioned. Should be thorough enough to actually learn from, not just memorize."
}

If it is NOT a medical question (e.g., a random screenshot, chat, webpage), return:
{
  "is_question": false,
  "reason": "brief explanation of what the image actually is"
}"""

    response = _get_client().chat.completions.create(
        model="nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ]
    )
    
    content = response.choices[0].message.content
    
    if not content:
        # Model returned empty — likely rate limited or filtered
        raise Exception("Model returned empty response. Try again or switch models.")
    
    content = content.replace("```json", "").replace("```", "").strip()
    
    # Find first { and last } to extract JSON even if there's surrounding text
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1:
        content = content[start:end+1]
    
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return json.loads(content, strict=False)