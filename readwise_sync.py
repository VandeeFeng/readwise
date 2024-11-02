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
        # 原有的初始化代码保持不变
        self.readwise_token = os.environ.get("READWISE_TOKEN")
        if not self.readwise_token:
            raise ValueError("READWISE_TOKEN not found in environment variables")

        self.github_token = os.environ.get("GITHUB_TOKEN")
        if not self.github_token:
            raise ValueError("GITHUB_TOKEN not found in environment variables")
        
        self.github_repo = os.environ.get("GITHUB_REPOSITORY")
        if not self.github_repo:
            raise ValueError("Not running in GitHub Actions environment (GITHUB_REPOSITORY not found)")

        self.github = Github(self.github_token)
        self.repo = self.github.get_repo(self.github_repo)

        self.base_url = "https://readwise.io/api/v2"
        self.headers = {
            "Authorization": f"Token {self.readwise_token}"
        }
        self.last_update_file = "last_update.json"
        self.articles_file = "articles.json"

    # ... 其他方法保持不变 ...

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
        updated_after = None
        
        if all_time:
            print("Fetching all highlights from the beginning")
            updated_after = None
        elif start_date:
            # 如果指定了开始日期，使用指定的日期范围
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') if end_date else datetime.now()
            print(f"Fetching highlights from {start_date} to {end_date or 'now'}")
            highlights_data = self.get_highlights(start_date=start_datetime, end_date=end_datetime)
        else:
            # 使用上次更新时间
            last_update = self.load_last_update()
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

        # Get highlights
        print("Fetching highlights from Readwise...")
        highlights_data = self.get_highlights(updated_after=updated_after)

        # Create article data
        new_articles = self.create_article_json(highlights_data)
        print(f"Found {len(new_articles)} new articles")

        # Load existing articles
        existing_articles = self.load_existing_articles()
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
        if not start_date:  # 只有在不是指定日期范围的情况下才更新最后同步时间
            self.save_last_update()

        print(f"Successfully updated articles in GitHub repository")
        if new_articles:
            print("New articles added:")
            for article in new_articles:
                print(f"- {article['title']}")

def main():
    parser = argparse.ArgumentParser(description='Sync Readwise highlights to GitHub')
    parser.add_argument('--start-date', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end-date', type=str, help='End date in YYYY-MM-DD format')
    parser.add_argument('--all-time', action='store_true', help='Fetch all highlights from the beginning')
    
    args = parser.parse_args()

    try:
        client = ReadwiseAPI()
        client.export_articles(
            start_date=args.start_date,
            end_date=args.end_date,
            all_time=args.all_time
        )
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    main()
