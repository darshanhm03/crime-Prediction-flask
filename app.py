from flask import Flask, render_template, request, redirect, session, jsonify
import pandas as pd
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# =========================
# DATABASE SETUP
# =========================
conn = sqlite3.connect("users.db", check_same_thread=False)

conn.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
)
""")
conn.commit()

# =========================
# LOAD DATASET
# =========================
df = pd.read_csv("crime.csv")

df.columns = df.columns.str.strip().str.upper()
df["STATE/UT"] = df["STATE/UT"].astype(str).str.strip()
df["DISTRICT"] = df["DISTRICT"].astype(str).str.strip()
df["YEAR"] = pd.to_numeric(df["YEAR"], errors="coerce").fillna(0).astype(int)

# =========================
# RISK FUNCTION
# =========================
def get_risk(total):
    if total > 10000:
        return "High"
    elif total > 6000:
        return "Medium High"
    elif total > 3000:
        return "Medium Low"
    else:
        return "Low"

# =========================
# LOGIN SYSTEM
# =========================
@app.route('/')
def login():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def do_login():
    user = request.form['username']
    pwd = request.form['password']

    cur = conn.execute(
        "SELECT * FROM users WHERE username=? AND password=?",
        (user, pwd)
    )

    if cur.fetchone():
        session['user'] = user
        return redirect('/dashboard')
    else:
        return "Invalid Login"

@app.route('/signup')
def signup():
    return render_template("signup.html")

@app.route('/register', methods=['POST'])
def register():
    user = request.form['username']
    pwd = request.form['password']

    try:
        conn.execute("INSERT INTO users VALUES(NULL, ?, ?)", (user, pwd))
        conn.commit()
        return redirect('/')
    except:
        return "User already exists"

# =========================
# DASHBOARD
# =========================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template("dashboard.html", user=session['user'])

# =========================
# LOGOUT
# =========================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# =========================
# PREDICTION PAGE
# =========================
@app.route('/prediction')
def prediction():
    if 'user' not in session:
        return redirect('/')

    states = sorted(df["STATE/UT"].unique())
    return render_template("prediction.html", states=states)

# =========================
# PREDICT + CHART DATA
# =========================
@app.route('/predict', methods=['POST'])
def predict():
    if 'user' not in session:
        return redirect('/')

    state = request.form['state']
    district = request.form['district']
    year = int(request.form['year'])

    filtered = df[
        df["STATE/UT"].str.contains(state, case=False) &
        df["DISTRICT"].str.contains(district, case=False) &
        (df["YEAR"] == year)
    ]

    if filtered.empty:
        return "No data found"

    crime_cols = df.columns.difference(["STATE/UT", "DISTRICT", "YEAR"])

    # 🔥 CHART DATA
    crime_data = filtered[crime_cols].iloc[0].to_dict()

    total = int(sum(crime_data.values()))
    risk = get_risk(total)

    return render_template(
        "result.html",
        state=state,
        district=district,
        year=year,
        total=total,
        risk=risk,
        crime_data=crime_data
    )

# =========================
# API ROUTES
# =========================
@app.route('/get_districts/<state>')
def get_districts(state):
    districts = df[
        df["STATE/UT"].str.contains(state, case=False)
    ]["DISTRICT"].unique().tolist()

    return jsonify({"districts": districts})

@app.route('/get_years')
def get_years():
    years = sorted(df["YEAR"].unique().tolist())
    return jsonify({"years": years})

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)