import subprocess
from pathlib import Path

project = Path(r"C:\MyPython\research_controller").resolve()

prompt = r"""
ตรวจสอบและปรับปรุง research_controller ในโฟลเดอร์ปัจจุบันตามข้อกำหนดต่อไปนี้

ข้อจำกัด:
- ห้ามแก้ไขไฟล์ใดนอก C:\MyPython\research_controller
- ห้ามแตะต้องโครงการวิจัยใด ๆ
- ห้ามรันงานวิจัยจริง
- ห้ามรัน pipeline วิเคราะห์ข้อมูลของ CMIP6PrachuapKhiriKhan

เป้าหมาย:
1. controller.py ต้อง resolve project เป็น absolute path ภายใต้ C:\MyPython
2. เมื่อเรียก agy ต้องใช้ --add-dir <absolute_project_path>
3. ห้ามพึ่งพา --project เพื่อเลือก local workspace
4. autonomous mode ต้องใช้ --dangerously-skip-permissions
5. ต้องตรวจว่า project path มีอยู่จริงก่อนเริ่ม task
6. ต้องเก็บ task specification, command metadata, raw AGY output,
   parsed response, exit status และ timestamp ไว้ใน results/<run_id>/
7. หาก workspace verification ไม่ผ่าน ให้หยุดแบบ FAIL-CLOSED
8. ห้ามสร้าง synthetic data หรือ fabricate evidence
9. ห้ามลบหรือแก้ไข evidence ใน project research
10. เพิ่มหรือปรับ unit tests สำหรับ workspace binding และ fail-closed behavior

ขั้นตอน:
- ตรวจโครงสร้างและ source code ปัจจุบันก่อน
- แก้เฉพาะไฟล์ที่จำเป็นภายใน research_controller
- รันเฉพาะ unit tests ของ research_controller
- ห้ามรัน research pipeline

รายงานเฉพาะสิ่งที่ตรวจสอบจริง:
- files changed
- tests run
- tests passed/failed
- exact AGY invocation pattern ที่ controller จะใช้
- unresolved risks
"""

cmd = [
    "agy",
    "-p", prompt,
    "--add-dir", str(project),
    "--dangerously-skip-permissions",
    "--output-format", "json",
]

result = subprocess.run(
    cmd,
    cwd=str(project),
    text=True,
    encoding="utf-8",
    errors="replace",
    capture_output=True,
)

print("=== EXIT CODE ===")
print(result.returncode)

print("=== STDOUT ===")
print(result.stdout)

print("=== STDERR ===")
print(result.stderr)