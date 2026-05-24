"""
Data source parsers. Each handles one input format and normalizes to NormalizedEmission.

Key design: Parsers are defensive. They flag anomalies rather than silently fixing them.
The analyst reviews flagged issues before approval.
"""

import csv
import json
from decimal import Decimal
from datetime import datetime
from io import StringIO
import pandas as pd
from abc import ABC, abstractmethod

from .models import (
    NormalizedEmission, RawIngestion, ScopeType, CategoryType, Unit,
    AuditLog
)


class EmissionConversionFactors:
    """
    Standard emission factors (kg CO2e per unit).
    Source: IPCC, EPA, UK Government GHG reporting framework.
    
    In real implementation, these would be configurable and versioned
    so auditors can see what factor was used for each row.
    """
    FUEL = {
        'diesel': 2.68,  # kg CO2e per litre
        'gasoline': 2.31,  # kg CO2e per litre
        'natural_gas': 2.04,  # kg CO2e per cubic metre (at STP)
        'coal': 2.41,  # kg CO2e per kg (varies by coal type)
    }
    
    # Electricity: grid-dependent. These are US average; should be parametrized by region
    ELECTRICITY = {
        'default': 0.385,  # kg CO2e per kWh (US average)
    }
    
    TRAVEL = {
        'flight_economy': 0.092,  # kg CO2e per km, economy
        'flight_business': 0.215,  # kg CO2e per km, business
        'hotel_per_night': 50.0,  # kg CO2e per night (rough average)
        'ground_transport': 0.112,  # kg CO2e per km (car average)
    }


class DataSourceParser(ABC):
    """Base class for all parsers"""
    
    @abstractmethod
    def parse(self, raw_data):
        """
        Parse raw data (dict from RawIngestion.raw_data).
        Return list of NormalizedEmission objects (unsaved).
        """
        pass


class SAPFuelProcurementParser(DataSourceParser):
    """
    Parses SAP flat file export (CSV) for fuel and procurement data.
    
    Expected columns (from real SAP SE16N export):
    - PO_NUMBER: Purchase order ID
    - LINE_ITEM: Line item number
    - MATERIAL: Material code
    - DESCRIPTION: Material description
    - QTY_ORDERED: Original quantity ordered
    - QTY_RECEIVED: Actual quantity received (goods receipt)
    - UOM: Unit of measure (L, KG, M3, etc.)
    - RECEIPT_DATE: Date goods were received
    - VENDOR: Vendor code
    - COST_CENTER: Cost center
    - GL_ACCOUNT: GL account code
    """
    
    def parse(self, raw_data):
        """Parse SAP export line item"""
        emissions = []
        
        try:
            # raw_data is a dict with one row
            row = raw_data
            
            # Determine if this is fuel or procurement
            material_desc = str(row.get('DESCRIPTION', '')).lower()
            uom = str(row.get('UOM', '')).upper()
            
            # Classify as fuel or procurement
            is_fuel = any(keyword in material_desc for keyword in ['diesel', 'petrol', 'gasoline', 'fuel', 'gas'])
            
            if is_fuel:
                emission = self._parse_fuel_line(row)
            else:
                emission = self._parse_procurement_line(row)
            
            if emission:
                emissions.append(emission)
        
        except Exception as e:
            raise ValueError(f"SAP parse error: {str(e)}")
        
        return emissions
    
    def _parse_fuel_line(self, row):
        """Parse fuel line item"""
        try:
            # Quantity
            qty_received = Decimal(str(row.get('QTY_RECEIVED', 0) or 0))
            uom = str(row.get('UOM', 'L')).upper()
            
            # Normalize UOM
            if uom in ['L', 'LITRE', 'LITRES']:
                quantity_unit = Unit.LITRE
                # Assume diesel (most common industrial fuel)
                conversion_factor = Decimal(str(EmissionConversionFactors.FUEL['diesel']))
                scope = ScopeType.SCOPE_1
                category = CategoryType.FUEL_DIESEL
            elif uom in ['KG', 'K']:
                # Could be coal or other solid fuel
                quantity_unit = Unit.KG
                conversion_factor = Decimal(str(EmissionConversionFactors.FUEL['coal']))
                scope = ScopeType.SCOPE_1
                category = CategoryType.FUEL_COAL
            else:
                # Unknown unit - flag as anomaly
                category = CategoryType.FUEL_DIESEL
                scope = ScopeType.SCOPE_1
                quantity_unit = Unit.LITRE
                conversion_factor = Decimal('0')
            
            # Parse date
            receipt_date_str = row.get('RECEIPT_DATE', '')
            try:
                activity_date = datetime.strptime(receipt_date_str, '%Y-%m-%d').date()
            except:
                activity_date = datetime.now().date()
            
            emission = NormalizedEmission(
                quantity_value=qty_received,
                quantity_unit=quantity_unit,
                unit_conversion_factor=conversion_factor,
                quantity_kg_co2e=qty_received * conversion_factor if conversion_factor else None,
                scope=scope,
                category=category,
                activity_date=activity_date,
                vendor_supplier=row.get('VENDOR', ''),
                cost_center=row.get('COST_CENTER', ''),
                flagged_anomaly='NONE' if conversion_factor else 'UNIT_MISMATCH',
                approval_status='PENDING_REVIEW',
            )
            return emission
        
        except Exception as e:
            raise ValueError(f"Fuel line parse error: {e}")
    
    def _parse_procurement_line(self, row):
        """Parse procurement line item"""
        try:
            # For procurement, we have limited data
            # In real deployment, would cross-ref with material master to get emission factors
            
            qty = Decimal(str(row.get('QTY_RECEIVED', 0) or 0))
            
            emission = NormalizedEmission(
                quantity_value=qty,
                quantity_unit=Unit.KG,  # Placeholder
                unit_conversion_factor=Decimal('0'),  # Unknown without material master
                scope=ScopeType.SCOPE_3,
                category=CategoryType.PROCUREMENT_MATERIALS,
                activity_date=datetime.now().date(),
                vendor_supplier=row.get('VENDOR', ''),
                cost_center=row.get('COST_CENTER', ''),
                flagged_anomaly='MISSING_FACTOR',  # Highlight this needs emission factor
                analyst_notes='Emission factor not available. Material master lookup needed.',
                approval_status='NEEDS_CLARIFICATION',
            )
            return emission
        
        except Exception as e:
            raise ValueError(f"Procurement line parse error: {e}")


class UtilityCSVParser(DataSourceParser):
    """
    Parses utility CSV export for electricity data.
    
    Expected columns:
    - Account_Number: Utility account ID
    - Meter_ID: Meter identifier
    - Billing_Period_Start: Date
    - Billing_Period_End: Date
    - Usage_kWh: Total usage
    - Peak_Demand_kW: Peak demand (for demand charges)
    - Total_Charge_USD: Total bill amount (for cost tracking)
    """
    
    def parse(self, raw_data):
        """Parse utility CSV line"""
        emissions = []
        
        try:
            row = raw_data
            
            # Parse usage
            usage_kwh = Decimal(str(row.get('Usage_kWh', 0) or 0))
            
            # Parse dates
            period_start_str = row.get('Billing_Period_Start', '')
            period_end_str = row.get('Billing_Period_End', '')
            
            try:
                period_start = datetime.strptime(period_start_str, '%Y-%m-%d').date()
                period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()
            except:
                period_start = None
                period_end = None
            
            # Use period end as activity date (when bill was issued)
            activity_date = period_end if period_end else datetime.now().date()
            
            # Emission factor - in real deployment, would be grid-region dependent
            conversion_factor = Decimal(str(EmissionConversionFactors.ELECTRICITY['default']))
            
            emission = NormalizedEmission(
                quantity_value=usage_kwh,
                quantity_unit=Unit.KWH,
                unit_conversion_factor=conversion_factor,
                quantity_kg_co2e=usage_kwh * conversion_factor,
                scope=ScopeType.SCOPE_2,
                category=CategoryType.ELECTRICITY,
                activity_date=activity_date,
                billing_period_start=period_start,
                billing_period_end=period_end,
                facility=row.get('Meter_ID', 'Unknown'),
                flagged_anomaly='NONE',
                approval_status='PENDING_REVIEW',
            )
            emissions.append(emission)
        
        except Exception as e:
            raise ValueError(f"Utility parse error: {str(e)}")
        
        return emissions


class ConcurTravelParser(DataSourceParser):
    """
    Parses Concur/corporate travel expense data.
    
    Expected fields:
    - Expense_ID: Unique expense record ID
    - Category: 'Airfare', 'Lodging', 'Ground_Transport'
    - Date: Transaction date
    - Origin: Airport code (flights) or city (hotels)
    - Destination: Airport code (flights) or city (hotels)
    - Distance_km: Actual distance or calculated from airport codes
    - Class_of_Service: 'Economy', 'Business', 'First'
    - Duration_Nights: For hotels
    """
    
    def parse(self, raw_data):
        """Parse Concur travel expense"""
        emissions = []
        
        try:
            row = raw_data
            category = str(row.get('Category', '')).lower()
            
            if 'airfare' in category or 'flight' in category:
                emission = self._parse_flight(row)
            elif 'lodging' in category or 'hotel' in category:
                emission = self._parse_hotel(row)
            elif 'ground' in category or 'transport' in category:
                emission = self._parse_ground(row)
            else:
                raise ValueError(f"Unknown travel category: {category}")
            
            if emission:
                emissions.append(emission)
        
        except Exception as e:
            raise ValueError(f"Travel parse error: {str(e)}")
        
        return emissions
    
    def _parse_flight(self, row):
        """Parse flight expense"""
        try:
            # Distance
            distance_km = Decimal(str(row.get('Distance_km', 0) or 0))
            
            if not distance_km or distance_km == 0:
                raise ValueError("Flight distance missing - cannot calculate emissions")
            
            # Class of service affects emission factor
            service_class = str(row.get('Class_of_Service', 'Economy')).lower()
            
            if 'business' in service_class:
                factor = Decimal(str(EmissionConversionFactors.TRAVEL['flight_business']))
            else:
                factor = Decimal(str(EmissionConversionFactors.TRAVEL['flight_economy']))
            
            # Parse date
            date_str = row.get('Date', '')
            try:
                activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                activity_date = datetime.now().date()
            
            emission = NormalizedEmission(
                quantity_value=distance_km,
                quantity_unit=Unit.KM,
                unit_conversion_factor=factor,
                quantity_kg_co2e=distance_km * factor,
                scope=ScopeType.SCOPE_3,
                category=CategoryType.TRAVEL_FLIGHTS,
                activity_date=activity_date,
                origin=row.get('Origin', ''),
                destination=row.get('Destination', ''),
                distance_km=distance_km,
                flagged_anomaly='NONE',
                analyst_notes=f"Class: {service_class}, Factor: {factor} kg CO2e/km",
                approval_status='PENDING_REVIEW',
            )
            return emission
        
        except Exception as e:
            raise ValueError(f"Flight parse error: {e}")
    
    def _parse_hotel(self, row):
        """Parse hotel stay"""
        try:
            nights = int(row.get('Duration_Nights', 1) or 1)
            
            factor = Decimal(str(EmissionConversionFactors.TRAVEL['hotel_per_night']))
            total_co2e = Decimal(nights) * factor
            
            date_str = row.get('Date', '')
            try:
                activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                activity_date = datetime.now().date()
            
            emission = NormalizedEmission(
                quantity_value=Decimal(nights),
                quantity_unit=Unit.NIGHT,
                unit_conversion_factor=factor,
                quantity_kg_co2e=total_co2e,
                scope=ScopeType.SCOPE_3,
                category=CategoryType.TRAVEL_HOTEL,
                activity_date=activity_date,
                destination=row.get('Destination', ''),
                flagged_anomaly='NONE',
                analyst_notes=f"Assumed {factor} kg CO2e/night (avg occupancy)",
                approval_status='PENDING_REVIEW',
            )
            return emission
        
        except Exception as e:
            raise ValueError(f"Hotel parse error: {e}")
    
    def _parse_ground(self, row):
        """Parse ground transport"""
        try:
            distance_km = Decimal(str(row.get('Distance_km', 0) or 0))
            
            if not distance_km or distance_km == 0:
                # Try to flag but don't fail
                anomaly = 'MISSING_FACTOR'
            else:
                anomaly = 'NONE'
            
            factor = Decimal(str(EmissionConversionFactors.TRAVEL['ground_transport']))
            
            date_str = row.get('Date', '')
            try:
                activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                activity_date = datetime.now().date()
            
            emission = NormalizedEmission(
                quantity_value=distance_km if distance_km else Decimal(1),
                quantity_unit=Unit.KM,
                unit_conversion_factor=factor,
                quantity_kg_co2e=distance_km * factor if distance_km else None,
                scope=ScopeType.SCOPE_3,
                category=CategoryType.TRAVEL_GROUND,
                activity_date=activity_date,
                flagged_anomaly=anomaly,
                analyst_notes="Assumed car; actual vehicle type unknown",
                approval_status='PENDING_REVIEW' if distance_km else 'NEEDS_CLARIFICATION',
            )
            return emission
        
        except Exception as e:
            raise ValueError(f"Ground transport parse error: {e}")


# Parser factory
PARSER_MAP = {
    'SAP': SAPFuelProcurementParser(),
    'UTILITY': UtilityCSVParser(),
    'TRAVEL': ConcurTravelParser(),
}
