import torch
import torch.nn as nn
import torch.nn.functional as F

class TextAwareDynamicRecommender(nn.Module):
    """Точная архитектура обученной модели"""

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