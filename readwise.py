import requests
import json
from datetime import datetime, timedelta
import os
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
import time
import re

load_dotenv()

class ReadwiseAPI:
    """Readwise API client for exporting highlights with smart update capability"""

    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or os.getenv("READWISE_TOKEN")
        if not self.api_token:
            raise ValueError("API token not found. Please set READWISE_TOKEN in .env file or pass it directly")

        self.base_url = "https://readwise.io/api/v2"
        self.headers = {
            "Authorization": f"Token {self.api_token}"
        }
        self.last_update_file = "last_update.json"
        self.articles_file = "articles.json"

    def clean_title(self, title: str) -> str:
        """Clean title by removing newlines and extra spaces"""
        title = re.sub(r'\s+', ' ', title.replace('\n', ' '))
        return title.strip()

    def get_highlights(self, updated_after: Optional[datetime] = None) -> Dict:
        """Get all highlights with their associated metadata"""
        endpoint = f"{self.base_url}/export/"
        params = {}

        if updated_after:
            params["updated_after"] = updated_after.isoformat()

        response = requests.get(endpoint, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def create_article_json(self, highlights_data: Dict) -> List[Dict]:
        """Create a list of articles with title and URL, only for category 'articles'"""
        articles = []

        for article in highlights_data.get('results', []):
            if article.get('category', '').lower() == 'articles':
                title = self.clean_title(article.get('title', 'Untitled'))
                url = article.get('source_url', '')

                articles.append({
                    'title': title,
                    'url': url
                })

        return articles

    def load_last_update(self, output_dir: Path) -> Optional[datetime]:
        """Load the last update date from file"""
        last_update_path = output_dir / self.last_update_file

        if last_update_path.exists():
            try:
                with open(last_update_path, 'r') as f:
                    data = json.load(f)
                    return datetime.strptime(data['last_update'], '%Y-%m-%d')
            except Exception as e:
                print(f"Error reading last update file: {e}")
                return None
        return None

    def save_last_update(self, output_dir: Path):
        """Save current date as last update date"""
        last_update_path = output_dir / self.last_update_file
        current_date = datetime.now().strftime('%Y-%m-%d')

        with open(last_update_path, 'w') as f:
            json.dump({'last_update': current_date}, f)

    def load_existing_articles(self, output_dir: Path) -> List[Dict]:
        """Load existing articles from the articles file"""
        articles_path = output_dir / self.articles_file

        if articles_path.exists():
            try:
                with open(articles_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading articles file: {e}")
                return []
        return []

    def merge_articles(self, existing_articles: List[Dict], new_articles: List[Dict]) -> List[Dict]:
        """Merge new articles with existing ones, avoiding duplicates"""
        # Convert existing articles to a set of (title, url) tuples for easy comparison
        existing_set = {(article['title'], article['url']) for article in existing_articles}

        # Add only new articles that don't exist in the current set
        for article in new_articles:
            article_tuple = (article['title'], article['url'])
            if article_tuple not in existing_set:
                existing_articles.append(article)
                existing_set.add(article_tuple)

        return existing_articles

    def export_articles(self, output_dir: str):
        """Export articles as JSON file with smart update capability"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get last update date
        last_update = self.load_last_update(output_path)

        # If we have a last update date, use it to fetch only new articles
        if last_update:
            days_since_update = (datetime.now() - last_update).days
            print(f"Last update was {days_since_update} days ago on {last_update.strftime('%Y-%m-%d')}")
            if days_since_update > 0:
                updated_after = last_update
            else:
                print("Already updated today, no need to fetch new articles")
                return
        else:
            print("No previous update found, fetching all articles")
            updated_after = None

        # Get highlights
        print("Fetching highlights from Readwise...")
        highlights_data = self.get_highlights(updated_after=updated_after)

        # Create article data
        new_articles = self.create_article_json(highlights_data)
        print(f"Found {len(new_articles)} new articles")

        # Load existing articles
        existing_articles = self.load_existing_articles(output_path)
        print(f"Found {len(existing_articles)} existing articles")

        # Merge new articles with existing ones
        merged_articles = self.merge_articles(existing_articles, new_articles)
        print(f"Total unique articles after merge: {len(merged_articles)}")

        # Save merged articles
        articles_path = output_path / self.articles_file
        with open(articles_path, "w", encoding="utf-8") as f:
            json.dump(merged_articles, f, ensure_ascii=False, indent=2)

        # Update the last update date
        self.save_last_update(output_path)

        print(f"Successfully updated articles in {articles_path}")
        if new_articles:
            print("New articles added:")
            for article in new_articles:
                print(f"- {article['title']}")

def main():
    try:
        client = ReadwiseAPI()
        output_dir = os.getenv("OUTPUT_DIR", "readwise_exports")
        client.export_articles(output_dir=output_dir)

    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
