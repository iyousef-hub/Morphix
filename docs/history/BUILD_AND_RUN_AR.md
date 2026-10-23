# تشغيل Morphix 1.3

## تشغيل الماك بسهولة

1. فك ضغط المشروع.
2. افتح مجلد `Morphix`.
3. افتح `Launch_Morphix_Mac.command` (قد يطلب macOS تأكيد تشغيله). أول مرة تحتاج الإنترنت لتنزيل مكتبات Python للمطور فقط.
4. ستظهر شاشة بداية Morphix ثم أداة التشغيل المصغرة. افتح Studio أو اضغط `⌘ + Shift + M` وأنت محدد ملفات في Finder.
5. من أيقونة M الزرقاء أعلى الشاشة اختر **Conversion Engines · Status** لتتأكد من وجود كل محرك.

لإنتاج نسخة مستخدم مستقلّة `Morphix.app` و`Morphix.dmg`، يجب أن يكون LibreOffice مثبتًا على **جهاز المطور** ثم تشغّل `Build_Morphix_Mac.command`. سيتم نسخه داخل Morphix، ولن يحتاج المستخدم النهائي إلى تثبيته مرة ثانية. تبقى مسؤولية توقيع التطبيق وتوثيقه واختباره على الماك.

## تشغيل Windows

من مجلد Morphix: `py -3 -m pip install -r requirements.txt` ثم `py -3 main.py`.
لإنشاء Windows executable مع كل المكونات، ثبّت LibreOffice على **جهاز بناء Windows** وشغّل `Build_Morphix_Windows.bat`. وزّع مجلد `dist/Morphix` بالكامل لا ملف exe وحده.

## وظائف الإصدار

- Office → PDF: Word وPowerPoint وExcel وصيغ LibreOffice المدعومة.
- PDF → Extract text: يقرأ النص العادي مباشرة، ويستخدم OCR باللغة العربية والإنجليزية للصفحات المصورة.
- PDF → OCR Arabic + English → TXT: يجبر OCR على الصفحات كلها.
- Scanned PDF → Searchable PDF: يُنتج نسخة PDF يمكن البحث فيها وتحديد النص المتعرف عليه.
- ZIP وTAR.GZ: جاهزان مباشرة.
- RAR: يتطلب محرّك إنشاء RAR مرخّصًا؛ لا نستطيع تضمينه مجانًا من دون موافقة صاحب الترخيص. يظهر الخيار غير متاح بدونه.

## الفحص السريع

`python doctor_engines.py`

ملفات اللغات مرفقة داخل `assets/tessdata`. تذكر أن OCR ليس مثاليًا خصوصًا مع صور ضبابية أو كتابة بخط اليد، وأن الحفظ للمستندات في صيغة PDF يعتمد على محرك LibreOffice المضمن أثناء بناء الحزمة.
