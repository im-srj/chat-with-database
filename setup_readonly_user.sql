-- SQL Script to Create Read-Only User for Production
-- Run this as PostgreSQL superuser (postgres)

-- ============================================
-- STEP 1: Create Read-Only User
-- ============================================
-- Replace 'readonly_user' and 'your_secure_password' with your values

CREATE USER readonly_user WITH PASSWORD 'your_secure_password';

-- ============================================
-- STEP 2: Grant Connection Rights
-- ============================================
-- Replace 'your_database_name' with your actual database name

GRANT CONNECT ON DATABASE your_database_name TO readonly_user;

-- ============================================
-- STEP 3: Grant Schema Usage
-- ============================================

GRANT USAGE ON SCHEMA public TO readonly_user;

-- ============================================
-- STEP 4: Grant SELECT on All Existing Tables
-- ============================================

GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- ============================================
-- STEP 5: Grant SELECT on Future Tables
-- ============================================
-- This ensures new tables created in the future
-- will automatically have SELECT permission

ALTER DEFAULT PRIVILEGES IN SCHEMA public 
GRANT SELECT ON TABLES TO readonly_user;

-- ============================================
-- STEP 6: Grant Access to Information Schema
-- ============================================
-- Required for schema extraction to work

GRANT SELECT ON information_schema.tables TO readonly_user;
GRANT SELECT ON information_schema.columns TO readonly_user;
GRANT SELECT ON information_schema.table_constraints TO readonly_user;
GRANT SELECT ON information_schema.key_column_usage TO readonly_user;
GRANT SELECT ON information_schema.constraint_column_usage TO readonly_user;

-- Grant access to pg_catalog for additional metadata
GRANT SELECT ON pg_catalog.pg_index TO readonly_user;
GRANT SELECT ON pg_catalog.pg_attribute TO readonly_user;
GRANT SELECT ON pg_catalog.pg_indexes TO readonly_user;

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check user was created
SELECT usename, usecreatedb, usesuper 
FROM pg_user 
WHERE usename = 'readonly_user';

-- Check database permissions
SELECT datname, has_database_privilege('readonly_user', datname, 'CONNECT') AS can_connect
FROM pg_database 
WHERE datname = 'your_database_name';

-- Check table permissions (run as readonly_user to test)
-- \c your_database_name readonly_user
-- SELECT table_name, privilege_type 
-- FROM information_schema.table_privileges 
-- WHERE grantee = 'readonly_user' AND table_schema = 'public'
-- LIMIT 10;

-- ============================================
-- REVOKE EXAMPLE (if needed)
-- ============================================
-- If you accidentally gave too many permissions:

-- REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA public FROM readonly_user;
-- REVOKE CREATE ON SCHEMA public FROM readonly_user;

-- ============================================
-- NOTES
-- ============================================
-- 1. Never use this user for write operations
-- 2. Store credentials in .env file, never in code
-- 3. Use different passwords for dev/staging/production
-- 4. Consider using connection pooling for better performance
-- 5. Monitor query performance and set timeouts
