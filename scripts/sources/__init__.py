"""Source registry.

Dispatches SOURCE_ID env var to the right fetcher class. Extend the dispatch
when adding new source types.
"""
from .youtube import YouTubeSource


def get_source(source_id: str):
    """Return the source instance for a given SOURCE_ID."""
    if source_id.startswith("youtube-"):
        return YouTubeSource()
    raise ValueError(
        f"Unknown SOURCE_ID: {source_id!r}. "
        "Add a fetcher in scripts/sources/ and extend get_source()."
    )
