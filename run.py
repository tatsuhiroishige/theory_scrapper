#!/usr/bin/env python
"""
Entry point for Hadron Physics Theory Scraper.

Usage:
    python run.py [--with-scheduler]

Options:
    --with-scheduler    Enable the email digest scheduler
"""

import sys
from app import create_app

app = create_app()

if __name__ == '__main__':
    # Check if scheduler should be enabled
    with_scheduler = '--with-scheduler' in sys.argv

    if with_scheduler:
        from scheduler import setup_scheduler
        scheduler = setup_scheduler(app)
        print("Running with email digest scheduler enabled.")

    # Run the Flask development server
    app.run(debug=True, host='0.0.0.0', port=5000)
