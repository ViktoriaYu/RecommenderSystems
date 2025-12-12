// Конфигурация пагинации
let visibleBooksCount = 12;
const booksPerLoad = 12;

// Функция для отображения рекомендованных книг с пагинацией
function renderRecommendations(booksData) {
    const booksGrid = document.getElementById('booksGrid');
    if (!booksGrid) return;
    
    booksGrid.innerHTML = '';
    
    if (!booksData || booksData.length === 0) {
        booksGrid.innerHTML = '<div class="no-books">Книги не найдены</div>';
        return;
    }
    
    // Показываем только visibleBooksCount книг
    const booksToShow = booksData.slice(0, visibleBooksCount);
    
    booksToShow.forEach(book => {
        const bookCard = createRecommendationBookCard(book);
        booksGrid.innerHTML += bookCard;
    });
    
    // Добавляем кнопку "Показать еще", если есть еще книги
    addLoadMoreButton(booksData);
}

// Функция для создания карточки книги для страницы рекомендаций
function createRecommendationBookCard(book) {
    // Проверяем и обрабатываем URL обложки
    let coverUrl = book.cover;
    if (!coverUrl || coverUrl === '' || coverUrl === 'NaN' || coverUrl === 'null') {
        const randomNumber = Math.floor(Math.random() * 8) + 1;
        coverUrl = `/static/images/error_pic_${randomNumber}.jpg`;
    }
    
    // Обрезаем длинные названия
    const shortTitle = book.title && book.title.length > 50 ? 
        book.title.substring(0, 50) + '...' : book.title;
    const shortAuthor = book.author && book.author.length > 30 ? 
        book.author.substring(0, 30) + '...' : book.author;
    
    // Создаем карточку с дополнительной информацией о рекомендации
    let reasonHtml = '';
    if (book.reason) {
        reasonHtml = `
            <div class="recommendation-reason">
                <i class="fas fa-lightbulb"></i> ${book.reason}
            </div>
        `;
    }
    
    let scoreHtml = '';
    if (book.score !== undefined) {
        const scorePercent = Math.round(book.score * 100);
        scoreHtml = `<span class="score-badge">${scorePercent}%</span>`;
    }
    
    return `
        <div class="book-card">
            <!-- Обложка книги -->
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
            
            <!-- Информация о книге -->
            <div class="book-info">
                <h3 class="book-title" title="${book.title || 'Название не указано'}">
                    ${shortTitle || 'Название не указано'} ${scoreHtml}
                </h3>
                <p class="book-author" title="${book.author || 'Автор не указан'}">
                    ${shortAuthor || 'Автор не указан'}
                </p>
                
                <!-- Дополнительная информация -->
                ${reasonHtml}
                
                <!-- Кнопки действий -->
                <div class="book-actions">
                    <div class="checkbox-group">
                        <label class="checkbox-label">
                            <input type="checkbox" name="want-to-read-${book.id}"> 
                            Хочу прочитать
                        </label>
                        <label class="checkbox-label">
                            <input type="checkbox" name="already-read-${book.id}"> 
                            Уже читал(а)
                        </label>
                    </div>
                    
                    <button class="action-button" onclick="getBookRecommendations('${book.id}')">
                        <i class="fas fa-search-plus"></i> Похожие книги
                    </button>
                </div>
            </div>
        </div>
    `;
}

// Функция для добавления кнопки "Показать еще"
function addLoadMoreButton(booksData) {
    const container = document.getElementById('loadMoreContainer');
    if (!container) return;
    
    // Удаляем существующую кнопку, если есть
    container.innerHTML = '';
    
    // Если есть еще книги для показа, добавляем кнопку
    if (visibleBooksCount < booksData.length) {
        container.innerHTML = `
            <div class="load-more-container">
                <button class="load-more-button" onclick="loadMoreBooks(booksData)">
                    <i class="fas fa-plus"></i> Показать еще книги
                    <span class="badge">(${booksData.length - visibleBooksCount} из ${booksData.length})</span>
                </button>
            </div>
        `;
    }
}

// Функция для загрузки дополнительных книг
function loadMoreBooks(booksData) {
    visibleBooksCount += booksPerLoad;
    renderRecommendations(booksData);
    
    // Плавная прокрутка к новым книгам
    setTimeout(() => {
        const booksGrid = document.getElementById('booksGrid');
        if (booksGrid) {
            const cards = booksGrid.querySelectorAll('.book-card');
            if (cards.length > visibleBooksCount - booksPerLoad) {
                cards[visibleBooksCount - booksPerLoad].scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest'
                });
            }
        }
    }, 100);
}

// Функция для получения рекомендаций по конкретной книге
async function getBookRecommendations(bookId) {
    try {
        console.log(`Запрос рекомендаций для книги: ${bookId}`);
        
        // Показываем индикатор загрузки
        const button = event.target;
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Поиск...';
        button.disabled = true;
        
        // Отправляем запрос к API
        const response = await fetch(`/api/book_recommendations/${bookId}`);
        const result = await response.json();
        
        // Восстанавливаем кнопку
        button.innerHTML = originalText;
        button.disabled = false;
        
        if (result.success) {
            alert(`Найдено ${result.recommendations.length} похожих книг`);
        } else {
            alert('Ошибка: ' + result.message);
        }
        
    } catch (error) {
        console.error('Ошибка при получении рекомендаций:', error);
        event.target.innerHTML = originalText;
        event.target.disabled = false;
        alert('Произошла ошибка. Попробуйте еще раз.');
    }
}

// Инициализация страницы рекомендаций
function initRecommendationsPage(recommendationsData) {
    console.log('Страница контекстных рекомендаций загружена');
    console.log('Всего рекомендаций:', recommendationsData ? recommendationsData.length : 0);
    console.log('Показываем:', visibleBooksCount);
    
    // Отрисовываем рекомендации
    renderRecommendations(recommendationsData);
    
    // Добавляем обработчики для чекбоксов
    document.addEventListener('change', function(e) {
        if (e.target.type === 'checkbox') {
            const bookId = e.target.name.split('-').pop();
            const action = e.target.name.includes('want-to-read') ? 'want_to_read' : 'already_read';
            const isChecked = e.target.checked;
            
            console.log(`Книга ${bookId}: ${action} = ${isChecked}`);
            // Здесь можно добавить AJAX запрос для сохранения состояния
        }
    });
}