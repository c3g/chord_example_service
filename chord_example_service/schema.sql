DROP TABLE IF EXISTS entries;

CREATE TABLE entries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    dataset TEXT NOT NULL
);

-- DUMMY VALUES

INSERT INTO entries (content, dataset) VALUES ('test 1', 'entries');
INSERT INTO entries (content, dataset) VALUES ('test 2', 'entries');
INSERT INTO entries (content, dataset) VALUES ('test 3', 'entries');
INSERT INTO entries (content, dataset) VALUES ('test 4', 'entries');
INSERT INTO entries (content, dataset) VALUES ('test 5', 'entries');
