CREATE OR REPLACE VIEW upcoming_bookings_view AS
SELECT
    b.id                                              AS booking_id,
    c.full_name                                       AS customer_name,
    c.email                                           AS customer_email,
    m.title                                           AS movie_title,
    cin.name                                          AS cinema_name,
    cin.city                                          AS cinema_city,
    s.start_time                                      AS showtime_start,
    b.status                                          AS booking_status,
    b.total_amount,
    ROUND(
        EXTRACT(EPOCH FROM (s.start_time - NOW())) / 3600.0,
        2
    )                                                 AS hours_until_show,
    m.title || ' @ ' || cin.name || ' (' || cin.city || ')' AS booking_summary
FROM bookings b
JOIN customers c  ON c.id  = b.customer_id
JOIN showtimes s  ON s.id  = b.showtime_id
JOIN movies m     ON m.id  = s.movie_id
JOIN screens sc   ON sc.id = s.screen_id
JOIN cinemas cin  ON cin.id = sc.cinema_id
WHERE b.status = 'confirmed'
  AND s.start_time > NOW()
  AND s.status = 'scheduled';
