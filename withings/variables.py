from bidict import bidict

MEAS_CODES = bidict({
    'Weight':                     1,    # (kg)
    'Height':                     4,    # (meter)
    'Fat Free Mass':              5,    # (kg)
    'Fat Ratio':                  6,    # (%)
    'Fat Mass Weight':            8,    # (kg)
    'Diastolic Blood Pressure':   9,    # (mmHg)
    'Systolic Blood Pressure':    10,   # (mmHg)
    'Heart Pulse':                11,   # (bpm) - only for BPM and scale',  # devices
    'Temperature':                12,   # (celsius)
    'SP02':                       54,   # (%)
    'Body Temperature':           71,   # (celsius)
    'Skin Temperature':           73,   # (celsius)
    'Muscle Mass':                76,   # (kg)
    'Hydration':                  77,   # (kg)
    'Bone Mass':                  88,   # (kg)
    'Pulse Wave Velocity':        91,   # (m/s)
    'VO2 max':                    123,  # Numerical measurement of your body’s ability to consume oxygen', # (ml/min/kg).
})