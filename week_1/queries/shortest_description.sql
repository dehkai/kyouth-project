SELECT LENGTH(description), source_id, job_title
FROM jobs
ORDER BY LENGTH(description) ASC
LIMIT 1;
