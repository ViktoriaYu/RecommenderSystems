import pickle
import torch
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional
import os
import sys

# Добавляем путь для импорта модели
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'ml_models'))

class BookRecommendationService:
    """
    Сервис рекомендаций книг для интеграции в API
    """
    
    def __init__(self, model_path: str = None):
        """
        Инициализация сервиса
        
        Args:
            model_path: путь к сохраненной системе
        """
        
        # Определяем путь к модели
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'models', 
                'enhanced_recommendation_system.pkl'
            )
        
        # Проверяем существование файла
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Загружаем систему
        with open(model_path, 'rb') as f:
            self.system = pickle.load(f)
        
        # Импортируем модель
        try:
            from ml_models.context_recommender_model import TextAwareDynamicRecommender
            self.model_class = TextAwareDynamicRecommender
        except ImportError:
            # Если не можем импортировать, создаем локальный класс
            print(f"[context_recommendation_service.py] Модель не инициализировалась")
        
        # Загружаем модель
        self.model = self.model_class(**self.system['model_config'])
        self.model.load_state_dict(self.system['model_state_dict'])
        self.model.eval()
        
        # Загружаем данные
        self.books_df = self.system['books_data']
        self.user_encoder = self.system['user_encoder']
        self.author_encoder = self.system['author_encoder']

        # Улучшенные структуры
        self.genre_keywords = self.system["genre_keywords"]
        self.book_genres = self.system["book_genres"]
        
        # Устройство
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        
        '''
        print(f" Сервис готов:")
        print(f"   • Книг в базе: {len(self.books_df)}")        
        print(f"   • Жанров: {len(self.genre_keywords)}")
        print(f"   • Устройство: {self.device}")
        print(f"   • Пользователей: {self.system['model_config']['num_users']}")
        print(f"   • Авторов: {self.system['model_config']['num_authors']}")
        '''
    
    def _text_to_tensor(self, text: str) -> torch.Tensor:
        """Конвертирует текст в тензор"""
        chars = [min(ord(c), 127) for c in text[:256]]
        if len(chars) < 256:
            chars += [0] * (256 - len(chars))
        return torch.tensor([chars], dtype=torch.long).to(self.device)
    
    def _detect_query_genres(self, query: str) -> List[str]:
        """Определяет жанры из текстового запроса"""
        query_lower = query.lower()
        detected_genres = []
        
        for genre, keywords in self.genre_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    detected_genres.append(genre)
                    break
        
        return detected_genres if detected_genres else ['general']

    def _get_genre_multiplier(self, query_genres: List[str], book_id: int) -> float:
        """Вычисляет множитель жанра"""
        book_genres = self.book_genres.get(book_id, ['general'])
        
        # Проверяем совпадение жанров
        if query_genres and query_genres[0] != 'general':
            genre_match = any(genre in book_genres for genre in query_genres)
            if genre_match:
                return 1.5  # Усиление для подходящего жанра
        
        return 1.0
    
    def _get_title_boost(self, query: str, title: str) -> float:
        """Вычисляет усиление по совпадению слов в названии"""
        if not isinstance(title, str):
            return 1.0
        
        query_words = query.lower().split()
        title_lower = title.lower()
        boost = 1.0
        
        for word in query_words:
            if len(word) > 3 and word in title_lower:
                boost *= 1.1
        
        return min(boost, 1.3)  # Ограничиваем максимальное усиление
    
    def _get_author_encoded(self, author: str) -> int:
        """Кодирует автора"""
        try:
            return self.author_encoder.transform([author])[0]
        except:
            return 0
    
    def _get_user_encoded(self, user_id: int) -> Optional[int]:
        """Кодирует пользователя"""
        try:
            return self.user_encoder.transform([user_id])[0]
        except ValueError:
            return None
    
    def recommend_for_user(
        self, 
        user_id: int, 
        context: str = "",
        top_k: int = 3,
        max_books: int = 2000,
        context_weight: float = 0.7,
        genre_boost: bool = True,
        title_boost: bool = True,
    ) -> Dict[str, Any]:
        """
        Рекомендации для конкретного пользователя с контекстом
        
        Args:
            user_id: ID пользователя
            context: текстовый запрос (опционально)
            top_k: количество рекомендаций
            max_books: максимальное количество книг для оценки
        
        Returns:
            Словарь с рекомендациями
        """
        start_time = datetime.now()
        
        try:
            user_encoded = self.user_encoder.transform([user_id])[0]
        except ValueError:
            return {
                "status": "error",
                "message": f"User {user_id} not found",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
            }
        
        query_genres = self._detect_query_genres(context)

        # Подготавливаем тензоры
        user_tensor = torch.tensor([user_encoded], dtype=torch.long).to(self.device)
        context_tensor = self._text_to_tensor(context)
        
        # Ограничиваем количество книг для скорости
        books_to_check = self.books_df.head(max_books)
        recommendations = []
        
        # Оцениваем книги
        for _, row in books_to_check.iterrows():
            book_id = int(row["book_id"])

            book_tensor = torch.tensor([book_id - 1], dtype=torch.long).to(self.device)

            try:
                author_encoded = self.author_encoder.transform([row["authors"]])[0]
            except Exception:
                author_encoded = 0

            author_tensor = torch.tensor([author_encoded], dtype=torch.long).to(self.device)

            with torch.no_grad():
                output = self.model(
                    user_tensor,
                    book_tensor,
                    author_tensor,
                    context_tensor
                )

                if isinstance(output, tuple):
                    rating, similarity = output
                    rating = rating.item()
                    similarity = similarity.item()
                else:
                    rating = output.item()
                    similarity = 0.0

            # Базовый score
            base_score = (1 - context_weight) * rating + context_weight * max(0, similarity)

            # Применяем улучшения
            final_score = base_score
            applied_boosts = []

            if genre_boost:
                genre_multiplier = self._get_genre_multiplier(query_genres, book_id)
                if genre_multiplier > 1.0:
                    final_score *= genre_multiplier
                    applied_boosts.append(f"genre×{genre_multiplier:.1f}")
            
            if title_boost:
                title = row['original_title']
                title_multiplier = self._get_title_boost(context, title)
                if title_multiplier > 1.0:
                    final_score *= title_multiplier
                    applied_boosts.append(f"title×{title_multiplier:.1f}")

            recommendations.append({
                "book_id": int(book_id),
                "title": row['original_title'],
                "author": row['authors'],
                "genres": row['genres'] if 'genres' in row else self.book_genres.get(book_id, ['general']),
                "score": float(final_score),
                "base_score": float(base_score),
                "rating": float(rating),
                #"similarity": float(sim),
                "applied_boosts": applied_boosts,
                "genre_match": genre_boost and self._get_genre_multiplier(query_genres, book_id) > 1.0
            })

        recommendations.sort(key=lambda x: x["score"], reverse=True)

        processing_time = (datetime.now() - start_time).total_seconds()

        return {
            "status": "success",
            "user_id": user_id,
            "context": context,
            "detected_genres": query_genres,
            "processing_time_seconds": round(processing_time, 3),
            "recommendations": [
                {
                    "rank": i + 1,
                    "book_id": r["book_id"],
                    "score": r["score"],
                    "title": r["title"],
                    "author": r["author"],
                    "genres": r["genres"],
                    "rating": r["rating"],
                    #"similarity": r["similarity"],
                    "applied_boosts": r["applied_boosts"],
                }
                for i, r in enumerate(recommendations[:top_k])
            ],
        }
    
    
    def batch_recommend(
        self,
        requests: List[Dict[str, Any]],
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Пакетная обработка запросов
        
        Args:
            requests: список запросов [{"user_id": 1, "context": "..."}, ...]
            top_k: количество рекомендаций на запрос
        
        Returns:
            Список результатов
        """
        results = []
        for req in requests:
            result = self.recommend(
                user_id=req['user_id'],
                context=req['context'],
                top_k=top_k
            )
            results.append(result)
        
        return results

