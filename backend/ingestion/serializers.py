"""
Django REST Framework serializers for ESG data.
"""

from rest_framework import serializers
from .models import (
    Company, RawIngestion, NormalizedEmission, AuditLog, DataSourceType
)


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ['id', 'name', 'industry', 'headquarters', 'created_at']


class RawIngestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RawIngestion
        fields = ['id', 'company', 'source_type', 'raw_data', 'uploaded_at', 'status', 'parse_error']
        read_only_fields = ['id', 'uploaded_at']


class NormalizedEmissionSerializer(serializers.ModelSerializer):
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    scope_display = serializers.CharField(source='get_scope_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    approval_status_display = serializers.CharField(source='get_approval_status_display', read_only=True)
    flagged_anomaly_display = serializers.CharField(source='get_flagged_anomaly_display', read_only=True)
    
    class Meta:
        model = NormalizedEmission
        fields = [
            'id', 'company', 'source_type', 'source_type_display',
            'scope', 'scope_display', 'category', 'category_display',
            'quantity_value', 'quantity_unit', 'quantity_kg_co2e', 'unit_conversion_factor',
            'activity_date', 'billing_period_start', 'billing_period_end',
            'facility', 'vendor_supplier', 'cost_center',
            'origin', 'destination', 'distance_km',
            'flagged_anomaly', 'flagged_anomaly_display', 'analyst_notes',
            'approval_status', 'approval_status_display', 'approved_by', 'approved_at',
            'data_source_ingestion',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = ['id', 'company', 'action', 'action_display', 'related_emission', 'related_ingestion', 
                  'user', 'timestamp', 'reason', 'details_json']
        read_only_fields = ['id', 'timestamp']
