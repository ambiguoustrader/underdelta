import os
import csv
import json
import hashlib
import datetime

from db_session import global_init, create_session
from models.user import User
from models.task import Task
from models.boss_battle import BossBattle
from models.badge import Badge
from models.iceberg_fact import IcebergFact


def add_user(**kwargs):
    def decorator(func):
        def wrapper(*args, **fkwargs):
            db = create_session()
            exists = db.query(User).filter(User.email == kwargs["email"]).first()
            if not exists:
                user = User(**kwargs)
                db.add(user)
                db.commit()
            db.close()
            return func(*args, **fkwargs)
        return wrapper
    return decorator


def add_boss(**kwargs):
    def decorator(func):
        def wrapper(*args, **fkwargs):
            db = create_session()
            exists = db.query(BossBattle).filter(
                BossBattle.boss_name == kwargs["boss_name"]
            ).first()
            if not exists:
                boss = BossBattle(**kwargs)
                db.add(boss)
                db.commit()
            db.close()
            return func(*args, **fkwargs)
        return wrapper
    return decorator


def add_badge(**kwargs):
    def decorator(func):
        def wrapper(*args, **fkwargs):
            db = create_session()
            exists = db.query(Badge).filter(
                Badge.badge_name == kwargs["badge_name"]
            ).first()
            if not exists:
                badge = Badge(**kwargs)
                db.add(badge)
                db.commit()
            db.close()
            return func(*args, **fkwargs)
        return wrapper
    return decorator


def add_fact(**kwargs):
    def decorator(func):
        def wrapper(*args, **fkwargs):
            db = create_session()
            exists = db.query(IcebergFact).filter(
                IcebergFact.title == kwargs["title"]
            ).first()
            if not exists:
                fact = IcebergFact(**kwargs)
                db.add(fact)
                db.commit()
            db.close()
            return func(*args, **fkwargs)
        return wrapper
    return decorator


def load_tasks_from_csv(path):
    db = create_session()
    if not os.path.exists(path):
        db.close()
        return
    with open(path, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            if len(row) < 10:
                continue
            task = Task(
                subject=row[0],
                difficulty=row[1],
                topic=row[2],
                question=row[3],
                options=json.dumps([row[4], row[5], row[6], row[7]], ensure_ascii=False),
                answer=row[8],
                hint=row[9],
                created_at=datetime.datetime.now()
            )
            db.add(task)
        db.commit()
    db.close()


def create_database():
    global_init()


@add_user(
    username="Администратор",
    email="admin@edu.ru",
    password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
    rating=1500,
    level=10,
    xp=1000,
    is_admin=True,
    is_active=True,
    created_at=datetime.datetime.now()
)
@add_boss(
    boss_name="Lancer",
    boss_description="Just a lancer",
    boss_hp=540,
    boss_image="/static/images/bosses/lancer.png",
    difficulty_level=1,
    reward_xp=500,
    unlock_level=1,
    is_active=True,
    created_at=datetime.datetime.now()
)
@add_badge(
    badge_name="Первые шаги",
    description="Решите первую задачу",
    icon_url="/static/badges/first_steps.png",
    rarity="common",
    requirement_type="solved_count",
    requirement_value=1,
    created_at=datetime.datetime.now()
)
@add_fact(
    title="Toby Fox создатель",
    content="Toby Fox создал Undertale и Deltarune практически в одиночку.",
    level=1,
    position_x=400,
    position_y=90,
    image_url=None,
    is_visible=True,
    views_count=0,
    created_at=datetime.datetime.now()
)
def seed():
    load_tasks_from_csv("tasks/tasks.csv")


if __name__ == "__main__":
    create_database()
    seed()