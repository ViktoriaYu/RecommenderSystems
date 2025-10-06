// Пример данных книг (в реальном приложении будут приходить с сервера)
const books = [
    { id: 1, title: "Мастер и Маргарита", cover: "Обложка 1" },
    { id: 2, title: "1984", cover: "Обложка 2" },
    { id: 3, title: "Преступление и наказание", cover: "Обложка 3" },
    { id: 4, title: "Маленький принц", cover: "Обложка 4" },
    { id: 5, title: "Гарри Поттер и философский камень", cover: "Обложка 5" },
    { id: 6, title: "Война и мир", cover: "Обложка 6" },
    { id: 7, title: "Три товарища", cover: "Обложка 7" },
    { id: 8, title: "Атлант расправил плечи", cover: "Обложка 8" }
];

// Функция для отображения книг
function renderBooks() {
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

// Функция для получения рекомендаций
function getRecommendations(bookId) {
    alert(`Получение рекомендаций для книги ID: ${bookId}`);
    // Здесь будет AJAX запрос к вашему Flask API
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', renderBooks);