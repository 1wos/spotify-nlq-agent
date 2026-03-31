-- ============================================
-- Load CSV data into AlloyDB
-- Run this AFTER uploading dataset.csv to your Cloud Shell or AlloyDB instance
-- ============================================

-- Option 1: Load from local CSV file (run from psql connected to AlloyDB)
\COPY spotify_tracks(track_id, artist_name, album_name, track_name, popularity, duration_ms, explicit, danceability, energy, "key", loudness, mode, speechiness, acousticness, instrumentalness, liveness, valence, tempo, time_signature, track_genre)
FROM 'clean_dataset.csv'
WITH (FORMAT csv, HEADER true, NULL '');

-- Option 2: If using Cloud SQL/AlloyDB Studio, you can import CSV directly
-- through the Google Cloud Console UI.

-- Verify data loaded successfully
SELECT COUNT(*) AS total_tracks FROM spotify_tracks;
SELECT COUNT(DISTINCT track_genre) AS total_genres FROM spotify_tracks;
SELECT COUNT(DISTINCT artist_name) AS total_artists FROM spotify_tracks;

-- Quick data preview
SELECT track_name, artist_name, track_genre, popularity, tempo, danceability, energy, valence
FROM spotify_tracks
ORDER BY popularity DESC
LIMIT 10;
