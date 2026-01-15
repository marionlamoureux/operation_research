-- =====================================================
-- Quick Check - View the Sustainability Narrative
-- =====================================================

-- The main result: sustainability claims
SELECT
  brand,
  year,
  leather_claim,
  audited_volume_kg,
  total_volume_kg
FROM marion_test.dbt_analytics_gold.sustainability_narrative
ORDER BY year DESC;

-- The underlying metric
SELECT
  year,
  total_volume_kg,
  audited_volume_kg,
  ROUND(audited_ratio * 100, 1) as audited_percentage
FROM marion_test.dbt_analytics_gold.claim_leather_audited_ratio
ORDER BY year DESC;

-- Sample of the fact table
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
ORDER BY year DESC, volume_kg DESC
LIMIT 10;
