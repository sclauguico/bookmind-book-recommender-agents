#!/usr/bin/env python3
import time
import modal
from datetime import datetime

def main():
    """
    Keep the Modal deployment warm by sending periodic requests.
    This prevents cold starts when users request recommendations.
    """
    print("Starting keep-warm process for BookMind's recommendation model...")
    print("Press Ctrl+C to stop")
    
    try:
        # Look up the BookRecommender class from Modal
        BookRecommender = modal.Cls.lookup("book-recommender", "BookRecommender")
        recommender = BookRecommender()
        
        while True:
            try:
                # Call the wake_up method to keep the model loaded
                reply = recommender.wake_up.remote()
                print(f"{datetime.now()}: {reply}")
                
                # Wait for 30 seconds before the next ping
                time.sleep(30)
            except Exception as e:
                print(f"Error pinging Modal: {str(e)}")
                print("Will try again in 60 seconds...")
                time.sleep(60)
    
    except KeyboardInterrupt:
        print("\nStopping keep-warm process")
    except Exception as e:
        print(f"Failed to connect to Modal: {str(e)}")
        print("Make sure you've deployed the model with 'modal deploy book_recommender.py'")

if __name__ == "__main__":
    main()