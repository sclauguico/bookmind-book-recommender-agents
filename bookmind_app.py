import gradio as gr
import json
import time
import threading
import queue
import logging
from typing import List, Dict, Any

from book_agent_framework import BookAgentFramework, Book, BookRecommendation, BookAnalysis, ReadingList

# Colors for styling
BG_COLOR = "#f9f7f5"
ACCENT_COLOR = "#7952b3"
TEXT_COLOR = "#333333"
CARD_BG = "#ffffff"

class BookMindApp:
    """Main application class for BookMind's Gradio UI"""
    
    def __init__(self):
        """Initialize the app with the BookMind agent framework"""
        self.agent_framework = BookAgentFramework()
        
        # Message queue for logging
        self.log_queue = queue.Queue()
        self.log_data = []
        
        # Set up custom logger
        self._setup_logging()
    
    def _setup_logging(self):
        """Set up custom logging to display in UI"""
        handler = logging.StreamHandler()
        handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        
        # Add custom handler
        logger = logging.getLogger()
        logger.addHandler(handler)
        
        # Add queue handler for UI
        class QueueHandler(logging.Handler):
            def __init__(self, log_queue):
                super().__init__()
                self.log_queue = log_queue

            def emit(self, record):
                self.log_queue.put(self.format(record))
        
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)
    
    def _format_book_card(self, book: Book) -> str:
        """Format a book as an HTML card"""
        cover_img = book.cover_url if book.cover_url else "/api/placeholder/200/300"
        
        genres_html = ""
        if book.genres:
            genres_html = "<div class='genres'>"
            for genre in book.genres[:3]:
                genres_html += f"<span class='genre-tag'>{genre}</span> "
            genres_html += "</div>"
        
        return f"""
        <div class="book-card">
            <div class="book-cover">
                <img src="{cover_img}" alt="{book.title} cover">
            </div>
            <div class="book-info">
                <h3>{book.title}</h3>
                <h4>by {book.author}</h4>
                {genres_html}
                <p>{book.description[:200]}{"..." if len(book.description) > 200 else ""}</p>
                {f'<a href="{book.goodreads_url}" target="_blank">View on Goodreads</a>' if book.goodreads_url else ''}
            </div>
        </div>
        """
    
    def _format_recommendation(self, recommendation: BookRecommendation) -> str:
        """Format a book recommendation as HTML"""
        book_card = self._format_book_card(recommendation.book)
        
        return f"""
        <div class="recommendation">
            {book_card}
            <div class="reasoning">
                <h4>Why we recommend this book:</h4>
                <p>{recommendation.reasoning}</p>
            </div>
        </div>
        """
    
    def _format_analysis(self, analysis: BookAnalysis) -> str:
        """Format a book analysis as HTML"""
        if not analysis:
            return "<p>No analysis available for this book.</p>"
        
        themes_html = ""
        if analysis.themes:
            themes_html = "<div class='themes'>"
            for theme in analysis.themes:
                themes_html += f"<span class='theme-tag'>{theme}</span> "
            themes_html += "</div>"
        
        similar_books_html = ""
        if analysis.similar_books:
            similar_books_html = "<h4>Similar Books You Might Enjoy:</h4><div class='similar-books'>"
            for book in analysis.similar_books[:3]:
                similar_books_html += self._format_book_card(book)
            similar_books_html += "</div>"
        
        hours = analysis.estimated_reading_time // 60
        minutes = analysis.estimated_reading_time % 60
        reading_time = f"{hours} hours, {minutes} minutes" if hours > 0 else f"{minutes} minutes"
        
        return f"""
        <div class="analysis">
            <div class="analysis-section">
                <h4>Sentiment: <span class="sentiment">{analysis.sentiment}</span></h4>
                <h4>Reading Complexity: <span class="complexity">{analysis.complexity:.1f}/1.0</span></h4>
                <h4>Estimated Reading Time: <span class="reading-time">{reading_time}</span></h4>
            </div>
            
            <div class="analysis-section">
                <h4>Main Themes:</h4>
                {themes_html}
            </div>
            
            {similar_books_html}
        </div>
        """
    
    def _format_reading_list(self, reading_list: ReadingList) -> Dict[str, str]:
        """Format reading lists as HTML"""
        to_read_html = "<div class='reading-list-books'>"
        for book in reading_list.to_read:
            to_read_html += self._format_book_card(book)
        to_read_html += "</div>"
        
        currently_reading_html = "<div class='reading-list-books'>"
        for book in reading_list.currently_reading:
            currently_reading_html += self._format_book_card(book)
        currently_reading_html += "</div>"
        
        completed_html = "<div class='reading-list-books'>"
        for book in reading_list.completed:
            completed_html += self._format_book_card(book)
        completed_html += "</div>"
        
        return {
            "to_read": to_read_html,
            "currently_reading": currently_reading_html,
            "completed": completed_html
        }
    
    def _html_for_logs(self, log_data: List[str]) -> str:
        """Format log data as HTML"""
        output = '<br>'.join(log_data[-15:])
        return f"""
        <div id="log-content" style="height: 200px; overflow-y: auto; border: 1px solid #ddd; background-color: #f5f5f5; padding: 10px; font-family: monospace;">
        {output}
        </div>
        <script>
            const logContent = document.getElementById('log-content');
            logContent.scrollTop = logContent.scrollHeight;
        </script>
        """
    
    def _css(self) -> str:
        """Return custom CSS for the UI"""
        return """
        /* General styling */
        body {
            font-family: 'Nunito', sans-serif;
            background-color: #f9f7f5;
            color: #333333;
        }
        
        /* Book cards */
        .book-card {
            display: flex;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 16px;
            overflow: hidden;
            transition: transform 0.2s ease;
        }
        
        .book-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        
        .book-cover {
            width: 100px;
            min-width: 100px;
            background-color: #f0f0f0;
        }
        
        .book-cover img {
            width: 100%;
            height: 150px;
            object-fit: cover;
        }
        
        .book-info {
            padding: 12px;
            flex-grow: 1;
        }
        
        .book-info h3 {
            margin: 0 0 4px 0;
            font-size: 18px;
            color: #333;
        }
        
        .book-info h4 {
            margin: 0 0 8px 0;
            font-size: 14px;
            color: #666;
            font-weight: normal;
        }
        
        .book-info p {
            margin: 8px 0;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .book-info a {
            color: #7952b3;
            text-decoration: none;
            font-size: 14px;
            display: inline-block;
            margin-top: 8px;
        }
        
        /* Genre and theme tags */
        .genres, .themes {
            margin: 8px 0;
        }
        
        .genre-tag, .theme-tag {
            display: inline-block;
            background-color: #f0f0f0;
            border-radius: 16px;
            padding: 4px 10px;
            margin-right: 6px;
            margin-bottom: 6px;
            font-size: 12px;
        }
        
        .genre-tag {
            background-color: #e6f0ff;
            color: #3366cc;
        }
        
        .theme-tag {
            background-color: #f0e6ff;
            color: #7952b3;
        }
        
        /* Recommendations */
        .recommendation {
            margin-bottom: 24px;
            border-bottom: 1px solid #eee;
            padding-bottom: 16px;
        }
        
        .reasoning {
            padding: 8px;
            background-color: #f9f7f5;
            border-radius: 8px;
            margin-top: 8px;
        }
        
        .reasoning h4 {
            margin: 0 0 8px 0;
            color: #7952b3;
        }
        
        /* Analysis */
        .analysis {
            background-color: white;
            border-radius: 8px;
            padding: 16px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .analysis-section {
            margin-bottom: 16px;
        }
        
        .analysis h4 {
            margin: 8px 0;
            color: #555;
        }
        
        .sentiment, .complexity, .reading-time {
            color: #7952b3;
            font-weight: bold;
        }
        
        /* Similar books */
        .similar-books {
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            margin-top: 8px;
        }
        
        .similar-books .book-card {
            flex: 1;
            min-width: 200px;
            max-width: 300px;
        }
        
        /* Reading lists */
        .reading-list-books {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }
        
        /* Tabs */
        .tab-selected {
            background-color: #7952b3 !important;
            color: white !important;
        }
        """
    
    def _process_recommendations(self, query: str, num_recommendations: int) -> str:
        """Process recommendation request in background thread"""
        try:
            recommendations = self.agent_framework.get_book_recommendation(
                query=query,
                num_recommendations=num_recommendations
            )
            
            # Format as HTML
            html = "<div class='recommendations-container'>"
            if recommendations:
                for recommendation in recommendations:
                    html += self._format_recommendation(recommendation)
            else:
                html += "<p>No recommendations found. Please try a different query.</p>"
            html += "</div>"
            
            return html
        except Exception as e:
            logging.error(f"Error in recommendation processing: {str(e)}")
            return f"<p>Error getting recommendations: {str(e)}</p>"
    
    def _process_book_analysis(self, title: str, author: str, description: str) -> str:
        """Process book analysis request in background thread"""
        try:
            # Create a book object
            book = Book(
                title=title,
                author=author,
                description=description,
                isbn="",
                genres=[]
            )
            
            # Get analysis
            analysis_result = self.agent_framework.planning_agent.analyze_book_request(book)
            book = analysis_result.get("book", book)
            analysis = analysis_result.get("analysis")
            
            # Format as HTML
            html = "<div class='analysis-container'>"
            html += self._format_book_card(book)
            html += self._format_analysis(analysis)
            html += "</div>"
            
            return html
        except Exception as e:
            logging.error(f"Error in book analysis: {str(e)}")
            return f"<p>Error analyzing book: {str(e)}</p>"
    
    def _process_genre_exploration(self, genre: str, limit: int) -> str:
        """Process genre exploration request in background thread"""
        try:
            # Explore the genre
            exploration_results = self.agent_framework.planning_agent.explore_genre(
                genre=genre,
                limit=limit
            )
            
            # Format as HTML
            html = f"<h3>Exploring {genre} Books</h3>"
            html += "<div class='genre-exploration'>"
            
            if exploration_results:
                for result in exploration_results:
                    book = result.get("book")
                    analysis = result.get("analysis")
                    
                    html += "<div class='exploration-item'>"
                    html += self._format_book_card(book)
                    html += self._format_analysis(analysis)
                    html += "</div>"
            else:
                html += f"<p>No books found for genre: {genre}</p>"
                
            html += "</div>"
            
            return html
        except Exception as e:
            logging.error(f"Error in genre exploration: {str(e)}")
            return f"<p>Error exploring genre: {str(e)}</p>"
    
    def _process_reading_list(self) -> Dict[str, str]:
        """Process reading list request"""
        try:
            reading_list = self.agent_framework.reading_list
            return self._format_reading_list(reading_list)
        except Exception as e:
            logging.error(f"Error loading reading list: {str(e)}")
            return {
                "to_read": f"<p>Error loading reading list: {str(e)}</p>",
                "currently_reading": "",
                "completed": ""
            }
    
    def _update_logs(self):
        """Update log display with new log messages"""
        try:
            # Get any new log messages
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_data.append(message)
                
            # Only keep the last 100 messages
            if len(self.log_data) > 100:
                self.log_data = self.log_data[-100:]
                
            # Format as HTML
            return self._html_for_logs(self.log_data)
        except Exception as e:
            return f"<p>Error updating logs: {str(e)}</p>"
    
    def add_to_reading_list(self, title: str, author: str, description: str, list_type: str = "to_read") -> Dict[str, str]:
        """Add a book to the reading list"""
        try:
            book = Book(
                title=title,
                author=author,
                description=description,
                isbn="",
                genres=[]
            )
            
            self.agent_framework.add_to_reading_list(book, list_type)
            return self._format_reading_list(self.agent_framework.reading_list)
        except Exception as e:
            logging.error(f"Error adding to reading list: {str(e)}")
            return self._format_reading_list(self.agent_framework.reading_list)
    
    def run(self):
        """Run the Gradio UI application"""
        # Initialize agent framework before running the UI
        self.agent_framework.init_agents_as_needed()
        
        with gr.Blocks(css=self._css(), title="BookMind", theme=gr.themes.Soft(primary_hue="purple")) as ui:
            with gr.Row():
                gr.Markdown('<div style="text-align: center; font-size: 28px; margin-bottom: 10px;"><strong>BookMind</strong> - Your Intelligent Book Discovery Assistant</div>')
            
            with gr.Row():
                gr.Markdown('<div style="text-align: center; font-size: 16px; margin-bottom: 20px;">Find your next favorite book with personalized recommendations and in-depth analysis</div>')
            
            # Create tabs for different features
            with gr.Tabs() as tabs:
                # Recommendations Tab
                with gr.Tab("Recommend Books", id="recommend-tab"):
                    with gr.Row():
                        with gr.Column(scale=3):
                            recommendation_input = gr.Textbox(
                                label="What kind of books are you looking for?",
                                placeholder="e.g., Science fiction books with strong female protagonists, or books similar to The Lord of the Rings",
                                lines=3
                            )
                            
                            with gr.Row():
                                num_recommendations = gr.Slider(
                                    minimum=1,
                                    maximum=10,
                                    value=5,
                                    step=1,
                                    label="Number of Recommendations"
                                )
                                recommend_button = gr.Button("Get Recommendations", variant="primary")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### How to get good recommendations:")
                            gr.Markdown("""
                            * Be specific about themes, genres, or styles you enjoy
                            * Mention books or authors you already like
                            * Include preferences about length, complexity, or mood
                            * Specify if you're looking for newer or classic books
                            """)
                    
                    recommendation_output = gr.HTML(
                        value="<p>Your personalized book recommendations will appear here.</p>",
                        label="Recommendations"
                    )
                
                # Book Analysis Tab
                with gr.Tab("Analyze a Book", id="analyze-tab"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            book_title = gr.Textbox(
                                label="Book Title",
                                placeholder="Enter book title"
                            )
                            book_author = gr.Textbox(
                                label="Author",
                                placeholder="Enter author name"
                            )
                            book_description = gr.Textbox(
                                label="Book Description",
                                placeholder="Enter a description of the book",
                                lines=5
                            )
                            analyze_button = gr.Button("Analyze Book", variant="primary")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### What book analysis provides:")
                            gr.Markdown("""
                            * Emotional sentiment of the book
                            * Main themes and topics
                            * Reading complexity score
                            * Estimated reading time
                            * Similar books you might enjoy
                            """)
                    
                    analysis_output = gr.HTML(
                        value="<p>Book analysis will appear here.</p>",
                        label="Analysis"
                    )
                
                # Genre Exploration Tab
                with gr.Tab("Explore Genres", id="explore-tab"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            genre_dropdown = gr.Dropdown(
                                choices=[
                                    "fantasy", "science_fiction", "mystery", 
                                    "romance", "historical", "biography", 
                                    "self_help", "horror"
                                ],
                                label="Select Genre",
                                value="fantasy"
                            )
                            limit_slider = gr.Slider(
                                minimum=3,
                                maximum=10,
                                value=5,
                                step=1,
                                label="Number of Books"
                            )
                            explore_button = gr.Button("Explore Genre", variant="primary")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### Discover trending books in your favorite genres")
                            gr.Markdown("""
                            Genre exploration helps you:
                            * Find popular books in specific genres
                            * Discover new authors and series
                            * Stay updated with trending titles
                            * Get recommendations similar to top books
                            """)
                    
                    exploration_output = gr.HTML(
                        value="<p>Genre exploration results will appear here.</p>",
                        label="Genre Exploration"
                    )
                
                # Reading List Tab
                with gr.Tab("Reading Lists", id="reading-list-tab"):
                    with gr.Row():
                        with gr.Column(scale=2):
                            with gr.Row():
                                reading_list_title = gr.Textbox(
                                    label="Book Title",
                                    placeholder="Enter book title to add to your reading list"
                                )
                                reading_list_author = gr.Textbox(
                                    label="Author",
                                    placeholder="Enter author name"
                                )
                            reading_list_description = gr.Textbox(
                                label="Description (optional)",
                                placeholder="Enter a brief description",
                                lines=2
                            )
                            with gr.Row():
                                list_type = gr.Radio(
                                    choices=["to_read", "currently_reading", "completed"],
                                    value="to_read",
                                    label="List Type"
                                )
                                add_to_list_button = gr.Button("Add to Reading List", variant="primary")
                        
                        with gr.Column(scale=1):
                            gr.Markdown("### Track your reading journey")
                            gr.Markdown("""
                            Organize your books into:
                            * **To Read**: Books you plan to read
                            * **Currently Reading**: Books you're reading now
                            * **Completed**: Books you've finished
                            
                            Add books manually or from recommendations.
                            """)
                    
                    with gr.Tabs():
                        with gr.Tab("To Read"):
                            to_read_output = gr.HTML(value="<p>Loading to-read list...</p>")
                        with gr.Tab("Currently Reading"):
                            currently_reading_output = gr.HTML(value="<p>Loading currently reading list...</p>")
                        with gr.Tab("Completed"):
                            completed_output = gr.HTML(value="<p>Loading completed list...</p>")
                
                # System Logs Tab (for debugging)
                with gr.Tab("System Logs", id="logs-tab"):
                    logs_output = gr.HTML(value="<p>System logs will appear here.</p>")
                    refresh_logs_button = gr.Button("Refresh Logs")
            
            # Set up event handlers
            recommend_button.click(
                fn=self._process_recommendations,
                inputs=[recommendation_input, num_recommendations],
                outputs=recommendation_output
            )
            
            analyze_button.click(
                fn=self._process_book_analysis,
                inputs=[book_title, book_author, book_description],
                outputs=analysis_output
            )
            
            explore_button.click(
                fn=self._process_genre_exploration,
                inputs=[genre_dropdown, limit_slider],
                outputs=exploration_output
            )
            
            add_to_list_button.click(
                fn=self.add_to_reading_list,
                inputs=[reading_list_title, reading_list_author, reading_list_description, list_type],
                outputs=[to_read_output, currently_reading_output, completed_output]
            )
            
            refresh_logs_button.click(
                fn=self._update_logs,
                inputs=[],
                outputs=logs_output
            )
            
            # Load initial data
            ui.load(
                fn=self._process_reading_list,
                inputs=[],
                outputs=[to_read_output, currently_reading_output, completed_output]
            )
            
            ui.load(
                fn=self._update_logs,
                inputs=[],
                outputs=logs_output
            )
            
            # Setup periodic refresh for logs
            logs_refresh = gr.Timer(10, ui=False)
            logs_refresh.tick(
                fn=self._update_logs,
                inputs=[],
                outputs=logs_output
            )
        
        # Launch the app
        ui.launch(share=False, inbrowser=True)

if __name__ == "__main__":
    BookMindApp().run()