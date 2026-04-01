"""Spotify NLQ Agent — FastAPI backend for AlloyDB AI natural language queries."""

from __future__ import annotations

import base64
import json
import logging
import os

import google.generativeai as genai
import pg8000
from fastapi import FastAPI, File, HTTPException, Request, UploadFile

from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────
DB_HOST = os.environ.get("DB_HOST", "")
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASS = os.environ.get("DB_PASS", "")
DB_NAME = os.environ.get("DB_NAME", "postgres")
DB_PORT = int(os.environ.get("DB_PORT", "5432"))
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI(title="Spotify NLQ Agent")
templates = Jinja2Templates(directory="templates")


# ── DB Connection ───────────────────────────────────────────────
def get_conn():
    return pg8000.connect(
        host=DB_HOST, port=DB_PORT,
        user=DB_USER, password=DB_PASS,
        database=DB_NAME,
    )


FORBIDDEN_SQL = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "MERGE", "CALL"}


def validate_sql(sql: str) -> str:
    """Only allow SELECT queries. Reject anything that could modify data."""
    normalized = sql.strip().rstrip(";").strip()
    first_word = normalized.split()[0].upper() if normalized else ""
    if first_word != "SELECT":
        raise ValueError("SELECT 쿼리만 허용됩니다.")
    for word in FORBIDDEN_SQL:
        if f" {word} " in f" {normalized.upper()} " or normalized.upper().startswith(word):
            raise ValueError(f"허용되지 않는 SQL 명령어입니다: {word}")
    return normalized


def run_query(sql: str) -> list[dict]:
    sql = validate_sql(sql)
    try:
        conn = get_conn()
    except Exception:
        raise ConnectionError("데이터베이스에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.")
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(columns, row)) for row in rows]
    finally:
        conn.close()


# ── NL → SQL via Gemini ────────────────────────────────────────
SCHEMA_CONTEXT = """
Table: spotify_tracks
Columns:
- id (SERIAL PRIMARY KEY)
- track_id (VARCHAR) — Spotify track ID
- artist_name (TEXT) — artist(s), multiple separated by ;
- album_name (TEXT)
- track_name (TEXT)
- popularity (INTEGER 0-100) — higher = more popular
- duration_ms (INTEGER) — track length in milliseconds
- duration_sec (NUMERIC) — auto-calculated seconds
- explicit (BOOLEAN) — has explicit lyrics
- danceability (NUMERIC 0-1) — dance suitability
- energy (NUMERIC 0-1) — intensity, 1=death metal, 0=Bach
- "key" (INTEGER 0-11) — pitch class
- loudness (NUMERIC) — decibels, typically -60 to 0
- mode (INTEGER) — 1=major, 0=minor
- speechiness (NUMERIC 0-1) — spoken words, >0.66=speech
- acousticness (NUMERIC 0-1) — acoustic confidence
- instrumentalness (NUMERIC 0-1) — no vocals likelihood
- liveness (NUMERIC 0-1) — live recording probability
- valence (NUMERIC 0-1) — positiveness, 1=happy, 0=sad
- tempo (NUMERIC) — BPM
- time_signature (INTEGER 3-7)
- track_genre (VARCHAR) — 125 genres

Total: ~114,000 rows
"""

NL_TO_SQL_PROMPT = """You are a PostgreSQL expert. Convert the natural language query to a SQL SELECT statement.

{schema}

Rules:
- Output ONLY the SQL query, no explanation, no markdown
- Always use double quotes for the "key" column (reserved word)
- LIMIT results to 20 unless specified
- Use ILIKE for text searches
- Return useful columns (track_name, artist_name, etc.)

Natural language query: {query}
"""


def nl_to_sql(query: str) -> str:
    response = model.generate_content(
        NL_TO_SQL_PROMPT.format(schema=SCHEMA_CONTEXT, query=query)
    )
    sql = response.text.strip()
    # Clean markdown fences if present
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[1] if "\n" in sql else sql[3:]
    if sql.endswith("```"):
        sql = sql[:-3]
    sql = sql.strip()
    if sql.lower().startswith("sql"):
        sql = sql[3:].strip()
    return sql


# ── NL → SQL via AlloyDB AI built-in ─────────────────────────
ALLOYDB_NL_PROMPT = (
    "Convert this natural language query about the spotify_tracks table to a PostgreSQL SELECT statement. "
    "The table has columns: track_name, artist_name, album_name, track_genre, popularity (0-100), "
    "danceability (0-1), energy (0-1), valence (0-1), tempo (BPM), acousticness (0-1), "
    'speechiness (0-1), instrumentalness (0-1), liveness (0-1), "key" (0-11), loudness (dB), '
    "duration_ms, explicit (boolean). Output ONLY the SQL, no explanation. Query: "
)


def alloydb_nl_to_sql(query: str) -> str:
    """Use AlloyDB AI's built-in google_ml.predict_row() to convert NL to SQL."""
    try:
        conn = get_conn()
    except Exception:
        raise ConnectionError("AlloyDB 연결 실패")
    try:
        cursor = conn.cursor()
        prompt = ALLOYDB_NL_PROMPT + query
        cursor.execute(
            "SELECT google_ml.predict_row('projects/track3-491911/locations/us-central1/publishers/google/models/gemini-2.0-flash', json_build_object('contents', json_build_array(json_build_object('role', 'user', 'parts', json_build_array(json_build_object('text', %s::text))))))::jsonb",
            (prompt,),
        )
        row = cursor.fetchone()
        if not row or not row[0]:
            raise ValueError("AlloyDB AI returned empty result")
        result = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        sql = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        sql = sql.strip()
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[1] if "\n" in sql else sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
        return sql
    finally:
        conn.close()


# ── Image → Mood → SQL ────────────────────────────────────────
IMAGE_MOOD_PROMPT = """Analyze this image and describe its mood/atmosphere for music recommendation.

Return a JSON object with:
{{
  "description": "한국어로 이미지 분위기 설명 (1-2문장)",
  "tags": ["분위기 태그 3-5개, 한국어"],
  "audio_params": {{
    "energy_min": 0.0-1.0,
    "energy_max": 0.0-1.0,
    "valence_min": 0.0-1.0,
    "valence_max": 0.0-1.0,
    "acousticness_min": 0.0-1.0,
    "tempo_min": number,
    "tempo_max": number,
    "genres": ["suggested genre names from: acoustic, pop, rock, jazz, classical, electronic, hip-hop, r-n-b, indie, ambient, blues, soul, latin, country, folk"]
  }}
}}

Map the visual mood to Spotify audio features:
- Calm/peaceful scene → low energy, high acousticness, moderate valence
- Energetic/bright scene → high energy, high valence, higher tempo
- Dark/moody scene → low valence, lower energy
- Nature/outdoor → high acousticness, moderate energy
- Party/urban → high energy, high danceability, electronic/pop

Return ONLY the JSON, no markdown."""


def analyze_image_mood(image_bytes: bytes) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    response = model.generate_content([
        IMAGE_MOOD_PROMPT,
        {"mime_type": "image/jpeg", "data": b64},  # Gemini handles common formats
    ])
    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    if text.lower().startswith("json"):
        text = text[4:].strip()
    return json.loads(text)


def _safe_float(val, min_v=0.0, max_v=999.0) -> float | None:
    try:
        f = float(val)
        return f if min_v <= f <= max_v else None
    except (TypeError, ValueError):
        return None


def mood_to_sql(mood: dict) -> str:
    params = mood.get("audio_params", {})
    conditions = []

    for col, key in [("energy", "energy_min"), ("energy", "energy_max"),
                     ("valence", "valence_min"), ("valence", "valence_max"),
                     ("acousticness", "acousticness_min"),
                     ("tempo", "tempo_min"), ("tempo", "tempo_max")]:
        val = _safe_float(params.get(key), 0.0, 300.0 if "tempo" in key else 1.0)
        if val is not None:
            op = ">=" if "min" in key else "<="
            conditions.append(f"{col} {op} {val}")

    genres = params.get("genres", [])
    if genres:
        safe_genres = [g.replace("'", "") for g in genres if isinstance(g, str) and len(g) < 30]
        if safe_genres:
            genre_list = ", ".join(f"'{g}'" for g in safe_genres)
            conditions.append(f"track_genre IN ({genre_list})")

    where = " AND ".join(conditions) if conditions else "1=1"

    return f"""SELECT track_name, artist_name, track_genre, popularity,
       energy, valence, acousticness, tempo, danceability
FROM spotify_tracks
WHERE {where}
  AND popularity > 30
ORDER BY popularity DESC
LIMIT 15"""


# ── Routes ──────────────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/query")
async def query_nl(request: Request):
    body = await request.json()
    q = body.get("query", "").strip()
    if not q:
        raise HTTPException(400, "query is required")

    source = "alloydb_ai"

    # Try AlloyDB AI built-in NL first
    try:
        sql = alloydb_nl_to_sql(q)
    except Exception as exc:
        logger.warning("AlloyDB AI NL failed, falling back to Gemini: %s", exc)
        source = "gemini"
        try:
            sql = nl_to_sql(q)
        except Exception:
            raise HTTPException(500, "자연어를 SQL로 변환하는 데 실패했습니다. 다른 표현으로 다시 시도해주세요.")

    try:
        results = run_query(sql)
    except ConnectionError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        raise HTTPException(500, "쿼리 실행 중 오류가 발생했습니다. 질문을 조금 바꿔서 다시 시도해주세요.")

    return {"sql": sql, "results": results, "source": source}


@app.post("/query/image")
async def query_image(image: UploadFile = File(...)):
    try:
        image_bytes = await image.read()
    except Exception:
        raise HTTPException(400, "이미지를 읽을 수 없습니다. 다른 파일로 시도해주세요.")

    try:
        mood = analyze_image_mood(image_bytes)
    except Exception:
        raise HTTPException(500, "이미지 분위기 분석에 실패했습니다. 다른 이미지로 시도해주세요.")

    try:
        sql = mood_to_sql(mood)
        results = run_query(sql)
    except ConnectionError as e:
        raise HTTPException(503, str(e))
    except Exception:
        raise HTTPException(500, "음악 검색 중 오류가 발생했습니다. 다시 시도해주세요.")

    return {
        "mood": {
            "description": mood.get("description", ""),
            "tags": mood.get("tags", []),
        },
        "sql": sql,
        "results": results,
    }


@app.get("/stats")
async def stats():
    try:
        rows = run_query("""
            SELECT
                COUNT(DISTINCT artist_name) AS artists,
                ROUND(AVG(tempo)::numeric, 1) AS avg_bpm
            FROM spotify_tracks
        """)
        if rows:
            return {"artists": rows[0]["artists"], "avg_bpm": float(rows[0]["avg_bpm"])}
        return {"artists": 0, "avg_bpm": 0}
    except Exception:
        return {"artists": 0, "avg_bpm": 0}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
