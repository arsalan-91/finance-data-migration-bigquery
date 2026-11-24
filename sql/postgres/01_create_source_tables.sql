-- Source system tables (synthetic SAP CO). Intentionally no PRIMARY KEY / NOT NULL:
-- invalid rows (e.g. missing_key) must reach the raw layer so dbt can quarantine them.

CREATE SCHEMA IF NOT EXISTS sap_source;

CREATE TABLE IF NOT EXISTS sap_source.csks (
    kokrs  varchar(4),
    kostl  varchar(10),
    ktext  varchar(40)
);

CREATE TABLE IF NOT EXISTS sap_source.cobk (
    kokrs  varchar(4),
    belnr  varchar(10),
    gjahr  smallint,
    vrgng  varchar(4),
    budat  date,
    bldat  date,
    cpudt  date,
    cputm  time,
    usnam  varchar(12),
    bltxt  varchar(50)
);

CREATE TABLE IF NOT EXISTS sap_source.coep (
    kokrs   varchar(4),
    belnr   varchar(10),
    buzei   varchar(3),
    gjahr   smallint,
    perio   varchar(3),
    objnr   varchar(22),
    kstar   varchar(10),
    wkgbtr  numeric(15, 2),
    twaer   varchar(5),
    beknz   char(1),
    sgtxt   varchar(50)
);

COMMENT ON TABLE sap_source.csks IS 'Cost center master data (SAP CSKS), synthetic';
COMMENT ON TABLE sap_source.cobk IS 'CO document headers (SAP COBK), synthetic';
COMMENT ON TABLE sap_source.coep IS 'CO document line items (SAP COEP), synthetic';
