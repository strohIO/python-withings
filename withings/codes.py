from enum import Enum

# TODO: Probably move this class into structures.py
class ApiCodeEnum(Enum):
    '''Case-insensitive; unique; auto indexed; reversible'''

    def __new__(cls, value, code=None):
        obj = object.__new__(cls)
        obj._value_ = value
        
        # code defaults to index
        obj.code = code or len(cls.__members__)
        
        return obj


    def __init__(self, *args):
        '''Check that no duplicate NAME, VALUE, or CODE exists.'''

        cls = self.__class__
        
        if any(self.value.lower() == e.value.lower() for e in cls):
            raise ValueError(
                "Case-insensitive alias already exists in Enum: %s"
                % self.value.lower())
        
        # necessary case-insensitive check on name?
        elif any(self.name.lower()  == e.lower() for e in cls._member_names_):
            raise ValueError(
                "Case-insensitive name already exists in Enum: %s"
                % self.name.upper())

        if any(self.code == e.code for e in cls):
            raise ValueError(
                "Code already exists in Enum: %s"
                % self.code)


    @classmethod
    def _missing_(cls, value):
        '''cls._member_names_,  cls._value2member_map_,  cls._member_names_,
           cls.__members__ == cpy of cls._member_map_'''

        # Check if value is an INDEX
        if isinstance(value,int):
            code2member_map = {v.code:v for k,v in cls.__members__.items()}
            if value in code2member_map:
                return code2member_map[value]

        else:
            # Check for case-insensitive member VALUE
            upper_value2member = {k.upper():v for k,v in cls._value2member_map_.items()}
            if value.upper() in upper_value2member:
                return upper_value2member[value.upper()]

            # Check for case insensitive member NAME
            upper_members = {k.upper():v for k,v in cls.__members__.items()}
            if value.upper() in upper_members:
                return upper_members[value.upper()]

    def __int__(self):
        return self.code



class MeasureType(ApiCodeEnum):
    WEIGHT = 'Weight',                          1   # (kg)
    HEIGHT = 'Height',                          4   # (meter)
    FAT_FREE_MASS = 'Fat Free Mass',            5   # (kg)
    BFP = 'Fat Ratio',                          6   # (%)
    FAT_MASS_WEIGHT = 'Fat Mass Weight',        8   # (kg)
    DIASTOLIC_BP = 'Diastolic Blood Pressure',  9   # (mmHg)
    SYSTOLIC_BP = 'Systolic Blood Pressure',   10   # (mmHg)
    PULSE = 'Heart Pulse',                     11   # (bpm) - only for BPM and scale', # devices
    TEMP = 'Temperature',                      12   # (celsius)
    SP02 = 'SP02',                             54   # (%)
    BODY_TEMP = 'Body Temperature',            71   # (celsius)
    SKIN_TEMP = 'Skin Temperature',            73   # (celsius)
    MUSCLE_MASS = 'Muscle Mass',               76   # (kg)
    HYDRATION = 'Hydration',                   77   # (kg)
    BONE_MASS = 'Bone Mass',                   88   # (kg)
    PULSE_WAVE_VEL = 'Pulse Wave Velocity',    91   # (m/s)
    V02_MAX = 'VO2 max',                      123   # Numerical measurement of your body’s ability to consume oxygen', # (ml/min/kg).


class SleepState(ApiCodeEnum):
    AWAKE = 'awake'
    LIGHT = 'light'
    DEEP = 'deep'
    REM = 'rem'



if __name__ == '__main__':
    print(int(MeasureType('Systolic Blood Pressure')))
    print(int(MeasureType('heart pulse')))
    print(MeasureType(10).value)
    print(MeasureType(MeasureType.BFP))