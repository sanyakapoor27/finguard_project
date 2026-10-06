"""
FinGuard CoCopilot - Realistic Financial Dataset Generator
Generates 4 referentially linked tables in FINGUARD_DB.PUBLIC via Snowpark Python.
"""
import uuid
import random
import math
from datetime import datetime, timedelta

from snowflake.snowpark import Session
from snowflake.snowpark.types import (
    StructType, StructField, StringType, FloatType,
    BooleanType, TimestampType, DateType, LongType, DoubleType
)

# --- Session ---
session = Session.builder.config("connection_name", "default").create()
session.sql("USE SCHEMA FINGUARD_DB.PUBLIC").collect()

random.seed(42)

# --- Constants ---
NOW = datetime.utcnow()
NINETY_DAYS_AGO = NOW - timedelta(days=90)
CHANNELS = ["WIRE", "ACH", "CRYPTO", "SWIFT"]
CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "SGD"]
COUNTRIES = [
    "US", "GB", "DE", "JP", "CH", "CA", "AU", "SG", "HK", "BR",
    "IN", "CN", "RU", "NG", "IR", "KP", "AF", "PK", "KY", "PA"
]
HIGH_RISK_COUNTRIES = {"RU", "NG", "IR", "KP", "AF", "PK", "KY", "PA"}
SECTORS = [
    "Technology", "Financial Services", "Healthcare", "Energy",
    "Consumer Discretionary", "Industrials", "Materials",
    "Real Estate", "Utilities", "Telecommunications"
]
RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
RATING_PD_RANGES = {
    "AAA": (0.0001, 0.001), "AA": (0.001, 0.005), "A": (0.005, 0.02),
    "BBB": (0.02, 0.05), "BB": (0.05, 0.15), "B": (0.15, 0.35), "CCC": (0.35, 0.70)
}
AML_RULES = ["Structuring", "Rapid Velocity", "High Risk Country"]
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
STATUSES = ["OPEN", "INVESTIGATING", "CLOSED"]

# --- Generate a pool of Account IDs (shared between TRANSACTIONS and AML_ALERTS) ---
NUM_ACCOUNTS = 5000
ACCOUNT_IDS = [f"ACCT-{i:06d}" for i in range(1, NUM_ACCOUNTS + 1)]

# =============================================================================
# 1. TRANSACTIONS (50,000 rows)
# =============================================================================
print("Generating TRANSACTIONS...")
txn_rows = []
for _ in range(50000):
    ts = NINETY_DAYS_AGO + timedelta(seconds=random.randint(0, 90 * 86400))
    country = random.choice(COUNTRIES)
    channel = random.choice(CHANNELS)
    amount = round(random.lognormvariate(8, 2), 2)  # realistic skewed distribution
    # fraud score: higher for high-risk countries, crypto, and round amounts
    base_fraud = random.betavariate(1.5, 10)
    if country in HIGH_RISK_COUNTRIES:
        base_fraud = min(1.0, base_fraud + random.uniform(0.1, 0.3))
    if channel == "CRYPTO":
        base_fraud = min(1.0, base_fraud + random.uniform(0.05, 0.15))
    fraud_score = round(base_fraud, 4)
    is_flagged = fraud_score > 0.65

    txn_rows.append((
        str(uuid.uuid4()),
        random.choice(ACCOUNT_IDS),
        ts,
        amount,
        random.choice(CURRENCIES),
        f"CP-{random.randint(10000, 99999)}",
        country,
        channel,
        fraud_score,
        is_flagged,
    ))

txn_schema = StructType([
    StructField("TXN_ID", StringType()),
    StructField("ACCOUNT_ID", StringType()),
    StructField("TIMESTAMP", TimestampType()),
    StructField("AMOUNT", DoubleType()),
    StructField("CURRENCY", StringType()),
    StructField("COUNTERPARTY_ID", StringType()),
    StructField("COUNTERPARTY_COUNTRY", StringType()),
    StructField("CHANNEL", StringType()),
    StructField("FRAUD_SCORE", FloatType()),
    StructField("IS_FLAGGED", BooleanType()),
])

txn_df = session.create_dataframe(txn_rows, schema=txn_schema)
txn_df.write.mode("overwrite").save_as_table("FINGUARD_DB.PUBLIC.TRANSACTIONS")
print("  TRANSACTIONS written.")

# =============================================================================
# 2. LIQUIDITY_POSITIONS (365 daily rows)
# =============================================================================
print("Generating LIQUIDITY_POSITIONS...")
liq_rows = []
base_date = NOW.date() - timedelta(days=364)
# Start with base values and add realistic drift
hqla1_base = 500_000_000.0
hqla2a_base = 200_000_000.0
hqla2b_base = 50_000_000.0
outflow_base = 600_000_000.0
inflow_base = 450_000_000.0

for day_offset in range(365):
    snapshot_date = base_date + timedelta(days=day_offset)
    # Sinusoidal seasonality + random walk
    seasonal = math.sin(2 * math.pi * day_offset / 365) * 0.05
    drift = random.gauss(0, 0.01)

    hqla1 = round(hqla1_base * (1 + seasonal + drift), 2)
    hqla2a = round(hqla2a_base * (1 + seasonal * 0.7 + random.gauss(0, 0.015)), 2)
    hqla2b = round(hqla2b_base * (1 + seasonal * 0.5 + random.gauss(0, 0.02)), 2)
    outflows = round(outflow_base * (1 + random.gauss(0, 0.03)), 2)
    inflows = round(inflow_base * (1 + random.gauss(0, 0.025)), 2)

    total_hqla = hqla1 + (hqla2a * 0.85) + (hqla2b * 0.50)  # haircut-adjusted
    net_outflows = max(outflows - (min(inflows, 0.75 * outflows)), 1.0)
    lcr_ratio = round(total_hqla / net_outflows, 4)

    liq_rows.append((
        snapshot_date,
        hqla1, hqla2a, hqla2b,
        outflows, inflows, lcr_ratio,
    ))

liq_schema = StructType([
    StructField("SNAPSHOT_DATE", DateType()),
    StructField("HQLA_LEVEL_1", DoubleType()),
    StructField("HQLA_LEVEL_2A", DoubleType()),
    StructField("HQLA_LEVEL_2B", DoubleType()),
    StructField("EXPECTED_CASH_OUTFLOWS_30D", DoubleType()),
    StructField("EXPECTED_CASH_INFLOWS_30D", DoubleType()),
    StructField("LCR_RATIO", DoubleType()),
])

liq_df = session.create_dataframe(liq_rows, schema=liq_schema)
liq_df.write.mode("overwrite").save_as_table("FINGUARD_DB.PUBLIC.LIQUIDITY_POSITIONS")
print("  LIQUIDITY_POSITIONS written.")

# =============================================================================
# 3. CREDIT_EXPOSURES (5,000 rows)
# =============================================================================
print("Generating CREDIT_EXPOSURES...")
cred_rows = []
# Weight ratings towards investment grade
rating_weights = [5, 10, 20, 30, 20, 10, 5]

for i in range(5000):
    rating = random.choices(RATINGS, weights=rating_weights, k=1)[0]
    pd_lo, pd_hi = RATING_PD_RANGES[rating]
    pd_val = round(random.uniform(pd_lo, pd_hi), 6)
    lgd = round(random.uniform(0.20, 0.65), 4)
    ead = round(random.lognormvariate(16, 1.5), 2)  # realistic EAD distribution
    # RWA = K * EAD, where K is a simplified risk weight
    risk_weight = min(pd_val * lgd * 12.5 * 1.06, 2.5)  # capped at 250%
    rwa = round(ead * risk_weight, 2)

    cred_rows.append((
        f"OBL-{i+1:06d}",
        random.choice(SECTORS),
        ead, pd_val, lgd, rwa, rating,
    ))

cred_schema = StructType([
    StructField("OBLIGOR_ID", StringType()),
    StructField("SECTOR", StringType()),
    StructField("EXPOSURE_AT_DEFAULT", DoubleType()),
    StructField("PROBABILITY_OF_DEFAULT", DoubleType()),
    StructField("LOSS_GIVEN_DEFAULT", DoubleType()),
    StructField("RISK_WEIGHTED_ASSETS", DoubleType()),
    StructField("RATING", StringType()),
])

cred_df = session.create_dataframe(cred_rows, schema=cred_schema)
cred_df.write.mode("overwrite").save_as_table("FINGUARD_DB.PUBLIC.CREDIT_EXPOSURES")
print("  CREDIT_EXPOSURES written.")

# =============================================================================
# 4. AML_ALERTS (1,000 rows) — referencing ACCOUNT_IDs from TRANSACTIONS
# =============================================================================
print("Generating AML_ALERTS...")

# Pull distinct account IDs actually used in transactions for 100% FK consistency
txn_account_ids = [
    row["ACCOUNT_ID"]
    for row in session.table("FINGUARD_DB.PUBLIC.TRANSACTIONS")
        .select("ACCOUNT_ID").distinct().collect()
]

aml_rows = []
for i in range(1000):
    acct = random.choice(txn_account_ids)
    rule = random.choice(AML_RULES)
    # severity correlates with rule type
    if rule == "High Risk Country":
        severity = random.choices(SEVERITIES, weights=[5, 15, 40, 40], k=1)[0]
    elif rule == "Structuring":
        severity = random.choices(SEVERITIES, weights=[10, 30, 40, 20], k=1)[0]
    else:
        severity = random.choices(SEVERITIES, weights=[20, 40, 30, 10], k=1)[0]

    status = random.choices(STATUSES, weights=[30, 40, 30], k=1)[0]

    aml_rows.append((
        f"AML-{i+1:06d}",
        acct,
        rule,
        severity,
        status,
    ))

aml_schema = StructType([
    StructField("ALERT_ID", StringType()),
    StructField("ACCOUNT_ID", StringType()),
    StructField("RULE_TRIGGERED", StringType()),
    StructField("SEVERITY", StringType()),
    StructField("STATUS", StringType()),
])

aml_df = session.create_dataframe(aml_rows, schema=aml_schema)
aml_df.write.mode("overwrite").save_as_table("FINGUARD_DB.PUBLIC.AML_ALERTS")
print("  AML_ALERTS written.")

# =============================================================================
# Verification
# =============================================================================
print("\n=== Row Count Verification ===")
for tbl in ["TRANSACTIONS", "LIQUIDITY_POSITIONS", "CREDIT_EXPOSURES", "AML_ALERTS"]:
    cnt = session.table(f"FINGUARD_DB.PUBLIC.{tbl}").count()
    print(f"  {tbl}: {cnt:,} rows")

# FK consistency check
orphan_count = session.sql("""
    SELECT COUNT(*) AS ORPHAN_COUNT
    FROM FINGUARD_DB.PUBLIC.AML_ALERTS a
    LEFT JOIN (SELECT DISTINCT ACCOUNT_ID FROM FINGUARD_DB.PUBLIC.TRANSACTIONS) t
        ON a.ACCOUNT_ID = t.ACCOUNT_ID
    WHERE t.ACCOUNT_ID IS NULL
""").collect()[0]["ORPHAN_COUNT"]
print(f"\n  FK Orphans (AML_ALERTS → TRANSACTIONS): {orphan_count}")

session.close()
print("\nDone.")
