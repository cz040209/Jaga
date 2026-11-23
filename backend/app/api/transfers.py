"""Send money to a payee, and view transfer receipts."""

from typing import Annotated, Any

from fastapi import APIRouter, Header, Response, status

from app.api.deps import CurrentCustomer, DbSession
from app.schemas.auth import ErrorResponse
from app.schemas.transfer import TransferCreate, TransferOut
from app.services import transfers as transfer_service

router = APIRouter(prefix="/transfers", tags=["transfers"])

OpenApiResponses = dict[int | str, dict[str, Any]]

SEND_RESPONSES: OpenApiResponses = {
    200: {
        "model": TransferOut,
        "description": "Replay: this Idempotency-Key was already used; the original "
        "transfer is returned and nothing new is sent (header Idempotent-Replayed: true)",
    },
    400: {"model": ErrorResponse, "description": "Invalid amount"},
    404: {"model": ErrorResponse, "description": "Payee not found (or not yours)"},
    409: {
        "model": ErrorResponse,
        "description": "Insufficient funds, account unavailable, or key reused for a "
        "different transfer",
    },
}

# A new random value (e.g. a UUID) per transfer. The app creates it when the
# customer taps "Send" and reuses it if the request has to be retried.
IdempotencyKey = Annotated[
    str,
    Header(
        min_length=8,
        max_length=100,
        pattern=r"^[A-Za-z0-9_\-:.]+$",
        description="Unique per transfer, e.g. a UUID. Retrying with the same key "
        "never sends the money twice.",
    ),
]


@router.post("", status_code=status.HTTP_201_CREATED, responses=SEND_RESPONSES)
async def send_transfer(
    body: TransferCreate,
    idempotency_key: IdempotencyKey,
    customer: CurrentCustomer,
    db: DbSession,
    response: Response,
) -> TransferOut:
    """Send money from your primary account to one of your payees."""
    result = await transfer_service.send_transfer(
        db,
        customer.id,
        payee_id=body.payee_id,
        amount=body.amount,
        note=body.note,
        idempotency_key=idempotency_key,
    )
    if result.replayed:
        response.status_code = status.HTTP_200_OK
        response.headers["Idempotent-Replayed"] = "true"
    return TransferOut.from_receipt(result.receipt)


@router.get(
    "/{transfer_id}",
    responses={404: {"model": ErrorResponse, "description": "Not found (or not yours)"}},
)
async def get_transfer(transfer_id: int, customer: CurrentCustomer, db: DbSession) -> TransferOut:
    """A transfer receipt. Works for the sender and the recipient."""
    receipt = await transfer_service.get_receipt(db, customer.id, transfer_id)
    return TransferOut.from_receipt(receipt)
