"""
Django REST API views for ESG data ingestion and review.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import (
    Company, RawIngestion, NormalizedEmission, AuditLog,
    DataSourceType, ScopeType
)
from .serializers import (
    CompanySerializer, RawIngestionSerializer, NormalizedEmissionSerializer,
    AuditLogSerializer
)
from .parsers import PARSER_MAP
import json


class CompanyViewSet(viewsets.ModelViewSet):
    """List and manage companies"""
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    
    def get_queryset(self):
        # In real app, filter to current user's companies
        return Company.objects.all()


class DataSourceViewSet(viewsets.ReadOnlyModelViewSet):
    """List available data sources (for UI dropdown, etc.)"""
    def list(self, request):
        sources = [
            {'value': code, 'label': label}
            for code, label in DataSourceType.choices
        ]
        return Response(sources)


class RawIngestionViewSet(viewsets.ModelViewSet):
    """List raw ingestions and their parse status"""
    queryset = RawIngestion.objects.all()
    serializer_class = RawIngestionSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['uploaded_at']
    ordering = ['-uploaded_at']
    
    def get_queryset(self):
        qs = RawIngestion.objects.all().select_related('company', 'uploaded_by')
        # Manual filtering from query params
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        source_type = self.request.query_params.get('source_type')
        if source_type:
            qs = qs.filter(source_type=source_type)
        status_val = self.request.query_params.get('status')
        if status_val:
            qs = qs.filter(status=status_val)
        return qs


class NormalizedEmissionViewSet(viewsets.ModelViewSet):
    """
    Main analyst dashboard endpoint.
    List, filter, and approve/reject emissions.
    """
    queryset = NormalizedEmission.objects.all()
    serializer_class = NormalizedEmissionSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['analyst_notes', 'vendor_supplier', 'facility', 'origin', 'destination']
    ordering_fields = ['activity_date', 'quantity_kg_co2e', 'created_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        qs = NormalizedEmission.objects.all().select_related(
            'company', 'approved_by', 'data_source_ingestion'
        )
        # Manual filtering from query params
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        scope = self.request.query_params.get('scope')
        if scope:
            qs = qs.filter(scope=scope)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        approval_status = self.request.query_params.get('approval_status')
        if approval_status:
            qs = qs.filter(approval_status=approval_status)
        flagged_anomaly = self.request.query_params.get('flagged_anomaly')
        if flagged_anomaly:
            qs = qs.filter(flagged_anomaly=flagged_anomaly)
        return qs
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Analyst approves an emission record"""
        emission = self.get_object()
        emission.approval_status = 'APPROVED'
        emission.approved_by = request.user
        emission.approved_at = timezone.now()
        emission.save()
        
        # Log audit event
        AuditLog.objects.create(
            company=emission.company,
            action='APPROVED',
            related_emission=emission,
            user=request.user,
            reason=request.data.get('reason', '')
        )
        
        return Response({'status': 'approved'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Analyst rejects an emission record"""
        emission = self.get_object()
        emission.approval_status = 'REJECTED'
        emission.approved_by = request.user
        emission.approved_at = timezone.now()
        emission.save()
        
        AuditLog.objects.create(
            company=emission.company,
            action='REJECTED',
            related_emission=emission,
            user=request.user,
            reason=request.data.get('reason', 'No reason provided')
        )
        
        return Response({'status': 'rejected'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def flag_anomaly(self, request, pk=None):
        """Flag an anomaly for analyst review"""
        emission = self.get_object()
        emission.flagged_anomaly = request.data.get('anomaly_type', 'OUTLIER')
        emission.analyst_notes = request.data.get('notes', '')
        emission.save()
        
        AuditLog.objects.create(
            company=emission.company,
            action='FLAGGED',
            related_emission=emission,
            user=request.user,
            reason=f"Flagged: {emission.flagged_anomaly}"
        )
        
        return Response({'status': 'flagged'}, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def add_notes(self, request, pk=None):
        """Add analyst notes to emission"""
        emission = self.get_object()
        emission.analyst_notes = request.data.get('notes', '')
        emission.save()
        
        AuditLog.objects.create(
            company=emission.company,
            action='NOTES_ADDED',
            related_emission=emission,
            user=request.user,
            reason=emission.analyst_notes
        )
        
        return Response({'status': 'notes added'}, status=status.HTTP_200_OK)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Immutable audit trail"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
    
    def get_queryset(self):
        qs = AuditLog.objects.all().select_related('company', 'user', 'related_emission', 'related_ingestion')
        # Manual filtering from query params
        company_id = self.request.query_params.get('company')
        if company_id:
            qs = qs.filter(company_id=company_id)
        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)
        user_id = self.request.query_params.get('user')
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs


class UploadDataView(APIView):
    """
    Handle file uploads for each data source type.
    Accepts JSON or CSV, parses, creates RawIngestion + NormalizedEmission records.
    """
    
    def post(self, request):
        """Upload and ingest data"""
        try:
            company_id = request.data.get('company_id')
            source_type = request.data.get('source_type')
            data_rows = request.data.get('data', [])
            
            # Validate
            if not company_id or not source_type:
                return Response(
                    {'error': 'company_id and source_type required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if source_type not in ['SAP', 'UTILITY', 'TRAVEL']:
                return Response(
                    {'error': f'Unknown source_type: {source_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            company = Company.objects.get(id=company_id)
            parser = PARSER_MAP[source_type]
            
            ingested_count = 0
            failed_count = 0
            emission_ids = []
            
            # Process each row
            for row_idx, row_data in enumerate(data_rows):
                try:
                    # Create raw ingestion record
                    raw_ingestion = RawIngestion.objects.create(
                        company=company,
                        source_type=source_type,
                        raw_data=row_data,
                        uploaded_by=request.user,
                        status='PARSED'
                    )
                    
                    # Parse to normalized
                    parsed_emissions = parser.parse(row_data)
                    
                    for emission_data in parsed_emissions:
                        emission_data.company = company
                        emission_data.data_source_ingestion = raw_ingestion
                        emission_data.save()
                        emission_ids.append(str(emission_data.id))
                    
                    # Log successful parse
                    AuditLog.objects.create(
                        company=company,
                        action='INGESTED',
                        related_ingestion=raw_ingestion,
                        user=request.user,
                        reason=f"Ingested {len(parsed_emissions)} emission record(s)"
                    )
                    
                    ingested_count += 1
                
                except Exception as e:
                    failed_count += 1
                    print(f"Row {row_idx} parse error: {str(e)}")
            
            return Response({
                'status': 'success',
                'ingested_count': ingested_count,
                'failed_count': failed_count,
                'emission_ids': emission_ids
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class DashboardSummaryView(APIView):
    """Dashboard summary statistics for analyst review"""
    
    def get(self, request):
        """Get summary stats"""
        company_id = request.query_params.get('company_id')
        
        if not company_id:
            return Response(
                {'error': 'company_id required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            company = Company.objects.get(id=company_id)
        except Company.DoesNotExist:
            return Response(
                {'error': 'Company not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get emissions
        emissions = NormalizedEmission.objects.filter(company=company)
        
        # Summary stats
        stats = {
            'total_records': emissions.count(),
            'total_co2e_kg': float(emissions.aggregate(Sum('quantity_kg_co2e'))['quantity_kg_co2e__sum'] or 0),
            'by_status': dict(
                emissions.values('approval_status').annotate(count=Count('id')).values_list('approval_status', 'count')
            ),
            'by_scope': dict(
                emissions.values('scope').annotate(count=Count('id')).values_list('scope', 'count')
            ),
            'by_category': dict(
                emissions.values('category').annotate(count=Count('id')).values_list('category', 'count')
            ),
            'flagged_anomalies': dict(
                emissions.filter(~Q(flagged_anomaly='NONE')).values('flagged_anomaly').annotate(count=Count('id')).values_list('flagged_anomaly', 'count')
            ),
            'pending_review': emissions.filter(approval_status='PENDING_REVIEW').count(),
            'approved': emissions.filter(approval_status='APPROVED').count(),
            'rejected': emissions.filter(approval_status='REJECTED').count(),
        }
        
        return Response(stats, status=status.HTTP_200_OK)
