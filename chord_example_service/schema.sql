DROP TABLE IF EXISTS entries;

CREATE TABLE entries(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    dataset TEXT NOT NULL
);

-- DUMMY VALUES

INSERT INTO entries (content, dataset) VALUES ('test 1', '56e4d7fb-42f1-4378-aeb2-aa33c731f56d');
INSERT INTO entries (content, dataset) VALUES ('test 2', '56e4d7fb-42f1-4378-aeb2-aa33c731f56d');
INSERT INTO entries (content, dataset) VALUES ('test 3', '56e4d7fb-42f1-4378-aeb2-aa33c731f56d');
INSERT INTO entries (content, dataset) VALUES ('test 4', '56e4d7fb-42f1-4378-aeb2-aa33c731f56d');
INSERT INTO entries (content, dataset) VALUES ('test 5', '56e4d7fb-42f1-4378-aeb2-aa33c731f56d');
