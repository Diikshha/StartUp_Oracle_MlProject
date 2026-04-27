import os
import json
import uuid
import pickle
import joblib
import hashlib
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")
import numpy as np
import pandas as pd
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, flash, send_file
)

# ── PDF generation ────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing, Rect, String, Circle
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "startup-predictor-secret-2024")

# ── paths ────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
USERS_FILE  = os.path.join(BASE_DIR, "users.json")
HISTORY_CSV = os.path.join(BASE_DIR, "data", "history.csv")
MODEL_DIR   = os.path.join(BASE_DIR, "model")

os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# ── model loading (with graceful fallback) ───────────────────────────────────
def _load_pickle(name):
    path = os.path.join(MODEL_DIR, name)
    if not os.path.exists(path):
        return None
    try:
        return joblib.load(path)
    except Exception as e:
        print(f"[WARN] Could not load {name}: {e}")
        return None

model         = _load_pickle("startup_model.pkl")
scaler        = _load_pickle("scaler.pkl")
features_list = _load_pickle("features.pkl")

def _demo_predict(funding_usd, rounds, age):
    score = (
        min(funding_usd / 10_000_000, 1.0) * 0.45
        + min(rounds / 10, 1.0) * 0.30
        + min(age / 10, 1.0) * 0.25
    )
    prob = round(float(np.clip(score + np.random.normal(0, 0.03), 0.05, 0.97)), 4)
    label = 1 if prob >= 0.5 else 0
    return label, prob

def predict_one(funding_usd, rounds, age):
    if model is None:
        return _demo_predict(funding_usd, rounds, age)
    try:
        if features_list and len(features_list) >= 3:
            row = pd.DataFrame([[funding_usd, rounds, age]], columns=features_list[:3])
        else:
            row = pd.DataFrame([[funding_usd, rounds, age]],
                               columns=["funding_total_usd", "funding_rounds", "startup_age"])
        if scaler:
            row = scaler.transform(row)
        prob  = float(model.predict_proba(row)[0][1])
        label = int(model.predict(row)[0])
        return label, round(prob, 4)
    except Exception as e:
        print(f"[predict error] {e}")
        return _demo_predict(funding_usd, rounds, age)

# ── helpers ──────────────────────────────────────────────────────────────────
def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE) as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_history():
    if not os.path.exists(HISTORY_CSV):
        return pd.DataFrame(columns=[
            "id","user","timestamp","funding_total_usd",
            "funding_rounds","startup_age","prediction","probability"
        ])
    return pd.read_csv(HISTORY_CSV)

def append_history(row: dict):
    df = load_history()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(HISTORY_CSV, index=False)

def insights(funding_usd, rounds, age, prob):
    tips = []
    if funding_usd < 500_000:
        tips.append(("💰", "Funding below $500K", "Consider seed/angel rounds to extend runway and credibility."))
    elif funding_usd < 5_000_000:
        tips.append(("💰", "Early-stage funding", "Strong Series A positioning. Focus on product-market fit metrics."))
    else:
        tips.append(("💰", "Well-funded startup", "Capital available — prioritize efficient growth over burn."))

    if rounds == 0:
        tips.append(("🔄", "No funding rounds", "Bootstrap signals lean ops; investors may want traction proof."))
    elif rounds <= 2:
        tips.append(("🔄", "Early funding rounds", "2-4 rounds is the sweet spot for Series A/B momentum."))
    else:
        tips.append(("🔄", "Seasoned fundraiser", "Multiple rounds signal investor confidence & market validation."))

    if age <= 1:
        tips.append(("📅", "Very early stage", "Less than 1 year — focus on MVP and first paying customers."))
    elif age <= 3:
        tips.append(("📅", "Growth stage", "Prime window for scaling; 1-3 yrs shows early product-market fit."))
    else:
        tips.append(("📅", "Mature startup", "4+ years of survival is itself a strong signal to investors."))

    if prob >= 0.75:
        tips.append(("🚀", "High success probability", "Strong fundamentals. Double down on growth levers."))
    elif prob >= 0.5:
        tips.append(("⚡", "Moderate outlook", "Promising — address weakest pillar to push above 75%."))
    else:
        tips.append(("⚠️", "High-risk profile", "Revisit funding strategy, timelines, and growth metrics."))

    return tips

def logged_in():
    return "username" in session

# ── PDF report generation ─────────────────────────────────────────────────────
BRAND_DARK   = colors.HexColor("#0f172a")   # slate-900
BRAND_MID    = colors.HexColor("#1e3a5f")   # deep navy
BRAND_ACCENT = colors.HexColor("#3b82f6")   # blue-500
BRAND_GREEN  = colors.HexColor("#22c55e")   # green-500
BRAND_RED    = colors.HexColor("#ef4444")   # red-500
BRAND_AMBER  = colors.HexColor("#f59e0b")   # amber-500
BRAND_LIGHT  = colors.HexColor("#f1f5f9")   # slate-100
BRAND_WHITE  = colors.white

def _prob_bar(prob, width=120, height=14):
    """Draw a small probability gauge bar."""
    d = Drawing(width, height)
    # Background track
    d.add(Rect(0, 2, width, height - 4, fillColor=colors.HexColor("#e2e8f0"), strokeColor=None))
    # Filled portion
    fill_w = width * prob
    bar_color = BRAND_GREEN if prob >= 0.65 else (BRAND_AMBER if prob >= 0.45 else BRAND_RED)
    d.add(Rect(0, 2, fill_w, height - 4, fillColor=bar_color, strokeColor=None))
    # Label
    label = f"{prob*100:.1f}%"
    d.add(String(width + 5, 3, label, fontSize=8, fillColor=BRAND_DARK))
    return d

def generate_history_pdf(username, records, output_path):
    """
    Generate a polished multi-section PDF report for a user's prediction history.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm, bottomMargin=16*mm,
        title=f"Startup Prediction Report — {username}",
        author="Startup Predictor AI",
    )

    W, H = A4
    content_width = W - 36*mm

    styles = getSampleStyleSheet()

    # ── custom styles ──────────────────────────────────────────────────────
    s_title = ParagraphStyle("ReportTitle",
        fontSize=26, leading=32, textColor=BRAND_WHITE,
        fontName="Helvetica-Bold", alignment=TA_LEFT)

    s_subtitle = ParagraphStyle("Subtitle",
        fontSize=11, leading=14, textColor=colors.HexColor("#94a3b8"),
        fontName="Helvetica", alignment=TA_LEFT)

    s_section = ParagraphStyle("Section",
        fontSize=13, leading=16, textColor=BRAND_ACCENT,
        fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4)

    s_body = ParagraphStyle("Body",
        fontSize=9, leading=13, textColor=BRAND_DARK,
        fontName="Helvetica")

    s_small = ParagraphStyle("Small",
        fontSize=8, leading=11, textColor=colors.HexColor("#64748b"),
        fontName="Helvetica")

    s_card_title = ParagraphStyle("CardTitle",
        fontSize=10, leading=13, textColor=BRAND_MID,
        fontName="Helvetica-Bold")

    s_card_body = ParagraphStyle("CardBody",
        fontSize=8.5, leading=12, textColor=colors.HexColor("#374151"),
        fontName="Helvetica")

    s_insight_title = ParagraphStyle("InsightTitle",
        fontSize=9, leading=12, textColor=BRAND_MID,
        fontName="Helvetica-Bold")

    s_insight_body = ParagraphStyle("InsightBody",
        fontSize=8.5, leading=12, textColor=colors.HexColor("#374151"),
        fontName="Helvetica")

    story = []

    # ══════════════════════════════════════════════════════════════════════
    # HEADER BANNER  (drawn as a coloured Table row)
    # ══════════════════════════════════════════════════════════════════════
    now_str = datetime.utcnow().strftime("%d %B %Y, %H:%M UTC")
    header_data = [[
        Paragraph(f"Startup Predictor AI", s_title),
        Paragraph(f"Prediction Report<br/><font size=9 color='#94a3b8'>"
                  f"User: {username} &nbsp;|&nbsp; Generated: {now_str}</font>",
                  ParagraphStyle("RH", fontSize=11, leading=15,
                                 textColor=BRAND_WHITE, fontName="Helvetica",
                                 alignment=TA_RIGHT)),
    ]]
    header_table = Table(header_data, colWidths=[content_width * 0.55, content_width * 0.45])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), BRAND_MID),
        ("TOPPADDING",   (0,0), (-1,-1), 14),
        ("BOTTOMPADDING",(0,0), (-1,-1), 14),
        ("LEFTPADDING",  (0,0), (0,-1),  14),
        ("RIGHTPADDING", (-1,0),(-1,-1), 14),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", (0,0), (-1,-1), [6, 6, 6, 6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10))

    # ══════════════════════════════════════════════════════════════════════
    # SUMMARY STATS CARDS
    # ══════════════════════════════════════════════════════════════════════
    total       = len(records)
    successes   = sum(1 for r in records if r.get("prediction") == "Success")
    failures    = total - successes
    avg_prob    = np.mean([float(r.get("probability", 0)) for r in records]) if records else 0
    best_prob   = max((float(r.get("probability", 0)) for r in records), default=0)
    avg_funding = np.mean([float(r.get("funding_total_usd", 0)) for r in records]) if records else 0

    def _stat_card(label, value, sub="", color=BRAND_ACCENT):
        data = [[
            Paragraph(f'<font color="{color.hexval() if hasattr(color,"hexval") else "#3b82f6"}">'
                      f'{value}</font>', ParagraphStyle("CV", fontSize=22, leading=26,
                      fontName="Helvetica-Bold", textColor=color)),
        ],[
            Paragraph(label, ParagraphStyle("CL", fontSize=9, leading=11,
                      fontName="Helvetica-Bold", textColor=BRAND_MID)),
        ],[
            Paragraph(sub, s_small),
        ]]
        t = Table(data, colWidths=[content_width / 4 - 4])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), BRAND_LIGHT),
            ("TOPPADDING",    (0,0), (-1,-1), 8),
            ("BOTTOMPADDING", (0,0), (-1,-1), 8),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 6),
            ("LINEABOVE",     (0,0), (-1,0),  2, color),
            ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ]))
        return t

    cards = [
        _stat_card("Total Predictions", str(total), "all-time runs", BRAND_ACCENT),
        _stat_card("Successful",  str(successes), f"{successes/total*100:.0f}% success rate" if total else "-", BRAND_GREEN),
        _stat_card("High-risk",   str(failures),  f"{failures/total*100:.0f}% failure rate" if total else "-", BRAND_RED),
        _stat_card("Avg. Probability", f"{avg_prob*100:.1f}%", f"Best: {best_prob*100:.1f}%", BRAND_AMBER),
    ]
    card_row = Table([cards], colWidths=[content_width / 4] * 4,
                     hAlign="LEFT", spaceAfter=4)
    card_row.setStyle(TableStyle([
        ("LEFTPADDING",  (0,0), (-1,-1), 0),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
    ]))
    story.append(card_row)
    story.append(Spacer(1, 10))

    # ══════════════════════════════════════════════════════════════════════
    # PREDICTION HISTORY TABLE
    # ══════════════════════════════════════════════════════════════════════
    story.append(Paragraph("Prediction History", s_section))
    story.append(HRFlowable(width=content_width, thickness=1,
                             color=BRAND_ACCENT, spaceAfter=6))

    col_widths = [22*mm, 34*mm, 28*mm, 20*mm, 22*mm, 36*mm, 26*mm]

    thead = [["ID", "Timestamp", "Funding (USD)", "Rounds", "Age (yrs)",
               "Probability", "Verdict"]]
    table_data = thead.copy()

    for r in records:
        prob      = float(r.get("probability", 0))
        verdict   = r.get("prediction", "—")
        verdict_color = "#22c55e" if verdict == "Success" else "#ef4444"
        table_data.append([
            Paragraph(str(r.get("id","—")), s_small),
            Paragraph(str(r.get("timestamp","—")), s_small),
            Paragraph(f"${float(r.get('funding_total_usd',0)):,.0f}", s_small),
            Paragraph(str(r.get("funding_rounds","—")), s_small),
            Paragraph(str(r.get("startup_age","—")), s_small),
            Paragraph(f"{prob*100:.1f}%", s_small),
            Paragraph(f'<font color="{verdict_color}"><b>{verdict}</b></font>', s_small),
        ])

    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0,0), (-1,0),  BRAND_MID),
        ("TEXTCOLOR",     (0,0), (-1,0),  BRAND_WHITE),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0),  8),
        ("TOPPADDING",    (0,0), (-1,0),  6),
        ("BOTTOMPADDING", (0,0), (-1,0),  6),
        # Body rows
        ("FONTSIZE",      (0,1), (-1,-1), 8),
        ("TOPPADDING",    (0,1), (-1,-1), 5),
        ("BOTTOMPADDING", (0,1), (-1,-1), 5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [BRAND_WHITE, BRAND_LIGHT]),
        # Grid
        ("GRID",          (0,0), (-1,-1), 0.4, colors.HexColor("#cbd5e1")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN",         (2,0), (5,-1),  "RIGHT"),
        ("ALIGN",         (3,0), (4,-1),  "CENTER"),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 14))

    # ══════════════════════════════════════════════════════════════════════
    # INSIGHTS CARDS  (for each prediction)
    # ══════════════════════════════════════════════════════════════════════
    if records:
        story.append(Paragraph("Detailed Insights per Prediction", s_section))
        story.append(HRFlowable(width=content_width, thickness=1,
                                 color=BRAND_ACCENT, spaceAfter=8))

        for idx, r in enumerate(records, 1):
            funding = float(r.get("funding_total_usd", 0))
            rounds  = int(r.get("funding_rounds", 0))
            age     = float(r.get("startup_age", 0))
            prob    = float(r.get("probability", 0))
            verdict = r.get("prediction", "—")
            ts      = r.get("timestamp", "—")
            rid     = r.get("id", str(idx))

            verdict_color = BRAND_GREEN if verdict == "Success" else BRAND_RED
            prob_pct = f"{prob*100:.1f}%"

            tip_list = insights(funding, rounds, age, prob)

            # Card header row
            card_header = [[
                Paragraph(f"#{idx} &nbsp; ID: {rid} &nbsp;|&nbsp; {ts}", s_card_title),
                Paragraph(
                    f'<font color="{verdict_color.hexval() if hasattr(verdict_color,"hexval") else "#22c55e"}">'
                    f'<b>{verdict}</b></font> &nbsp; <font size=10><b>{prob_pct}</b></font>',
                    ParagraphStyle("VD", fontSize=10, leading=13,
                                   fontName="Helvetica-Bold", alignment=TA_RIGHT,
                                   textColor=BRAND_MID)
                ),
            ]]
            ch = Table(card_header, colWidths=[content_width * 0.65, content_width * 0.35])
            ch.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#dbeafe")),
                ("TOPPADDING",    (0,0), (-1,-1), 7),
                ("BOTTOMPADDING", (0,0), (-1,-1), 7),
                ("LEFTPADDING",   (0,0), (0,-1),  10),
                ("RIGHTPADDING",  (-1,0),(-1,-1), 10),
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ]))

            # Metrics row
            metrics_data = [[
                Paragraph(f"<b>Funding:</b> ${funding:,.0f}", s_card_body),
                Paragraph(f"<b>Rounds:</b> {rounds}", s_card_body),
                Paragraph(f"<b>Company Age:</b> {age} yrs", s_card_body),
                Paragraph(f"<b>Risk Score:</b> {(1-prob)*100:.1f}%", s_card_body),
            ]]
            metrics_row = Table(metrics_data,
                                colWidths=[content_width / 4] * 4)
            metrics_row.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), BRAND_LIGHT),
                ("TOPPADDING",    (0,0), (-1,-1), 6),
                ("BOTTOMPADDING", (0,0), (-1,-1), 6),
                ("LEFTPADDING",   (0,0), (-1,-1), 10),
                ("RIGHTPADDING",  (0,0), (-1,-1), 6),
            ]))

            # Insights rows
            insight_rows = []
            for icon, title, desc in tip_list:
                insight_rows.append([
                    Paragraph(f"<b>{title}</b>", s_insight_title),
                    Paragraph(desc, s_insight_body),
                ])
            ins_table = Table(insight_rows,
                              colWidths=[content_width * 0.30, content_width * 0.70])
            ins_table.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,-1), BRAND_WHITE),
                ("TOPPADDING",    (0,0), (-1,-1), 5),
                ("BOTTOMPADDING", (0,0), (-1,-1), 5),
                ("LEFTPADDING",   (0,0), (0,-1),  10),
                ("LEFTPADDING",   (1,0), (1,-1),  6),
                ("RIGHTPADDING",  (-1,0),(-1,-1), 10),
                ("LINEBELOW",     (0,0), (-1,-2), 0.3, colors.HexColor("#e2e8f0")),
                ("VALIGN",        (0,0), (-1,-1), "TOP"),
            ]))

            full_card_data = [
                [ch],
                [metrics_row],
                [ins_table],
            ]
            full_card = Table(full_card_data, colWidths=[content_width])
            full_card.setStyle(TableStyle([
                ("BOX",           (0,0), (-1,-1), 0.8, colors.HexColor("#cbd5e1")),
                ("LEFTPADDING",   (0,0), (-1,-1), 0),
                ("RIGHTPADDING",  (0,0), (-1,-1), 0),
                ("TOPPADDING",    (0,0), (-1,-1), 0),
                ("BOTTOMPADDING", (0,0), (-1,-1), 0),
            ]))

            story.append(KeepTogether(full_card))
            story.append(Spacer(1, 10))

    # ══════════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════════
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width=content_width, thickness=0.5,
                             color=colors.HexColor("#cbd5e1")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Confidential — Generated by Startup Predictor AI &nbsp;|&nbsp; "
        f"User: {username} &nbsp;|&nbsp; {now_str} &nbsp;|&nbsp; "
        f"Predictions are probabilistic and for informational purposes only.",
        ParagraphStyle("Footer", fontSize=7, leading=10,
                       textColor=colors.HexColor("#94a3b8"),
                       fontName="Helvetica", alignment=TA_CENTER)
    ))

    doc.build(story)


# ── routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard") if logged_in() else url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if logged_in():
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        users = load_users()
        if u in users and users[u]["password"] == hash_pw(p):
            session["username"] = u
            return redirect(url_for("dashboard"))
        error = "Invalid credentials. Please try again."
    return render_template("login.html", error=error)

@app.route("/register", methods=["GET","POST"])
def register():
    if logged_in():
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","")
        c = request.form.get("confirm","")
        if not u or not p:
            error = "Username and password are required."
        elif p != c:
            error = "Passwords do not match."
        else:
            users = load_users()
            if u in users:
                error = "Username already taken."
            else:
                users[u] = {"password": hash_pw(p), "created": datetime.utcnow().isoformat()}
                save_users(users)
                session["username"] = u
                return redirect(url_for("dashboard"))
    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if not logged_in():
        return redirect(url_for("login"))

    prediction = probability = None
    input_vals  = {}
    insight_list = []

    if request.method == "POST":
        try:
            funding = float(request.form["funding_total_usd"])
            rounds  = int(request.form["funding_rounds"])
            age     = float(request.form["startup_age"])
            input_vals = {"funding_total_usd": funding, "funding_rounds": rounds, "startup_age": age}

            label, prob = predict_one(funding, rounds, age)
            prediction   = "Success" if label == 1 else "Failure"
            probability  = prob
            insight_list = insights(funding, rounds, age, prob)

            append_history({
                "id": str(uuid.uuid4())[:8],
                "user": session["username"],
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                "funding_total_usd": funding,
                "funding_rounds": rounds,
                "startup_age": age,
                "prediction": prediction,
                "probability": prob,
            })
        except (ValueError, KeyError) as e:
            flash(f"Input error: {e}", "error")

    df = load_history()
    user_hist = df[df["user"] == session["username"]].tail(20).to_dict("records") if not df.empty else []
    user_hist_rev = list(reversed(user_hist))

    return render_template(
        "dashboard.html",
        username=session["username"],
        prediction=prediction,
        probability=probability,
        input_vals=input_vals,
        insights=insight_list,
        history=user_hist_rev,
    )

@app.route("/api/predict", methods=["POST"])
def api_predict():
    if not logged_in():
        return jsonify({"error": "Unauthorized"}), 401
    data = request.get_json(force=True)
    try:
        funding = float(data["funding_total_usd"])
        rounds  = int(data["funding_rounds"])
        age     = float(data["startup_age"])
        label, prob = predict_one(funding, rounds, age)
        return jsonify({"prediction": "Success" if label else "Failure", "probability": prob})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/upload", methods=["POST"])
def upload_csv():
    if not logged_in():
        return redirect(url_for("login"))
    f = request.files.get("csv_file")
    if not f:
        flash("No file uploaded.", "error")
        return redirect(url_for("dashboard"))
    try:
        df = pd.read_csv(f)
        required = {"funding_total_usd", "funding_rounds", "startup_age"}
        if not required.issubset(df.columns):
            flash(f"CSV must contain: {required}", "error")
            return redirect(url_for("dashboard"))
        results = []
        for _, row in df.iterrows():
            label, prob = predict_one(
                float(row["funding_total_usd"]),
                int(row["funding_rounds"]),
                float(row["startup_age"]),
            )
            results.append({**row.to_dict(),
                            "prediction": "Success" if label else "Failure",
                            "probability": prob})
        out = pd.DataFrame(results)
        path = os.path.join(BASE_DIR, "data", "bulk_results.csv")
        out.to_csv(path, index=False)
        return send_file(path, as_attachment=True, download_name="bulk_predictions.csv")
    except Exception as e:
        flash(f"Error processing CSV: {e}", "error")
        return redirect(url_for("dashboard"))

# ── FIX 1: leaderboard now always returns valid JSON ─────────────────────────
@app.route("/leaderboard")
def leaderboard():
    try:
        df = load_history()
        if df.empty:
            return jsonify({"status": "ok", "data": []})

        board = (
            df[df["prediction"] == "Success"]
            .sort_values("probability", ascending=False)
            .head(10)
            [["id", "user", "timestamp", "funding_total_usd",
              "funding_rounds", "startup_age", "prediction", "probability"]]
            .fillna("")
        )

        # Convert to plain Python types so jsonify won't choke on numpy scalars
        records = []
        for row in board.to_dict("records"):
            records.append({
                "id":               str(row["id"]),
                "user":             str(row["user"]),
                "timestamp":        str(row["timestamp"]),
                "funding_total_usd": float(row["funding_total_usd"]),
                "funding_rounds":    int(row["funding_rounds"]),
                "startup_age":       float(row["startup_age"]),
                "prediction":        str(row["prediction"]),
                "probability":       round(float(row["probability"]), 4),
            })

        return jsonify({"status": "ok", "data": records})

    except Exception as e:
        # Instead of crashing, return a structured error the frontend can handle
        return jsonify({"status": "error", "message": str(e), "data": []}), 500


# ── FIX 2: history download now returns a beautiful PDF ──────────────────────
@app.route("/history/download")
def download_history():
    if not logged_in():
        return redirect(url_for("login"))
    try:
        df = load_history()
        user_df = df[df["user"] == session["username"]]
        records = user_df.to_dict("records")

        pdf_path = os.path.join(BASE_DIR, "data",
                                f"report_{session['username']}.pdf")
        generate_history_pdf(session["username"], records, pdf_path)

        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"startup_report_{session['username']}.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        flash(f"Could not generate PDF: {e}", "error")
        return redirect(url_for("dashboard"))


@app.route("/about")
def about():
    return render_template("about.html", logged_in=logged_in(),
                           username=session.get("username",""))

if __name__ == "__main__":
    app.run(debug=True)