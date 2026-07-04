"""
Flask Server.
Initializes database and coordinates middleware and router configuration.
"""

from flask import Flask, send_from_directory, jsonify
import os
from api.routes import api_blueprint
from routers.semantic_router import semantic_blueprint
from db.init_db import init_database
from core.logger import logger

app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates"
)

# Configure CORS for frontend access
@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Headers", "*")
    response.headers.add("Access-Control-Allow-Methods", "*")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# Register API routes (Blueprints)
app.register_blueprint(api_blueprint, url_prefix="/api")
app.register_blueprint(semantic_blueprint, url_prefix="/api/semantic")

# Serve HTML templates directly
TEMPLATES_DIR = "templates"

@app.route("/")
@app.route("/index.html")
def read_index():
    return send_from_directory(TEMPLATES_DIR, "index.html")

@app.route("/dashboard.html")
def read_dashboard():
    return send_from_directory(TEMPLATES_DIR, "dashboard.html")

@app.route("/chat.html")
def read_chat():
    return send_from_directory(TEMPLATES_DIR, "chat.html")

@app.route("/faculty.html")
def read_faculty():
    return send_from_directory(TEMPLATES_DIR, "faculty.html")

@app.route("/research_gap.html")
def read_research_gap():
    return send_from_directory(TEMPLATES_DIR, "research_gap.html")

@app.route("/collaboration.html")
def read_collaboration():
    return send_from_directory(TEMPLATES_DIR, "collaboration.html")

@app.route("/citation_graph.html")
def read_citation_graph():
    return send_from_directory(TEMPLATES_DIR, "citation_graph.html")

@app.route("/analytics.html")
def read_analytics():
    return send_from_directory(TEMPLATES_DIR, "analytics.html")

@app.route("/profile.html")
def read_profile():
    return send_from_directory(TEMPLATES_DIR, "profile.html")

@app.route("/<path:catchall>")
def read_catchall(catchall):
    path_404 = os.path.join(TEMPLATES_DIR, "404.html")
    if os.path.exists(path_404):
        return send_from_directory(TEMPLATES_DIR, "404.html"), 404
    return jsonify({"error": "Page not found"}), 404

# Export handler for Vercel Serverless Function compatibility
handler = app

# Database initialization during application startup
with app.app_context():
    try:
        init_database()
    except Exception as e:
        logger.error(f"Database initialization failed during startup: {e}")
        # In a local development environment, raise the error so the developer is aware.
        # On Vercel, catch it so the server can still run and serve static content.
        if not os.getenv("VERCEL"):
            raise

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
