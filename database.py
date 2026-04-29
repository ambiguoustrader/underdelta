import sqlite3
import hashlib
import csv
import os
import sys
import json
from datetime import datetime


def create_database():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    with open('database.sql', 'r', encoding='utf-8') as file:
        sql_schema = file.read()

    cursor.executescript(sql_schema)

    cursor.execute("SELECT * FROM users WHERE email = ?", ("admin@edu.ru",))
    if cursor.fetchone() is None:
        s = "moy_secret_sol_2024"
        password = hashlib.sha256(("admin123" + s).encode()).hexdigest()

        cursor.execute("""
            INSERT INTO users (username, email, password_hash, rating, level, xp, is_admin, is_active)
            VALUES (?, ?, ?, 1500, 10, 1000, 1, 1)
        """, ("Администратор", "admin@edu.ru", password))

        conn.commit()

    # Боссы
    bosses = [
        ("Lancer", "Just a lancer", 3500, "/static/images/bosses/lancer.png", 1, 500, 1, 1),
        ("Spamton NEO", "BIIIG SHOOOT", 5000, "/static/images/bosses/BIGSHOT.png", 2, 750, 5, 1),
        ("Sans", "SanS Undertale", 1, "/static/images/bosses/sans.png", 3, 1000, 10, 1)
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

    # Значки
    badges = [
        ("Первые шаги", "Решите первую задачу", "/static/badges/first_steps.png", "common", "solved_count", 1),
        ("Знаток", "Решите 50 задач", "/static/badges/expert.png", "rare", "solved_count", 50),
        ("Мастер", "Решите 100 задач", "/static/badges/master.png", "epic", "solved_count", 100),
        ("Победитель Лансера", "Победите Jevil", "/static/badges/jevil_winner.png", "rare", "boss_defeat", 1),
        ("Победитель Спамтона", "Победите Spamton NEO", "/static/badges/spamton_winner.png", "epic", "boss_defeat", 2),
        ("Победитель Санса", "Победите Sans", "/static/badges/sans_winner.png", "legendary", "boss_defeat", 3),
        (
        "Исследователь", "Просмотрите 10 фактов айсберга", "/static/badges/explorer.png", "common", "facts_viewed", 10),
        ("Археолог", "Просмотрите все факты айсберга", "/static/badges/archaeologist.png", "epic", "facts_viewed", -1),
        # Новые значки для глубоких слоев
        ("Искатель правды", "Достигните 7-го уровня айсберга", "/static/badges/truth_seeker.png", "rare",
         "iceberg_level", 7),
        ("Житель пустоты", "Достигните 9-го уровня айсберга", "/static/badges/void_dweller.png", "legendary",
         "iceberg_level", 9)
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

    facts = [
        # Уровень 1
        ("Toby Fox создатель",
         "Toby Fox создал Undertale и Deltarune практически в одиночку, включая музыку и программирование.", 1, 400, 90,
         None, 1),
        ("Разные концовки", "В Undertale есть три основных концовки: Нейтральная, Пацифистская и Геноцидная.", 1, 300,
         80, None, 1),
        ("Ральзей = Эйзриэль",
         "Теория: Ральзей из Deltarune — это Эйзриэль из Undertale, упавший в Темный Мир.", 1, 500, 60, None, 1),

        # Уровень 2
        ("Gaster Mystery", "W.D. Gaster - загадочный персонаж, упоминаемый только в скрытых файлах игры.", 2, 350, 250,
         None, 1),
        ("Deltarune анаграмма", "DELTARUNE - это анаграмма слова UNDERTALE.", 2, 450, 280, None, 1),
        ("Крис не Рыцарь",
         "Несмотря на открытие фонтанов, многие фанаты считают, что Крис — не настоящий Темный Рыцарь.", 2, 250, 340,
         None, 1),

        # Уровень 3
        ("Entry Number 17", "Таинственная запись #17 в лаборатории связана с экспериментами Гастера.", 3, 320, 550,
         None, 1),
        ("Джевил встретил Рыцаря",
         "Джевил сошел с ума после встречи с 'невероятным кем-то' — предположительно, Темным Рыцарем.", 3, 380, 490,
         None, 1),

        # Уровень 4
        ("96 концовок",
         "В Undertale существует более 96 вариаций нейтральной концовки в зависимости от убитых персонажей.", 4, 380,
         720, None, 1),
        ("DARKER YET DARKER", "Фраза 'DARKER YET DARKER' связана с экспериментами Гастера в пустоте.", 4, 420, 750,
         None, 1),
        ("Ноэль и Ангел", "Ноэль Лесной связывают с 'Ангелом' из пророчества из-за её магических способностей.", 4, 280,
         730, None, 1),

        # Уровень 5
        ("666 комната", "В файлах игры есть скрытая комната с необычным содержимым (sound_test).", 5, 360, 820, None,
         1),
        ("Следователи Гастера",
         "В Deltarune есть персонажи, похожие на последователей Гастера из Undertale (человек с руками, человек из другого мира).",
         5, 500, 800, None, 1),
        ("Яйцо", "В игре можно найти 'Яйцо', которое остается в инвентаре между главами — связь с Гастером.", 5, 200,
         840, None, 1),

        # Уровень 6
        ("Пророчество об Ангеле",
         "Ангел, упомянутый в пророчестве, возможно, не враг, а ключ к спасению. Некоторые связывают его с Десс.", 6,
         150, 1000, None, 1),
        ("Спамтон и Майк",
         "Спамтон упоминает 'Майка' — возможно, это Тенна (Tenna), телевизор или связанный с медиа персонаж.", 6, 400,
         1020, None, 1),
        ("Поисковый отряд Десс",
         "После исчезновения Десс был организован поисковый отряд. Санс и Папирус участвовали в поисках.", 6, 550,
         1080, None, 1),

        # Уровень 7
        ("Папирус — Темный Рыцарь?",
         "Теория: Папирус из Undertale — это Темный Рыцарь. Санс прибыл в Касти Сити, чтобы найти его. Чертежи в мастерской описывают 'рыцарский' доспех.",
         7, 100, 1130, None, 1),
        ("Зеленая комната Гастера",
         "Существует 'Зеленая комната' — место между мирами, где скрывается Гастер. Связана с записью №17 и зеленым цветом текста.",
         7, 300, 1120, None, 1),
        ("Десс и больница",
         "Десс пропала при загадочных обстоятельствах. Её поиски связаны с больницей и тайной комнатой в доме Лесных.",
         7, 500, 1080, None, 1),
        ("Санс знает о Сохранениях",
         "В Deltarune Санс намекает, что 'встречал Крис раньше', возможно, помнит события Undertale или другие временные линии.",
         7, 420, 1150, None, 1),

        # Уровень 8
        ("Амальгаметы — Провалившиеся Темные",
         "Амальгаметы из Undertale (существа из слитых душ) — результат экспериментов с Определением. Возможно, они были попыткой создать искусственный Темный Мир.",
         8, 200, 1280, None, 1),
        ("Гастер — Первый Темнер",
         "Д-р Гастер мог стать первым существом, существующим вне реальности — прародителем Темныхнеров, живущим в Пустоте между мирами.",
         8, 450, 1250, None, 1),
        ("Красный Крест",
         "В комнате Крис есть красный крест, похожий на тот, что носит Эйзриэль. Указывает на связь семьи Дримурров с церковью Ангела.",
         8, 370, 1300, None, 1),
        ("Существо из-за дерева",
         "В Касти Сити за одним из деревьев скрывается странная фигура, похожая на Гастера или его последователя.", 8,
         300, 1280, None, 1),

        # Уровень 9
        ("Рыцарь — Герой?",
         "Темный Рыцарь открывает фонтаны не для зла, а чтобы предотвратить 'Рок' другим путем. Он — герой, действующий из отчаяния.",
         9, 150, 1350, None, 1),
        ("Десс стала Фонтаном",
         "Десс не погибла, а сама стала живым Темным Фонтаном или его сердцевиной, питая энергией миры Темнеров.", 9,
         480, 1480, None, 1),
        ("Третья сущность",
         "Внутри тела Крис находятся три сущности: сам Крис, Игрок (душа) и третья сила — осколок Гастера или дух Десс, управляющий ночными событиями.",
         9, 420, 1400, None, 1),
        ("Папирус в Зеленой комнате",
         "Папирус заперт в Зеленой комнате Гастера между мирами. Он жив, но недоступен, что объясняет его отсутствие в Deltarune, но присутствие в сердце Санса.",
         9, 300, 1560, None, 1),
        ("Истинная цель Рока",
         "'Рок' (The Roaring) — это не уничтожение мира, а его пересоздание. Темные Рыцарь и Гастер пытаются создать идеальный мир, объединив все реальности.",
         9, 260, 1450, None, 1)
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

    csv_path = 'tasks/tasks.csv'
    if not os.path.exists(csv_path):
        print(f"Файл {csv_path} не найден, задачи не загружены")
    else:
        with open(csv_path, 'r', encoding='utf-8') as file:
            tasks_demo = csv.reader(file)
            next(tasks_demo)  # пропускаем заголовок

            count = 0
            for task in tasks_demo:
                # CSV: subject, difficulty, topic, question, option_1, option_2, option_3, option_4, answer, hint
                if not task or len(task) < 10:
                    print(f"Пропущена некорректная строка (не хватает полей): {task}")
                    continue
                try:
                    subject = task[0]
                    difficulty = task[1]
                    topic = task[2]
                    question = task[3]
                    options = [task[4], task[5], task[6], task[7]]
                    answer = task[8]
                    hint = task[9]

                    cursor.execute("""
                        INSERT INTO tasks (subject, difficulty, topic, question, options, answer, hint)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        subject,
                        difficulty,
                        topic,
                        question,
                        json.dumps(options, ensure_ascii=False),
                        answer,
                        hint
                    ))
                    count += 1
                except Exception as e:
                    print(f"Ошибка в строке {task}: {e}")

            conn.commit()
            print(f"Загружено {count} задач из CSV")

    conn.commit()
    conn.close()

    print("Администратор: admin@edu.ru / admin123")


if __name__ == "__main__":
    if os.path.exists("database.db"):
        os.remove("database.db")
        print("Старая база данных удалена :)")

    create_database()
