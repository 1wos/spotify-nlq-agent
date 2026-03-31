-- ============================================
-- Track 3: Spotify Tracks AlloyDB Schema
-- Dataset: maharshipandya/spotify-tracks-dataset (HuggingFace)
-- Use case: "Exploring Spotify music tracks and audio features using natural language"
-- ============================================

-- Drop table if exists (for clean setup)
DROP TABLE IF EXISTS spotify_tracks;

-- Create custom table schema (requirement: at least one table created by you)
CREATE TABLE spotify_tracks (
    id              SERIAL PRIMARY KEY,
    track_id        VARCHAR(30),
    artist_name     TEXT,
    album_name      TEXT,
    track_name      TEXT,
    popularity      INTEGER CHECK (popularity >= 0 AND popularity <= 100),
    duration_ms     INTEGER,
    duration_sec    NUMERIC GENERATED ALWAYS AS (duration_ms / 1000.0) STORED,
    explicit        BOOLEAN DEFAULT FALSE,
    danceability    NUMERIC(4,3),
    energy          NUMERIC(4,3),
    "key"           INTEGER,
    loudness        NUMERIC(6,3),
    mode            INTEGER,
    speechiness     NUMERIC(4,3),
    acousticness    NUMERIC(4,3),
    instrumentalness NUMERIC(7,6),
    liveness        NUMERIC(4,3),
    valence         NUMERIC(4,3),
    tempo           NUMERIC(6,3),
    time_signature  INTEGER,
    track_genre     VARCHAR(50)
);

-- Add comments for AlloyDB AI natural language context
COMMENT ON TABLE spotify_tracks IS 'Spotify music tracks with audio features from 125 genres. Contains 114K tracks with attributes like danceability, energy, tempo (BPM), valence (positiveness), and popularity scores.';

COMMENT ON COLUMN spotify_tracks.artist_name IS 'Artist or artists who performed the track. Multiple artists separated by semicolons.';
COMMENT ON COLUMN spotify_tracks.popularity IS 'Popularity score from 0 to 100. Higher means more popular. Based on total plays and recency.';
COMMENT ON COLUMN spotify_tracks.duration_sec IS 'Track duration in seconds. Auto-calculated from duration_ms.';
COMMENT ON COLUMN spotify_tracks.danceability IS 'How suitable for dancing from 0.0 to 1.0. Higher is more danceable.';
COMMENT ON COLUMN spotify_tracks.energy IS 'Intensity and activity from 0.0 to 1.0. Death metal is high, Bach prelude is low.';
COMMENT ON COLUMN spotify_tracks.tempo IS 'Tempo in BPM (beats per minute).';
COMMENT ON COLUMN spotify_tracks.valence IS 'Musical positiveness from 0.0 to 1.0. High valence means happy and cheerful.';
COMMENT ON COLUMN spotify_tracks.speechiness IS 'Presence of spoken words from 0.0 to 1.0. Above 0.66 is mostly speech like talk shows.';
COMMENT ON COLUMN spotify_tracks.acousticness IS 'Confidence of being acoustic from 0.0 to 1.0.';
COMMENT ON COLUMN spotify_tracks.instrumentalness IS 'Likelihood of no vocals from 0.0 to 1.0.';
COMMENT ON COLUMN spotify_tracks.liveness IS 'Probability of being recorded live from 0.0 to 1.0.';
COMMENT ON COLUMN spotify_tracks.loudness IS 'Overall loudness in decibels (dB). Typically between -60 and 0.';
COMMENT ON COLUMN spotify_tracks.track_genre IS 'Genre of the track. 125 different genres available.';
COMMENT ON COLUMN spotify_tracks.explicit IS 'Whether the track has explicit lyrics. True means explicit content.';

-- Create indexes for common query patterns
CREATE INDEX idx_genre ON spotify_tracks(track_genre);
CREATE INDEX idx_popularity ON spotify_tracks(popularity DESC);
CREATE INDEX idx_tempo ON spotify_tracks(tempo);
CREATE INDEX idx_artist ON spotify_tracks(artist_name);
