from flask import Flask, render_template, url_for

app = Flask(__name__, static_folder='static', template_folder='Templates')
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/reportcomplete')
def report_complete():
    return render_template('reportcomplete.html')

if __name__ == '__main__':
    app.run(debug=True) 