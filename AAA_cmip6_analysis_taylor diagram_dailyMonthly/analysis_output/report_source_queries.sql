-- DuckDB source projections for the portable review report.
-- The artifact JSON is the reviewed, bounded snapshot.  These views expose
-- each structured dataset without changing values or row order.

CREATE OR REPLACE VIEW audit_summary AS
SELECT row_value.*
FROM read_json_auto('q3_review_artifact.json', format = 'unstructured') AS artifact,
UNNEST(artifact.snapshot.datasets.audit_summary) AS rows(row_value);

CREATE OR REPLACE VIEW priority_counts AS
SELECT row_value.*
FROM read_json_auto('q3_review_artifact.json', format = 'unstructured') AS artifact,
UNNEST(artifact.snapshot.datasets.priority_counts) AS rows(row_value);

CREATE OR REPLACE VIEW findings AS
SELECT row_value.*
FROM read_json_auto('q3_review_artifact.json', format = 'unstructured') AS artifact,
UNNEST(artifact.snapshot.datasets.findings) AS rows(row_value);

CREATE OR REPLACE VIEW study_comparison AS
SELECT row_value.*
FROM read_json_auto('q3_review_artifact.json', format = 'unstructured') AS artifact,
UNNEST(artifact.snapshot.datasets.study_comparison) AS rows(row_value);

CREATE OR REPLACE VIEW research_design AS
SELECT row_value.*
FROM read_json_auto('q3_review_artifact.json', format = 'unstructured') AS artifact,
UNNEST(artifact.snapshot.datasets.research_design) AS rows(row_value);

CREATE OR REPLACE VIEW implementation_plan AS
SELECT row_value.*
FROM read_json_auto('q3_review_artifact.json', format = 'unstructured') AS artifact,
UNNEST(artifact.snapshot.datasets.implementation_plan) AS rows(row_value);

CREATE OR REPLACE VIEW page_budget AS
SELECT row_value.*
FROM read_json_auto('q3_review_artifact.json', format = 'unstructured') AS artifact,
UNNEST(artifact.snapshot.datasets.page_budget) AS rows(row_value);

SELECT severity, count
FROM priority_counts
ORDER BY CASE severity WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 ELSE 3 END;
