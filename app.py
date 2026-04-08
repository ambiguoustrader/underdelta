from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
@app.route('/index', methods=['POST', 'GET'])
def index():
    user = "Ученик Яндекс.Лицея"
    return render_template('index.html')

if __name__ == '__main__':
    app.run(port=8080, host='127.0.0.1', debug=True)