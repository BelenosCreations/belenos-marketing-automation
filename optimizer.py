"""Deterministic, offline scheduling and third-party curation. No publishing code."""
from dataclasses import dataclass
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from urllib.parse import urlparse

TZ = ZoneInfo('America/New_York')

@dataclass(frozen=True)
class Candidate:
    source_name: str
    source_url: str
    original_url: str
    category: str
    summary: str
    source_approved: bool = False
    rights_verified: bool = False
    sponsored: bool = False
    sensitive: bool = False
    verified_facts: bool = False

CATEGORIES = {'impressive_print', 'creative_project', 'industry_news', 'education',
              'industry_best_practice', 'community', 'facility_care', 'case_study'}

def curate(item: Candidate):
    """Conservative recommendation: linking is allowed, copying media requires rights."""
    urls = (item.source_url, item.original_url)
    if any(urlparse(u).scheme != 'https' or not urlparse(u).netloc for u in urls):
        return 'blocked', 'invalid_source_url'
    if item.category not in CATEGORIES or not item.summary.strip():
        return 'blocked', 'invalid_content'
    if item.sensitive or item.sponsored:
        return 'approval_required', 'sensitive_or_sponsored'
    if not item.source_approved or not item.verified_facts:
        return 'approval_required', 'unverified_source_or_claim'
    return 'eligible_link_only', 'no_media_reuse_without_rights' if not item.rights_verified else 'attribution_required'

def rank_slots(*, start, scores, occupied=(), days=7, min_gap_hours=4, allowed_hours=range(8,21), fixed_deadline=None):
    """Rank hourly local slots using external audience activity scores.

    scores keys are (Python weekday 0=Mon, hour 0..23), values are nonnegative
    relative activity. No extrapolation for missing days/hours. DST handled by
    zoneinfo. Returns only future slots; never changes a remote schedule.
    """
    if start.tzinfo is None or start.utcoffset() is None:
        raise ValueError('start must be timezone-aware')
    if days < 1 or days > 31 or min_gap_hours < 0:
        raise ValueError('invalid scheduling bounds')
    local = start.astimezone(TZ)
    occupied_utc = [t.astimezone(ZoneInfo('UTC')) for t in occupied]
    options = []
    for d in range(days):
        day = local.date() + timedelta(days=d)
        for hour in allowed_hours:
            score = scores.get((day.weekday(), hour))
            if score is None or not isinstance(score, (int,float)) or score < 0:
                continue
            slot = datetime.combine(day, time(hour), tzinfo=TZ)
            if slot <= local or (fixed_deadline is not None and slot > fixed_deadline):
                continue
            instant = slot.astimezone(ZoneInfo('UTC'))
            if any(abs((instant - used).total_seconds()) < min_gap_hours*3600 for used in occupied_utc):
                continue
            options.append((slot, score))
    return sorted(options, key=lambda pair: (-pair[1], pair[0]))

def choose_balanced(items, *, max_items=3):
    """Round-robin among categories; retain source order within each category."""
    if max_items < 0: raise ValueError('max_items must be nonnegative')
    buckets = {category: [] for category in sorted(CATEGORIES)}
    for item in items:
        if curate(item)[0] == 'eligible_link_only':
            buckets[item.category].append(item)
    chosen = []
    while len(chosen) < max_items and any(buckets.values()):
        for category in buckets:
            if buckets[category] and len(chosen) < max_items:
                chosen.append(buckets[category].pop(0))
    return chosen
