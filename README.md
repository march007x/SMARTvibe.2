# SmartVibe — เว็บไซต์อธิบายโปรเจกต์

เว็บหน้าเดียวที่อธิบายโครงงาน **SmartVibe — ระบบตรวจสุขภาพโครงสร้างอาคารรายชั้น
ด้วยความถี่ธรรมชาติและไอโอที** ใช้ได้ 2 กรณี

1. ทีมงานอ่านทบทวนก่อนแข่ง
2. เปิดให้กรรมการและผู้ชมดูหน้างาน โดยไม่ต้องมีคนยืนบรรยาย

## โครงไฟล์

```
index.html          หน้าเว็บทั้งหมด (โครงสร้าง + เนื้อหา)
assets/style.css    ระบบดีไซน์ · ธีมสว่าง/มืด · @media print
assets/app.js       ธีม · overlay เมนู · overlay เนื้อล้วน · แถบความคืบหน้า
vercel.json         ตั้งค่า deploy บน Vercel
robots.txt
```

ไม่มีขั้นตอน build ไม่มี dependency ไม่มี framework
เปิด `index.html` จากเครื่องได้ตรง ๆ โดยไม่ต้องมีเซิร์ฟเวอร์

## ขึ้น Vercel

1. push โฟลเดอร์นี้ขึ้น GitHub repo
2. เข้า vercel.com → **Add New → Project** → เลือก repo นี้
3. Framework Preset เลือก **Other** · Build Command เว้นว่าง · Output Directory เว้นว่าง
4. กด Deploy

พอ push commit ใหม่ Vercel จะ deploy ให้เองอัตโนมัติ

## หมายเหตุเรื่องเนื้อหา

ตัวเลขทุกตัวบนเว็บมาจากเอกสารโครงงานและซอร์สโค้ดจริงใน repo
`march007x/SMARTvibe.2` ไม่มีตัวเลขใดถูกสร้างขึ้นใหม่
