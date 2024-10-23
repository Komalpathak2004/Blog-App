from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
CORS(app)

# MongoDB configuration
app.config['MONGO_URI'] = 'mongodb+srv://komal:komal1234@blogapp.4hk3z.mongodb.net/?retryWrites=true&w=majority&appName=BlogApp'
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # Change this to a secure key in a real application

client = MongoClient(app.config['MONGO_URI'])
db = client.blog_db
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Collections
users_collection = db.users
blogs_collection = db.blogs

# Default Route (Home Page)
@app.route('/')
def home():
    return render_template("index.html")  # Render index.html as the homepage

# User Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        if users_collection.find_one({"username": data['username']}):
            return jsonify({"msg": "Username already exists"}), 409

        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        users_collection.insert_one({"username": data['username'], "password": hashed_password})
        return redirect(url_for('login'))  # Redirect to login after successful registration
    return render_template("register.html")

# User Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        user = users_collection.find_one({"username": data['username']})

        if user and bcrypt.check_password_hash(user['password'], data['password']):
            access_token = create_access_token(identity=str(user['_id']))
            return redirect(url_for('dashboard'))  # Redirect to dashboard after login
        return jsonify({"msg": "Bad username or password"}), 401
    return render_template("login.html")

# User Dashboard Route
@app.route('/dashboard')
@jwt_required()
def dashboard():
    current_user = get_jwt_identity()
    return render_template("dashboard.html", user_id=current_user)  # Render dashboard.html

# Route to Create Blog
@app.route('/blogs', methods=['POST'])
@jwt_required()
def create_blog():
    current_user = get_jwt_identity()
    data = request.get_json()
    new_blog = {
        "title": data['title'],
        "content": data['content'],
        "photo": data.get('photo', ''),  # Photo upload
        "audio": data.get('audio', ''),  # Audio upload
        "video": data.get('video', ''),  # Video upload
        "created_at": datetime.utcnow(),
        "author_id": current_user,
        "comments": [],
        "likes": 0
    }
    blogs_collection.insert_one(new_blog)
    return jsonify({"msg": "Blog created", "blog_id": str(new_blog['_id'])}), 201

# Route to Fetch All Blogs
@app.route('/blogs', methods=['GET'])
def get_blogs():
    blogs = blogs_collection.find()
    return jsonify([{"id": str(blog['_id']), "title": blog['title'], "content": blog['content'], "likes": blog['likes']} for blog in blogs]), 200

# Route to Like a Blog
@app.route('/blogs/<blog_id>/like', methods=['POST'])
@jwt_required()
def like_blog(blog_id):
    current_user = get_jwt_identity()
    # Logic for liking the blog
    blogs_collection.update_one({"_id": ObjectId(blog_id)}, {"$inc": {"likes": 1}})
    return jsonify({"msg": "Blog liked"}), 200

# Route to Comment on a Blog
@app.route('/blogs/<blog_id>/comment', methods=['POST'])
@jwt_required()
def comment_blog(blog_id):
    current_user = get_jwt_identity()
    data = request.get_json()
    comment = {"user_id": current_user, "comment": data['comment'], "created_at": datetime.utcnow()}
    blogs_collection.update_one({"_id": ObjectId(blog_id)}, {"$push": {"comments": comment}})
    return jsonify({"msg": "Comment added"}), 201

# Route to Delete a Blog
@app.route('/blogs/<blog_id>', methods=['DELETE'])
@jwt_required()
def delete_blog(blog_id):
    current_user = get_jwt_identity()
    blog = blogs_collection.find_one({"_id": ObjectId(blog_id)})

    if blog and blog['author_id'] == current_user:
        blogs_collection.delete_one({"_id": ObjectId(blog_id)})
        return jsonify({"msg": "Blog deleted"}), 200
    return jsonify({"msg": "Unauthorized or blog not found"}), 403

if __name__ == '__main__':
    app.run(debug=True)
