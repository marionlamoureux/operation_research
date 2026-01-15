-- =====================================================
-- Verify dbt Results - Sustainability Demo
-- =====================================================

-- Check all schemas exist
SHOW SCHEMAS IN marion_test;

-- =====================================================
-- 1. Gold Layer - Sustainability Narrative
-- =====================================================
SELECT
  '=== SUSTAINABILITY NARRATIVE ===' as section,
  NULL as brand,
  NULL as year,
  NULL as leather_claim,
  NULL as audited_volume_kg,
  NULL as total_volume_kg

UNION ALL

SELECT
  NULL as section,
  brand,
  year,
  leather_claim,
  audited_volume_kg,
  total_volume_kg
FROM marion_test.dbt_analytics_gold.sustainability_narrative
ORDER BY year DESC;

-- =====================================================
-- 2. Gold Layer - Leather Audited Ratio
-- =====================================================
SELECT
  year,
  total_volume_kg,
  audited_volume_kg,
  ROUND(audited_ratio * 100, 1) as audited_percentage
FROM marion_test.dbt_analytics_gold.claim_leather_audited_ratio
ORDER BY year DESC;

-- =====================================================
-- 3. Silver Layer - Fact Material Sourcing (LEATHER only)
-- =====================================================
SELECT
  year,
  material_type,
  supplier_id,
  COUNT(*) as order_count,
  SUM(volume_kg) as total_volume_kg,
  SUM(CASE WHEN is_audited THEN volume_kg ELSE 0 END) as audited_volume_kg,
  COUNT(DISTINCT CASE WHEN is_audited THEN supplier_id END) as audited_suppliers
FROM marion_test.dbt_analytics_silver.fact_material_sourcing
WHERE material_type = 'LEATHER'
GROUP BY year, material_type, supplier_id
ORDER BY year DESC, total_volume_kg DESC
LIMIT 20;

-- =====================================================
-- 4. Sample of Fact Table Records
-- =====================================================
SELECT
  year,
  material_type,
  supplier_id,
  order_id,
  volume_kg,
  audit_status,
  certification,
  is_audited
FROM marion_test.dbt_analytics_silver.fact_material_sourcing
WHERE material_type = 'LEATHER'
ORDER BY year DESC, order_date DESC
LIMIT 10;

-- =====================================================
-- 5. Summary Statistics by Material Type
-- =====================================================
SELECT
  material_type,
  COUNT(DISTINCT year) as years_tracked,
  COUNT(*) as total_orders,
  SUM(volume_kg) as total_volume_kg,
  COUNT(DISTINCT supplier_id) as unique_suppliers,
  SUM(CASE WHEN is_audited THEN 1 ELSE 0 END) as audited_orders,
  ROUND(AVG(CASE WHEN is_audited THEN 1.0 ELSE 0.0 END) * 100, 1) as pct_audited
FROM marion_test.dbt_analytics_silver.fact_material_sourcing
GROUP BY material_type
ORDER BY total_volume_kg DESC;

-- =====================================================
-- 6. Audit Coverage Over Time
-- =====================================================
SELECT
  year,
  COUNT(*) as total_orders,
  SUM(CASE WHEN is_audited THEN 1 ELSE 0 END) as audited_orders,
  SUM(volume_kg) as total_volume,
  SUM(CASE WHEN is_audited THEN volume_kg ELSE 0 END) as audited_volume,
  ROUND(SUM(CASE WHEN is_audited THEN volume_kg ELSE 0 END) / SUM(volume_kg) * 100, 1) as pct_volume_audited
FROM marion_test.dbt_analytics_silver.fact_material_sourcing
GROUP BY year
ORDER BY year DESC;

-- =====================================================
-- 7. Check Staging Views
-- =====================================================
SELECT 'stg_procurement_orders' as view_name, COUNT(*) as row_count
FROM marion_test.dbt_analytics_silver.stg_procurement_orders

UNION ALL

SELECT 'stg_supplier_audits' as view_name, COUNT(*) as row_count
FROM marion_test.dbt_analytics_silver.stg_supplier_audits

UNION ALL

SELECT 'stg_emissions' as view_name, COUNT(*) as row_count
FROM marion_test.dbt_analytics_silver.stg_emissions;
