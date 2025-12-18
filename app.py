from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pandas as pd
import os
import sys
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

import time
import json
from datetime import datetime

LOG_PATH = "inference_logs.jsonl"

def log_inference(
    endpoint: str,
    user_id: int,
    model: str,
    inference_time: float,
    status: str,
    **kwargs
):
    log_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "user_id": user_id,
        "model": model,
        "inference_time_ms": round(inference_time * 1000, 3),
        "status": status,
        **kwargs
    }

    # режим ДОЗАПИСИ
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_record, ensure_ascii=False) + "\n")

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Добавляем пути для импорта

sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))


# Импортируем функцию инициализации
try:
    from services.init_service import init_recommendation_service, recommendation_service
    from services.simple_recommender_service import get_simple_recommender
except ImportError as e:
    print(f"❌ Не удалось импортировать init_service: {e}")
    init_recommendation_service = None
    recommendation_service = None
    simple_recommender = None 

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

# Инициализация простого сервиса
try:
    simple_recommender = get_simple_recommender()
    #simple_recommender=None
    if simple_recommender:
        print()
    else:
        print("⚠️  Не удалось загрузить SimpleRecommender")
except Exception as e:
    print(f"❌ Ошибка при инициализации SimpleRecommender: {e}")
    simple_recommender = None

# Путь к базе данных
DB_PATH = 'books_recommender.db'

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
        
        
        return books_data, books_by_id
        
    except Exception as e:
        print(f"Ошибка при загрузке Parquet файла: {e}")
        import traceback
        traceback.print_exc()
        return []
 
# Загружаем данные при старте приложения

all_books_data, books_by_id_dict = load_books_data()
#print(f"[DEBUG] Создан словарь книг по book_id: {len(books_by_id_dict)} записей")
#print(f"[DEBUG] Пример ключей: {list(books_by_id_dict.keys())[:5]}")
#print(f"[DEBUG] Пример данных первой книги: {list(books_by_id_dict.values())[0] if books_by_id_dict else 'Словарь пуст'}")

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
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()

            # Генерируем уникальный user_id
            cursor.execute('SELECT MAX(user_id) FROM users')
            max_id = cursor.fetchone()[0]
            new_user_id = (max_id or 0) + 1

            cursor.execute(
                'INSERT INTO users (user_id, username, email, password) VALUES (?, ?, ?, ?)',
                (new_user_id, username, email, hashed_password)
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
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[3], password):
            session['user_id'] = user[0]  # user_id теперь в первом столбце
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


# =============================================
# API для контекстных рекомендаций (старый сервис)
# =============================================

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
            k=12
            start_time = time.perf_counter()

            # Получаем рекомендации из модели
            result = recommendation_service.recommend_for_user(
                user_id=user_id_for_model,
                context=context_text,
                top_k=k,
                max_books=2000  # Можно регулировать производительность
            )

            
            inference_time = time.perf_counter() - start_time
            '''
            log_inference(
                endpoint="/api/context_recommendations",
                user_id=user_id_for_model,
                model="context_recommender",
                inference_time=inference_time,
                status=result.get("status", "error"),
                top_k=k,
                max_books=2000,
                recommendations_count=len(result.get("recommendations", []))
            )
            '''
        
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
# =============================================
# API для простых рекомендаций (SimpleRecommender)
# =============================================

@app.route('/api/simple/recommend/me')
def simple_recommend_for_me():
    """Получить простые рекомендации для текущего пользователя"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Необходима авторизация'}), 401
    
    try:
        # Проверяем доступность сервиса рекомендаций
        if simple_recommender is None:
            # Используем тестовые данные если модель не загружена
            recommendations = generate_test_recommendations("ваши персональные рекомендации")
        else:
            # Используем реальную модель
            user_id = session.get('user_id', 1)
            k=10
            #k = request.args.get('k', default=6, type=int)
            start_time = time.perf_counter()
            # Получаем рекомендации из модели
            result = simple_recommender.recommend_for_user(
                user_id=user_id,
                k=min(k, 20)
            )
            inference_time = time.perf_counter() - start_time
            '''
            log_inference(
                endpoint="/api/simple/recommend/me",
                user_id=user_id,
                model="simple_recommender",
                inference_time=inference_time,
                status=result.get("status", "error"),
                top_k=k,
                max_books=0,
                recommendations_count=len(result.get("recommendations", []))
            )
            '''



            # Преобразуем рекомендации в нужный формат
            recommendations = []
            if result.get('status') == 'success' and 'recommendations' in result:
                for rec in result['recommendations']:
                    # Ищем книгу в наших данных по book_id
                    rec_book_id = str(rec.get('item_id', ''))
                    
                    
                    # Поиск в словаре по book_id
                    book_data = None
                    if rec_book_id in books_by_id_dict:
                        book_data = books_by_id_dict[rec_book_id]
                    else:
                        # Если не нашли по book_id, ищем по названию
                        for book in all_books_data:
                            if book['title'].lower() == rec['title'].lower():
                                book_data = book
                                break

                    if book_data:
                        recommendations.append({
                            'id': book_data.get('id', rec_book_id),
                            'book_id': rec_book_id,
                            'title': book_data.get('title', rec.get('title', 'Название не указано')),
                            'author': book_data.get('author', rec.get('author', 'Автор не указан')),
                            'cover':  book_data.get('cover', '/static/images/error_pic_4.jpg'),
                            'score': rec.get('score', 0.5),
                            'reason': rec.get('reason', f"Рекомендовано на основе ваших оценок")
                        })
                    else:
                        # Если книга не найдена, используем данные из рекомендации
                        recommendations.append({
                            'id': rec_book_id,
                            'book_id': rec_book_id,
                            'title': rec.get('title', f'Book {rec_book_id}'),
                            'author': rec.get('author', f'Author of {rec_book_id}'),
                            'cover': '/static/images/error_pic_1.jpg',
                            'score': rec.get('score', 0.5),
                            'reason': rec.get('reason', 'Рекомендовано на основе ваших оценок')
                        })
            else:
                # Если модель вернула ошибку, используем тестовые данные
                recommendations = generate_test_recommendations("ваши персональные рекомендации")
        
        # Возвращаем в том же формате, что и контекстные рекомендации
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'recommendations_count': len(recommendations)
        })
        
    except Exception as e:
        print(f"❌ Ошибка в simple_recommend_for_me: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/simple/similar/<book_id>')
def simple_similar_books(book_id):
    """Получить похожие книги через SimpleRecommender"""
    try:
        # Проверяем доступность сервиса рекомендаций
        if simple_recommender is None:
            # Используем тестовые данные если модель не загружена
            recommendations = generate_test_recommendations(f"похожие на книгу {book_id}")
            
            return jsonify({
                'success': True,
                'recommendations': recommendations,
                'recommendations_count': len(recommendations)
            })
        
        k=9
        #k = request.args.get('k', default=6, type=int)
        method = request.args.get('method', default='hybrid', type=str)
        
        # Допустимые методы
        valid_methods = ['als', 'content', 'hybrid']
        if method not in valid_methods:
            method = 'hybrid'
        start_time = time.perf_counter()

        # Получаем похожие книги
        result = simple_recommender.similar_items(
            item_id=book_id,
            k=min(k, 20),
            method=method
        )
        # Замер времени инференса
        inference_time = time.perf_counter() - start_time
        '''
        log_inference(
                endpoint="api/simple/similar",
                user_id=book_id,
                model="book_simple_recommender",
                inference_time=inference_time,
                status=result.get("status", "error"),
                top_k=k,
                max_books=0,
                recommendations_count=len(result.get("recommendations", []))
            )
        '''
        # Преобразуем рекомендации в нужный формат
        recommendations = []
        if result.get('status') == 'success' and 'recommendations' in result:
            # Получаем информацию о базовой книге
            base_book_info = result.get('base_book', {})
            base_book_id = base_book_info.get('book_id', book_id)
            #base_book_title = base_book_info.get('title', f'Книга {book_id}')
            #base_book_author = base_book_info.get('author', 'Автор не указан')

            base_book_data = books_by_id_dict[base_book_id]
            base_book_title = base_book_data.get('title', f'Книга {book_id}')
            base_book_author = base_book_data.get('author', 'Автор не указан')
            
            for rec in result['recommendations']:
                # Ищем книгу в наших данных по book_id
                rec_book_id = str(rec.get('book_id', ''))
                
                # Поиск в словаре по book_id
                book_data = None
                if rec_book_id in books_by_id_dict:
                    book_data = books_by_id_dict[rec_book_id]
                else:
                    # Если не нашли по book_id, ищем по названию
                    for book in all_books_data:
                        if book['title'].lower() == rec['title'].lower():
                            book_data = book
                            break
                
                if book_data:
                    recommendations.append({
                        'id': book_data.get('id', rec_book_id),
                        'book_id': rec_book_id,
                        'title': book_data.get('title', rec.get('title', 'Название не указано')),
                        'author': book_data.get('author', rec.get('author', 'Автор не указан')),
                        'cover': book_data.get('cover', '/static/images/error_pic_4.jpg'),
                        'score': rec.get('score', 0.5),
                        'reason': f'Похоже на "{base_book_title}" (сходство: {rec.get("score", 0.5)*100:.1f}%)'
                    })
                else:
                    # Если книга не найдена, используем данные из рекомендации
                    recommendations.append({
                        'id': rec_book_id,
                        'book_id': rec_book_id,
                        'title': rec.get('title', f'Book {rec_book_id}'),
                        'author': rec.get('author', f'Author of {rec_book_id}'),
                        'cover': '/static/images/no_cover.jpg',
                        'score': rec.get('score', 0.5),
                        'reason': f'Похоже на "{base_book_title}" (сходство: {rec.get("score", 0.5)*100:.1f}%)'
                    })
        else:
            # Если модель вернула ошибку, используем тестовые данные
            recommendations = generate_test_recommendations(f"похожие на книгу {book_id}")
        
        # Возвращаем в том же формате, что и контекстные рекомендации
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'recommendations_count': len(recommendations),
            'base_book': {
                'book_id': base_book_id,
                'title': base_book_title,
                'author': base_book_author
            }
        })
        
    except Exception as e:
        print(f"❌ Ошибка в simple_similar_books: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False)