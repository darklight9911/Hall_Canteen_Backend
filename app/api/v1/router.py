from fastapi import APIRouter

from app.api.v1.endpoints import auth, partner

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(partner.router, prefix="/partner", tags=["partner"])

# Registered as endpoints are built:
# from app.api.v1.endpoints import menu, orders, billing, reports
# api_router.include_router(menu.router, prefix="/menu", tags=["menu"])
# api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
# api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
# api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
