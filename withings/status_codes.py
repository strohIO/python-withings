
from requests import codes


class LookupDict(dict):
    '''Mostly based on Request module's LookupDict class and codes object.'''

    def __init__(self,items=None,name=None,):
        self.name = name

        for title, codes in items.items():
                setattr(self, title.lower(), codes)
                setattr(self, title.upper(), codes)

        super(LookupDict,self).__init__()

    def __repr__(self):
        return '<lookup \s%\s>' % (self.name)

    def __getitem__(self, key):
        # Allow fall-through here, so values default to None
        return self.__dict__.get(key, None)

    def get(self, key, default=None):
        return self.__dict__.get(key, default)



_codes = {
    'Operation_was_successful': (0,), 
    'Authentication_failed': (100, 101, 102, 200, 401), 
    'Invalid_params': (201, 202, 203, 204, 205, 206, 207, 208, 209,
                       210, 211, 212, 213, 216, 217, 218, 220, 221,
                       223, 225, 227, 228, 229, 230, 234, 235, 236,
                       238, 240, 241, 242, 243, 244, 245, 246, 247,
                       248, 249, 250, 251, 252, 254, 260, 261, 262,
                       263, 264, 265, 266, 267, 271, 272, 275, 276,
                       283, 284, 285, 286, 287, 288, 290, 293, 294,
                       295, 297, 300, 301, 302, 303, 304, 321, 323,
                       324, 325, 326, 327, 328, 329, 330, 331, 332,
                       333, 334, 335, 336, 337, 338, 339, 340, 341,
                       342, 343, 344, 345, 346, 347, 348, 349, 350,
                       351, 352, 353, 380, 381, 382, 400, 501, 502,
                       503, 504, 505, 506, 509, 510, 511, 523, 532,
                       3017, 3018, 3019),
    'Unauthorized': (214, 277, 2553, 2555),
    'An_error_occurred': (215, 219, 222, 224, 226, 231, 233, 237, 253,
                          255, 256, 257, 258, 259, 268, 269, 270, 273,
                          274, 278, 279, 280, 281, 282, 289, 291, 292,
                          296, 298, 305, 306, 308, 309, 310, 311, 312,
                          313, 314, 315, 316, 317, 318, 319, 320, 322,
                          370, 371, 372, 373, 374, 375, 383, 391, 402,
                          516, 517, 518, 519, 520, 521, 525, 526, 527,
                          528, 529, 530, 531, 533, 602, 700, 1051, 1052,
                          1053, 1054, 2551, 2552, 2556, 2557, 2558, 2559,
                          3000, 3001, 3002, 3003, 3004, 3005, 3006, 3007,
                          3008, 3009, 3010, 3011, 3012, 3013, 3014, 3015,
                          3016, 3020, 3021, 3022, 3023, 3024, 5000, 5001,
                          5005, 5006, 6000, 6010, 6011, 9000, 10000),
    'Timeout': (522,),
    'Bad_state': (524,),
    'Too_many_request': (601,),
    'Not_implemented': (2554,)
}

# {'error': 'Invalid Params: Missing [access_token]', 'status': 503}


codes = LookupDict(_codes, name='status_codes')

results = {}

def add_to_results(key, value):
    if key not in results:
        results[key] = [value,]
    else:
        results[key].append(value)
