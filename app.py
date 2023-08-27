from flask import Flask, flash, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import re
import numpy as np
import pandas as pd

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///text_db.sqlite3'
db = SQLAlchemy(app)

class TextEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(500), nullable=False)

class AssayEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    activity = db.Column(db.Float, nullable=False)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_file(filename):
    # Open the file
    try:
        df = pd.read_excel(filename)
    except:
        print("Couldn't open file: ", filename)
    # Identify the relevant portion of data
    data = df.fillna("")

    def get_column_most_abundant_in(label, df):
        label_counts = [np.sum(df[x].str.contains(label, na=False, flags=re.IGNORECASE)) for x in df.columns]
        label_col = df.columns[np.where(np.asarray(label_counts) == np.max(label_counts))[0][0]]
        return label_col
    # Want to find the column that contains all of the lane labels, and navigate from there
    # lane_counts = [np.sum(data[x].str.contains("lane", na=False, flags=re.IGNORECASE)) for x in data.columns]
    # lane_col = data.columns[np.where(np.asarray(lane_counts) == np.max(lane_counts))[0][0]]

    lane_col = get_column_most_abundant_in("lane", data)
    subset = data[data[lane_col].str.contains("lane", na=False, flags=re.IGNORECASE)]
    # Next find the columns containing the lane names, and the activity results
    # name_counts = [np.sum(subset[x].str.contains("pcdna|blank|wt", na=False, flags=re.IGNORECASE)) for x in subset.columns]
    # name_col = subset.columns[np.where(np.asarray(name_counts) == np.max(name_counts))[0][0]]

    name_col = get_column_most_abundant_in("pcdna|blank|wt", subset)
    # Look for the "pmol/mg" column - this should be aligned to the labels, whereas the "pmol/mg/min" isn't
    activity_col = False
    for x in subset.columns:
        if subset[x].to_list()[0] == "pmol/mg":
            activity_col = subset.columns[x]
            break
    if not activity_col:
        # Couldn't find the activity data by name alone - try something slower
        # activity_counts = [np.sum(subset[x].str.contains("pmol/mg", na=False, flags=re.IGNORECASE)) for x in subset.columns]
        # activity_col = subset.columns[np.where(np.asarray(name_counts) == np.max(name_counts))[0][0]]
        activity_col = get_column_most_abundant_in("pmol/mg", subset)
    # Lastly we need to know the experiment time to log the final activity
    time_col = get_column_most_abundant_in("time \(min\)", data)
    log_next_field = False
    experiment_time = False
    for i in data[time_col]:
        if log_next_field and not experiment_time:
            experiment_time = float(i)
        if i == "time (min)":
            log_next_field = True
        
    # Store in the database
    for name, activity in zip(subset[name_col], subset[activity_col]):
        if name.strip() == "":
            continue
        else:
            try:
                print(name, activity/experiment_time)
                assay_entry = AssayEntry(name=name, activity=activity/experiment_time)
                db.session.add(assay_entry)
                db.session.commit()
            except:
                print("Activity data not processed correctly!")

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


@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the request has a file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # Catch empty filenames
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            process_file(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('index'))
        # At this point, we should have the file in the local "uploads" folder

    return render_template('uploader.html')


@app.route('/view', methods=['GET'])
def show_data():
    data = AssayEntry.query.all()
    return render_template('index.html', text_entries=data)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
