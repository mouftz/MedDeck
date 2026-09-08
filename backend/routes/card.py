from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.anki import add_card, create_deck, get_deck_fronts
from services.pipeline import generate_cached, mark_duplicate, process_batch
import traceback

router = APIRouter()

class ScreenshotRequest(BaseModel):
    image_base64: str
    deck_name: str = "Wrong Answers"

class BatchRequest(BaseModel):
    images: list[str]
    deck_name: str = "Wrong Answers"

class SaveCardRequest(BaseModel):
    anki_front: str
    anki_back: str
    deck_name: str = "Wrong Answers"
    reason: str = "Knowledge gap"

@router.post("/generate-card")
async def generate_card(req: ScreenshotRequest):
    """Generate a card (cached by screenshot) and flag it if it already exists in the deck."""
    try:
        card = generate_cached(req.image_base64)
        try:
            existing = get_deck_fronts(req.deck_name)
        except Exception:
            existing = []  # dedup is best-effort; never block generation on Anki being down
        return mark_duplicate(card, existing)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate-batch")
async def generate_batch(req: BatchRequest):
    """Generate cards for many screenshots; failures are isolated per item."""
    try:
        try:
            existing = get_deck_fronts(req.deck_name)
        except Exception:
            existing = []
        return {"results": process_batch(req.images, existing)}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/save-card")
async def save_card(req: SaveCardRequest):
    """Pushes a (possibly edited) card to Anki."""
    try:
        create_deck(req.deck_name)
        tags = [req.reason.lower().replace(" ", "_")]
        
        note_id = add_card(
            deck_name=req.deck_name,
            front=req.anki_front,
            back=req.anki_back,
            tags=tags
        )
        
        return {
            "anki_note_id": note_id,
            "deck": req.deck_name
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

class CreateDeckRequest(BaseModel):
    deck_name: str

@router.get("/decks")
async def list_decks():
    """Returns all Anki deck names."""
    try:
        from services.anki import get_deck_names
        decks = get_deck_names()
        return {"decks": decks}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/decks")
async def create_new_deck(req: CreateDeckRequest):
    """Creates a new deck."""
    try:
        create_deck(req.deck_name)
        return {"deck": req.deck_name, "created": True}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))