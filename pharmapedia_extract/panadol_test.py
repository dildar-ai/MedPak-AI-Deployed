import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect(r"d:\Pak Med AI\pharmapedia_extract\pharmapedia.db")
c = conn.cursor()

SEP  = "=" * 70
LINE = "-" * 70

print(f"\nSEARCHING FOR: Panadol")
print(SEP)

# ── Step 1: All Panadol brand variants ──────────────────────────────────────
c.execute(
    "SELECT bd.NAME, bd.FORM, bd.MG, bd.PACKING, bd.TRADEPRICE, bd.RETIALPRICE, "
    "       b.BNAME, co.NAME as COMPANY, d.NAME as SALT, bd.DID "
    "FROM BRAND_DRUG bd "
    "JOIN BRAND b ON bd.BID = b.BID "
    "LEFT JOIN COMPANY co ON b.CID = co.ID "
    "LEFT JOIN DRUG d ON bd.DID = d.CODE "
    "WHERE bd.NAME LIKE '%Panadol%' OR b.BNAME LIKE '%PANADOL%' "
    "ORDER BY bd.MG, bd.FORM"
)
rows = c.fetchall()
print(f"\nFound {len(rows)} Panadol product variants:\n")
for r in rows:
    print(f"  {r[0]:<30}  {r[2]:<12}  {r[1]:<10}  Pack: {r[3]:<10}  "
          f"Retail: {r[5]:>8} PKR   Salt: {r[8]}")

# ── Step 2: Full drug info for Paracetamol ───────────────────────────────────
print(f"\n{SEP}")
c.execute(
    "SELECT CODE, NAME, INDICATIONS, CONTRAINDICATIONS, EFFECTS, WARNINING, STORAGE "
    "FROM DRUG WHERE NAME LIKE '%Paracetamol%' LIMIT 1"
)
drug = c.fetchone()

if not drug:
    print("No Paracetamol entry found in DRUG table.")
    conn.close()
    sys.exit()

did = drug[0]
print(f"\nGENERIC DRUG: {drug[1]}  (CODE={did})")
print(f"\n[Indications]\n  {drug[2][:400]}...")
print(f"\n[Side Effects]\n  {drug[4][:400]}...")
print(f"\n[Warnings]\n  {drug[5][:300]}...")
print(f"\n[Storage]\n  {drug[6][:200]}")

# ── Step 3: Dosage by age group ──────────────────────────────────────────────
print(f"\n{SEP}")
print("DOSAGE BY AGE GROUP:")

for tbl, label in [("Neonatal", "Neonatal"), ("Paedriatic", "Paediatric"), ("adult", "Adult")]:
    c.execute(
        f"SELECT DOSE, SINGLE, FREQ, ROUTE, INSTRUCTION FROM [{tbl}] WHERE CODE=? LIMIT 3",
        (did,)
    )
    doses = c.fetchall()
    print(f"\n  [{label}]")
    if doses:
        for dose in doses:
            dose_val = dose[0].strip()
            if dose_val:
                print(f"    Dose     : {dose[0]}  (Single: {dose[1]})")
                print(f"    Frequency: {dose[2]}  |  Route: {dose[3]}")
                print(f"    Note     : {dose[4]}")
            else:
                print(f"    {dose[4]}")
    else:
        print("    No data found.")

# ── Step 4: Cheaper alternatives (same salt, sorted by price) ───────────────
print(f"\n{SEP}")
print(f"CHEAPEST ALTERNATIVES (same generic salt as Panadol):\n")

c.execute(
    "SELECT bd.NAME, bd.FORM, bd.MG, bd.RETIALPRICE, bd.PACKING, co.NAME "
    "FROM BRAND_DRUG bd "
    "JOIN BRAND b ON bd.BID = b.BID "
    "LEFT JOIN COMPANY co ON b.CID = co.ID "
    "WHERE bd.DID = ? "
    "  AND bd.RETIALPRICE != '' AND bd.RETIALPRICE != '0' "
    "ORDER BY CAST(REPLACE(bd.RETIALPRICE, ',', '') AS REAL) ASC "
    "LIMIT 10",
    (did,)
)
alts = c.fetchall()
for i, a in enumerate(alts, 1):
    company = (a[5] or "").strip() or "Unknown"
    print(f"  {i:>2}. {a[0]:<28} {a[1]:<10} {a[2]:<12} "
          f"Retail: {a[3]:>8} PKR   Pack: {a[4]:<10}  ({company})")

# ── Step 5: Drug interaction snippet ────────────────────────────────────────
print(f"\n{SEP}")
c.execute("SELECT INTERACTIONS FROM DRUG WHERE CODE=?", (did,))
interactions = c.fetchone()
if interactions and interactions[0]:
    print(f"DRUG INTERACTIONS (first 500 chars):\n  {interactions[0][:500]}...")

print(f"\n{SEP}")

# ── Summary stats ────────────────────────────────────────────────────────────
print("\nDATABASE SUMMARY:")
for tbl in ["BRAND", "BRAND_DRUG", "COMPANY", "DRUG", "Neonatal", "Paedriatic", "adult"]:
    c.execute(f"SELECT COUNT(*) FROM [{tbl}]")
    print(f"  {tbl:<15}: {c.fetchone()[0]:>6,} rows")

conn.close()
print(f"\n{SEP}")
print("Full inspection complete!")
