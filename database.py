import sqlite3
import hashlib
import os
import uuid
import json
import random
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from PIL import Image
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets

def get_db_connection():
    conn = sqlite3.connect('products.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if not os.path.exists('products.db'):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Создание таблицы пользователей
        cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            address TEXT,
            role TEXT NOT NULL DEFAULT 'customer',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Создание таблицы товаров
        cursor.execute('''
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT,
            features TEXT,
            images TEXT,
            seller_id INTEGER NOT NULL,
            rating REAL DEFAULT 0,
            reviews_count INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (seller_id) REFERENCES users (id)
        )
        ''')
        
        # Создание таблицы корзин
        cursor.execute('''
        CREATE TABLE carts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            selected BOOLEAN DEFAULT 1,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
        ''')
        
        # Создание таблицы заказов
        cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            products TEXT NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'payment',
            verification_code TEXT,
            address TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Создание таблицы отзывов
        cursor.execute('''
        CREATE TABLE reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Создание таблицы сброса пароля
        cursor.execute('''
        CREATE TABLE password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT NOT NULL,
            expires_at DATETIME NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        # Создание таблицы уведомлений
        cursor.execute('''
        CREATE TABLE notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            order_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (order_id) REFERENCES orders (id)
        )
        ''')
        
        # Добавляем тестового продавца
        hashed_password = hash_password('seller123')
        cursor.execute(
            'INSERT INTO users (email, password, name, address, role) VALUES (?, ?, ?, ?, ?)',
            ('seller@example.com', hashed_password, 'Тестовый Продавец', 'Москва, ул. Тверская, 1', 'seller')
        )
        
        # Добавляем тестового покупателя
        hashed_password = hash_password('customer123')
        cursor.execute(
            'INSERT INTO users (email, password, name, address, role) VALUES (?, ?, ?, ?, ?)',
            ('customer@example.com', hashed_password, 'Тестовый Покупатель', 'Санкт-Петербург, Невский пр., 10', 'customer')
        )
        
        conn.commit()
        conn.close()

def init_upload_folder():
    if not os.path.exists('static/uploads'):
        os.makedirs('static/uploads')
    if not os.path.exists('static/images'):
        os.makedirs('static/images')

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(email, password, name, address, role='customer'):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    try:
        cursor.execute(
            'INSERT INTO users (email, password, name, address, role) VALUES (?, ?, ?, ?, ?)',
            (email, hashed_password, name, address, role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None

def get_user_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def verify_user(email, password):
    user = get_user_by_email(email)
    if user and user['password'] == hash_password(password):
        return user
    return None

def add_product(name, price, description, features, images, seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO products (name, price, description, features, images, seller_id) VALUES (?, ?, ?, ?, ?, ?)',
        (name, price, description, features, images, seller_id)
    )
    conn.commit()
    product_id = cursor.lastrowid
    conn.close()
    return product_id

def get_all_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products')
    products = cursor.fetchall()
    conn.close()
    return products

def get_product_by_id(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def search_products(query):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE name LIKE ?', ('%' + query + '%',))
    products = cursor.fetchall()
    conn.close()
    return products

def get_products_with_filters(min_price=None, max_price=None, sort_by='name', sort_order='asc'):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM products WHERE 1=1'
    params = []
    
    if min_price is not None:
        query += ' AND price >= ?'
        params.append(min_price)
    
    if max_price is not None:
        query += ' AND price <= ?'
        params.append(max_price)
    
    # Сортировка
    if sort_by == 'price':
        query += ' ORDER BY price'
    elif sort_by == 'rating':
        query += ' ORDER BY rating'
    elif sort_by == 'reviews':
        query += ' ORDER BY reviews_count'
    else:
        query += ' ORDER BY name'
    
    if sort_order == 'desc':
        query += ' DESC'
    else:
        query += ' ASC'
    
    cursor.execute(query, params)
    products = cursor.fetchall()
    conn.close()
    return products

def add_to_cart(user_id, product_id, quantity=1):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже товар в корзине
    cursor.execute(
        'SELECT * FROM carts WHERE user_id = ? AND product_id = ?',
        (user_id, product_id)
    )
    existing_item = cursor.fetchone()
    
    if existing_item:
        # Обновляем количество
        cursor.execute(
            'UPDATE carts SET quantity = quantity + ? WHERE user_id = ? AND product_id = ?',
            (quantity, user_id, product_id)
        )
    else:
        # Добавляем новый товар
        cursor.execute(
            'INSERT INTO carts (user_id, product_id, quantity) VALUES (?, ?, ?)',
            (user_id, product_id, quantity)
        )
    
    conn.commit()
    conn.close()

def get_cart_items(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT carts.*, products.name, products.price, products.images 
        FROM carts 
        JOIN products ON carts.product_id = products.id 
        WHERE user_id = ?
    ''', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def get_selected_cart_items(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT carts.*, products.name, products.price, products.images 
        FROM carts 
        JOIN products ON carts.product_id = products.id 
        WHERE user_id = ? AND selected = 1
    ''', (user_id,))
    items = cursor.fetchall()
    conn.close()
    return items

def remove_from_cart(user_id, product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM carts WHERE user_id = ? AND product_id = ?',
        (user_id, product_id)
    )
    conn.commit()
    conn.close()

def clear_cart(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM carts WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def clear_selected_cart_items(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM carts WHERE user_id = ? AND selected = 1', (user_id,))
    conn.commit()
    conn.close()

def update_cart_item_selection(user_id, product_id, selected):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE carts SET selected = ? WHERE user_id = ? AND product_id = ?',
        (selected, user_id, product_id)
    )
    conn.commit()
    conn.close()

def update_cart_quantity(user_id, product_id, quantity):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if quantity <= 0:
        cursor.execute(
            'DELETE FROM carts WHERE user_id = ? AND product_id = ?',
            (user_id, product_id)
        )
    else:
        cursor.execute(
            'UPDATE carts SET quantity = ? WHERE user_id = ? AND product_id = ?',
            (quantity, user_id, product_id)
        )
    
    conn.commit()
    conn.close()

def generate_order_number(user_id, order_id):
    """Генерация случайного номера заказа"""
    timestamp = int(datetime.now().timestamp())
    random_part = random.randint(1000, 9999)
    return f"ORD-{timestamp}-{user_id}-{order_id}-{random_part}"

def generate_verification_code():
    """Генерация 6-значного кода подтверждения"""
    return str(random.randint(100000, 999999))

def create_order(user_id, products, total_price, address):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Преобразуем список товаров в строку JSON
    products_json = json.dumps(products)
    
    # Сначала создаем заказ чтобы получить ID
    cursor.execute(
        'INSERT INTO orders (user_id, products, total_price, address, order_number) VALUES (?, ?, ?, ?, ?)',
        (user_id, products_json, total_price, address, 'temp')
    )
    order_id = cursor.lastrowid
    
    # Генерируем номер заказа
    order_number = generate_order_number(user_id, order_id)
    
    # Обновляем номер заказа
    cursor.execute(
        'UPDATE orders SET order_number = ? WHERE id = ?',
        (order_number, order_id)
    )
    
    conn.commit()
    conn.close()
    return order_id

def get_user_orders(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

def get_seller_orders(seller_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT orders.* 
        FROM orders 
        JOIN products ON JSON_EXTRACT(orders.products, '$[0].product_id') = products.id 
        WHERE products.seller_id = ?
        ORDER BY orders.created_at DESC
    ''', (seller_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders
    
def get_order_by_id(order_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders WHERE id = ?', (order_id,))
    order = cursor.fetchone()
    conn.close()
    return order

def update_order_status(order_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Если статус "delivery", генерируем код подтверждения
    verification_code = None
    if status == 'delivery':
        verification_code = generate_verification_code()
        cursor.execute(
            'UPDATE orders SET status = ?, verification_code = ?, updated_at = ? WHERE id = ?',
            (status, verification_code, datetime.now(), order_id)
        )
    else:
        cursor.execute(
            'UPDATE orders SET status = ?, updated_at = ? WHERE id = ?',
            (status, datetime.now(), order_id)
        )
    
    conn.commit()
    conn.close()
    return verification_code

def verify_delivery_code(order_id, code):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT verification_code FROM orders WHERE id = ? AND status = "delivery"',
        (order_id,)
    )
    order = cursor.fetchone()
    
    if order and order['verification_code'] == code:
        cursor.execute(
            'UPDATE orders SET status = "received", verification_code = NULL, updated_at = ? WHERE id = ?',
            (datetime.now(), order_id)
        )
        conn.commit()
        conn.close()
        return True
    
    conn.close()
    return False

def add_review(product_id, user_id, rating, comment):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Добавляем отзыв
    cursor.execute(
        'INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)',
        (product_id, user_id, rating, comment)
    )
    
    # Обновляем рейтинг товара
    cursor.execute('''
        UPDATE products 
        SET rating = (
            SELECT AVG(rating) FROM reviews WHERE product_id = ?
        ),
        reviews_count = (
            SELECT COUNT(*) FROM reviews WHERE product_id = ?
        )
        WHERE id = ?
    ''', (product_id, product_id, product_id))
    
    conn.commit()
    conn.close()

def get_product_reviews(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reviews.*, users.name as user_name 
        FROM reviews 
        JOIN users ON reviews.user_id = users.id 
        WHERE product_id = ? 
        ORDER BY created_at DESC
    ''', (product_id,))
    reviews = cursor.fetchall()
    conn.close()
    return reviews

def add_notification(user_id, order_id, message):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO notifications (user_id, order_id, message) VALUES (?, ?, ?)',
        (user_id, order_id, message)
    )
    conn.commit()
    conn.close()

def get_user_notifications(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT notifications.*, orders.order_number 
        FROM notifications 
        JOIN orders ON notifications.order_id = orders.id 
        WHERE notifications.user_id = ? 
        ORDER BY notifications.created_at DESC
    ''', (user_id,))
    notifications = cursor.fetchall()
    conn.close()
    return notifications
    
def mark_notification_as_read(notification_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE notifications SET is_read = 1 WHERE id = ?',
        (notification_id,)
    )
    conn.commit()
    conn.close()

def get_unread_notifications_count(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0',
        (user_id,)
    )
    count = cursor.fetchone()['count']
    conn.close()
    return count
    
def generate_reset_token():
    return secrets.token_urlsafe(32)

def save_reset_token(user_id, token):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Удаляем старые токены
    cursor.execute('DELETE FROM password_resets WHERE user_id = ?', (user_id,))
    
    # Сохраняем новый токен
    expires_at = datetime.now() + timedelta(hours=1)
    cursor.execute(
        'INSERT INTO password_resets (user_id, token, expires_at) VALUES (?, ?, ?)',
        (user_id, token, expires_at)
    )
    
    conn.commit()
    conn.close()

def get_user_by_reset_token(token):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT users.* FROM users JOIN password_resets ON users.id = password_resets.user_id WHERE token = ? AND expires_at > ?',
        (token, datetime.now())
    )
    user = cursor.fetchone()
    conn.close()
    return user

def update_password(user_id, new_password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(new_password)
    cursor.execute(
        'UPDATE users SET password = ? WHERE id = ?',
        (hashed_password, user_id)
    )
    
    # Удаляем использованный токен
    cursor.execute('DELETE FROM password_resets WHERE user_id = ?', (user_id,))
    
    conn.commit()
    conn.close()

def send_password_reset_email(email, reset_url):
    # Настройки SMTP (замените на свои)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = "your_email@gmail.com"
    smtp_password = "your_app_password"
    
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = email
    msg['Subject'] = "Восстановление пароля - SunshineStore"
    
    body = f"""
    <h2>Восстановление пароля</h2>
    <p>Для восстановления пароля перейдите по ссылке:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>Ссылка действительна в течение 1 часа.</p>
    <p>Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.</p>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def process_and_save_image(file):
    """Обрабатывает и сохраняет изображение с обрезкой до 800x600"""
    if file and allowed_file(file.filename):
        # Генерируем уникальное имя файла
        filename = secure_filename(file.filename)
        file_extension = filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        
        # Сохраняем файл
        file_path = os.path.join('static/uploads', unique_filename)
        
        # Обрабатываем изображение
        try:
            image = Image.open(file)
            
            # Конвертируем в RGB если нужно
            if image.mode in ('RGBA', 'P'):
                image = image.convert('RGB')
            
            # Обрезаем до 800x600 с сохранением пропорций
            image.thumbnail((800, 600))
            image.save(file_path, 'JPEG' if file_extension == 'jpg' else file_extension.upper())
            
            return f"/static/uploads/{unique_filename}"
        except Exception as e:
            print(f"Error processing image: {e}")
            return None
    
    return None

def save_uploaded_images(files):
    """Сохраняет загруженные изображения (максимум 5)"""
    image_paths = []
    
    for i, file in enumerate(files):
        if i >= 5:  # Максимум 5 изображений
            break
            
        if file and file.filename:  # Проверяем что файл не пустой
            image_path = process_and_save_image(file)
            if image_path:
                image_paths.append(image_path)
    
    return image_paths
