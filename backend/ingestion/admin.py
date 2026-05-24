from django.contrib import admin
from .models import Company, RawIngestion, NormalizedEmission, AuditLog


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ['name', 'industry', 'created_at']
    search_fields = ['name']


@admin.register(RawIngestion)
class RawIngestionAdmin(admin.ModelAdmin):
    list_display = ['company', 'source_type', 'status', 'uploaded_at']
    list_filter = ['source_type', 'status', 'uploaded_at']
    search_fields = ['company__name']
    readonly_fields = ['id', 'uploaded_at', 'raw_data']


@admin.register(NormalizedEmission)
class NormalizedEmissionAdmin(admin.ModelAdmin):
    list_display = ['company', 'category', 'scope', 'quantity_kg_co2e', 'approval_status', 'created_at']
    list_filter = ['scope', 'category', 'approval_status', 'flagged_anomaly']
    search_fields = ['company__name', 'vendor_supplier', 'facility']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['company', 'action', 'user', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['company__name', 'user__username']
    readonly_fields = ['id', 'timestamp']
