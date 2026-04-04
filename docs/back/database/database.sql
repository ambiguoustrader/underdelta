-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rating INTEGER DEFAULT 1000,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    is_admin INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    banned_by INTEGER,
    banned_at TEXT,
    ban_reason TEXT,
    solved_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    subject_stats TEXT DEFAULT '{}',
    last_login TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Таблица задач
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    topic TEXT,
    question TEXT NOT NULL,
    options TEXT NOT NULL,
    answer TEXT NOT NULL,
    hint TEXT DEFAULT '',
    created_by INTEGER,
    generated_by_llm INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT
);

-- Таблица истории пользователя
CREATE TABLE IF NOT EXISTS user_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_text TEXT,
    action_date TEXT,
    created_at REAL DEFAULT (strftime('%s', 'now'))
);


-- Таблица достижений пользователей
CREATE TABLE IF NOT EXISTS user_achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    earned_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_id)
);

-- Таблица дневной статистики
CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    stat_date TEXT NOT NULL,
    day_of_week TEXT,
    subject TEXT DEFAULT 'all',
    solved INTEGER DEFAULT 0,
    correct INTEGER DEFAULT 0,
    UNIQUE(user_id, stat_date, subject)
);


CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_rating ON users(rating DESC);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_tasks_subject ON tasks(subject);
CREATE INDEX IF NOT EXISTS idx_daily_stats_user ON daily_stats(user_id);