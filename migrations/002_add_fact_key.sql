-- Migration: Add fact_key primary key to fact_employee_attrition
-- Date: 2026-03-27
-- Description: Adds a SERIAL primary key column to the fact table

ALTER TABLE fact_employee_attrition
ADD COLUMN fact_key SERIAL PRIMARY KEY;
