-- Seed reference data for cinema booking platform (3+ rows per table).

INSERT INTO cinemas (id, name, city, address) VALUES
    (1, 'Grand Plaza Cinema',   'Baku',    '28 May Street 45'),
    (2, 'Seaside Multiplex',    'Sumgait', 'Caspian Boulevard 12'),
    (3, 'Old Town Art House',   'Ganja',   'Javad Khan Avenue 8'),
    (4, 'Metroplex Central',    'Baku',    'Nizami Street 102');

SELECT setval('cinemas_id_seq', (SELECT MAX(id) FROM cinemas));

INSERT INTO screens (id, cinema_id, screen_number, capacity, screen_type) VALUES
    (1, 1, 1, 120, 'imax'),
    (2, 1, 2,  80, '3d'),
    (3, 2, 1, 150, '2d'),
    (4, 3, 1,  60, '2d'),
    (5, 4, 1, 200, 'imax');

SELECT setval('screens_id_seq', (SELECT MAX(id) FROM screens));

INSERT INTO movies (id, title, duration_minutes, release_date, mpaa_rating) VALUES
    (1, 'The Last Horizon',    142, '2025-11-01', 'PG-13'),
    (2, 'Midnight in Baku',  118, '2026-01-15', 'R'),
    (3, 'Starlight Express',  95, '2026-03-20', 'PG'),
    (4, 'Deep Current',      128, '2026-02-10', 'PG-13');

SELECT setval('movies_id_seq', (SELECT MAX(id) FROM movies));

INSERT INTO genres (id, name) VALUES
    (1, 'Action'),
    (2, 'Drama'),
    (3, 'Sci-Fi'),
    (4, 'Comedy');

SELECT setval('genres_id_seq', (SELECT MAX(id) FROM genres));

INSERT INTO movie_genres (movie_id, genre_id) VALUES
    (1, 1), (1, 3),
    (2, 2),
    (3, 4), (3, 2),
    (4, 1), (4, 3);

INSERT INTO customers (id, email, full_name, phone, membership_tier) VALUES
    (1, 'aylin.m@example.com',  'Aylin Mammadova',  '+994501112233', 'gold'),
    (2, 'rashid.h@example.com', 'Rashid Hasanov',   '+994502223344', 'silver'),
    (3, 'nigar.k@example.com',  'Nigar Karimova',   '+994503334455', 'standard'),
    (4, 'elvin.t@example.com',  'Elvin Tagiyev',    '+994504445566', 'standard');

SELECT setval('customers_id_seq', (SELECT MAX(id) FROM customers));

INSERT INTO showtimes (id, screen_id, movie_id, start_time, base_price, status) VALUES
    (1, 1, 1, '2026-07-01 18:00:00+04', 12.50, 'scheduled'),
    (2, 2, 2, '2026-07-01 20:30:00+04', 10.00, 'scheduled'),
    (3, 3, 3, '2026-07-02 15:00:00+04',  8.50, 'scheduled'),
    (4, 5, 4, '2026-07-02 21:00:00+04', 14.00, 'scheduled');

SELECT setval('showtimes_id_seq', (SELECT MAX(id) FROM showtimes));

INSERT INTO bookings (id, customer_id, showtime_id, booked_at, status, total_amount) VALUES
    (1, 1, 1, '2026-06-28 10:00:00+04', 'confirmed',  25.00),
    (2, 2, 2, '2026-06-28 11:30:00+04', 'confirmed',  20.00),
    (3, 3, 3, '2026-06-29 09:15:00+04', 'confirmed',   8.50),
    (4, 4, 4, '2026-06-29 14:00:00+04', 'checked_in', 28.00);

SELECT setval('bookings_id_seq', (SELECT MAX(id) FROM bookings));

INSERT INTO booking_seats (id, booking_id, seat_row, seat_number, price) VALUES
    (1, 1, 'D', 5, 12.50),
    (2, 1, 'D', 6, 12.50),
    (3, 2, 'F', 8, 10.00),
    (4, 2, 'F', 9, 10.00),
    (5, 3, 'B', 3,  8.50),
    (6, 4, 'A', 1, 14.00),
    (7, 4, 'A', 2, 14.00);

SELECT setval('booking_seats_id_seq', (SELECT MAX(id) FROM booking_seats));
