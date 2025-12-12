
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
                    <div class="checkbox-group">
                        <label class="checkbox-label">
                            <input type="checkbox" name="want-to-read-${book.id}"> Хочу прочитать
                        </label>
                        <label class="checkbox-label">
                            <input type="checkbox" name="already-read-${book.id}"> Уже читал(а)
                        </label>
                    </div>
                    
                    <button class="action-button" onclick="getRecommendations('${book.id}')">
                        Показать похожее
                    </button>
                </div>
            </div>
        </div>
    `;
}