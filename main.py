from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from jose import jwt, JWTError
from datetime import datetime, timedelta
import sqlite3
import os
import zipfile

app = FastAPI(title="India Village Geo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "mysecretkey"
ALGORITHM = "HS256"
DB_NAME = "geo_api.db"
ZIP_NAME = "geo_api.zip"


class LoginData(BaseModel):
    username: str
    password: str


def extract_database():
    if os.path.exists(ZIP_NAME):
        with zipfile.ZipFile(ZIP_NAME, "r") as zip_ref:
            zip_ref.extractall()
        print("Database extracted successfully from geo_api.db.zip")


def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    extract_database()

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT UNIQUE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            username TEXT PRIMARY KEY,
            plan TEXT,
            daily_limit INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT,
            endpoint TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO api_keys (api_key)
        VALUES ('demo123')
    """)

    cursor.execute("""
        INSERT OR IGNORE INTO subscriptions (username, plan, daily_limit)
        VALUES ('admin', 'Free', 50)
    """)

    conn.commit()
    conn.close()


@app.on_event("startup")
def startup_event():
    init_db()


init_db()


def create_token(username: str):
    expiry = datetime.utcnow() + timedelta(hours=2)
    data = {"sub": username, "exp": expiry}
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/login")
def login(data: LoginData):
    if data.username == "admin" and data.password == "admin123":
        token = create_token(data.username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "plan": "Free",
            "daily_limit": 50
        }

    raise HTTPException(status_code=401, detail="Invalid username or password")


def verify_api_key(x_api_key: str):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM api_keys WHERE api_key = ?", (x_api_key,))
    result = cursor.fetchone()

    conn.close()

    if result:
        return "admin"

    return None


def verify_jwt_token(authorization: str):
    if not authorization:
        return None

    if not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username
    except JWTError:
        return None


def check_rate_limit(username):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT plan, daily_limit
        FROM subscriptions
        WHERE username = ?
    """, (username,))

    subscription = cursor.fetchone()

    if not subscription:
        conn.close()
        raise HTTPException(status_code=403, detail="No subscription found")

    plan, daily_limit = subscription

    cursor.execute("""
        SELECT COUNT(*)
        FROM api_logs
        WHERE api_key = ?
        AND DATE(timestamp) = DATE('now')
    """, (username,))

    today_count = cursor.fetchone()[0]
    conn.close()

    if today_count >= daily_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {plan} plan. Daily limit: {daily_limit}"
        )


def verify_access(x_api_key: str = None, authorization: str = None):
    username = None

    if x_api_key:
        username = verify_api_key(x_api_key)

    if not username and authorization:
        username = verify_jwt_token(authorization)

    if not username:
        raise HTTPException(
            status_code=401,
            detail="Invalid API Key or JWT Token"
        )

    check_rate_limit(username)
    return username


def log_request(username, endpoint):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO api_logs (api_key, endpoint)
        VALUES (?, ?)
    """, (username, endpoint))

    conn.commit()
    conn.close()


@app.get("/")
def home():
    return {
        "message": "Village Geo API is working",
        "docs": "/docs"
    }


@app.get("/subscription")
def get_subscription(
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    username = verify_access(x_api_key, authorization)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT username, plan, daily_limit
        FROM subscriptions
        WHERE username = ?
    """, (username,))

    data = cursor.fetchone()
    conn.close()

    if not data:
        raise HTTPException(status_code=404, detail="Subscription not found")

    return {
        "username": data[0],
        "plan": data[1],
        "daily_limit": data[2]
    }


@app.get("/states")
def get_states(
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    username = verify_access(x_api_key, authorization)
    log_request(username, "/states")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT state_name
        FROM states
        ORDER BY state_name
    """)

    data = cursor.fetchall()
    conn.close()

    states = [row[0] for row in data]

    return {"states": states}


@app.get("/districts")
def get_districts(
    state_name: str,
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    username = verify_access(x_api_key, authorization)
    log_request(username, "/districts")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT d.district_name
        FROM districts d
        JOIN states s ON d.state_id = s.id
        WHERE s.state_name = ?
        ORDER BY d.district_name
    """, (state_name,))

    data = cursor.fetchall()
    conn.close()

    districts = [row[0] for row in data]

    return {"districts": districts}


@app.get("/subdistricts")
def get_subdistricts(
    district_name: str,
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    username = verify_access(x_api_key, authorization)
    log_request(username, "/subdistricts")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT sd.sub_district_name
        FROM sub_districts sd
        JOIN districts d ON sd.district_id = d.id
        WHERE d.district_name = ?
        ORDER BY sd.sub_district_name
    """, (district_name,))

    data = cursor.fetchall()
    conn.close()

    subdistricts = [row[0] for row in data]

    return {"subdistricts": subdistricts}


@app.get("/villages")
def get_villages(
    subdistrict_name: str,
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    username = verify_access(x_api_key, authorization)
    log_request(username, "/villages")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT v.village_name
        FROM villages v
        JOIN sub_districts sd ON v.sub_district_id = sd.id
        WHERE sd.sub_district_name = ?
        ORDER BY v.village_name
        LIMIT 100
    """, (subdistrict_name,))

    data = cursor.fetchall()
    conn.close()

    villages = [row[0] for row in data]

    return {
        "count": len(villages),
        "villages": villages
    }


@app.get("/search")
def search_location(
    query: str,
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    username = verify_access(x_api_key, authorization)
    log_request(username, "/search")

    conn = get_db()
    cursor = conn.cursor()

    search_value = f"%{query}%"

    cursor.execute("""
        SELECT DISTINCT
            v.village_name,
            sd.sub_district_name,
            d.district_name,
            s.state_name
        FROM villages v
        JOIN sub_districts sd ON v.sub_district_id = sd.id
        JOIN districts d ON sd.district_id = d.id
        JOIN states s ON d.state_id = s.id
        WHERE 
            v.village_name LIKE ?
            OR sd.sub_district_name LIKE ?
            OR d.district_name LIKE ?
            OR s.state_name LIKE ?
        ORDER BY
            CASE
                WHEN v.village_name = ? THEN 1
                WHEN sd.sub_district_name = ? THEN 2
                WHEN d.district_name = ? THEN 3
                WHEN s.state_name = ? THEN 4
                ELSE 5
            END,
            v.village_name
        LIMIT 20
    """, (
        search_value,
        search_value,
        search_value,
        search_value,
        query,
        query,
        query,
        query
    ))

    data = cursor.fetchall()
    conn.close()

    results = []

    for row in data:
        results.append({
            "village": row[0],
            "subdistrict": row[1],
            "district": row[2],
            "state": row[3]
        })

    return {
        "query": query,
        "count": len(results),
        "results": results
    }


@app.get("/analytics")
def get_analytics(
    x_api_key: str = Header(None),
    authorization: str = Header(None)
):
    username = verify_access(x_api_key, authorization)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT endpoint, COUNT(*) as count
        FROM api_logs
        GROUP BY endpoint
        ORDER BY count DESC
    """)

    data = cursor.fetchall()
    conn.close()

    analytics = []

    for row in data:
        analytics.append({
            "endpoint": row[0],
            "usage_count": row[1]
        })

    return {"analytics": analytics}
