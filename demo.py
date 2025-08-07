from flask import Flask, jsonify, request
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import os
import mysql.connector
import sys

app = Flask(__name__)

# --- App Configuration ---
app.config["JWT_SECRET_KEY"] = "super-secret-key"
jwt = JWTManager(app)

# --- User Authentication ---
users = {
    "admin": { "username": "admin", "password": generate_password_hash("admin123") }
}

@app.route("/login", methods=["POST"])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    user = users.get(username, None)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"msg": "Bad username or password"}), 401
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

# --- Database Configuration & Connection Handling ---
DB_CFG = dict(
    host=os.getenv("DB_HOST", "127.0.0.1"),
    port=int(os.getenv("DB_PORT", 3306)),
    user=os.getenv("DB_USER", "demo"),
    password=os.getenv("DB_PASSWORD", "demopass"),
    database=os.getenv("DB_NAME", "demo"),
    # ssl_disabled=True
)

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CFG)
    except mysql.connector.Error as err:
        print(f"FATAL: Could not connect to database: {err}", file=sys.stderr)
        return None

def setup_database():
    """
    This function automatically creates and populates the database tables.
    It runs once when the application starts.
    """
    print("Connecting to database to run setup...")
    conn = get_db_connection()
    if not conn:
        sys.exit(1)
    
    print("Setting up tables... (This is safe to run multiple times)")
    cur = conn.cursor()
    
    # Create tables IF THEY DON'T EXIST
    cur.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        display_name VARCHAR(255) NOT NULL,
        client_status VARCHAR(50)
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        client_id BIGINT,
        account_no_dataphile VARCHAR(100) NULL,
        market_value DECIMAL(20, 2),
        FOREIGN KEY (client_id) REFERENCES clients(id) ON DELETE CASCADE
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        role_name VARCHAR(100),
        resource_name VARCHAR(100),
        can_read BOOLEAN
    );""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payloads (
        id BIGINT PRIMARY KEY AUTO_INCREMENT,
        data LONGTEXT
    );""")
    
    # Clear existing data to ensure a clean state for the demo
    cur.execute("""
    TRUNCATE 
        TABLE accounts;
    """)
    cur.execute("DELETE FROM clients;")
    cur.execute("ALTER TABLE clients AUTO_INCREMENT = 1;")
    cur.execute("TRUNCATE TABLE permissions;")
    
    # Insert sample data needed for the complex queries
    cur.execute("INSERT INTO clients (display_name, client_status) VALUES ('Global Corp Inc.', 'Active'), ('Tech Innovators LLC', 'Active');")
    cur.execute("INSERT INTO accounts (client_id, account_no_dataphile, market_value) VALUES (1, 'F12345', 150000.75), (1, NULL, 25000.50);")
    cur.execute("INSERT INTO permissions (role_name, resource_name, can_read) VALUES ('admin', 'ClientsViewSet', true);")
    
    conn.commit()
    cur.close()
    conn.close()
    print("Database setup complete. Tables are ready.")

# --- Original Simple Endpoints (Unchanged) ---
@app.route("/data", methods=["POST"])
@jwt_required()
def create_data():
    message = request.json.get("message")
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO payloads (data) VALUES (%s)", (message,))
    conn.commit()
    conn.close()
    return jsonify({"status": "created"}), 201

@app.route("/data", methods=["GET"])
@jwt_required()
def get_all_data():
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, data FROM payloads ORDER BY id DESC")
    payloads = cur.fetchall()
    conn.close()
    return jsonify(payloads)

# --- NEW Endpoints to Generate Complex Queries ---
@app.route("/generate-complex-queries", methods=["GET"])
@jwt_required()
def generate_complex_queries():
    """This single endpoint runs all the complex queries you need to capture."""
    conn = get_db_connection()
    if not conn: return jsonify({"error": "Database connection failed"}), 500
    
    results = {}
    try:
        cur = conn.cursor(dictionary=True)
        
        # Query 1: INNER JOIN
        cur.execute("""
            SELECT c.id as client_id, c.display_name, a.id as account_id, a.account_no_dataphile
            FROM clients c INNER JOIN accounts a ON c.id = a.client_id WHERE c.id = 1
        """)
        results['join_query'] = cur.fetchall()

        # Query 2: Subquery
        cur.execute("""
            SELECT id, display_name FROM clients 
            WHERE id IN (SELECT client_id FROM accounts WHERE market_value > 50000)
        """)
        results['subquery_query'] = cur.fetchall()

        # Query 3: Simple permission check
        cur.execute("SELECT role_name FROM permissions WHERE can_read = TRUE")
        results['permission_query'] = cur.fetchall()
        
        return jsonify(results)
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    setup_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
