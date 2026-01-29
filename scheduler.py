"""
Email digest scheduler for Hadron Physics Theory Scraper.

This module provides functionality to send daily email digests of new papers
to subscribed users.
"""

from datetime import datetime, timedelta
from flask import render_template_string
from flask_mail import Message

from app import create_app, db, mail
from app.models import User, Paper
from app.arxiv_client import get_papers_since


EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #2c3e50; color: white; padding: 20px; text-align: center; }
        .paper { border-bottom: 1px solid #eee; padding: 15px 0; }
        .paper-title { color: #2c3e50; font-size: 16px; font-weight: bold; margin-bottom: 5px; }
        .paper-authors { color: #666; font-size: 14px; margin-bottom: 10px; }
        .paper-categories { color: #888; font-size: 12px; }
        .footer { text-align: center; padding: 20px; color: #888; font-size: 12px; }
        a { color: #3498db; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Hadron Physics Daily Digest</h1>
            <p>{{ date }}</p>
        </div>

        <p>Here are the latest papers in hadron physics:</p>

        {% for paper in papers %}
        <div class="paper">
            <div class="paper-title">
                <a href="{{ paper.arxiv_id }}">{{ paper.title }}</a>
            </div>
            <div class="paper-authors">{{ paper.authors[:100] }}{% if paper.authors|length > 100 %}...{% endif %}</div>
            <div class="paper-categories">{{ paper.categories }}</div>
        </div>
        {% endfor %}

        {% if not papers %}
        <p>No new papers in the last 24 hours.</p>
        {% endif %}

        <div class="footer">
            <p>You're receiving this because you subscribed to daily digests.</p>
            <p>Data sourced from arXiv.org</p>
        </div>
    </div>
</body>
</html>
"""


def send_digest_email(user, papers):
    """Send a digest email to a single user."""
    html_content = render_template_string(
        EMAIL_TEMPLATE,
        papers=papers,
        date=datetime.utcnow().strftime('%B %d, %Y')
    )

    msg = Message(
        subject=f"Hadron Physics Digest - {datetime.utcnow().strftime('%Y-%m-%d')}",
        recipients=[user.email],
        html=html_content
    )

    mail.send(msg)


def send_daily_digest():
    """Send daily digest to all subscribed users."""
    app = create_app()

    with app.app_context():
        # Get papers from last 24 hours
        papers = get_papers_since(hours=24)

        # Get subscribed users
        users = User.query.filter_by(email_digest_enabled=True).all()

        sent_count = 0
        for user in users:
            try:
                send_digest_email(user, papers)
                sent_count += 1
                print(f"Sent digest to {user.email}")
            except Exception as e:
                print(f"Failed to send digest to {user.email}: {e}")

        print(f"Daily digest complete. Sent to {sent_count}/{len(users)} users.")


def setup_scheduler(app):
    """Set up APScheduler for daily digest emails."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()

    # Run daily at 8:00 AM UTC
    scheduler.add_job(
        func=send_daily_digest,
        trigger='cron',
        hour=8,
        minute=0,
        id='daily_digest',
        replace_existing=True
    )

    scheduler.start()
    print("Email digest scheduler started. Daily digest will be sent at 8:00 AM UTC.")

    return scheduler


if __name__ == '__main__':
    # Manual trigger for testing
    send_daily_digest()
