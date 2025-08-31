# voice-shopping-app

This project is a voice-based shopping list manager that allows users to add, remove, and manage their shopping list items using voice commands. It's designed to be a smart assistant with features like multilingual support and smart suggestions.

1. Features:

- Voice Input: Add items to your shopping list using natural language voice commands.

- Multilingual Support: Supports voice commands in English and Hindi.

- Shopping List Management: Easily add, remove, or modify items on your list.

- Quantity Management: Specify quantities for items using your voice.

- Smart Suggestions: Get recommendations based on your shopping history and seasonal availability.

- Product Search: Find items from a catalog with filters for price and brand.

- Substitutes: Get suggestions for alternative products.

2. Technical Approach:

    The application is built as a single-file Flask web server that handles both the backend logic and serves the frontend user interface.

- Backend (Flask & Python)
  The backend is responsible for all the core logic, including natural language understanding, database management, and business logic for the shopping list.

- Database:

1. A local SQLite database (shopping.db) is used for data persistence.

2. The database is initialized with three main tables:

3. shopping_list: Stores the current items the user wants to buy.

4. history: Tracks items that have been added previously to provide recommendations.

5. catalog: A predefined list of products with details like brand, price, and availability for the search functionality.

4. Natural Language Processing (NLP):

- The core of the voice interaction is the parse_command function, which acts as a simple NLP engine.

- Language Detection: It uses the langdetect library to identify if the command is in English or Hindi.

- Intent Recognition: The function determines the user's intent (add, remove, modify, search) by matching keywords (e.g., "add", "buy", "hatao", "dhundo") in both English and Hindi.

- Entity Extraction: It uses regular expressions and keyword filtering to extract key entities from the command string:

- Item Name: Identifies the product by filtering out action words, numbers, and other noise. It also normalizes items (e.g., "apples" to "apple") and translates Hindi names to English (e.g.,   "seb" to "apple").

- Quantity: Recognizes both numeric digits (2) and number words (two, do).

- Price Filters: Parses phrases like "under $5" or "between 50 and 100".

- Brand: Extracts brand names from phrases like "by Amul".

5. API Endpoints:

  The application exposes a set of RESTful API endpoints that the frontend interacts with:

- POST /api/command: The main endpoint that receives a voice/text command, parses it, executes the corresponding action (e.g., Notes, catalog_search), and returns the updated list state.

- GET /api/list: Fetches the current shopping list and suggestions.

- POST /api/list: Allows for non-voice modifications to the list (e.g., clicking a button to add/remove an item).

- GET /api/search: Provides a way to query the product catalog.

- GET /api/suggestions: Retrieves smart suggestions.

6. Smart Features:

- History Recommendations: Suggests items that were added to the list more than two weeks ago.

- Seasonal Recommendations: Suggests items based on the current month from a predefined dictionary.

- Substitutes: Offers alternatives for certain items (e.g., suggests "almond milk" if the user adds "milk").

7. Frontend (HTML, CSS, JavaScript):
   
   The frontend is a single, self-contained INDEX_HTML string within the Python script, providing a clean and reactive user interface.

9. Voice Recognition:

- It uses the browser's built-in Web Speech API (SpeechRecognition) to capture the user's voice.

- The interface allows the user to select the language (English-US, English-IN, Hindi-IN) to improve recognition accuracy.

- When the user speaks, the transcribed text is sent to the backend's /api/command endpoint.

9. Dynamic UI Rendering:

- The entire UI is rendered using vanilla JavaScript.

- The shopping list, suggestions, and search results are dynamically updated by fetching data from the backend APIs and manipulating the DOM.

- This approach avoids page reloads, creating a smooth, single-page application (SPA) experience.

- It provides visual feedback, such as a loading spinner when a command is being processed.

10. User Interaction:

- Users can interact via voice (Start/Stop buttons) or by typing commands into a text input field.

- The shopping list can also be managed directly by clicking buttons to increase/decrease quantity or remove items, which provides a fallback for non-voice interaction.

11. Getting Started:

  These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

- Prerequisites
  Python 3.x

- Installation
  Clone the repository:

  git clone [https://github.com/your-username/voice-command-shopping-assistant.git](https://github.com/your-username/voice-command-shopping-assistant.git)
  cd voice-command-shopping-assistant

- Create and activate a virtual environment:

  For Windows:
  
  python -m venv venv
  .\venv\Scripts\activate
  
  For macOS/Linux:
  
  python3 -m venv venv
  source venv/bin/activate

- Install the required packages:

  pip install flask flask-cors langdetect

- Run the application:

  python app.py
  
  The application will be running on http://127.0.0.1:5000.

12. Technologies Used:

- Python: Core programming language.

- Flask: Web framework for the backend server.

- Flask-CORS: For handling Cross-Origin Resource Sharing.

- langdetect: To detect the language of the voice command.

- SQLite: For the database.

- Vanilla JavaScript: For all frontend logic.

- Web Speech API: For voice recognition in the browser.
