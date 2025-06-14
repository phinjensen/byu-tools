## byu-tools

A little tool to find open rooms on BYU campus.

### Setup

1. Install the required packages (`pip install -r requirements.txt`)
2. Use the scraper to download a semester's schedule from BYU (see the usage comment at the top of `scraper/scrape.py`)
3. Run the app (`DATABASE_URL=postgresql://host:port/db flask run`)
