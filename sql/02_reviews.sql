CREATE TABLE reviews (
    recommendationid BIGINT PRIMARY KEY,
    appid BIGINT NOT NULL REFERENCES games(appid),

    language VARCHAR,
    review_text VARCHAR,

    voted_up BOOLEAN,

    -- Playtime is stored in minutes, as returned by the Steam API.
    -- playtime_at_review is the key column for the research questions:
    -- how much the author had played *when the review was written*.
    author_steamid VARCHAR,
    author_num_games_owned INTEGER,
    author_num_reviews INTEGER,
    author_playtime_forever INTEGER,
    author_playtime_last_two_weeks INTEGER,
    author_playtime_at_review INTEGER,
    author_last_played TIMESTAMP,

    timestamp_created TIMESTAMP,
    timestamp_updated TIMESTAMP,

    votes_up INTEGER,
    votes_funny INTEGER,
    weighted_vote_score DOUBLE,
    comment_count INTEGER,

    steam_purchase BOOLEAN,
    received_for_free BOOLEAN,
    written_during_early_access BOOLEAN,

    data_fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
