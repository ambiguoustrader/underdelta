import sqlite3
import hashlib
from flask import Flask, render_template, request, jsonify, g, abort

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


BOSS_SLUGS = {
    "lancer": "Lancer",
    "spamton": "Spamton NEO",
    "sans": "Sans",
}


def hash_password(password):
    """Хэширует пароль так же, как в вашем database.py."""
    s = "moy_secret_sol_2024"
    return hashlib.sha256((password + s).encode()).hexdigest()


def build_user_payload(user_id: int) -> dict | None:
    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    if not user:
        return None

    user_dict = dict(user)
    user_dict.pop('password_hash', None)
    user_dict['name'] = user_dict['username']

    achievements = query_db(
        'SELECT achievement_id FROM user_achievements WHERE user_id = ?',
        [user_id]
    )
    user_dict['achievements'] = [row['achievement_id'] for row in achievements]

    bosses_defeated = query_db(
        'SELECT COUNT(*) AS cnt FROM user_boss_progress WHERE user_id = ? AND is_defeated = 1',
        [user_id],
        one=True
    )
    user_dict['bosses_defeated'] = bosses_defeated['cnt'] if bosses_defeated else 0

    history_rows = query_db(
        'SELECT action_text, action_date FROM user_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 8',
        [user_id]
    )
    user_dict['history'] = [
        {
            'action_text': row['action_text'],
            'action_date': row['action_date'],
        }
        for row in history_rows
    ]

    return user_dict


def give_achievement(user_id: int, achievement_id: str) -> None:
    db = get_db()
    db.execute(
        '''
        INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
        VALUES (?, ?)
        ''',
        (user_id, achievement_id)
    )
    db.commit()


# --- МАРШРУТЫ ---

@app.route('/')
def index():
    """Отдает вашу главную HTML-страницу."""
    return render_template('index.html')


@app.route('/api/user/<int:user_id>', methods=['GET'])
def api_get_user(user_id: int):
    user_data = build_user_payload(user_id)
    if not user_data:
        return jsonify({"error": "Пользователь не найден"}), 404
    return jsonify(user_data)


@app.route('/boss/<slug>')
def boss_page(slug):
    boss_name = BOSS_SLUGS.get(slug)
    if not boss_name:
        abort(404)

    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        [boss_name],
        one=True
    )

    if not boss:
        abort(404)

    return render_template('boss_page.html', boss=dict(boss), slug=slug)


@app.route('/api/bosses/<slug>/complete', methods=['POST'])
def api_complete_boss(slug: str):
    boss_name = BOSS_SLUGS.get(slug)
    if not boss_name:
        return jsonify({"error": "Босс не найден"}), 404

    data = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({"error": "Не указан user_id"}), 400

    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        [boss_name],
        one=True
    )
    if not boss:
        return jsonify({"error": "Босс не найден в БД"}), 404

    db = get_db()

    progress = query_db(
        'SELECT * FROM user_boss_progress WHERE user_id = ? AND boss_id = ?',
        [user_id, boss['id']],
        one=True
    )

    first_victory = progress is None or progress['is_defeated'] == 0

    if progress is None:
        db.execute(
            '''
            INSERT INTO user_boss_progress (
                user_id, boss_id, is_defeated, attempts, first_victory_at, last_attempt_at
            )
            VALUES (?, ?, 1, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''',
            (user_id, boss['id'])
        )
    else:
        db.execute(
            '''
            UPDATE user_boss_progress
            SET is_defeated = 1,
                attempts = attempts + 1,
                first_victory_at = CASE
                    WHEN first_victory_at IS NULL THEN CURRENT_TIMESTAMP
                    ELSE first_victory_at
                END,
                last_attempt_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND boss_id = ?
            ''',
            (user_id, boss['id'])
        )

    if first_victory:
        db.execute(
            '''
            UPDATE users
            SET xp = xp + ?, wins = wins + 1
            WHERE id = ?
            ''',
            (boss['reward_xp'], user_id)
        )

        if slug == 'sans':
            give_achievement(user_id, 'boss_sans')

        defeated_count = query_db(
            'SELECT COUNT(*) AS cnt FROM user_boss_progress WHERE user_id = ? AND is_defeated = 1',
            [user_id],
            one=True
        )['cnt']

        if defeated_count >= 3:
            give_achievement(user_id, 'all_bosses')

        db.execute(
            '''
            INSERT INTO user_history (user_id, action_text, action_date)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ''',
            (user_id, f'Победил босса {boss_name}')
        )

    db.commit()

    user_data = build_user_payload(user_id)
    return jsonify({
        "success": True,
        "first_victory": first_victory,
        "user": user_data
    })

@app.route('/lancer')
def lancer_page():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        ['Lancer'],
        one=True
    )

    if not boss:
        abort(404)

    return render_template('boss_page.html', boss=dict(boss), slug='lancer')


@app.route('/spamton')
def spamton_page():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        ['Spamton NEO'],
        one=True
    )

    if not boss:
        abort(404)

    return render_template('boss_page.html', boss=dict(boss), slug='spamton')

@app.route('/sans')
def sans_page():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        ['Sans'],
        one=True
    )

    if not boss:
        abort(404)

    return render_template('boss_page.html', boss=dict(boss), slug='sans')


@app.route('/sans-simulator')
def sans_simulator():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        ['Sans'],
        one=True
    )

    if not boss:
        abort(404)

    return render_template('sans_simulator.html', boss=dict(boss))


# --- API МАРШРУТЫ ---

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({"success": False, "error": "Заполните все поля"}), 400

    user = query_db('SELECT * FROM users WHERE email = ?', [data['email']], one=True)
    if user:
        return jsonify({"success": False, "error": "Пользователь с таким email уже существует"}), 400

    password_hash = hash_password(data['password'])

    db_connection = get_db()
    cursor = db_connection.cursor()
    cursor.execute(
        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
        (data['name'], data['email'], password_hash)
    )
    db_connection.commit()

    new_user_id = cursor.lastrowid
    full_user = build_user_payload(new_user_id)

    return jsonify({"success": True, "user": full_user}), 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"success": False, "error": "Не указан email или пароль"}), 400

    user = query_db('SELECT * FROM users WHERE email = ?', [data['email']], one=True)
    password_hash = hash_password(data['password'])

    if not user or user['password_hash'] != password_hash:
        return jsonify({"success": False, "error": "Неверный email или пароль"}), 401

    if not user['is_active']:
        return jsonify({"success": False, "error": "Этот аккаунт заблокирован"}), 403

    full_user = build_user_payload(user['id'])
    return jsonify({"success": True, "user": full_user})


# --- ЗАПУСК ПРИЛОЖЕНИЯ ---

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)
