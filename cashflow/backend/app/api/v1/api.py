from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    business,
    cash_accounts,
    commitments,
    receivables,
    credit_cards,
    purchase_orders,
    forecast,
    alerts,
    weekly_review,
    scenarios,
    integrations,
    reconciliation,
    dashboard,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(business.router, prefix="/businesses", tags=["Business"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(cash_accounts.router, prefix="/cash-accounts", tags=["Cash Accounts"])
api_router.include_router(commitments.router, prefix="/commitments", tags=["Commitments"])
api_router.include_router(receivables.router, prefix="/receivables", tags=["Receivables"])
api_router.include_router(credit_cards.router, prefix="/credit-cards", tags=["Credit Cards"])
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["Purchase Orders"])
api_router.include_router(forecast.router, prefix="/forecast", tags=["Forecast"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(weekly_review.router, prefix="/weekly-review", tags=["Weekly Review"])
api_router.include_router(scenarios.router, prefix="/scenarios", tags=["Scenarios"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["Integrations"])
api_router.include_router(reconciliation.router, prefix="/reconciliation", tags=["Reconciliation"])
