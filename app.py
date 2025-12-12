from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
import os
import sys
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Добавляем пути для импорта

sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))


# Импортируем функцию инициализации
try:
    from services.init_service import init_recommendation_service, recommendation_service
except ImportError as e:
    print(f"❌ Не удалось импортировать init_service: {e}")
    init_recommendation_service = None
    recommendation_service = None

# Инициализируем сервис один раз при запуске приложения
MODEL_AVAILABLE = False
if init_recommendation_service:
    # Вызываем инициализацию явно
    service = init_recommendation_service()
    MODEL_AVAILABLE = service is not None
    if MODEL_AVAILABLE:
        recommendation_service = service
        print("✅ Сервис рекомендаций успешно инициализирован (один раз)")
    else:
        print("⚠️  Модель не найдена или не удалось загрузить")
        recommendation_service = None
else:
    print("❌ Функция инициализации не найдена")
    recommendation_service = None

# Путь к базе данных
DB_PATH = 'users.db'

# Загрузка данных из Parquet файла
def load_books_data():
    try:
        # Путь к Parquet файлу в папке /data
        base_dir = os.path.dirname(os.path.abspath(__file__))
        parquet_path = os.path.join(base_dir, 'data', 'books_result.parquet')
        
        print(f"Пытаюсь загрузить Parquet файл из: {parquet_path}")
        
        # Проверяем существование файла
        if not os.path.exists(parquet_path):
            print(f"❌ Файл не найден: {parquet_path}")
            return []
        
        # Загружаем данные из Parquet
        books_df = pd.read_parquet(parquet_path)
        
        # Выводим информацию о загруженных данных для отладки
        print(f"Успешно загружено {len(books_df)} книг")
        
        # Создаем словарь для быстрого поиска книг по book_id
        books_by_id = {}
        
        # Преобразуем DataFrame в список словарей
        books_data = []
        for index, row in books_df.iterrows():
            # Получаем book_id как строку
            book_id = str(row.get('book_id', ''))
            
            # Преобразуем isbn13
            isbn13 = str(row.get('isbn13', ''))
            if isbn13.endswith('.0'):
                isbn13 = isbn13[:-2]
            
            # Получаем cover_url
            cover_url = str(row.get('cover_url', '')) if pd.notna(row.get('cover_url')) else ''
            
            # Формируем книгу в нужном формате
            book = {
                'book_id': book_id,
                'id': isbn13 if isbn13 else book_id,  # Для обратной совместимости оставляем id
                'isbn13': isbn13,
                'title': str(row.get('title', 'Название не указано')),
                'author': str(row.get('authors', 'Автор не указан')),
                'cover': cover_url,
                'saved_path': str(row.get('cover_path', '')) if pd.notna(row.get('cover_path', '')) else '',
                'status': ''  # Поле для статуса
            }
            
            # Проверяем, есть ли хотя бы название
            if book['title'] != 'Название не указано':
                books_data.append(book)
                # Сохраняем в словаре для быстрого поиска
                books_by_id[book_id] = book
        
        print(f"Успешно обработано {len(books_data)} книг")
        
        # Сохраняем словарь для быстрого поиска в глобальной переменной
        global books_by_id_dict
        books_by_id_dict = books_by_id
        
        return books_data
        
    except Exception as e:
        print(f"Ошибка при загрузке Parquet файла: {e}")
        import traceback
        traceback.print_exc()
        return []
    
# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Загружаем данные при старте приложения
init_db()
all_books_data = load_books_data()
books_by_id_dict = {}

# Функция поиска книг
def search_books(query):
    if not query or not all_books_data:
        return []
    
    query_lower = query.lower()
    results = []
    
    for book in all_books_data:
        # Поиск по названию
        title_match = query_lower in book['title'].lower() if book['title'] else False
        
        # Поиск по автору
        author_match = query_lower in book['author'].lower() if book['author'] else False
        
        if title_match or author_match:
            results.append(book)
    
    # Сортируем по релевантности (сначала точные совпадения по названию)
    results.sort(key=lambda x: (
        query_lower == x['title'].lower() if x['title'] else False,
        query_lower in x['title'].lower() if x['title'] else False,
        query_lower in x['author'].lower() if x['author'] else False
    ), reverse=True)
    
    return results

# Главная страница
@app.route('/')
def index():
    if 'user_id' in session:
        print(f"user_id = {session.get('user_id', 1)}")
        # Получаем поисковый запрос если есть
        search_query = request.args.get('search', '').strip()
        
        if search_query:
            # Ищем книги по запросу
            search_results = search_books(search_query)
            return render_template('form.html', 
                                 books=search_results, 
                                 username=session.get('username'),
                                 search_query=search_query,
                                 is_search=True,
                                 results_count=len(search_results))
        else:
            
            # Показываем книги с обложками для отображения            
            return render_template('form.html', 
                                 books=all_books_data, 
                                 username=session.get('username'),
                                 search_query='',
                                 is_search=False,
                                 results_count=len(all_books_data))
    return redirect(url_for('login'))

# Страница регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Проверка паролей
        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')
        
        # Хеширование пароля
        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect('users.db')
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            conn.commit()
            conn.close()
            
            flash('Регистрация успешна! Теперь вы можете войти.', 'success')
            return redirect(url_for('login'))
            
        except sqlite3.IntegrityError:
            flash('Пользователь с таким именем или email уже существует', 'error')
        except Exception as e:
            flash('Ошибка при регистрации', 'error')
            print(f"Ошибка регистрации: {e}")
    
    return render_template('register.html')

# Страница входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]
            session['username'] = user[1]
            session['email'] = user[2]
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
    
    return render_template('login.html')

# Выход
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))

# Новый маршрут для получения рекомендаций
@app.route('/recommend/<book_id>')
def recommend(book_id):
    # Находим книгу по ID
    book = next((b for b in all_books_data if b['id'] == book_id), None)
    if book:
        # Здесь будет логика получения рекомендаций
        return f"Рекомендации для книги: {book['title']}"
    else:
        return "Книга не найдена"

# Страница контекстных рекомендаций
@app.route('/context_recommendations')
def context_recommendations_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Получаем контекст из сессии (если был сохранен)
    context = session.get('last_context', '')
    recommendations = session.get('last_recommendations', [])
    
    return render_template(
        'context_recommendations.html',
        username=session.get('username'),
        context=context,
        recommendations=recommendations,
        recommendations_count=len(recommendations)
    )

# API для контекстных рекомендаций
@app.route('/api/context_recommendations', methods=['POST'])
def get_context_recommendations():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходима авторизация'}), 401
    
    try:
        data = request.get_json()
        context_text = data.get('context', '').strip()
        
        if not context_text:
            return jsonify({'success': False, 'message': 'Введите текст для рекомендации'}), 400
        
        print(f"Получен контекст для рекомендаций: {context_text[:100]}...")
        
        # Проверяем доступность сервиса рекомендаций
        if recommendation_service is None:
            # Используем тестовые данные если модель не загружена
            recommendations = generate_test_recommendations(context_text)
        else:
            # Используем реальную модель
            # Получаем user_id из сессии (конвертируем для модели)
            user_id_for_model = session.get('user_id', 1)
            
            # Получаем рекомендации из модели
            result = recommendation_service.recommend_for_user(
                user_id=user_id_for_model,
                context=context_text,
                top_k=12,
                max_books=2000  # Можно регулировать производительность
            )

        if result['status'] == 'success':
            # Преобразуем рекомендации в нужный формат
            recommendations = []
            for rec in result['recommendations']:
                # Ищем книгу в наших данных по book_id
                rec_book_id = str(rec.get('book_id', ''))
                
                # Поиск в словаре по book_id
                book_data = None
                if rec_book_id in books_by_id_dict:
                    book_data = books_by_id_dict[rec_book_id]
                else:
                    # Если не нашли по book_id, ищем по названию (для обратной совместимости)
                    for book in all_books_data:
                        if book['title'].lower() == rec['title'].lower():
                            book_data = book
                            break
                
                if book_data:
                    recommendations.append({
                        'id': book_data.get('id', ''),
                        'book_id': book_data.get('book_id', ''),
                        'title': rec['title'],
                        'author': rec['author'],
                        'cover': book_data.get('cover', '/static/images/error_pic_4.jpg'),
                        'score': rec['score'],
                        'reason': f"Рекомендовано моделью с оценкой {rec['score']:.2f}"
                    })
                else:
                    # Если книга не найдена, используем данные из рекомендации
                    recommendations.append({
                        'id': rec_book_id,
                        'book_id': rec_book_id,
                        'title': rec['title'],
                        'author': rec['author'],
                        'cover': '/static/images/no_cover.jpg',
                        'score': rec['score'],
                        'reason': f"Рекомендовано моделью с оценкой {rec['score']:.2f}"
                    })
        else:
            # Если модель вернула ошибку, используем тестовые данные
            print(f"Ошибка модели: {result.get('message', 'Unknown error')}")
            recommendations = generate_test_recommendations(context_text)


        # Сохраняем в сессии для отображения на отдельной странице
        session['last_context'] = context_text
        session['last_recommendations'] = recommendations
        
        return jsonify({
            'success': True,
            'redirect_url': url_for('context_recommendations_page'),
            'recommendations_count': len(recommendations)
        })
        
    except Exception as e:
        print(f"Ошибка при получении контекстных рекомендаций: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

def generate_test_recommendations(context_text):
    """Генерация тестовых рекомендаций"""
    # Используем первые 10 книг из загруженных данных как тестовые
    test_books = all_books_data[:10] if len(all_books_data) > 10 else all_books_data
    
    for i, book in enumerate(test_books):
        book['score'] = 0.9 - (i * 0.1)  # Имитация рейтинга
        book['reason'] = f'Подходит по теме "{context_text[:20]}..."'
    
    return test_books[:4]

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)