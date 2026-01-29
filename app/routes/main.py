from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import current_user

from app.arxiv_client import fetch_hadron_papers, get_recent_papers, get_all_keywords
from app.models import Paper, Favorite

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    keyword = request.args.get('keyword')
    search_query = request.args.get('q')

    papers = get_recent_papers(limit=50, keyword=keyword, search_query=search_query)
    keywords = get_all_keywords()
    favorite_ids = set()

    if current_user.is_authenticated:
        favorite_ids = {f.paper_id for f in current_user.favorites.all()}

    return render_template(
        'index.html',
        papers=papers,
        favorite_ids=favorite_ids,
        keywords=keywords,
        current_keyword=keyword,
        search_query=search_query
    )


@main_bp.route('/refresh')
def refresh_papers():
    """Fetch new papers from arXiv."""
    try:
        papers = fetch_hadron_papers(days_back=7)
        flash(f'Fetched {len(papers)} papers from arXiv.', 'success')
    except Exception as e:
        flash(f'Error fetching papers: {str(e)}', 'danger')

    return redirect(url_for('main.index'))


@main_bp.route('/paper/<int:paper_id>')
def paper_detail(paper_id):
    paper = Paper.query.get_or_404(paper_id)
    is_favorite = False

    if current_user.is_authenticated:
        is_favorite = Favorite.query.filter_by(
            user_id=current_user.id,
            paper_id=paper_id
        ).first() is not None

    return render_template('paper_detail.html', paper=paper, is_favorite=is_favorite)
