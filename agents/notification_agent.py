import os
import http.client
import urllib
from typing import Optional

from agents.agent import Agent
from book_agent_framework import Book, BookRecommendation

class NotificationAgent(Agent):
    """
    Agent responsible for sending notifications to users about 
    new book recommendations or interesting discoveries.
    """

    name = "Notification Agent"
    color = Agent.WHITE
    
    # Constants for notification methods
    DO_PUSH = True  # Use Pushover for push notifications
    DO_EMAIL = False  # Email notifications (not implemented)

    def __init__(self):
        """Initialize the notification agent"""
        self.log("Initializing Notification Agent")
        
        # Initialize Pushover credentials
        if self.DO_PUSH:
            self.pushover_user = os.getenv('PUSHOVER_USER', '')
            self.pushover_token = os.getenv('PUSHOVER_TOKEN', '')
            
            if not self.pushover_user or not self.pushover_token:
                self.log("Pushover credentials not found, push notifications will not work")
                self.DO_PUSH = False
            else:
                self.log("Pushover configured for notifications")
        
        self.log("Notification Agent is ready")
    
    def push(self, message: str, title: str = "BookMind") -> bool:
        """
        Send a push notification using Pushover.
        
        Args:
            message: The notification message
            title: The notification title
            
        Returns:
            True if the notification was sent successfully
        """
        if not self.DO_PUSH:
            self.log("Push notifications are disabled")
            return False
        
        self.log(f"Sending push notification: {title}")
        
        try:
            conn = http.client.HTTPSConnection("api.pushover.net:443")
            conn.request(
                "POST", 
                "/1/messages.json",
                urllib.parse.urlencode({
                    "token": self.pushover_token,
                    "user": self.pushover_user,
                    "title": title,
                    "message": message,
                    "sound": "bookSound"  # Default sound
                }), 
                {"Content-type": "application/x-www-form-urlencoded"}
            )
            
            response = conn.getresponse()
            return response.status == 200
            
        except Exception as e:
            self.log(f"Error sending push notification: {str(e)}")
            return False
    
    def notify(self, message: str, title: str = "BookMind Notification") -> bool:
        """
        Send a notification through all available channels.
        
        Args:
            message: The notification message
            title: The notification title
            
        Returns:
            True if at least one notification was sent successfully
        """
        self.log(f"Sending notification: {title}")
        
        success = False
        
        if self.DO_PUSH:
            push_success = self.push(message, title)
            success = success or push_success
        
        if not success:
            self.log("No notifications were sent successfully")
        
        return success
    
    def notify_recommendation(self, recommendation: BookRecommendation) -> bool:
        """
        Send a notification about a book recommendation.
        
        Args:
            recommendation: The book recommendation to notify about
            
        Returns:
            True if the notification was sent successfully
        """
        book = recommendation.book
        title = f"Book Recommendation: {book.title}"
        
        message = f"{book.title} by {book.author}\n\n"
        message += f"Reasoning: {recommendation.reasoning}\n\n"
        
        if book.goodreads_url:
            message += f"View on Goodreads: {book.goodreads_url}"
        
        return self.notify(message, title)
    
    def notify_trending_books(self, books: list[Book], genre: Optional[str] = None) -> bool:
        """
        Send a notification about trending books.
        
        Args:
            books: List of trending books
            genre: Optional genre these books belong to
            
        Returns:
            True if the notification was sent successfully
        """
        if not books:
            return False
        
        genre_text = f" in {genre}" if genre else ""
        title = f"Trending Books{genre_text}"
        
        message = f"Check out these trending books{genre_text}:\n\n"
        
        for i, book in enumerate(books[:5], 1):
            message += f"{i}. {book.title} by {book.author}\n"
        
        if len(books) > 5:
            message += f"\n...and {len(books) - 5} more."
        
        return self.notify(message, title)