from flask import jsonify, Response, Blueprint, request
from models import db, Game, Publisher, Category
from sqlalchemy.orm import Query
from sqlalchemy.exc import IntegrityError

# Create a Blueprint for games routes
games_bp = Blueprint('games', __name__)

def get_games_base_query() -> Query:
    return db.session.query(Game).join(
        Publisher, 
        Game.publisher_id == Publisher.id, 
        isouter=True
    ).join(
        Category, 
        Game.category_id == Category.id, 
        isouter=True
    )

@games_bp.route('/api/games', methods=['GET'])
def get_games() -> Response:
    # Use the base query for all games
    games_query = get_games_base_query().all()
    
    # Convert the results using the model's to_dict method
    games_list = [game.to_dict() for game in games_query]
    
    return jsonify(games_list)

@games_bp.route('/api/games/<int:id>', methods=['GET'])
def get_game(id: int) -> tuple[Response, int] | Response:
    # Use the base query and add filter for specific game
    game_query = get_games_base_query().filter(Game.id == id).first()
    
    # Return 404 if game not found
    if not game_query: 
        return jsonify({"error": "Game not found"}), 404
    
    # Convert the result using the model's to_dict method
    game = game_query.to_dict()
    
    return jsonify(game)

@games_bp.route('/api/games', methods=['POST'])
def create_game() -> tuple[Response, int]:
    # Get JSON data from request
    data = request.get_json(silent=True)
    
    # Validate required fields
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    required_fields = ['title', 'description', 'category_id', 'publisher_id']
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    
    # Validate that category and publisher exist
    category = db.session.query(Category).filter(Category.id == data['category_id']).first()
    if not category:
        return jsonify({"error": "Category not found"}), 400
    
    publisher = db.session.query(Publisher).filter(Publisher.id == data['publisher_id']).first()
    if not publisher:
        return jsonify({"error": "Publisher not found"}), 400
    
    try:
        # Create new game
        game = Game(
            title=data['title'],
            description=data['description'],
            category_id=data['category_id'],
            publisher_id=data['publisher_id'],
            star_rating=data.get('star_rating')
        )
        
        db.session.add(game)
        db.session.commit()
        
        # Return created game with 201 status
        return jsonify(game.to_dict()), 201
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error"}), 400

@games_bp.route('/api/games/<int:id>', methods=['PUT'])
def update_game(id: int) -> tuple[Response, int] | Response:
    # Find the game
    game = db.session.query(Game).filter(Game.id == id).first()
    
    if not game:
        return jsonify({"error": "Game not found"}), 404
    
    # Get JSON data from request
    data = request.get_json(silent=True)
    
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    
    # Validate category if provided
    if 'category_id' in data:
        category = db.session.query(Category).filter(Category.id == data['category_id']).first()
        if not category:
            return jsonify({"error": "Category not found"}), 400
    
    # Validate publisher if provided
    if 'publisher_id' in data:
        publisher = db.session.query(Publisher).filter(Publisher.id == data['publisher_id']).first()
        if not publisher:
            return jsonify({"error": "Publisher not found"}), 400
    
    try:
        # Update fields if provided
        if 'title' in data:
            game.title = data['title']
        if 'description' in data:
            game.description = data['description']
        if 'category_id' in data:
            game.category_id = data['category_id']
        if 'publisher_id' in data:
            game.publisher_id = data['publisher_id']
        if 'star_rating' in data:
            game.star_rating = data['star_rating']
        
        db.session.commit()
        
        # Return updated game
        return jsonify(game.to_dict()), 200
    except ValueError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 400
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error"}), 400

@games_bp.route('/api/games/<int:id>', methods=['DELETE'])
def delete_game(id: int) -> tuple[Response, int]:
    # Find the game
    game = db.session.query(Game).filter(Game.id == id).first()
    
    if not game:
        return jsonify({"error": "Game not found"}), 404
    
    try:
        db.session.delete(game)
        db.session.commit()
        
        # Return 204 No Content on successful deletion
        return jsonify({}), 204
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error"}), 400
