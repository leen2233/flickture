# Flickture Backend

A powerful Django-based backend service for the Flickture movie platform, providing a robust API for movie discovery, user management, and social features.

## 🚀 Current Features

### Movie Management

- **Movie Data Integration**
  - Integration with TMDB API for comprehensive movie data
  - Automatic movie data synchronization and updates
  - Support for movie details, cast, genres, and collections
  - High-quality movie posters and backdrop images

### User Features

- **Authentication System**
  - Token-based authentication
  - User registration and login
  - Profile management with customizable avatars and banners
  - Social features including following/followers system

### Movie Discovery

- **Advanced Movie Management**
  - Detailed movie information storage
  - Cast and crew information
  - Genre categorization
  - Movie collections support
  - Popularity and rating tracking

### User Interaction

- **Watchlist System**

  - Multiple watch statuses (Watchlist, Watching, Watched)
  - Personal watchlist management
  - Watch progress tracking

- **Social Features**
  - Movie comments and reviews
  - Rating system (1-5 stars)
  - Comment likes and responses
  - User following system

### Technical Features

- **API Documentation**

  - Swagger/OpenAPI integration
  - Interactive API documentation
  - Detailed endpoint descriptions

- **Media Management**
  - User avatar and banner image handling
  - Secure media file storage
  - Optimized image serving

## 🛠️ Technical Stack

- **Framework**: Django 4.2
- **API**: Django REST Framework
- **Database**: SQLite (Development) / PostgreSQL (Production)
- **Authentication**: Token-based authentication
- **Documentation**: drf-yasg (Swagger/OpenAPI)
- **Image Processing**: Pillow
- **External APIs**: TMDB API Integration

## 🎯 Planned Features

### Enhanced Movie Features

- **Advanced Movie Statistics**

  - Watch time analytics
  - Genre preferences
  - Viewing history trends
  - Personalized recommendations

- **Extended Movie Information**
  - Crew details
  - Production companies
  - Filming locations
  - Budget and revenue data

### Social Enhancements

- **Advanced Social Features**
  - User activity feed
  - Movie discussions/forums
  - User groups and communities
  - Shared watchlists

### Content Management

- **Content Moderation**
  - Comment moderation system
  - User-generated content filtering
  - Report handling
  - Content guidelines enforcement

### API Improvements

- **API Enhancements**
  - GraphQL support
  - Real-time updates
  - Enhanced caching
  - Rate limiting
  - Webhook support

## 🚀 Getting Started

1. **Prerequisites**

   - Python 3.8+
   - pip
   - virtualenv (recommended)

2. **Environment Setup**

   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Set up environment variables
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Database Setup**

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. **Running the Server**

   ```bash
   python manage.py runserver
   ```

5. **API Documentation**
   - Swagger UI: http://localhost:8000/swagger/
   - ReDoc: http://localhost:8000/redoc/

## 📝 API Documentation

The API documentation is available through Swagger UI and ReDoc interfaces when the server is running. Key endpoints include:

- **Authentication**

  - `/api/v1/auth/register/`: User registration
  - `/api/v1/auth/login/`: User login
  - `/api/v1/auth/profile/`: User profile management

- **Movies**

  - `/api/v1/movies/`: Movie listing and search
  - `/api/v1/movies/{id}/`: Detailed movie information
  - `/api/v1/movies/{id}/cast/`: Movie cast information

- **User Features**
  - `/api/v1/watchlist/`: Watchlist management
  - `/api/v1/favorites/`: Favorites management
  - `/api/v1/comments/`: Movie comments and reviews

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- TMDB API for movie data
- Django and Django REST Framework communities
- All contributors to the project
