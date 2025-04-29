from typing import List, Dict, Any, Optional

from agents.agent import Agent
from book_agent_framework import Book, BookRecommendation

class PlanningAgent(Agent):
    """
    Agent responsible for coordinating other agents to provide
    comprehensive book recommendations and analysis.
    """

    name = "Planning Agent"
    color = Agent.GREEN

    def __init__(self, recommendation_agent, semantic_search_agent, analysis_agent, community_agent):
        """
        Initialize the planning agent with references to other agents.
        
        Args:
            recommendation_agent: Agent for generating book recommendations
            semantic_search_agent: Agent for finding similar books
            analysis_agent: Agent for analyzing book sentiment and themes
            community_agent: Agent for finding trending books
        """
        self.log("Initializing Planning Agent")
        self.recommendation_agent = recommendation_agent
        self.semantic_search_agent = semantic_search_agent
        self.analysis_agent = analysis_agent
        self.community_agent = community_agent
        self.log("Planning Agent is ready")
    
    def get_recommendations(self, query: str, num_recommendations: int = 5) -> List[BookRecommendation]:
        """
        Coordinate a comprehensive recommendation process.
        
        Steps:
        1. Get initial recommendations from recommendation agent
        2. Enhance recommendations with analysis
        3. Find similar books for each recommendation
        
        Args:
            query: User's recommendation request
            num_recommendations: Maximum number of recommendations to return
            
        Returns:
            List of enhanced BookRecommendation objects
        """
        self.log(f"Planning recommendation workflow for query: {query}")
        
        # Step 1: Get initial recommendations
        recommendations = self.recommendation_agent.get_recommendations(query, num_recommendations)
        if not recommendations:
            self.log("No recommendations found, trying community trending books")
            trending_books = self.community_agent.get_trending_books(limit=num_recommendations)
            recommendations = [
                BookRecommendation(
                    book=book,
                    relevance_score=0.5,
                    reasoning="This is a trending book that might interest you."
                )
                for book in trending_books
            ]
        
        # Step 2: Enhance recommendations with analysis and similar books
        enhanced_recommendations = []
        for recommendation in recommendations:
            # Get book analysis
            self.log(f"Enhancing recommendation for {recommendation.book.title}")
            
            try:
                # Analyze the book
                analysis = self.analysis_agent.analyze_book(recommendation.book)
                
                # Find similar books
                similar_books = self.semantic_search_agent.find_similar_books(
                    recommendation.book, 
                    num_results=3
                )
                
                # Update the book with analysis data
                recommendation.book.genres = list(set(recommendation.book.genres + analysis.themes))
                
                # Add similar books to analysis
                analysis.similar_books = similar_books
                
                # Add the book and its analysis to vector store if it has an ISBN
                if recommendation.book.isbn:
                    self.semantic_search_agent.add_book_to_index(recommendation.book)
                
                # Keep recommendation with enhanced context
                enhanced_recommendations.append(recommendation)
                
            except Exception as e:
                self.log(f"Error enhancing recommendation: {str(e)}")
                # Still include the recommendation even if enhancement fails
                enhanced_recommendations.append(recommendation)
        
        self.log(f"Enhanced {len(enhanced_recommendations)} recommendations")
        return enhanced_recommendations
    
    def explore_genre(self, genre: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Provide an exploration of books in a specific genre.
        
        Args:
            genre: Genre to explore
            limit: Maximum number of books to include
            
        Returns:
            List of dictionaries with book, analysis, and similar books
        """
        self.log(f"Planning genre exploration for: {genre}")
        
        # Step 1: Get trending books in this genre
        trending_books = self.community_agent.get_trending_books(genre=genre, limit=limit)
        
        # Step 2: Analyze each book and find similar books
        exploration_results = []
        for book in trending_books:
            try:
                # Analyze the book
                analysis = self.analysis_agent.analyze_book(book)
                
                # Find similar books
                similar_books = self.semantic_search_agent.find_similar_books(
                    book, 
                    num_results=3
                )
                
                # Add similar books to analysis
                analysis.similar_books = similar_books
                
                # Add the book to results
                exploration_results.append({
                    "book": book,
                    "analysis": analysis
                })
                
                # Add the book and its analysis to vector store if it has an ISBN
                if book.isbn:
                    self.semantic_search_agent.add_book_to_index(book)
                
            except Exception as e:
                self.log(f"Error analyzing trending book: {str(e)}")
                # Still include the book without analysis
                exploration_results.append({
                    "book": book,
                    "analysis": None
                })
        
        self.log(f"Completed exploration with {len(exploration_results)} results")
        return exploration_results
    
    def analyze_book_request(self, book: Book) -> Dict[str, Any]:
        """
        Process a request to analyze a specific book.
        
        Args:
            book: The book to analyze
            
        Returns:
            Dictionary with analysis and similar books
        """
        self.log(f"Planning analysis for book: {book.title}")
        
        try:
            # Step 1: Check if book exists in vector store
            if book.isbn:
                existing_book = self.semantic_search_agent.get_book_by_isbn(book.isbn)
                if existing_book:
                    # Use existing book data but keep original book's ISBN
                    isbn = book.isbn
                    book = existing_book
                    book.isbn = isbn
            
            # Step 2: Analyze the book
            analysis = self.analysis_agent.analyze_book(book)
            
            # Step 3: Find similar books
            similar_books = self.semantic_search_agent.find_similar_books(
                book, 
                num_results=5
            )
            
            # Step 4: Add similar books to analysis
            analysis.similar_books = similar_books
            
            # Step 5: Add the book to vector store if it has an ISBN
            if book.isbn:
                self.semantic_search_agent.add_book_to_index(book)
            
            self.log("Book analysis complete")
            return {
                "book": book,
                "analysis": analysis
            }
            
        except Exception as e:
            self.log(f"Error analyzing book: {str(e)}")
            return {
                "book": book,
                "analysis": None,
                "error": str(e)
            }