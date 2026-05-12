import sqlite3
import hashlib
from flask import Flask, render_template, request, jsonify, g, abort
import json
import ast
import random
import os
import re
DATABASE = 'database.db'

app = Flask(__name__)

EMAIL_RE = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")


def normalize_email(value) -> str:
    return str(value or '').strip().lower()


def is_valid_email(value) -> bool:
    email = normalize_email(value)
    if len(email) > 254:
        return False
    return bool(EMAIL_RE.fullmatch(email))


def parse_options(raw):
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        try:
            value = ast.literal_eval(raw)
            if isinstance(value, (list, tuple)):
                return list(value)
        except (ValueError, SyntaxError):
            pass
        return [s.strip() for s in str(raw).split('|') if s.strip()]

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


BOSS_SLUGS = {
    "lancer": "Lancer",
    "spamton": "Spamton NEO",
    "sans": "Sans",
}

BOSS_DEFAULTS = {
    "Lancer": {"hp": 540},
    "Spamton NEO": {"hp": 4809},
    "Sans": {"hp": 1},
}


def sync_boss_defaults() -> None:
    """Обновляет важные параметры боссов в уже существующей базе."""
    if not os.path.exists(DATABASE):
        return

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            for boss_name, defaults in BOSS_DEFAULTS.items():
                cursor.execute(
                    'UPDATE boss_battles SET boss_hp = ? WHERE boss_name = ?',
                    (defaults['hp'], boss_name)
                )
            conn.commit()
    except sqlite3.OperationalError:
        # Таблица может ещё не существовать при первом создании БД.
        pass


def render_unavailable_page(
    message: str = 'эта страница недоступна, приятель.',
    status_code: int = 404,
):
    return render_template(
        'unavailable.html',
        message=message,
        status_code=status_code,
    ), status_code


def render_boss_unavailable(slug: str, boss_name: str | None = None):
    return render_unavailable_page(
        message='эта страница недоступна, приятель.',
        status_code=403,
    )


@app.errorhandler(404)
def handle_not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Страница не найдена"}), 404

    return render_unavailable_page(
        message='эта страница не найдена, приятель.',
        status_code=404,
    )


@app.errorhandler(403)
def handle_forbidden(error):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Доступ запрещён"}), 403

    return render_unavailable_page(
        message='эта страница недоступна, приятель.',
        status_code=403,
    )


def load_subject_stats(raw) -> dict:
    if not raw:
        return {}

    if isinstance(raw, dict):
        return raw

    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def merge_subject_stats(current_raw, delta_raw) -> str:
    stats = load_subject_stats(current_raw)

    if not isinstance(delta_raw, dict):
        delta_raw = {}

    for subject, delta in delta_raw.items():
        if not subject or not isinstance(delta, dict):
            continue

        current = stats.setdefault(subject, {"solved": 0, "correct": 0})
        current["solved"] = int(current.get("solved") or 0) + max(int(delta.get("solved") or 0), 0)
        current["correct"] = int(current.get("correct") or 0) + max(int(delta.get("correct") or 0), 0)

        if current["correct"] > current["solved"]:
            current["correct"] = current["solved"]

    return json.dumps(stats, ensure_ascii=False)


sync_boss_defaults()


def hash_password(password):
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
        'SELECT * FROM boss_battles WHERE boss_name = ?',
        [boss_name],
        one=True
    )

    if not boss:
        abort(404)

    if not boss['is_active']:
        return render_boss_unavailable(slug, boss['boss_name'])

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

    # ↓↓↓ ВСЁ ЭТО ДОЛЖНО БЫТЬ ВНЕ if/else ↓↓↓
    if first_victory:
        db.execute(
            'UPDATE users SET xp = xp + ?, wins = wins + 1 WHERE id = ?',
            (boss['reward_xp'], user_id)
        )

        if slug == 'lancer':
            give_achievement(user_id, 'boss_lancer')
        elif slug == 'spamton':
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
        'SELECT * FROM boss_battles WHERE boss_name = ?',
        ['Lancer'],
        one=True
    )

    if not boss:
        abort(404)

    if not boss['is_active']:
        return render_boss_unavailable('lancer', boss['boss_name'])

    return render_template('boss_page.html', boss=dict(boss), slug='lancer')


@app.route('/spamton')
def spamton_page():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ?',
        ['Spamton NEO'],
        one=True
    )

    if not boss:
        abort(404)

    if not boss['is_active']:
        return render_boss_unavailable('spamton', boss['boss_name'])

    return render_template('boss_page.html', boss=dict(boss), slug='spamton')


@app.route('/sans')
def sans_page():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ?',
        ['Sans'],
        one=True
    )

    if not boss:
        abort(404)

    if not boss['is_active']:
        return render_boss_unavailable('sans', boss['boss_name'])

    return render_template('boss_page.html', boss=dict(boss), slug='sans')


@app.route('/sans-simulator')
def sans_simulator():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ?',
        ['Sans'],
        one=True
    )

    if not boss:
        abort(404)

    if not boss['is_active']:
        return render_boss_unavailable('sans', boss['boss_name'])

    return render_template('sans_simulator.html', boss=dict(boss))


@app.route('/spamton-simulator')
def spamton_simulator():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ?',
        ['Spamton NEO'],
        one=True
    )

    if not boss:
        abort(404)

    if not boss['is_active']:
        return render_boss_unavailable('spamton', boss['boss_name'])

    return render_template('spamton_simulator.html', boss=dict(boss))


@app.route('/lancer-simulator')
def lancer_simulator():
    boss = query_db(
        'SELECT * FROM boss_battles WHERE boss_name = ?',
        ['Lancer'],
        one=True
    )

    if not boss:
        abort(404)

    if not boss['is_active']:
        return render_boss_unavailable('lancer', boss['boss_name'])

    return render_template('lancer_simulator.html', boss=dict(boss))



@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}

    name = str(data.get('name') or '').strip()
    email = normalize_email(data.get('email'))
    password = data.get('password') or ''

    if not name or not email or not password:
        return jsonify({"success": False, "error": "Заполните все поля"}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Введите email в формате name@example.com"}), 400

    user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True)
    if user:
        return jsonify({"success": False, "error": "Пользователь с таким email уже существует"}), 400

    password_hash = hash_password(password)

    db_connection = get_db()
    cursor = db_connection.cursor()
    cursor.execute(
        'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
        (name, email, password_hash)
    )
    db_connection.commit()

    new_user_id = cursor.lastrowid
    full_user = build_user_payload(new_user_id)

    return jsonify({"success": True, "user": full_user}), 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}

    email = normalize_email(data.get('email'))
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({"success": False, "error": "Не указан email или пароль"}), 400

    if not is_valid_email(email):
        return jsonify({"success": False, "error": "Введите email в формате name@example.com"}), 400

    user = query_db('SELECT * FROM users WHERE email = ?', [email], one=True)
    password_hash = hash_password(password)

    if not user or user['password_hash'] != password_hash:
        return jsonify({"success": False, "error": "Неверный email или пароль"}), 401

    if not user['is_active']:
        return jsonify({"success": False, "error": "Этот аккаунт заблокирован"}), 403

    full_user = build_user_payload(user['id'])
    return jsonify({"success": True, "user": full_user})



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


@app.route('/api/admin/bosses/<int:boss_id>/toggle', methods=['POST'])
def api_admin_toggle_boss(boss_id: int):
    data = request.get_json() or {}
    admin_id = data.get('admin_id')

    if not admin_id:
        return jsonify({"error": "Не указан admin_id"}), 400

    _, error = ensure_admin(admin_id)
    if error:
        return error

    boss = query_db('SELECT * FROM boss_battles WHERE id = ?', [boss_id], one=True)
    if not boss:
        return jsonify({"error": "Босс не найден"}), 404

    new_state = 0 if boss['is_active'] else 1

    db = get_db()
    db.execute(
        'UPDATE boss_battles SET is_active = ? WHERE id = ?',
        (new_state, boss_id)
    )
    db.execute('''
        INSERT INTO admin_logs (admin_id, action_type, target_type, target_id, description)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        admin_id,
        'toggle_boss',
        'boss',
        boss_id,
        f"Босс {boss['boss_name']} теперь {'активен' if new_state else 'неактивен'}"
    ))
    db.commit()

    updated = query_db('SELECT * FROM boss_battles WHERE id = ?', [boss_id], one=True)
    return jsonify({"success": True, "boss": dict(updated)})


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


@app.route('/api/quiz/start', methods=['POST'])
def start_quiz():
    user_id = request.args.get('user_id', type=int)
    subject = request.args.get('subject', 'all')
    difficulty = request.args.get('difficulty', 'all')
    count = request.args.get('count', 5, type=int)

    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if subject != 'all':
        query += " AND subject = ?"
        params.append(subject)
    if difficulty != 'all':
        query += " AND difficulty = ?"
        params.append(difficulty)

    query += " ORDER BY RANDOM() LIMIT ?"
    params.append(count)

    rows = query_db(query, params)

    if not rows:
        return jsonify({"error": "Нет задач по заданным критериям"}), 404

    tasks = []
    for row in rows:
        options = parse_options(row['options'])
        random.shuffle(options)

        tasks.append({
            'id': row['id'],
            'subject': row['subject'],
            'difficulty': row['difficulty'],
            'topic': row['topic'],
            'question': row['question'],
            'options': options,
            'answer': row['answer'],
            'hint': row['hint'] or ''
        })

    return jsonify({
        "tasks": tasks,
        "count": len(tasks)
    })


@app.route('/api/quiz/result', methods=['POST'])
def save_quiz_result():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    tasks_solved = int(data.get('tasks_solved') or 0)
    correct_count = int(data.get('correct_count') or 0)
    xp_earned = int(data.get('xp_earned') or 0)

    if not user_id:
        return jsonify({"error": "Не указан user_id"}), 400

    tasks_solved = max(tasks_solved, 0)
    correct_count = max(0, min(correct_count, tasks_solved))
    wrong_count = max(tasks_solved - correct_count, 0)
    rating_delta = max(correct_count * 10 - wrong_count * 3, 0)

    subject_stats_delta = data.get('subject_stats_delta') or {}

    user_before = query_db('SELECT solved_count, subject_stats FROM users WHERE id = ?', [user_id], one=True)
    if not user_before:
        return jsonify({"error": "Пользователь не найден"}), 404

    solved_before = user_before['solved_count'] or 0
    solved_after = solved_before + tasks_solved
    subject_stats = merge_subject_stats(user_before['subject_stats'], subject_stats_delta)

    db = get_db()
    db.execute('''
        UPDATE users
        SET solved_count = solved_count + ?,
            correct_count = correct_count + ?,
            xp = xp + ?,
            rating = rating + ?,
            subject_stats = ?
        WHERE id = ?
    ''', (tasks_solved, correct_count, xp_earned, rating_delta, subject_stats, user_id))

    db.execute('''
        INSERT INTO user_history (user_id, action_text, action_date)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, f'Викторина: {correct_count}/{tasks_solved} правильных'))

    if solved_before == 0 and tasks_solved > 0:
        give_achievement(user_id, 'first_question')
    if solved_after >= 10:
        give_achievement(user_id, 'ten_questions')
    if solved_after >= 50:
        give_achievement(user_id, 'fifty_questions')

    db.commit()

    user_data = build_user_payload(user_id)
    return jsonify({
        "success": True,
        "user": user_data
    })


@app.route('/api/endless/best', methods=['GET'])
def get_endless_best():
    user_id = request.args.get('user_id', type=int)

    if not user_id:
        return jsonify({"error": "Не указан user_id"}), 400

    record = query_db('''
        SELECT MAX(time_survived) as best_time, MAX(score) as best_score
        FROM endless_mode_records 
        WHERE user_id = ?
    ''', [user_id], one=True)

    if record and record['best_time']:
        return jsonify({
            "best_time": record['best_time'],
            "best_score": record['best_score'] or 0
        })

    return jsonify({
        "best_time": 0,
        "best_score": 0
    })


@app.route('/api/endless/result', methods=['POST'])
def save_endless_result():
    data = request.get_json() or {}
    user_id = data.get('user_id')
    time_survived = int(data.get('time_survived') or 0)
    correct_answers = int(data.get('correct_answers') or 0)
    xp_earned = int(data.get('xp_earned') or 0)

    if not user_id:
        return jsonify({"error": "Не указан user_id"}), 400

    time_survived = max(time_survived, 0)
    correct_answers = max(correct_answers, 0)
    rating_delta = correct_answers * 5 + time_survived // 10

    subject_stats_delta = data.get('subject_stats_delta') or {}

    user_before = query_db('SELECT id, subject_stats FROM users WHERE id = ?', [user_id], one=True)
    if not user_before:
        return jsonify({"error": "Пользователь не найден"}), 404

    subject_stats = merge_subject_stats(user_before['subject_stats'], subject_stats_delta)

    db = get_db()
    db.execute('''
        INSERT INTO endless_mode_records (user_id, time_survived, score, achieved_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, time_survived, correct_answers))

    db.execute('''
        UPDATE users
        SET xp = xp + ?,
            rating = rating + ?,
            subject_stats = ?
        WHERE id = ?
    ''', (xp_earned, rating_delta, subject_stats, user_id))

    db.execute('''
        INSERT INTO user_history (user_id, action_text, action_date)
        VALUES (?, ?, CURRENT_TIMESTAMP)
    ''', (user_id, f'Бесконечный режим: {format_time(time_survived)} времени, {correct_answers} правильных'))

    if time_survived >= 300:
        give_achievement(user_id, 'endless_master')

    db.commit()

    user_data = build_user_payload(user_id)
    return jsonify({
        "success": True,
        "user": user_data
    })


def format_time(seconds):
    seconds = int(seconds or 0)
    minutes = seconds // 60
    secs = seconds % 60
    return f"{minutes:02d}:{secs:02d}"


if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)
