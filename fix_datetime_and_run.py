with open('update_and_reconcile_all.py', 'r') as f:
    code = f.read()

code = 'import datetime\n' + code

with open('update_and_reconcile_all.py', 'w') as f:
    f.write(code)

print("Added datetime import.")
