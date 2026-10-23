# Morphix 1.4.10 — إصلاح تعليق Studio

هذا التحديث يصلح رسالتَي AttributeError اللتين ظهرتا في Morphix 22:

- ShortcutRecorder: `_recording` غير موجود أثناء `QLineEdit::event()`.
- StudioController: الدالة `show_wheel` غير موجودة.

## تطبيق التحديث

1. أغلق كل نسخ Morphix الحالية.
2. افتح ملف تحديث ZIP، وانسخ الملفات **داخل مجلد Morphix** إلى مجلد مشروعك `Morphix 22` مع الموافقة على الاستبدال. احرص ألا تصنع مجلد `Morphix` آخر داخل المشروع.
3. **لا تحذف** `.venv_clean`، ولا تحتاج إلى إعادة تثبيت Python أو PySide6.
4. داخل مجلد `Morphix 22` في Terminal، شغّل:

```bash
.venv_clean/bin/python main.py --studio-window
```

5. جرّب زر **Wheel appearance** ثم **Record a shortcut**. يجب أن تفتح نافذة الإعدادات دون ظهور Traceback. جرّب زر **Quick Wheel**. إن لم يكن Morphix يعمل بالخلفية، ستظهر رسالة لإرشادك إلى تشغيله، وليست حالة تجمد.

لتشغيل خدمة الخلفية من Terminal آخر:

```bash
.venv_clean/bin/python main.py --background
```

وللتحقق التلقائي من النقرات على الماك:

```bash
.venv_clean/bin/python gui_selftest_v1410.py
```

**ملاحظة:** اختبارات البرمجيات نجحت على بيئة البناء، لكن لم نختبر واجهة macOS رسوميًا هنا. لا تدّعي هذه الحزمة أنها ملف `.app` نهائي.
