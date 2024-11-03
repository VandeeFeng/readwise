import requests
import json
from datetime import datetime, timedelta
import os
from typing import List, Dict, Optional
from pathlib import Path
import re
from github import Github
import argparse

class ReadwiseAPI:
    """Readwise API client for exporting highlights with smart update capability and GitHub integration"""

    def __init__(self):
        # Initialize Readwise token
        self.readwise_token = os.environ.get("READWISE_TOKEN")
        if not self.readwise_token:
            raise ValueError("READWISE_TOKEN not found in environment variables")

        # Initialize GitHub token
        self.github_token = os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN not found in environment variables")
        
        # Get repository from GitHub Actions environment variable
        self.github_repo = os.environ.get("GITHUB_REPOSITORY")
        if not self.github_repo:
            raise ValueError("Not running in GitHub Actions environment (GITHUB_REPOSITORY not found)")

        # Initialize GitHub client
        self.github = Github(self.github_token)
        self.repo = self.github.get_repo(self.github_repo)

        # Initialize Readwise API settings
        self.base_url = "https://readwise.io/api/v2"
        self.headers = {
            "Authorization": f"Token {self.readwise_token}"
        }
        self.last_update_file = "last_update.json"
        self.articles_file = "articles.json"

    def get_highlights(self, updated_after: Optional[datetime] = None, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None) -> Dict:
        """Get all highlights with their associated metadata"""
        endpoint = f"{self.base_url}/export/"
        params = {}

        if updated_after:
            params["updated_after"] = updated_after.isoformat()
        elif start_date:
            params["updated_after"] = start_date.isoformat()
            if end_date:
                params["updated_before"] = end_date.isoformat()

        print(f"Fetching highlights with params: {params}")
        response = requests.get(endpoint, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_file_content(self, path: str) -> Optional[str]:
        """Get file content from GitHub repository"""
        try:
            content = self.repo.get_contents(path)
            return content.decoded_content.decode('utf-8')
        except Exception as e:
            print(f"File {path} not found in repository: {e}")
            return None

    def update_file(self, path: str, content: str, message: str):
        """Update or create file in GitHub repository"""
        try:
            # Try to get existing file
            file = self.repo.get_contents(path)
            # Update existing file
            self.repo.update_file(
                path=path,
                message=message,
                content=content,
                sha=file.sha
            )
        except Exception:
            # Create new file if it doesn't exist
            self.repo.create_file(
                path=path,
                message=message,
                content=content
            )

    def clean_title(self, title: str) -> str:
        """Clean title by removing newlines and extra spaces"""
        title = re.sub(r'\s+', ' ', title.replace('\n', ' '))
        return title.strip()

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

    def load_last_update_from_github(self) -> Optional[datetime]:
        """Load the last update date from GitHub"""
        content = self.get_file_content(self.last_update_file)
        if content:
            try:
                data = json.loads(content)
                return datetime.strptime(data['last_update'], '%Y-%m-%d')
            except Exception as e:
                print(f"Error parsing last update file: {e}")
                return None
        return None

    def save_last_update_to_github(self):
        """Save current date as last update date to GitHub"""
        current_date = datetime.now().strftime('%Y-%m-%d')
        content = json.dumps({'last_update': current_date})
        self.update_file(
            path=self.last_update_file,
            content=content,
            message="Update last sync date"
        )

    def load_existing_articles_from_github(self) -> List[Dict]:
        """Load existing articles from GitHub"""
        content = self.get_file_content(self.articles_file)
        if content:
            try:
                return json.loads(content)
            except Exception as e:
                print(f"Error parsing articles file: {e}")
                return []
        return []

    def merge_articles(self, existing_articles: List[Dict], new_articles: List[Dict]) -> List[Dict]:
        """Merge new articles with existing ones, avoiding duplicates"""
        existing_set = {(article['title'], article['url']) for article in existing_articles}

        for article in new_articles:
            article_tuple = (article['title'], article['url'])
            if article_tuple not in existing_set:
                existing_articles.append(article)
                existing_set.add(article_tuple)

        return existing_articles

    def export_articles(self, start_date: Optional[str] = None, 
                       end_date: Optional[str] = None,
                       all_time: bool = False):
        """
        Export articles to GitHub with smart update capability
        
        Args:
            start_date: Optional start date in YYYY-MM-DD format
            end_date: Optional end date in YYYY-MM-DD format
            all_time: If True, fetch all highlights regardless of dates
        """
        if all_time:
            # 当选择 all_time 时，强制获取所有 highlights，忽略上次更新时间
            print("Fetching all highlights from the beginning")
            highlights_data = self.get_highlights()
        elif start_date:
            # 如果指定了开始日期，使用指定的日期范围
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now()
            print(f"Fetching highlights from {start_date} to {end_date or 'now'}")
            highlights_data = self.get_highlights(start_date=start_datetime, end_date=end_datetime)
        else:
            # 使用上次更新时间的增量更新逻辑
            last_update = self.load_last_update_from_github()
            if last_update:
                days_since_update = (datetime.now() - last_update).days
                print(f"Last update was {days_since_update} days ago on {last_update.strftime('%Y-%m-%d')}")
                if days_since_update > 0:
                    print(f"Fetching highlights updated after {last_update.strftime('%Y-%m-%d')}")
                    highlights_data = self.get_highlights(updated_after=last_update)
                else:
                    print("Already updated today, no need to fetch new articles")
                    return
            else:
                print("No previous update found, fetching all articles")
                highlights_data = self.get_highlights()

        # Create article data
        new_articles = self.create_article_json(highlights_data)
        print(f"Found {len(new_articles)} new articles")

        # Load existing articles
        existing_articles = self.load_existing_articles_from_github()
        print(f"Found {len(existing_articles)} existing articles")

        # Merge new articles with existing ones
        merged_articles = self.merge_articles(existing_articles, new_articles)
        print(f"Total unique articles after merge: {len(merged_articles)}")

        # Save merged articles to GitHub
        self.update_file(
            path=self.articles_file,
            content=json.dumps(merged_articles, ensure_ascii=False, indent=2),
            message="Update articles list"
        )

        # Update the last update date
        if not start_date and not all_time:  # 只有在非指定日期范围和非全量更新的情况下才更新最后同步时间
            self.save_last_update_to_github()

        print(f"Successfully updated articles in GitHub repository")
        if new_articles:
            print("New articles added:")
            for article in new_articles:
                print(f"- {article['title']}")

def main():
    # 从环境变量获取 GitHub Actions 的输入参数
    gh_start_date = os.environ.get('INPUT_START_DATE', '')
    gh_end_date = os.environ.get('INPUT_END_DATE', '')
    gh_all_time = os.environ.get('INPUT_ALL_TIME', '').lower() == 'true'

    # 设置命令行参数解析器
    parser = argparse.ArgumentParser(description='Sync Readwise highlights to GitHub')
    parser.add_argument('--start-date', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=str, help='End date in YYYY-MM-DD format')
    parser.add_argument('--all-time', action='store_true', help='Fetch all highlights from the beginning')
    
    args = parser.parse_args()

    # 优先使用命令行参数，如果没有则使用 GitHub Actions 的输入参数
    start_date = args.start_date or gh_start_date
    end_date = args.end_date or gh_end_date
    all_time = args.all_time or gh_all_time

    try:
        client = ReadwiseAPI()
        client.export_articles(
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            all_time=all_time
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
