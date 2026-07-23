"""Shared app state — singletons accessed by both API and web routers."""

from sqlalchemy.orm import sessionmaker

from linguaalayam.rag.tools import DictionaryTools
from linguaalayam.translation.base import TranslationService

_tools: DictionaryTools | None = None
_translator: TranslationService | None = None
_session_factory: sessionmaker | None = None


def set_tools(tools: DictionaryTools) -> None:
    """Store the shared DictionaryTools singleton.

    Parameters
    ----------
    tools : DictionaryTools
        Fully initialised retrieval tools to make available to request handlers.
    """
    global _tools
    _tools = tools


def get_tools() -> DictionaryTools:
    """Return the shared DictionaryTools singleton.

    Returns
    -------
    DictionaryTools
        The active retrieval tools.

    Raises
    ------
    RuntimeError
        If called before ``set_tools`` (i.e. before the lifespan context runs).
    """
    if _tools is None:
        raise RuntimeError("DictionaryTools not initialised — lifespan may not have run")
    return _tools


def set_translator(translator: TranslationService) -> None:
    """Store the shared TranslationService singleton.

    Parameters
    ----------
    translator : TranslationService
        Fully initialised translation service to make available to request handlers.
    """
    global _translator
    _translator = translator


def get_translator() -> TranslationService:
    """Return the shared TranslationService singleton.

    Returns
    -------
    TranslationService
        The active translation service.

    Raises
    ------
    RuntimeError
        If called before ``set_translator`` (i.e. before the lifespan context runs).
    """
    if _translator is None:
        raise RuntimeError("TranslationService not initialised — lifespan may not have run")
    return _translator


def set_session_factory(session_factory: sessionmaker) -> None:
    """Store the shared DB session factory, used by the request-logging middleware.

    Parameters
    ----------
    session_factory : sessionmaker
        Session factory bound to the application's database engine.
    """
    global _session_factory
    _session_factory = session_factory


def get_session_factory() -> sessionmaker:
    """Return the shared DB session factory.

    Returns
    -------
    sessionmaker
        The active session factory.

    Raises
    ------
    RuntimeError
        If called before ``set_session_factory`` (i.e. before the lifespan context runs).
    """
    if _session_factory is None:
        raise RuntimeError("Session factory not initialised — lifespan may not have run")
    return _session_factory
