{{
  config(
    materialized='view',
    tags=['staging', 'esg']
  )
}}

select
  supplier_id,
  audit_year as year,
  audit_status,
  certification
from {{ source('dynamics365', 'esg_supplier_audits') }}
where audit_status = 'PASSED'  -- Only certified suppliers
