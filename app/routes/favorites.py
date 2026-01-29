from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, request
from flask_login import login_required, current_user

from app import db
from app.models import Paper, Favorite

favorites_bp = Blueprint('favorites', __name__)


@favorites_bp.route('/')
@login_required
def list_favorites():
    favorites = current_user.favorites.order_by(Favorite.created_at.desc()).all()
    papers = [f.paper for f in favorites]
    return render_template('favorites.html', papers=papers)


@favorites_bp.route('/add/<int:paper_id>', methods=['POST'])
@login_required
def add_favorite(paper_id):
    paper = Paper.query.get_or_404(paper_id)

    existing = Favorite.query.filter_by(
        user_id=current_user.id,
        paper_id=paper_id
    ).first()

    if existing:
        flash('Paper already in favorites.', 'info')
    else:
        favorite = Favorite(user_id=current_user.id, paper_id=paper_id)
        db.session.add(favorite)
        db.session.commit()
        flash('Paper added to favorites.', 'success')

    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'action': 'added'})

    return redirect(request.referrer or url_for('main.index'))


@favorites_bp.route('/remove/<int:paper_id>', methods=['POST'])
@login_required
def remove_favorite(paper_id):
    favorite = Favorite.query.filter_by(
        user_id=current_user.id,
        paper_id=paper_id
    ).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        flash('Paper removed from favorites.', 'success')
    else:
        flash('Paper not in favorites.', 'info')

    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': 'success', 'action': 'removed'})

    return redirect(request.referrer or url_for('favorites.list_favorites'))
