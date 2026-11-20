"""Endpoint catalog for the NASA Open APIs used by the cover dashboard."""

# APOD migrated to the WordPress API in September 2026.
APOD_URL = "https://science.nasa.gov/wp-json/wp/v2/apod-basic"

NEOWS_FEED_URL = "https://api.nasa.gov/neo/rest/v1/feed"
DONKI_NOTIFICATIONS_URL = "https://api.nasa.gov/DONKI/notifications"
# EPIC is served directly from epic.gsfc.nasa.gov (the api.nasa.gov alias now 404s).
EPIC_NATURAL_IMAGES_URL = "https://epic.gsfc.nasa.gov/api/natural"
EONET_EVENTS_URL = "https://eonet.gsfc.nasa.gov/api/v3/events"
EPIC_ARCHIVE_BASE_URL = "https://epic.gsfc.nasa.gov/archive"


def epic_image_url(image_name: str, date: str, api_key: str | None = None, enhanced: bool = False) -> str:
    """Build a direct EPIC PNG URL from an image record's name and date.

    The direct epic.gsfc.nasa.gov archive does not accept an api_key query and
    returns 404 when one is supplied, so the key is intentionally ignored here.
    """
    date_part = date[:10].replace("-", "/")
    color = "enhanced" if enhanced else "natural"
    return f"{EPIC_ARCHIVE_BASE_URL}/{color}/{date_part}/png/{image_name}.png"
