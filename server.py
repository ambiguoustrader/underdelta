# -*- coding: utf-8 -*-
"""Flask EduBattle Server + Admin Panel"""
# server.py

import sqlite3
import json
import hashlib
import time
import random
import csv
import io
import os
import threading
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, session, render_template_string, redirect, url_for, flash, Response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)
app.secret_key = "your-secret-key-here-change-in-production"
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# === КОНФИГ ===
DB_PATH = "edubattle.db"
HEARTBEAT_INTERVAL = 10
MAX_NO_RESPONSE_TIME = 15


# === ПОМОЩНИКИ БАЗЫ ДАННЫХ ===
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализация всех таблиц"""
    conn = get_db()
    c = conn.cursor()

    # Пользователи
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        xp INTEGER DEFAULT 0,
        rating INTEGER DEFAULT 1000,
        solved_count INTEGER DEFAULT 0,
        correct_count INTEGER DEFAULT 0,
        wins INTEGER DEFAULT 0,
        losses INTEGER DEFAULT 0,
        draws INTEGER DEFAULT 0,
        achievements TEXT DEFAULT '[]',
        subject_stats TEXT DEFAULT '{}',
        is_admin INTEGER DEFAULT 0,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Задачи (викторина)
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        topic TEXT,
        question TEXT NOT NULL,
        options TEXT NOT NULL, -- JSON
        answer TEXT NOT NULL,
        hint TEXT DEFAULT '',
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Боссы (для клиентского JS)
    c.execute('''CREATE TABLE IF NOT EXISTS bosses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        boss_hp INTEGER DEFAULT 100,
        difficulty_level INTEGER DEFAULT 1,
        reward_xp INTEGER DEFAULT 100,
        is_active INTEGER DEFAULT 1
    )''')

    # Матчи (PvP и боссы)
    c.execute('''CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player1_id INTEGER,
        player1_name TEXT,
        player1_rating INTEGER,
        player2_id INTEGER,
        player2_name TEXT,
        player2_rating INTEGER,
        subject TEXT,
        mode TEXT, -- 'ranked', 'casual', 'boss', 'tournament'
        is_bot INTEGER DEFAULT 0,
        tasks TEXT, -- JSON массив задач
        player1_answers TEXT DEFAULT '[]',
        player2_answers TEXT DEFAULT '[]',
        player1_score INTEGER DEFAULT 0,
        player2_score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active', -- active, finished, cancelled
        winner_id INTEGER,
        cancel_reason TEXT,
        event_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP
    )''')

    # История битв с боссами (для achievements)
    c.execute('''CREATE TABLE IF NOT EXISTS boss_battles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        boss_id INTEGER,
        victory INTEGER,
        correct_answers INTEGER,
        total_questions INTEGER,
        xp_earned INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Бесконечный режим рекорды
    c.execute('''CREATE TABLE IF NOT EXISTS endless_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        best_time INTEGER DEFAULT 0,
        best_score INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Айсберг факты
    c.execute('''CREATE TABLE IF NOT EXISTS iceberg_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        level INTEGER DEFAULT 1, -- 1-5
        position_x INTEGER,
        position_y INTEGER,
        views_count INTEGER DEFAULT 0,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # История просмотров айсберга
    c.execute('''CREATE TABLE IF NOT EXISTS iceberg_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        fact_id INTEGER,
        viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # История действий
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action_text TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    # Сессии для админки
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP
    )''')

    conn.commit()
    conn.close()


# === УТИЛИТЫ ===

def hash_password(password):
    return hashlib.sha256((password + "salt").encode()).hexdigest()


def generate_id():
    """Генератор ID как в FastAPI"""
    return int(time.time() * 1000) + random.randint(1000, 9999)


def calculate_elo(my_rating, opp_rating, result):
    """Расчет ELO рейтинга"""
    K = 32
    expected = 1 / (1 + 10 ** ((opp_rating - my_rating) / 400))
    actual = 1 if result == 'win' else 0.5 if result == 'draw' else 0
    return round(K * (actual - expected))


def shuffle_list(lst):
    """Перемешивание списка"""
    result = lst[:]
    random.shuffle(result)
    return result


def format_user(user_row):
    """Форматирование пользователя для ответа"""
    if not user_row:
        return None
    return {
        "id": user_row["id"],
        "name": user_row["name"],
        "email": user_row["email"],
        "is_admin": bool(user_row["is_admin"]),
        "is_active": bool(user_row["is_active"]),
        "level": user_row["level"],
        "xp": user_row["xp"],
        "rating": user_row["rating"],
        "solved_count": user_row["solved_count"],
        "correct_count": user_row["correct_count"],
        "stats": {
            "solved": user_row["solved_count"],
            "correct": user_row["correct_count"],
            "wins": user_row["wins"],
            "losses": user_row["losses"],
            "draws": user_row["draws"]
        },
        "achievements": json.loads(user_row["achievements"]),
        "subject_stats": json.loads(user_row["subject_stats"])
    }


def get_level_color(level):
    colors = {
        1: {"bg": "rgba(16,185,129,0.2)", "border": "#10b981", "text": "#10b981", "label": "Уровень 1"},
        2: {"bg": "rgba(59,130,246,0.2)", "border": "#3b82f6", "text": "#3b82f6", "label": "Уровень 2"},
        3: {"bg": "rgba(168,85,247,0.2)", "border": "#a855f7", "text": "#a855f7", "label": "Уровень 3"},
        4: {"bg": "rgba(245,158,11,0.2)", "border": "#f59e0b", "text": "#f59e0b", "label": "Уровень 4"},
        5: {"bg": "rgba(239,68,68,0.2)", "border": "#ef4444", "text": "#ef4444", "label": "Уровень 5"}
    }
    return colors.get(level, colors[1])


# === ДЕКОРАТОРЫ ===

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Для API используем простую проверку по user_id в параметрах или сессии
        # В продакшене здесь должен быть JWT или сессии
        return f(*args, **kwargs)

    return decorated


# === WEBSOCKET МЕНЕДЖЕР (для матчей) ===

class MatchManager:
    def __init__(self):
        self.active_matches = {}  # match_id -> {player1_id, player2_id, last_activity}
        self.user_match = {}  # user_id -> match_id
        self.user_socket = {}  # user_id -> socket_id

    def join_match(self, user_id, match_id, socket_id):
        self.user_match[user_id] = match_id
        self.user_socket[user_id] = socket_id
        if match_id not in self.active_matches:
            self.active_matches[match_id] = {
                "players": [],
                "last_activity": time.time()
            }
        if user_id not in self.active_matches[match_id]["players"]:
            self.active_matches[match_id]["players"].append(user_id)
        join_room(f"match_{match_id}")

    def leave_match(self, user_id):
        if user_id in self.user_match:
            match_id = self.user_match[user_id]
            leave_room(f"match_{match_id}")
            if match_id in self.active_matches:
                if user_id in self.active_matches[match_id]["players"]:
                    self.active_matches[match_id]["players"].remove(user_id)
                if len(self.active_matches[match_id]["players"]) == 0:
                    del self.active_matches[match_id]
            del self.user_match[user_id]
            if user_id in self.user_socket:
                del self.user_socket[user_id]

    def broadcast_to_match(self, match_id, data):
        socketio.emit('match_update', data, room=f"match_{match_id}")

    def heartbeat_check(self):
        """Проверка отключений"""
        current_time = time.time()
        to_cancel = []
        for match_id, data in list(self.active_matches.items()):
            if current_time - data["last_activity"] > MAX_NO_RESPONSE_TIME:
                # Проверяем подключены ли игроки
                for user_id in data["players"]:
                    if user_id not in self.user_socket:
                        to_cancel.append((match_id, user_id))

        for match_id, user_id in to_cancel:
            self.cancel_match(match_id, user_id)

    def cancel_match(self, match_id, disconnected_user_id):
        """Отмена матча при отключении"""
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE matches SET status='cancelled', cancel_reason='player_disconnected' WHERE id=?", (match_id,))
        conn.commit()
        conn.close()

        self.broadcast_to_match(match_id, {
            "type": "match_cancelled",
            "reason": "player_disconnected",
            "disconnected_user_id": disconnected_user_id
        })


match_manager = MatchManager()


# === API МАРШРУТЫ (игровые) ===

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')

    if not all([name, email, password]):
        return jsonify({'error': 'Заполните все поля'}), 400

    conn = get_db()
    c = conn.cursor()

    # Проверка существования
    c.execute("SELECT id FROM users WHERE email=?", (email,))
    if c.fetchone():
        conn.close()
        return jsonify({'error': 'Email уже зарегистрирован'}), 400

    # Создание
    pwd_hash = hash_password(password)
    c.execute("""INSERT INTO users (name, email, password_hash, level, xp, rating) 
                 VALUES (?, ?, ?, 1, 0, 1000)""",
              (name, email, pwd_hash))
    user_id = c.lastrowid
    conn.commit()

    # Получаем созданного пользователя
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    return jsonify({'success': True, 'user': format_user(user)})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()

    if not user or user['password_hash'] != hash_password(password):
        return jsonify({'error': 'Неверный email или пароль'}), 401

    if not user['is_active']:
        return jsonify({'error': 'Аккаунт заблокирован'}), 403

    return jsonify({'success': True, 'user': format_user(user)})


@app.route('/api/user/<int:user_id>')
def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()

    # История
    c.execute("SELECT action_text, created_at FROM history WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
              (user_id,))
    history = [{'text': row['action_text'], 'date': row['created_at']} for row in c.fetchall()]
    conn.close()

    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    user_data = format_user(user)
    user_data['history'] = history
    return jsonify(user_data)


# === ВИКТОРИНА (ТРЕНИРОВКА) ===

@app.route('/api/quiz/start', methods=['POST'])
def start_quiz():
    """Совместимость с клиентом JS (используется вместо /api/training/start)"""
    user_id = request.args.get('user_id', type=int)
    subject = request.args.get('subject', 'all')
    difficulty = request.args.get('difficulty', 'all')
    count = request.args.get('count', 5, type=int)

    conn = get_db()
    c = conn.cursor()

    # Получаем задачи
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []

    if subject != 'all':
        query += " AND subject=?"
        params.append(subject)
    if difficulty != 'all':
        query += " AND difficulty=?"
        params.append(difficulty)

    c.execute(query, params)
    tasks = c.fetchall()
    conn.close()

    if not tasks:
        return jsonify({'error': 'Нет задач по заданным критериям'}), 404

    # Перемешиваем и берем count
    tasks = shuffle_list(tasks)[:count]

    result_tasks = []
    for task in tasks:
        result_tasks.append({
            'id': task['id'],
            'subject': task['subject'],
            'difficulty': task['difficulty'],
            'topic': task['topic'],
            'question': task['question'],
            'options': json.loads(task['options']),
            'answer': task['answer'],
            'hint': task['hint']
        })

    return jsonify({'tasks': result_tasks, 'count': len(result_tasks)})


@app.route('/api/quiz/result', methods=['POST'])
def save_quiz_result():
    """Сохранение результатов тренировки"""
    data = request.get_json()
    user_id = data.get('user_id')
    tasks_solved = data.get('tasks_solved', 0)
    correct_count = data.get('correct_count', 0)
    xp_earned = data.get('xp_earned', 0)

    conn = get_db()
    c = conn.cursor()

    # Обновляем пользователя
    c.execute("""UPDATE users SET 
                 solved_count = solved_count + ?,
                 correct_count = correct_count + ?,
                 xp = xp + ?
                 WHERE id=?""",
              (tasks_solved, correct_count, xp_earned, user_id))

    # Проверяем уровень
    c.execute("SELECT xp, level FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    xp = row['xp']
    level = row['level']

    # Простая логика уровней: каждые 100 XP = новый уровень
    new_level = (xp // 100) + 1
    if new_level > level:
        c.execute("UPDATE users SET level=? WHERE id=?", (new_level, user_id))

    # Добавляем в историю
    c.execute("INSERT INTO history (user_id, action_text) VALUES (?, ?)",
              (user_id, f"Викторина: {correct_count}/{tasks_solved} правильных"))

    conn.commit()

    # Получаем обновленного пользователя
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    return jsonify({'success': True, 'user': format_user(user)})


# === БОССЫ ===

@app.route('/api/bosses')
def get_bosses():
    """Список боссов для клиентского каталога"""
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM bosses WHERE is_active=1")
    bosses = []
    for row in c.fetchall():
        bosses.append({
            'id': row['id'],
            'slug': row['slug'],
            'name': row['name'],
            'boss_hp': row['boss_hp'],
            'difficulty_level': row['difficulty_level'],
            'reward_xp': row['reward_xp']
        })
    conn.close()
    return jsonify(bosses)


@app.route('/api/bosses/<int:boss_id>/start', methods=['POST'])
def start_boss_battle(boss_id):
    """Начало боя с боссом (создает матч против бота)"""
    user_id = request.args.get('user_id', type=int)

    conn = get_db()
    c = conn.cursor()

    # Получаем босса
    c.execute("SELECT * FROM bosses WHERE id=?", (boss_id,))
    boss = c.fetchone()

    # Получаем пользователя
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()

    if not boss or not user:
        conn.close()
        return jsonify({'error': 'Босс или пользователь не найден'}), 404

    # Получаем задачи для боя (5 штук подходящей сложности)
    diff_map = {1: 'easy', 2: 'medium', 3: 'hard'}
    difficulty = diff_map.get(boss['difficulty_level'], 'medium')

    c.execute("SELECT * FROM tasks WHERE difficulty=? ORDER BY RANDOM() LIMIT 5", (difficulty,))
    tasks = c.fetchall()

    if len(tasks) < 5:
        # Добираем случайные
        c.execute("SELECT * FROM tasks ORDER BY RANDOM() LIMIT ?", (5 - len(tasks),))
        tasks += c.fetchall()

    tasks_json = json.dumps([{
        'id': t['id'],
        'question': t['question'],
        'options': json.loads(t['options']),
        'answer': t['answer'],
        'hint': t['hint'],
        'topic': t['topic']
    } for t in tasks])

    # Создаем матч (player2_id=0 означает бота)
    c.execute("""INSERT INTO matches 
                 (player1_id, player1_name, player1_rating, player2_id, player2_name, 
                  player2_rating, subject, mode, is_bot, tasks, status)
                 VALUES (?, ?, ?, 0, ?, ?, ?, 'boss', 1, ?, 'active')""",
              (user_id, user['name'], user['rating'], boss['name'], boss['difficulty_level'] * 300, tasks_json))
    match_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        'match_id': match_id,
        'boss': {
            'id': boss['id'],
            'boss_name': boss['name'],
            'boss_hp': boss['boss_hp'],
            'reward_xp': boss['reward_xp']
        },
        'tasks': json.loads(tasks_json)
    })


@app.route('/api/bosses/<int:boss_id>/result', methods=['POST'])
def save_boss_result(boss_id):
    """Сохранение результата боя с боссом"""
    data = request.get_json()
    user_id = data.get('user_id')
    victory = data.get('victory')
    correct_answers = data.get('correct_answers')
    total_questions = data.get('total_questions')
    xp_earned = data.get('xp_earned')

    conn = get_db()
    c = conn.cursor()

    # Сохраняем запись о бое
    c.execute("""INSERT INTO boss_battles 
                 (user_id, boss_id, victory, correct_answers, total_questions, xp_earned)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (user_id, boss_id, 1 if victory else 0, correct_answers, total_questions, xp_earned))

    # Начисляем XP и обновляем статистику
    c.execute("UPDATE users SET xp = xp + ?, solved_count = solved_count + ? WHERE id=?",
              (xp_earned, total_questions, user_id))

    if victory:
        c.execute("UPDATE users SET wins = wins + 1 WHERE id=?", (user_id,))
        # Добавляем достижение (если реализована система achievements)

    conn.commit()

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    return jsonify({'success': True, 'user': format_user(user)})


# === БЕСКОНЕЧНЫЙ РЕЖИМ ===

@app.route('/api/endless/best')
def get_endless_best():
    user_id = request.args.get('user_id', type=int)
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT best_time, best_score FROM endless_records WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()

    if row:
        return jsonify({'best_time': row['best_time'], 'best_score': row['best_score']})
    return jsonify({'best_time': 0, 'best_score': 0})


@app.route('/api/endless/result', methods=['POST'])
def save_endless_result():
    data = request.get_json()
    user_id = data.get('user_id')
    time_survived = data.get('time_survived')
    correct_answers = data.get('correct_answers')
    xp_earned = data.get('xp_earned')

    conn = get_db()
    c = conn.cursor()

    # Проверяем рекорд
    c.execute("SELECT * FROM endless_records WHERE user_id=?", (user_id,))
    record = c.fetchone()

    if record:
        if time_survived > record['best_time']:
            c.execute("""UPDATE endless_records SET 
                         best_time=?, best_score=?, updated_at=CURRENT_TIMESTAMP 
                         WHERE user_id=?""", (time_survived, correct_answers, user_id))
    else:
        c.execute("""INSERT INTO endless_records (user_id, best_time, best_score)
                     VALUES (?, ?, ?)""", (user_id, time_survived, correct_answers))

    # Начисляем XP
    c.execute("UPDATE users SET xp = xp + ? WHERE id=?", (xp_earned, user_id))
    conn.commit()

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    return jsonify({'success': True, 'user': format_user(user)})


# === АЙСБЕРГ ===

@app.route('/api/iceberg/facts')
def get_iceberg_facts():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM iceberg_facts ORDER BY level, id")
    facts = []
    for row in c.fetchall():
        facts.append({
            'id': row['id'],
            'title': row['title'],
            'content': row['content'],
            'level': row['level'],
            'position_x': row['position_x'],
            'position_y': row['position_y'],
            'views_count': row['views_count']
        })
    conn.close()
    return jsonify({'facts': facts})


@app.route('/api/iceberg/facts', methods=['POST'])
def add_iceberg_fact():
    """Добавление факта (админ)"""
    data = request.get_json()
    title = data.get('title')
    content = data.get('content')
    level = data.get('level', 1)
    pos_x = data.get('position_x')
    pos_y = data.get('position_y')
    created_by = data.get('created_by')

    conn = get_db()
    c = conn.cursor()
    c.execute("""INSERT INTO iceberg_facts 
                 (title, content, level, position_x, position_y, created_by)
                 VALUES (?, ?, ?, ?, ?, ?)""",
              (title, content, level, pos_x, pos_y, created_by))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': c.lastrowid})


@app.route('/api/iceberg/facts/<int:fact_id>/position', methods=['POST'])
def update_fact_position(fact_id):
    """Обновление позиции факта (для drag-and-drop)"""
    data = request.get_json()
    x = data.get('position_x')
    y = data.get('position_y')

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE iceberg_facts SET position_x=?, position_y=? WHERE id=?",
              (x, y, fact_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


@app.route('/api/iceberg/view', methods=['POST'])
def record_iceberg_view():
    data = request.get_json()
    user_id = data.get('user_id')
    fact_id = data.get('fact_id')

    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO iceberg_views (user_id, fact_id) VALUES (?, ?)",
              (user_id, fact_id))
    c.execute("UPDATE iceberg_facts SET views_count = views_count + 1 WHERE id=?", (fact_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})


# === PvP МАТЧИ (через SocketIO и HTTP) ===

@app.route('/api/match/search', methods=['POST'])
def search_match():
    """Поиск матча (упрощенная версия - сразу создаем с ботом или в очередь)"""
    data = request.get_json()
    user_id = data.get('user_id')
    subject = data.get('subject')
    mode = data.get('mode', 'casual')

    # Для простоты - сразу создаем матч с ботом
    # В полной версии здесь должна быть очередь
    return jsonify({'status': 'play_with_bot', 'message': 'Use /api/match/play_with_bot'})


@app.route('/api/match/play_with_bot', methods=['POST'])
def play_with_bot():
    """Создание матча с ботом (PvP-like)"""
    data = request.get_json()
    user_id = data.get('user_id')
    subject = data.get('subject', 'math')

    conn = get_db()
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()

    # Получаем задачи
    c.execute("SELECT * FROM tasks WHERE subject=? ORDER BY RANDOM() LIMIT 5", (subject,))
    tasks = c.fetchall()

    if len(tasks) < 5:
        c.execute("SELECT * FROM tasks ORDER BY RANDOM() LIMIT 5")
        tasks = c.fetchall()

    tasks_data = [{
        'question': t['question'],
        'options': json.loads(t['options']),
        'answer': t['answer']
    } for t in tasks]

    # Создаем матч
    bot_names = ["Умник", "Знайка", "Эрудит"]
    bot_name = random.choice(bot_names)
    bot_rating = user['rating'] + random.randint(-100, 100)

    c.execute("""INSERT INTO matches 
                 (player1_id, player1_name, player1_rating, player2_id, player2_name,
                  player2_rating, subject, mode, is_bot, tasks, status)
                 VALUES (?, ?, ?, 0, ?, ?, ?, 'ranked', 1, ?, 'active')""",
              (user_id, user['name'], user['rating'], bot_name, bot_rating,
               json.dumps(tasks_data)))
    match_id = c.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        'success': True,
        'match': {
            'id': match_id,
            'player1_id': user_id,
            'player2_id': 0,
            'tasks': tasks_data
        }
    })


# === WEBSOCKET СОБЫТИЯ ===

@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    user_id = None
    for uid, sid in match_manager.user_socket.items():
        if sid == request.sid:
            user_id = uid
            break
    if user_id:
        match_manager.leave_match(user_id)
        # Проверяем матч на отмену
        if user_id in match_manager.user_match:
            match_id = match_manager.user_match[user_id]
            match_manager.cancel_match(match_id, user_id)
    print(f'Client disconnected: {request.sid}')


@socketio.on('join_match')
def handle_join_match(data):
    match_id = data.get('match_id')
    user_id = data.get('user_id')
    match_manager.join_match(user_id, match_id, request.sid)
    emit('joined', {'match_id': match_id}, room=f"match_{match_id}")
    match_manager.broadcast_to_match(match_id, {
        'type': 'user_connected',
        'user_id': user_id
    })


@socketio.on('match_answer')
def handle_match_answer(data):
    """Обработка ответа в матче"""
    match_id = data.get('match_id')
    user_id = data.get('user_id')
    task_index = data.get('task_index')
    answer = data.get('answer')

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM matches WHERE id=?", (match_id,))
    match = c.fetchone()

    if not match:
        conn.close()
        return emit('error', {'message': 'Match not found'})

    tasks = json.loads(match['tasks'])
    correct = answer == tasks[task_index]['answer']

    # Обновляем ответы
    if match['player1_id'] == user_id:
        answers = json.loads(match['player1_answers'])
        score = match['player1_score']
        key = 'player1'
    else:
        answers = json.loads(match['player2_answers'])
        score = match['player2_score']
        key = 'player2'

    answers.append({
        'task_index': task_index,
        'answer': answer,
        'correct': correct,
        'time_spent': data.get('time_spent', 0)
    })

    if correct:
        score += 1

    c.execute(f"UPDATE matches SET {key}_answers=?, {key}_score=? WHERE id=?",
              (json.dumps(answers), score, match_id))
    conn.commit()
    conn.close()

    # Уведомляем обоих игроков
    match_manager.broadcast_to_match(match_id, {
        'type': 'answer_result',
        'user_id': user_id,
        'task_index': task_index,
        'correct': correct,
        'correct_answer': tasks[task_index]['answer'],
        'player1_score': score if key == 'player1' else match['player1_score'],
        'player2_score': score if key == 'player2' else match['player2_score']
    })


# === ЛИДЕРБОРД ===

@app.route('/api/leaderboard')
def leaderboard():
    filter_type = request.args.get('filter', 'rating')
    limit = request.args.get('limit', 50, type=int)

    conn = get_db()
    c = conn.cursor()

    if filter_type == 'rating':
        c.execute("SELECT * FROM users ORDER BY rating DESC LIMIT ?", (limit,))
    elif filter_type == 'bosses':
        # Количество побед над боссами
        c.execute("""SELECT u.*, COUNT(bb.id) as boss_wins 
                     FROM users u LEFT JOIN boss_battles bb ON u.id=bb.user_id AND bb.victory=1
                     GROUP BY u.id ORDER BY boss_wins DESC LIMIT ?""", (limit,))
    elif filter_type == 'endless':
        c.execute("""SELECT u.*, COALESCE(er.best_time, 0) as best_time
                     FROM users u LEFT JOIN endless_records er ON u.id=er.user_id
                     ORDER BY best_time DESC LIMIT ?""", (limit,))
    else:
        c.execute("SELECT * FROM users ORDER BY solved_count DESC LIMIT ?", (limit,))

    users = []
    for row in c.fetchall():
        users.append({
            'id': row['id'],
            'name': row['name'],
            'level': row['level'],
            'rating': row['rating'],
            'solved_count': row['solved_count'],
            'bosses_defeated': row.get('boss_wins', 0) if filter_type == 'bosses' else 0
        })
    conn.close()
    return jsonify(users)


# === АДМИН API (из первого файла) ===

@app.route('/admin/login', methods=['POST'])
def admin_login():
    # Простая авторизация для админа
    # В реальном проекте - отдельная таблица админов
    pass


# === ЗАПУСК ===

def run_heartbeat():
    """Фоновая задача проверки соединений"""
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        match_manager.heartbeat_check()


if __name__ == '__main__':
    init_db()

    # Запускаем heartbeat в отдельном потоке
    heartbeat_thread = threading.Thread(target=run_heartbeat, daemon=True)
    heartbeat_thread.start()

    # Запуск Flask + SocketIO
    print("=" * 50)
    print("EduBattle Flask Server")
    print("API: http://localhost:5000")
    print("SocketIO: ws://localhost:5000")
    print("=" * 50)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)