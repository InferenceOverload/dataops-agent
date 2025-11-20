
CREATE OR REPLACE PACKAGE BILLING.PKG_UTILS IS
    PROCEDURE LOG_EVENT(
        p_event_type IN VARCHAR2,
        p_policy_id IN NUMBER,
        p_amount IN NUMBER
    );

    PROCEDURE LOG_ERROR(
        p_error_code IN VARCHAR2,
        p_policy_id IN NUMBER
    );
END PKG_UTILS;
/

CREATE OR REPLACE PACKAGE BODY BILLING.PKG_UTILS IS
    PROCEDURE LOG_EVENT(
        p_event_type IN VARCHAR2,
        p_policy_id IN NUMBER,
        p_amount IN NUMBER
    ) IS
    BEGIN
        INSERT INTO BILLING.EVENT_LOG (
            event_type,
            policy_id,
            amount,
            event_timestamp
        ) VALUES (
            p_event_type,
            p_policy_id,
            p_amount,
            SYSDATE
        );
    END LOG_EVENT;

    PROCEDURE LOG_ERROR(
        p_error_code IN VARCHAR2,
        p_policy_id IN NUMBER
    ) IS
    BEGIN
        INSERT INTO BILLING.ERROR_LOG (
            error_code,
            policy_id,
            error_timestamp
        ) VALUES (
            p_error_code,
            p_policy_id,
            SYSDATE
        );
    END LOG_ERROR;
END PKG_UTILS;
/
