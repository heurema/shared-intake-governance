"""Read-only source collectors."""

from .arxiv_rss_keywords import (
    ArxivRssKeywordsCollectionResult,
    ArxivRssKeywordsCollector,
    ArxivRssKeywordsSource,
)
from .arxiv_query import (
    ArxivQueryCollectionResult,
    ArxivQueryCollector,
    ArxivQuerySource,
)
from .github_repo import (
    GitHubRepoCollectionResult,
    GitHubRepoCollector,
    GitHubRepoSource,
    HttpRequest,
    HttpResponse,
)
from .rss_feed import (
    RssFeedCollectionResult,
    RssFeedCollector,
    RssFeedSource,
)

__all__ = [
    "ArxivRssKeywordsCollectionResult",
    "ArxivRssKeywordsCollector",
    "ArxivRssKeywordsSource",
    "ArxivQueryCollectionResult",
    "ArxivQueryCollector",
    "ArxivQuerySource",
    "GitHubRepoCollectionResult",
    "GitHubRepoCollector",
    "GitHubRepoSource",
    "HttpRequest",
    "HttpResponse",
    "RssFeedCollectionResult",
    "RssFeedCollector",
    "RssFeedSource",
]
