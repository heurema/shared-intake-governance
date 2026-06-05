"""Read-only source collectors."""

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
from .github_releases import (
    GitHubReleasesCollectionResult,
    GitHubReleasesCollector,
    GitHubReleasesSource,
)
from .github_search import (
    GitHubSearchCollectionResult,
    GitHubSearchCollector,
    GitHubSearchSource,
)
from .news_feed import (
    NewsFeedCollectionResult,
    NewsFeedCollector,
    NewsFeedSource,
)
from .rss_feed import (
    RssFeedCollectionResult,
    RssFeedCollector,
    RssFeedSource,
)

__all__ = [
    "ArxivQueryCollectionResult",
    "ArxivQueryCollector",
    "ArxivQuerySource",
    "GitHubRepoCollectionResult",
    "GitHubRepoCollector",
    "GitHubRepoSource",
    "GitHubReleasesCollectionResult",
    "GitHubReleasesCollector",
    "GitHubReleasesSource",
    "GitHubSearchCollectionResult",
    "GitHubSearchCollector",
    "GitHubSearchSource",
    "HttpRequest",
    "HttpResponse",
    "NewsFeedCollectionResult",
    "NewsFeedCollector",
    "NewsFeedSource",
    "RssFeedCollectionResult",
    "RssFeedCollector",
    "RssFeedSource",
]
