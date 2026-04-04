import os
from flask import Flask, render_template
from back.database.database import create_database

app = Flask(__name__)

@app.route('/')
@app.route('/index')
def index():
    user = "Ученик Яндекс.Лицея"
    return render_template('base.html')

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)