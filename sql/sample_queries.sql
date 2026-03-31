-- ============================================
-- Sample Natural Language Queries & Expected SQL
-- These are YOUR OWN queries (requirement: not copied from lab)
-- ============================================

-- ─── Query 1 ──────────────────────────────────────────
-- Natural Language: "Show me the top 10 most popular dance songs with high energy"
-- Expected SQL:
SELECT track_name, artist_name, popularity, energy, danceability, tempo
FROM spotify_tracks
WHERE track_genre = 'dance'
  AND energy > 0.8
ORDER BY popularity DESC
LIMIT 10;


-- ─── Query 2 ──────────────────────────────────────────
-- Natural Language: "Find acoustic songs with BPM between 80 and 120 that feel happy"
-- Expected SQL:
SELECT track_name, artist_name, tempo, valence, acousticness
FROM spotify_tracks
WHERE track_genre = 'acoustic'
  AND tempo BETWEEN 80 AND 120
  AND valence > 0.7
ORDER BY valence DESC
LIMIT 10;


-- ─── Query 3 ──────────────────────────────────────────
-- Natural Language: "Which genres have the highest average danceability?"
-- Expected SQL:
SELECT track_genre, 
       ROUND(AVG(danceability)::numeric, 3) AS avg_danceability,
       COUNT(*) AS track_count
FROM spotify_tracks
GROUP BY track_genre
ORDER BY avg_danceability DESC
LIMIT 10;


-- ─── Query 4 ──────────────────────────────────────────
-- Natural Language: "Find me energetic songs longer than 5 minutes"
-- Expected SQL:
SELECT track_name, artist_name, track_genre,
       ROUND(duration_ms / 60000.0, 1) AS duration_min,
       energy, tempo
FROM spotify_tracks
WHERE duration_ms > 300000
  AND energy > 0.8
ORDER BY energy DESC
LIMIT 10;


-- ─── Query 5 ──────────────────────────────────────────
-- Natural Language: "What are the most popular explicit rap songs?"
-- Expected SQL:
SELECT track_name, artist_name, popularity, speechiness, energy
FROM spotify_tracks
WHERE track_genre = 'hip-hop'
  AND explicit = TRUE
ORDER BY popularity DESC
LIMIT 10;


-- ─── Query 6 ──────────────────────────────────────────
-- Natural Language: "Compare average tempo and energy across pop, rock, and jazz genres"
-- Expected SQL:
SELECT track_genre,
       ROUND(AVG(tempo)::numeric, 1) AS avg_bpm,
       ROUND(AVG(energy)::numeric, 3) AS avg_energy,
       ROUND(AVG(danceability)::numeric, 3) AS avg_danceability,
       COUNT(*) AS tracks
FROM spotify_tracks
WHERE track_genre IN ('pop', 'rock', 'jazz')
GROUP BY track_genre
ORDER BY track_genre;


-- ─── Query 7 ──────────────────────────────────────────
-- Natural Language: "Show me calm, instrumental tracks good for studying"
-- Expected SQL:
SELECT track_name, artist_name, track_genre,
       instrumentalness, acousticness, energy, valence
FROM spotify_tracks
WHERE instrumentalness > 0.8
  AND energy < 0.3
  AND acousticness > 0.5
ORDER BY instrumentalness DESC
LIMIT 10;
