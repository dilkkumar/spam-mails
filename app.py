import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from joblib import load
from bson.objectid import ObjectId

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-123')
app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb+srv://obul12:Obul123@cluster0.p1mlwmz.mongodb.net/Spammails?retryWrites=true&w=majority&appName=Cluster0')
mongo = PyMongo(app)

try:
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    tfidf = load(os.path.join(model_dir, 'tfidf_vectorizer.pkl'))
    model = load(os.path.join(model_dir, 'spam_detector_model.pkl'))
except Exception as e:
    raise RuntimeError(f"Failed to load ML models: {str(e)}") from e

def predict_spam(email_content):
    try:
        X = tfidf.transform([email_content])
        proba = model.predict_proba(X)[0]
        prediction = model.predict(X)[0]
        return {'is_spam': bool(prediction), 'probability': round(max(proba) * 100, 2)}
    except Exception as e:
        app.logger.error(f"Prediction error: {str(e)}")
        return {'error': 'Failed to process request'}

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
        total = mongo.db.checks.count_documents({'user_id': session['user_id']})
        spam_count = mongo.db.checks.count_documents({'user_id': session['user_id'], 'is_spam': True})
        
        return render_template('dashboard.html', user=user, total=total, spam_count=spam_count)
    except Exception as e:
        app.logger.error(f"Dashboard error: {str(e)}")
        flash('Error loading dashboard')
        return redirect(url_for('login'))

@app.route('/check', methods=['POST'])
def check_spam():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    email_content = request.form.get('email_content', '')
    
    if not email_content.strip():
        return jsonify({'error': 'No content provided'}), 400
    
    try:
        result = predict_spam(email_content)
        if 'error' in result:
            return jsonify(result), 500
            
        check_data = {
            'user_id': session['user_id'],
            'content': email_content[:200],
            'is_spam': result['is_spam'],
            'probability': result['probability'],
            'timestamp': datetime.datetime.utcnow()
        }
        mongo.db.checks.insert_one(check_data)
        
        return jsonify(result)
    
    except Exception as e:
        app.logger.error(f"Check error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            user = mongo.db.users.find_one({'email': email})
            if user and check_password_hash(user['password'], password):
                session['user_id'] = str(user['_id'])
                return redirect(url_for('dashboard'))
            
            flash('Invalid email or password')
            return redirect(url_for('login'))
        
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            flash('Login failed')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = generate_password_hash(request.form['password'])
            
            if mongo.db.users.find_one({'email': email}):
                flash('Email already registered')
                return redirect(url_for('register'))
            
            mongo.db.users.insert_one({
                'email': email,
                'password': password,
                'created_at': datetime.datetime.utcnow()
            })
            flash('Registration successful. Please login.')
            return redirect(url_for('login'))
        
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            flash('Registration failed')
            return redirect(url_for('register'))
    
    return render_template('register.html')

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Convert string user_id to ObjectId for query
        user_id = ObjectId(session['user_id'])
        # Add timestamp exists filter and proper sorting
        checks = list(mongo.db.checks.find({
            'user_id': session['user_id'],
            'timestamp': {'$exists': True}
        }).sort('timestamp', -1))
        
        return render_template('history.html', checks=checks)
    except Exception as e:
        app.logger.error(f"History error: {str(e)}")
        flash('Error loading history')
        return redirect(url_for('dashboard'))

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password')
            new_email = request.form.get('new_email')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            updates = {}
            
            if not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect')
                return redirect(url_for('settings'))
            
            if new_email and new_email != user['email']:
                if mongo.db.users.find_one({'email': new_email}):
                    flash('Email already exists')
                    return redirect(url_for('settings'))
                updates['email'] = new_email
            
            if new_password:
                if new_password != confirm_password:
                    flash('New passwords do not match')
                    return redirect(url_for('settings'))
                updates['password'] = generate_password_hash(new_password)
            
            if updates:
                mongo.db.users.update_one(
                    {'_id': ObjectId(session['user_id'])},
                    {'$set': updates}
                )
                flash('Settings updated successfully')
            
            return redirect(url_for('settings'))
        
        except Exception as e:
            app.logger.error(f"Settings error: {str(e)}")
            flash('Error updating settings')
            return redirect(url_for('settings'))
    
    return render_template('settings.html', user=user)

@app.route('/delete_check/<check_id>', methods=['DELETE'])
def delete_check(check_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        result = mongo.db.checks.delete_one({
            '_id': ObjectId(check_id),
            'user_id': session['user_id']
        })
        
        if result.deleted_count == 0:
            return jsonify({'error': 'Check not found or unauthorized'}), 404
            
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Delete check error: {str(e)}")
        return jsonify({'error': 'Server error'}), 500

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
