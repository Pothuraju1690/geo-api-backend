# 🌍 India Village Geo API

A full-stack geo data platform that provides hierarchical location data of India including **States, Districts, Sub-Districts, and Villages** with authentication, rate limiting, and analytics.

---

## 🚀 Features

- 🔐 JWT-based Authentication
- 📊 API Usage Analytics (with charts)
- ⚡ Rate Limiting (Subscription-based)
- 🌐 State → District → Subdistrict → Village hierarchy
- 🔍 Smart Search with pagination
- 🗺️ Google Maps integration
- 🎯 Clean and professional dashboard UI

---

## 🛠️ Tech Stack

- **Backend**: FastAPI (Python)
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **Authentication**: JWT (python-jose)
- **Charts**: Chart.js

---

## 📦 API Endpoints

### 🔐 Authentication
- `POST /login` → Get JWT token

### 📍 Geo Data
- `GET /states`
- `GET /districts?state_name=`
- `GET /subdistricts?district_name=`
- `GET /villages?subdistrict_name=`

### 🔍 Search
- `GET /search?query=`

### 📊 Analytics
- `GET /analytics`

### 💳 Subscription
- `GET /subscription`

---

## ▶️ Run Locally

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
