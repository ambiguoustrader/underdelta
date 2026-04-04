import os
from flask import Flask, render_template
from back.database.database import create_database

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..'))
static_dir = os.path.join(project_root, 'static')

app = Flask(__name__, static_folder=static_dir)

@app.route('/')
@app.route('/index')
def index():
    user = "Ученик Яндекс.Лицея"
    return render_template('base.html')

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)