import sqlite3
import hashlib
import os
from datetime import datetime

import os
import uuid
from werkzeug.utils import secure_filename

# Добавьте эти настройки в начало файла
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
def get_product_with_images(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if product and product['images']:
        # Преобразуем строку с путями в список
        images = product['images'].split('\n')
        # Создаем копию продукта с правильными путями к изображениям
        product_dict = dict(product)
        product_dict['images_list'] = images
        conn.close()
        return product_dict
    
    conn.close()
    return product

def get_product_with_images(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    
    if product and product['images']:
        # Преобразуем строку с путями в список
        images = product['images'].split('\n')
        # Создаем копию продукта с правильными путями к изображениям
        product_dict = dict(product)
        product_dict['images_list'] = images
        conn.close()
        return product_dict
    
    conn.close()
    return product

def get_user_by_id(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
def init_upload_folder():
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_images(files):
    """Сохраняет загруженные изображения и возвращает список путей"""
    image_paths = []
    
    for file in files:
        if file and allowed_file(file.filename):
            # Генерируем уникальное имя файла
            filename = secure_filename(file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            
            # Сохраняем файл
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            
            # Добавляем относительный путь
            image_paths.append(f"/{file_path}")
    
    return image_paths

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
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
        ''')
        
        # Создание таблицы заказов
        cursor.execute('''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            products TEXT NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'payment',
            address TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')
        
        conn.commit()
        conn.close()

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

def create_order(user_id, products, total_price, address):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Преобразуем список товаров в строку JSON
    import json
    products_json = json.dumps(products)
    
    cursor.execute(
        'INSERT INTO orders (user_id, products, total_price, address) VALUES (?, ?, ?, ?)',
        (user_id, products_json, total_price, address)
    )
    conn.commit()
    order_id = cursor.lastrowid
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

def update_order_status(order_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        'UPDATE orders SET status = ?, updated_at = ? WHERE id = ?',
        (status, datetime.now(), order_id)
    )
    conn.commit()
    conn.close()
