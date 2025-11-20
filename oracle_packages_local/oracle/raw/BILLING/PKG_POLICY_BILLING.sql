
CREATE OR REPLACE PACKAGE BILLING.PKG_POLICY_BILLING IS
    -- Global constants
    G_DEFAULT_LATE_FEE_RATE NUMBER := 0.05;
    G_MAX_RETRIES NUMBER := 3;

    -- Calculate late fee for a policy
    PROCEDURE CALC_LATE_FEE(
        p_policy_id IN NUMBER,
        p_days_overdue IN NUMBER,
        p_late_fee OUT NUMBER
    );

    -- Process payment for a policy
    PROCEDURE PROCESS_PAYMENT(
        p_policy_id IN NUMBER,
        p_payment_amount IN NUMBER,
        p_payment_date IN DATE
    );

    -- Generate billing statement
    FUNCTION GENERATE_STATEMENT(
        p_policy_id IN NUMBER,
        p_statement_date IN DATE
    ) RETURN VARCHAR2;

END PKG_POLICY_BILLING;
/

CREATE OR REPLACE PACKAGE BODY BILLING.PKG_POLICY_BILLING IS

    PROCEDURE CALC_LATE_FEE(
        p_policy_id IN NUMBER,
        p_days_overdue IN NUMBER,
        p_late_fee OUT NUMBER
    ) IS
        v_premium NUMBER;
        v_policy_status VARCHAR2(20);
    BEGIN
        -- Read policy premium from table
        SELECT premium, status
        INTO v_premium, v_policy_status
        FROM BILLING.POLICIES
        WHERE policy_id = p_policy_id;

        -- Check if policy is active
        IF v_policy_status = 'ACTIVE' THEN
            -- Calculate late fee: premium * rate * days
            p_late_fee := v_premium * G_DEFAULT_LATE_FEE_RATE * (p_days_overdue / 30);

            -- Log the calculation
            BILLING.PKG_UTILS.LOG_EVENT('LATE_FEE_CALC', p_policy_id, p_late_fee);
        ELSE
            p_late_fee := 0;
        END IF;

    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_late_fee := 0;
            BILLING.PKG_UTILS.LOG_ERROR('POLICY_NOT_FOUND', p_policy_id);
        WHEN OTHERS THEN
            RAISE;
    END CALC_LATE_FEE;

    PROCEDURE PROCESS_PAYMENT(
        p_policy_id IN NUMBER,
        p_payment_amount IN NUMBER,
        p_payment_date IN DATE
    ) IS
        v_current_balance NUMBER;
        v_new_balance NUMBER;
    BEGIN
        -- Get current balance
        SELECT balance
        INTO v_current_balance
        FROM BILLING.POLICIES
        WHERE policy_id = p_policy_id
        FOR UPDATE;

        -- Calculate new balance
        v_new_balance := v_current_balance - p_payment_amount;

        -- Update policy balance
        UPDATE BILLING.POLICIES
        SET balance = v_new_balance,
            last_payment_date = p_payment_date
        WHERE policy_id = p_policy_id;

        -- Insert payment record
        INSERT INTO BILLING.PAYMENTS (
            policy_id,
            payment_amount,
            payment_date,
            balance_after
        ) VALUES (
            p_policy_id,
            p_payment_amount,
            p_payment_date,
            v_new_balance
        );

        -- Send payment confirmation
        NOTIFICATIONS.PKG_EMAIL.SEND_PAYMENT_CONFIRMATION(p_policy_id, p_payment_amount);

        COMMIT;

    EXCEPTION
        WHEN OTHERS THEN
            ROLLBACK;
            BILLING.PKG_UTILS.LOG_ERROR('PAYMENT_FAILED', p_policy_id);
            RAISE;
    END PROCESS_PAYMENT;

    FUNCTION GENERATE_STATEMENT(
        p_policy_id IN NUMBER,
        p_statement_date IN DATE
    ) RETURN VARCHAR2 IS
        v_statement CLOB;
        v_policy_rec BILLING.POLICIES%ROWTYPE;

        CURSOR c_payments IS
            SELECT payment_date, payment_amount
            FROM BILLING.PAYMENTS
            WHERE policy_id = p_policy_id
            AND payment_date >= ADD_MONTHS(p_statement_date, -1)
            ORDER BY payment_date;
    BEGIN
        -- Get policy details
        SELECT *
        INTO v_policy_rec
        FROM BILLING.POLICIES
        WHERE policy_id = p_policy_id;

        -- Build statement header
        v_statement := 'Policy Statement for Policy #' || p_policy_id || CHR(10);
        v_statement := v_statement || 'Premium: $' || v_policy_rec.premium || CHR(10);
        v_statement := v_statement || 'Current Balance: $' || v_policy_rec.balance || CHR(10);

        -- Add payment history
        FOR payment_rec IN c_payments LOOP
            v_statement := v_statement || 'Payment on ' || TO_CHAR(payment_rec.payment_date, 'YYYY-MM-DD');
            v_statement := v_statement || ': $' || payment_rec.payment_amount || CHR(10);
        END LOOP;

        RETURN v_statement;
    END GENERATE_STATEMENT;

END PKG_POLICY_BILLING;
/
