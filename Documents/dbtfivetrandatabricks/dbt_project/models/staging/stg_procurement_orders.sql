{{
  config(
    materialized='view',
    tags=['staging', 'procurement']
  )
}}

select
  order_id,
  supplier_id,
  upper(material_type) as material_type,
  volume_kg,
  year(order_date) as year,
  order_date
from {{ source('sap', 'sap_procurement_orders') }}
