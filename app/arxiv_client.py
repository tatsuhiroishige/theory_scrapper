import re
import arxiv
from datetime import datetime, timedelta
from flask import current_app

from app import db
from app.models import Paper, Keyword


# Physics-related keywords to extract from papers
PHYSICS_KEYWORDS = [
    'hadron', 'quark', 'gluon', 'meson', 'baryon', 'qcd', 'lattice',
    'pion', 'kaon', 'proton', 'neutron', 'nucleon', 'parton',
    'confinement', 'chiral', 'symmetry', 'scattering', 'decay',
    'cross-section', 'form factor', 'pdf', 'gpd', 'tmd',
    'drell-yan', 'deep inelastic', 'fragmentation', 'jet',
    'heavy quark', 'charm', 'bottom', 'charmonium', 'bottomonium',
    'exotic', 'tetraquark', 'pentaquark', 'glueball', 'hybrid',
    'effective field theory', 'eft', 'perturbative', 'non-perturbative',
    'renormalization', 'factorization', 'resummation',
    'collider', 'lhc', 'rhic', 'electron-ion', 'eic',
    'qgp', 'quark-gluon plasma', 'heavy-ion', 'nuclear'
]


def extract_keywords(title, abstract):
    """Extract relevant physics keywords from paper title and abstract."""
    text = f"{title} {abstract}".lower()
    found_keywords = set()

    for kw in PHYSICS_KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r's?\b'
        if re.search(pattern, text):
            found_keywords.add(kw)

    return found_keywords


def get_or_create_keyword(name):
    """Get existing keyword or create new one."""
    keyword = Keyword.query.filter_by(name=name).first()
    if not keyword:
        keyword = Keyword(name=name)
        db.session.add(keyword)
    return keyword


def fetch_hadron_papers(days_back=7, max_results=None):
    """
    Fetch recent papers related to hadron physics from arXiv.

    Args:
        days_back: Number of days to look back for papers
        max_results: Maximum number of results to return (uses config default if None)

    Returns:
        List of Paper objects (both new and existing)
    """
    if max_results is None:
        max_results = current_app.config.get('ARXIV_MAX_RESULTS', 100)

    categories = current_app.config.get('ARXIV_CATEGORIES', ['hep-ph', 'hep-th', 'hep-lat', 'nucl-th'])
    keywords = current_app.config.get('ARXIV_KEYWORDS', ['hadron', 'QCD', 'quark', 'gluon', 'meson', 'baryon'])

    # Build search query
    category_query = ' OR '.join([f'cat:{cat}' for cat in categories])
    keyword_query = ' OR '.join([f'all:{kw}' for kw in keywords])
    query = f'({category_query}) AND ({keyword_query})'

    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    papers = []
    cutoff_date = datetime.utcnow() - timedelta(days=days_back)

    for result in client.results(search):
        published = result.published.replace(tzinfo=None)
        if published < cutoff_date:
            continue

        # Check if paper already exists
        existing = Paper.query.filter_by(external_id=result.entry_id).first()
        if existing:
            papers.append(existing)
            continue

        # Create new paper
        paper = Paper(
            external_id=result.entry_id,
            source='arxiv',
            title=result.title,
            authors=', '.join([author.name for author in result.authors]),
            abstract=result.summary,
            categories=', '.join(result.categories),
            published_date=published,
            pdf_url=result.pdf_url,
            doi=result.doi if result.doi else None
        )

        # Extract and assign keywords
        keyword_names = extract_keywords(result.title, result.summary)
        for kw_name in keyword_names:
            keyword = get_or_create_keyword(kw_name)
            paper.keywords.append(keyword)

        db.session.add(paper)
        papers.append(paper)

    db.session.commit()
    return papers


def get_papers_since(hours=24):
    """Get papers published within the last N hours."""
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    return Paper.query.filter(Paper.published_date >= cutoff).order_by(Paper.published_date.desc()).all()


def get_recent_papers(limit=50, keyword=None, search_query=None, source=None):
    """Get the most recent papers from the database with optional filtering."""
    query = Paper.query

    if keyword:
        query = query.join(Paper.keywords).filter(Keyword.name == keyword)

    if source:
        query = query.filter(Paper.source == source)

    if search_query:
        search_term = f"%{search_query}%"
        query = query.filter(
            db.or_(
                Paper.title.ilike(search_term),
                Paper.abstract.ilike(search_term),
                Paper.authors.ilike(search_term)
            )
        )

    return query.order_by(Paper.published_date.desc()).limit(limit).all()


def get_all_sources():
    """Get all sources with paper counts."""
    return db.session.query(
        Paper.source,
        db.func.count(Paper.id).label('paper_count')
    ).group_by(Paper.source).order_by(db.desc('paper_count')).all()


def get_all_keywords():
    """Get all keywords sorted by paper count."""
    return db.session.query(
        Keyword,
        db.func.count(Paper.id).label('paper_count')
    ).join(Keyword.papers).group_by(Keyword.id).order_by(
        db.desc('paper_count')
    ).all()


def get_papers_by_keyword(keyword_name, limit=50):
    """Get papers with a specific keyword."""
    return Paper.query.join(Paper.keywords).filter(
        Keyword.name == keyword_name
    ).order_by(Paper.published_date.desc()).limit(limit).all()
