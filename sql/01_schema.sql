CREATE TABLE games (
    appid BIGINT PRIMARY KEY,
    name VARCHAR NOT NULL,
    type VARCHAR,

    release_date DATE,

    is_free BOOLEAN,
    required_age INTEGER,

    developers VARCHAR[],
    publishers VARCHAR[],

    genres VARCHAR[],
    categories VARCHAR[],
    tags VARCHAR[],

    price_initial INTEGER,
    price_final INTEGER,
    price_discount_percent INTEGER,
    currency VARCHAR,

    metacritic_score INTEGER,
    metacritic_url VARCHAR,

    recommendations_total INTEGER,

    header_image_url VARCHAR,
    website_url VARCHAR,

    data_fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);