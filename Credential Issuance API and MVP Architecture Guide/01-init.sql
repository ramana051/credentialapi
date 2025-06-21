-- Create database if it doesn't exist
CREATE DATABASE IF NOT EXISTS digital_credentials;

-- Create user if it doesn't exist
DO
$do$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'dcp_user') THEN

      CREATE ROLE dcp_user LOGIN PASSWORD 'dcp_password';
   END IF;
END
$do$;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE digital_credentials TO dcp_user;

-- Connect to the database
\c digital_credentials;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO dcp_user;

