// Данные книг будут переданы из Flask
let books = [];
let visibleBooksCount = 12;
const booksPerLoad = 12;

// Функция для инициализации с данными из Flask
function initBooks(booksData) {
    books = booksData;
    console.log(`Загружено ${books.length} книг с обложками`);
    renderBooks();
}

// Функция для отображения книг
function renderBooks() {
    const booksGrid = document.getElementById('booksGrid');
    if (!booksGrid) {
        console.error('Элемент booksGrid не найден');
        return;
    }
    
    booksGrid.innerHTML = '';

    if (books.length === 0) {
        booksGrid.innerHTML = '<div class="no-books">Книги не найдены</div>';
        return;
    }

    // Показываем только visibleBooksCount книг
    const booksToShow = books.slice(0, visibleBooksCount);
    
    booksToShow.forEach(book => {
        const bookCard = createBookCard(book);
        booksGrid.innerHTML += bookCard;
    });

    // Добавляем кнопку "Показать еще", если есть еще книги
    addLoadMoreButton();
}

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
                    <button class="action-button" onclick="getRecommendations('${book.id}')">
                        Показать похожее
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Функция для добавления кнопки "Показать еще"
function addLoadMoreButton() {
    const booksGrid = document.getElementById('booksGrid');
    if (!booksGrid) return;

    // Удаляем существующую кнопку, если есть
    const existingButton = document.getElementById('loadMoreButton');
    if (existingButton) {
        existingButton.remove();
    }

    // Если есть еще книги для показа, добавляем кнопку
    if (visibleBooksCount < books.length) {
        const loadMoreButton = document.createElement('div');
        loadMoreButton.id = 'loadMoreButton';
        loadMoreButton.className = 'load-more-container';
        loadMoreButton.innerHTML = `
            <button class="load-more-button" onclick="loadMoreBooks()">
                Показать еще
            </button>
        `;
        booksGrid.parentNode.appendChild(loadMoreButton);
    }
}

// Функция для загрузки дополнительных книг
function loadMoreBooks() {
    visibleBooksCount += booksPerLoad;
    renderBooks();
    
    // Прокрутка к новым книгам
    const booksGrid = document.getElementById('booksGrid');
    if (booksGrid) {
        booksGrid.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Функции для работы с изображениями
function handleImageError(img) {
    console.warn(`Не удалось загрузить изображение для книги ${img.dataset.bookId}`);
    // Заглушка для отсутствующего изображения
    
    const randomNumber = Math.floor(Math.random() * 8) + 1;
    img.src = `/static/images/error_pic_${randomNumber}.jpg`;
    img.alt = 'Обложка недоступна';
    img.classList.add('image-error');
}

function handleImageLoad(img) {
    img.classList.add('image-loaded');
    img.style.opacity = '1';
}

// Функция для получения рекомендаций
function getRecommendations(bookId) {
    console.log(`Запрос рекомендаций для книги ID: ${bookId}`);
    window.location.href = `/recommend/${bookId}`;
}

// Обработчики событий для чекбоксов
document.addEventListener('DOMContentLoaded', function() {
    // Делегирование событий для чекбоксов
    document.addEventListener('change', function(e) {
        if (e.target.type === 'checkbox') {
            const bookId = e.target.name.split('-').pop();
            const action = e.target.name.includes('want-to-read') ? 'want_to_read' : 'already_read';
            const isChecked = e.target.checked;
            
            console.log(`Книга ${bookId}: ${action} = ${isChecked}`);
            // Здесь можно добавить AJAX запрос для сохранения состояния
        }
    });
});


// Модальное окно для контекстных рекомендаций
let contextModal = null;

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    contextModal = document.getElementById('contextModal');
    
    // Закрытие модального окна при клике вне его
    window.addEventListener('click', function(event) {
        if (event.target === contextModal) {
            closeContextModal();
        }
    });
    
    // Закрытие модального окна по Escape
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape' && contextModal.style.display === 'block') {
            closeContextModal();
        }
    });
});

// Открытие модального окна
function openContextModal() {
    if (contextModal) {
        contextModal.style.display = 'block';
        document.getElementById('contextText').focus();
        document.getElementById('contextText').value = '';
    }
}

// Закрытие модального окна
function closeContextModal() {
    if (contextModal) {
        contextModal.style.display = 'none';
    }
}

// Получение контекстных рекомендаций
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
        spinner.style.display = 'block';
        getBtn.disabled = true;
        getBtn.textContent = 'Поиск...';
        
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
        spinner.style.display = 'none';
        getBtn.disabled = false;
        getBtn.textContent = 'Получить рекомендации';
        
        if (result.success) {
            // Перенаправляем на страницу с рекомендациями
            window.location.href = result.redirect_url;
        } else {
            alert('Ошибка: ' + result.message);
        }
        
    } catch (error) {
        console.error('Ошибка при получении рекомендаций:', error);
        spinner.style.display = 'none';
        getBtn.disabled = false;
        getBtn.textContent = 'Получить рекомендации';
        alert('Произошла ошибка при получении рекомендаций. Попробуйте еще раз.');
    }
}

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