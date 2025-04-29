import re
import json
import time
from typing import List, Dict, Any, Optional
import requests
import feedparser
from bs4 import BeautifulSoup

from agents.agent import Agent
from book_agent_framework import Book

class CommunityAgent(Agent):
    """
    Agent responsible for discovering trending books from community sources
    like Goodreads feeds, bestseller lists, and book recommendation sites.
    """

    name = "Community Agent"
    color = Agent.CYAN
    
    # URLs for book discovery
    GOODREADS_RSS_FEEDS = [
        "https://www.goodreads.com/shelf/show/currently-reading.rss",
        "https://www.goodreads.com/shelf/show/popular.rss",
        "https://www.goodreads.com/shelf/show/new-releases.rss"
    ]
    
    # Genre-specific feed URLs
    GENRE_FEEDS = {
        "fantasy": "https://www.goodreads.com/shelf/show/fantasy.rss",
        "science_fiction": "https://www.goodreads.com/shelf/show/science-fiction.rss",
        "mystery": "https://www.goodreads.com/shelf/show/mystery.rss",
        "romance": "https://www.goodreads.com/shelf/show/romance.rss",
        "historical": "https://www.goodreads.com/shelf/show/historical-fiction.rss",
        "biography": "https://www.goodreads.com/shelf/show/biography.rss",
        "self_help": "https://www.goodreads.com/shelf/show/self-help.rss",
        "horror": "https://www.goodreads.com/shelf/show/horror.rss"
    }
    
    # New York Times API endpoint for bestsellers
    NYT_API_ENDPOINT = "https://api.nytimes.com/svc/books/v3/lists/current/hardcover-fiction.json"
    
    def __init__(self):
        """Initialize the community agent"""
        self.log("Initializing Community Agent")
        self.nyt_api_key = None
        try:
            # Try to load API key
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('NYT_API_KEY='):
                        self.nyt_api_key = line.split('=')[1].strip()
        except:
            pass
            
        self.log("Community Agent is ready")
    
    def _clean_html(self, html_text: str) -> str:
        """
        Clean HTML from text.
        
        Args:
            html_text: Text that may contain HTML tags
            
        Returns:
            Cleaned text without HTML tags
        """
        soup = BeautifulSoup(html_text, 'html.parser')
        return soup.get_text()
    
    def _extract_book_from_goodreads_entry(self, entry) -> Optional[Book]:
        """
        Extract book information from a Goodreads RSS entry.
        
        Args:
            entry: RSS entry from Goodreads
            
        Returns:
            Book object or None if extraction fails
        """
        try:
            title_author = entry.title
            
            # Goodreads RSS format is typically "Book Title by Author Name"
            match = re.match(r"(.*) by (.*)", title_author)
            if match:
                title = match.group(1).strip()
                author = match.group(2).strip()
            else:
                title = title_author
                author = "Unknown Author"
            
            # Extract description
            description = ""
            if 'description' in entry:
                description = self._clean_html(entry.description)
            elif 'summary' in entry:
                description = self._clean_html(entry.summary)
            
            # Extract URL
            url = entry.link if 'link' in entry else ""
            
            # Try to extract ISBN from URL or content
            isbn = ""
            if url and 'goodreads.com' in url:
                isbn_match = re.search(r"([0-9]{10}|[0-9]{13})", url)
                if isbn_match:
                    isbn = isbn_match.group(1)
            
            if not isbn and description:
                isbn_match = re.search(r"ISBN[-: ]?([0-9]{10}|[0-9]{13})", description)
                if isbn_match:
                    isbn = isbn_match.group(1)
            
            # Create book object
            return Book(
                title=title,
                author=author,
                description=description,
                isbn=isbn,
                genres=[],  # Will be filled later
                goodreads_url=url
            )
        
        except Exception as e:
            self.log(f"Error extracting book from Goodreads entry: {str(e)}")
            return None
    
    def _fetch_goodreads_books(self, feed_url: str, limit: int = 10) -> List[Book]:
        """
        Fetch books from a Goodreads RSS feed.
        
        Args:
            feed_url: URL of the Goodreads RSS feed
            limit: Maximum number of books to fetch
            
        Returns:
            List of Book objects
        """
        self.log(f"Fetching books from Goodreads feed: {feed_url}")
        
        try:
            feed = feedparser.parse(feed_url)
            books = []
            
            for entry in feed.entries[:limit]:
                book = self._extract_book_from_goodreads_entry(entry)
                if book:
                    books.append(book)
            
            self.log(f"Fetched {len(books)} books from Goodreads feed")
            return books
        
        except Exception as e:
            self.log(f"Error fetching books from Goodreads: {str(e)}")
            return []
    
    def _fetch_nyt_bestsellers(self, limit: int = 10) -> List[Book]:
        """
        Fetch bestselling books from the New York Times API.
        
        Args:
            limit: Maximum number of books to fetch
            
        Returns:
            List of Book objects
        """
        if not self.nyt_api_key:
            self.log("NYT API key not found, skipping bestsellers")
            return []
        
        self.log("Fetching bestsellers from New York Times")
        
        try:
            params = {"api-key": self.nyt_api_key}
            response = requests.get(self.NYT_API_ENDPOINT, params=params)
            
            if response.status_code != 200:
                self.log(f"Error from NYT API: {response.status_code}")
                return []
            
            data = response.json()
            books = []
            
            for book_data in data.get("results", {}).get("books", [])[:limit]:
                book = Book(
                    title=book_data.get("title", "Unknown Title"),
                    author=book_data.get("author", "Unknown Author"),
                    description=book_data.get("description", ""),
                    isbn=book_data.get("primary_isbn13", ""),
                    genres=["bestseller"],
                    published_year=None,  # Not provided by API
                    cover_url=book_data.get("book_image", "")
                )
                books.append(book)
            
            self.log(f"Fetched {len(books)} bestsellers from NYT")
            return books
        
        except Exception as e:
            self.log(f"Error fetching NYT bestsellers: {str(e)}")
            return []
    
    def get_trending_books(self, genre: Optional[str] = None, limit: int = 10) -> List[Book]:
        """
        Get trending books, optionally filtered by genre.
        
        Args:
            genre: Optional genre to filter by
            limit: Maximum number of books to return
            
        Returns:
            List of trending Book objects
        """
        self.log(f"Finding trending books{' in ' + genre if genre else ''}")
        
        trending_books = []
        
        # If genre is specified, use genre-specific feed
        if genre and genre in self.GENRE_FEEDS:
            feed_url = self.GENRE_FEEDS[genre]
            trending_books.extend(self._fetch_goodreads_books(feed_url, limit))
        else:
            # Otherwise, fetch from general trending feeds
            for feed_url in self.GOODREADS_RSS_FEEDS:
                # Avoid rate limiting
                time.sleep(1)
                trending_books.extend(self._fetch_goodreads_books(feed_url, limit // 2))
                
                # Stop if we have enough books
                if len(trending_books) >= limit:
                    break
            
            # Try to add NYT bestsellers if we need more books
            if len(trending_books) < limit:
                trending_books.extend(self._fetch_nyt_bestsellers(limit // 2))
        
        # Deduplicate books by ISBN and title+author
        unique_books = []
        seen_isbns = set()
        seen_title_authors = set()
        
        for book in trending_books:
            title_author = f"{book.title} by {book.author}".lower()
            
            if book.isbn and book.isbn in seen_isbns:
                continue
            
            if title_author in seen_title_authors:
                continue
            
            unique_books.append(book)
            
            if book.isbn:
                seen_isbns.add(book.isbn)
            
            seen_title_authors.add(title_author)
            
            if len(unique_books) >= limit:
                break
        
        self.log(f"Found {len(unique_books)} trending books")
        return unique_books[:limit]