-- Full reload of the source tables from data/*.csv (mounted at /import).
-- Run with psql inside the container; \copy reads files on the psql client side.

\set ON_ERROR_STOP on

BEGIN;

TRUNCATE sap_source.csks, sap_source.cobk, sap_source.coep;

\copy sap_source.csks (kokrs, kostl, ktext) FROM '/import/csks.csv' WITH (FORMAT csv, HEADER true)
\copy sap_source.cobk (kokrs, belnr, gjahr, vrgng, budat, bldat, cpudt, cputm, usnam, bltxt) FROM '/import/cobk.csv' WITH (FORMAT csv, HEADER true)
\copy sap_source.coep (kokrs, belnr, buzei, gjahr, perio, objnr, kstar, wkgbtr, twaer, beknz, sgtxt) FROM '/import/coep.csv' WITH (FORMAT csv, HEADER true)

COMMIT;

SELECT 'csks' AS table_name, count(*) AS row_count FROM sap_source.csks
UNION ALL
SELECT 'cobk', count(*) FROM sap_source.cobk
UNION ALL
SELECT 'coep', count(*) FROM sap_source.coep
UNION ALL
SELECT 'coep_null_buzei', count(*) FROM sap_source.coep WHERE buzei IS NULL;
