-- =====================================================
-- Bronze Layer Setup for Sustainability Demo
-- This simulates data ingested by Fivetran from various sources
-- =====================================================

-- Create bronze schema
CREATE SCHEMA IF NOT EXISTS marion_test.bronze;

-- =====================================================
-- 1. SAP Procurement Orders (ERP Source)
-- =====================================================
DROP TABLE IF EXISTS marion_test.bronze.sap_procurement_orders;

CREATE TABLE marion_test.bronze.sap_procurement_orders (
  order_id STRING,
  supplier_id STRING,
  material_type STRING,
  volume_kg DECIMAL(10,2),
  order_date DATE
) USING DELTA;

-- Generate 1000+ rows of procurement data
INSERT INTO marion_test.bronze.sap_procurement_orders
WITH suppliers AS (
  SELECT 'SUP-' || LPAD(CAST(id AS STRING), 2, '0') as supplier_id
  FROM (SELECT explode(sequence(1, 25)) as id)
),
materials AS (
  SELECT material FROM VALUES
    ('LEATHER'), ('COTTON'), ('SILK'), ('WOOL'), ('CASHMERE'),
    ('LINEN'), ('POLYESTER'), ('NYLON'), ('SPANDEX'), ('VISCOSE')
  AS t(material)
),
dates AS (
  SELECT date_add('2023-01-01', cast(rand() * 730 as int)) as order_date
  FROM (SELECT explode(sequence(1, 50)) as id)
)
SELECT
  'PO-' || LPAD(CAST(row_number() OVER (ORDER BY d.order_date, s.supplier_id, m.material) AS STRING), 6, '0') as order_id,
  s.supplier_id,
  m.material as material_type,
  ROUND(100 + (rand() * 2000), 2) as volume_kg,
  d.order_date
FROM suppliers s
CROSS JOIN materials m
CROSS JOIN dates d
WHERE rand() < 0.08  -- Sample to get ~1000 rows
ORDER BY order_date;

-- =====================================================
-- 2. ESG Supplier Audits (Dynamics 365 Source)
-- =====================================================
DROP TABLE IF EXISTS marion_test.bronze.esg_supplier_audits;

CREATE TABLE marion_test.bronze.esg_supplier_audits (
  supplier_id STRING,
  audit_year INT,
  audit_status STRING,
  certification STRING
) USING DELTA;

-- Generate audit data for suppliers
INSERT INTO marion_test.bronze.esg_supplier_audits
WITH suppliers AS (
  SELECT 'SUP-' || LPAD(CAST(id AS STRING), 2, '0') as supplier_id
  FROM (SELECT explode(sequence(1, 25)) as id)
),
years AS (
  SELECT year FROM VALUES (2023), (2024) AS t(year)
),
certifications AS (
  SELECT cert, weight FROM VALUES
    ('LWG Gold', 0.15),
    ('LWG Silver', 0.20),
    ('GOTS', 0.10),
    ('OEKO-TEX', 0.15),
    ('FSC', 0.10),
    ('None', 0.30)
  AS t(cert, weight)
)
SELECT
  s.supplier_id,
  y.year as audit_year,
  CASE
    WHEN c.cert = 'None' THEN 'NOT_AUDITED'
    WHEN rand() > 0.1 THEN 'PASSED'
    ELSE 'FAILED'
  END as audit_status,
  c.cert as certification
FROM suppliers s
CROSS JOIN years y
CROSS JOIN certifications c
WHERE rand() < c.weight * 2  -- Weighted sampling
ORDER BY supplier_id, audit_year;

-- =====================================================
-- 3. ESG Emissions Data (Excel/SharePoint Source)
-- =====================================================
DROP TABLE IF EXISTS marion_test.bronze.esg_emissions;

CREATE TABLE marion_test.bronze.esg_emissions (
  year INT,
  scope STRING,
  emissions_tco2 DECIMAL(10,2)
) USING DELTA;

-- Generate emissions data
INSERT INTO marion_test.bronze.esg_emissions
VALUES
  (2020, 'Scope 1', 1450.00),
  (2020, 'Scope 2', 3200.00),
  (2020, 'Scope 3', 18500.00),
  (2021, 'Scope 1', 1380.00),
  (2021, 'Scope 2', 3050.00),
  (2021, 'Scope 3', 17800.00),
  (2022, 'Scope 1', 1290.00),
  (2022, 'Scope 2', 2850.00),
  (2022, 'Scope 3', 16900.00),
  (2023, 'Scope 1', 1200.00),
  (2023, 'Scope 2', 2650.00),
  (2023, 'Scope 3', 15800.00),
  (2024, 'Scope 1', 1120.00),
  (2024, 'Scope 2', 2480.00),
  (2024, 'Scope 3', 14500.00);

-- =====================================================
-- Verification queries
-- =====================================================
SELECT 'sap_procurement_orders' as table_name, COUNT(*) as row_count FROM marion_test.bronze.sap_procurement_orders
UNION ALL
SELECT 'esg_supplier_audits' as table_name, COUNT(*) as row_count FROM marion_test.bronze.esg_supplier_audits
UNION ALL
SELECT 'esg_emissions' as table_name, COUNT(*) as row_count FROM marion_test.bronze.esg_emissions;
