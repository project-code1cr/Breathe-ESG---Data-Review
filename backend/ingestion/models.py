"""
Core data models for ESG emissions ingestion and tracking.

Design Principles:
1. Multi-tenancy: All data scoped to Company
2. Source-of-truth tracking: Every normalized emission points to raw data source
3. Scope categorization: Scope 1/2/3 at data level, not computed downstream
4. Unit normalization: Raw units stored, normalized to SI at ingestion
5. Audit trail: Every state change tracked with user, timestamp, reason
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from enum import Enum
import uuid


class Company(models.Model):
    """
    Multi-tenant isolation. Each company gets their own data silo.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    industry = models.CharField(max_length=100)  # e.g., "Manufacturing", "Technology"
    headquarters = models.CharField(max_length=255)  # For utility baselines
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Companies"
    
    def __str__(self):
        return self.name


class DataSourceType(models.TextChoices):
    """Types of data sources we ingest"""
    SAP = 'SAP', 'SAP Fuel/Procurement'
    UTILITY = 'UTILITY', 'Utility CSV'
    TRAVEL = 'TRAVEL', 'Corporate Travel (Concur)'


class ScopeType(models.TextChoices):
    """GHG Protocol scopes"""
    SCOPE_1 = 'SCOPE_1', 'Scope 1 - Direct Emissions'
    SCOPE_2 = 'SCOPE_2', 'Scope 2 - Purchased Energy'
    SCOPE_3 = 'SCOPE_3', 'Scope 3 - Value Chain'


class CategoryType(models.TextChoices):
    """Emission categories (subset per source)"""
    # SAP/Fuel categories
    FUEL_DIESEL = 'FUEL_DIESEL', 'Diesel (Scope 1)'
    FUEL_GASOLINE = 'FUEL_GASOLINE', 'Gasoline (Scope 1)'
    FUEL_NATURAL_GAS = 'FUEL_NATURAL_GAS', 'Natural Gas (Scope 1)'
    FUEL_COAL = 'FUEL_COAL', 'Coal (Scope 1)'
    
    # Procurement (typically Scope 3)
    PROCUREMENT_MATERIALS = 'PROCUREMENT_MATERIALS', 'Raw Materials (Scope 3)'
    PROCUREMENT_PACKAGING = 'PROCUREMENT_PACKAGING', 'Packaging (Scope 3)'
    
    # Utility (Scope 2)
    ELECTRICITY = 'ELECTRICITY', 'Electricity (Scope 2)'
    
    # Travel
    TRAVEL_FLIGHTS = 'TRAVEL_FLIGHTS', 'Business Flights (Scope 3)'
    TRAVEL_HOTEL = 'TRAVEL_HOTEL', 'Hotel Stays (Scope 3)'
    TRAVEL_GROUND = 'TRAVEL_GROUND', 'Ground Transport (Scope 3)'


class Unit(models.TextChoices):
    """Supported units (normalized to SI at ingestion)"""
    KG = 'KG', 'Kilograms'
    TONNE = 'TONNE', 'Metric Tonnes (1000 kg)'
    LITRE = 'LITRE', 'Litres'
    CUBIC_METER = 'M3', 'Cubic Meters'
    KWH = 'KWH', 'Kilowatt Hours'
    KM = 'KM', 'Kilometres'
    MILES = 'MILES', 'Miles'
    NIGHT = 'NIGHT', 'Hotel Nights'


class RawIngestion(models.Model):
    """
    Raw data as received from source. Never modified after creation.
    This is our audit trail foundation - every normalized record traces back here.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='raw_ingestions')
    source_type = models.CharField(max_length=20, choices=DataSourceType.choices)
    
    # Raw data snapshot (JSON to handle varied formats)
    raw_data = models.JSONField()  # Store original row as-is
    
    # Ingestion metadata
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Processing status
    INGESTION_STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('PARSED', 'Parsed Successfully'),
        ('FAILED', 'Failed to Parse'),
        ('APPROVED', 'Approved for Audit'),
        ('REJECTED', 'Rejected by Analyst'),
    ]
    status = models.CharField(max_length=20, choices=INGESTION_STATUS_CHOICES, default='PENDING')
    
    # If parsing failed, store the error
    parse_error = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['company', 'source_type', 'status']),
            models.Index(fields=['uploaded_at']),
        ]
    
    def __str__(self):
        return f"{self.source_type} - {self.company.name} ({self.uploaded_at})"


class NormalizedEmission(models.Model):
    """
    Normalized, standardized emission data ready for analysis.
    Every row traces back to RawIngestion via data_source_ingestion.
    
    Key principle: This is the analyst's review surface. All data quality issues
    surface here before approval.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='normalized_emissions')
    
    # Data source lineage (source-of-truth tracking)
    data_source_ingestion = models.ForeignKey(RawIngestion, on_delete=models.PROTECT, related_name='normalized_emissions')
    source_type = models.CharField(max_length=20, choices=DataSourceType.choices)
    
    # Classification
    scope = models.CharField(max_length=20, choices=ScopeType.choices)
    category = models.CharField(max_length=50, choices=CategoryType.choices)
    
    # Normalized quantities (always SI units: kg, km, kWh)
    # Raw units stored separately for audit trail
    quantity_kg_co2e = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    quantity_value = models.DecimalField(max_digits=15, decimal_places=6)
    quantity_unit = models.CharField(max_length=20, choices=Unit.choices)
    
    # For tracking conversions (e.g., 50 L diesel → 50 * 2.68 = 134 kg CO2e)
    unit_conversion_factor = models.DecimalField(max_digits=10, decimal_places=6, help_text="Applied to convert to CO2e")
    
    # Temporal data
    activity_date = models.DateField(help_text="Date of actual activity")
    billing_period_start = models.DateField(null=True, blank=True, help_text="For utilities: period start")
    billing_period_end = models.DateField(null=True, blank=True, help_text="For utilities: period end")
    
    # Optional metadata
    facility = models.CharField(max_length=255, null=True, blank=True, help_text="e.g., 'Plant A', 'HQ Building'")
    vendor_supplier = models.CharField(max_length=255, null=True, blank=True)
    cost_center = models.CharField(max_length=100, null=True, blank=True)
    
    # Travel-specific
    origin = models.CharField(max_length=100, null=True, blank=True, help_text="e.g., airport code 'ORD'")
    destination = models.CharField(max_length=100, null=True, blank=True, help_text="e.g., airport code 'SEA'")
    distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Analyst review flags (these surface data quality issues)
    ANOMALY_CHOICES = [
        ('NONE', 'No Issues'),
        ('UNIT_MISMATCH', 'Unit conversion unclear'),
        ('MISSING_FACTOR', 'Emission factor missing'),
        ('OUTLIER', 'Value significantly outside normal range'),
        ('DATE_INCONSISTENT', 'Date inconsistent with period'),
        ('DUPLICATE_LIKELY', 'Likely duplicate record'),
    ]
    flagged_anomaly = models.CharField(max_length=50, choices=ANOMALY_CHOICES, default='NONE')
    analyst_notes = models.TextField(null=True, blank=True)
    
    # Approval workflow
    APPROVAL_STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Analyst Review'),
        ('APPROVED', 'Approved for Audit'),
        ('REJECTED', 'Rejected - See Notes'),
        ('NEEDS_CLARIFICATION', 'Needs Clarification'),
    ]
    approval_status = models.CharField(max_length=30, choices=APPROVAL_STATUS_CHOICES, default='PENDING_REVIEW')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_emissions')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['company', 'approval_status']),
            models.Index(fields=['activity_date']),
            models.Index(fields=['scope']),
        ]
        verbose_name_plural = "Normalized Emissions"
    
    def __str__(self):
        return f"{self.category} - {self.quantity_value} {self.quantity_unit}"


class AuditLog(models.Model):
    """
    Immutable record of every state change. Who did what, when, why.
    This is not just for compliance—it's for debugging data issues.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.PROTECT, related_name='audit_logs')
    
    # What changed
    ACTION_CHOICES = [
        ('INGESTED', 'Raw data ingested'),
        ('PARSED', 'Data parsed to normalized'),
        ('APPROVED', 'Analyst approved'),
        ('REJECTED', 'Analyst rejected'),
        ('FLAGGED', 'Anomaly flagged'),
        ('UNFLAGGED', 'Anomaly unflagged'),
        ('NOTES_ADDED', 'Analyst notes added'),
    ]
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    related_emission = models.ForeignKey(NormalizedEmission, on_delete=models.SET_NULL, null=True, blank=True)
    related_ingestion = models.ForeignKey(RawIngestion, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Who and when
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Why
    reason = models.TextField(null=True, blank=True)
    
    # State snapshot (before/after for debugging)
    details_json = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['company', 'timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.timestamp}"
