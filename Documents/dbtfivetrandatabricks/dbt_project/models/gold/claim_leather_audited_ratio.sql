{{
  config(
    materialized='table',
    tags=['gold', 'claim']
  )
}}

with leather_sourcing as (
  select
    year,
    sum(volume_kg) as total_volume_kg,
    sum(case when is_audited then volume_kg else 0 end) as audited_volume_kg
  from {{ ref('fact_material_sourcing') }}
  where material_type = 'LEATHER'
  group by year
)

select
  year,
  total_volume_kg,
  audited_volume_kg,
  round(audited_volume_kg / nullif(total_volume_kg, 0), 3) as audited_ratio
from leather_sourcing
order by year desc
