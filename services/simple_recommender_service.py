import sys
import os
from pathlib import Path

def init_simple_recommender():
    """
    Инициализация простого сервиса рекомендаций (ALS + Content)
    """
    try:
        print("🚀 Инициализация SimpleRecommender сервиса...")
        
        # Добавляем путь к ml_models
        current_dir = Path(__file__).parent.parent
        ml_models_path = current_dir / "ml_models"
        
        if str(ml_models_path) not in sys.path:
            sys.path.insert(0, str(ml_models_path))
        
        # Проверяем наличие папки models_prod
        models_prod_path = current_dir / "models"
        if not models_prod_path.exists():
            print(f"⚠️  Папка models не найдена: {models_prod_path}")
            return None
        
        # Проверяем основные файлы
        required_files = ['als_model.pkl', 'content_similarity.pkl', 
                         'mappings.pkl', 'model_params.json', 
                         'user_item_matrix.npz']
        
        missing_files = []
        for file in required_files:
            if not (models_prod_path / file).exists():
                missing_files.append(file)
        
        if missing_files:
            print(f"⚠️  Отсутствуют файлы модели: {missing_files}")
            return None
        
        print(f"[simple_recommender_service.py] {models_prod_path}")
        
        # Импортируем и инициализируем модель
        from ml_models.simple_recommender import SimpleRecommender
        print(f"[simple_recommender_service.py] after impoert")
        recommender = SimpleRecommender(str(models_prod_path))
        
        print("✅ SimpleRecommender сервис успешно инициализирован")
        return recommender
        
    except Exception as e:
        print(f"❌ Ошибка инициализации SimpleRecommender: {e}")
        import traceback
        traceback.print_exc()
        return None

# Синглтон для глобального использования
simple_recommender_service = None

def get_simple_recommender():
    """
    Получить или инициализировать SimpleRecommender
    """
    global simple_recommender_service
    if simple_recommender_service is None:
        simple_recommender_service = init_simple_recommender()
    return simple_recommender_service