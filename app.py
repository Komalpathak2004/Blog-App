from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import os

app = Flask(__name__)
CORS(app)

# MongoDB configuration
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # Change this to a secure key in a real application

client = MongoClient(app.config['MONGO_URI'])
db = client.blog_db
bcrypt = Bcrypt(app)
jwt = JWTManager(app)

# Collections
users_collection = db.users
blogs_collection = db.blogs

# Default Route
@app.route('/')
def home():
    return render_template("index.html")  # Render index.html as the homepage

@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")

# Route for Login Page
@app.route('/login')
def login_page():
    return render_template("login.html")

# Route for Logout
@app.route('/logout')
def logout():
    return render_template("index.html")

# Route for View Page
@app.route('/view')
def view():
    return render_template("view.html")

# Route for Register Page
@app.route('/register')
def register_page():
    return render_template("register.html")  # Render register.html

# Route for Create Blog Page
@app.route('/create_blog')
def create_blog_page():
    return render_template("create_blog.html")  # Render create_blog.html

# User Registration Route
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if users_collection.find_one({"username": data['username']}):
        return jsonify({"msg": "Username already exists"}), 409

    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    users_collection.insert_one({"username": data['username'], "password": hashed_password})
    return jsonify({"msg": "User registered successfully"}), 201

# User Login Route
@app.route('/auth', methods=['POST'])
def login():
    data = request.get_json()
    user = users_collection.find_one({"username": data['username']})

    if user and bcrypt.check_password_hash(user['password'], data['password']):
        access_token = create_access_token(identity=str(user['_id']))
        return jsonify(access_token=access_token), 200
    return jsonify({"msg": "Bad username or password"}), 401

# Route to Create Blog
@app.route('/blogs', methods=['POST'])
@jwt_required()
def create_blog():
    current_user = get_jwt_identity()
    data = request.get_json()
    new_blog = {
        "title": data['title'],
        "content": data['content'],
        "created_at": datetime.utcnow(),
        "author_id": current_user,
        "comments": [],
        "likes": 0
    }
    result = blogs_collection.insert_one(new_blog)
    return jsonify({"msg": "Blog created", "blog_id": str(result.inserted_id)}), 201

# Route to Fetch Blogs
@app.route('/blogs', methods=['GET'])
def get_blogs():
    blogs = blogs_collection.find()
    return jsonify([{"id": str(blog['_id']), "title": blog['title'], "content": blog['content'], "likes": blog['likes']} for blog in blogs]), 200

# Route to Update Blog
@app.route('/blogs/<string:blog_id>', methods=['PUT'])
@jwt_required()
def update_blog(blog_id):
    current_user = get_jwt_identity()
    data = request.get_json()

    blog = blogs_collection.find_one({"_id": ObjectId(blog_id), "author_id": current_user})
    if not blog:
        return jsonify({"msg": "Blog not found or you're not authorized to update this blog"}), 404

    blogs_collection.update_one({"_id": ObjectId(blog_id)}, {"$set": {"title": data['title'], "content": data['content'], "updated_at": datetime.utcnow()}})
    return jsonify({"msg": "Blog updated successfully"}), 200

# Route to Delete Blog
@app.route('/blogs/<string:blog_id>', methods=['DELETE'])
@jwt_required()
def delete_blog(blog_id):
    current_user = get_jwt_identity()
    blog = blogs_collection.find_one({"_id": ObjectId(blog_id), "author_id": current_user})
    if not blog:
        return jsonify({"msg": "Blog not found or you're not authorized to delete this blog"}), 404

    blogs_collection.delete_one({"_id": ObjectId(blog_id)})
    return jsonify({"msg": "Blog deleted successfully"}), 200

# Route to Add a Comment to a Blog
@app.route('/blogs/<string:blog_id>/comments', methods=['POST'])
@jwt_required()
def add_comment(blog_id):
    current_user = get_jwt_identity()
    data = request.get_json()

    comment = {
        "user_id": current_user,
        "content": data['content'],
        "created_at": datetime.utcnow()
    }
    blogs_collection.update_one({"_id": ObjectId(blog_id)}, {"$push": {"comments": comment}})
    return jsonify({"msg": "Comment added successfully"}), 201

# Route to Like a Blog
@app.route('/blogs/<string:blog_id>/like', methods=['POST'])
@jwt_required()
def like_blog(blog_id):
    current_user = get_jwt_identity()
    
    # Check if the blog already has this user liking it
    blog = blogs_collection.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        return jsonify({"msg": "Blog not found"}), 404
    
    # Increment likes
    blogs_collection.update_one({"_id": ObjectId(blog_id)}, {"$inc": {"likes": 1}})
    return jsonify({"msg": "Blog liked successfully"}), 200

# Route to Fetch Comments for a Blog
@app.route('/blogs/<string:blog_id>/comments', methods=['GET'])
def get_comments(blog_id):
    blog = blogs_collection.find_one({"_id": ObjectId(blog_id)})
    if not blog:
        return jsonify({"msg": "Blog not found"}), 404
    
    return jsonify({"comments": blog['comments']}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
