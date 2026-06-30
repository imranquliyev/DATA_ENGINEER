-- =============================================================================
-- Domain: Cinema Booking Platform
--
-- Entities:
--   cinemas        — physical venue locations
--   screens        — auditoriums within a cinema
--   movies         — film catalog
--   genres         — normalized genre lookup (avoids transitive dependency)
--   movie_genres   — many-to-many link between movies and genres
--   showtimes      — a scheduled screening (screen + movie + time)
--   customers      — registered patrons
--   bookings       — ticket reservations for a showtime
--
-- Key relationships:
--   cinemas 1──N screens 1──N showtimes N──1 movies
--   movies  N──M genres  (via movie_genres)
--   customers 1──N bookings N──1 showtimes
-- =============================================================================

CREATE TABLE cinemas (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    city        VARCHAR(100) NOT NULL,
    address     TEXT         NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE screens (
    id            SERIAL PRIMARY KEY,
    cinema_id     INTEGER      NOT NULL REFERENCES cinemas (id),
    screen_number SMALLINT     NOT NULL,
    capacity      SMALLINT     NOT NULL CHECK (capacity > 0),
    screen_type   VARCHAR(20)  NOT NULL DEFAULT '2d'
                      CHECK (screen_type IN ('2d', '3d', 'imax')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (cinema_id, screen_number)
);

CREATE INDEX idx_screens_cinema_id ON screens (cinema_id);

CREATE TABLE movies (
    id               SERIAL PRIMARY KEY,
    title            VARCHAR(300) NOT NULL,
    duration_minutes SMALLINT     NOT NULL CHECK (duration_minutes > 0),
    release_date     DATE         NOT NULL,
    mpaa_rating      VARCHAR(10)  NOT NULL
                         CHECK (mpaa_rating IN ('G', 'PG', 'PG-13', 'R', 'NC-17')),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE genres (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE movie_genres (
    movie_id INTEGER NOT NULL REFERENCES movies (id),
    genre_id INTEGER NOT NULL REFERENCES genres (id),
    PRIMARY KEY (movie_id, genre_id)
);

CREATE INDEX idx_movie_genres_genre_id ON movie_genres (genre_id);

CREATE TABLE customers (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    full_name       VARCHAR(200) NOT NULL,
    phone           VARCHAR(20),
    membership_tier VARCHAR(20)  NOT NULL DEFAULT 'standard'
                        CHECK (membership_tier IN ('standard', 'silver', 'gold')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE showtimes (
    id         SERIAL PRIMARY KEY,
    screen_id  INTEGER      NOT NULL REFERENCES screens (id),
    movie_id   INTEGER      NOT NULL REFERENCES movies (id),
    start_time TIMESTAMPTZ  NOT NULL,
    base_price NUMERIC(8, 2) NOT NULL CHECK (base_price >= 0),
    status     VARCHAR(20)  NOT NULL DEFAULT 'scheduled'
                   CHECK (status IN ('scheduled', 'cancelled', 'completed')),
    created_at TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_showtimes_screen_id ON showtimes (screen_id);
CREATE INDEX idx_showtimes_movie_id ON showtimes (movie_id);

CREATE TABLE bookings (
    id           SERIAL PRIMARY KEY,
    customer_id  INTEGER       NOT NULL REFERENCES customers (id),
    showtime_id  INTEGER       NOT NULL REFERENCES showtimes (id),
    booked_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    status       VARCHAR(20)   NOT NULL DEFAULT 'confirmed'
                     CHECK (status IN ('confirmed', 'cancelled', 'checked_in')),
    total_amount NUMERIC(8, 2) NOT NULL CHECK (total_amount >= 0)
);

CREATE INDEX idx_bookings_customer_id ON bookings (customer_id);
CREATE INDEX idx_bookings_showtime_id ON bookings (showtime_id);
