# 🔮 StartupOracle – Startup Success Prediction System

## 📌 Project Overview

**StartupOracle** is an AI-powered web application that predicts the success probability of startups using key business features such as funding, funding rounds, and startup age.

The system provides:

* 📊 Success / Failure prediction
* 📈 Probability score
* 💡 Business insights
* ⚠ Risk analysis

---

## 🎯 Problem Statement

Many startups fail due to weak financial planning, poor market fit, or lack of investor confidence.

There is a need for a system that:

* Predicts startup success
* Helps investors make informed decisions
* Provides actionable insights

---

## 🧠 Solution

StartupOracle uses Machine Learning to:

* Analyze startup features
* Predict success probability
* Generate business recommendations
* Deliver results through a user-friendly web interface

---

## 📊 Dataset & Features

Key features used:

* `funding_total_usd`
* `funding_rounds`
* `startup_age`
* Investment types (seed, venture, etc.)
* Market & location data

Target Variable:

* `1 → Success (IPO / Acquisition)`
* `0 → Failure`

---

## ⚙️ Data Preprocessing

* Handled missing values
* Encoded categorical features
* Created new feature → `startup_age`
* Applied **StandardScaler** for normalization

---

## ⚖️ Handling Imbalanced Data

The dataset had more failures than successes.

We applied:
👉 **SMOTE (Synthetic Minority Oversampling Technique)**

Benefits:

* Balanced dataset
* Improved recall and F1-score
* Reduced bias

---

## 🤖 Models Used

We trained and compared:

* Logistic Regression
* Decision Tree
* Random Forest
* K-Nearest Neighbors (KNN)
* XGBoost
* Support Vector Machine (SVM)

---

## 🏆 Final Model Selection

We selected **SVM (LinearSVC + CalibratedClassifierCV)** because:

* ✔ Strong classification performance
* ✔ Fast and scalable
* ✔ Handles high-dimensional data
* ✔ Provides probability outputs

---

## 📈 Evaluation Metrics

Models were evaluated using:

* Accuracy
* Precision
* Recall
* **F1 Score (primary metric)**

👉 F1 Score was prioritized due to class imbalance.

---

## 🔍 Feature Importance

Feature importance was derived from SVM coefficients.

Key findings:

* Funding has the highest influence
* More funding rounds increase success chances
* Startup age impacts stability

---

## 💡 Business Insights

StartupOracle provides insights such as:

* High funding → higher success probability
* More rounds → strong investor confidence
* Low funding → higher risk
* Early-stage startups → more uncertainty

---

## 🌐 Web Application (Flask)

The project includes a full web application with:

### Features:

* 🔐 Login & Registration
* 📥 Input-based prediction
* 📊 Probability visualization
* 📈 Interactive charts
* 🏆 Leaderboard
* 📂 CSV upload (bulk prediction)
* 💼 Business insights

---

## 🏗️ Project Structure

```text id="n6y8ap"
startup-premium-app/
│
├── app.py
├── model/
├── data/
├── templates/
├── static/
├── users.json
├── requirements.txt
```

---

## ⚙️ Installation & Setup

### 1. Clone the repository

```bash id="c2m0ac"
git clone <your-repo-link>
cd startup-premium-app
```

### 2. Install dependencies

```bash id="0h6r7b"
pip install -r requirements.txt
```

### 3. Run the app

```bash id="b6f0lo"
python app.py
```

### 4. Open in browser

https://startup-oracle-mlproject.onrender.com

---

## 🚀 Future Improvements

* 🔮 Explainability (SHAP / LIME)
* 📊 Advanced analytics dashboard
* 🤖 AI chatbot for startup advice
* ☁️ Cloud deployment (Render / AWS)
* 📱 Mobile optimization

---

## 👨‍💻 Team

Diksha
Nitika Anand
Namha Dhawan

---

## 📌 Conclusion

StartupOracle is not just a prediction model—it is a **decision support system** that helps startups and investors make data-driven decisions.

---

## ⭐ Key Highlights

✔ End-to-end ML pipeline
✔ Real-world web application
✔ Business-focused insights
✔ Scalable solution

---
