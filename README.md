# FoodShare - Smart Food Donation & Marketplace Platform

A real-time food waste management web application built with Flask, HTML, CSS, JavaScript, and SQLite.

## Features

- User roles: Food Donors and Volunteers/Buyers
- Authentication system with hashed passwords
- Donors can post food with details and images
- Volunteers can browse, filter, and book food
- Mock payment system for paid items
- Order and donation history
- Profile management

## Setup Instructions

1. **Clone or Download the Project**
   - Ensure all files are in the project directory.

2. **Install Python**
   - Make sure Python 3.7+ is installed.

3. **Create Virtual Environment (Recommended)**
   ```
   python -m venv venv
   venv\Scripts\activate  # On Windows
   ```

4. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```

5. **Run the Application**
   ```
   python app.py
   ```

6. **Access the App**
   - Open your browser and go to `http://127.0.0.1:5000/`

## File Structure

- `app.py`: Main Flask application
- `templates/`: HTML templates
- `static/css/`: Stylesheets
- `static/js/`: JavaScript files (if any)
- `static/uploads/`: Uploaded images
- `database.db`: SQLite database (created automatically)
- `requirements.txt`: Python dependencies

## Usage

- Start at the landing page, choose role, signup/login.
- Donors: Add food, view posts, check history.
- Volunteers: Browse food, filter by free/paid/location, book and pay if needed.

## Notes

- Images are stored in `static/uploads/`.
- Database is initialized on first run.
- Change `app.secret_key` in production.
- For real deployment, use a proper server like Gunicorn.