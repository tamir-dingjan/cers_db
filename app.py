from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///text_db.sqlite3'
db = SQLAlchemy(app)

class TextEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(500), nullable=False)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        new_name = request.form['name']
        new_text = request.form['text']
        text_entry = TextEntry(name=new_name, text=new_text)
        db.session.add(text_entry)
        db.session.commit()
        return redirect('/')
    else:
        text_entries = TextEntry.query.all()
        return render_template('index.html', text_entries=text_entries)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
