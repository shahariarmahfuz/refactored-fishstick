DROP TABLE IF EXISTS wallet_transactions, redeem_codes, orders, product, category, game, users, admin, banners, notices, popup_messages, payment_methods CASCADE;

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    balance REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE wallet_transactions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    amount REAL NOT NULL,
    payment_method TEXT NOT NULL,
    transaction_id TEXT,
    screenshot_url TEXT,
    status TEXT NOT NULL DEFAULT 'Pending',
    request_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE redeem_codes (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    value REAL NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    is_used INTEGER NOT NULL DEFAULT 0,
    used_by_id INTEGER REFERENCES users(id),
    used_at TIMESTAMP
);

CREATE TABLE game (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL UNIQUE
);

CREATE TABLE category (
    id SERIAL PRIMARY KEY,
    game_id INTEGER NOT NULL REFERENCES game(id),
    name TEXT NOT NULL,
    image_url TEXT NOT NULL,
    rules_text TEXT
);

CREATE TABLE product (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES category(id),
    name TEXT NOT NULL,
    price REAL NOT NULL,
    is_limited INTEGER NOT NULL DEFAULT 0,
    stock INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    restriction_days INTEGER DEFAULT 0
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES product(id),
    account_user_id INTEGER NOT NULL REFERENCES users(id),
    game_uid TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Pending',
    payment_method TEXT,
    transaction_id TEXT,
    screenshot_url TEXT,
    order_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completion_time TIMESTAMP
);

CREATE TABLE admin (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE banners (
    id SERIAL PRIMARY KEY,
    image_url TEXT NOT NULL,
    target_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE notices (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE popup_messages (
    id SERIAL PRIMARY KEY,
    title TEXT,
    content TEXT NOT NULL,
    image_url TEXT,
    button_text TEXT,
    button_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE payment_methods (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    account_number TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1
);