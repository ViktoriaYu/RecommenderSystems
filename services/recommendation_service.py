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
        print(f"[recommendation_service.py] Инициализация сервиса рекомендаций...")
        
        # Определяем путь к модели
        if model_path is None:
            model_path = os.path.join(
                os.path.dirname(__file__), 
                '..', 
                'models', 
                'recommendation_system.pkl'
            )
        
        print("[recommendation_service.py]", model_path)
        # Проверяем существование файла
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found: {model_path}")
        
        # Загружаем систему
        with open(model_path, 'rb') as f:
            self.system = pickle.load(f)
        
        # Импортируем модель
        try:
            from ml_models.recommender_model import TextAwareDynamicRecommender
            self.model_class = TextAwareDynamicRecommender
        except ImportError:
            # Если не можем импортировать, создаем локальный класс
            self.model_class = self._create_model_class()
        
        # Загружаем модель
        self.model = self.model_class(**self.system['model_config'])
        self.model.load_state_dict(self.system['model_state_dict'])
        self.model.eval()
        
        # Загружаем данные
        self.books_df = self.system['books_data']
        self.user_encoder = self.system['user_encoder']
        self.author_encoder = self.system['author_encoder']
        
        # Устройство
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model.to(self.device)
        
        print(f" Сервис готов:")
        print(f"   • Книг в базе: {len(self.books_df)}")
        print(f"   • Устройство: {self.device}")
        print(f"   • Пользователей: {self.system['model_config']['num_users']}")
        print(f"   • Авторов: {self.system['model_config']['num_authors']}")
    
    def _create_model_class(self):
        """Создает класс модели локально, если не удалось импортировать"""
        import torch.nn as nn
        import torch.nn.functional as F
        
        class TextAwareDynamicRecommender(nn.Module):
            """Локальная версия модели"""
            
            def __init__(self, num_users, num_books, num_authors, 
                         text_encoder_dim=128, user_dim=128, book_dim=128, author_dim=64):
                super().__init__()
                
                # Основные эмбеддинги
                self.user_embedding = nn.Embedding(num_users, user_dim)
                self.book_embedding = nn.Embedding(num_books, book_dim)
                self.author_embedding = nn.Embedding(num_authors, author_dim)
                
                # Текстовый энкодер
                self.text_encoder = nn.Sequential(
                    nn.Embedding(128, 32),
                    nn.Flatten(),
                    nn.Linear(32 * 256, 128),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(128, 64),
                    nn.ReLU(),
                    nn.Linear(64, 64)
                )
                
                # Проекция книги в текстовое пространство
                self.book_to_text_space = nn.Sequential(
                    nn.Linear(book_dim + author_dim, 128),
                    nn.ReLU(),
                    nn.Linear(128, 64)
                )
                
                # Основная рекомендательная часть
                self.recommender = nn.Sequential(
                    nn.Linear(user_dim + book_dim + author_dim + 64, 256),
                    nn.ReLU(),
                    nn.Dropout(0.3),
                    nn.Linear(256, 128),
                    nn.ReLU(),
                    nn.Linear(128, 1),
                    nn.Sigmoid()
                )
            
            def forward(self, user_ids, book_ids, author_ids, text_tensor=None):
                """Forward pass"""
                user_emb = self.user_embedding(user_ids)
                book_emb = self.book_embedding(book_ids)
                author_emb = self.author_embedding(author_ids)
                
                if text_tensor is not None:
                    # Кодируем текст
                    text_emb = self.text_encoder(text_tensor)
                    
                    # Проецируем книгу
                    book_features = torch.cat([book_emb, author_emb], dim=1)
                    book_text_emb = self.book_to_text_space(book_features)
                    
                    # Вычисляем сходство
                    similarity = F.cosine_similarity(text_emb, book_text_emb, dim=1)
                    
                    # Объединяем всё
                    combined = torch.cat([user_emb, book_emb, author_emb, text_emb], dim=1)
                    rating = self.recommender(combined)
                    
                    return rating, similarity.unsqueeze(1)
                else:
                    # Без текста
                    combined = torch.cat([user_emb, book_emb, author_emb, 
                                         torch.zeros_like(book_emb)], dim=1)
                    rating = self.recommender(combined)
                    return rating
        
        return TextAwareDynamicRecommender
    
    def _text_to_tensor(self, text: str) -> torch.Tensor:
        """Конвертирует текст в тензор"""
        chars = [min(ord(c), 127) for c in text[:256]]
        if len(chars) < 256:
            chars += [0] * (256 - len(chars))
        return torch.tensor([chars], dtype=torch.long).to(self.device)
    
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
        max_books: int = 2000
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
            # Кодируем пользователя
            user_encoded = self._get_user_encoded(user_id)
            if user_encoded is None:
                return {
                    "status": "error",
                    "message": f"User {user_id} not found in model",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error encoding user: {str(e)}",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
        
        # Подготавливаем тензоры
        user_tensor = torch.tensor([user_encoded], dtype=torch.long).to(self.device)
        context_tensor = self._text_to_tensor(context) if context else None
        
        # Ограничиваем количество книг для скорости
        books_to_check = self.books_df.head(max_books)
        
        recommendations = []
        
        # Оцениваем книги
        for _, row in books_to_check.iterrows():
            book_tensor = torch.tensor([row['book_id'] - 1], dtype=torch.long).to(self.device)

            try:
                author_encoded = self.author_encoder.transform([row['authors']])[0]
            except:
                author_encoded = 0

            author_tensor = torch.tensor([author_encoded], dtype=torch.long).to(self.device)
            
            with torch.no_grad():
                output = self.model(user_tensor, book_tensor, author_tensor, context_tensor)
                
                if isinstance(output, tuple):
                    rating_pred, similarity = output
                    rating = rating_pred.item()
                    sim = similarity.item()
                else:
                    rating = output.item()
                    sim = 0.0

                # Комбинированный score
                score = 0.7 * rating + 0.3 * max(0, sim)

            recommendations.append({
                "book_id": int(row['book_id']),
                "title": row['original_title'],
                "author": row['authors'],
                "score": float(score),
                "rating": float(rating),
                "similarity": float(sim)
            })
        
        # Сортировка
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        
        # Формируем ответ
        processing_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "user_id": user_id,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(processing_time, 3),
            "recommendations": [
                {
                    "item_id": rec["book_id"],
                    "score": rec["score"],
                    "title": rec["title"],
                    "author": rec["author"]
                }
                for rec in recommendations[:top_k]
            ],
            "metadata": {
                "total_books_checked": len(recommendations),
                "top_k_requested": top_k,
                "top_k_returned": min(top_k, len(recommendations)),
                "max_books_limit": max_books
            }
        }
        
        return result
    
    
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

