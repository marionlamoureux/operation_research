{{
  config(
    materialized='view',
    tags=['staging', 'esg']
  )
}}

select
  year,
  scope,
  emissions_tco2
from {{ source('esg', 'esg_emissions') }}
