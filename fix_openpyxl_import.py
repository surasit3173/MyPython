with open('run_full_forensic_pipeline.py', 'r') as f:
    code = f.read()

code = code.replace("from openpyxl.utils import dataframe_to_rows", "from openpyxl.utils.dataframe import dataframe_to_rows")

with open('run_full_forensic_pipeline.py', 'w') as f:
    f.write(code)

print("Import fix applied.")
