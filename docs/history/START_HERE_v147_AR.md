# Morphix v1.4.7 — إصلاح عدم استجابة Studio للنقر

هذه نسخة مصدرية كاملة. شغّلها في مجلد جديد، ولا تدمجها مع نسخ سابقة.

1) أغلق كل نسخ Morphix من شريط القوائم ومن Terminal (Ctrl+C إن كانت تعمل).
2) افتح Terminal داخل مجلد المشروع ونفّذ:

    zsh ./Launch_Morphix_Mac.command

3) من أيقونة M أعلى الشاشة اختر Open Morphix Studio.
4) جرّب الضغط على Add files أو Customize Wheel أو Wheel appearance.
5) إذا لم تستجب Studio، اختبر نافذتها مستقلة عن الخلفية:

    .venv/bin/python main.py --studio-window

6) للتحقق من أحداث النقر عبر Qt:

    .venv/bin/python gui_selftest_v147.py

من المفترض أن يظهر STUDIO QT CLICK TEST: PASS إذا وصلت النقرات البرمجية للأزرار.
لا يثبت الاختبار البرمجي وحده وصول نقرات الماوس الحقيقية على macOS.

**التغيير:** Studio صار في عملية منفصلة عن العجلة. إغلاق Studio لا يغلق Morphix بالخلفية.
