
// ============================================
// DELTARUNE WORLD — Client
// ============================================

let tekushiyUser = null;
let quizZadachi = [];
let quizIndex = 0;
let quizPravilno = 0;
let quizTimer = null;
let quizSekundy = 30;

let bossZadachi = [];
let bossIndex = 0;
let bossPravilno = 0;
let bossTimer = null;
let bossSekundy = 30;
let tekushiyBoss = null;
let bossHpPlayer = 100;
let bossHpBoss = 100;

let endlessZadachi = [];
let endlessIndex = 0;
let endlessPravilno = 0;
let endlessTimer = null;
let endlessSekundy = 0;
let endlessQTimer = null;
let endlessQSekundy = 15;
let endlessLives = 3;
let endlessActive = false;

let ibergFakty = [];
let tekushiyLeaderboardFilter = 'rating';
let tekushiyAdminTab = 'users';

const API_URL = window.location.origin;

// ============================================
// API
// ============================================

async function apiZapros(endpoint, options) {
    if (!options) options = {};

    let nastroyki = {
        headers: { 'Content-Type': 'application/json' }
    };

    if (options.method) nastroyki.method = options.method;
    if (options.body) nastroyki.body = JSON.stringify(options.body);

    try {
        const response = await fetch(API_URL + endpoint, nastroyki);
        const contentType = response.headers.get("content-type");

        if (contentType && contentType.indexOf("application/json") !== -1) {
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.detail || data.error || 'Ошибка от API');
            }
            return data;
        } else {
            const textData = await response.text();
            throw new Error(`Ожидался JSON, но получен не JSON. Ответ сервера: ${textData}`);
        }
    } catch (err) {
        console.error('API ошибка:', err);
        throw err;
    }
}

// ============================================
// УТИЛИТЫ
// ============================================

function showToast(type, message) {
    let toast = document.createElement('div');
    toast.className = 'toast ' + type;
    let icons = { success: '✓', error: '✕', info: 'ℹ' };
    toast.innerHTML = '<span>' + (icons[type] || '') + '</span> ' + message;
    document.body.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}

function formatVremya(sekundy) {
    let min = Math.floor(sekundy / 60);
    let sek = sekundy % 60;
    return (min < 10 ? '0' + min : min) + ':' + (sek < 10 ? '0' + sek : sek);
}

function getLevelColor(level) {
    let colors = {
        1: { bg: 'rgba(16,185,129,0.2)', border: '#10b981', text: '#10b981', label: 'Уровень 1' },
        2: { bg: 'rgba(59,130,246,0.2)', border: '#3b82f6', text: '#3b82f6', label: 'Уровень 2' },
        3: { bg: 'rgba(168,85,247,0.2)', border: '#a855f7', text: '#a855f7', label: 'Уровень 3' },
        4: { bg: 'rgba(245,158,11,0.2)', border: '#f59e0b', text: '#f59e0b', label: 'Уровень 4' },
        5: { bg: 'rgba(239,68,68,0.2)', border: '#ef4444', text: '#ef4444', label: 'Уровень 5' }
    };
    return colors[level] || colors[1];
}

// ============================================
// АВТОРИЗАЦИЯ
// ============================================

function pokazatRegistraciyu() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
    document.getElementById('auth-error').classList.add('hidden');
}

function pokazatVhod() {
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
    document.getElementById('auth-error').classList.add('hidden');
}

function pokazatOshibkuAuth(tekst) {
    let el = document.getElementById('auth-error');
    el.textContent = tekst;
    el.classList.remove('hidden');
}

async function vypolnitVhod() {
    let email = document.getElementById('login-email').value.trim();
    let password = document.getElementById('login-password').value;

    if (!email || !password) {
        pokazatOshibkuAuth('Заполните все поля');
        return;
    }

    try {
        let result = await apiZapros('/api/login', {
            method: 'POST',
            body: { email, password }
        });

        if (result.success) {
            tekushiyUser = result.user;
            localStorage.setItem('deltarune_user', JSON.stringify(tekushiyUser));
            pokazatGlavniy();
        }
    } catch (err) {
        pokazatOshibkuAuth(err.message);
    }
}

async function vypolnitRegistraciyu() {
    let name = document.getElementById('reg-name').value.trim();
    let email = document.getElementById('reg-email').value.trim();
    let password = document.getElementById('reg-password').value;

    if (!name || !email || !password) {
        pokazatOshibkuAuth('Заполните все поля');
        return;
    }

    if (password.length < 6) {
        pokazatOshibkuAuth('Пароль минимум 6 символов');
        return;
    }

    try {
        let result = await apiZapros('/api/register', {
            method: 'POST',
            body: { name, email, password }
        });

        if (result.success) {
            tekushiyUser = result.user;
            localStorage.setItem('deltarune_user', JSON.stringify(tekushiyUser));
            pokazatGlavniy();
        }
    } catch (err) {
        pokazatOshibkuAuth(err.message);
    }
}

function vyjtiIzAkkunta() {
    tekushiyUser = null;
    localStorage.removeItem('deltarune_user');
    document.getElementById('main-screen').classList.add('hidden');
    document.getElementById('auth-screen').classList.remove('hidden');
}

// ============================================
// НАВИГАЦИЯ
// ============================================

function pokazatSekciyu(name) {
    document.querySelectorAll('[id^="section-"]').forEach(s => s.classList.add('hidden'));
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

    let sekcia = document.getElementById('section-' + name);
    if (sekcia) sekcia.classList.remove('hidden');

    let navItem = document.querySelector('[data-section="' + name + '"]');
    if (navItem) navItem.classList.add('active');

    if (name === 'leaderboard') zagruzitLiderboard();
    else if (name === 'dashboard') obnovitDashboard();
    else if (name === 'admin') zagruzitAdminData();
    else if (name === 'bosses') zagruzitBossov();
    else if (name === 'iceberg') zagruzitAysberg();
    else if (name === 'profile') obnovitProfil();
    else if (name === 'endless') zagruzitEndlessRekord();

    if (window.innerWidth <= 768) {
        document.getElementById('sidebar').classList.remove('open');
    }
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}

// ============================================
// ГЛАВНЫЙ ЭКРАН
// ============================================

async function pokazatGlavniy() {
    document.getElementById('loading-screen').classList.add('hidden');
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('main-screen').classList.remove('hidden');

    obnovitUserInfo();
    obnovitDashboard();

    if (tekushiyUser.is_admin) {
        document.getElementById('admin-nav').classList.remove('hidden');
        document.getElementById('admin-nav-title').style.display = 'block';
    }
}

function obnovitUserInfo() {
    let imya = tekushiyUser.name || tekushiyUser.username || 'Игрок';
    let bukva = imya.charAt(0).toUpperCase();

    document.getElementById('user-avatar').textContent = bukva;
    document.getElementById('user-name-sidebar').textContent = imya;
    document.getElementById('user-level-sidebar').textContent = tekushiyUser.level || 1;
    document.getElementById('welcome-name').textContent = imya;
}

async function obnovitDashboard() {
    let stats = tekushiyUser.stats || {};

    let solved = tekushiyUser.solved_count || 0;
    let correct = tekushiyUser.correct_count || 0;
    let tochnost = solved > 0 ? Math.round(correct / solved * 100) : 0;

    document.getElementById('stat-solved').textContent = solved;
    document.getElementById('stat-correct').textContent = tochnost + '%';
    document.getElementById('stat-rating').textContent = tekushiyUser.rating || 1000;

    document.getElementById('stat-bosses').textContent =
        (tekushiyUser.bosses_defeated || 0) + '/3';

    pokazatDostizheniya('achievements-list');
    pokazatIstoriyu();
}

function pokazatDostizheniya(containerId) {
    let konteyner = document.getElementById(containerId);
    let achi = tekushiyUser.achievements || [];

    let achievementData = [
        { id: 'first_question', icon: '🎯', name: 'Первый вопрос', desc: 'Ответьте на первый вопрос' },
        { id: 'ten_questions', icon: '📚', name: 'Начинающий', desc: 'Решите 10 вопросов' },
        { id: 'fifty_questions', icon: '🔥', name: 'Упорный', desc: 'Решите 50 вопросов' },
        { id: 'boss_jevil', icon: '🃏', name: 'Победитель Джевила', desc: 'Победите Jevil' },
        { id: 'boss_spamton', icon: '🤖', name: 'Победитель Спэмтона', desc: 'Победите Spamton NEO' },
        { id: 'boss_sans', icon: '💀', name: 'Победитель Санса', desc: 'Победите Sans' },
        { id: 'all_bosses', icon: '🏆', name: 'Истребитель боссов', desc: 'Победите всех боссов' },
        { id: 'explorer', icon: '🧊', name: 'Исследователь', desc: 'Просмотрите 10 фактов' },
        { id: 'endless_master', icon: '♾', name: 'Мастер бесконечности', desc: 'Продержитесь 5 минут' }
    ];

    let html = '';
    achievementData.forEach(a => {
        let polucheno = achi.includes(a.id);
        html += `
            <div title="${a.name}: ${a.desc}" style="display: flex; flex-direction: column; align-items: center; gap: 4px;">
                <div class="achievement-badge ${polucheno ? 'earned' : ''}" style="${!polucheno ? 'opacity: 0.3;' : ''}">
                    ${a.icon}
                </div>
                <div style="font-size: 0.65rem; color: #9ca3af; text-align: center; max-width: 60px;">${a.name}</div>
            </div>
        `;
    });

    konteyner.innerHTML = html;
}

function pokazatIstoriyu() {
    let konteyner = document.getElementById('activity-list');
    let istoriya = tekushiyUser.history || [];

    if (istoriya.length === 0) {
        konteyner.innerHTML = '<p style="color: #9ca3af; text-align: center; font-size: 0.85rem;">Пока нет активности</p>';
        return;
    }

    let html = '';
    let items = istoriya.slice(-8).reverse();
    items.forEach(zapis => {
        html += `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: rgba(255,255,255,0.03); border-radius: 8px; font-size: 0.85rem;">
                <span style="color: #d1d5db;">${zapis.text || zapis.action_text}</span>
                <span style="color: #6b7280; font-size: 0.75rem; flex-shrink: 0; margin-left: 8px;">${zapis.date || zapis.action_date || ''}</span>
            </div>
        `;
    });

    konteyner.innerHTML = html;
}

// ============================================
// ВИКТОРИНА
// ============================================

async function nachatViktorimu() {
    let subject = document.getElementById('quiz-subject').value;
    let difficulty = document.getElementById('quiz-difficulty').value;
    let count = parseInt(document.getElementById('quiz-count').value);

    try {
        let params = '?count=' + count + '&user_id=' + tekushiyUser.id;
        if (subject !== 'all') params += '&subject=' + subject;
        if (difficulty !== 'all') params += '&difficulty=' + difficulty;

        let result = await apiZapros('/api/quiz/start' + params, { method: 'POST' });

        quizZadachi = result.tasks;
        quizIndex = 0;
        quizPravilno = 0;

        document.getElementById('quiz-setup').classList.add('hidden');
        document.getElementById('quiz-results').classList.add('hidden');
        document.getElementById('quiz-active').classList.remove('hidden');
        document.getElementById('quiz-total').textContent = quizZadachi.length;

        pokazatVoprosQuiz();
    } catch (err) {
        showToast('error', 'Ошибка загрузки вопросов: ' + err.message);
    }
}

function pokazatVoprosQuiz() {
    if (quizIndex >= quizZadachi.length) {
        zavershitViktorimu();
        return;
    }

    let zadacha = quizZadachi[quizIndex];

    document.getElementById('quiz-current').textContent = quizIndex + 1;
    document.getElementById('quiz-topic').textContent = zadacha.topic || 'Вопрос';
    document.getElementById('quiz-question').textContent = zadacha.question;
    document.getElementById('quiz-hint-block').classList.add('hidden');
    document.getElementById('quiz-hint-text').textContent = zadacha.hint || '';
    document.getElementById('quiz-hint-btn').disabled = !zadacha.hint;
    document.getElementById('quiz-next-btn').disabled = true;

    let progress = (quizIndex / quizZadachi.length) * 100;
    document.getElementById('quiz-progress').style.width = progress + '%';

    let konteyner = document.getElementById('quiz-options');
    konteyner.innerHTML = '';

    zadacha.options.forEach(opt => {
        let div = document.createElement('div');
        div.className = 'task-option';
        div.textContent = opt;
        div.onclick = () => vybratOtvetQuiz(div, opt);
        konteyner.appendChild(div);
    });

    quizSekundy = 30;
    obnovitTajmerQuiz();

    if (quizTimer) clearInterval(quizTimer);
    quizTimer = setInterval(() => {
        quizSekundy--;
        obnovitTajmerQuiz();
        if (quizSekundy <= 0) {
            clearInterval(quizTimer);
            document.getElementById('quiz-next-btn').disabled = false;
        }
    }, 1000);
}

function obnovitTajmerQuiz() {
    let el = document.getElementById('quiz-timer');
    el.textContent = quizSekundy;
    let procent = (quizSekundy / 30) * 100;
    document.getElementById('quiz-timer-ring').style.setProperty('--progress', procent + '%');
}

function vybratOtvetQuiz(element, otvet) {
    if (quizTimer) clearInterval(quizTimer);

    let zadacha = quizZadachi[quizIndex];
    let vse = document.querySelectorAll('#quiz-options .task-option');

    vse.forEach(o => { o.onclick = null; });

    if (otvet === zadacha.answer) {
        element.classList.add('correct');
        quizPravilno++;
        document.getElementById('quiz-score').textContent = quizPravilno;
    } else {
        element.classList.add('wrong');
        vse.forEach(o => {
            if (o.textContent === zadacha.answer) o.classList.add('correct');
        });
    }

    document.getElementById('quiz-next-btn').disabled = false;
}

function pokazatPodskazku() {
    document.getElementById('quiz-hint-block').classList.remove('hidden');
    document.getElementById('quiz-hint-btn').disabled = true;
}

function sleduushiyVopros() {
    if (quizTimer) clearInterval(quizTimer);
    quizIndex++;
    pokazatVoprosQuiz();
}

async function zavershitViktorimu() {
    if (quizTimer) clearInterval(quizTimer);

    let xp = quizPravilno * 10;
    let total = quizZadachi.length;

    try {
        let result = await apiZapros('/api/quiz/result', {
            method: 'POST',
            body: {
                user_id: tekushiyUser.id,
                tasks_solved: total,
                correct_count: quizPravilno,
                xp_earned: xp
            }
        });

        if (result.success) {
            tekushiyUser = result.user;
            localStorage.setItem('deltarune_user', JSON.stringify(tekushiyUser));
            obnovitUserInfo();
        }
    } catch (err) {
        console.error('Ошибка сохранения:', err);
    }

    document.getElementById('quiz-active').classList.add('hidden');
    document.getElementById('quiz-results').classList.remove('hidden');

    document.getElementById('quiz-res-correct').textContent = quizPravilno;
    document.getElementById('quiz-res-wrong').textContent = total - quizPravilno;
    document.getElementById('quiz-res-xp').textContent = '+' + xp;

    let procent = Math.round(quizPravilno / total * 100);
    if (procent >= 80) {
        document.getElementById('quiz-result-emoji').textContent = '🎉';
        document.getElementById('quiz-result-title').textContent = 'Отличный результат!';
    } else if (procent >= 50) {
        document.getElementById('quiz-result-emoji').textContent = '👍';
        document.getElementById('quiz-result-title').textContent = 'Неплохо!';
    } else {
        document.getElementById('quiz-result-emoji').textContent = '📚';
        document.getElementById('quiz-result-title').textContent = 'Нужно повторить!';
    }
}

function resetViktorimy() {
    document.getElementById('quiz-setup').classList.remove('hidden');
    document.getElementById('quiz-active').classList.add('hidden');
    document.getElementById('quiz-results').classList.add('hidden');
    quizZadachi = [];
    quizIndex = 0;
    quizPravilno = 0;
}

// ============================================
// БОССЫ
// ============================================

async function zagruzitBossov() {
    document.getElementById('bosses-list').classList.remove('hidden');
    document.getElementById('boss-battle').classList.add('hidden');
    document.getElementById('boss-result').classList.add('hidden');

    let konteyner = document.getElementById('bosses-grid');
    konteyner.innerHTML = '<p style="color: #9ca3af; grid-column: 1/-1;">Загрузка...</p>';

    try {
        let data = await apiZapros('/api/bosses?user_id=' + tekushiyUser.id);
        let bossy = data.bosses || [];

        if (bossy.length === 0) {
            konteyner.innerHTML = '<p style="color: #9ca3af; grid-column: 1/-1; text-align: center; padding: 40px;">Боссы не найдены</p>';
            return;
        }

        let html = '';
        bossy.forEach(boss => {
            let defeated = boss.is_defeated;
            let locked = boss.is_locked;
            let diffClass = 'boss-difficulty-' + boss.difficulty_level;

            html += `
                <div class="boss-card ${diffClass} ${defeated ? 'defeated' : ''} ${locked ? 'locked' : ''}"
                     onclick="${locked ? '' : 'nachatBossBattle(' + boss.id + ')'}">
                    <div style="padding: 20px;">
                        ${defeated ? '<div style="position: absolute; top: 12px; right: 12px; background: rgba(16,185,129,0.2); border: 1px solid #10b981; border-radius: 20px; padding: 2px 10px; font-size: 0.7rem; color: #10b981;">Побеждён</div>' : ''}
                        ${locked ? '<div style="position: absolute; top: 12px; right: 12px; font-size: 1.2rem;">🔒</div>' : ''}

                        <div style="font-size: 3rem; text-align: center; margin-bottom: 12px;">
                            ${boss.boss_image ? `<img src="${boss.boss_image}" alt="${boss.boss_name}" style="width: 80px; height: 80px; object-fit: contain; margin: 0 auto; display: block;">` : '👾'}
                        </div>

                        <h3 style="font-size: 1.2rem; font-weight: 700; text-align: center; margin-bottom: 8px;">${boss.boss_name}</h3>
                        <p style="color: #9ca3af; font-size: 0.85rem; text-align: center; margin-bottom: 16px; line-height: 1.4;">${boss.boss_description || ''}</p>

                        <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #9ca3af;">
                            <span>Сложность: ${'★'.repeat(boss.difficulty_level)}${'☆'.repeat(3 - boss.difficulty_level)}</span>
                            <span>+${boss.reward_xp} XP</span>
                        </div>

                        ${boss.best_time ? `<div style="margin-top: 8px; font-size: 0.75rem; color: #10b981;">Лучшее время: ${formatVremya(Math.round(boss.best_time))}</div>` : ''}
                        ${boss.attempts ? `<div style="font-size: 0.75rem; color: #9ca3af;">Попыток: ${boss.attempts}</div>` : ''}
                    </div>
                </div>
            `;
        });

        konteyner.innerHTML = html;

    } catch (err) {
        konteyner.innerHTML = '<p style="color: #ef4444; grid-column: 1/-1; text-align: center;">Ошибка загрузки боссов</p>';
    }
}

async function nachatBossBattle(bossId) {
    try {
        let data = await apiZapros('/api/bosses/' + bossId + '/start?user_id=' + tekushiyUser.id, {
            method: 'POST'
        });

        tekushiyBoss = data.boss;
        bossZadachi = data.tasks;
        bossIndex = 0;
        bossPravilno = 0;
        bossHpBoss = tekushiyBoss.boss_hp;
        bossHpPlayer = 100;

        document.getElementById('bosses-list').classList.add('hidden');
        document.getElementById('boss-battle').classList.remove('hidden');
        document.getElementById('boss-result').classList.add('hidden');

        document.getElementById('battle-boss-name').textContent = tekushiyBoss.boss_name;
        document.getElementById('battle-player-name').textContent = tekushiyUser.name || 'Игрок';
        document.getElementById('battle-q-total').textContent = bossZadachi.length;
        document.getElementById('battle-boss-hp-max').textContent = bossHpBoss;
        document.getElementById('battle-player-hp-max').textContent = bossHpPlayer;

        pokazatVoprosBoss();

    } catch (err) {
        showToast('error', 'Ошибка: ' + err.message);
    }
}

function pokazatVoprosBoss() {
    if (bossIndex >= bossZadachi.length) {
        zavershitBossBattle(true);
        return;
    }

    let zadacha = bossZadachi[bossIndex];

    document.getElementById('battle-q-current').textContent = bossIndex + 1;
    document.getElementById('battle-topic').textContent = zadacha.topic || 'Вопрос';
    document.getElementById('battle-question').textContent = zadacha.question;
    document.getElementById('battle-next-btn').disabled = true;

    let progress = (bossIndex / bossZadachi.length) * 100;
    document.getElementById('battle-progress').style.width = progress + '%';

    let konteyner = document.getElementById('battle-options');
    konteyner.innerHTML = '';

    zadacha.options.forEach(opt => {
        let div = document.createElement('div');
        div.className = 'task-option';
        div.textContent = opt;
        div.onclick = () => vybratOtvetBoss(div, opt);
        konteyner.appendChild(div);
    });

    bossSekundy = 30;
    document.getElementById('battle-timer').textContent = bossSekundy;

    if (bossTimer) clearInterval(bossTimer);
    bossTimer = setInterval(() => {
        bossSekundy--;
        document.getElementById('battle-timer').textContent = bossSekundy;
        if (bossSekundy <= 0) {
            clearInterval(bossTimer);
            nevernyiOtvetBoss();
        }
    }, 1000);
}

function vybratOtvetBoss(element, otvet) {
    if (bossTimer) clearInterval(bossTimer);

    let zadacha = bossZadachi[bossIndex];
    let vse = document.querySelectorAll('#battle-options .task-option');
    vse.forEach(o => { o.onclick = null; });

    if (otvet === zadacha.answer) {
        element.classList.add('correct');
        bossPravilno++;

        let uronBossu = Math.floor(bossHpBoss / bossZadachi.length);
        bossHpBoss = Math.max(0, bossHpBoss - uronBossu);
        obnovitHpBoss();
    } else {
        element.classList.add('wrong');
        vse.forEach(o => { if (o.textContent === zadacha.answer) o.classList.add('correct'); });
        nevernyiOtvetBoss(false);
    }

    document.getElementById('battle-next-btn').disabled = false;
}

function nevernyiOtvetBoss(updateUI) {
    let uronIgroku = 20;
    bossHpPlayer = Math.max(0, bossHpPlayer - uronIgroku);
    obnovitHpBoss();

    if (bossHpPlayer <= 0) {
        zavershitBossBattle(false);
        return;
    }

    if (updateUI !== false) {
        document.getElementById('battle-next-btn').disabled = false;
    }
}

function obnovitHpBoss() {
    let bossProc = (bossHpBoss / tekushiyBoss.boss_hp) * 100;
    let playerProc = bossHpPlayer;

    document.getElementById('battle-boss-hp').style.width = bossProc + '%';
    document.getElementById('battle-player-hp').style.width = playerProc + '%';
    document.getElementById('battle-boss-hp-val').textContent = bossHpBoss;
    document.getElementById('battle-player-hp-val').textContent = bossHpPlayer;
}

function sleduushiyVoprosBoss() {
    if (bossTimer) clearInterval(bossTimer);
    bossIndex++;

    if (bossHpPlayer <= 0) {
        zavershitBossBattle(false);
        return;
    }

    pokazatVoprosBoss();
}

async function zavershitBossBattle(pobeda) {
    if (bossTimer) clearInterval(bossTimer);

    let xp = pobeda ? tekushiyBoss.reward_xp : Math.floor(tekushiyBoss.reward_xp * 0.1);

    try {
        let result = await apiZapros('/api/bosses/' + tekushiyBoss.id + '/result', {
            method: 'POST',
            body: {
                user_id: tekushiyUser.id,
                victory: pobeda,
                correct_answers: bossPravilno,
                total_questions: bossZadachi.length,
                xp_earned: xp
            }
        });

        if (result.success) {
            tekushiyUser = result.user;
            localStorage.setItem('deltarune_user', JSON.stringify(tekushiyUser));
            obnovitUserInfo();
        }
    } catch (err) {
        console.error('Ошибка сохранения результата:', err);
    }

    document.getElementById('boss-battle').classList.add('hidden');
    document.getElementById('boss-result').classList.remove('hidden');

    document.getElementById('boss-result-emoji').textContent = pobeda ? '🏆' : '💀';
    document.getElementById('boss-result-title').textContent = pobeda ? 'Победа!' : 'Поражение...';
    document.getElementById('boss-result-desc').textContent = pobeda
        ? tekushiyBoss.boss_name + ' повержен!'
        : 'Попробуй ещё раз!';
    document.getElementById('boss-res-correct').textContent = bossPravilno + '/' + bossZadachi.length;
    document.getElementById('boss-res-xp').textContent = '+' + xp;
}

function vernutsyaKBossam() {
    if (bossTimer) clearInterval(bossTimer);
    document.getElementById('boss-battle').classList.add('hidden');
    document.getElementById('boss-result').classList.add('hidden');
    zagruzitBossov();
}

// ============================================
// БЕСКОНЕЧНЫЙ РЕЖИМ
// ============================================

async function zagruzitEndlessRekord() {
    try {
        let data = await apiZapros('/api/endless/best?user_id=' + tekushiyUser.id);
        document.getElementById('endless-best-time').textContent = formatVremya(data.best_time || 0);
        document.getElementById('endless-best-score').textContent = data.best_score || 0;
    } catch (err) {
        console.error('Ошибка загрузки рекорда:', err);
    }
}

async function nachatEndless() {
    let subject = document.getElementById('endless-subject').value;

    try {
        let result = await apiZapros('/api/quiz/start?count=100&user_id=' + tekushiyUser.id +
            (subject !== 'all' ? '&subject=' + subject : ''), { method: 'POST' });

        endlessZadachi = result.tasks;
        endlessIndex = 0;
        endlessPravilno = 0;
        endlessSekundy = 0;
        endlessLives = 3;
        endlessActive = true;

        document.getElementById('endless-setup').classList.add('hidden');
        document.getElementById('endless-result').classList.add('hidden');
        document.getElementById('endless-active').classList.remove('hidden');

        if (endlessTimer) clearInterval(endlessTimer);
        endlessTimer = setInterval(() => {
            endlessSekundy++;
            document.getElementById('endless-timer').textContent = formatVremya(endlessSekundy);
        }, 1000);

        pokazatVoprosEndless();
    } catch (err) {
        showToast('error', 'Ошибка: ' + err.message);
    }
}

function pokazatVoprosEndless() {
    if (!endlessActive) return;

    if (endlessIndex >= endlessZadachi.length) {
        endlessZadachi = [...endlessZadachi];
        endlessIndex = 0;
    }

    let zadacha = endlessZadachi[endlessIndex];

    document.getElementById('endless-topic').textContent = zadacha.topic || 'Вопрос';
    document.getElementById('endless-question').textContent = zadacha.question;
    document.getElementById('endless-correct').textContent = endlessPravilno;

    let zhizni = '';
    for (let i = 0; i < 3; i++) {
        zhizni += i < endlessLives ? '❤' : '🖤';
    }
    document.getElementById('endless-lives').textContent = zhizni;

    let konteyner = document.getElementById('endless-options');
    konteyner.innerHTML = '';

    zadacha.options.forEach(opt => {
        let div = document.createElement('div');
        div.className = 'task-option';
        div.textContent = opt;
        div.onclick = () => vybratOtvetEndless(div, opt);
        konteyner.appendChild(div);
    });

    endlessQSekundy = 15;
    document.getElementById('endless-q-timer').textContent = endlessQSekundy;

    if (endlessQTimer) clearInterval(endlessQTimer);
    endlessQTimer = setInterval(() => {
        endlessQSekundy--;
        document.getElementById('endless-q-timer').textContent = endlessQSekundy;
        if (endlessQSekundy <= 0) {
            clearInterval(endlessQTimer);
            endlessLives--;
            if (endlessLives <= 0) {
                zavershitEndless();
            } else {
                endlessIndex++;
                pokazatVoprosEndless();
            }
        }
    }, 1000);
}

function vybratOtvetEndless(element, otvet) {
    if (endlessQTimer) clearInterval(endlessQTimer);

    let zadacha = endlessZadachi[endlessIndex];
    let vse = document.querySelectorAll('#endless-options .task-option');
    vse.forEach(o => { o.onclick = null; });

    if (otvet === zadacha.answer) {
        element.classList.add('correct');
        endlessPravilno++;
    } else {
        element.classList.add('wrong');
        vse.forEach(o => { if (o.textContent === zadacha.answer) o.classList.add('correct'); });
        endlessLives--;
    }

    if (endlessLives <= 0) {
        setTimeout(zavershitEndless, 800);
    } else {
        endlessIndex++;
        setTimeout(pokazatVoprosEndless, 800);
    }
}

async function zavershitEndless() {
    if (endlessTimer) clearInterval(endlessTimer);
    if (endlessQTimer) clearInterval(endlessQTimer);
    endlessActive = false;

    let xp = Math.floor(endlessSekundy / 10) + endlessPravilno * 5;

    let bestTime = 0;
    try {
        let best = await apiZapros('/api/endless/best?user_id=' + tekushiyUser.id);
        bestTime = best.best_time || 0;
    } catch (e) {}

    let novyiRekord = endlessSekundy > bestTime;

    try {
        let result = await apiZapros('/api/endless/result', {
            method: 'POST',
            body: {
                user_id: tekushiyUser.id,
                time_survived: endlessSekundy,
                correct_answers: endlessPravilno,
                xp_earned: xp
            }
        });

        if (result.success) {
            tekushiyUser = result.user;
            localStorage.setItem('deltarune_user', JSON.stringify(tekushiyUser));
            obnovitUserInfo();
        }
    } catch (err) {
        console.error('Ошибка сохранения:', err);
    }

    document.getElementById('endless-active').classList.add('hidden');
    document.getElementById('endless-result').classList.remove('hidden');

    document.getElementById('endless-res-time').textContent = formatVremya(endlessSekundy);
    document.getElementById('endless-res-correct').textContent = endlessPravilno;
    document.getElementById('endless-res-xp').textContent = '+' + xp;

    if (novyiRekord) {
        document.getElementById('endless-new-record').classList.remove('hidden');
    } else {
        document.getElementById('endless-new-record').classList.add('hidden');
    }
}

function resetEndless() {
    document.getElementById('endless-setup').classList.remove('hidden');
    document.getElementById('endless-active').classList.add('hidden');
    document.getElementById('endless-result').classList.add('hidden');
    zagruzitEndlessRekord();
}

// ============================================
// АЙСБЕРГ ФАКТОВ
// ============================================

async function zagruzitAysberg() {
    document.getElementById('iceberg-view').classList.remove('hidden');
    document.getElementById('fact-page').classList.add('hidden');

    try {
        let data = await apiZapros('/api/iceberg/facts');
        ibergFakty = data.facts || [];

        renderIcebergButtons();
        renderIcebergList();

    } catch (err) {
        console.error('Ошибка загрузки фактов:', err);
    }
}

function renderIcebergButtons() {
    let konteyner = document.getElementById('iceberg-buttons');
    konteyner.innerHTML = '';

    ibergFakty.forEach((fact, index) => {
        if (fact.position_x && fact.position_y) {
            let btn = document.createElement('button');
            btn.className = 'fact-btn level-' + fact.level;
            btn.style.left = fact.position_x + 'px';
            btn.style.top = fact.position_y + 'px';
            btn.textContent = index + 1;
            btn.title = fact.title;
            btn.onclick = () => otkrytFakt(fact);
            konteyner.appendChild(btn);
        }
    });
}

function renderIcebergList() {
    let konteyner = document.getElementById('iceberg-facts-list');
    let html = '';

    let levels = [1, 2, 3, 4, 5];
    levels.forEach(level => {
        let faktyUrovnya = ibergFakty.filter(f => f.level === level);
        if (faktyUrovnya.length === 0) return;

        let color = getLevelColor(level);
        html += `<div style="font-size: 0.75rem; font-weight: 700; color: ${color.text}; margin-top: 12px; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 1px;">
            Уровень ${level}
        </div>`;

        faktyUrovnya.forEach(fact => {
            html += `
                <div onclick="otkrytFakt(${JSON.stringify(fact).replace(/"/g, '&quot;')})"
                     style="padding: 10px 14px; background: rgba(255,255,255,0.03); border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; transition: background 0.2s;"
                     onmouseover="this.style.background='rgba(168,85,247,0.08)'"
                     onmouseout="this.style.background='rgba(255,255,255,0.03)'">
                    <span style="font-size: 0.9rem;">${fact.title}</span>
                    <span style="font-size: 0.75rem; color: ${color.text}; margin-left: 12px; flex-shrink: 0;">Ур. ${fact.level}</span>
                </div>
            `;
        });
    });

    konteyner.innerHTML = html;
}

function otkrytFakt(fact) {
    if (typeof fact === 'string') {
        try { fact = JSON.parse(fact); } catch (e) { return; }
    }

    let color = getLevelColor(fact.level);

    let badge = document.getElementById('modal-fact-level-badge');
    badge.textContent = color.label;
    badge.style.background = color.bg;
    badge.style.border = '1px solid ' + color.border;
    badge.style.color = color.text;
    badge.style.padding = '4px 12px';
    badge.style.borderRadius = '20px';
    badge.style.fontSize = '0.75rem';
    badge.style.fontWeight = '600';
    badge.style.marginBottom = '12px';
    badge.style.display = 'inline-block';

    document.getElementById('modal-fact-title').textContent = fact.title;
    document.getElementById('modal-fact-content').textContent = fact.content;

    document.getElementById('fact-modal').classList.remove('hidden');

    zaregistrirovatProsmotr(fact.id);
}

function zakrytModalFakta() {
    document.getElementById('fact-modal').classList.add('hidden');
}

async function zaregistrirovatProsmotr(factId) {
    try {
        await apiZapros('/api/iceberg/view', {
            method: 'POST',
            body: { user_id: tekushiyUser.id, fact_id: factId }
        });
    } catch (err) {
        console.error('Ошибка регистрации просмотра:', err);
    }
}

function vernutsyaKAysberg() {
    document.getElementById('iceberg-view').classList.remove('hidden');
    document.getElementById('fact-page').classList.add('hidden');
}

// ============================================
// РЕЙТИНГ
// ============================================

async function zagruzitLiderboard() {
    let konteyner = document.getElementById('leaderboard-list');
    konteyner.innerHTML = '<p style="color: #9ca3af; text-align: center; padding: 40px;">Загрузка...</p>';

    try {
        let data = await apiZapros('/api/leaderboard?filter=' + tekushiyLeaderboardFilter + '&limit=50');
        let users = data.users || data || [];

        if (users.length === 0) {
            konteyner.innerHTML = '<p style="color: #9ca3af; text-align: center; padding: 40px;">Нет данных</p>';
            return;
        }

        let html = '';
        users.forEach((user, idx) => {
            let rank = idx + 1;
            let medalya = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '#' + rank;
            let rankClass = rank === 1 ? 'gold' : rank === 2 ? 'silver' : rank === 3 ? 'bronze' : '';
            let rowClass = rank <= 3 ? 'top-' + rank : '';
            let moy = user.id === tekushiyUser.id ? 'my-row' : '';

            let mainValue = user.rating || 1000;
            let mainLabel = 'рейтинг';

            if (tekushiyLeaderboardFilter === 'bosses') {
                mainValue = (user.bosses_defeated || 0) + '/3';
                mainLabel = 'боссов';
            } else if (tekushiyLeaderboardFilter === 'endless') {
                mainValue = formatVremya(user.best_endless_time || 0);
                mainLabel = 'время';
            } else if (tekushiyLeaderboardFilter === 'quiz') {
                mainValue = user.solved_count || 0;
                mainLabel = 'вопросов';
            }

            html += `
                <div class="leaderboard-row ${rowClass} ${moy}">
                    <div class="rank-badge ${rankClass}">${medalya}</div>
                    <div style="flex: 1;">
                        <div style="font-weight: 600;">${user.name || user.username}</div>
                        <div style="font-size: 0.75rem; color: #9ca3af;">Уровень ${user.level || 1}</div>
                    </div>
                    <div style="text-align: right;">
                        <div style="font-size: 1.3rem; font-weight: 800; color: #a855f7;">${mainValue}</div>
                        <div style="font-size: 0.7rem; color: #9ca3af;">${mainLabel}</div>
                    </div>
                </div>
            `;
        });

        konteyner.innerHTML = html;

    } catch (err) {
        konteyner.innerHTML = '<p style="color: #ef4444; text-align: center; padding: 40px;">Ошибка загрузки рейтинга</p>';
    }
}

function filterLeaderboard(filter, btn) {
    tekushiyLeaderboardFilter = filter;

    document.querySelectorAll('.tabs-container .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    zagruzitLiderboard();
}

// ============================================
// ПРОФИЛЬ
// ============================================

function obnovitProfil() {
    let imya = tekushiyUser.name || tekushiyUser.username || 'Игрок';
    let bukva = imya.charAt(0).toUpperCase();

    document.getElementById('profile-avatar').textContent = bukva;
    document.getElementById('profile-name').textContent = imya;
    document.getElementById('profile-email').textContent = tekushiyUser.email || '';
    document.getElementById('profile-level').textContent = tekushiyUser.level || 1;
    document.getElementById('profile-xp').textContent = tekushiyUser.xp || 0;
    document.getElementById('profile-rating').textContent = tekushiyUser.rating || 1000;
    document.getElementById('profile-solved').textContent = tekushiyUser.solved_count || 0;
    document.getElementById('profile-bosses').textContent = (tekushiyUser.bosses_defeated || 0) + '/3';

    let solved = tekushiyUser.solved_count || 0;
    let correct = tekushiyUser.correct_count || 0;
    let tochnost = solved > 0 ? Math.round(correct / solved * 100) : 0;
    document.getElementById('profile-accuracy').textContent = tochnost + '%';

    let xpDlyaLvla = (tekushiyUser.level || 1) * 100;
    let ostatok = (tekushiyUser.xp || 0) % xpDlyaLvla;
    let procent = (ostatok / xpDlyaLvla) * 100;
    document.getElementById('profile-xp-bar').style.width = procent + '%';

    pokazatDostizheniya('profile-achievements');

    let subjectStats = tekushiyUser.subject_stats || {};
    let konteyner = document.getElementById('profile-subject-stats');

    try {
        if (typeof subjectStats === 'string') subjectStats = JSON.parse(subjectStats);
    } catch (e) {}

    let predmety = { 'deltarune': 'Deltarune', 'undertale': 'Undertale' };
    let html = '';

    for (let key in predmety) {
        let stat = subjectStats[key] || { solved: 0, correct: 0 };
        let proc = stat.solved > 0 ? Math.round(stat.correct / stat.solved * 100) : 0;

        html += `
            <div style="padding: 14px; background: rgba(255,255,255,0.03); border-radius: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="font-weight: 600;">${predmety[key]}</span>
                    <span style="color: #9ca3af; font-size: 0.85rem;">${stat.solved} вопросов · ${proc}%</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${proc}%;"></div>
                </div>
            </div>
        `;
    }

    konteyner.innerHTML = html || '<p style="color: #9ca3af; font-size: 0.85rem;">Пока нет статистики</p>';
}

// ============================================
// АДМИНКА
// ============================================

async function zagruzitAdminData() {
    await zagruzitAdminUsers();
}

async function zagruzitAdminUsers() {
    try {
        let data = await apiZapros('/api/admin/users');
        let users = data.users || data || [];

        let tbody = document.getElementById('admin-users-list');
        let html = '';

        users.forEach(u => {
            let adminMark = u.is_admin ? ' 👑' : '';
            let statusColor = u.is_active ? '#10b981' : '#ef4444';
            let statusText = u.is_active ? 'Активен' : 'Заблокирован';

            html += `
                <tr style="border-bottom: 1px solid rgba(168,85,247,0.1);">
                    <td style="padding: 10px; color: #9ca3af;">${u.id}</td>
                    <td style="padding: 10px; font-weight: 600;">${u.name || u.username}${adminMark}</td>
                    <td style="padding: 10px; color: #9ca3af;">${u.email}</td>
                    <td style="padding: 10px;">${u.level || 1}</td>
                    <td style="padding: 10px;">${u.rating || 1000}</td>
                    <td style="padding: 10px;">
                        <span style="color: ${statusColor}; font-size: 0.8rem;">${statusText}</span>
                    </td>
                    <td style="padding: 10px;">
                        <div style="display: flex; gap: 6px;">
                            ${u.is_active ?
                                `<button onclick="zablokirovatPol(${u.id})" class="btn-danger" style="padding: 4px 10px; font-size: 0.75rem;">Бан</button>` :
                                `<button onclick="razblokirovat(${u.id})" class="btn-success" style="padding: 4px 10px; font-size: 0.75rem;">Разбан</button>`
                            }
                        </div>
                    </td>
                </tr>
            `;
        });

        tbody.innerHTML = html;

    } catch (err) {
        console.error('Ошибка загрузки пользователей:', err);
    }
}

async function zablokirovatPol(userId) {
    if (!confirm('Заблокировать пользователя?')) return;

    try {
        await apiZapros('/api/admin/ban', {
            method: 'POST',
            body: { admin_id: tekushiyUser.id, user_id: userId, reason: 'Нарушение правил' }
        });
        showToast('success', 'Пользователь заблокирован');
        zagruzitAdminUsers();
    } catch (err) {
        showToast('error', 'Ошибка: ' + err.message);
    }
}

async function razblokirovat(userId) {
    try {
        await apiZapros('/api/admin/unban', {
            method: 'POST',
            body: { admin_id: tekushiyUser.id, user_id: userId }
        });
        showToast('success', 'Пользователь разблокирован');
        zagruzitAdminUsers();
    } catch (err) {
        showToast('error', 'Ошибка: ' + err.message);
    }
}

function pokazatAdminTab(tab, btn) {
    tekushiyAdminTab = tab;

    document.getElementById('admin-tab-users').classList.add('hidden');
    document.getElementById('admin-tab-tasks').classList.add('hidden');
    document.getElementById('admin-tab-facts').classList.add('hidden');
    document.getElementById('admin-tab-bosses').classList.add('hidden');

    document.getElementById('admin-tab-' + tab).classList.remove('hidden');

    document.querySelectorAll('.tabs-container .tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    if (tab === 'users') zagruzitAdminUsers();
    else if (tab === 'tasks') zagruzitAdminZadachi();
    else if (tab === 'facts') zagruzitAdminFakty();
    else if (tab === 'bosses') zagruzitAdminBossov();
}

function pokazatFormuDobavleniyaZadachi() {
    document.getElementById('admin-tasks-form').classList.remove('hidden');
}

function pokazatFormuDobavleniyaFakta() {
    document.getElementById('admin-facts-form').classList.remove('hidden');
}

async function dobavitZadachu() {
    let optionsStr = document.getElementById('admin-options').value;
    let options = optionsStr.split(';').map(o => o.trim()).filter(o => o);

    try {
        let result = await apiZapros('/api/tasks', {
            method: 'POST',
            body: {
                subject: document.getElementById('admin-subject').value,
                difficulty: document.getElementById('admin-difficulty').value,
                topic: document.getElementById('admin-topic').value,
                question: document.getElementById('admin-question').value,
                options: options,
                answer: document.getElementById('admin-answer').value,
                hint: document.getElementById('admin-hint').value,
                created_by: tekushiyUser.id
            }
        });

        if (result.success) {
            showToast('success', 'Задача добавлена!');
            document.getElementById('admin-tasks-form').classList.add('hidden');
            document.getElementById('admin-topic').value = '';
            document.getElementById('admin-question').value = '';
            document.getElementById('admin-options').value = '';
            document.getElementById('admin-answer').value = '';
            document.getElementById('admin-hint').value = '';
        }
    } catch (err) {
        showToast('error', 'Ошибка: ' + err.message);
    }
}

async function dobavitFakt() {
    try {
        let result = await apiZapros('/api/iceberg/facts', {
            method: 'POST',
            body: {
                title: document.getElementById('admin-fact-title').value,
                content: document.getElementById('admin-fact-content').value,
                level: parseInt(document.getElementById('admin-fact-level').value),
                position_x: parseInt(document.getElementById('admin-fact-x').value) || null,
                position_y: parseInt(document.getElementById('admin-fact-y').value) || null,
                created_by: tekushiyUser.id
            }
        });

        if (result.success) {
            showToast('success', 'Факт добавлен!');
            document.getElementById('admin-facts-form').classList.add('hidden');
            zagruzitAdminFakty();
        }
    } catch (err) {
        showToast('error', 'Ошибка: ' + err.message);
    }
}

async function zagruzitAdminZadachi() {
    let konteyner = document.getElementById('admin-tasks-list');
    try {
        let data = await apiZapros('/api/tasks?limit=50');
        let tasks = data.tasks || [];

        let html = '<table style="width: 100%; border-collapse: collapse; font-size: 0.8rem;">';
        html += '<tr style="border-bottom: 1px solid rgba(168,85,247,0.2);"><th style="padding: 8px; text-align: left; color: #9ca3af;">ID</th><th style="padding: 8px; text-align: left; color: #9ca3af;">Тема</th><th style="padding: 8px; text-align: left; color: #9ca3af;">Сложность</th><th style="padding: 8px; text-align: left; color: #9ca3af;">Вопрос</th></tr>';

        tasks.forEach(t => {
            html += `<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 8px; color: #9ca3af;">${t.id}</td>
                <td style="padding: 8px;">${t.subject}</td>
                <td style="padding: 8px;">${t.difficulty}</td>
                <td style="padding: 8px;">${(t.question || '').substring(0, 60)}...</td>
            </tr>`;
        });

        html += '</table>';
        konteyner.innerHTML = html;
    } catch (err) {
        konteyner.innerHTML = '<p style="color: #ef4444;">Ошибка загрузки</p>';
    }
}

async function zagruzitAdminFakty() {
    let konteyner = document.getElementById('admin-facts-list');
    try {
        let data = await apiZapros('/api/iceberg/facts');
        let fakty = data.facts || [];

        let html = '';
        fakty.forEach(f => {
            let color = getLevelColor(f.level);
            html += `
                <div style="padding: 12px; margin-bottom: 8px; background: rgba(255,255,255,0.03); border-radius: 8px; border-left: 3px solid ${color.border};">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <span style="font-weight: 600; font-size: 0.9rem;">${f.title}</span>
                            <span style="margin-left: 8px; font-size: 0.7rem; color: ${color.text};">Ур. ${f.level}</span>
                        </div>
                        <span style="font-size: 0.75rem; color: #9ca3af;">👁 ${f.views_count || 0}</span>
                    </div>
                    <p style="font-size: 0.8rem; color: #9ca3af; margin-top: 4px;">${(f.content || '').substring(0, 100)}...</p>
                </div>
            `;
        });

        konteyner.innerHTML = html;
    } catch (err) {
        konteyner.innerHTML = '<p style="color: #ef4444;">Ошибка загрузки</p>';
    }
}

async function zagruzitAdminBossov() {
    let konteyner = document.getElementById('admin-bosses-list');
    try {
        let data = await apiZapros('/api/bosses');
        let bossy = data.bosses || [];

        let html = '';
        bossy.forEach(b => {
            html += `
                <div style="padding: 14px; margin-bottom: 10px; background: rgba(255,255,255,0.03); border-radius: 10px; display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <div style="font-weight: 700;">${b.boss_name}</div>
                        <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 2px;">HP: ${b.boss_hp} | Сложность: ${'★'.repeat(b.difficulty_level)} | +${b.reward_xp} XP</div>
                    </div>
                    <div style="font-size: 0.8rem; color: ${b.is_active ? '#10b981' : '#ef4444'};">
                        ${b.is_active ? 'Активен' : 'Неактивен'}
                    </div>
                </div>
            `;
        });

        konteyner.innerHTML = html;
    } catch (err) {
        konteyner.innerHTML = '<p style="color: #ef4444;">Ошибка загрузки</p>';
    }
}

// ============================================
// ЗАКРЫТИЕ МОДАЛКИ ПО КЛИКУ ВНЕ
// ============================================

document.getElementById('fact-modal').addEventListener('click', function(e) {
    if (e.target === this) zakrytModalFakta();
});

// ============================================
// ИНИЦИАЛИЗАЦИЯ
// ============================================

window.onload = function() {
    let saved = localStorage.getItem('deltarune_user');

    if (saved) {
        try {
            tekushiyUser = JSON.parse(saved);

            apiZapros('/api/user/' + tekushiyUser.id).then(userData => {
                tekushiyUser = userData;
                localStorage.setItem('deltarune_user', JSON.stringify(tekushiyUser));
                pokazatGlavniy();
            }).catch(() => {
                pokazatGlavniy();
            });

        } catch (e) {
            localStorage.removeItem('deltarune_user');
            document.getElementById('loading-screen').classList.add('hidden');
            document.getElementById('auth-screen').classList.remove('hidden');
        }
    } else {
        document.getElementById('loading-screen').classList.add('hidden');
        document.getElementById('auth-screen').classList.remove('hidden');
    }
};
