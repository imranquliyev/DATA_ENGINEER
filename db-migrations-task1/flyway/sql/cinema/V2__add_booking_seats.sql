-- V2: Per-seat reservation detail — allows one booking to cover multiple seats
-- with individual pricing (e.g. premium rows cost more).

CREATE TABLE booking_seats (
    id          SERIAL PRIMARY KEY,
    booking_id  INTEGER       NOT NULL REFERENCES bookings (id),
    seat_row    CHAR(1)       NOT NULL CHECK (seat_row ~ '^[A-Z]$'),
    seat_number SMALLINT      NOT NULL CHECK (seat_number > 0),
    price       NUMERIC(8, 2) NOT NULL CHECK (price >= 0),
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (booking_id, seat_row, seat_number)
);

CREATE INDEX idx_booking_seats_booking_id ON booking_seats (booking_id);
