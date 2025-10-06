from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Маршрут для отображения формы
@app.route('/')
def index():
    return render_template('form.html')

# Маршрут для обработки данных формы
@app.route('/submit', methods=['POST'])
def submit():
    # Получаем данные из формы
    name = request.form.get('name')
    email = request.form.get('email')
    
    # Обрабатываем данные (здесь можно добавить логику)
    print(f"Получены данные: {name}, {email}")
    
    # Перенаправляем или возвращаем ответ
    return f"Спасибо, {name}! Ваш email: {email}"

if __name__ == '__main__':
    app.run(debug=True)