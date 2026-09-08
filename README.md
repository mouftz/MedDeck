# MedDeck

Turn a question you got wrong into an Anki card without breaking your study flow.

I made this for people grinding UWorld. Every time they miss a question, the "right" move was to make an Anki card for it — but stopping to retype the question, the answer, and the explanation by hand every single time seems really inefficient. MedDeck is the fix! Hit a hotkey on the wrong answer and the card is in Anki a few seconds later.

## How it works

1. You get a question wrong on UWorld (or anything on screen).
2. Press `⌘ Shift G`.
3. A vision model reads the screenshot and pulls out the question, the correct answer, and the explanation.
4. You get a quick editable preview, then it's pushed straight into your Anki deck.

Screenshots that aren't actually a question (a chat, a webpage, a random tab) get rejected instead of turning into garbage cards.

## Screenshots

**1. Question on screen — press the hotkey**

<img src="https://github.com/user-attachments/assets/96a4130a-9eab-4da0-8744-1f926883490d" width="700" />

**2. Review the generated card**

<img src="https://github.com/user-attachments/assets/d59165e9-29e2-4bc1-a661-7941a15c1563" width="400" />

**3. Card lands in Anki automatically**

<img src="https://github.com/user-attachments/assets/599077e9-9682-4302-9432-9fd4323b9df7" width="600" />

## A few things it does that aren't obvious

- **Won't spam your deck with duplicates.** Before saving, it compares the new card against what's already in that Anki deck and flags near-identical ones, so re-screenshotting the same question doesn't create a second copy.
- **Doesn't pay to read the same screenshot twice.** Identical screenshots are cached by hash, so the vision model only runs once per unique image.
- **Bulk mode.** You can send a whole batch of screenshots at once; if one fails or isn't a question, it's skipped and the rest still go through.

## Stack

- **Frontend:** Electron + React — a transparent overlay with a global hotkey.
- **Backend:** FastAPI (Python).
- **Vision:** a free vision model on OpenRouter (set in `backend/services/vision.py`).
- **Anki:** AnkiConnect, to read your existing cards and push new ones.

## Setup

**You'll need:**
- Python 3.11+
- Node.js 18+
- [Anki](https://apps.ankiweb.net/) running, with the [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on installed
- An [OpenRouter](https://openrouter.ai) API key (the free tier is fine)

**Backend**
~~~bash
cd backend
pip install -r requirements.txt
cp .env.example .env          # then drop your OpenRouter key into .env
uvicorn main:app --reload --port 8001
~~~

**Frontend**
~~~bash
cd frontend
npm install
npm start
~~~

## Running the tests

The backend suite runs without a key or a running Anki — it fakes the vision model so you can test the pipeline logic (caching, dedup, batching, failure handling) offline:

~~~bash
cd backend
MEDDECK_FAKE_VISION=1 python -m pytest -q
~~~

CI runs the same suite on every push.

## Honest limitations

- **macOS only** right now — the overlay and hotkey are built around it.
- **Deduplication is wording-based.** It reliably catches the same question re-screenshotted, but two genuinely different phrasings of the same fact can slip through. Swapping the local matcher for real semantic embeddings is the obvious next step.
- **Anki has to be open** for cards to save. If it's closed, generation still works and dedup just gets skipped.
- Card quality is only as good as the vision model — the free models are decent but occasionally miss a detail in a dense vignette.
