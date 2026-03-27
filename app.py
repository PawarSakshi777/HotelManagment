from datetime import datetime
from functools import wraps
import os

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from flask_mysqldb import MySQL
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'change-this-in-production')
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'hotel_management')
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)


@app.before_request
def load_logged_in_user():
    user_id = session.get('user_id')
    if user_id is None:
        g.user = None
        return

    cur = mysql.connection.cursor()
    cur.execute('SELECT id, name, email, role FROM users WHERE id = %s', (user_id,))
    g.user = cur.fetchone()
    cur.close()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash('Please login first.', 'warning')
            return redirect(url_for('login'))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if g.user is None:
                flash('Please login first.', 'warning')
                return redirect(url_for('login'))
            if g.user['role'] != role:
                flash('You are not authorized to access this page.', 'danger')
                return redirect(url_for('route_dashboard'))
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


@app.route('/')
def home():
    if g.user:
        return redirect(url_for('route_dashboard'))
    return render_template('home.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'customer')

        if not name or not email or not password or role not in {'admin', 'customer'}:
            flash('All fields are required and role must be valid.', 'danger')
            return render_template('register.html')

        cur = mysql.connection.cursor()
        cur.execute('SELECT id FROM users WHERE email = %s', (email,))
        existing = cur.fetchone()

        if existing:
            cur.close()
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))

        hashed_password = generate_password_hash(password)
        cur.execute(
            'INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, %s)',
            (name, email, hashed_password, role),
        )
        mysql.connection.commit()
        cur.close()

        flash('Registration successful. Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        cur = mysql.connection.cursor()
        cur.execute('SELECT * FROM users WHERE email = %s', (email,))
        user = cur.fetchone()
        cur.close()

        if user is None or not check_password_hash(user['password_hash'], password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')

        session.clear()
        session['user_id'] = user['id']
        flash(f"Welcome back, {user['name']}!", 'success')
        return redirect(url_for('route_dashboard'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def route_dashboard():
    if g.user['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('customer_dashboard'))


@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    cur = mysql.connection.cursor()

    cur.execute('SELECT COUNT(*) AS total_rooms FROM rooms')
    total_rooms = cur.fetchone()['total_rooms']

    cur.execute('SELECT COUNT(*) AS total_bookings FROM bookings')
    total_bookings = cur.fetchone()['total_bookings']

    cur.execute("SELECT COUNT(*) AS active_bookings FROM bookings WHERE status = 'booked'")
    active_bookings = cur.fetchone()['active_bookings']

    cur.execute('SELECT * FROM rooms ORDER BY created_at DESC')
    rooms = cur.fetchall()

    cur.execute(
        '''
        SELECT b.id, u.name AS customer_name, r.room_number, r.room_type,
               b.check_in_date, b.check_out_date, b.total_price, b.status
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.created_at DESC
        '''
    )
    bookings = cur.fetchall()
    cur.close()

    stats = {
        'total_rooms': total_rooms,
        'total_bookings': total_bookings,
        'active_bookings': active_bookings,
    }

    return render_template('admin_dashboard.html', rooms=rooms, bookings=bookings, stats=stats)


@app.route('/admin/room/add', methods=['POST'])
@role_required('admin')
def add_room():
    room_number = request.form.get('room_number', '').strip()
    room_type = request.form.get('room_type', '').strip()
    price = request.form.get('price_per_night', '').strip()
    capacity = request.form.get('capacity', '').strip()

    if not all([room_number, room_type, price, capacity]):
        flash('All room fields are required.', 'danger')
        return redirect(url_for('admin_dashboard'))

    try:
        price_val = float(price)
        capacity_val = int(capacity)
        if price_val <= 0 or capacity_val <= 0:
            raise ValueError
    except ValueError:
        flash('Price and capacity must be valid positive numbers.', 'danger')
        return redirect(url_for('admin_dashboard'))

    cur = mysql.connection.cursor()
    cur.execute('SELECT id FROM rooms WHERE room_number = %s', (room_number,))
    if cur.fetchone():
        cur.close()
        flash('Room number already exists.', 'warning')
        return redirect(url_for('admin_dashboard'))

    cur.execute(
        '''
        INSERT INTO rooms (room_number, room_type, price_per_night, capacity)
        VALUES (%s, %s, %s, %s)
        ''',
        (room_number, room_type, price_val, capacity_val),
    )
    mysql.connection.commit()
    cur.close()
    flash('Room added successfully.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/room/<int:room_id>/delete', methods=['POST'])
@role_required('admin')
def delete_room(room_id):
    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT COUNT(*) AS active_count FROM bookings WHERE room_id = %s AND status = 'booked'",
        (room_id,),
    )
    active_count = cur.fetchone()['active_count']

    if active_count > 0:
        cur.close()
        flash('Cannot delete room with active bookings.', 'danger')
        return redirect(url_for('admin_dashboard'))

    cur.execute('DELETE FROM rooms WHERE id = %s', (room_id,))
    mysql.connection.commit()
    cur.close()
    flash('Room removed successfully.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/customer/dashboard')
@role_required('customer')
def customer_dashboard():
    capacity_needed = request.args.get('capacity', '').strip()
    selected_check_in = request.args.get('check_in_date', '').strip()
    selected_check_out = request.args.get('check_out_date', '').strip()

    params = []
    room_query = 'SELECT * FROM rooms WHERE 1 = 1'

    if capacity_needed:
        room_query += ' AND capacity >= %s'
        params.append(capacity_needed)

    room_query += ' ORDER BY price_per_night ASC'

    cur = mysql.connection.cursor()
    cur.execute(room_query, tuple(params))
    rooms = cur.fetchall()

    cur.execute(
        '''
        SELECT b.id, r.room_number, r.room_type, r.price_per_night,
               b.check_in_date, b.check_out_date, b.total_price, b.status
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.user_id = %s
        ORDER BY b.created_at DESC
        ''',
        (g.user['id'],),
    )
    bookings = cur.fetchall()
    cur.close()

    return render_template(
        'customer_dashboard.html',
        rooms=rooms,
        bookings=bookings,
        selected_check_in=selected_check_in,
        selected_check_out=selected_check_out,
        selected_capacity=capacity_needed,
    )


@app.route('/customer/book', methods=['POST'])
@role_required('customer')
def book_room():
    room_id = request.form.get('room_id')
    check_in = request.form.get('check_in_date', '').strip()
    check_out = request.form.get('check_out_date', '').strip()

    if not room_id or not check_in or not check_out:
        flash('Please select room and dates.', 'danger')
        return redirect(url_for('customer_dashboard'))

    try:
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()

        if check_in_date >= check_out_date:
            flash('Check-out date must be after check-in date.', 'danger')
            return redirect(url_for('customer_dashboard'))

        if check_in_date < datetime.utcnow().date():
            flash('Check-in date cannot be in the past.', 'danger')
            return redirect(url_for('customer_dashboard'))
    except ValueError:
        flash('Invalid date format.', 'danger')
        return redirect(url_for('customer_dashboard'))

    cur = mysql.connection.cursor()

    cur.execute('SELECT * FROM rooms WHERE id = %s', (room_id,))
    room = cur.fetchone()
    if room is None:
        cur.close()
        flash('Selected room does not exist.', 'danger')
        return redirect(url_for('customer_dashboard'))

    cur.execute(
        '''
        SELECT id FROM bookings
        WHERE room_id = %s
          AND status = 'booked'
          AND check_in_date < %s
          AND check_out_date > %s
        ''',
        (room_id, check_out_date, check_in_date),
    )

    if cur.fetchone():
        cur.close()
        flash('Room is not available for the selected dates.', 'warning')
        return redirect(url_for('customer_dashboard'))

    nights = (check_out_date - check_in_date).days
    total_price = nights * float(room['price_per_night'])

    cur.execute(
        '''
        INSERT INTO bookings (user_id, room_id, check_in_date, check_out_date, total_price, status)
        VALUES (%s, %s, %s, %s, %s, 'booked')
        ''',
        (g.user['id'], room_id, check_in_date, check_out_date, total_price),
    )
    mysql.connection.commit()
    cur.close()

    flash('Room booked successfully.', 'success')
    return redirect(url_for('customer_dashboard'))


@app.route('/customer/booking/<int:booking_id>/cancel', methods=['POST'])
@role_required('customer')
def cancel_booking(booking_id):
    cur = mysql.connection.cursor()
    cur.execute(
        '''
        SELECT id, check_in_date, status FROM bookings
        WHERE id = %s AND user_id = %s
        ''',
        (booking_id, g.user['id']),
    )
    booking = cur.fetchone()

    if booking is None:
        cur.close()
        flash('Booking not found.', 'danger')
        return redirect(url_for('customer_dashboard'))

    if booking['status'] != 'booked':
        cur.close()
        flash('This booking is already cancelled.', 'info')
        return redirect(url_for('customer_dashboard'))

    if booking['check_in_date'] <= datetime.utcnow().date():
        cur.close()
        flash('You can only cancel before check-in date.', 'warning')
        return redirect(url_for('customer_dashboard'))

    cur.execute("UPDATE bookings SET status = 'cancelled' WHERE id = %s", (booking_id,))
    mysql.connection.commit()
    cur.close()
    flash('Booking cancelled successfully.', 'success')
    return redirect(url_for('customer_dashboard'))


if __name__ == '__main__':
    app.run(debug=True)
