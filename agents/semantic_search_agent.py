import json
from typing import List, Dict, Any
import numpy as np
from sentence_transformers import SentenceTransformer

from agents.agent import Agent
from book_agent_framework import Book

class SemanticSearchAgent(Agent):
    """
    Agent responsible for finding books similar to a given book
    using vector embeddings and semantic search.
    """

    name = "Semantic Search Agent"
    color = Agent.BLUE

    def __init__(self, collection):
        """
        Initialize the semantic search agent with the Chroma collection.
        
        Args:
            collection: ChromaDB collection containing book embeddings
        """
        self.log("Initializing Semantic Search Agent")
        self.collection = collection
        self.model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        self.log("Semantic Search Agent is ready")
    
    def _get_book_embedding(self, book: Book) -> List[float]:
        """
        Generate an embedding vector for a book based on its description and title.
        
        Args:
            book: The book to generate an embedding for
            
        Returns:
            Embedding vector as a list of floats
        """
        # Combine title and description for better embedding
        text = f"{book.title} by {book.author}. {book.description}"
        
        # Generate embedding
        embedding = self.model.encode([text])[0]
        return embedding.astype(float).tolist()
    
    def _book_from_metadata(self, metadata: Dict[str, Any]) -> Book:
        """
        Create a Book object from metadata stored in the vector database.
        
        Args:
            metadata: Book metadata from Chroma
            
        Returns:
            Book object
        """
        return Book(
            title=metadata.get("title", "Unknown Title"),
            author=metadata.get("author", "Unknown Author"),
            description=metadata.get("description", ""),
            isbn=metadata.get("isbn", ""),
            genres=metadata.get("genres", []),
            pages=metadata.get("pages"),
            published_year=metadata.get("published_year"),
            cover_url=metadata.get("cover_url", ""),
            goodreads_url=metadata.get("goodreads_url", "")
        )
    
    def add_book_to_index(self, book: Book) -> None:
        """
        Add a book to the vector index for future similarity searches.
        
        Args:
            book: The book to add to the index
        """
        self.log(f"Adding book to vector index: {book.title}")
        
        # Generate embedding
        embedding = self._get_book_embedding(book)
        
        # Create metadata
        metadata = {
            "title": book.title,
            "author": book.author,
            "description": book.description,
            "isbn": book.isbn or "",
            "genres": book.genres,
            "pages": book.pages or 0,
            "published_year": book.published_year or 0,
            "cover_url": book.cover_url or "",
            "goodreads_url": book.goodreads_url or ""
        }
        
        # Add to collection
        book_id = book.isbn if book.isbn else f"book_{hash(book.title + book.author)}"
        self.collection.add(
            ids=[book_id],
            embeddings=[embedding],
            metadatas=[metadata],
            documents=[book.description]
        )
        
        self.log(f"Book added to vector index with ID: {book_id}")
    
    def find_similar_books(self, book: Book, num_results: int = 5) -> List[Book]:
        """
        Find books similar to the provided book using vector similarity.
        
        Args:
            book: The reference book to find similar books for
            num_results: Maximum number of similar books to return
            
        Returns:
            List of similar Book objects
        """
        self.log(f"Searching for books similar to: {book.title}")
        
        # Generate embedding for query book
        query_embedding = self._get_book_embedding(book)
        
        # Search the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=num_results + 1  # Add 1 to filter out the book itself
        )
        
        # Process results
        similar_books = []
        for i, metadata in enumerate(results["metadatas"][0]):
            # Skip if this is the same book (by ISBN or title+author)
            if metadata.get("isbn") == book.isbn or (
                metadata.get("title") == book.title and 
                metadata.get("author") == book.author
            ):
                continue
            
            similar_book = self._book_from_metadata(metadata)
            similar_books.append(similar_book)
            
            if len(similar_books) >= num_results:
                break
        
        self.log(f"Found {len(similar_books)} similar books")
        return similar_books
    
    def search_books(self, query: str, num_results: int = 10) -> List[Book]:
        """
        Search for books matching the query using semantic search.
        
        Args:
            query: Text query to search for
            num_results: Maximum number of results to return
            
        Returns:
            List of matching Book objects
        """
        self.log(f"Searching for books matching query: {query}")
        
        # Generate embedding for query
        query_embedding = self.model.encode([query])[0].astype(float).tolist()
        
        # Search the collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=num_results
        )
        
        # Process results
        matching_books = []
        for metadata in results["metadatas"][0]:
            book = self._book_from_metadata(metadata)
            matching_books.append(book)
        
        self.log(f"Found {len(matching_books)} books matching query")
        return matching_books
    
    def get_book_by_isbn(self, isbn: str) -> Book:
        """
        Retrieve a book from the vector database by ISBN.
        
        Args:
            isbn: ISBN of the book to retrieve
            
        Returns:
            Book object or None if not found
        """
        self.log(f"Retrieving book with ISBN: {isbn}")
        
        result = self.collection.get(
            ids=[isbn],
            include=["metadatas"]
        )
        
        if result["ids"] and result["metadatas"]:
            metadata = result["metadatas"][0]
            book = self._book_from_metadata(metadata)
            self.log(f"Found book: {book.title}")
            return book
        
        self.log(f"No book found with ISBN: {isbn}")
        return None