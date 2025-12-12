import os
import sys
# Создаем глобальную переменную для сервиса
recommendation_service = None

def init_recommendation_service():
    """
    Инициализирует сервис рекомендаций
    Возвращает экземпляр сервиса или None если не удалось
    """
    global recommendation_service
    
    # Если уже инициализирован, возвращаем существующий
    if recommendation_service is not None:
        return recommendation_service
    try:
        # Определяем путь к модели
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'models', 'recommendation_system.pkl')

        # Проверяем существование файла
        if not os.path.exists(model_path):
            print(f" Файл модели не найден: {model_path}")
            return None
        
        # Импортируем сервис
        from .recommendation_service import BookRecommendationService
        
        # Создаем экземпляр
        service = BookRecommendationService(model_path)
        print(" Сервис рекомендаций успешно инициализирован")
        return service
        
    except Exception as e:
        print(f" Ошибка инициализации сервиса рекомендаций: {e}")
        return None

# Глобальный экземпляр сервиса
#recommendation_service = init_recommendation_service()