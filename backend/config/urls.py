"""
URL Configuration for ESG ingestion app.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter
from ingestion.views import (
    CompanyViewSet, DataSourceViewSet, RawIngestionViewSet, 
    NormalizedEmissionViewSet, AuditLogViewSet, UploadDataView,
    DashboardSummaryView
)

router = DefaultRouter()
router.register(r'companies', CompanyViewSet, basename='company')
router.register(r'data-sources', DataSourceViewSet, basename='datasource')
router.register(r'raw-ingestions', RawIngestionViewSet, basename='raw-ingestion')
router.register(r'emissions', NormalizedEmissionViewSet, basename='emission')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('', RedirectView.as_view(url='/api/', permanent=False)),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/upload/', UploadDataView.as_view(), name='upload-data'),
    path('api/dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]
