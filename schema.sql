-- ==========================================
-- Casino Analytics Database Schema
-- ==========================================

-- 1. PLAYERS — базовая таблица, на неё ссылаются все остальные
CREATE TABLE players (
    player_id INTEGER PRIMARY KEY,
    registration_date DATE NOT NULL,
    country VARCHAR(50) NOT NULL,
    age_group VARCHAR(10) NOT NULL,
    player_type VARCHAR(10) NOT NULL
);

-- 2. ACTIVITY — дни, когда игрок заходил
CREATE TABLE activity (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    activity_date DATE NOT NULL
);

-- 3. SESSIONS — сессии с временем входа/выхода
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    session_start TIMESTAMP NOT NULL,
    session_end TIMESTAMP NOT NULL
);

-- 4. DEPOSITS — пополнения баланса
CREATE TABLE deposits (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    deposit_date DATE NOT NULL,
    amount NUMERIC(12, 2) NOT NULL
);

-- 5. BETS — ставки и выигрыши
CREATE TABLE bets (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    timestamp TIMESTAMP NOT NULL,
    game VARCHAR(50) NOT NULL,
    bet_amount NUMERIC(12, 2) NOT NULL,
    win_amount NUMERIC(12, 2) NOT NULL,
    balance_after NUMERIC(12, 2) NOT NULL
);

-- 6. WITHDRAWALS — выводы средств
CREATE TABLE withdrawals (
    id SERIAL PRIMARY KEY,
    player_id INTEGER NOT NULL REFERENCES players(player_id),
    timestamp TIMESTAMP NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    balance_after NUMERIC(12, 2) NOT NULL
);

-- Индексы на player_id для ускорения JOIN и агрегаций
CREATE INDEX idx_activity_player_id ON activity(player_id);
CREATE INDEX idx_sessions_player_id ON sessions(player_id);
CREATE INDEX idx_deposits_player_id ON deposits(player_id);
CREATE INDEX idx_bets_player_id ON bets(player_id);
CREATE INDEX idx_withdrawals_player_id ON withdrawals(player_id);