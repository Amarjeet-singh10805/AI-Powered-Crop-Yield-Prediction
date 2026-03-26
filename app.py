from flask import Flask, request, jsonify, render_template, send_from_directory
import pickle
import numpy as np
import pandas as pd
import os
import json
import datetime
import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

try:
    import mysql.connector
    MYSQL_AVAILABLE = True
except ImportError:
    MYSQL_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder='templates', static_folder='static')

MODEL_PATH = os.path.join(BASE_DIR, "model", "crop_model.pkl")
with open(MODEL_PATH, "rb") as f:
    bundle = pickle.load(f)

model     = bundle["model"]
le_crop   = bundle["le_crop"]
le_season = bundle["le_season"]
le_state  = bundle["le_state"]
CROPS     = bundle["crops"]
SEASONS   = bundle["seasons"]
STATES    = bundle["states"]
YEAR_MIN  = bundle["year_min"]
YEAR_MAX  = bundle["year_max"]

DATA_PATH = os.path.join(BASE_DIR, "crop_yield.csv")
raw_df = pd.read_csv(DATA_PATH)
raw_df.columns = raw_df.columns.str.strip()
for col in ['Crop', 'Season', 'State']:
    raw_df[col] = raw_df[col].astype(str).str.strip()
raw_df = raw_df[raw_df['Yield'] < raw_df['Yield'].quantile(0.99)].dropna()
  
  
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "Jeet12"),
    "database": os.environ.get("DB_NAME",     "crop_yield"),
}

def get_db():
    if not MYSQL_AVAILABLE:
        return None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Exception:
        return None

def ensure_table(conn):
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id            INT AUTO_INCREMENT PRIMARY KEY,
            created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
            crop          VARCHAR(100),
            season        VARCHAR(50),
            state         VARCHAR(100),
            area          FLOAT,
            rainfall      FLOAT,
            fertilizer    FLOAT,
            pesticide     FLOAT,
            predicted_yield FLOAT
        )
    """)
    conn.commit()
    cur.close()

def save_to_db(conn, data: dict, predicted_yield: float):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO prediction_history
            (crop, season, state, area, rainfall, fertilizer, pesticide, predicted_yield)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        data['crop'], data['season'], data['state'],
        data['area'], data['rainfall'], data['fertilizer'],
        data['pesticide'], predicted_yield
    ))
    conn.commit()
    cur.close()

def fetch_history(conn, limit=20):
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT * FROM prediction_history
        ORDER BY created_at DESC LIMIT %s
    """, (limit,))
    rows = cur.fetchall()
    cur.close()
    for r in rows:
        if isinstance(r.get('created_at'), datetime.datetime):
            r['created_at'] = r['created_at'].strftime('%Y-%m-%d %H:%M:%S')
    return rows

in_memory_history = []

CHART_STYLE = {
    "bg":       "#0d1117",
    "axes_bg":  "#161b22",
    "grid":     "#21262d",
    "text":     "#e6edf3",
    "accent1":  "#58a6ff",
    "accent2":  "#3fb950",
    "accent3":  "#f78166",
}

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded

def make_trend_chart(crop, season, state, area, rainfall, fertilizer, pesticide):
    """Year-wise historical average yield + future prediction line."""
    subset = raw_df[
        (raw_df['Crop'].str.lower() == crop.lower()) &
        (raw_df['Season'].str.lower() == season.lower()) &
        (raw_df['State'].str.lower() == state.lower())
    ]
    yearly = (
        subset.groupby('Crop_Year')['Yield']
        .mean()
        .reset_index()
        .sort_values('Crop_Year')
    )
    if not yearly.empty:
        n = len(yearly)
        yearly['Crop_Year'] = list(range(2026 - n + 1, 2027))

    # Future predictions: next 5 years
    future_years = list(range(2027, 2032))
    future_preds = []
    for yr in future_years:
        try:
            crop_enc   = le_crop.transform([crop])[0]
            season_enc = le_season.transform([season])[0]
            state_enc  = le_state.transform([state])[0]
            pred = model.predict([[crop_enc, season_enc, state_enc,
                                   area, rainfall, fertilizer, pesticide]])[0]
            future_preds.append(max(0, pred))
        except Exception:
            future_preds.append(0)

    fig, ax = plt.subplots(figsize=(10, 4.5), facecolor=CHART_STYLE["bg"])
    ax.set_facecolor(CHART_STYLE["axes_bg"])

    if not yearly.empty:
        
        ax.plot(yearly['Crop_Year'], yearly['Yield'],
                color=CHART_STYLE["accent1"], linewidth=2,
                marker='o', markersize=4, label='Historical Avg Yield')
        
        

    if future_preds:
        
        if not yearly.empty:
        # 🔥 connect last historical point to future
            connect_years = [yearly['Crop_Year'].iloc[-1]] + future_years
            connect_vals  = [yearly['Yield'].iloc[-1]] + future_preds
        else:
            connect_years = future_years
            connect_vals  = future_preds

        ax.plot(connect_years, connect_vals,
            color=CHART_STYLE["accent2"], linewidth=2,
            linestyle='--', marker='s', markersize=5,
            label='Predicted (Future)')
        # 🔵 BLUE FILL (history only)
    if not yearly.empty:
        ax.fill_between(
            yearly['Crop_Year'],
            yearly['Yield'],
            alpha=0.12,
            color=CHART_STYLE["accent1"]
        )

    # 🟢 GREEN FILL (prediction including connection)
    if future_preds:
        ax.fill_between(
            connect_years,
            connect_vals,
            alpha=0.10,
            color=CHART_STYLE["accent2"]
        )

    ax.set_title(f'{crop}  •  {season}  •  {state}',
                 color=CHART_STYLE["text"], fontsize=13, pad=12, fontweight='bold')
    ax.set_xlabel('Year', color=CHART_STYLE["text"], fontsize=10)
    ax.set_ylabel('Yield (tons/ha)', color=CHART_STYLE["text"], fontsize=10)
    ax.tick_params(colors=CHART_STYLE["text"])
    ax.spines[:].set_color(CHART_STYLE["grid"])
    ax.grid(True, color=CHART_STYLE["grid"], linestyle='--', linewidth=0.6)
    ax.legend(facecolor=CHART_STYLE["axes_bg"], labelcolor=CHART_STYLE["text"],
              edgecolor=CHART_STYLE["grid"])
    for spine in ax.spines.values():
        spine.set_linewidth(0.8)

    plt.tight_layout()
    return fig_to_base64(fig)


def make_comparison_chart(crop, season, top_n=5):
    """State-wise yield comparison bar chart."""
    subset = raw_df[
        (raw_df['Crop'].str.lower() == crop.lower()) &
        (raw_df['Season'].str.lower() == season.lower())
    ]
    state_avg = (
        subset.groupby('State')['Yield']
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
    )

    fig, ax = plt.subplots(figsize=(8, 4), facecolor=CHART_STYLE["bg"])
    ax.set_facecolor(CHART_STYLE["axes_bg"])

    colors = [CHART_STYLE["accent1"]] * len(state_avg)
    bars = ax.barh(state_avg.index[::-1], state_avg.values[::-1],
                   color=colors, edgecolor=CHART_STYLE["bg"], linewidth=0.5,
                   height=0.6)
    for bar in bars:
        bar.set_alpha(0.85)

    ax.set_title(f'Top States – {crop} ({season})',
                 color=CHART_STYLE["text"], fontsize=12, pad=10, fontweight='bold')
    ax.set_xlabel('Avg Yield (tons/ha)', color=CHART_STYLE["text"], fontsize=9)
    ax.tick_params(colors=CHART_STYLE["text"])
    ax.spines[:].set_color(CHART_STYLE["grid"])
    ax.grid(True, axis='x', color=CHART_STYLE["grid"], linestyle='--', linewidth=0.5)

    plt.tight_layout()
    return fig_to_base64(fig)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/metadata')
def metadata():
    return jsonify({
        "crops":   CROPS,
        "seasons": SEASONS,
        "states":  STATES,
        "year_min": YEAR_MIN,
        "year_max": YEAR_MAX,
    })

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        crop      = data['crop'].strip()
        season    = data['season'].strip()
        state     = data['state'].strip()
        area      = float(data['area'])
        rainfall  = float(data['rainfall'])
        fertilizer = float(data['fertilizer'])
        pesticide  = float(data['pesticide'])

        crop_enc   = le_crop.transform([crop])[0]
        season_enc = le_season.transform([season])[0]
        state_enc  = le_state.transform([state])[0]

        X = np.array([[crop_enc, season_enc, state_enc,
                       area, rainfall, fertilizer, pesticide]])
        yield_pred = float(model.predict(X)[0])
        yield_pred = max(0, round(yield_pred, 4))

        trend_chart   = make_trend_chart(crop, season, state,
                                         area, rainfall, fertilizer, pesticide)
        compare_chart = make_comparison_chart(crop, season)

        record = {
            "crop": crop, "season": season, "state": state,
            "area": area, "rainfall": rainfall,
            "fertilizer": fertilizer, "pesticide": pesticide,
            "predicted_yield": yield_pred,
            "created_at": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        conn = get_db()
        if conn:
            ensure_table(conn)
            save_to_db(conn, data, yield_pred)
            conn.close()
        else:
            in_memory_history.insert(0, record)
            if len(in_memory_history) > 50:
                in_memory_history.pop()

        return jsonify({
            "success": True,
            "predicted_yield": yield_pred,
            "trend_chart":   trend_chart,
            "compare_chart": compare_chart,
        })

    except ValueError as ve:
        return jsonify({"success": False, "error": f"Invalid value: {str(ve)}"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/history')
def history():
    conn = get_db()
    if conn:
        ensure_table(conn)
        rows = fetch_history(conn)
        conn.close()
        return jsonify({"success": True, "history": rows, "source": "mysql"})
    else:
        return jsonify({
            "success": True,
            "history": in_memory_history[:20],
            "source": "memory"
        })


@app.route('/api/history/<int:rec_id>', methods=['DELETE'])
def delete_history(rec_id):
    conn = get_db()
    if conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM prediction_history WHERE id = %s", (rec_id,))
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "MySQL not available"}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000)
