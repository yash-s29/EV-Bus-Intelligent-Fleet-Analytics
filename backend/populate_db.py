import pandas as pd
import pymongo
from datetime import datetime
from config import Config

# Connect to MongoDB
client = pymongo.MongoClient(Config.MONGO_URI)
db = client[Config.DB_NAME]

# Load processed data
df = pd.read_csv('../data/processed/cleaned_telemetry.csv')

# Add bus_id (simulate multiple buses)
df['bus_id'] = ['EV' + str(i % 10 + 1).zfill(3) for i in range(len(df))]

# Convert timestamp
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Insert into telemetry_logs
telemetry_data = df.to_dict('records')
db.telemetry_logs.insert_many(telemetry_data)

print(f"Inserted {len(telemetry_data)} telemetry records")

# Create some maintenance records
maintenance_data = [
    {
        "bus_id": f"EV{i:03d}",
        "predicted_soh": 0.8 + (i % 5) * 0.05,
        "maintenance_due": datetime.utcnow(),
        "issues": ["Battery check" if i % 2 == 0 else "Tire rotation"]
    } for i in range(1, 11)
]

db.maintenance_health.insert_many(maintenance_data)
print(f"Inserted {len(maintenance_data)} maintenance records")

print("Data population complete!")