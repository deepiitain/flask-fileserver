from flask import Flask
from flask_cors import CORS
from routes import api_blueprint

def create_app():
    app = Flask(__name__)

    # Allow CORS on localhost only (any port)
    CORS(
        app, 
        supports_credentials=True, 
        origins=["http://localhost:*"], 
        allow_headers=["Authorization"]
    )
    
    # Register the blueprint
    app.register_blueprint(api_blueprint)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
