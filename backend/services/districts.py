"""Maharashtra district reference (name, division, approximate centroid). Administrative
reference only — contains no surveillance figures."""

MAHARASHTRA_DISTRICTS = [
    {"name": "Ahmednagar", "division": "Nashik", "lat": 19.0948, "lng": 74.7480},
    {"name": "Akola", "division": "Amravati", "lat": 20.7002, "lng": 77.0082},
    {"name": "Amravati", "division": "Amravati", "lat": 20.9374, "lng": 77.7796},
    {"name": "Chhatrapati Sambhajinagar", "division": "Marathwada", "lat": 19.8762, "lng": 75.3433},
    {"name": "Beed", "division": "Marathwada", "lat": 18.9891, "lng": 75.7601},
    {"name": "Bhandara", "division": "Nagpur", "lat": 21.1667, "lng": 79.6500},
    {"name": "Buldhana", "division": "Amravati", "lat": 20.5317, "lng": 76.1843},
    {"name": "Chandrapur", "division": "Nagpur", "lat": 19.9615, "lng": 79.2961},
    {"name": "Dhule", "division": "Nashik", "lat": 20.9042, "lng": 74.7749},
    {"name": "Gadchiroli", "division": "Nagpur", "lat": 20.1849, "lng": 80.0029},
    {"name": "Gondia", "division": "Nagpur", "lat": 21.4598, "lng": 80.1961},
    {"name": "Hingoli", "division": "Marathwada", "lat": 19.7198, "lng": 77.1471},
    {"name": "Jalgaon", "division": "Nashik", "lat": 21.0077, "lng": 75.5626},
    {"name": "Jalna", "division": "Marathwada", "lat": 19.8410, "lng": 75.8864},
    {"name": "Kolhapur", "division": "Pune", "lat": 16.7050, "lng": 74.2433},
    {"name": "Latur", "division": "Marathwada", "lat": 18.4088, "lng": 76.5604},
    {"name": "Mumbai City", "division": "Konkan", "lat": 18.9388, "lng": 72.8354},
    {"name": "Mumbai Suburban", "division": "Konkan", "lat": 19.0760, "lng": 72.8777},
    {"name": "Nagpur", "division": "Nagpur", "lat": 21.1458, "lng": 79.0882},
    {"name": "Nanded", "division": "Marathwada", "lat": 19.1383, "lng": 77.3210},
    {"name": "Nandurbar", "division": "Nashik", "lat": 21.3745, "lng": 74.2405},
    {"name": "Nashik", "division": "Nashik", "lat": 20.0110, "lng": 73.7903},
    {"name": "Dharashiv", "division": "Marathwada", "lat": 18.1861, "lng": 76.0419},
    {"name": "Palghar", "division": "Konkan", "lat": 19.6967, "lng": 72.7655},
    {"name": "Parbhani", "division": "Marathwada", "lat": 19.2608, "lng": 76.7748},
    {"name": "Pune", "division": "Pune", "lat": 18.5204, "lng": 73.8567},
    {"name": "Raigad", "division": "Konkan", "lat": 18.5158, "lng": 73.1822},
    {"name": "Ratnagiri", "division": "Konkan", "lat": 16.9902, "lng": 73.3120},
    {"name": "Sangli", "division": "Pune", "lat": 16.8524, "lng": 74.5815},
    {"name": "Satara", "division": "Pune", "lat": 17.6805, "lng": 74.0183},
    {"name": "Sindhudurg", "division": "Konkan", "lat": 16.1180, "lng": 73.6980},
    {"name": "Solapur", "division": "Pune", "lat": 17.6599, "lng": 75.9064},
    {"name": "Thane", "division": "Konkan", "lat": 19.2183, "lng": 72.9781},
    {"name": "Wardha", "division": "Nagpur", "lat": 20.7453, "lng": 78.6022},
    {"name": "Washim", "division": "Amravati", "lat": 20.1110, "lng": 77.1350},
    {"name": "Yavatmal", "division": "Amravati", "lat": 20.3888, "lng": 78.1204}
]

DISTRICT_NAMES = {d["name"].lower(): d["name"] for d in MAHARASHTRA_DISTRICTS}
