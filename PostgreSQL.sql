-- Extensión para generar UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla Users (User Service)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cognito_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL
);

-- Tabla Notifications (Notifications Service)
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    recipient_email VARCHAR(255) NOT NULL,
    notification_type VARCHAR(50) NOT NULL, -- registration, payment, transaction, general
    subject VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    user_id VARCHAR(255), -- Cognito user ID
    reference_id UUID, -- payment_id, transaction_id, etc.
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed
    email_message_id VARCHAR(255), -- SES MessageId
    push_message_id VARCHAR(255), -- SNS MessageId
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP
);

-- Tabla Accounts (Account Service)
-- CREATE TABLE accounts (
--     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
--     user_id VARCHAR(255) NOT NULL, -- Cognito user ID
--     account_number VARCHAR(20) UNIQUE NOT NULL,
--     balance DECIMAL(12, 2) DEFAULT 0.00
-- );

-- Tabla Payments (Payment Service)
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_account_id UUID NOT NULL,
    to_account_id UUID NOT NULL,
    amount DECIMAL(12, 2) NOT NULL
);

-- Tabla Transactions (Transaction Service)
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL,
    payment_id UUID,
    amount DECIMAL(12, 2) NOT NULL,
    balance_after DECIMAL(12, 2) NOT NULL
);

-- Datos de muestra (opcional para testing)
INSERT INTO 
    users (cognito_id, email) 
VALUES
    ('cognito-user-1', 'admin@company.com')

INSERT INTO 
    users (cognito_id, email) 
VALUES
    ('cognito-user-1', 'john@example.com'),
    ('cognito-user-2', 'jane@example.com');

INSERT INTO 
    accounts (user_id, account_number, balance) 
VALUES
    ('cognito-user-1', '1001234567', 1500.00),
    ('cognito-user-1', '1001234568', 5000.00),
    ('cognito-user-2', '1001234569', 2500.00);

INSERT INTO payments 
    (from_account_id, to_account_id, amount) 
VALUES
    (
        (SELECT id FROM accounts WHERE account_number = '1001234567'),
        (SELECT id FROM accounts WHERE account_number = '1001234569'),
        100.00);

INSERT INTO transactions
    (account_id, payment_id, amount, balance_after) 
VALUES
    (
        (SELECT id FROM accounts WHERE account_number = '1001234567'),
        (SELECT id FROM accounts WHERE account_number = '1001234568'),
        100.00, 1400.00),
    (
        (SELECT id FROM accounts WHERE account_number = '1001234569'),
        (SELECT id FROM accounts WHERE account_number = '1001234568'),
        100.00, 2600.00);
