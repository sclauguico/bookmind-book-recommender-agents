import re
import json
from typing import List, Dict, Any, Tuple
from openai import OpenAI

from agents.agent import Agent
from book_agent_framework import Book, BookAnalysis

class AnalysisAgent(Agent):
    """
    Agent responsible for analyzing books to extract sentiment,
    themes, complexity, and estimated reading time.
    """

    name = "Analysis Agent"
    color = Agent.MAGENTA
    
    # Average reading speeds in words per minute for different complexity levels
    READING_SPEEDS = {
        "low": 250,    # Easy books
        "medium": 200, # Average complexity
        "high": 150    # Complex books
    }
    
    # Words per page for typical books
    WORDS_PER_PAGE = 300

    def __init__(self):
        """Initialize the analysis agent"""
        self.log("Initializing Analysis Agent")
        self.openai = OpenAI()
        self.log("Analysis Agent is ready")
    
    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extract JSON from a text response that might contain other content.
        
        Args:
            response: The text response that should contain JSON
            
        Returns:
            Parsed JSON as a dictionary
        """
        try:
            # Try to find JSON block in markdown format
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without code blocks
                json_match = re.search(r'\{[\s\S]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    self.log("Could not extract JSON from response")
                    return {}
            
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.log(f"Error parsing JSON: {str(e)}")
            return {}
    
    def _analyze_with_llm(self, book: Book) -> Dict[str, Any]:
        """
        Use LLM to analyze a book and extract sentiment, themes, and complexity.
        
        Args:
            book: The book to analyze
            
        Returns:
            Dictionary with sentiment, themes, and complexity
        """
        self.log(f"Analyzing book with LLM: {book.title}")
        
        system_prompt = """
        You are a literary analysis expert. Analyze the book description provided and return a JSON object with:
        
        1. sentiment: The emotional tone of the book (e.g., "hopeful", "dark", "humorous", "melancholic")
        2. themes: An array of 3-5 main themes or topics in the book
        3. complexity: A float from 0.0 to 1.0 representing the reading complexity (0.0 = very easy, 1.0 = very complex)
        
        Base your analysis on the book's title, author, and description.
        
        Return ONLY a JSON object like:
        ```json
        {
          "sentiment": "hopeful",
          "themes": ["identity", "resilience", "family dynamics", "social change"],
          "complexity": 0.7
        }
        ```
        """
        
        book_text = f"Title: {book.title}\nAuthor: {book.author}\nDescription: {book.description}\nGenres: {', '.join(book.genres)}"
        
        try:
            response = self.openai.chat.completions.create(
                model="gpt-4-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": book_text}
                ]
            )
            
            analysis_data = self._extract_json_from_response(response.choices[0].message.content)
            
            # Apply defaults if data is missing
            if "sentiment" not in analysis_data:
                analysis_data["sentiment"] = "neutral"
            
            if "themes" not in analysis_data or not analysis_data["themes"]:
                analysis_data["themes"] = ["general fiction"]
            
            if "complexity" not in analysis_data:
                analysis_data["complexity"] = 0.5
                
            return analysis_data
            
        except Exception as e:
            self.log(f"Error in LLM analysis: {str(e)}")
            return {
                "sentiment": "neutral",
                "themes": ["general fiction"],
                "complexity": 0.5
            }
    
    def _calculate_reading_time(self, book: Book, complexity: float) -> int:
        """
        Calculate estimated reading time in minutes based on book length and complexity.
        
        Args:
            book: The book to calculate reading time for
            complexity: The complexity rating (0.0 to 1.0)
            
        Returns:
            Estimated reading time in minutes
        """
        if not book.pages or book.pages <= 0:
            # If no page count, estimate based on description length
            words = len(book.description.split())
            # Assume the book is 50-100 times longer than the description
            estimated_words = words * 75
            pages = estimated_words / self.WORDS_PER_PAGE
        else:
            pages = book.pages
        
        # Determine reading speed based on complexity
        if complexity < 0.3:
            reading_speed = self.READING_SPEEDS["low"]
        elif complexity < 0.7:
            reading_speed = self.READING_SPEEDS["medium"]
        else:
            reading_speed = self.READING_SPEEDS["high"]
        
        # Calculate reading time
        words = pages * self.WORDS_PER_PAGE
        reading_time_minutes = words / reading_speed
        
        return int(reading_time_minutes)
    
    def analyze_book(self, book: Book) -> BookAnalysis:
        """
        Analyze a book to extract sentiment, themes, complexity, and estimated reading time.
        
        Args:
            book: The book to analyze
            
        Returns:
            BookAnalysis object with the analysis results
        """
        self.log(f"Starting analysis for book: {book.title}")
        
        # Get sentiment, themes, and complexity from LLM
        analysis_data = self._analyze_with_llm(book)
        
        sentiment = analysis_data.get("sentiment", "neutral")
        themes = analysis_data.get("themes", ["general fiction"])
        complexity = analysis_data.get("complexity", 0.5)
        
        # Calculate estimated reading time
        reading_time = self._calculate_reading_time(book, complexity)
        
        self.log(f"Analysis complete - Sentiment: {sentiment}, Complexity: {complexity:.2f}, Reading time: {reading_time} minutes")
        
        # Create and return BookAnalysis object
        return BookAnalysis(
            book=book,
            sentiment=sentiment,
            themes=themes,
            complexity=complexity,
            estimated_reading_time=reading_time,
            similar_books=[]  # To be filled by semantic search later
        )