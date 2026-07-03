"""Data models for dictionary entries from various sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


def _compute_morphology(headword: str) -> list[str] | None:
    """Return mlmorph analysis labels for *headword*, or ``None`` if unavailable.

    Called once at parse/ingest time so results are stored in ``data`` JSONB
    and never recomputed at query time.
    """
    try:
        from linguaalayam.morphology import analyse_word

        return analyse_word(headword.split(",")[0].strip() if "," in headword else headword)
    except Exception:
        return None


@runtime_checkable
class Embeddable(Protocol):
    """Protocol for entries that can be embedded into a vector space."""

    source: str
    headword: str

    def to_embed_text(self) -> str: ...


def _definition_embed_text(headword: str, definitions: list[tuple[str | None, str]]) -> str:
    """Shared embed-text format for definition-based entry types."""
    by_pos: dict[str, list[str]] = {}
    for pos, defn in definitions:
        by_pos.setdefault(pos or "general", []).append(defn)
    lines = [f"word: {headword}"]
    for pos, defns in by_pos.items():
        lines.append(f"  [{pos}] {'; '.join(defns)}")
    return "\n".join(lines)


@dataclass
class OlamEntry:
    """English–Malayalam dictionary entry from the Olam corpus.

    Attributes
    ----------
    headword : str
        The English word or phrase being defined.
    definitions : list[tuple[str | None, str]]
        Ordered list of ``(part-of-speech, Malayalam definition)`` pairs.
    source : str
        Corpus identifier; defaults to ``"olam_enml"``.
    morphology : None
        Always ``None`` — mlmorph does not process English headwords.
    """

    headword: str
    definitions: list[tuple[str | None, str]]
    source: str = "olam_enml"
    morphology: list[str] | None = field(init=False, default=None)

    def to_embed_text(self) -> str:
        """Convert to embed-text format grouping definitions by part of speech."""
        return _definition_embed_text(self.headword, self.definitions)


@dataclass
class DatukEntry:
    """Malayalam–Malayalam dictionary entry from the Datuk corpus.

    Attributes
    ----------
    headword : str
        The Malayalam word being defined.
    definitions : list[tuple[str | None, str]]
        Ordered list of ``(part-of-speech, Malayalam definition)`` pairs.
    source : str
        Corpus identifier; defaults to ``"datuk"``.
    morphology : list[str] or None
        mlmorph analysis labels, computed at ingest time.
    """

    headword: str
    definitions: list[tuple[str | None, str]]
    source: str = "datuk"
    morphology: list[str] | None = field(init=False)

    def __post_init__(self) -> None:
        """Compute morphology at ingest time via mlmorph."""
        self.morphology = _compute_morphology(self.headword)

    def to_embed_text(self) -> str:
        """Convert to embed-text format grouping definitions by part of speech."""
        return _definition_embed_text(self.headword, self.definitions)


@dataclass
class SayahnaEntry:
    """Malayalam–Malayalam dictionary entry from the Sayahna Shabdataaravali corpus (1917).

    Attributes
    ----------
    headword : str
        The Malayalam word being defined.
    definitions : list[tuple[str | None, str]]
        Ordered list of ``(part-of-speech, definition)`` pairs.
    explanations : list[str]
        Supplementary notes from ``<expl>`` elements.
    source : str
        Corpus identifier; defaults to ``"sayahna"``.
    morphology : list[str] or None
        mlmorph analysis labels, computed at ingest time.
    """

    headword: str
    definitions: list[tuple[str | None, str]]
    explanations: list[str] = field(default_factory=list)
    source: str = "sayahna"
    morphology: list[str] | None = field(init=False)

    def __post_init__(self) -> None:
        """Compute morphology at ingest time via mlmorph."""
        self.morphology = _compute_morphology(self.headword)

    def to_embed_text(self) -> str:
        """Convert to embed-text format with definitions grouped by POS and appended notes."""
        text = _definition_embed_text(self.headword, self.definitions)
        if self.explanations:
            text += "\n  notes: " + "; ".join(self.explanations)
        return text


@dataclass
class EkkurupSense:
    """One sense (POS cluster) within an Ekkurup thesaurus entry."""

    pos: str | None
    en: list[list[str]] = field(default_factory=list)
    ml: list[list[str]] = field(default_factory=list)


@dataclass
class EkkurupEntry:
    """English–Malayalam thesaurus entry from the Ekkurup corpus.

    Attributes
    ----------
    headword : str
        The English word or phrase.
    senses : list[EkkurupSense]
        All sense clusters for this headword.
    source : str
        Corpus identifier; defaults to ``"ekkurup"``.
    morphology : None
        Always ``None`` — English headwords are not analysed by mlmorph.
    """

    headword: str
    senses: list[EkkurupSense]
    source: str = "ekkurup"
    morphology: list[str] | None = field(init=False, default=None)

    def to_embed_text(self) -> str:
        """Convert to embed-text format with EN and ML synonym clusters per sense."""
        lines = [f"word: {self.headword}"]
        for sense in self.senses:
            pos_tag = f"[{sense.pos}]" if sense.pos else "[general]"
            en_flat = "; ".join(", ".join(g) for g in sense.en if g)
            ml_flat = "; ".join(", ".join(g) for g in sense.ml if g)
            if en_flat:
                lines.append(f"  {pos_tag} en: {en_flat}")
            if ml_flat:
                lines.append(f"  {pos_tag} ml: {ml_flat}")
        return "\n".join(lines)
