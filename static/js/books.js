// books.js - Основной файл JavaScript для работы с книгами

// ============ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ И КОНСТАНТЫ ============
const config = {
    booksPerLoad: 12,
    defaultCoverImage: '/static/images/no_cover.jpg',
    errorCoverImages: Array.from({length: 8}, (_, i) => `/static/images/error_pic_${i + 1}.jpg`)
};

// Состояние приложения
let appState = {
    books: [],
    visibleBooksCount: 12,
    personalRecommendations: [],
    similarBooksCache: new Map() // Кэш для похожих книг
};

// ============ ОСНОВНЫЕ ФУНКЦИИ ДЛЯ КНИГ ============

/**
 * Инициализация книг с данными из Flask
 */
function initBooks(booksData) {
    appState.books = booksData;
    console.log(`📚 Загружено ${appState.books.length} книг`);
    renderBooks();
}

/**
 * Рендеринг всех книг
 */
function renderBooks() {
    const booksGrid = document.getElementById('booksGrid');
    if (!booksGrid) {
        console.error('❌ Элемент booksGrid не найден');
        return;
    }
    
    booksGrid.innerHTML = '';

    if (appState.books.length === 0) {
        booksGrid.innerHTML = '<div class="no-books">Книги не найдены</div>';
        return;
    }

    // Показываем только visibleBooksCount книг
    const booksToShow = appState.books.slice(0, appState.visibleBooksCount);
    
    booksToShow.forEach(book => {
        const bookCard = createBookCard(book);
        booksGrid.innerHTML += bookCard;
    });

    // Добавляем кнопку "Показать еще", если есть еще книги
    addLoadMoreButton();
}

/**
 * Создание карточки книги (используем существующую функцию)
 */
function createBookCard(book) {
    // Проверяем и обрабатываем URL обложки
    let coverUrl = book.cover;
    if (!coverUrl || coverUrl === '' || coverUrl === 'NaN' || coverUrl === 'null') {
        const randomNumber = Math.floor(Math.random() * 8) + 1;
        coverUrl = `/static/images/error_pic_${randomNumber}.jpg`;
    }

    // Обрезаем длинные названия
    const shortTitle = book.title && book.title.length > 50 ? book.title.substring(0, 50) + '...' : book.title;
    const shortAuthor = book.author && book.author.length > 30 ? book.author.substring(0, 30) + '...' : book.author;

    return `
        <div class="book-card">
            <!-- Обложка книги в прямоугольнике -->
            <div class="book-cover-container">
                <div class="book-cover">
                    <img src="${coverUrl}" 
                        class="book-cover-image"
                        alt="${book.title || 'Название не указано'}"
                        loading="lazy"
                        data-book-id="${book.id}"
                        onerror="handleImageError(this)"
                        onload="handleImageLoad(this)">
                </div>
            </div>
            
            <!-- Информация о книге под обложкой -->
            <div class="book-info">
                <h3 class="book-title" title="${book.title || 'Название не указано'}">${shortTitle || 'Название не указано'}</h3>
                <p class="book-author" title="${book.author || 'Автор не указан'}">${shortAuthor || 'Автор не указан'}</p>
                
                <div class="book-actions">
                    <button class="action-button" onclick="showSimilarBooks('${book.book_id || ''}')">
                        <i class="fas fa-book"></i> Показать похожее
                    </button>
                </div>
            </div>
        </div>
    `;
}

/**
 * Создание карточки для рекомендаций
 */
function createRecommendationCard(book) {
    // Используем ту же функцию createBookCard, но с небольшими изменениями
    let coverUrl = book.cover;
    if (!coverUrl || coverUrl === '' || coverUrl === 'NaN' || coverUrl === 'null') {
        const randomNumber = Math.floor(Math.random() * 8) + 1;
        coverUrl = `/static/images/error_pic_${randomNumber}.jpg`;
    }

    const shortTitle = book.title && book.title.length > 40 ? book.title.substring(0, 40) + '...' : book.title;
    const shortAuthor = book.author && book.author.length > 25 ? book.author.substring(0, 25) + '...' : book.author;

    return `
        <div class="recommendation-card">
            <!-- Обложка книги -->
            <div class="book-cover-container">
                <img src="${coverUrl}" 
                     class="book-cover"
                     alt="${book.title || 'Название не указано'}"
                     loading="lazy"
                     onerror="handleImageError(this)"
                     onload="handleImageLoad(this)">
            </div>
            
            <!-- Информация о книге -->
            <div class="book-info">
                <h4 class="book-title" title="${book.title || ''}">${shortTitle || 'Название не указано'}</h4>
                <p class="book-author" title="${book.author || ''}">${shortAuthor || 'Автор не указан'}</p>
                
                <button class="similar-books-btn small" onclick="showSimilarBooks('${book.book_id || ''}')">
                    <i class="fas fa-book"></i> Показать похожие
                </button>
            </div>
        </div>
    `;
}

// ============ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ============

/**
 * Функция для добавления кнопки "Показать еще"
 */
function addLoadMoreButton() {
    const booksGrid = document.getElementById('booksGrid');
    if (!booksGrid) return;

    // Удаляем существующую кнопку, если есть
    const existingButton = document.getElementById('loadMoreButton');
    if (existingButton) {
        existingButton.remove();
    }

    // Если есть еще книги для показа, добавляем кнопку
    if (appState.visibleBooksCount < appState.books.length) {
        const loadMoreButton = document.createElement('div');
        loadMoreButton.id = 'loadMoreButton';
        loadMoreButton.className = 'load-more-container';
        loadMoreButton.innerHTML = `
            <button class="load-more-button" onclick="loadMoreBooks()">
                <i class="fas fa-plus"></i> Показать еще
            </button>
        `;
        booksGrid.parentNode.appendChild(loadMoreButton);
    }
}

/**
 * Функция для загрузки дополнительных книг
 */
function loadMoreBooks() {
    appState.visibleBooksCount += config.booksPerLoad;
    renderBooks();
    
    // Прокрутка к новым книгам
    const booksGrid = document.getElementById('booksGrid');
    if (booksGrid) {
        booksGrid.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

/**
 * Функции для работы с изображениями
 */
function handleImageError(img) {
    console.warn(`⚠️ Не удалось загрузить изображение для книги ${img.dataset.bookId}`);
    
    const randomNumber = Math.floor(Math.random() * 8) + 1;
    img.src = `/static/images/error_pic_${randomNumber}.jpg`;
    img.alt = 'Обложка недоступна';
    img.classList.add('image-error');
}

function handleImageLoad(img) {
    img.classList.add('image-loaded');
    img.style.opacity = '1';
}

// ============ ФУНКЦИИ ДЛЯ РЕКОМЕНДАЦИЙ ============

/**
 * Загрузка персональных рекомендаций
 */
async function loadPersonalRecommendations() {
    const section = document.getElementById('personalRecommendationsSection');
    const grid = document.getElementById('personalRecommendationsGrid');
    const loading = document.getElementById('personalRecommendationsLoading');
    const noRec = document.getElementById('noPersonalRecommendations');
    
    if (!section || !grid) return;
    
    try {
        // Показываем секцию рекомендаций
        section.style.display = 'block';
        
        // Показываем спиннер
        if (loading) loading.style.display = 'block';
        if (noRec) noRec.style.display = 'none';
        grid.innerHTML = '';
        
        // Отправляем запрос на сервер
        const response = await fetch('/api/simple/recommend/me?k=6');
        const result = await response.json();
        
        // Скрываем спиннер
        if (loading) loading.style.display = 'none';
        
        if (result.success && result.recommendations && result.recommendations.length > 0) {
            // Сохраняем рекомендации в состоянии
            appState.personalRecommendations = result.recommendations;
            
            // Рендерим рекомендации
            grid.innerHTML = '';
            result.recommendations.forEach(book => {
                const bookCard = createRecommendationCard(book);
                grid.innerHTML += bookCard;
            });
            
            if (noRec) noRec.style.display = 'none';
        } else {
            // Показываем сообщение об отсутствии рекомендаций
            grid.innerHTML = '';
            if (noRec) noRec.style.display = 'block';
        }
        
    } catch (error) {
        console.error('❌ Ошибка загрузки персональных рекомендаций:', error);
        
        // Скрываем спиннер
        if (loading) loading.style.display = 'none';
        
        // Показываем сообщение об ошибке
        grid.innerHTML = '<div class="error-message">Ошибка загрузки рекомендаций</div>';
    }
}

/**
 * Показать похожие книги для указанной книги
 */
async function showSimilarBooks(bookId) {
    console.log(`🔍 Поиск похожих книг для: ${bookId}`);
    
    // Проверяем кэш
    if (appState.similarBooksCache.has(bookId)) {
        displaySimilarBooks(bookId, appState.similarBooksCache.get(bookId));
        return;
    }
    
    try {
        // Показываем модальное окно
        const modal = document.getElementById('similarBooksModal');
        if (modal) {
            modal.classList.add('active');
        }
        
        // Показываем спиннер
        const infoDiv = document.getElementById('similarBooksInfo');
        const gridDiv = document.getElementById('similarBooksGrid');
        const noSimilarDiv = document.getElementById('noSimilarBooks');
        
        if (infoDiv) infoDiv.innerHTML = '<p><i class="fas fa-spinner fa-spin"></i> Загружаем похожие книги...</p>';
        if (gridDiv) gridDiv.innerHTML = '';
        if (noSimilarDiv) noSimilarDiv.style.display = 'none';
        
        // Отправляем запрос на сервер
        const response = await fetch(`/api/simple/similar/${bookId}?k=6&method=hybrid`);
        const result = await response.json();
        
        // Обновляем информацию в заголовке
        if (infoDiv) {
            if (result.base_book) {
                infoDiv.innerHTML = `
                    <h4>Похожие книги на "${result.base_book.title}"</h4>
                    <p>Автор: ${result.base_book.author}</p>
                `;
            } else {
                infoDiv.innerHTML = '<h4>Похожие книги</h4>';
            }
        }
        
        if (result.success && result.recommendations && result.recommendations.length > 0) {
            // Сохраняем в кэш
            appState.similarBooksCache.set(bookId, result);
            
            // Рендерим похожие книги
            if (gridDiv) {
                gridDiv.innerHTML = '';
                result.recommendations.forEach(book => {
                    const bookCard = createSimilarBookCard(book);
                    gridDiv.innerHTML += bookCard;
                });
            }
            
            if (noSimilarDiv) noSimilarDiv.style.display = 'none';
        } else {
            // Показываем сообщение об отсутствии похожих книг
            if (gridDiv) gridDiv.innerHTML = '';
            if (noSimilarDiv) noSimilarDiv.style.display = 'block';
        }
        
    } catch (error) {
        console.error('❌ Ошибка при получении похожих книг:', error);
        
        // Показываем сообщение об ошибке
        const infoDiv = document.getElementById('similarBooksInfo');
        if (infoDiv) {
            infoDiv.innerHTML = '<p style="color: #e74c3c;">Ошибка при загрузке похожих книг</p>';
        }
    }
}

/**
 * Отображение похожих книг из кэша
 */
function displaySimilarBooks(bookId, data) {
    console.log(`📖 Загружаем похожие книги из кэша для: ${bookId}`);
    
    // Показываем модальное окно
    const modal = document.getElementById('similarBooksModal');
    if (modal) {
        modal.classList.add('active');
    }
    
    // Обновляем информацию в заголовке
    const infoDiv = document.getElementById('similarBooksInfo');
    const gridDiv = document.getElementById('similarBooksGrid');
    const noSimilarDiv = document.getElementById('noSimilarBooks');
    
    if (infoDiv) {
        if (data.base_book) {
            infoDiv.innerHTML = `
                <h4>Похожие книги на "${data.base_book.title}"</h4>
                <p>Автор: ${data.base_book.author}</p>
                <small>(из кэша)</small>
            `;
        } else {
            infoDiv.innerHTML = '<h4>Похожие книги (из кэша)</h4>';
        }
    }
    
    if (gridDiv) {
        gridDiv.innerHTML = '';
        data.recommendations.forEach(book => {
            const bookCard = createSimilarBookCard(book);
            gridDiv.innerHTML += bookCard;
        });
    }
    
    if (noSimilarDiv) noSimilarDiv.style.display = 'none';
}

/**
 * Создание карточки для похожей книги
 */
function createSimilarBookCard(book) {
    // Используем похожую логику, как для обычной карточки
    let coverUrl = book.cover;
    if (!coverUrl || coverUrl === '' || coverUrl === 'NaN' || coverUrl === 'null') {
        const randomNumber = Math.floor(Math.random() * 8) + 1;
        coverUrl = `/static/images/error_pic_${randomNumber}.jpg`;
    }

    const shortTitle = book.title && book.title.length > 30 ? book.title.substring(0, 30) + '...' : book.title;
    const shortAuthor = book.author && book.author.length > 20 ? book.author.substring(0, 20) + '...' : book.author;

    return `
        <div class="similar-book-card">
            <img src="${coverUrl}" 
                 class="similar-book-cover"
                 alt="${shortTitle}"
                 loading="lazy"
                 onerror="handleImageError(this)"
                 onload="handleImageLoad(this)">
            
            <div class="similar-book-info">
                <h4 class="similar-book-title" title="${book.title || ''}">${shortTitle || 'Название не указано'}</h4>
                <p class="similar-book-author" title="${book.author || ''}">${shortAuthor || 'Автор не указан'}</p>
               
            </div>
        </div>
    `;
}

/**
 * Закрытие модального окна с похожими книгами
 */
function closeSimilarBooksModal() {
    const modal = document.getElementById('similarBooksModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

// ============ КОНТЕКСТНЫЕ РЕКОМЕНДАЦИИ ============

let contextModal = null;

/**
 * Инициализация при загрузке страницы
 */
document.addEventListener('DOMContentLoaded', function() {
    contextModal = document.getElementById('contextModal');
    
    // Закрытие модального окна при клике вне его
    window.addEventListener('click', function(event) {
        if (event.target === contextModal) {
            closeContextModal();
        }
        
        // Закрытие модального окна с похожими книгами
        const similarModal = document.getElementById('similarBooksModal');
        if (event.target === similarModal) {
            closeSimilarBooksModal();
        }
    });
    
    // Закрытие модального окна по Escape
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            if (contextModal && contextModal.style.display === 'block') {
                closeContextModal();
            }
            
            const similarModal = document.getElementById('similarBooksModal');
            if (similarModal && similarModal.classList.contains('active')) {
                closeSimilarBooksModal();
            }
        }
    });
});

/**
 * Открытие модального окна контекстной рекомендации
 */
function openContextModal() {
    if (contextModal) {
        contextModal.style.display = 'block';
        document.getElementById('contextText').focus();
        document.getElementById('contextText').value = '';
    }
}

/**
 * Закрытие модального окна контекстной рекомендации
 */
function closeContextModal() {
    if (contextModal) {
        contextModal.style.display = 'none';
    }
}

/**
 * Получение контекстных рекомендаций
 */
async function getContextRecommendations() {
    const contextText = document.getElementById('contextText').value.trim();
    const spinner = document.getElementById('loadingSpinner');
    const getBtn = document.getElementById('getRecommendationsBtn');
    
    if (!contextText) {
        alert('Пожалуйста, введите описание для рекомендаций');
        return;
    }
    
    try {
        // Показываем спиннер и отключаем кнопку
        if (spinner) spinner.style.display = 'block';
        if (getBtn) {
            getBtn.disabled = true;
            getBtn.textContent = 'Поиск...';
        }
        
        // Отправляем запрос на сервер
        const response = await fetch('/api/context_recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ context: contextText })
        });
        
        const result = await response.json();
        
        // Скрываем спиннер
        if (spinner) spinner.style.display = 'none';
        if (getBtn) {
            getBtn.disabled = false;
            getBtn.textContent = 'Получить рекомендации';
        }
        
        if (result.success) {
            // Перенаправляем на страницу с рекомендациями
            window.location.href = result.redirect_url;
        } else {
            alert('Ошибка: ' + result.message);
        }
        
    } catch (error) {
        console.error('❌ Ошибка при получении контекстных рекомендаций:', error);
        
        if (spinner) spinner.style.display = 'none';
        if (getBtn) {
            getBtn.disabled = false;
            getBtn.textContent = 'Получить рекомендации';
        }
        
        alert('Произошла ошибка при получении рекомендаций. Попробуйте еще раз.');
    }
}

// ============ УТИЛИТЫ ============

/**
 * Проверка, является ли строка URL
 */
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

/**
 * Получение случайного изображения-заглушки
 */
function getRandomErrorImage() {
    const randomNumber = Math.floor(Math.random() * 8) + 1;
    return `/static/images/error_pic_${randomNumber}.jpg`;
}

// ============ ИНИЦИАЛИЗАЦИЯ ============

/**
 * Инициализация при загрузке страницы
 */
function initializePage() {
    // Загружаем персональные рекомендации для авторизованных пользователей
    const username = document.body.dataset.username || '';
    if (username && username !== 'None') {
        loadPersonalRecommendations();
    }
}

// Экспорт функций для глобального использования
window.initBooks = initBooks;
window.loadMoreBooks = loadMoreBooks;
window.handleImageError = handleImageError;
window.handleImageLoad = handleImageLoad;
window.showSimilarBooks = showSimilarBooks;
window.closeSimilarBooksModal = closeSimilarBooksModal;
window.openContextModal = openContextModal;
window.closeContextModal = closeContextModal;
window.getContextRecommendations = getContextRecommendations;
window.loadPersonalRecommendations = loadPersonalRecommendations;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', initializePage);

console.log('✅ books.js успешно загружен');
// Функция для отображения книг
/*function renderBooks() {
    const booksGrid = document.getElementById('booksGrid');
    booksGrid.innerHTML = '';

    books.forEach(book => {
        const bookCard = `
            <div class="book-card">
                <div class="book-cover">${book.cover}</div>
                <div class="book-info">
                    <h3 class="book-title">${book.title}</h3>
                    <div class="book-actions">
                        <div class="checkbox-group">
                            <label class="checkbox-label">
                                <input type="checkbox" name="want-to-read-${book.id}"> Хочу прочитать
                            </label>
                            <label class="checkbox-label">
                                <input type="checkbox" name="already-read-${book.id}"> Уже читал(а)
                            </label>
                        </div>
                        <button class="action-button" onclick="getRecommendations(${book.id})">Получить рекомендации</button>
                    </div>
                </div>
            </div>
        `;
        booksGrid.innerHTML += bookCard;
    });
}
*/
// Функция для получения рекомендаций
//function getRecommendations(bookId) {
//    alert(`Получение рекомендаций для книги ID: ${bookId}`);
    // Здесь будет AJAX запрос к вашему Flask API
//}

// Инициализация при загрузке страницы
//document.addEventListener('DOMContentLoaded', renderBooks);