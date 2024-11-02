import requests
import json
from datetime import datetime, timedelta
import os
from typing import List, Dict, Optional
from pathlib import Path
import re
from github import Github

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

    # ... 其余代码保持不变 ...

def main():
    try:
        client = ReadwiseAPI()
        client.export_articles()
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        raise  # 在 GitHub Actions 中抛出异常以标记任务失败

if __name__ == "__main__":
    main()
