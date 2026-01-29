from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    email_digest_enabled = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    favorites = db.relationship('Favorite', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.email}>'


# Association table for Paper-Keyword many-to-many relationship
paper_keywords = db.Table(
    'paper_keywords',
    db.Column('paper_id', db.Integer, db.ForeignKey('papers.id'), primary_key=True),
    db.Column('keyword_id', db.Integer, db.ForeignKey('keywords.id'), primary_key=True)
)


class Keyword(db.Model):
    __tablename__ = 'keywords'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    papers = db.relationship('Paper', secondary=paper_keywords, back_populates='keywords')

    def __repr__(self):
        return f'<Keyword {self.name}>'


class Paper(db.Model):
    __tablename__ = 'papers'

    id = db.Column(db.Integer, primary_key=True)
    external_id = db.Column(db.String(200), unique=True, nullable=False, index=True)
    source = db.Column(db.String(50), nullable=False, default='arxiv', index=True)
    title = db.Column(db.Text, nullable=False)
    authors = db.Column(db.Text, nullable=False)
    abstract = db.Column(db.Text)
    categories = db.Column(db.String(200))
    published_date = db.Column(db.DateTime, index=True)
    pdf_url = db.Column(db.String(500))
    doi = db.Column(db.String(100), index=True)
    journal = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    favorites = db.relationship('Favorite', backref='paper', lazy='dynamic', cascade='all, delete-orphan')
    keywords = db.relationship('Keyword', secondary=paper_keywords, back_populates='papers')

    def __repr__(self):
        return f'<Paper {self.source}:{self.external_id}>'


class Favorite(db.Model):
    __tablename__ = 'favorites'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'paper_id', name='unique_user_paper'),)

    def __repr__(self):
        return f'<Favorite user={self.user_id} paper={self.paper_id}>'


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
