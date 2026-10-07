import hashlib
import json
import uuid

from django.core.cache import cache


PRICE_PANEL_CACHE_VERSION_KEY = "price_panel:cache_version"

PRODUCT_LIST_CACHE_TIMEOUT = 60
PRODUCT_DETAIL_CACHE_TIMEOUT = 120
HISTORY_CACHE_TIMEOUT = 60
DASHBOARD_CACHE_TIMEOUT = 30
CATEGORIES_CACHE_TIMEOUT = 300


def get_price_panel_cache_version():
    version = cache.get(PRICE_PANEL_CACHE_VERSION_KEY)

    if not version:
        version = uuid.uuid4().hex
        cache.add(
            PRICE_PANEL_CACHE_VERSION_KEY,
            version,
            timeout=None,
        )

        version = cache.get(PRICE_PANEL_CACHE_VERSION_KEY) or version

    return str(version)


def invalidate_price_panel_cache():
    """
    Invalidates every price-panel cache without touching
    unrelated application caches.
    """

    new_version = uuid.uuid4().hex

    cache.set(
        PRICE_PANEL_CACHE_VERSION_KEY,
        new_version,
        timeout=None,
    )

    return new_version


def build_price_panel_cache_key(prefix, *parts):
    version = get_price_panel_cache_version()

    normalized_parts = []

    for part in parts:
        if part is None:
            normalized_parts.append("")
        elif isinstance(part, (dict, list, tuple)):
            normalized_parts.append(
                json.dumps(
                    part,
                    sort_keys=True,
                    ensure_ascii=False,
                    default=str,
                )
            )
        else:
            normalized_parts.append(str(part))

    raw_key = ":".join(
        [
            "price_panel",
            version,
            prefix,
            *normalized_parts,
        ]
    )

    digest = hashlib.sha256(
        raw_key.encode("utf-8")
    ).hexdigest()

    return f"price_panel:{prefix}:{version}:{digest}"