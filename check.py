import sqlite3
import hashlib
from flask import Flask, render_template, request, jsonify, g

DATABASE = 'database.db'

app = Flask(__name__)


# --- Управление подключением к БД ---

def get_db():
    """Открывает новое подключение к БД, если его еще нет для текущего запроса."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        # Эта строка позволяет получать результаты из БД в виде словарей, а не кортежей
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    """Закрывает подключение к БД после обработки запроса."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


# --- Вспомогательные функции ---

def query_db(query, args=(), one=False):
    """Вспомогательная функция для выполнения запросов к БД."""
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def hash_password(password):
    """Хэширует пароль так же, как в вашем database.py."""
    s = "moy_secret_sol_2024"
    return hashlib.sha256((password + s).encode()).hexdigest()


# --- МАРШРУТЫ ---

@app.route('/')
def index():
    """Отдает вашу главную HTML-страницу."""
    return render_template('index.html')


# --- API МАРШРУТЫ ---

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({"success": False, "error": "Заполните все поля"}), 400

    # Проверяем, не занят ли email
    user = query_db('SELECT * FROM users WHERE email = ?', [data['email']], one=True)
    if user:
        return jsonify({"success": False, "error": "Пользователь с таким email уже существует"}), 400

    # Хэшируем пароль
    password_hash = hash_password(data['password'])

    # Сохраняем нового пользователя
    db_connection = get_db()
    cursor = db_connection.cursor()
    cursor.execute(
        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
        (data['name'], data['email'], password_hash)
    )
    db_connection.commit()

    # Получаем только что созданного пользователя, чтобы вернуть его данные
    new_user_id = cursor.lastrowid
    new_user_data = query_db('SELECT * FROM users WHERE id = ?', [new_user_id], one=True)

    # Преобразуем Row-объект в словарь
    user_dict = dict(new_user_data)
    # Удаляем хэш пароля перед отправкой клиенту
    del user_dict['password_hash']

    # В вашем JS коде username, а в БД username
    user_dict['name'] = user_dict['username']

    return jsonify({"success": True, "user": user_dict}), 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"success": False, "error": "Не указан email или пароль"}), 400

    # Ищем пользователя по email
    user = query_db('SELECT * FROM users WHERE email = ?', [data['email']], one=True)

    # Хэшируем введенный пароль для сравнения
    password_hash = hash_password(data['password'])

    # Проверяем, найден ли пользователь и совпадает ли хэш пароля
    if not user or user['password_hash'] != password_hash:
        return jsonify({"success": False, "error": "Неверный email или пароль"}), 401

    if not user['is_active']:
        return jsonify({"success": False, "error": "Этот аккаунт заблокирован"}), 403

    # Преобразуем Row-объект в словарь для отправки
    user_dict = dict(user)
    del user_dict['password_hash']

    # В вашем JS коде username, а в БД username
    user_dict['name'] = user_dict['username']

    return jsonify({"success": True, "user": user_dict})


# --- ЗАПУСК ПРИЛОЖЕНИЯ ---

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)