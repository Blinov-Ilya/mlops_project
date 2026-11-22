CREATE TABLE IF NOT EXISTS ticket_results (
    ticket_id uuid PRIMARY KEY,
    text text NOT NULL,
    category text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS daily_category_counts (
    day date NOT NULL,
    category text NOT NULL,
    ticket_count bigint NOT NULL,
    PRIMARY KEY (day, category)
);

CREATE ROLE grafana_reader LOGIN PASSWORD 'grafana';
GRANT SELECT ON daily_category_counts TO grafana_reader;
