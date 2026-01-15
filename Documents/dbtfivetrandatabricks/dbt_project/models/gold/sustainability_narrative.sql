{{
  config(
    materialized='table',
    tags=['gold', 'narrative']
  )
}}

select
  'Maison Étoile' as brand,
  year,
  concat(
    'In ', year,
    ', ', round(audited_ratio * 100, 1),
    '% of our leather sourcing volume came from audited suppliers.'
  ) as leather_claim,
  audited_volume_kg,
  total_volume_kg
from {{ ref('claim_leather_audited_ratio') }}
order by year desc
