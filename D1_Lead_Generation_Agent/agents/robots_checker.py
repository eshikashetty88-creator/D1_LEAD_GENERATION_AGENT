from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


@lru_cache(maxsize=512)
def check_robots(url: str, user_agent: str = "D1LeadGenerationAgent/1.0") -> bool:
    """Return True only when robots.txt permits fetching the URL."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False

    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    try:
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        allowed = rp.can_fetch(user_agent, url)
        if not allowed:
            logger.info("ROBOTS BLOCKED: %s", url)
        return allowed
    except Exception as exc:
        # Fail closed: if we cannot verify robots.txt, do not fetch.
        logger.warning("ROBOTS CHECK FAILED; SKIPPING %s: %s", url, exc)
        return False
