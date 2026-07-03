"""Malayalam → English translation for query understanding.

Separate from MarianTranslationService (which handles UI language switching)
because this has a different concern: extracting intent from Malayalam natural
language phrases so spaCy can parse them in English.

Uses Helsinki-NLP/opus-mt-ml-en — a dedicated ML→EN model with better quality
than the multilingual opus-mt-mul-en for this specific language pair.

Lazy-loads on first call so app startup stays fast.
"""

import logging

from transformers import MarianMTModel, MarianTokenizer

log = logging.getLogger(__name__)

_MODEL_NAME = "Helsinki-NLP/opus-mt-ml-en"
_tokenizer: MarianTokenizer | None = None
_model: MarianMTModel | None = None


def _load() -> None:
    """Lazily load the tokenizer and model on first call."""
    global _tokenizer, _model
    if _model is None:
        log.info("Loading ML→EN query understanding model %s", _MODEL_NAME)
        _tokenizer = MarianTokenizer.from_pretrained(_MODEL_NAME)
        _model = MarianMTModel.from_pretrained(_MODEL_NAME)
        log.info("ML→EN model ready")


def translate_ml_to_en(text: str) -> str:
    """Translate a Malayalam phrase to English for query understanding.

    Returns the original text unchanged on any error so the caller can
    still attempt a search with the raw Malayalam input.

    Parameters
    ----------
    text : str
        Malayalam natural language phrase, e.g. "ചാടുക എന്നതിൻറെ അർത്ഥം എന്ത്".

    Returns
    -------
    str
        English translation, or ``text`` unchanged if translation fails.
    """
    try:
        _load()
        inputs = _tokenizer(  # type: ignore[misc]
            [text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=128,
        )
        translated_ids = _model.generate(**inputs)  # type: ignore[union-attr]
        return _tokenizer.batch_decode(  # type: ignore[union-attr]
            translated_ids, skip_special_tokens=True
        )[0]
    except Exception:
        log.warning("ML→EN translation failed for %r — using original text", text, exc_info=True)
        return text