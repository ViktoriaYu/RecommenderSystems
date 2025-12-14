/**
 * Контекстные рекомендации - независимый JavaScript модуль
 * Не зависит от books.js
 */

// Конфигурация
const config = {
    defaultCoverImage: '/static/images/no_cover.jpg',
    errorCoverImages: Array.from({length: 8}, (_, i) => `/static/images/error_pic_${i + 1}.jpg`),
    maxTitleLength: 50,
    maxAuthorLength: 30
};

// Состояние приложения
let appState = {
    recommendations: [],
    context: '',
    currentPage: 1,
    itemsPerPage: 12,
    isLoading: false
};

// Основная функция инициализации
function initContextRecommendations(data) {
    console.log('Инициализация контекстных рекомендаций');
    
    appState.recommendations = data.recommendations || [];
    appState.context = data.context || '';
    
    // Обновляем счетчик
    updateRecommendationsCount(appState.recommendations.length);
    
    // Рендерим рекомендации
    renderRecommendations();
    
    // Управляем видимостью элементов
    toggleEmptyState();
    toggleNewRequestButton();
}

// Функция рендеринга рекомендаций
function renderRecommendations() {
    const grid = document.getElementById('recommendationsGrid');
    if (!grid) {
        console.error('Элемент recommendationsGrid не найден');
        return;
    }
    
    grid.innerHTML = '';
    
    if (appState.recommendations.length === 0) {
        return;
    }
    
    // Вычисляем, какие книги показывать на текущей странице
    const startIndex = (appState.currentPage - 1) * appState.itemsPerPage;
    const endIndex = Math.min(startIndex + appState.itemsPerPage, appState.recommendations.length);
    const booksToShow = appState.recommendations.slice(startIndex, endIndex);
    
    // Рендерим книги
    booksToShow.forEach((book, index) => {
        const bookCard = createBookCard(book, startIndex + index);
        grid.appendChild(bookCard);
    });
    
    // Добавляем пагинацию если нужно
    addPaginationIfNeeded();
}

// Создание карточки книги
function createBookCard(book, index) {
    const card = document.createElement('div');
    card.className = 'book-card';
    card.dataset.index = index;
    
    // Обработка URL обложки
    let coverUrl = book.cover || book.image_url || '';
    if (!coverUrl || coverUrl === 'NaN' || coverUrl === 'null' || coverUrl.trim() === '') {
        const randomIndex = Math.floor(Math.random() * config.errorCoverImages.length);
        coverUrl = config.errorCoverImages[randomIndex];
    }
    
    // Обработка текстов
    const title = book.title || 'Название не указано';
    const author = book.author || 'Автор не указан';
    const shortTitle = title.length > config.maxTitleLength ? 
        title.substring(0, config.maxTitleLength) + '...' : title;
    const shortAuthor = author.length > config.maxAuthorLength ?
        author.substring(0, config.maxAuthorLength) + '...' : author;
    
    // Форматирование оценки если есть
    
    // Создание HTML
    card.innerHTML = `
        <div class="book-cover-container">
            <div class="book-cover">
                <img src="${coverUrl}" 
                     class="book-cover-image"
                     alt="${title}"
                     loading="lazy"
                     data-book-id="${book.id || index}"
                     onerror="handleRecommendationImageError(this)"
                     onload="handleRecommendationImageLoad(this)">
            </div>
        </div>
        
        <div class="book-info">
            <h3 class="book-title" title="${title}">${shortTitle}</h3>
            <p class="book-author" title="${author}">${shortAuthor}</p>
            
            ${book.year ? `<p class="book-meta"><i class="fas fa-calendar-alt"></i> ${book.year}</p>` : ''}
            ${book.publisher ? `<p class="book-meta"><i class="fas fa-building"></i> ${book.publisher}</p>` : ''}
            
        </div>
    `;
    
    return card;
}

// Функции для работы с изображениями
function handleRecommendationImageError(img) {
    console.warn(`Не удалось загрузить изображение для рекомендации`);
    
    const randomIndex = Math.floor(Math.random() * config.errorCoverImages.length);
    img.src = config.errorCoverImages[randomIndex];
    img.alt = 'Обложка недоступна';
    img.classList.add('image-error');
    img.classList.remove('image-loaded');
}

function handleRecommendationImageLoad(img) {
    img.classList.add('image-loaded');
    img.classList.remove('image-error');
    img.style.opacity = '1';
}

// Добавление пагинации
function addPaginationIfNeeded() {
    const totalPages = Math.ceil(appState.recommendations.length / appState.itemsPerPage);
    
    if (totalPages <= 1) {
        return;
    }
    
    const container = document.querySelector('.container');
    let pagination = document.getElementById('recommendationsPagination');
    
    // Удаляем старую пагинацию если есть
    if (pagination) {
        pagination.remove();
    }
    
    // Создаем новую пагинацию
    pagination = document.createElement('div');
    pagination.id = 'recommendationsPagination';
    pagination.className = 'pagination';
    
    // Кнопка "Назад"
    const prevButton = document.createElement('button');
    prevButton.className = 'pagination-button';
    prevButton.disabled = appState.currentPage === 1;
    prevButton.innerHTML = '<i class="fas fa-chevron-left"></i> Назад';
    prevButton.onclick = () => changePage(appState.currentPage - 1);
    
    // Информация о странице
    const pageInfo = document.createElement('span');
    pageInfo.className = 'page-info';
    pageInfo.textContent = `Страница ${appState.currentPage} из ${totalPages}`;
    
    // Кнопка "Вперед"
    const nextButton = document.createElement('button');
    nextButton.className = 'pagination-button';
    nextButton.disabled = appState.currentPage === totalPages;
    nextButton.innerHTML = 'Вперед <i class="fas fa-chevron-right"></i>';
    nextButton.onclick = () => changePage(appState.currentPage + 1);
    
    pagination.appendChild(prevButton);
    pagination.appendChild(pageInfo);
    pagination.appendChild(nextButton);
    
    const booksSection = document.querySelector('.books-section');
    if (booksSection) {
        booksSection.appendChild(pagination);
    }
}

// Смена страницы
function changePage(newPage) {
    const totalPages = Math.ceil(appState.recommendations.length / config.itemsPerPage);
    
    if (newPage < 1 || newPage > totalPages || newPage === appState.currentPage) {
        return;
    }
    
    appState.currentPage = newPage;
    renderRecommendations();
    
    // Прокрутка к началу сетки
    const grid = document.getElementById('recommendationsGrid');
    if (grid) {
        grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

// Обновление счетчика рекомендаций
function updateRecommendationsCount(count) {
    const countElement = document.getElementById('recommendationsCount');
    if (countElement) {
        countElement.textContent = count;
    }
}

// Показать/скрыть состояние "нет рекомендаций"
function toggleEmptyState() {
    const emptyElement = document.getElementById('emptyRecommendations');
    const grid = document.getElementById('recommendationsGrid');
    
    if (emptyElement && grid) {
        if (appState.recommendations.length === 0) {
            emptyElement.style.display = 'block';
            grid.style.display = 'none';
        } else {
            emptyElement.style.display = 'none';
            grid.style.display = 'grid';
        }
    }
}

// Показать/скрыть кнопку нового запроса
function toggleNewRequestButton() {
    const buttonContainer = document.getElementById('newRequestContainer');
    
    if (buttonContainer) {
        if (appState.recommendations.length > 0) {
            buttonContainer.style.display = 'block';
        } else {
            buttonContainer.style.display = 'none';
        }
    }
}

// Экспорт функций для глобального использования
window.handleRecommendationImageError = handleRecommendationImageError;
window.handleRecommendationImageLoad = handleRecommendationImageLoad;
window.initContextRecommendations = initContextRecommendations;

// Добавляем стили для пагинации если их нет в CSS
(function() {
    if (!document.getElementById('contextRecommendationsStyles')) {
        const style = document.createElement('style');
        style.id = 'contextRecommendationsStyles';
        style.textContent = `
            .pagination {
                display: flex;
                justify-content: center;
                align-items: center;
                gap: 20px;
                margin: 30px 0;
                padding: 20px;
                background: rgba(255, 255, 255, 0.9);
                border-radius: 10px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }
            
            .pagination-button {
                padding: 10px 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 0.9rem;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .pagination-button:hover:not(:disabled) {
                background: linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%);
                transform: translateY(-2px);
            }
            
            .pagination-button:disabled {
                background: #cccccc;
                cursor: not-allowed;
                transform: none;
            }
            
            .page-info {
                font-size: 0.9rem;
                color: #666;
                font-weight: 500;
            }
            
            .book-score {
                display: inline-block;
                background: #ffd700;
                color: #333;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.8rem;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            .image-loaded {
                opacity: 1;
                transition: opacity 0.3s ease;
            }
            
            .image-error {
                filter: grayscale(100%);
                opacity: 0.7;
            }
        `;
        document.head.appendChild(style);
    }
})();

console.log('context-recommendations.js загружен и готов к использованию');