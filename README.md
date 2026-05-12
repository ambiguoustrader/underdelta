# UNDERDELTA

**UNDERDELTA** — фан-сайт по вселенной *Deltarune* и *Undertale* с викторинами, битвами с боссами, бесконечным режимом, айсбергом фактов, достижениями, рейтингом и панелью администратора.

Проект работает на Flask, SQLite и обычном фронтенде на HTML/CSS/JavaScript.

## Релиз

Актуальный стабильный релиз проекта: [Underdelta v1.0.1](https://github.com/ambiguoustrader/underdelta/releases/tag/v1.0.1).

---

## Возможности

### Для пользователя

- регистрация и вход по email;
- проверка формата email на клиенте и сервере;
- викторина по темам *Deltarune* и *Undertale*;
- перемешивание вариантов ответа в вопросах;
- сохранение результатов викторин;
- бесконечный режим с сохранением лучшего результата;
- рейтинг по очкам, боссам, викторине и бесконечному режиму;
- достижения;
- история активности с последними событиями сверху;
- айсберг фактов с интерактивными точками.

### Для администратора

- просмотр пользователей;
- блокировка и разблокировка пользователей;
- добавление задач;
- добавление и перемещение фактов айсберга;
- просмотр списка боссов;
- включение и отключение доступности боссов.

### Специальные страницы

Если пользователь переходит на несуществующую страницу или на страницу отключённого босса, открывается общая страница недоступности в стиле Undertale/Sans:

- чёрный фон;
- `sansshrug.gif` по центру;
- печатающийся текст;
- звуковой blip для каждой буквы;
- кнопка возврата назад.

---

## Стек

- Python 3.10+
- Flask
- SQLite
- HTML
- CSS
- JavaScript
- Web Audio API
- Tailwind CDN на странице `index.html`

---

## Структура проекта

```text
.
├── check.py
├── database.py
├── database.sql
├── requirements.txt
├── README.md
├── tasks
│   ├── tasks.csv
│   └── tasks.json
├── templates
│   ├── index.html
│   ├── boss_page.html
│   ├── unavailable.html
│   ├── lancer_simulator.html
│   ├── spamton_simulator.html
│   └── sans_simulator.html
└── static
    ├── css
    │   └── style.css
    ├── js
    │   └── script.js
    ├── gifs
    │   ├── sansshrug.gif
    │   └── dance10.webp
    ├── sounds
    │   └── snd_txtsans.wav
    ├── images
    │   ├── iceberg.png
    │   └── bosses
    └── games
        ├── c2-sans-fight
        ├── lancer_boss
        └── spamton_boss
```

---

## Установка

### 1. Клонировать проект

```bash
git clone https://github.com/ambiguoustrader/underdelta.git
cd underdelta
```

### 2. Создать виртуальное окружение

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Установить зависимости

```bash
pip install -r requirements.txt
```

---

## Первый запуск

### 1. Создать базу данных

```bash
python database.py
```

Скрипт создаст `database.db`, применит схему из `database.sql`, добавит стандартного администратора, боссов, факты айсберга и задачи из `tasks/tasks.csv`.

Стандартный администратор:

```text
Email: admin@edu.ru
Password: admin123
```

### 2. Запустить сервер

```bash
python check.py
```

По умолчанию приложение запускается на:

```text
http://127.0.0.1:8080
```

---

## Основные страницы

```text
/                   главная страница приложения
/lancer             страница босса Lancer
/spamton            страница босса Spamton NEO
/sans               страница босса Sans
/lancer-simulator   симулятор Lancer
/spamton-simulator  симулятор Spamton NEO
/sans-simulator     симулятор Sans
```

Если страница не существует, Flask отдаёт общий шаблон:

```text
templates/unavailable.html
```

---

## Основные API-эндпоинты

### Пользователь

```text
POST /api/register
POST /api/login
GET  /api/user/<user_id>
```

### Рейтинг

```text
GET /api/leaderboard?filter=rating
GET /api/leaderboard?filter=bosses
GET /api/leaderboard?filter=endless
GET /api/leaderboard?filter=quiz
```

### Викторина

```text
POST /api/quiz/start
POST /api/quiz/result
```

### Бесконечный режим

```text
GET  /api/endless/best?user_id=<id>
POST /api/endless/result
```

### Боссы

```text
GET  /api/bosses
POST /api/bosses/<slug>/complete
POST /api/admin/bosses/<boss_id>/toggle
```

### Айсберг фактов

```text
GET  /api/iceberg/facts
POST /api/iceberg/facts
POST /api/iceberg/facts/<fact_id>/position
```

### Администрирование

```text
GET  /api/admin/users
POST /api/admin/ban
POST /api/admin/unban
```

---

## Работа с задачами

Задачи загружаются из файла:

```text
tasks/tasks.csv
```

Ожидаемый порядок колонок:

```text
subject,difficulty,topic,question,option_1,option_2,option_3,option_4,answer,hint
```

Пример строки:

```csv
deltarune,easy,Персонажи,Как зовут маму Криса?,Ториэль,Андайн,Альфис,Ундина,Ториэль,Она работает учителем
```

Варианты ответа на сервере перемешиваются перед отправкой клиенту. Правильный ответ проверяется по полю `answer`.

---

## Работа с боссами

Боссы хранятся в таблице `boss_battles`.

Текущие значения HP:

```text
Lancer:      540
Spamton NEO: 4809
Sans:        1
```

Администратор может включать и отключать босса из панели администратора. Если босс отключён:

- карточка босса становится недоступной;
- прямая ссылка на страницу босса показывает страницу недоступности;
- прямая ссылка на симулятор тоже показывает страницу недоступности.

---

## Страница недоступности

Шаблон:

```text
templates/unavailable.html
```

Используемые ресурсы:

```text
static/gifs/sansshrug.gif
static/sounds/snd_txtsans.wav
```

Особенность браузеров: автозапуск звука без действия пользователя может блокироваться Chrome, Firefox и Safari. Поэтому страница поддерживает два поведения:

- при переходе внутри сайта текст может начать печататься сразу;
- при прямом вводе неизвестного URL в адресную строку звёздочка мигает до первого действия пользователя, после чего запускается печать текста со звуком.

---

## Лицензия и материалы

**UNDERDELTA** — неофициальный учебный фан-сайт по мотивам *UNDERTALE* и *DELTARUNE*. Проект не является официальным продуктом Toby Fox, tobyfox, Fangamer, 8-4 или других правообладателей, не связан с ними и не одобрен ими.

Исходный код проекта и сторонние игровые материалы разделяются:

- код сайта распространяется только по лицензии, указанной автором проекта в файле `LICENSE`;
- изображения, музыка, звуки, названия, персонажи, спрайты, логотипы и встроенные игры из *UNDERTALE* / *DELTARUNE* не переходят под лицензию исходного кода проекта;
- материалы из папок `static/images`, `static/gifs`, `static/sounds` и `static/games` относятся к соответствующим авторам и правообладателям.

### Используемые материалы и официальные ссылки

| Что используется или упоминается | Официальный / справочный источник |
| --- | --- |
| *UNDERTALE*, персонажи, визуальный стиль, звуки, музыка, спрайты и названия | [Официальный сайт UNDERTALE](https://undertale.com/) |
| *DELTARUNE*, персонажи, визуальный стиль, звуки, музыка, спрайты и названия | [Официальный сайт DELTARUNE](https://deltarune.com/) |
| Разработчик и издатель игр в Steam: `tobyfox` | [Страница разработчика tobyfox в Steam](https://store.steampowered.com/developer/tobyfox/) |
| Страница *UNDERTALE* в Steam | [UNDERTALE в Steam](https://store.steampowered.com/app/391540/Undertale/) |
| Страница *DELTARUNE* в Steam | [DELTARUNE в Steam](https://store.steampowered.com/app/1671210/DELTARUNE/) |
| Официальная рассылка и новости *UNDERTALE* / *DELTARUNE* | [DELTARUNE / UNDERTALE Mailing List](https://deltarune.com/newsletter/) |
| Архив официальных рассылок Toby Fox / Fangamer | [UNDERTALE / DELTARUNE Newsletter Archive](https://toby.fangamer.com/newsletters/) |
| Официальные товары *UNDERTALE* | [UNDERTALE на Fangamer](https://www.fangamer.com/collections/undertale) |
| Официальные товары *DELTARUNE* | [DELTARUNE на Fangamer](https://www.fangamer.com/collections/deltarune) |
| Публичная страница с кредитами команды *DELTARUNE Chapter 2* | [DELTARUNE Status Update — September 2021](https://deltarune.com/update-092021/) |

### Материалы внутри проекта

В проекте используются или могут использоваться следующие типы материалов, связанные с *UNDERTALE* и *DELTARUNE*:

```text
static/images/bosses/       изображения боссов и персонажей
static/gifs/                анимированные персонажи и декоративные гифки
static/sounds/              звуки текста и эффектов
static/games/               встроенные мини-игры и симуляторы
tasks/tasks.csv             вопросы по лору, персонажам и геймплею
tasks/tasks.json            вопросы по лору, персонажам и геймплею
```
