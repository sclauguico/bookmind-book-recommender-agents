# BookMind: Book Recommender with AI Agents

## Overview

BookMind is an intelligent book recommendation and analysis system that helps users discover new books, analyze content, and manage their reading journey. The system is built using a multi-agent architecture where specialized AI agents collaborate to provide comprehensive book insights.

## Key Components

### 1. Multi-Agent Framework
The system is organized around a framework of specialized agents that work together:

- **Recommendation Agent**: Uses a fine-tuned LLM deployed on Modal to generate personalized book recommendations based on user queries.
- **Semantic Search Agent**: Maintains a vector database of books and uses embedding similarity to find books with related themes or content.
- **Analysis Agent**: Performs sentiment analysis, theme extraction, and reading time estimation for books.
- **Community Agent**: Scrapes and processes data from Goodreads and other sources to identify trending books.
- **Planning Agent**: Coordinates the other agents to fulfill user requests efficiently.
- **Notification Agent**: Sends push notifications about new recommendations or interesting book discoveries.

### 2. Vector Database
BookMind uses a Chroma vector database to store book embeddings for semantic search. The system:
- Generates embeddings for book descriptions using Sentence Transformers
- Indexes books by their content, themes, and metadata
- Enables similarity search to find related books
- Persists book information for rapid retrieval

### 3. Modal Deployment
The recommendation model is deployed on Modal.com for:
- Cost-effective serverless inference
- GPU acceleration for the recommendation model
- Easy scaling to handle multiple users
- Remote API access to the fine-tuned LLM

### 4. Gradio UI
The user interface is built with Gradio and provides:
- Multiple tabs for different features (recommendations, analysis, exploration)
- Input forms for user queries and book information
- Responsive design with custom CSS
- Real-time system logs for transparency

### 5. Reading List Management
Users can organize their reading journey by:
- Adding books to "To Read," "Currently Reading," or "Completed" lists
- Adding books from recommendations or manually
- Tracking their reading progress
- Getting insights about their reading preferences

## Technical Innovations

1. **Agent Collaboration**: The system demonstrates how multiple specialized AI agents can work together to solve complex tasks.

2. **RAG Implementation**: BookMind implements Retrieval-Augmented Generation by using vector similarity to enhance LLM recommendations.

3. **Hybrid Architecture**: The system combines remote API calls with local vector search for efficient operation.

4. **Reading Analysis**: The system provides unique insights about books, including estimated reading time based on complexity.

5. **Memory Persistence**: BookMind maintains memory of past recommendations and analyses to improve future interactions.

## Use Cases

1. **Personalized Discovery**: Find books that match specific interests, themes, or preferences.

2. **Pre-Reading Analysis**: Get insights about a book's content, themes, and time commitment before starting.

3. **Similar Book Finding**: Discover books similar to ones you've enjoyed.

4. **Genre Exploration**: Explore trending books within specific genres.

5. **Reading Organization**: Maintain organized reading lists and track reading progress.

## Deployment Considerations

- **API Keys**: Requires OpenAI API key for analysis and Modal for recommendation deployment.
- **Vector Database**: Needs local storage for the Chroma vector database.
- **Performance**: Recommendation and analysis operations typically take 5-15 seconds to complete.
- **Scaling**: The Modal deployment can scale to handle multiple users, while the local components would need containerization for full scaling.

## Future Enhancements

1. **User Profiles**: Add support for multiple user profiles with personalized recommendations.
2. **Reading Progress Tracking**: Implement page/chapter tracking for currently reading books.
3. **Social Features**: Allow sharing of recommendations and reading lists.
4. **Local LLM Option**: Add support for running smaller LLMs locally for users without API access.
5. **Mobile Application**: Develop a companion mobile app for on-the-go access.