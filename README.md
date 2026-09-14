# Student Placement Prediction System

A machine learning web application that predicts whether a student is likely to
be placed, returns a placement probability, classifies it as High, Medium or
Low, and generates rule-based recommendations.

## Overview

- Students register, fill in their profile, and run a placement prediction.
- A prediction returns a status (Placed / Not Placed), a probability percentage,
  and a High/Medium/Low category.
- A rule-based engine lists each student's strengths, areas to improve, and
  recommended actions.
- Every prediction is stored in the database.
- Admins get a dashboard with statistics and charts, student management
  (search, filter, pagination), the ability to predict for any student, and a
  downloadable CSV report.

The model is trained once by a separate script and saved to disk. The web app
loads the saved model and uses it for predictions, so the model is never trained
during a web request.

## Technology Stack

| Layer            | Technology |
|------------------|------------|
| Frontend         | HTML5, CSS3, Bootstrap 5, Vanilla JavaScript, Chart.js |
| Backend          | Python 3, Flask (application factory + blueprints) |
| Database         | MySQL (SQLAlchemy, PyMySQL) |
| Machine Learning | scikit-learn, pandas, NumPy, joblib |
| Auth / Forms     | Flask-Login, Flask-WTF (CSRF), Werkzeug password hashing |

## Project Structure

```
app.py                    create_app() factory, error handlers, logging
config.py                 thresholds, feature lists, validation ranges, rules
extensions.py             shared db / login_manager / csrf instances
requirements.txt
.env.example

data/                     dataset CSV goes here
logs/                     app.log (created at runtime)

ml/
  data_validation.py      dataset validation
  train_model.py          trains and compares models, saves the best pipeline
  eda.py                  exploratory data analysis and charts
  predict.py              loads the saved pipeline and runs inference
  models/                 placement_model.pkl + model_metadata.json

models/database_models.py User, Student, Prediction (SQLAlchemy)
routes/                   auth, student, admin, prediction (JSON API) blueprints
services/                 prediction, recommendation, stats, input validation
templates/                Bootstrap templates (base, student/, admin/)
static/                   css/style.css, js/app.js
scripts/                  init_db.py, import_dataset.py
tests/                    pytest suite (in-memory SQLite, no MySQL needed)
```

Routes, services, ML, models and templates are kept separate so new features can
be added without changing unrelated parts of the app.

## Requirements

- Python 3.11 or 3.12 (a virtual environment is recommended).
- MySQL Server 8.x running locally.
- The dataset CSV placed at `data/student_placement.csv`.

## Installation

Clone the repository and move into the project folder, then create and activate
a virtual environment:

```bash
python -m venv venv
```

Windows (PowerShell or cmd):

```bash
venv\Scripts\activate
```

macOS / Linux:

```bash
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

## MySQL Setup

Log into MySQL and create the database:

```sql
CREATE DATABASE student_placement CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

You can use the `root` account or create a dedicated user.

## Environment Setup

Copy the example environment file and edit the values:

```bash
copy .env.example .env      # Windows
# cp .env.example .env       # macOS / Linux
```

Set `SECRET_KEY` and your MySQL credentials in `.env`:

```
SECRET_KEY=some-long-random-string
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=student_placement
MYSQL_USER=root
MYSQL_PASSWORD=your_password
```

## Dataset

Place the dataset at `data/student_placement.csv` with these columns:

```
Student_ID, Age, Gender, Degree, Branch, CGPA, Internships, Projects,
Coding_Skills, Communication_Skills, Aptitude_Test_Score, Soft_Skills_Rating,
Certifications, Backlogs, Placement_Status
```

`Placement_Status` must be either `Placed` or `Not Placed`.

To print dataset statistics and save charts to `ml/eda_output/`:

```bash
python ml/eda.py
```

## Train the Model

```bash
python ml/train_model.py
```

This validates the data, trains Logistic Regression, Decision Tree, Random
Forest and Gradient Boosting, prints a comparison table (Accuracy, Precision,
Recall, F1, ROC-AUC and a confusion matrix), selects the best model, and saves:

```
ml/models/placement_model.pkl
ml/models/model_metadata.json
```

## Initialize the Database

Creates the tables and a default admin account:

```bash
python scripts/init_db.py
```

The default admin credentials come from `.env` (`admin` / `admin123`). Change
them before deploying anywhere.

## Import the Dataset

Bulk-imports student records into MySQL and skips duplicate Student IDs:

```bash
python scripts/import_dataset.py
```

## Run the Application

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in a browser. You can also run it with
`flask --app app run`.

## Using the App

Student:

1. Register an account and log in.
2. Fill in your profile (Student ID and the profile fields).
3. Open Predict and click Predict Placement.
4. View the probability, category and predicted status.
5. Check Recommendations and History.

Admin (log in with the seeded admin account):

- Dashboard: totals, Placed vs Not Placed, High/Medium/Low, branch distribution,
  a CGPA vs placement chart, and the latest model's metrics.
- Students: search by Student ID, filter by degree, branch or category, and run
  a prediction for any student.
- Reports: download a CSV of each student's latest prediction.

## Running the Tests

```bash
pytest
```

The tests use an in-memory SQLite database and a small in-memory model, so they
run without MySQL or the full dataset.

## Configuration

The values you are most likely to change live in `config.py`:

- `PROBABILITY_THRESHOLDS`: the High/Medium/Low cut-offs (default 0.80 and 0.50).
- `NUMERIC_FEATURES`, `CATEGORICAL_FEATURES`: the model feature lists.
- `VALIDATION_RANGES`: allowed minimum and maximum for each numeric input.
- `RECOMMENDATION_RULES`: the recommendation thresholds and messages.

## A Note on Model Scores

On this dataset the tree-based models reach very high accuracy because
`Placement_Status` is almost fully determined by the feature values, so the
models can separate the two classes very well. A fully grown tree would output
probabilities of only 0% or 100%, which would make the Medium category never
appear. To avoid that, the tree models use a limited depth and the best model is
chosen among near-tied candidates by how varied its probabilities are. See
`ml/train_model.py`.

## Troubleshooting

- Cannot connect to MySQL: make sure MySQL is running, the `student_placement`
  database exists, and the `.env` credentials are correct.
- Trained model not found: run `python ml/train_model.py` first.
- Access denied for user: the MySQL user or password in `.env` is wrong.
- `caching_sha2_password` errors: upgrade PyMySQL or set the MySQL user's auth
  plugin to `mysql_native_password`.
- Errors are written to `logs/app.log`; users only see friendly messages.

## Security

- Passwords are stored as Werkzeug hashes, never in plain text.
- Session-based authentication with student / admin role checks.
- CSRF protection on HTML forms (Flask-WTF).
- SQLAlchemy uses parameterized queries.
- The dataset and `.env` are not served through the web server.
- Change all default credentials before deploying anywhere.
