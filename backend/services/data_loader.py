import pandas as pd
import os
from typing import Dict, List, Optional
from backend.models.data_models import PatientProfile, Biomarkers, RiskLevel

import logging
logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._cache: Dict[str, PatientProfile] = {}

    def load_data(self) -> Dict[str, PatientProfile]:
        if self._cache:
            return self._cache

        if not os.path.exists(self.file_path):
            logger.warning(f"Warning: Data file {self.file_path} not found.")
            return {}

        try:
            df = pd.read_excel(self.file_path)
            # Map columns to schema
            for _, row in df.iterrows():
                try:
                    # Parse BP (e.g., "120/80")
                    bp = str(row.get('Blood Pressure', '120/80'))
                    if '/' in bp:
                        systolic, diastolic = map(int, bp.split('/'))
                    else:
                        systolic, diastolic = 120, 80

                    # Parse Risk Level (1-High, 2-Moderate, 3-Low) or text
                    risk_val = row.get('Diabetes Risk', 'Moderate')
                    risk_enum = RiskLevel.MODERATE
                    if isinstance(risk_val, str):
                        if 'High' in risk_val: risk_enum = RiskLevel.HIGH
                        elif 'Low' in risk_val: risk_enum = RiskLevel.LOW
                    
                    user_id = str(row.get('PREVENT_ID', ''))
                    if not user_id: continue

                    biomarkers = Biomarkers(
                        a1c=float(row.get('A1c', 0)),
                        fbs=float(row.get('FBS', 0)),
                        systolic_bp=systolic,
                        diastolic_bp=diastolic,
                        ldl=float(row.get('LDL', 0)),
                        hdl=float(row.get('HDL', 0)),
                        total_cholesterol=float(row.get('Total_Cholesterol', 0)),
                        weight=float(row.get('BMI', 25) * 2.5), # Rough est since we don't have weight, only BMI
                        height=170 # Default
                    )
                    
                    profile = PatientProfile(
                        user_id=user_id,
                        name=str(row.get('Name', 'User')),
                        age=int(row.get('Age', 30)),
                        diabetes_risk_score=risk_enum,
                        risk_score_numeric=int(row.get('Years to DM', 5) * 10), # Mock mapping
                        biomarkers=biomarkers,
                        motivation_level=str(row.get('Behavioral Segment', 'Unknown')),
                        physician_name=str(row.get('Physician', 'Dr. Smith'))
                    )
                    
                    self._cache[user_id] = profile
                except Exception as e:
                    logger.error(f"Error skipping row {row.get('PREVENT_ID')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error loading excel: {e}")
            return {}

        return self._cache

    def get_patient_by_name(self, name: str) -> Optional[PatientProfile]:
        """Case-insensitive search for patient by name."""
        self.load_data() # Ensure data is loaded
        name_lower = name.lower().strip()
        for profile in self._cache.values():
            if profile.name.lower() == name_lower:
                return profile
        return None

