import os
import json
import re
import modal
from typing import List, Dict, Any

from agents.agent import Agent
from book_agent_framework import Book, BookRecommendation

class RecommendationAgent(Agent):
    """
    Agent responsible for generating personalized book recommendations
    using a fine-tuned LLM deployed on Modal.
    """

    name = "Recommendation Agent"
    color = Agent.RED

    def __init__(self):
        """
        Initialize the recommendation agent by connecting to the Modal service.
        """
        self.log("Initializing Recommendation Agent - connecting to modal")
        try:
            BookRecommender = modal.Cls.lookup("book-recommender", "BookRecommender")
            self.recommender = BookRecommender()
            self.log("Recommendation Agent successfully connected to Modal")
        except Exception as e:
            self.log(f"Failed to connect to Modal: {str(e)}")
            self.log("Using fallback to OpenAI API for recommendations")
            from openai import OpenAI
            self.recommender = None
            self.openai_client = OpenAI()
        
        # Load genre mapping for categorizing books
        self.genres = self._load_genres()
    
    def _load_genres(self) -> Dict[str, List[str]]:
        """Load genre categories and their keywords"""
        genres_file = "data/genres.json"
        if os.path.exists(genres_file):
            with open(genres_file, "r") as f:
                return json.load(f)
        return {
            "fantasy": ["fantasy", "magic", "dragons", "wizards", "mythical"],
            "science_fiction": ["sci-fi", "science fiction", "space", "future", "dystopian"],
            "mystery": ["mystery", "detective", "crime", "thriller", "suspense"],
            "romance": ["romance", "love", "relationship", "romantic", "passion"],
            "historical": ["historical", "history", "period", "ancient", "medieval"],
            "biography": ["biography", "memoir", "autobiography", "true story", "life story"],
            "self_help": ["self-help", "personal development", "motivation", "productivity", "psychology"],
            "horror": ["horror", "scary", "supernatural", "ghost", "terrifying"]
        }
    
    def _categorize_book(self, book: Book) -> List[str]:
        """
        Categorize a book into genres based on its description and existing genres
        """
        if book.genres and len(book.genres) > 0:
            return book.genres
        
        assigned_genres = []
        lower_desc = book.description.lower()
        
        for genre, keywords in self.genres.items():
            for keyword in keywords:
                if keyword.lower() in lower_desc:
                    assigned_genres.append(genre)
                    break
        
        return assigned_genres if assigned_genres else ["uncategorized"]
    
    def _format_user_query(self, query: str) -> str:
        """Format the user query for the recommendation model"""
        return f"""
        I'm looking for book recommendations. Here's what I'm interested in:
        {query}
        
        Please recommend books that match my interests.
        """
    
    def _parse_remote_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse the response from the remote model into structured book data"""
        try:
            # Extract the JSON part from the response
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'\[\s*\{.*\}\s*\]', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    self.log("Could not extract JSON from response. Returning empty list.")
                    return []
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log(f"Error parsing JSON: {str(e)}")
            return []
    
    def _create_book_from_data(self, book_data: Dict[str, Any]) -> Book:
        """Create a Book object from parsed book data"""
        return Book(
            title=book_data.get("title", "Unknown Title"),
            author=book_data.get("author", "Unknown Author"),
            description=book_data.get("description", ""),
            isbn=book_data.get("isbn", ""),
            genres=book_data.get("genres", []),
            pages=book_data.get("pages"),
            published_year=book_data.get("published_year"),
            cover_url=book_data.get("cover_url", ""),
            goodreads_url=book_data.get("goodreads_url", "")
        )
    
    def _fallback_recommendation(self, query: str) -> List[Dict[str, Any]]:
        """Use OpenAI API as fallback when Modal is unavailable"""
        self.log("Using OpenAI API fallback for recommendations")
        
        system_prompt = """
        You are a book recommendation expert. When a user asks for book recommendations,
        provide 3-5 relevant book suggestions in JSON format. Each book should include:
        
        - title (string): The book title
        - author (string): The book author
        - description (string): A brief description of the book
        - isbn (string, optional): ISBN if known
        - genres (array of strings): Book genres
        - reasoning (string): Why this book matches the user's interests
        
        Respond with only a JSON array of books. Format the response like:
        ```json
        [
          {
            "title": "Book Title",
            "author": "Book Author",
            "description": "Book description...",
            "isbn": "1234567890",
            "genres": ["Fantasy", "Adventure"],
            "reasoning": "This book matches your interest in..."
          },
          ...
        ]
        ```
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": self._format_user_query(query)}
                ]
            )
            return self._parse_remote_response(response.choices[0].message.content)
        except Exception as e:
            self.log(f"Error in OpenAI fallback: {str(e)}")
            return []
    
    def get_recommendations(self, query: str, num_recommendations: int = 5) -> List[BookRecommendation]:
        """
        Get personalized book recommendations based on the user query.
        
        Args:
            query: User's request describing what they're looking for
            num_recommendations: Maximum number of recommendations to return
            
        Returns:
            List of BookRecommendation objects
        """
        self.log(f"Generating recommendations for query: {query}")
        
        try:
            if self.recommender:
                # Use Modal-deployed fine-tuned model
                response = self.recommender.recommend.remote(
                    query=self._format_user_query(query),
                    num_results=num_recommendations
                )
                book_data_list = self._parse_remote_response(response)
            else:
                # Use fallback to OpenAI
                book_data_list = self._fallback_recommendation(query)
        except Exception as e:
            self.log(f"Error getting recommendations: {str(e)}")
            book_data_list = self._fallback_recommendation(query)
        
        # Create BookRecommendation objects
        recommendations = []
        for i, book_data in enumerate(book_data_list):
            if i >= num_recommendations:
                break
                
            book = self._create_book_from_data(book_data)
            
            # Ensure the book has genres
            if not book.genres or len(book.genres) == 0:
                book.genres = self._categorize_book(book)
            
            # Calculate relevance score (descending from 1.0)
            relevance_score = 1.0 - (i * 0.1)
            
            reasoning = book_data.get("reasoning", "This book matches your interests.")
            
            recommendations.append(BookRecommendation(
                book=book,
                relevance_score=relevance_score,
                reasoning=reasoning
            ))
        
        self.log(f"Generated {len(recommendations)} recommendations")
        return recommendations