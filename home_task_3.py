from flask import Flask
from flask import request
import sqlite3

app = Flask(__name__)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


class DbReader:
    def __enter__(self):
        self.my_db = sqlite3.connect('identifier.sqlite')
        self.my_db.row_factory = dict_factory
        self.my_cursor = self.my_db.cursor()
        return self.my_cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.my_db.commit()
        self.my_db.close()


def read_database(table_name: str, selectors: dict = None):
    with DbReader() as my_cursor:
        cursor_string = f'SELECT * FROM {table_name}'
        if selectors:
            cursor_string += " WHERE "
            conditions = []
            vals = []
            for key, val in selectors.items():
                conditions.append(f'{key} = ?')
                vals.append(val)
            cursor_string += " AND ".join(conditions)
            my_cursor.execute(cursor_string, vals)
        else:
            my_cursor.execute(cursor_string)
        return my_cursor.fetchall()


def write_database(table_name: str, data: dict):
    with DbReader() as my_cursor:
        cursor_string = f'INSERT INTO {table_name} ({", ".join(data.keys())}) VALUES ({", ".join(["?"] * len(data))})'
        my_cursor.execute(cursor_string, list(data.values()))


def update_database(table_name: str, data, condition):
    with DbReader() as my_cursor:
        update_expression = ", ".join([str(key) + " = '" + str(val) + "'" for key, val in data.items()])
        cursor_string = f'UPDATE {table_name} SET {update_expression} WHERE {" and ".join([f"{key} = {val}" for key, val in condition.items()])}'
        my_cursor.execute(cursor_string)


def delete_data_from_database(table_name: str, selectors: dict):
    with DbReader() as my_cursor:
        cursor_string = f'DELETE FROM {table_name}'
        if selectors:
            cursor_string += " WHERE "
            conditions = []
            vals = []
            for key, val in selectors.items():
                conditions.append(f'{key} = ?')
                vals.append(val)
            cursor_string += " AND ".join(conditions)
            my_cursor.execute(cursor_string, vals)
        else:
            my_cursor.execute(cursor_string)
        return my_cursor.fetchall()


@app.route('/register', methods=['POST'])
def register_user():
    login = request.form['login']
    password = request.form['password']
    phone = request.form['phone']
    name = request.form['name']
    surname = request.form['surname']
    write_database('users', {'login': login, 'password': password, 'phone': phone, 'name': name, 'surname': surname})
    return f'User {login} was registered!'


@app.route('/login', methods=['POST'])
def login_user():
    login = request.form['login']
    password = request.form['password']
    user = read_database('users', {'login': login, 'password': password})
    if user:
        return f'User {login} was logged in!'
    else:
        return f'User {login} was not found or wrong password!'


@app.route('/user', methods=['PUT'])
def update_user():
    update_database('users', {'login': request.form['login'], 'password': request.form['password'],
                              'phone': request.form['phone'], 'name': request.form['name'],
                              'surname': request.form['surname']}, {'login': request.form['login']})


@app.route('/shop/items/<item_id>', methods=['GET'])
def item_info(item_id):
    return read_database('items', {'id': item_id})


@app.route('/shop/items/<item_id>/review', methods=['GET', 'POST'])
def item_review(item_id):
    if request.method == 'POST':
        write_database('feedbacks', {'item_id': item_id, 'text': request.form['feedback'],
                                     'rating': request.form['rating'], 'user_login': request.form['user_login']})
    return read_database('feedbacks', {'item_id': item_id})


@app.route('/shop/items/<item_id>/review/<review_id>', methods=['GET', 'PUT'])
def review_info(item_id, review_id):
    if request.method == 'PUT':
        update_database('feedbacks', {'text': request.form['feedback'], 'rating': request.form['rating']},
                        {'item_id': item_id, 'feedback_id': review_id})
    return read_database('feedbacks', {'item_id': item_id, 'feedback_id': review_id})


@app.route('/shop/items', methods=['GET'])
def all_items():
    return read_database('items')


@app.route('/shop/cart/<cart_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def cart(cart_id):
    if request.method == 'POST':
        write_database('cart', {'user_login': request.form['user_login'], 'item_id': request.form['item_id'],
                                'quantity': request.form['quantity']})
    elif request.method == 'PUT':
        update_database('cart', {'item_id': request.form['item_id'], 'quantity': request.form['quantity']},
                        {'cart_id': cart_id})
    elif request.method == 'DELETE':
        delete_data_from_database('cart', {'cart_id': cart_id})
    return read_database('cart', {'user_login': request.form['user_login']})


@app.route('/shop/cart/order', methods=['POST'])
def cart_order():
    if request.method == 'POST':
        user_login = request.form['user_login']
        user_cart = read_database('cart', {'user_login': user_login})
        user_address = request.form['user_address']
        total_price = 0
        for row in user_cart:
            delete_data_from_database('cart', {'cart_id': row['cart_id']})
            del row['cart_id']
            write_database('order_items', row)
            price_item = read_database('items', {'id': row['item_id']})
            total_price += float(price_item[0]['price']) * int(row['quantity'])
        write_database('orders', {'user_login': user_login, 'order_total_price': str(total_price),
                                  'address': user_address, 'status': 1})
        return read_database('orders', {'user_login': user_login})


@app.route('/shop/favorites', methods=['POST'])
def favorites():
    if request.method == 'POST':
        write_database('wishlist', {'item_id': request.form['item_id'], 'list_name': request.form['list_name'],
                                    'user_login': request.form['user_login']})
    return read_database('wishlist')


@app.route('/shop/favorites/<list_id>', methods=['GET', 'PUT'])
def favorite(list_id):
    if request.method == 'PUT':
        update_database('wishlist', {'list_id': list_id}, {'item_id': request.form['item_id']})
    return read_database('wishlist', {'list_id': list_id})


@app.route('/shop/waitlist/<list_id>', methods=['GET', 'PUT'])
def wailtist(list_id):
    if request.method == 'PUT':
        update_database('waitlist', {'list_id': list_id}, {'item_id': request.form['item_id']})
    return read_database('waitlist', {'list_id': list_id})


@app.route('/admin/items', methods=['GET', 'POST'])
def items():
    if request.method == 'POST':
        write_database('items',
                       {'name': request.form['name'], 'status': request.form['status'],
                        'category': request.form['category'], 'description': request.form['description'],
                        'price': request.form['price']})
    return read_database('items')


@app.route('/admin/items/<item_id>', methods=['GET', 'PUT', 'DELETE'])
def item(item_id):
    if request.method == 'PUT':
        update_database('items', {'name': request.form['name'],
                                  'status': request.form['status'],
                                  'category': request.form['category'],
                                  'description': request.form['description'],
                                  'price': request.form['price']},
                        {'id': item_id})
    elif request.method == 'DELETE':
        delete_data_from_database('items', {'id': item_id})
    return read_database('items', {'id': item_id})


@app.route('/admin/orders', methods=['GET'])
def orders():
    return read_database('orders')


@app.route('/admin/orders/<order_id>', methods=['PUT'])
def order(order_id):
    if request.method == 'PUT':
        update_database('orders', {'address': request.form['address'], 'status': request.form['status']},
                        {'order_id': order_id})


@app.route('/shop/compare', methods=['POST'])
def compare_list_create():
    if request.method == 'POST':
        write_database('compare', {'user_login': request.form['user_login'],
                                   'first_item_id': request.form['first_item_id'],
                                   'second_item_id': request.form['second_item_id']})
    return read_database('compare')


@app.route('/shop/compare/<cmp_id>', methods=['GET', 'POST', 'PUT'])
def compare(cmp_id):
    if request.method == 'PUT':
        update_database('compare', {'first_item_id': request.form['first_item_id'],
                                    'second_item_id': request.form['second_item_id']},
                        {'compare_id': cmp_id})
    return read_database('compare', {'compare_id': cmp_id})


app.run()
