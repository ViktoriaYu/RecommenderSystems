// static/js/common.js
// Общие функции для обеих страниц

console.log('🔧 common.js загружен');

// Модальное окно для контекстных рекомендаций
let contextModal = null;

// Инициализация модального окна
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ Общие скрипты инициализированы');
    
    contextModal = document.getElementById('contextModal');
    
    if (contextModal) {
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
    }
});

// Открытие модального окна
window.openContextModal = function() {
    if (contextModal) {
        contextModal.style.display = 'block';
        const contextText = document.getElementById('contextText');
        if (contextText) {
            contextText.focus();
            contextText.value = '';
        }
    }
};

// Закрытие модального окна
window.closeContextModal = function() {
    if (contextModal) {
        contextModal.style.display = 'none';
    }
};

// Получение контекстных рекомендаций
window.getContextRecommendations = async function() {
    const contextText = document.getElementById('contextText');
    const spinner = document.getElementById('loadingSpinner');
    const getBtn = document.getElementById('getRecommendationsBtn');
    
    if (!contextText || !contextText.value.trim()) {
        alert('Пожалуйста, введите описание для рекомендаций');
        return;
    }
    
    const text = contextText.value.trim();
    
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
            body: JSON.stringify({ context: text })
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
        console.error('Ошибка при получении рекомендаций:', error);
        if (spinner) spinner.style.display = 'none';
        if (getBtn) {
            getBtn.disabled = false;
            getBtn.textContent = 'Получить рекомендации';
        }
        alert('Произошла ошибка при получении рекомендаций. Попробуйте еще раз.');
    }
};