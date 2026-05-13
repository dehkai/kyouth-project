SELECT LENGTH(description), source_id, job_title
FROM jobs
ORDER BY LENGTH(description) DESC
LIMIT 1;
