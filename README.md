# Hotel Management Website (Flask + MySQL)

A role-based hotel management system built with:
- **Frontend:** HTML, CSS, JS
- **Backend:** Flask (Python)
- **Database:** MySQL

## Flow
1. User lands on home page.
2. User registers or logs in.
3. Based on role:
   - **Admin** → Admin dashboard.
   - **Customer/User** → Customer dashboard.

## Features

### Admin
- Add room
- Remove room (only if no active booking exists)
- View all rooms
- View all bookings (with customer names and status)
- Quick stats: total rooms, total bookings, active bookings

### Customer/User
- See available rooms
- Filter rooms by capacity and dates
- Book a room with check-in and check-out
- See only **their own** bookings
- Cancel booking before check-in date

## Extra feature added (recommended)
**Smart overlap-safe booking + cancellation window**
- The system checks if selected dates overlap an existing active booking for the same room.
- If overlap exists, booking is rejected.
- Customers can cancel only before the check-in date.

This improves data integrity and avoids double-booking.

## Setup

### 1) Install dependencies
```bash
pip install -r requirements.txt
```

### 2) Create database and tables
```bash
mysql -u root -p < schema.sql
```

### 3) Set environment variables (optional but recommended)
```bash
export SECRET_KEY='super-secret-key'
export MYSQL_HOST='localhost'
export MYSQL_USER='root'
export MYSQL_PASSWORD='your_password'
export MYSQL_DB='hotel_management'
```

### 4) Run app
```bash
python app.py
```

Open: `http://127.0.0.1:5000`

## Suggested folder structure
```
HotelManagment/
├── app.py
├── requirements.txt
├── schema.sql
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── home.html
    ├── login.html
    ├── register.html
    ├── admin_dashboard.html
    └── customer_dashboard.html
```

