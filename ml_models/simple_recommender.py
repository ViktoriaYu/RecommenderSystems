import pickle
import json
import numpy as np
from scipy.sparse import load_npz
import os
import sys
from pathlib import Path
from datetime import datetime
import time
import pandas as pd

class SimpleRecommender:
    """Простой загрузчик модели рекомендательной системы (ALS + Content)"""
    
    def __init__(self, model_path=None):
        """Загрузка всех файлов модели"""
        if model_path is None:
            # Определяем путь относительно расположения файла
            current_dir = Path(__file__).parent.parent
            model_path = current_dir / "models"
        
        print(f"📦 Загрузка SimpleRecommender из {model_path}...")
        
        try:
            # Проверяем существование файлов
            required_files = [
                'model_params.json',
                'als_model.pkl', 
                'user_item_matrix.npz',
                'content_similarity.pkl',
                'mappings.pkl'
            ]
            
            for file in required_files:
                file_path = os.path.join(model_path, file)
                if not os.path.exists(file_path):
                    print(f"⚠️  Файл {file} не найден по пути: {file_path}")
                    raise FileNotFoundError(f"Файл {file} не найден")
            
            # Загрузка всех необходимых файлов
            with open(os.path.join(model_path, 'model_params.json'), 'r', encoding='utf-8') as f:
                self.params = json.load(f)
            
            with open(os.path.join(model_path, 'als_model.pkl'), 'rb') as f:
                self.als_model = pickle.load(f)
            
            self.user_item_matrix = load_npz(os.path.join(model_path, 'user_item_matrix.npz'))
            
            with open(os.path.join(model_path, 'content_similarity.pkl'), 'rb') as f:
                self.content_similarity = pickle.load(f)
            
            with open(os.path.join(model_path, 'mappings.pkl'), 'rb') as f:
                mappings = pickle.load(f)
            
            self.user_to_idx = mappings['user_to_idx']
            self.item_to_idx = mappings['item_to_idx']
            self.idx_to_item = mappings['idx_to_item']
            self.popular_items = mappings['popular_items']
            
            # Загрузка дополнительных файлов если есть
            self.content_features = None
            if os.path.exists(os.path.join(model_path, 'content_features.pkl')):
                with open(os.path.join(model_path, 'content_features.pkl'), 'rb') as f:
                    self.content_features = pickle.load(f)
            
            # Подготовка эмбеддингов для item-item
            self.item_embeddings = self.als_model.item_factors
            norms = np.linalg.norm(self.item_embeddings, axis=1)
            norms[norms == 0] = 1  # избегаем деления на 0
            self.normalized_item_embeddings = self.item_embeddings / norms[:, np.newaxis]
            
            print(f"✅ SimpleRecommender загружен: {len(self.user_to_idx)} пользователей, {len(self.item_to_idx)} книг")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки SimpleRecommender: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def recommend_for_user(self, user_id, k=10, include_history=False):
        """
        Получить рекомендации для пользователя
        """
        start_time = time.time()
        
        try:
            # Преобразуем user_id в строку
            user_id_str = str(user_id)
            
            # Если новый пользователь - популярные книги
            if user_id not in self.user_to_idx:
                recommendations = []
                for i, item_id in enumerate(self.popular_items[:k]):
                    item_id_str = str(item_id)
                    recommendations.append({
                    "item_id": item_id,
                    "score": 1.0 - (i * 0.1),
                    "title": f"Book {item_id}",
                    "author": f"Author of {item_id}"
                    })
                
                return {
                    'status': 'success',
                    'user_id': user_id,
                    'recommendations': recommendations,
                    'message': 'Новый пользователь, показаны популярные книги',
                    'processing_time': round(time.time() - start_time, 3)
                }
            
            # Существующий пользователь
            user_idx = self.user_to_idx[user_id]
            
            # Получаем рекомендации от ALS
            als_indices, als_scores = self.als_model.recommend(
                user_idx, 
                self.user_item_matrix[user_idx], 
                N=self.params.get('als_candidates', 100), 
                filter_already_liked_items=True
            )
            
            # Преобразуем в item_id
            als_recommendations = {}
            for idx, score in zip(als_indices, als_scores):
                item_id = self.idx_to_item[idx]
                als_recommendations[item_id] = float(score)
            
            # Получаем историю пользователя
            user_history = []
            if include_history:
                user_indices = self.user_item_matrix[user_idx].indices
                user_history = [self.idx_to_item[idx] for idx in user_indices 
                              if self.user_item_matrix[user_idx, idx] > 0]
            
            # Комбинируем с контентными рекомендациями
            final_items = self._combine_recommendations(als_recommendations, user_history, k)
            
            # Формируем ответ
            recommendations = []
            for item_id, score in final_items:
                item_id_str = str(item_id)
                recommendations.append({
                    'book_id': item_id_str,
                    'score': round(score, 4),
                    'title': f'Book {item_id_str}',
                    'author': f'Author of {item_id_str}',
                    'reason': f'Рекомендовано на основе ваших оценок (score: {round(score, 2)})'
                })
            
            return {
                'status': 'success',
                'user_id': user_id_str,
                'recommendations': recommendations,
                'processing_time': round(time.time() - start_time, 3)
            }
            
        except Exception as e:
            print(f"❌ Ошибка в recommend_for_user: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'user_id': user_id,
                'recommendations': []
            }
    
    def similar_items(self, item_id, k=10, method="hybrid"):
        """
        Получить похожие книги
        """
        start_time = time.time()
        
        try:
            # Преобразуем item_id в строку
            item_id_str = str(item_id)
            
            if item_id not in self.item_to_idx:
                return {
                    'status': 'error',
                    'message': f'Книга "{item_id}" не найдена в модели',
                    'recommendations': []
                }
            
            # Получаем похожие книги
            if method == "als":
                similar = self._get_similar_als(item_id, k)
            elif method == "content":
                similar = self._get_similar_content(item_id, k)
            else:  # hybrid
                similar = self._get_similar_hybrid(item_id, k)
            
            # Формируем ответ
            recommendations = []
            for similar_item_id, score in similar:
                similar_item_id_str = str(similar_item_id)
                recommendations.append({
                    'book_id': similar_item_id,
                    'score': round(score, 4),
                    'title': f'Book {similar_item_id}',
                    'author': f'Author of {similar_item_id}',
                    'reason': f'Похоже на книгу {item_id} (score: {round(score, 2)})'
                })
            
            return {
                'status': 'success',
                'base_book': {
                    'book_id': item_id,
                    'title': f'Book {item_id}',
                    'author': f'Author of {item_id}'
                },
                'recommendations': recommendations,
                'method': method,
                'processing_time': round(time.time() - start_time, 3)
            }
            
        except Exception as e:
            print(f"❌ Ошибка в similar_items: {e}")
            return {
                'status': 'error',
                'message': str(e),
                'item_id': item_id,
                'recommendations': []
            }
    
    def _combine_recommendations(self, als_recommendations, user_history, k):
        """Простое комбинирование рекомендаций"""
        if not user_history:
            return sorted(als_recommendations.items(), key=lambda x: x[1], reverse=True)[:k]
        
        combined = {}
        content_weight = self.params.get('content_weight', 0.3)
        
        for item_id, als_score in als_recommendations.items():
            item_id_str = str(item_id)
            
            # Контентный скор
            content_score = 0
            count = 0
            
            for hist_item in user_history:
                hist_item_str = str(hist_item)
                if hist_item_str in self.content_similarity and item_id_str in self.content_similarity[hist_item_str]:
                    content_score += self.content_similarity[hist_item_str][item_id_str]
                    count += 1
            
            if count > 0:
                content_score /= count
            
            # Комбинируем
            combined_score = (1 - content_weight) * als_score + content_weight * content_score
            combined[item_id] = combined_score
        
        return sorted(combined.items(), key=lambda x: x[1], reverse=True)[:k]
    
    def _get_similar_als(self, item_id, k):
        """Похожие книги через ALS"""
        item_idx = self.item_to_idx[item_id]
        item_embedding = self.normalized_item_embeddings[item_idx]
        
        similarities = np.dot(self.normalized_item_embeddings, item_embedding)
        similarities[item_idx] = -1  # исключаем саму книгу
        
        similar_indices = np.argsort(similarities)[::-1][:k]
        similar_scores = similarities[similar_indices]
        
        return [(self.idx_to_item[idx], float(score)) 
                for idx, score in zip(similar_indices, similar_scores)]
    
    def _get_similar_content(self, item_id, k):
        """Похожие книги через контент"""
        if item_id not in self.content_similarity:
            return []
        
        similarities = self.content_similarity[item_id]
        # Конвертируем в список кортежей
        similar_items = []
        for sim_item, score in similarities.items():
            try:
                similar_items.append((int(sim_item), float(score)))
            except:
                similar_items.append((sim_item, float(score)))
        
        return sorted(similar_items, key=lambda x: x[1], reverse=True)[:k]
    
    def _get_similar_hybrid(self, item_id, k):
        """Гибридный метод"""
        als_similar = self._get_similar_als(item_id, k*2)
        content_similar = self._get_similar_content(item_id, k*2)
        
        # Объединяем
        all_items = {}
        for item, score in als_similar:
            all_items[item] = score * 0.7  # вес ALS
        
        for item, score in content_similar:
            try:
                item_key = int(item) if isinstance(item, str) and item.isdigit() else item
            except:
                item_key = item
            
            if item_key in all_items:
                all_items[item_key] += score * 0.3  # добавляем content вес
            else:
                all_items[item_key] = score * 0.3
        
        # Исключаем исходную книгу
        try:
            item_id_key = int(item_id) if item_id.isdigit() else item_id
        except:
            item_id_key = item_id
            
        if item_id_key in all_items:
            del all_items[item_id_key]
        
        return sorted(all_items.items(), key=lambda x: x[1], reverse=True)[:k]