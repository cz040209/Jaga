from enum import StrEnum


class CustomerStatus(StrEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class StaffRole(StrEnum):
    ANALYST = "analyst"
    RISK_MANAGER = "risk_manager"
    ADMIN = "admin"


class StaffStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class SessionStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class DeviceTrustStatus(StrEnum):
    UNKNOWN = "unknown"
    TRUSTED = "trusted"
    BLOCKED = "blocked"


class AccountType(StrEnum):
    CUSTOMER = "customer"
    MERCHANT = "merchant"
    SYSTEM = "system"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class PayeeCheckStatus(StrEnum):
    PENDING = "pending"
    CLEAR = "clear"
    WATCHLISTED = "watchlisted"
    BLOCKED = "blocked"
    ERROR = "error"


class TransactionType(StrEnum):
    OPENING_BALANCE = "opening_balance"
    TRANSFER = "transfer"
    MERCHANT_PAYMENT = "merchant_payment"
    QR_PAYMENT = "qr_payment"
    REVERSAL = "reversal"
    ADJUSTMENT = "adjustment"


class TransactionStatus(StrEnum):
    PENDING = "pending"
    STEP_UP_REQUIRED = "step_up_required"
    HELD = "held"
    POSTED = "posted"
    BLOCKED = "blocked"
    FAILED = "failed"
    REVERSED = "reversed"
    CANCELLED = "cancelled"


class LedgerDirection(StrEnum):
    DEBIT = "debit"
    CREDIT = "credit"


class Channel(StrEnum):
    WEB = "web"
    PWA = "pwa"
    TELEGRAM = "telegram"
    API = "api"
    SYSTEM = "system"


class EventType(StrEnum):
    REGISTRATION = "registration"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    PASSWORD_CHANGED = "password_changed"
    DEVICE_ADDED = "device_added"
    PAYEE_ADDED = "payee_added"
    PAYEE_CHANGED = "payee_changed"
    TRANSFER = "transfer"
    MERCHANT_PAYMENT = "merchant_payment"
    QR_PAYMENT = "qr_payment"
    ACCOUNT_FROZEN = "account_frozen"
    ACCOUNT_UNFROZEN = "account_unfrozen"
    SCAM_CHECK = "scam_check"


class ScoringStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DecisionAction(StrEnum):
    APPROVE = "approve"
    STEP_UP = "step_up"
    HOLD = "hold"
    BLOCK = "block"


class CaseStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    AWAITING_CUSTOMER = "awaiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CasePriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LabelValue(StrEnum):
    FRAUD = "fraud"
    NOT_FRAUD = "not_fraud"
    SUSPICIOUS = "suspicious"
    INCONCLUSIVE = "inconclusive"


class LabelSource(StrEnum):
    ANALYST = "analyst"
    CUSTOMER = "customer"
    ARENA = "arena"
    SYSTEM = "system"
    MODEL = "model"


class RuleStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DISABLED = "disabled"
    RETIRED = "retired"


class ModelStatus(StrEnum):
    CANDIDATE = "candidate"
    SHADOW = "shadow"
    ACTIVE = "active"
    RETIRED = "retired"
    FAILED = "failed"


class NotificationChannel(StrEnum):
    IN_APP = "in_app"
    SMS_INBOX = "sms_inbox"
    TELEGRAM = "telegram"
    WEB_PUSH = "web_push"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


class ChallengeType(StrEnum):
    OTP = "otp"
    SCAM_QUESTIONNAIRE = "scam_questionnaire"
    TRANSACTION_CONFIRMATION = "transaction_confirmation"


class ChallengeStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class WatchlistEntityType(StrEnum):
    ACCOUNT = "account"
    PHONE = "phone"
    EMAIL = "email"
    DEVICE = "device"
    IP_ADDRESS = "ip_address"
    MERCHANT = "merchant"


class ScamCheckInputType(StrEnum):
    TEXT = "text"
    IMAGE = "image"


class ScamCheckStatus(StrEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    DISABLED = "disabled"