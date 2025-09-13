-- Extensión para generar UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla Users (User Service)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cognito_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL
);

-- Tabla Transactions (Transaction Service)
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_user_id UUID NOT NULL,
    to_user_id UUID NOT NULL,
    amount DECIMAL(12, 2) NOT NULL
);

-- Datos de muestra (opcional para testing)
INSERT INTO 
    users (cognito_id, email) 
VALUES
    ('11111111-2222-3333-4444-555555555555', 'admin@micropay.com')
