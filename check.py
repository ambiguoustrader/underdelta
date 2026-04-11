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


@app.route('/api/leaderboard', methods=['GET'])
def api_leaderboard():
    filter_name = request.args.get('filter', 'rating')
    limit = request.args.get('limit', default=50, type=int)

    if limit is None:
        limit = 50

    limit = max(1, min(limit, 100))

    order_map = {
        'rating': 'u.rating DESC, u.level DESC, u.id ASC',
        'bosses': 'bosses_defeated DESC, u.rating DESC, u.level DESC, u.id ASC',
        'endless': 'best_endless_time DESC, u.rating DESC, u.level DESC, u.id ASC',
        'quiz': 'u.solved_count DESC, u.correct_count DESC, u.rating DESC, u.id ASC',
    }

    order_clause = order_map.get(filter_name, order_map['rating'])

    rows = query_db(f'''
        SELECT
            u.id,
            u.username,
            u.email,
            u.rating,
            u.level,
            u.xp,
            u.solved_count,
            u.correct_count,
            u.is_admin,
            COALESCE(bp.bosses_defeated, 0) AS bosses_defeated,
            COALESCE(er.best_endless_time, 0) AS best_endless_time
        FROM users u
        LEFT JOIN (
            SELECT
                user_id,
                COUNT(*) AS bosses_defeated
            FROM user_boss_progress
            WHERE is_defeated = 1
            GROUP BY user_id
        ) bp ON bp.user_id = u.id
        LEFT JOIN (
            SELECT
                user_id,
                MAX(time_survived) AS best_endless_time
            FROM endless_mode_records
            GROUP BY user_id
        ) er ON er.user_id = u.id
        WHERE u.is_active = 1
        ORDER BY {order_clause}
        LIMIT ?
    ''', [limit])

    users = []
    for row in rows:
        user = dict(row)
        user['name'] = user['username']

        solved = user.get('solved_count', 0) or 0
        correct = user.get('correct_count', 0) or 0
        user['accuracy'] = round(correct / solved * 100) if solved else 0

        users.append(user)

    return jsonify({"users": users})


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

            if slug == 'lancer':
                give_achievement(user_id, 'boss_lancer')
            elif slug == 'spamton': # SPAMTON UPDATE
                give_achievement(user_id, 'boss_spamton')
            elif slug == 'sans':
                give_achievement(user_id, 'boss_sans')

            db.execute(
                '''
                INSERT INTO user_history (user_id, action_text, action_date)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ''',
                (user_id, f'Победил босса {boss_name}')
            )

        defeated_count = query_db(
            'SELECT COUNT(*) AS cnt FROM user_boss_progress WHERE user_id = ? AND is_defeated = 1',
            [user_id],
            one=True
        )['cnt']

        if defeated_count >= 3:
            give_achievement(user_id, 'all_bosses')

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


@app.route('/spamton-simulator')
def spamton_simulator():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        ['Spamton NEO'],
        one=True
    )

    if not boss:
        abort(404)

    return render_template('spamton_simulator.html', boss=dict(boss))


@app.route('/lancer-simulator')
def lancer_simulator():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ? AND is_active = 1',
        ['Lancer'],
        one=True
    )

    if not boss:
        abort(404)

    return render_template('lancer_simulator.html', boss=dict(boss))


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


# --- ADMIN API ---

def ensure_admin(admin_id: int):
    admin = query_db('SELECT * FROM users WHERE id = ?', [admin_id], one=True)
    if not admin:
        return None, (jsonify({"error": "Администратор не найден"}), 404)

    if not admin['is_admin']:
        return None, (jsonify({"error": "Недостаточно прав"}), 403)

    return admin, None


@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    users = query_db('''
        SELECT
            u.id,
            u.username,
            u.email,
            u.level,
            u.rating,
            u.xp,
            u.is_admin,
            u.is_active,
            u.created_at,
            COALESCE(bp.bosses_defeated, 0) AS bosses_defeated
        FROM users u
        LEFT JOIN (
            SELECT user_id, COUNT(*) AS bosses_defeated
            FROM user_boss_progress
            WHERE is_defeated = 1
            GROUP BY user_id
        ) bp ON bp.user_id = u.id
        ORDER BY u.id ASC
    ''')

    result = []
    for row in users:
        item = dict(row)
        item['name'] = item['username']
        result.append(item)

    return jsonify({"users": result})


@app.route('/api/admin/ban', methods=['POST'])
def api_admin_ban():
    data = request.get_json() or {}

    admin_id = data.get('admin_id')
    user_id = data.get('user_id')
    reason = data.get('reason', 'Нарушение правил')

    if not admin_id or not user_id:
        return jsonify({"error": "Не указан admin_id или user_id"}), 400

    _, error = ensure_admin(admin_id)
    if error:
        return error

    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    if user['is_admin']:
        return jsonify({"error": "Нельзя заблокировать администратора"}), 400

    db = get_db()
    db.execute('''
        UPDATE users
        SET is_active = 0,
            banned_by = ?,
            banned_at = CURRENT_TIMESTAMP,
            ban_reason = ?
        WHERE id = ?
    ''', (admin_id, reason, user_id))

    db.execute('''
        INSERT INTO admin_logs (admin_id, action_type, target_type, target_id, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (admin_id, 'ban_user', 'user', user_id, f'Блокировка пользователя. Причина: {reason}'))

    db.commit()

    return jsonify({"success": True})


@app.route('/api/admin/unban', methods=['POST'])
def api_admin_unban():
    data = request.get_json() or {}

    admin_id = data.get('admin_id')
    user_id = data.get('user_id')

    if not admin_id or not user_id:
        return jsonify({"error": "Не указан admin_id или user_id"}), 400

    _, error = ensure_admin(admin_id)
    if error:
        return error

    user = query_db('SELECT * FROM users WHERE id = ?', [user_id], one=True)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    db = get_db()
    db.execute('''
        UPDATE users
        SET is_active = 1,
            banned_by = NULL,
            banned_at = NULL,
            ban_reason = NULL
        WHERE id = ?
    ''', (user_id,))

    db.execute('''
        INSERT INTO admin_logs (admin_id, action_type, target_type, target_id, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (admin_id, 'unban_user', 'user', user_id, 'Разблокировка пользователя'))

    db.commit()

    return jsonify({"success": True})


@app.route('/api/tasks', methods=['GET'])
def api_tasks_list():
    limit = request.args.get('limit', default=50, type=int)
    limit = max(1, min(limit or 50, 200))

    tasks = query_db('''
        SELECT *
        FROM tasks
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    ''', [limit])

    result = []
    for row in tasks:
        item = dict(row)
        result.append(item)

    return jsonify({"tasks": result})


@app.route('/api/tasks', methods=['POST'])
def api_task_create():
    data = request.get_json() or {}

    created_by = data.get('created_by')
    _, error = ensure_admin(created_by)
    if error:
        return error

    subject = data.get('subject')
    difficulty = data.get('difficulty')
    topic = data.get('topic', '')
    question = data.get('question')
    options = data.get('options')
    answer = data.get('answer')
    hint = data.get('hint', '')

    if not subject or not difficulty or not question or not options or not answer:
        return jsonify({"error": "Не заполнены обязательные поля"}), 400

    if not isinstance(options, list) or len(options) < 2:
        return jsonify({"error": "Нужно минимум 2 варианта ответа"}), 400

    import json

    db = get_db()
    db.execute('''
        INSERT INTO tasks (
            subject, difficulty, topic, question, options, answer, hint, created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        subject,
        difficulty,
        topic,
        question,
        json.dumps(options, ensure_ascii=False),
        answer,
        hint,
        created_by
    ))
    db.commit()

    return jsonify({"success": True})


@app.route('/api/iceberg/facts', methods=['GET'])
def api_iceberg_facts():
    facts = query_db('''
        SELECT *
        FROM iceberg_facts
        WHERE is_visible = 1
        ORDER BY level ASC, id ASC
    ''')

    result = [dict(row) for row in facts]
    return jsonify({"facts": result})


@app.route('/api/iceberg/facts', methods=['POST'])
def api_iceberg_fact_create():
    data = request.get_json() or {}

    created_by = data.get('created_by')
    _, error = ensure_admin(created_by)
    if error:
        return error

    title = data.get('title')
    content = data.get('content')
    level = data.get('level')
    position_x = data.get('position_x')
    position_y = data.get('position_y')

    if not title or not content or not level:
        return jsonify({"error": "Не заполнены обязательные поля"}), 400

    db = get_db()
    db.execute('''
        INSERT INTO iceberg_facts (
            title, content, level, position_x, position_y, is_visible
        )
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (
        title,
        content,
        int(level),
        position_x,
        position_y
    ))

    db.execute('''
        INSERT INTO admin_logs (admin_id, action_type, target_type, description)
        VALUES (?, ?, ?, ?)
    ''', (created_by, 'create_fact', 'fact', f'Добавлен факт айсберга: {title}'))

    db.commit()

    return jsonify({"success": True})


@app.route('/api/bosses', methods=['GET'])
def api_bosses_list():
    bosses = query_db('''
        SELECT *
        FROM boss_battles
        ORDER BY difficulty_level ASC, id ASC
    ''')

    result = [dict(row) for row in bosses]
    return jsonify({"bosses": result})


@app.route('/api/iceberg/facts/<int:fact_id>/position', methods=['POST'])
def api_iceberg_fact_update_position(fact_id: int):
    data = request.get_json() or {}

    admin_id = data.get('admin_id')
    position_x = data.get('position_x')
    position_y = data.get('position_y')

    if not admin_id:
        return jsonify({"error": "Не указан admin_id"}), 400

    if position_x is None or position_y is None:
        return jsonify({"error": "Не указаны координаты"}), 400

    _, error = ensure_admin(admin_id)
    if error:
        return error

    fact = query_db('SELECT * FROM iceberg_facts WHERE id = ?', [fact_id], one=True)
    if not fact:
        return jsonify({"error": "Факт не найден"}), 404

    db = get_db()
    db.execute('''
        UPDATE iceberg_facts
        SET position_x = ?, position_y = ?
        WHERE id = ?
    ''', (int(position_x), int(position_y), fact_id))

    db.execute('''
        INSERT INTO admin_logs (admin_id, action_type, target_type, target_id, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        admin_id,
        'move_fact',
        'fact',
        fact_id,
        f'Изменена позиция факта #{fact_id}: x={int(position_x)}, y={int(position_y)}'
    ))

    db.commit()

    return jsonify({
        "success": True,
        "fact_id": fact_id,
        "position_x": int(position_x),
        "position_y": int(position_y)
    })


# --- ЗАПУСК ПРИЛОЖЕНИЯ ---

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)
