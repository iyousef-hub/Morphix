# إصلاح Morphix 1.4.9

اكتشفنا أن كود التشغيل في 1.4.8 كان يُعيد تشغيل الواجهة باستخدام `.venv` القديمة بدل `.venv_clean` التي نجح فيها اختبار Cocoa. أيضًا إضافات Qt كانت مخفية بعلامة `UF_HIDDEN`.

**لنسخة Morphix 21 الموجودة بالفعل:** أغلق نسخ Morphix القديمة، وفك ضغط تحديث v1.4.9 إلى المجلد ذاته مع الاستبدال. لا تمسح `.venv_clean`. ثم جرّب Studio:

```sh
.venv_clean/bin/python main.py --studio-window
```

بعد نجاح Studio، شغّل التطبيق بالخلفية:

```sh
zsh ./Launch_Morphix_Mac.command
```

إذا فشل Studio، افحص سجل الطرفية مباشرة؛ ويمكن تشغيل:

```sh
.venv_clean/bin/python doctor_qt_macos.py
.venv_clean/bin/python doctor_qt_macos.py --fix-hidden
```

هذا الإصدار لم يُجرَّب على macOS داخل بيئة البناء، لكنّه يعالج مشكلتين تم تحديدهما من نتائج جهازك.
