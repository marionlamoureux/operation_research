{{
  config(
    materialized='table',
    tags=['silver', 'fact']
  )
}}

select
  p.year,
  p.material_type,
  p.supplier_id,
  p.order_id,
  p.volume_kg,
  a.audit_status,
  a.certification,
  case
    when a.supplier_id is not null then true
    else false
  end as is_audited
from {{ ref('stg_procurement_orders') }} p
left join {{ ref('stg_supplier_audits') }} a
  on p.supplier_id = a.supplier_id
 and p.year = a.year
