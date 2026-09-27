from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    CategoryViewSet, ProductViewSet, SaleViewSet, UserViewSet,
    RefundViewSet, AuditLogViewSet, ReceiptSettingsViewSet,
    report_summary, report_revenue_per_day, report_top_products,
    report_revenue_per_cashier, report_revenue_per_category,
    report_revenue_per_hour, report_top_margin, report_low_stock,
    report_average_basket, report_comparison,
    daily_report, periodic_report, me,
)

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('products', ProductViewSet, basename='product')
router.register('sales', SaleViewSet, basename='sale')
router.register('refunds', RefundViewSet, basename='refund')
router.register('audit-log', AuditLogViewSet, basename='audit-log')
router.register('users', UserViewSet, basename='user')
router.register('receipt-settings', ReceiptSettingsViewSet, basename='receipt-settings')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', me),
    path('reports/summary/', report_summary),
    path('reports/revenue-per-day/', report_revenue_per_day),
    path('reports/top-products/', report_top_products),
    path('reports/revenue-per-cashier/', report_revenue_per_cashier),
    path('reports/revenue-per-category/', report_revenue_per_category),
    path('reports/revenue-per-hour/', report_revenue_per_hour),
    path('reports/top-margin/', report_top_margin),
    path('reports/low-stock/', report_low_stock),
    path('reports/average-basket/', report_average_basket),
    path('reports/comparison/', report_comparison),
    path('reports/daily/', daily_report),
    path('reports/periodic/', periodic_report),
]