from flask import Flask, render_template, request, redirect, url_for, session, jsonify, json
import database as db
import os
import ssl
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Добавьте custom filter для Jinja2
@app.template_filter('from_json')
def from_json_filter(value):
    return json.loads(value)

# Инициализация базы данных
db.init_db()
db.init_upload_folder()

@app.route('/')
def index():
    search_query = request.args.get('search', '')
    if search_query:
        products = db.search_products(search_query)
    else:
        products = db.get_all_products()
    
    # Получаем количество товаров в корзине
    cart_count = 0
    if 'user_id' in session:
        cart_items = db.get_cart_items(session['user_id'])
        cart_count = sum(item['quantity'] for item in cart_items)
    
    return render_template('index.html', products=products, search_query=search_query, cart_count=cart_count)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = db.get_product_by_id(product_id)
    if not product:
        return "Товар не найден", 404
    
    # Получаем количество товаров в корзине
    cart_count = 0
    if 'user_id' in session:
        cart_items = db.get_cart_items(session['user_id'])
        cart_count = sum(item['quantity'] for item in cart_items)
    
    # Преобразуем строки в списки
    features = product['features'].split('\n') if product['features'] else []
    images = product['images'].split('\n') if product['images'] else []
    
    return render_template('product.html', product=product, features=features, images=images, cart_count=cart_count)

@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходимо авторизоваться'})
    
    product_id = request.form.get('product_id')
    quantity = int(request.form.get('quantity', 1))
    
    db.add_to_cart(session['user_id'], product_id, quantity)
    return jsonify({'success': True, 'message': 'Товар добавлен в корзину'})

@app.route('/get_cart_count')
def get_cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    
    cart_items = db.get_cart_items(session['user_id'])
    total_items = sum(item['quantity'] for item in cart_items)
    return jsonify({'count': total_items})

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cart_items = db.get_cart_items(session['user_id'])
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Получаем количество товаров в корзине
    cart_count = sum(item['quantity'] for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total_price=total_price, cart_count=cart_count)

@app.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходимо авторизоваться'})
    
    product_id = request.form.get('product_id')
    db.remove_from_cart(session['user_id'], product_id)
    
    return jsonify({'success': True, 'message': 'Товар удален из корзины'})

@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходимо авторизоваться'})
    
    cart_items = db.get_cart_items(session['user_id'])
    if not cart_items:
        return jsonify({'success': False, 'message': 'Корзина пуста'})
    
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    
    # Получаем адрес пользователя
    user = db.get_user_by_id(session['user_id'])
    address = user['address']
    
    # Формируем список товаров для заказа
    products = []
    for item in cart_items:
        products.append({
            'product_id': item['product_id'],
            'name': item['name'],
            'price': item['price'],
            'quantity': item['quantity']
        })
    
    # Создаем заказ
    order_id = db.create_order(session['user_id'], products, total_price, address)
    
    # Очищаем корзину
    db.clear_cart(session['user_id'])
    
    return jsonify({'success': True, 'message': 'Заказ оформлен', 'order_id': order_id})

@app.route('/orders')
def orders():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_orders = db.get_user_orders(session['user_id'])
    
    # Получаем количество товаров в корзине
    cart_count = 0
    if 'user_id' in session:
        cart_items = db.get_cart_items(session['user_id'])
        cart_count = sum(item['quantity'] for item in cart_items)
    
    return render_template('orders.html', orders=user_orders, cart_count=cart_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = db.verify_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            
            if user['role'] == 'seller':
                return redirect(url_for('seller_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            # Получаем количество товаров в корзине
            cart_count = 0
            if 'user_id' in session:
                cart_items = db.get_cart_items(session['user_id'])
                cart_count = sum(item['quantity'] for item in cart_items)
                
            return render_template('login.html', error='Неверный email или пароль', cart_count=cart_count)
    
    # Получаем количество товаров в корзине
    cart_count = 0
    if 'user_id' in session:
        cart_items = db.get_cart_items(session['user_id'])
        cart_count = sum(item['quantity'] for item in cart_items)
        
    return render_template('login.html', cart_count=cart_count)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        address = request.form.get('address')
        role = request.form.get('role', 'customer')
        
        user_id = db.create_user(email, password, name, address, role)
        if user_id:
            session['user_id'] = user_id
            session['user_email'] = email
            session['user_name'] = name
            session['user_role'] = role
            
            if role == 'seller':
                return redirect(url_for('seller_dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            # Получаем количество товаров в корзине
            cart_count = 0
            if 'user_id' in session:
                cart_items = db.get_cart_items(session['user_id'])
                cart_count = sum(item['quantity'] for item in cart_items)
                
            return render_template('register.html', error='Пользователь с таким email уже существует', cart_count=cart_count)
    
    # Получаем количество товаров в корзине
    cart_count = 0
    if 'user_id' in session:
        cart_items = db.get_cart_items(session['user_id'])
        cart_count = sum(item['quantity'] for item in cart_items)
        
    return render_template('register.html', cart_count=cart_count)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/seller/dashboard')
def seller_dashboard():
    if 'user_id' not in session or session['user_role'] != 'seller':
        return redirect(url_for('login'))
    
    # Получаем заказы для товаров продавца
    orders = db.get_seller_orders(session['user_id'])
    
    # Получаем количество товаров в корзине
    cart_count = 0
    if 'user_id' in session:
        cart_items = db.get_cart_items(session['user_id'])
        cart_count = sum(item['quantity'] for item in cart_items)
    
    return render_template('seller_dashboard.html', orders=orders, cart_count=cart_count)

@app.route('/seller/add_product', methods=['POST'])
def add_product():
    if 'user_id' not in session or session['user_role'] != 'seller':
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        name = request.form.get('name')
        price = float(request.form.get('price'))
        description = request.form.get('description')
        features = request.form.get('features')
        
        # Проверяем обязательные поля
        if not all([name, price, description, features]):
            return jsonify({'success': False, 'message': 'Все поля обязательны для заполнения'})
        
        # Обрабатываем загрузку изображений
        images = request.files.getlist('images')
        image_paths = db.save_uploaded_images(images)
        
        # Если нет изображений, используем заглушку
        if not image_paths:
            image_paths = ['/static/images/placeholder.jpg']
        
        # Сохраняем пути к изображениям как строку с разделителем
        images_str = '\n'.join(image_paths)
        
        product_id = db.add_product(name, price, description, features, images_str, session['user_id'])
        
        return jsonify({'success': True, 'message': 'Товар добавлен', 'product_id': product_id})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка при добавлении товара: {str(e)}'})
@app.route('/seller/update_order_status', methods=['POST'])
def update_order_status():
    if 'user_id' not in session or session['user_role'] != 'seller':
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    order_id = request.form.get('order_id')
    status = request.form.get('status')
    
    db.update_order_status(order_id, status)
    
    return jsonify({'success': True, 'message': 'Статус заказа обновлен'})

if __name__ == '__main__':
    # Генерируем SSL сертификат (если нет)
    if not os.path.exists('static/uploads'):
      os.makedirs('static/uploads')
    if not os.path.exists('static/images'):
      os.makedirs('static/images')
    if not os.path.exists('ssl/certificate.pem') or not os.path.exists('ssl/private.key'):
        os.makedirs('ssl', exist_ok=True)
        # Генерация самоподписанного сертификата (для разработки)
        os.system('openssl req -x509 -newkey rsa:4096 -nodes -out ssl/certificate.pem -keyout ssl/private.key -days 365 -subj "/CN=localhost"')
    
    # Запускаем приложение с HTTPS
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
    context.load_cert_chain('ssl/certificate.pem', 'ssl/private.key')
    
    app.run(host='0.0.0.0', port=443, ssl_context=context, debug=True)