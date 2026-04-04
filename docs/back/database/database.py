import sqlite3
import hashlib
import json
import os
import sys
from datetime import datetime


def create_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    with open('database.sql', 'r', encoding='utf-8') as file:
        sql_schema = file.read()

    cursor.executescript(sql_schema)

    # Создание администратора
    cursor.execute("SELECT * FROM users WHERE email = ?", ("admin@edu.ru",))
    if cursor.fetchone() is None:
        s = "moy_secret_sol_2024"
        password = hashlib.sha256(("admin123" + s).encode()).hexdigest()

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, rating, level, xp, is_admin, is_active)
            VALUES (?, ?, ?, 1500, 10, 1000, 1, 1)
        """, ("Администратор", "admin@edu.ru", password))

        conn.commit()

    bosses = [
        (
            "Lancer",
            "Just a lancer",
            3500,
            "/static/images/bosses/lancer.png",
            1,
            500,
            1,
            1
        ),
        (
            "Spamton NEO",
            "BIIIG SHOOOT",
            5000,
            "/static/images/bosses/BIGSHOT.png",
            2,
            750,
            5,
            1
        ),
        (
            "Sans",
            "SanS Undertale",
            1,
            "/static/images/bosses/sans.png",
            3,
            1000,
            10,
            1
        )
    ]

    for boss in bosses:
        cursor.execute("SELECT * FROM boss_battles WHERE boss_name = ?", (boss[0],))
        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO boss_battles (
                    boss_name, boss_description, boss_hp, boss_image, 
                    difficulty_level, reward_xp, unlock_level, is_active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, boss)

    conn.commit()

    # Добавление значков
    badges = [
        ("Первые шаги", "Решите первую задачу", "/static/badges/first_steps.png", "common", "solved_count", 1),
        ("Знаток", "Решите 50 задач", "/static/badges/expert.png", "rare", "solved_count", 50),
        ("Мастер", "Решите 100 задач", "/static/badges/master.png", "epic", "solved_count", 100),
        ("Победитель Лансера", "Победите Jevil", "/static/badges/jevil_winner.png", "rare", "boss_defeat", 1),
        ("Победитель Спамтона", "Победите Spamton NEO", "/static/badges/spamton_winner.png", "epic", "boss_defeat", 2),
        ("Победитель Санса", "Победите Sans", "/static/badges/sans_winner.png", "legendary", "boss_defeat", 3),
        (
        "Исследователь", "Просмотрите 10 фактов айсберга", "/static/badges/explorer.png", "common", "facts_viewed", 10),
        ("Археолог", "Просмотрите все факты айсберга", "/static/badges/archaeologist.png", "epic", "facts_viewed", -1)
    ]

    for badge in badges:
        cursor.execute("SELECT * FROM badges WHERE badge_name = ?", (badge[0],))
        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO badges (
                    badge_name, description, icon_url, rarity, 
                    requirement_type, requirement_value
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, badge)

    conn.commit()

    # Добавление фактов айсберга
    facts = [
        ("Toby Fox создатель",
         "Toby Fox создал Undertale и Deltarune практически в одиночку, включая музыку и программирование.", 1, 400, 50,
         None, 1),
        ("Разные концовки", "В Undertale есть три основных концовки: Нейтральная, Пацифистская и Геноцидная.", 1, 300,
         80, None, 1),
        ("Gaster Mystery", "W.D. Gaster - загадочный персонаж, упоминаемый только в скрытых файлах игры.", 2, 350, 150,
         None, 1),
        ("Deltarune анаграмма", "DELTARUNE - это анаграмма слова UNDERTALE.", 2, 450, 180, None, 1),
        (
        "Entry Number 17", "Таинственная запись #17 в лаборатории связана с экспериментами Гастера.", 3, 320, 250, None,
        1),
        ("Концовки?", "В игре более 96 концовок", 4, 380, 320, None, 1),
        ("Зелёный гастер", "Фраза 'DARKER YET DARKER' связана с экспериментами в пустоте.", 4, 420, 350, None, 1),
        ("Темнее чем темнота", "Фраза 'DARKER YET DARKER' связана с экспериментами в пустоте.", 4, 420, 350, None, 1),
        ("666 комната", "В файлах игры есть скрытая комната с необычным содержимым.", 5, 360, 420, None, 1)
    ]

    for fact in facts:
        cursor.execute("SELECT * FROM iceberg_facts WHERE title = ?", (fact[0],))
        if cursor.fetchone() is None:
            cursor.execute("""
                INSERT INTO iceberg_facts (
                    title, content, level, position_x, position_y, 
                    image_url, is_visible
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, fact)

    conn.commit()


    conn.commit()
    conn.close()

    print("Администратор: admin@edu.ru / admin123")


if __name__ == "__main__":
    if os.path.exists("database.db"):
        os.remove("database.db")
        print("Старая база данных удалена :)")

    create_database()