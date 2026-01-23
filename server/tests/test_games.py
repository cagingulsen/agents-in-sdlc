import unittest
import json
from typing import Dict, Any
from flask import Flask, Response
from models import Game, Publisher, Category, db
from routes.games import games_bp

class TestGamesRoutes(unittest.TestCase):
    # Test data as complete objects
    TEST_DATA: Dict[str, Any] = {
        "publishers": [
            {"name": "DevGames Inc"},
            {"name": "Scrum Masters"}
        ],
        "categories": [
            {"name": "Strategy"},
            {"name": "Card Game"}
        ],
        "games": [
            {
                "title": "Pipeline Panic",
                "description": "Build your DevOps pipeline before chaos ensues",
                "publisher_index": 0,
                "category_index": 0,
                "star_rating": 4.5
            },
            {
                "title": "Agile Adventures",
                "description": "Navigate your team through sprints and releases",
                "publisher_index": 1,
                "category_index": 1,
                "star_rating": 4.2
            }
        ]
    }
    
    # API paths
    GAMES_API_PATH: str = '/api/games'

    def setUp(self) -> None:
        """Set up test database and seed data"""
        # Create a fresh Flask app for testing
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        # Register the games blueprint
        self.app.register_blueprint(games_bp)
        
        # Initialize the test client
        self.client = self.app.test_client()
        
        # Initialize in-memory database for testing
        db.init_app(self.app)
        
        # Create tables and seed data
        with self.app.app_context():
            db.create_all()
            self._seed_test_data()

    def tearDown(self) -> None:
        """Clean up test database and ensure proper connection closure"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def _seed_test_data(self) -> None:
        """Helper method to seed test data"""
        # Create test publishers
        publishers = [
            Publisher(**publisher_data) for publisher_data in self.TEST_DATA["publishers"]
        ]
        db.session.add_all(publishers)
        
        # Create test categories
        categories = [
            Category(**category_data) for category_data in self.TEST_DATA["categories"]
        ]
        db.session.add_all(categories)
        
        # Commit to get IDs
        db.session.commit()
        
        # Create test games
        games = []
        for game_data in self.TEST_DATA["games"]:
            game_dict = game_data.copy()
            publisher_index = game_dict.pop("publisher_index")
            category_index = game_dict.pop("category_index")
            
            games.append(Game(
                **game_dict,
                publisher=publishers[publisher_index],
                category=categories[category_index]
            ))
            
        db.session.add_all(games)
        db.session.commit()

    def _get_response_data(self, response: Response) -> Any:
        """Helper method to parse response data"""
        return json.loads(response.data)

    def test_get_games_success(self) -> None:
        """Test successful retrieval of multiple games"""
        # Act
        response = self.client.get(self.GAMES_API_PATH)
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(data), len(self.TEST_DATA["games"]))
        
        # Verify all games using loop instead of manual testing
        for i, game_data in enumerate(data):
            test_game = self.TEST_DATA["games"][i]
            test_publisher = self.TEST_DATA["publishers"][test_game["publisher_index"]]
            test_category = self.TEST_DATA["categories"][test_game["category_index"]]
            
            self.assertEqual(game_data['title'], test_game["title"])
            self.assertEqual(game_data['publisher']['name'], test_publisher["name"])
            self.assertEqual(game_data['category']['name'], test_category["name"])
            self.assertEqual(game_data['starRating'], test_game["star_rating"])

    def test_get_games_structure(self) -> None:
        """Test the response structure for games"""
        # Act
        response = self.client.get(self.GAMES_API_PATH)
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), len(self.TEST_DATA["games"]))
        
        required_fields = ['id', 'title', 'description', 'publisher', 'category', 'starRating']
        for field in required_fields:
            self.assertIn(field, data[0])

    def test_get_game_by_id_success(self) -> None:
        """Test successful retrieval of a single game by ID"""
        # Get the first game's ID from the list endpoint
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        # Act
        response = self.client.get(f'{self.GAMES_API_PATH}/{game_id}')
        data = self._get_response_data(response)
        
        # Assert
        first_game = self.TEST_DATA["games"][0]
        first_publisher = self.TEST_DATA["publishers"][first_game["publisher_index"]]
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], first_game["title"])
        self.assertEqual(data['publisher']['name'], first_publisher["name"])
        
    def test_get_game_by_id_not_found(self) -> None:
        """Test retrieval of a non-existent game by ID"""
        # Act
        response = self.client.get(f'{self.GAMES_API_PATH}/999')
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], "Game not found")

    def test_get_games_empty_database(self) -> None:
        """Test retrieval of games when database is empty"""
        # Clear all games from the database
        with self.app.app_context():
            db.session.query(Game).delete()
            db.session.commit()
        
        # Act
        response = self.client.get(self.GAMES_API_PATH)
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0)

    def test_get_game_by_invalid_id_type(self) -> None:
        """Test retrieval of a game with invalid ID type"""
        # Act
        response = self.client.get(f'{self.GAMES_API_PATH}/invalid-id')
        
        # Assert
        # Flask should return 404 for routes that don't match the <int:id> pattern
        self.assertEqual(response.status_code, 404)

    def test_create_game_success(self) -> None:
        """Test successful creation of a new game"""
        # Arrange
        with self.app.app_context():
            category = db.session.query(Category).first()
            publisher = db.session.query(Publisher).first()
        
        new_game_data = {
            'title': 'Bug Bash',
            'description': 'Race to fix bugs before they reach production',
            'category_id': category.id,
            'publisher_id': publisher.id,
            'star_rating': 4.7
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            json=new_game_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 201)
        self.assertEqual(data['title'], new_game_data['title'])
        self.assertEqual(data['description'], new_game_data['description'])
        self.assertEqual(data['starRating'], new_game_data['star_rating'])
        self.assertIn('id', data)

    def test_create_game_missing_fields(self) -> None:
        """Test creation fails with missing required fields"""
        # Arrange
        incomplete_data = {
            'title': 'Incomplete Game'
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            json=incomplete_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertIn('Missing required fields', data['error'])

    def test_create_game_invalid_category(self) -> None:
        """Test creation fails with non-existent category"""
        # Arrange
        with self.app.app_context():
            publisher = db.session.query(Publisher).first()
        
        invalid_data = {
            'title': 'Test Game',
            'description': 'Test description',
            'category_id': 999,
            'publisher_id': publisher.id,
            'star_rating': 4.0
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            json=invalid_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Category not found')

    def test_create_game_invalid_publisher(self) -> None:
        """Test creation fails with non-existent publisher"""
        # Arrange
        with self.app.app_context():
            category = db.session.query(Category).first()
        
        invalid_data = {
            'title': 'Test Game',
            'description': 'Test description',
            'category_id': category.id,
            'publisher_id': 999,
            'star_rating': 4.0
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            json=invalid_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Publisher not found')

    def test_create_game_validation_error(self) -> None:
        """Test creation fails with invalid title (too short)"""
        # Arrange
        with self.app.app_context():
            category = db.session.query(Category).first()
            publisher = db.session.query(Publisher).first()
        
        invalid_data = {
            'title': 'A',  # Too short (minimum is 2 characters)
            'description': 'Test description with enough characters',
            'category_id': category.id,
            'publisher_id': publisher.id
        }
        
        # Act
        response = self.client.post(
            self.GAMES_API_PATH,
            json=invalid_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)

    def test_create_game_no_json(self) -> None:
        """Test creation fails without JSON body"""
        # Act
        response = self.client.post(self.GAMES_API_PATH)
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Request body must be JSON')

    def test_update_game_success(self) -> None:
        """Test successful update of an existing game"""
        # Arrange - get the first game
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        update_data = {
            'title': 'Updated Title',
            'star_rating': 5.0
        }
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/{game_id}',
            json=update_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['title'], update_data['title'])
        self.assertEqual(data['starRating'], update_data['star_rating'])

    def test_update_game_not_found(self) -> None:
        """Test update fails for non-existent game"""
        # Arrange
        update_data = {
            'title': 'Updated Title'
        }
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/999',
            json=update_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], 'Game not found')

    def test_update_game_invalid_category(self) -> None:
        """Test update fails with non-existent category"""
        # Arrange - get the first game
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        update_data = {
            'category_id': 999
        }
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/{game_id}',
            json=update_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Category not found')

    def test_update_game_no_json(self) -> None:
        """Test update fails without JSON body"""
        # Arrange - get the first game
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        # Act
        response = self.client.put(f'{self.GAMES_API_PATH}/{game_id}')
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['error'], 'Request body must be JSON')

    def test_update_game_validation_error(self) -> None:
        """Test update fails with invalid data (title too short)"""
        # Arrange - get the first game
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        
        update_data = {
            'title': 'A'  # Too short
        }
        
        # Act
        response = self.client.put(
            f'{self.GAMES_API_PATH}/{game_id}',
            json=update_data,
            content_type='application/json'
        )
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)

    def test_delete_game_success(self) -> None:
        """Test successful deletion of a game"""
        # Arrange - get the first game
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        game_id = games[0]['id']
        initial_count = len(games)
        
        # Act
        response = self.client.delete(f'{self.GAMES_API_PATH}/{game_id}')
        
        # Assert
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data, b'')  # Should be empty for 204
        
        # Verify game is deleted
        response = self.client.get(self.GAMES_API_PATH)
        games = self._get_response_data(response)
        self.assertEqual(len(games), initial_count - 1)

    def test_delete_game_not_found(self) -> None:
        """Test deletion fails for non-existent game"""
        # Act
        response = self.client.delete(f'{self.GAMES_API_PATH}/999')
        data = self._get_response_data(response)
        
        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(data['error'], 'Game not found')

if __name__ == '__main__':
    unittest.main()