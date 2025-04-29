import os
import sys
import logging
import json
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import chromadb
from datetime import datetime

# Colors for logging
BG_BLUE = '\033[44m'
WHITE = '\033[37m'
RESET = '\033[0m'

def init_logging():
    """Initialize logging with custom formatter"""
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "[%(asctime)s] [BookMind] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S %z",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

class Book:
    """Class to represent a book with its metadata"""
    def __init__(self, title: str, author: str, description: str, 
                 isbn: str = None, genres: List[str] = None, 
                 pages: int = None, published_year: int = None,
                 cover_url: str = None, goodreads_url: str = None):
        self.title = title
        self.author = author
        self.description = description
        self.isbn = isbn
        self.genres = genres or []
        self.pages = pages
        self.published_year = published_year
        self.cover_url = cover_url
        self.goodreads_url = goodreads_url
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert Book object to dictionary for serialization"""
        return {
            "title": self.title,
            "author": self.author,
            "description": self.description,
            "isbn": self.isbn,
            "genres": self.genres,
            "pages": self.pages,
            "published_year": self.published_year,
            "cover_url": self.cover_url,
            "goodreads_url": self.goodreads_url
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Book':
        """Create Book object from dictionary"""
        return cls(
            title=data.get("title"),
            author=data.get("author"),
            description=data.get("description"),
            isbn=data.get("isbn"),
            genres=data.get("genres"),
            pages=data.get("pages"),
            published_year=data.get("published_year"),
            cover_url=data.get("cover_url"),
            goodreads_url=data.get("goodreads_url")
        )

class BookRecommendation:
    """Class to represent a book recommendation with reasoning"""
    def __init__(self, book: Book, relevance_score: float, reasoning: str):
        self.book = book
        self.relevance_score = relevance_score
        self.reasoning = reasoning
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert recommendation to dictionary for serialization"""
        return {
            "book": self.book.to_dict(),
            "relevance_score": self.relevance_score,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookRecommendation':
        """Create BookRecommendation from dictionary"""
        recommendation = cls(
            book=Book.from_dict(data.get("book", {})),
            relevance_score=data.get("relevance_score", 0.0),
            reasoning=data.get("reasoning", "")
        )
        if "timestamp" in data:
            recommendation.timestamp = datetime.fromisoformat(data["timestamp"])
        return recommendation

class BookAnalysis:
    """Class to represent an analysis of a book"""
    def __init__(self, book: Book, sentiment: str, themes: List[str], 
                 complexity: float, estimated_reading_time: int,
                 similar_books: List[Book] = None):
        self.book = book
        self.sentiment = sentiment
        self.themes = themes
        self.complexity = complexity  # 0-1 scale
        self.estimated_reading_time = estimated_reading_time  # in minutes
        self.similar_books = similar_books or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary for serialization"""
        return {
            "book": self.book.to_dict(),
            "sentiment": self.sentiment,
            "themes": self.themes,
            "complexity": self.complexity,
            "estimated_reading_time": self.estimated_reading_time,
            "similar_books": [book.to_dict() for book in self.similar_books]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookAnalysis':
        """Create BookAnalysis from dictionary"""
        return cls(
            book=Book.from_dict(data.get("book", {})),
            sentiment=data.get("sentiment", ""),
            themes=data.get("themes", []),
            complexity=data.get("complexity", 0.5),
            estimated_reading_time=data.get("estimated_reading_time", 0),
            similar_books=[Book.from_dict(book_data) for book_data in data.get("similar_books", [])]
        )

class ReadingList:
    """Class to manage a user's reading lists"""
    def __init__(self):
        self.to_read = []  # List of Books
        self.currently_reading = []  # List of Books
        self.completed = []  # List of Books
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert reading list to dictionary for serialization"""
        return {
            "to_read": [book.to_dict() for book in self.to_read],
            "currently_reading": [book.to_dict() for book in self.currently_reading],
            "completed": [book.to_dict() for book in self.completed]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReadingList':
        """Create ReadingList from dictionary"""
        reading_list = cls()
        reading_list.to_read = [Book.from_dict(book_data) for book_data in data.get("to_read", [])]
        reading_list.currently_reading = [Book.from_dict(book_data) for book_data in data.get("currently_reading", [])]
        reading_list.completed = [Book.from_dict(book_data) for book_data in data.get("completed", [])]
        return reading_list

class BookAgentFramework:
    """Main framework for coordinating book recommendation agents"""
    
    DB = "books_vectorstore"
    MEMORY_FILENAME = "book_memory.json"
    
    def __init__(self):
        init_logging()
        load_dotenv()
        # Initialize vector database
        client = chromadb.PersistentClient(path=self.DB)
        self.collection = client.get_or_create_collection('books')
        
        # Memory for recommendations and analyses
        self.recommendations_memory = self.read_recommendations()
        self.analyses_memory = self.read_analyses()
        self.reading_list = self.read_reading_list()
        
        # Initialize agents (to be done in init_agents_as_needed)
        self.recommendation_agent = None
        self.semantic_search_agent = None
        self.analysis_agent = None
        self.community_agent = None
        self.planning_agent = None
        self.notification_agent = None
    
    def init_agents_as_needed(self):
        """Initialize agents if they haven't been initialized yet"""
        if not self.recommendation_agent:
            self.log("Initializing BookMind Agent Framework")
            from agents.recommendation_agent import RecommendationAgent
            from agents.semantic_search_agent import SemanticSearchAgent
            from agents.analysis_agent import AnalysisAgent
            from agents.community_agent import CommunityAgent
            from agents.planning_agent import PlanningAgent
            from agents.notification_agent import NotificationAgent
            
            self.recommendation_agent = RecommendationAgent()
            self.semantic_search_agent = SemanticSearchAgent(self.collection)
            self.analysis_agent = AnalysisAgent()
            self.community_agent = CommunityAgent()
            self.planning_agent = PlanningAgent(
                self.recommendation_agent,
                self.semantic_search_agent,
                self.analysis_agent,
                self.community_agent
            )
            self.notification_agent = NotificationAgent()
            self.log("BookMind Agent Framework is ready")
    
    def read_recommendations(self) -> List[BookRecommendation]:
        """Read recommendations from persistent storage"""
        recommendations_file = "recommendations_memory.json"
        if os.path.exists(recommendations_file):
            with open(recommendations_file, "r") as file:
                data = json.load(file)
            return [BookRecommendation.from_dict(item) for item in data]
        return []
    
    def write_recommendations(self) -> None:
        """Write recommendations to persistent storage"""
        recommendations_file = "recommendations_memory.json"
        data = [recommendation.to_dict() for recommendation in self.recommendations_memory]
        with open(recommendations_file, "w") as file:
            json.dump(data, file, indent=2)
    
    def read_analyses(self) -> Dict[str, BookAnalysis]:
        """Read book analyses from persistent storage"""
        analyses_file = "analyses_memory.json"
        if os.path.exists(analyses_file):
            with open(analyses_file, "r") as file:
                data = json.load(file)
            return {isbn: BookAnalysis.from_dict(analysis_data) 
                   for isbn, analysis_data in data.items() if isbn}
        return {}
    
    def write_analyses(self) -> None:
        """Write book analyses to persistent storage"""
        analyses_file = "analyses_memory.json"
        data = {analysis.book.isbn: analysis.to_dict() 
                for analysis in self.analyses_memory.values() if analysis.book.isbn}
        with open(analyses_file, "w") as file:
            json.dump(data, file, indent=2)
    
    def read_reading_list(self) -> ReadingList:
        """Read reading list from persistent storage"""
        reading_list_file = "reading_list.json"
        if os.path.exists(reading_list_file):
            with open(reading_list_file, "r") as file:
                data = json.load(file)
            return ReadingList.from_dict(data)
        return ReadingList()
    
    def write_reading_list(self) -> None:
        """Write reading list to persistent storage"""
        reading_list_file = "reading_list.json"
        data = self.reading_list.to_dict()
        with open(reading_list_file, "w") as file:
            json.dump(data, file, indent=2)
    
    def log(self, message: str):
        """Log a message with the agent framework prefix"""
        text = BG_BLUE + WHITE + "[BookMind Framework] " + message + RESET
        logging.info(text)
    
    def get_book_recommendation(self, query: str, num_recommendations: int = 5) -> List[BookRecommendation]:
        """Get book recommendations based on user query"""
        self.init_agents_as_needed()
        self.log(f"Processing recommendation request: {query}")
        
        # Let the planning agent coordinate the recommendation process
        recommendations = self.planning_agent.get_recommendations(query, num_recommendations)
        
        # Update memory with new recommendations
        for recommendation in recommendations:
            if recommendation not in self.recommendations_memory:
                self.recommendations_memory.append(recommendation)
        
        self.write_recommendations()
        return recommendations
    
    def analyze_book(self, book: Book) -> BookAnalysis:
        """Analyze a book for sentiment, themes, complexity and reading time"""
        self.init_agents_as_needed()
        
        # Check if we've already analyzed this book
        if book.isbn and book.isbn in self.analyses_memory:
            self.log(f"Retrieved cached analysis for {book.title}")
            return self.analyses_memory[book.isbn]
        
        self.log(f"Analyzing book: {book.title}")
        analysis = self.analysis_agent.analyze_book(book)
        
        # Update memory with new analysis
        if book.isbn:
            self.analyses_memory[book.isbn] = analysis
            self.write_analyses()
        
        return analysis
    
    def find_similar_books(self, book: Book, num_results: int = 5) -> List[Book]:
        """Find books similar to the provided book"""
        self.init_agents_as_needed()
        self.log(f"Finding books similar to: {book.title}")
        return self.semantic_search_agent.find_similar_books(book, num_results)
    
    def get_trending_books(self, genre: str = None, limit: int = 10) -> List[Book]:
        """Get trending books, optionally filtered by genre"""
        self.init_agents_as_needed()
        self.log(f"Retrieving trending books{' in ' + genre if genre else ''}")
        return self.community_agent.get_trending_books(genre, limit)
    
    def add_to_reading_list(self, book: Book, list_type: str = "to_read") -> None:
        """Add a book to one of the reading lists"""
        self.log(f"Adding {book.title} to {list_type} list")
        
        # Remove from other lists if present
        for lst in ["to_read", "currently_reading", "completed"]:
            if lst != list_type:
                lst_obj = getattr(self.reading_list, lst)
                lst_obj = [b for b in lst_obj if b.isbn != book.isbn]
                setattr(self.reading_list, lst, lst_obj)
        
        # Add to the specified list
        lst_obj = getattr(self.reading_list, list_type)
        lst_obj.append(book)
        setattr(self.reading_list, list_type, lst_obj)
        
        self.write_reading_list()
    
    def remove_from_reading_list(self, book: Book, list_type: str = "to_read") -> None:
        """Remove a book from one of the reading lists"""
        self.log(f"Removing {book.title} from {list_type} list")
        
        lst_obj = getattr(self.reading_list, list_type)
        lst_obj = [b for b in lst_obj if b.isbn != book.isbn]
        setattr(self.reading_list, list_type, lst_obj)
        
        self.write_reading_list()
    
    def notify_user(self, message: str, title: str = "BookMind Notification") -> None:
        """Send a notification to the user"""
        self.init_agents_as_needed()
        self.log(f"Sending notification: {title}")
        self.notification_agent.notify(message, title)


if __name__ == "__main__":
    framework = BookAgentFramework()
    # Example usage
    recommendations = framework.get_book_recommendation("fantasy books with strong female protagonists")
    for rec in recommendations:
        print(f"Recommended: {rec.book.title} by {rec.book.author}")
        print(f"Reasoning: {rec.reasoning}")
        print("---")