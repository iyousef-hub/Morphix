# تشغيل Morphix v1.4.8 على macOS

## تحديث مشروعك الحالي (أفضل خيار)
1. اختر Quit Morphix من أيقونة M، وأوقف أي عمليات Python قديمة للمشروع.
2. فك ضغط تحديث v1.4.8 وانسخ محتوياته إلى مجلد Morphix الحالي مع الاستبدال.
3. **لا تحذف** مجلد `.venv` أو ملفات إعداداتك.
4. افتح Terminal في نفس مجلد المشروع، ثم نفّذ:

```bash
zsh ./Launch_Morphix_Mac.command
```

5. اضغط على أيقونة M أعلى الشاشة، واختر `Open Morphix Studio`.

## إن لم يفتح Studio
نفّذ هذه الأوامر من مجلد Morphix نفسه:

```bash
.venv/bin/python doctor_qt_macos.py
cat ~/Library/Logs/Morphix/studio.log | tail -60
```

إذا كانت `Cocoa exists: False` فشغّل:

```bash
.venv/bin/python doctor_qt_macos.py --repair
```

إذا كانت `Cocoa exists: True` لكن Studio لا يزال لا يفتح، جرّب **اختبار التحميل الاختياري**:

```bash
.venv/bin/python doctor_qt_macos.py --probe
```

يمكن أن يسبب الاختبار ظهور تقرير انهيار Python إذا كانت مكتبات Qt الأصلية
معطوبة، لكنه يعمل في عملية مستقلة ولا يشغّل Morphix Studio نفسه.

## سجل المشكلة
`~/Library/Logs/Morphix/studio.log`

لا حاجة لتعطيل Gatekeeper أو حذف Python أو Anaconda أو تغيير إعدادات النظام.
