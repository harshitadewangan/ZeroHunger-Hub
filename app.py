from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify
import os
import html
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
from pymongo import MongoClient
from bson.objectid import ObjectId

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_secret_key')
UPLOAD_FOLDER = '/tmp/uploads' if os.environ.get('VERCEL') == '1' else 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
    except Exception:
        pass

# --- DATABASE CONFIGURATION ---
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/zerohungerhub')
client = MongoClient(MONGO_URI)
try:
    db = client.get_default_database()
except Exception:
    db = client['zerohungerhub']

@app.context_processor
def inject_notifications():
    if 'user_id' in session:
        user_id = session['user_id']
        notifs = list(db.notifications.find({'user_id': user_id}).sort('created_at', -1).limit(5))
        unread = db.notifications.count_documents({'user_id': user_id, 'is_read': 0})
        for n in notifs:
            n['id'] = str(n['_id'])
        return dict(notifications=notifs, unread_count=unread)
    return dict(notifications=[], unread_count=0)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    active_donors = db.users.count_documents({'role': 'donor'})
    meals_shared = db.bookings.count_documents({'status': 'completed'})
    return render_template('index.html', active_donors=active_donors, meals_shared=meals_shared)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        location = request.form.get('location', '')
        contact = request.form.get('contact', '')
        
        if db.users.find_one({'email': email}):
            flash('Email already exists.')
            return redirect(url_for('signup'))
            
        db.users.insert_one({
            'name': name,
            'email': email,
            'password': password,
            'role': role,
            'location': location,
            'contact': contact
        })
        flash('Signup successful! Please login.')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.users.find_one({'email': email})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['user_name'] = user['name']
            session['role'] = user['role']
            if user['role'] == 'donor':
                return redirect(url_for('donor_dashboard'))
            else:
                return redirect(url_for('volunteer_dashboard'))
        else:
            flash('Invalid credentials.')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/donor_dashboard')
@login_required
def donor_dashboard():
    if session['role'] != 'donor':
        return redirect(url_for('index'))
        
    user_id = session['user_id']
    total_posts = db.food_posts.count_documents({'donor_id': user_id})
    
    food_ids = [str(f['_id']) for f in db.food_posts.find({'donor_id': user_id}, {'_id': 1})]
    completed = db.bookings.count_documents({'food_id': {'$in': food_ids}, 'status': 'completed'})
    
    pending_bookings = db.bookings.find({'food_id': {'$in': food_ids}, 'status': 'pending'})
    pending_requests = []
    for b in pending_bookings:
        food = db.food_posts.find_one({'_id': ObjectId(b['food_id'])})
        volunteer = db.users.find_one({'_id': ObjectId(b['user_id'])})
        if food and volunteer:
            pending_requests.append({
                'booking_id': str(b['_id']),
                'food_name': food.get('name'),
                'volunteer_name': volunteer.get('name'),
                'status': b.get('status')
            })
            
    return render_template('donor_dashboard.html', total_posts=total_posts, completed=completed, pending_requests=pending_requests)

@app.route('/add_food', methods=['GET', 'POST'])
def add_food():
    if 'user_id' not in session or session['role'] != 'donor':
        return redirect(url_for('login'))
        
    user = db.users.find_one({'_id': ObjectId(session['user_id'])})
    user_contact = user.get('contact', '') if user else ''
    
    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        price = float(request.form['price'])
        location = request.form['location']
        expiry = request.form['expiry']
        
        try:
            exp_date = datetime.strptime(expiry, '%Y-%m-%dT%H:%M')
            if exp_date < datetime.now():
                flash('Expiry date must be in the future.')
                return redirect(url_for('add_food'))
        except ValueError:
            pass
            
        contact = request.form.get('contact', user_contact)
        payment_method = request.form.get('payment_method', 'online')
        upi_id = request.form.get('upi_id', '')
        
        qr_code_file = request.files.get('qr_code')
        qr_code_filename = None
        if qr_code_file:
            qr_code_filename = secure_filename(qr_code_file.filename)
            qr_code_file.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_code_filename))
            
        verification_code = request.form.get('verification_code', '')
        
        image = request.files['image']
        image_filename = None
        if image:
            image_filename = secure_filename(image.filename)
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))
            
        db.food_posts.insert_one({
            'donor_id': session['user_id'],
            'name': name,
            'quantity': quantity,
            'price': price,
            'location': location,
            'expiry': expiry,
            'image': image_filename,
            'contact': contact,
            'payment_method': payment_method,
            'upi_id': upi_id,
            'qr_code': qr_code_filename,
            'verification_code': verification_code,
            'is_booked': 0
        })
        flash('Food added successfully!')
        return redirect(url_for('donor_dashboard'))
    return render_template('add_food.html', user_contact=user_contact)

@app.route('/edit_food/<food_id>', methods=['GET', 'POST'])
def edit_food(food_id):
    if 'user_id' not in session or session['role'] != 'donor':
        return redirect(url_for('login'))
        
    try:
        food = db.food_posts.find_one({'_id': ObjectId(food_id)})
    except:
        flash('Invalid food ID.')
        return redirect(url_for('view_food'))
        
    if not food or food.get('donor_id') != session['user_id']:
        flash('You do not have permission to edit this listing.')
        return redirect(url_for('view_food'))

    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        price = float(request.form['price'])
        location = request.form['location']
        expiry = request.form['expiry']
        contact = request.form.get('contact', food.get('contact', ''))
        payment_method = request.form.get('payment_method', 'online')
        upi_id = request.form.get('upi_id', food.get('upi_id', ''))
        verification_code = request.form.get('verification_code', food.get('verification_code', ''))

        image_file = request.files.get('image')
        image_filename = food.get('image')
        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        qr_file = request.files.get('qr_code')
        qr_code_filename = food.get('qr_code')
        if qr_file and qr_file.filename:
            qr_code_filename = secure_filename(qr_file.filename)
            qr_file.save(os.path.join(app.config['UPLOAD_FOLDER'], qr_code_filename))

        db.food_posts.update_one(
            {'_id': ObjectId(food_id)},
            {'$set': {
                'name': name,
                'quantity': quantity,
                'price': price,
                'location': location,
                'expiry': expiry,
                'contact': contact,
                'payment_method': payment_method,
                'upi_id': upi_id,
                'qr_code': qr_code_filename,
                'verification_code': verification_code,
                'image': image_filename
            }}
        )
        flash('Listing updated successfully!')
        return redirect(url_for('view_food'))

    food['id'] = str(food['_id'])
    return render_template('edit_food.html', food=food)

@app.route('/api/delete_post/<food_id>', methods=['DELETE', 'POST'])
def api_delete_post(food_id):
    if 'user_id' not in session or session['role'] != 'donor':
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        food = db.food_posts.find_one({'_id': ObjectId(food_id)})
    except:
        return jsonify({'error': 'Not found'}), 404
        
    if not food or food.get('donor_id') != session['user_id']:
        return jsonify({'error': 'Not allowed'}), 403

    affected_bookings = db.bookings.find({
        'food_id': food_id,
        'status': {'$in': ['pending', 'accepted']}
    })
    
    for booking in affected_bookings:
        msg = f"Your request for {food.get('name')} was cancelled because the donor removed the post."
        db.notifications.insert_one({
            'user_id': booking['user_id'],
            'message': msg,
            'link': url_for('order_history'),
            'is_read': 0,
            'created_at': datetime.now()
        })

    db.bookings.delete_many({'food_id': food_id})
    db.food_posts.delete_one({'_id': ObjectId(food_id)})
    
    return jsonify({'success': True})

@app.route('/api/notifications')
def api_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
        
    user_id = session['user_id']
    notifs = list(db.notifications.find({'user_id': user_id}).sort('created_at', -1).limit(20))
    for n in notifs:
        n['id'] = str(n['_id'])
        n['_id'] = str(n['_id'])
        
    unread = db.notifications.count_documents({'user_id': user_id, 'is_read': 0})
    return jsonify({'notifications': notifs, 'unread_count': unread})

@app.route('/api/notifications/delete/<notification_id>', methods=['DELETE', 'POST'])
def api_delete_notification(notification_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        result = db.notifications.delete_one({'_id': ObjectId(notification_id), 'user_id': session['user_id']})
        if result.deleted_count == 0:
            return jsonify({'error': 'Not found'}), 404
    except:
        return jsonify({'error': 'Invalid ID'}), 400
        
    unread = db.notifications.count_documents({'user_id': session['user_id'], 'is_read': 0})
    return jsonify({'success': True, 'unread_count': unread})

@app.route('/api/notifications/clear', methods=['POST'])
def api_clear_notifications():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
        
    db.notifications.delete_many({'user_id': session['user_id']})
    return jsonify({'success': True, 'unread_count': 0})

@app.route('/view_food')
def view_food():
    if 'user_id' not in session or session['role'] != 'donor':
        return redirect(url_for('login'))
        
    foods_cursor = db.food_posts.find({'donor_id': session['user_id']})
    foods = []
    for f in foods_cursor:
        f['id'] = str(f['_id'])
        foods.append(f)
        
    return render_template('view_food.html', foods=foods)

@app.route('/donor_history')
def donor_history():
    if 'user_id' not in session or session['role'] != 'donor':
        return redirect(url_for('login'))
        
    user_id = session['user_id']
    food_ids = [str(f['_id']) for f in db.food_posts.find({'donor_id': user_id}, {'_id': 1})]
    
    bookings = db.bookings.find({'food_id': {'$in': food_ids}}).sort('updated_at', -1)
    history = []
    for b in bookings:
        food = db.food_posts.find_one({'_id': ObjectId(b['food_id'])})
        volunteer = db.users.find_one({'_id': ObjectId(b['user_id'])})
        if food and volunteer:
            history.append({
                'name': food.get('name'),
                'volunteer_name': volunteer.get('name'),
                'volunteer_contact': volunteer.get('contact'),
                'volunteer_location': volunteer.get('location'),
                'status': b.get('status'),
                'payment_status': b.get('payment_status'),
                'booking_id': str(b['_id'])
            })
            
    return render_template('donor_history.html', history=history)

@app.route('/volunteer_dashboard')
def volunteer_dashboard():
    if 'user_id' not in session or session['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    view = request.args.get('view', 'available')
    filter_type = request.args.get('filter', 'all')
    location = request.args.get('location', '')
    
    query = {}
    
    if view == 'available':
        query['is_booked'] = 0
    elif view == 'booked':
        booked_food_ids = [b['food_id'] for b in db.bookings.find({'user_id': session['user_id'], 'status': {'$in': ['pending', 'accepted']}})]
        query['_id'] = {'$in': [ObjectId(fid) for fid in booked_food_ids]}
    else:
        view = 'available'
        query['is_booked'] = 0
        
    if filter_type == 'free':
        query['price'] = 0
    elif filter_type == 'paid':
        query['price'] = {'$gt': 0}
        
    if location:
        query['location'] = {'$regex': location, '$options': 'i'}
        
    foods_cursor = db.food_posts.find(query)
    foods = []
    for f in foods_cursor:
        f['id'] = str(f['_id'])
        if view == 'booked':
            booking = db.bookings.find_one({'food_id': str(f['_id']), 'user_id': session['user_id'], 'status': {'$in': ['pending', 'accepted']}})
            if booking:
                f['booking_status'] = booking.get('status')
        foods.append(f)
        
    return render_template('volunteer_dashboard.html', foods=foods, filter=filter_type, location=location, view=view)

@app.route('/api/volunteer_dashboard')
def api_volunteer_dashboard():
    if 'user_id' not in session or session['role'] != 'volunteer':
        return jsonify({'error': 'Unauthorized'}), 403
        
    view = request.args.get('view', 'available')
    filter_type = request.args.get('filter', 'all')
    location = request.args.get('location', '')
    
    query = {}
    
    if view == 'available':
        query['is_booked'] = 0
    elif view == 'booked':
        booked_food_ids = [b['food_id'] for b in db.bookings.find({'user_id': session['user_id'], 'status': {'$in': ['pending', 'accepted']}})]
        query['_id'] = {'$in': [ObjectId(fid) for fid in booked_food_ids]}
    else:
        return jsonify({'error': 'Invalid view'}), 400
        
    if filter_type == 'free':
        query['price'] = 0
    elif filter_type == 'paid':
        query['price'] = {'$gt': 0}
        
    if location:
        query['location'] = {'$regex': location, '$options': 'i'}
        
    foods_cursor = db.food_posts.find(query)
    foods = []
    for f in foods_cursor:
        f['id'] = str(f['_id'])
        f['_id'] = str(f['_id'])
        if view == 'booked':
            booking = db.bookings.find_one({'food_id': f['id'], 'user_id': session['user_id'], 'status': {'$in': ['pending', 'accepted']}})
            if booking:
                f['booking_status'] = booking.get('status')
        foods.append(f)
        
    return jsonify({'foods': foods, 'view': view})

@app.route('/api/donor_dashboard')
def api_donor_dashboard():
    try:
        if 'user_id' not in session or session['role'] != 'donor':
            return jsonify({'error': 'Unauthorized'}), 403
            
        user_id = session['user_id']
        food_ids = [str(f['_id']) for f in db.food_posts.find({'donor_id': user_id}, {'_id': 1})]
        
        pending_bookings = db.bookings.find({'food_id': {'$in': food_ids}, 'status': 'pending'})
        pending_requests = []
        for b in pending_bookings:
            food = db.food_posts.find_one({'_id': ObjectId(b['food_id'])})
            volunteer = db.users.find_one({'_id': ObjectId(b['user_id'])})
            if food and volunteer:
                pending_requests.append({
                    'booking_id': str(b['_id']),
                    'food_name': food.get('name'),
                    'volunteer_name': volunteer.get('name'),
                    'status': b.get('status'),
                    'volunteer_contact': volunteer.get('contact'),
                    'volunteer_location': volunteer.get('location')
                })
                
        return jsonify({'pending_requests': pending_requests})
    except Exception as e:
        return jsonify({'error': str(e), 'pending_requests': []}), 500

@app.route('/food_details/<food_id>')
def food_details(food_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    try:
        food = db.food_posts.find_one({'_id': ObjectId(food_id)})
    except:
        flash('Invalid food ID.')
        return redirect(url_for('volunteer_dashboard'))
        
    if not food:
        flash('Food not found.')
        return redirect(url_for('volunteer_dashboard'))
        
    food['id'] = str(food['_id'])
    donor = db.users.find_one({'_id': ObjectId(food['donor_id'])})
    if donor:
        food['donor_name'] = donor.get('name')
        
    booking = db.bookings.find_one({
        'food_id': food_id,
        'user_id': session['user_id'],
        'status': {'$in': ['pending', 'accepted']}
    })
    
    if booking:
        booking['id'] = str(booking['_id'])
        
    return render_template('food_details.html', food=food, booking=booking)

@app.route('/book_confirm/<food_id>', methods=['POST'])
def book_confirm(food_id):
    if 'user_id' not in session or session['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    try:
        food = db.food_posts.find_one({'_id': ObjectId(food_id)})
    except:
        flash('Invalid food ID.')
        return redirect(url_for('volunteer_dashboard'))
        
    if not food:
        flash('Food not found.')
        return redirect(url_for('volunteer_dashboard'))
        
    food['id'] = str(food['_id'])
    donor = db.users.find_one({'_id': ObjectId(food['donor_id'])})
    if donor:
        food['donor_name'] = donor.get('name')
        
    existing_booking = db.bookings.find_one({'food_id': food_id, 'status': {'$ne': 'completed'}})
    if existing_booking:
        flash('Food is already booked.')
        return redirect(url_for('food_details', food_id=food_id))
        
    return render_template('book_confirm.html', food=food)

@app.route('/book_food/<food_id>', methods=['POST'])
def book_food(food_id):
    if 'user_id' not in session or session['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    existing_booking = db.bookings.find_one({'food_id': food_id, 'status': {'$in': ['pending', 'accepted', 'completed']}})
    if existing_booking:
        flash('Food already requested or booked by someone else.')
        return redirect(url_for('food_details', food_id=food_id))
        
    result = db.bookings.insert_one({
        'user_id': session['user_id'],
        'food_id': food_id,
        'status': 'pending',
        'updated_at': datetime.now()
    })
    
    db.food_posts.update_one({'_id': ObjectId(food_id)}, {'$set': {'is_booked': 1}})
    
    food_data = db.food_posts.find_one({'_id': ObjectId(food_id)})
    if food_data:
        donor_id = food_data.get('donor_id')
        food_name = food_data.get('name')
        msg = f"{session['user_name']} has requested your food: {food_name}"
        db.notifications.insert_one({
            'user_id': donor_id,
            'message': msg,
            'link': url_for('donor_dashboard'),
            'is_read': 0,
            'created_at': datetime.now()
        })

    flash('Food request sent to the donor! Waiting for their approval.')
    return redirect(url_for('volunteer_dashboard'))

@app.route('/donor/accept_booking/<booking_id>', methods=['POST'])
def accept_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'donor':
        return redirect(url_for('login'))
        
    try:
        booking = db.bookings.find_one({'_id': ObjectId(booking_id), 'status': 'pending'})
    except:
        booking = None
        
    if booking:
        food_id = booking['food_id']
        food = db.food_posts.find_one({'_id': ObjectId(food_id), 'donor_id': session['user_id']})
        if food:
            db.bookings.update_one({'_id': ObjectId(booking_id)}, {'$set': {'status': 'accepted', 'updated_at': datetime.now()}})
            db.food_posts.update_one({'_id': ObjectId(food_id)}, {'$set': {'is_booked': 1}})
            msg = f"Your request for {food.get('name')} was accepted! Please proceed."
            db.notifications.insert_one({
                'user_id': booking['user_id'],
                'message': msg,
                'link': url_for('order_history'),
                'is_read': 0,
                'created_at': datetime.now()
            })
            flash('Booking accepted.')
            
    return redirect(url_for('donor_dashboard'))

@app.route('/donor/reject_booking/<booking_id>', methods=['POST'])
def reject_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'donor':
        return redirect(url_for('login'))
        
    try:
        booking = db.bookings.find_one({'_id': ObjectId(booking_id), 'status': 'pending'})
    except:
        booking = None
        
    if booking:
        food_id = booking['food_id']
        food = db.food_posts.find_one({'_id': ObjectId(food_id), 'donor_id': session['user_id']})
        if food:
            db.bookings.update_one({'_id': ObjectId(booking_id)}, {'$set': {'status': 'rejected', 'updated_at': datetime.now()}})
            db.food_posts.update_one({'_id': ObjectId(food_id)}, {'$set': {'is_booked': 0}})
            msg = f"Your request for {food.get('name')} was declined."
            db.notifications.insert_one({
                'user_id': booking['user_id'],
                'message': msg,
                'link': url_for('order_history'),
                'is_read': 0,
                'created_at': datetime.now()
            })
            flash('Booking rejected.')
            
    return redirect(url_for('donor_dashboard'))

@app.route('/volunteer/complete_booking/<booking_id>', methods=['POST'])
def complete_booking(booking_id):
    if 'user_id' not in session or session['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    try:
        booking = db.bookings.find_one({'_id': ObjectId(booking_id), 'user_id': session['user_id'], 'status': 'accepted'})
    except:
        booking = None
        
    if booking:
        food = db.food_posts.find_one({'_id': ObjectId(booking['food_id'])})
        if food:
            price = food.get('price', 0)
            method = food.get('payment_method', '')
            if price > 0 and method == 'online':
                return redirect(url_for('payment', booking_id=booking_id))
            else:
                db.bookings.update_one(
                    {'_id': ObjectId(booking_id)},
                    {'$set': {'status': 'completed', 'payment_status': 'free', 'updated_at': datetime.now()}}
                )
                flash('Food collection marked as completed!')
                
    return redirect(url_for('order_history'))

@app.route('/notifications/read', methods=['POST'])
def read_notifications():
    if 'user_id' not in session:
        return jsonify({'success': False})
        
    db.notifications.update_many(
        {'user_id': session['user_id']},
        {'$set': {'is_read': 1}}
    )
    return jsonify({'success': True})

@app.route('/payment/<booking_id>', methods=['GET', 'POST'])
def payment(booking_id):
    if 'user_id' not in session or session['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    try:
        booking = db.bookings.find_one({'_id': ObjectId(booking_id), 'user_id': session['user_id']})
    except:
        booking = None
        
    if not booking or booking.get('status') == 'completed':
        flash('Invalid or already completed booking.')
        return redirect(url_for('volunteer_dashboard'))
        
    food = db.food_posts.find_one({'_id': ObjectId(booking['food_id'])})
    if not food:
        flash('Food not found.')
        return redirect(url_for('volunteer_dashboard'))
        
    booking_dict = {
        'id': str(booking['_id']),
        'price': food.get('price'),
        'name': food.get('name'),
        'upi_id': food.get('upi_id'),
        'qr_code': food.get('qr_code'),
        'status': booking.get('status'),
        'verification_code': food.get('verification_code')
    }
    
    if request.method == 'POST':
        entered_code = request.form.get('verification_code')
        if entered_code == food.get('verification_code'):
            db.bookings.update_one(
                {'_id': ObjectId(booking_id)},
                {'$set': {'status': 'completed', 'payment_status': 'paid', 'updated_at': datetime.now()}}
            )
            return redirect(url_for('payment_success', booking_id=booking_id))
        else:
            flash('Invalid verification code. Please contact the donor for the correct code.')
            
    return render_template('payment.html', booking=booking_dict)

@app.route('/payment_success/<booking_id>')
def payment_success(booking_id):
    if 'user_id' not in session or session['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    try:
        booking = db.bookings.find_one({'_id': ObjectId(booking_id), 'user_id': session['user_id']})
    except:
        booking = None
        
    if not booking or booking.get('status') != 'completed':
        flash('Payment verification failed.')
        return redirect(url_for('volunteer_dashboard'))
        
    food = db.food_posts.find_one({'_id': ObjectId(booking['food_id'])})
    return render_template('payment_success.html', food_name=food.get('name') if food else 'Unknown')

@app.route('/order_history')
def order_history():
    if 'user_id' not in session or session['role'] != 'volunteer':
        return redirect(url_for('login'))
        
    bookings = db.bookings.find({'user_id': session['user_id']}).sort('updated_at', -1)
    orders = []
    for b in bookings:
        food = db.food_posts.find_one({'_id': ObjectId(b['food_id'])})
        if food:
            orders.append({
                'id': str(b['_id']),
                'name': food.get('name'),
                'status': b.get('status'),
                'payment_status': b.get('payment_status')
            })
            
    return render_template('order_history.html', orders=orders)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        location = request.form.get('location', '')
        contact = request.form.get('contact', '')
        
        db.users.update_one(
            {'_id': ObjectId(session['user_id'])},
            {'$set': {'name': name, 'email': email, 'location': location, 'contact': contact}}
        )
        session['user_name'] = name
        flash('Profile updated.')
        return redirect(url_for('profile'))
        
    user = db.users.find_one({'_id': ObjectId(session['user_id'])})
    if user:
        user_data = {
            'name': user.get('name'),
            'email': user.get('email'),
            'location': user.get('location'),
            'contact': user.get('contact')
        }
    else:
        user_data = None
    return render_template('profile.html', user=user_data)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/reviews')
def reviews():
    all_reviews = list(db.reviews.find().sort('created_at', -1))
    formatted_reviews = []
    for r in all_reviews:
        formatted_reviews.append({
            'user_name': r.get('user_name'),
            'role': r.get('role'),
            'rating': r.get('rating'),
            'content': r.get('content'),
            'created_at': r.get('created_at')
        })
    return render_template('reviews.html', reviews=formatted_reviews)

@app.route('/reviews/submit', methods=['GET', 'POST'])
def submit_review():
    if 'user_id' not in session:
        flash('Please log in to write a review.')
        return redirect(url_for('login'))

    if request.method == 'POST':
        raw_content = request.form.get('content', '').strip()
        raw_rating  = request.form.get('rating', '').strip()

        if not raw_content:
            flash('Review content cannot be empty.')
            return redirect(url_for('submit_review'))

        try:
            rating = int(raw_rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            flash('Please select a valid rating between 1 and 5 stars.')
            return redirect(url_for('submit_review'))

        safe_content = html.escape(raw_content)

        db.reviews.insert_one({
            'user_id': session['user_id'],
            'user_name': session['user_name'],
            'role': session['role'],
            'rating': rating,
            'content': safe_content,
            'created_at': datetime.now()
        })
        
        flash('Your review has been posted! Thank you for sharing your experience.')
        return redirect(url_for('reviews'))

    return render_template('submit_review.html')

@app.route('/reviews/my')
def my_reviews():
    if 'user_id' not in session:
        flash('Please log in to view your reviews.')
        return redirect(url_for('login'))

    user_reviews = list(db.reviews.find({'user_id': session['user_id']}).sort('created_at', -1))
    formatted_reviews = []
    for r in user_reviews:
        formatted_reviews.append({
            'user_name': r.get('user_name'),
            'role': r.get('role'),
            'rating': r.get('rating'),
            'content': r.get('content'),
            'created_at': r.get('created_at')
        })
    return render_template('my_reviews.html', reviews=formatted_reviews)

if __name__ == '__main__':
    app.run(debug=False)