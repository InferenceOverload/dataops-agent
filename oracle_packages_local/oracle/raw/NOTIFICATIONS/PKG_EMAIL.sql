
CREATE OR REPLACE PACKAGE NOTIFICATIONS.PKG_EMAIL IS
    PROCEDURE SEND_PAYMENT_CONFIRMATION(
        p_policy_id IN NUMBER,
        p_amount IN NUMBER
    );
END PKG_EMAIL;
/

CREATE OR REPLACE PACKAGE BODY NOTIFICATIONS.PKG_EMAIL IS
    PROCEDURE SEND_PAYMENT_CONFIRMATION(
        p_policy_id IN NUMBER,
        p_amount IN NUMBER
    ) IS
        v_email_address VARCHAR2(200);
    BEGIN
        -- Get customer email
        SELECT email
        INTO v_email_address
        FROM CUSTOMERS.CUSTOMER_EMAILS
        WHERE policy_id = p_policy_id;

        -- Send email (simplified)
        INSERT INTO NOTIFICATIONS.EMAIL_QUEUE (
            recipient,
            subject,
            body,
            queue_timestamp
        ) VALUES (
            v_email_address,
            'Payment Confirmation',
            'Your payment of $' || p_amount || ' has been received.',
            SYSDATE
        );
    END SEND_PAYMENT_CONFIRMATION;
END PKG_EMAIL;
/
