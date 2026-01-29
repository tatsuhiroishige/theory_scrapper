"""
Journal RSS client for fetching papers from Physical Review, PTEP, and EPJ.
"""

import feedparser
from datetime import datetime
from dateutil import parser as date_parser
from flask import current_app

from app import db
from app.models import Paper
from app.arxiv_client import extract_keywords, get_or_create_keyword


# Journal RSS feed configurations
JOURNAL_FEEDS = {
    'phys_rev_d': {
        'name': 'Physical Review D',
        'url': 'https://feeds.aps.org/rss/recent/prd.xml',
        'source': 'phys_rev_d',
    },
    'phys_rev_lett': {
        'name': 'Physical Review Letters',
        'url': 'https://feeds.aps.org/rss/recent/prl.xml',
        'source': 'phys_rev_lett',
    },
    'phys_rev_c': {
        'name': 'Physical Review C',
        'url': 'https://feeds.aps.org/rss/recent/prc.xml',
        'source': 'phys_rev_c',
    },
    'ptep': {
        'name': 'PTEP',
        'url': 'https://academic.oup.com/rss/site_5322/3258.xml',
        'source': 'ptep',
    },
    'epjc': {
        'name': 'European Physical Journal C',
        'url': 'https://link.springer.com/search.rss?facet-content-type=Article&facet-journal-id=10052&channel-name=The+European+Physical+Journal+C',
        'source': 'epjc',
    },
}

# Source display names for UI
SOURCE_NAMES = {
    'arxiv': 'arXiv',
    'phys_rev_d': 'Phys. Rev. D',
    'phys_rev_lett': 'Phys. Rev. Lett.',
    'phys_rev_c': 'Phys. Rev. C',
    'ptep': 'PTEP',
    'epjc': 'Eur. Phys. J. C',
}


def parse_date(date_str):
    """Parse date string from RSS feed."""
    if not date_str:
        return datetime.utcnow()
    try:
        return date_parser.parse(date_str).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


def extract_doi_from_link(link):
    """Extract DOI from article link if possible."""
    if not link:
        return None
    if '10.' in link:
        # Try to extract DOI pattern
        import re
        match = re.search(r'(10\.\d{4,}/[^\s]+)', link)
        if match:
            return match.group(1).rstrip('/')
    return None


def fetch_journal_papers(journal_key=None, filter_hadron=True):
    """
    Fetch papers from journal RSS feeds.

    Args:
        journal_key: Specific journal to fetch (None for all)
        filter_hadron: If True, only include hadron-related papers

    Returns:
        List of Paper objects
    """
    feeds_to_fetch = JOURNAL_FEEDS if journal_key is None else {journal_key: JOURNAL_FEEDS[journal_key]}
    papers = []
    hadron_terms = current_app.config.get('ARXIV_KEYWORDS', ['hadron', 'QCD', 'quark', 'gluon', 'meson', 'baryon'])

    for key, feed_config in feeds_to_fetch.items():
        try:
            feed = feedparser.parse(feed_config['url'])

            for entry in feed.entries:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))

                # Filter for hadron-related papers
                if filter_hadron:
                    text = f"{title} {summary}".lower()
                    if not any(term.lower() in text for term in hadron_terms):
                        continue

                # Get external ID (prefer DOI, fallback to link)
                doi = entry.get('prism_doi') or entry.get('dc_identifier') or extract_doi_from_link(entry.get('link'))
                external_id = doi or entry.get('id') or entry.get('link')

                if not external_id:
                    continue

                # Check if paper already exists
                existing = Paper.query.filter_by(external_id=external_id).first()
                if existing:
                    papers.append(existing)
                    continue

                # Parse authors
                authors = ''
                if 'authors' in entry:
                    authors = ', '.join([a.get('name', '') for a in entry.authors])
                elif 'author' in entry:
                    authors = entry.author
                elif 'dc_creator' in entry:
                    authors = entry.dc_creator

                # Parse date
                pub_date = parse_date(
                    entry.get('published') or
                    entry.get('prism_publicationdate') or
                    entry.get('updated')
                )

                # Create paper
                paper = Paper(
                    external_id=external_id,
                    source=feed_config['source'],
                    title=title,
                    authors=authors,
                    abstract=summary,
                    categories=feed_config['name'],
                    published_date=pub_date,
                    pdf_url=entry.get('link'),
                    doi=doi,
                    journal=feed_config['name']
                )

                # Extract and assign keywords
                keyword_names = extract_keywords(title, summary)
                for kw_name in keyword_names:
                    keyword = get_or_create_keyword(kw_name)
                    paper.keywords.append(keyword)

                db.session.add(paper)
                papers.append(paper)

        except Exception as e:
            current_app.logger.error(f"Error fetching {feed_config['name']}: {e}")
            continue

    db.session.commit()
    return papers


def fetch_all_sources(filter_hadron=True):
    """Fetch papers from all sources (arXiv and journals)."""
    from app.arxiv_client import fetch_hadron_papers

    papers = []

    # Fetch from arXiv
    try:
        arxiv_papers = fetch_hadron_papers(days_back=7)
        papers.extend(arxiv_papers)
    except Exception as e:
        current_app.logger.error(f"Error fetching arXiv: {e}")

    # Fetch from journals
    try:
        journal_papers = fetch_journal_papers(filter_hadron=filter_hadron)
        papers.extend(journal_papers)
    except Exception as e:
        current_app.logger.error(f"Error fetching journals: {e}")

    return papers


def get_source_display_name(source):
    """Get display name for a source."""
    return SOURCE_NAMES.get(source, source)
