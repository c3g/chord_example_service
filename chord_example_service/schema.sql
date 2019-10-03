DROP TABLE IF EXISTS data_types;
DROP TABLE IF EXISTS datasets;
DROP TABLE IF EXISTS entries;

CREATE TABLE data_types (
    id TEXT PRIMARY KEY,
    schema TEXT NOT NULL
);

CREATE TABLE datasets (
    id TEXT PRIMARY KEY,
    data_type TEXT NOT NULL,
    metadata TEXT NOT NULL,
    FOREIGN KEY (data_type) REFERENCES data_types
);

CREATE TABLE entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    dataset TEXT NOT NULL,
    FOREIGN KEY (dataset) REFERENCES datasets
)
