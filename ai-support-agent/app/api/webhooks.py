
"""Webhook endpoints for external integrations."""

from fastapi import APIRouter, Depends, HTTPException, status
import logging

from app.schemas.request import WebhookRequest
from app.schemas.response import WebhookResponse
from app.dependencies import verify_api_key

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/webhooks",
    response_model=WebhookResponse,
    summary="Process webhook",
    description="Receive and process webhooks from external services",
)
async def process_webhook(
    request: WebhookRequest,
    api_key: str = Depends(verify_api_key),
) -> WebhookResponse:
    """
    Process incoming webhook.
    
    Args:
        request: Webhook request
        api_key: Verified API key
        
    Returns:
        WebhookResponse
    """
    logger.info(f"Received webhook: {request.event_type} from {request.source}")
    
    # Route webhook based on event type
    if request.event_type.startswith("order."):
        return await _handle_order_webhook(request)
    elif request.event_type.startswith("ticket."):
        return await _handle_ticket_webhook(request)
    else:
        logger.warning(f"Unknown webhook type: {request.event_type}")
    
    return WebhookResponse(
        success=True,
        event_type=request.event_type,
        message="Webhook processed"
    )


async def _handle_order_webhook(request: WebhookRequest) -> WebhookResponse:
    """Handle order-related webhooks."""
    # Process order updates (e.g., from Shopify)
    # Update memory, notify users, etc.
    return WebhookResponse(
        success=True,
        event_type=request.event_type,
        message="Order webhook processed"
    )


async def _handle_ticket_webhook(request: WebhookRequest) -> WebhookResponse:
    """Handle ticket-related webhooks."""
    # Process ticket updates (e.g., from Gorgias)
    return WebhookResponse(
        success=True,
        event_type=request.event_type,
        message="Ticket webhook processed"
    )
