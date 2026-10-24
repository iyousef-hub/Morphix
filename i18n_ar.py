# -*- coding: utf-8 -*-
"""Arabic interface text for Morphix.

Written to read naturally for Arabic speakers (not a literal translation).
Keys are the English source strings used with tr(). Product names such as
Morphix, Finder, PDF, OCR, ZIP keep their familiar Latin spelling.
"""

AR = {
    # ------------------------------------------------------------------ general
    'Morphix': 'Morphix',
    'Cancel': 'إلغاء',
    'Close': 'إغلاق',
    'Save': 'حفظ',
    'Start': 'ابدأ',
    'Reset': 'إعادة ضبط',
    'Ready': 'جاهز',
    'Unavailable': 'غير متاح',
    'Arabic': 'العربية',
    'English': 'English',
    'Email': 'البريد الإلكتروني',
    'Images': 'صور',
    'Files': 'الملفات',
    'Pages': 'الصفحات',
    'From': 'من',
    'To': 'إلى',
    'Angle': 'الزاوية',
    'Crop': 'قص',
    'Saved': 'تم الحفظ',
    'Custom': 'مخصص',
    'Custom…': 'لون آخر…',
    'Done.': 'اكتمل.',
    'By Yousef': 'من تطوير يوسف',
    'YOUR FILE TOOLKIT': 'أدواتك لكل ملفاتك',
    'Your files, transformed.': 'ملفاتك، بالشكل الذي تريده.',
    'Your file toolkit  ·  Designed by Yousef': 'أدواتك لكل ملفاتك  ·  تصميم يوسف',
    'YOUSEF ALGHAMDI': 'يوسف الغامدي',
    'Developed by Yousef Alghamdi': 'تطوير: يوسف الغامدي',
    'DEVELOPER & CONTACT': 'المطوّر والتواصل',
    'Send an email': 'أرسل بريدًا إلكترونيًا',
    'About Morphix': 'عن Morphix',
    'Morphix — your files, transformed. Private and offline.':
        'Morphix — حوّل ملفاتك كما تريد، بخصوصية تامة ودون اتصال بالإنترنت.',
    '{n} file(s)': '{n} ملف',
    '{n} files': '{n} ملف',
    'Created: {path}': 'تم إنشاء الملف:\n{path}',

    # ------------------------------------------------------------------ Action Hub names
    'Action Hub': 'مركز الأدوات',
    'Show the Action Hub': 'إظهار مركز الأدوات',
    'Hide the Action Hub': 'إخفاء مركز الأدوات',
    'Action Hub appearance': 'شكل مركز الأدوات',
    'Customize the Action Hub': 'خصّص مركز الأدوات',
    'Try the Action Hub with files…': 'جرّب مركز الأدوات على ملفات…',
    'Choose files for the Action Hub': 'اختر ملفات لمركز الأدوات',
    'Choose files for the Action Hub…': 'اختر ملفات لمركز الأدوات…',
    'Reset the Action Hub appearance': 'استعادة الشكل الافتراضي لمركز الأدوات',
    'The Action Hub appearance was reset to its defaults.': 'عاد مركز الأدوات إلى شكله الافتراضي.',
    'SHOW THE ACTION HUB': 'اختصار إظهار مركز الأدوات',
    'Wheel': 'عجلة',
    'Square': 'مربّع',
    'Rectangle': 'مستطيل',
    'Bar': 'شريط',
    'Next to the mouse pointer': 'بجانب مؤشر الفأرة',
    'Center of the screen': 'وسط الشاشة',
    'Top of the screen': 'أعلى الشاشة',
    'Bottom of the screen': 'أسفل الشاشة',
    'Left edge': 'الحافة اليسرى',
    'Right edge': 'الحافة اليمنى',
    'Where I last dragged it': 'آخر مكان سحبته إليه',
    'Drag to move': 'اسحب للتحريك',
    'More tools': 'أدوات أخرى',
    'Hide': 'إخفاء',
    'Select files in Finder': 'حدّد ملفات في Finder',
    'Select one or more files in Finder, then hover here or press your shortcut.':
        'حدّد ملفًا أو أكثر في Finder، ثم مرّر الفأرة هنا أو اضغط الاختصار.',

    # ------------------------------------------------------------------ tray / menus
    'Morphix  ·  Running in background': 'Morphix  ·  يعمل في الخلفية',
    'Cancel current task': 'إلغاء المهمة الحالية',
    'Simple actions menu · Choose files…': 'قائمة الأدوات البسيطة · اختر ملفات…',
    'Open Morphix Studio': 'فتح استوديو Morphix',
    'Open Studio': 'فتح الاستوديو',
    'Settings…': 'الإعدادات…',
    'Help & diagnostics': 'المساعدة والتشخيص',
    'Check the Finder selection': 'فحص الملفات المحددة في Finder',
    'Status of conversion engines': 'حالة محركات التحويل',
    'Shortcut not working? Allow access…': 'الاختصار لا يعمل؟ امنح الإذن…',
    'Quit Morphix': 'إنهاء Morphix',
    'Morphix · Select files, then press your shortcut': 'Morphix · حدّد ملفاتك ثم اضغط الاختصار',
    'Add more files…': 'إضافة ملفات أخرى…',
    'Add files to the selection': 'أضف ملفات إلى التحديد',
    'Refresh Finder selection': 'تحديث الملفات المحددة من Finder',
    'Clear selection': 'إلغاء التحديد',
    'Selection cleared. Choose new files to continue.': 'أُلغي التحديد. اختر ملفات جديدة للمتابعة.',
    'Choose files for Morphix actions': 'اختر ملفات لأدوات Morphix',
    'No files selected.': 'لم تحدّد أي ملف.',
    'Select a file first.': 'حدّد ملفًا أولًا.',
    'Select one or more files in Finder, then try again.': 'حدّد ملفًا أو أكثر في Finder، ثم حاول مرة أخرى.',
    'Select one or more files in Studio first.': 'حدّد ملفًا أو أكثر في الاستوديو أولًا.',
    'Morphix · Finder selection': 'Morphix · الملفات المحددة في Finder',
    'Finder did not answer. Check the Automation permission for Morphix.':
        'لم يستجب Finder. تأكد من منح Morphix إذن «الأتمتة» (Automation).',
    'Finder selection unavailable': 'تعذّرت قراءة الملفات المحددة في Finder',
    'Found {n} file(s):': 'وُجد {n} ملف:',
    'No selected files were found.\n\nSelect one or more files in a Finder window, then press your shortcut. '
    'macOS may ask for permission under Privacy & Security → Automation.':
        'لم يُعثر على ملفات محددة.\n\nحدّد ملفًا أو أكثر داخل نافذة Finder ثم اضغط الاختصار. '
        'قد يطلب macOS إذنًا من: الخصوصية والأمن ← الأتمتة.',
    'Morphix · Ready': 'Morphix · جاهز',
    'Morphix is running': 'Morphix يعمل الآن',
    'Morphix keeps running in the background after you close Studio. Look for the blue M in the menu bar.':
        'يبقى Morphix يعمل في الخلفية بعد إغلاق الاستوديو. ستجد أيقونة M الزرقاء في شريط القوائم.',
    '1. Select files in Finder.\n2. Press your shortcut to open the Action Hub.\n3. Use the blue M menu for settings, or to quit.':
        '١. حدّد ملفاتك في Finder.\n٢. اضغط الاختصار لفتح مركز الأدوات.\n٣. من قائمة M الزرقاء تصل إلى الإعدادات أو تُنهي البرنامج.',
    'Keep running in the background': 'استمر في العمل بالخلفية',
    'Morphix is busy': 'Morphix مشغول',
    'Wait for the current task to finish, or cancel it from the M menu.':
        'انتظر حتى تنتهي المهمة الحالية، أو ألغِها من قائمة M.',
    'Working on: {task}…': 'جارٍ العمل: {task}…',
    'Morphix · Done': 'Morphix · اكتمل',
    '{n} file(s) saved next to the originals.': 'حُفظ {n} ملف بجانب الملفات الأصلية.',
    'Morphix · Something went wrong': 'Morphix · حدثت مشكلة',
    'Morphix · The task could not be completed': 'Morphix · تعذّر إكمال المهمة',
    'Cancelled. Speech → Text continues where it stopped next time you run it on the same file.':
        'أُلغيت المهمة. عند تشغيل «تحويل الكلام إلى نص» على الملف نفسه، سيكمل من حيث توقف.',
    'Morphix · A task is running': 'Morphix · توجد مهمة قيد التنفيذ',
    'A task is still running. Cancel it and quit?\n\nSpeech → Text keeps its progress and continues next time.':
        'ما زالت هناك مهمة قيد التنفيذ. هل تريد إلغاءها وإنهاء البرنامج؟\n\n'
        'يحتفظ «تحويل الكلام إلى نص» بما أنجزه، ويكمل في المرة القادمة.',
    'A task is still running. Cancel it and close Studio?\n\nSpeech → Text keeps its progress and continues next time.':
        'ما زالت هناك مهمة قيد التنفيذ. هل تريد إلغاءها وإغلاق الاستوديو؟\n\n'
        'يحتفظ «تحويل الكلام إلى نص» بما أنجزه، ويكمل في المرة القادمة.',
    'Morphix · Editor unavailable': 'Morphix · المحرر غير متاح',
    'Morphix · PDF tools unavailable': 'Morphix · أدوات PDF غير متاحة',
    'Run Launch_Morphix_Mac.command again to repair the installation.':
        'شغّل الملف Launch_Morphix_Mac.command مرة أخرى لإصلاح التثبيت.',
    'Studio could not start (code {code}). Details: {log}': 'تعذّر فتح الاستوديو (الرمز {code}). التفاصيل في: {log}',
    'Morphix is not running in the background. Open Morphix from your Applications folder.':
        'Morphix لا يعمل في الخلفية حاليًا. افتحه من مجلد التطبيقات (Applications).',

    # ------------------------------------------------------------------ shortcut / permission
    'Shortcut unavailable': 'الاختصار غير متاح',
    'Use the Morphix menu instead.': 'استخدم قائمة Morphix بدلًا منه.',
    'Morphix · Allow the shortcut': 'Morphix · اسمح بعمل الاختصار',
    'System Settings → Privacy & Security → Accessibility → turn on Morphix.':
        'إعدادات النظام ← الخصوصية والأمن ← تسهيلات الاستخدام ← فعّل Morphix.',
    'Shortcut is ready. Select files in Finder and press it.': 'الاختصار جاهز. حدّد ملفاتك في Finder ثم اضغطه.',
    'Click, then press a modifier and a key. Esc cancels.': 'انقر هنا، ثم اضغط مفتاح تعديل مع مفتاح آخر. للإلغاء اضغط Esc.',
    'Press your shortcut…': 'اضغط الاختصار الآن…',
    'That key is not supported — try a letter, Delete or an F-key': 'هذا المفتاح غير مدعوم — جرّب حرفًا أو Delete أو أحد مفاتيح F',
    'Hold ⌘ / Ctrl / Option / Shift, then press a key': 'اضغط باستمرار ⌘ أو Ctrl أو Option أو Shift، ثم اضغط مفتاحًا',
    'Keyboard shortcut': 'اختصار لوحة المفاتيح',
    'Click the box, then press the keys you want. It works the same whether your keyboard is set to Arabic or English.':
        'انقر على المربع ثم اضغط المفاتيح التي تريدها. يعمل الاختصار بالطريقة نفسها سواء كانت لوحة المفاتيح بالعربية أو بالإنجليزية.',
    'Examples: ⌘ Command + Shift + M, Option + M, Ctrl + Delete. Press Esc to cancel.':
        'أمثلة: ⌘ Command + Shift + M، أو Option + M، أو Ctrl + Delete. للإلغاء اضغط Esc.',
    'Restore default': 'استعادة الافتراضي',
    'Morphix listens to the physical key position, not the letter it types, so switching keyboard languages never breaks the shortcut. '
    'macOS needs Accessibility permission once for shortcuts to work.':
        'يعتمد Morphix على موضع المفتاح في لوحة المفاتيح لا على الحرف الذي يكتبه، لذلك لا يتأثر الاختصار بتغيير لغة الكتابة. '
        'يحتاج macOS إلى منح إذن «تسهيلات الاستخدام» مرة واحدة حتى تعمل الاختصارات.',
    'Open Accessibility settings': 'افتح إعدادات تسهيلات الاستخدام',
    'Finish recording': 'أكمل تسجيل الاختصار',
    'Press a key while holding a modifier, or press Esc to cancel.': 'اضغط مفتاحًا مع مفتاح تعديل، أو اضغط Esc للإلغاء.',
    'Invalid shortcut': 'اختصار غير صالح',
    'Hold a modifier key, then press a letter, Delete or a function key.':
        'اضغط باستمرار مفتاح تعديل (مثل ⌘ أو Ctrl)، ثم اضغط حرفًا أو Delete أو أحد مفاتيح F.',

    # ------------------------------------------------------------------ engines status
    'Morphix · Conversion engines': 'Morphix · محركات التحويل',
    'PDF & images': 'ملفات PDF والصور',
    'Arabic + English OCR': 'التعرّف على النص بالعربية والإنجليزية (OCR)',
    'Language data missing': 'ملفات اللغة مفقودة',
    'Office → PDF': 'مستندات Office ← PDF',
    'Needs LibreOffice': 'يحتاج إلى LibreOffice',
    'Speech → Text (offline)': 'تحويل الكلام إلى نص (دون إنترنت)',
    'ZIP and TAR.GZ': 'ضغط ZIP و TAR.GZ',
    'RAR creation': 'إنشاء ملفات RAR',
    'Licensed RAR program found': 'تم العثور على برنامج RAR مرخّص',
    'Needs a separately licensed RAR program': 'يحتاج إلى برنامج RAR مرخّص بشكل مستقل',
    'RAR needs a separately licensed RAR program. ZIP and TAR.GZ work without it.':
        'إنشاء RAR يحتاج إلى برنامج RAR مرخّص بشكل مستقل. أما ZIP و TAR.GZ فتعمل دونه.',
    'Engine not installed (run Launch_Morphix_Mac.command)': 'المحرك غير مثبّت (شغّل Launch_Morphix_Mac.command)',
    'No model downloaded yet (Studio → Speech models)': 'لم يُنزَّل أي نموذج بعد (الاستوديو ← نماذج الكلام)',

    # ------------------------------------------------------------------ Studio
    'Morphix — Studio': 'استوديو Morphix',
    'WORKSPACE': 'مساحة العمل',
    'SETTINGS': 'الإعدادات',
    'Files & tools': 'الملفات والأدوات',
    'Speech models': 'نماذج تحويل الكلام',
    'Language': 'اللغة',
    'About & contact': 'عن البرنامج والتواصل',
    'About': 'عن البرنامج',
    'RUNNING IN THE BACKGROUND': 'يعمل في الخلفية',
    'Closing Studio keeps the Action Hub and shortcut working.': 'إغلاق الاستوديو لا يوقف مركز الأدوات ولا الاختصار.',
    'Close Studio': 'إغلاق الاستوديو',
    'Your files': 'ملفاتك',
    'Add files, pick a tool, and Morphix does the rest — all on this computer.':
        'أضف ملفاتك، واختر الأداة، ودع الباقي على Morphix — وكل شيء يتم على جهازك.',
    'PRIVATE & OFFLINE': 'خاص ودون إنترنت',
    'Your files, one shortcut away.': 'ملفاتك على بُعد اختصار واحد.',
    'Select files anywhere, then press': 'حدّد ملفاتك من أي مكان، ثم اضغط',
    'Add files': 'إضافة ملفات',
    'Remove selected': 'حذف المحدد من القائمة',
    'Clear list': 'تفريغ القائمة',
    'All tools…': 'كل الأدوات…',
    'Drop files here, or use Add files': 'أفلت الملفات هنا، أو استخدم «إضافة ملفات»',
    'Drag files here from any folder': 'اسحب ملفاتك إلى هنا من أي مجلد',
    'Tools for these files': 'الأدوات المناسبة لهذه الملفات',
    'Add files to see the tools that fit them.': 'أضف ملفات لتظهر لك الأدوات المناسبة لها.',
    'Choose a tool. Select some files in the list to work on them only.':
        'اختر الأداة. وإن أردت العمل على بعض الملفات فقط، حدّدها في القائمة.',
    'ACTIVITY  ·  Everything stays on your computer': 'النشاط  ·  كل شيء يبقى على جهازك',
    'Ready. Drop files to get started.': 'جاهز. أفلت ملفاتك للبدء.',
    'Show in Finder': 'إظهار في Finder',
    'Show in folder': 'إظهار في المجلد',
    'Choose files': 'اختر الملفات',
    'Where should the results be saved?': 'أين تريد حفظ الملفات الناتجة؟',
    '{n} file(s) created:': 'تم إنشاء {n} ملف:',
    'Something went wrong:': 'حدثت مشكلة:',
    'Choose pages': 'اختر الصفحات',
    'Pages (for example 1-3, 5):': 'الصفحات (مثال: 1-3، 5):',
    'How much to trim from each edge (%):': 'مقدار القص من كل حافة (٪):',
    'Resize images': 'تغيير حجم الصور',
    'Longest side (pixels):': 'طول الضلع الأطول (بالبكسل):',
    'Morphix · Speech models': 'Morphix · نماذج تحويل الكلام',

    # ------------------------------------------------------------------ action names (Studio / menus)
    'Visual PDF editor': 'تحرير PDF بصريًا',
    'Visual image editor': 'تحرير الصورة بصريًا',
    'Merge to PDF': 'دمج في ملف PDF',
    'Merge to PDF + compress': 'دمج في PDF مع الضغط',
    'Extract PDF page range': 'استخراج نطاق من الصفحات',
    'Separate PDF into multiple parts': 'تقسيم PDF إلى عدة أجزاء',
    'Optimize PDF': 'ضغط ملف PDF',
    'Rotate PDF 90°': 'تدوير PDF ‏90°',
    'PDF pages → PNG': 'صفحات PDF ← صور PNG',
    'PDF → PNG (ZIP for multi-page)': 'PDF ← صور PNG (ملف ZIP إذا تعددت الصفحات)',
    'PDF → JPG (ZIP for multi-page)': 'PDF ← صور JPG (ملف ZIP إذا تعددت الصفحات)',
    'Crop PDF pages (margins)': 'قص هوامش صفحات PDF',
    'Remove PDF pages': 'حذف صفحات من PDF',
    'Images → single PDF': 'الصور ← ملف PDF واحد',
    'Images → PNG': 'الصور ← PNG',
    'Images → JPG': 'الصور ← JPG',
    'Images → WebP': 'الصور ← WebP',
    'Resize images (max 1920 px)': 'تغيير حجم الصور',
    'Compress images (JPEG)': 'ضغط الصور (JPEG)',
    'Rotate images 90°': 'تدوير الصور ‏90°',
    'Images → grayscale': 'الصور ← أبيض وأسود',
    'Crop image borders by percentage': 'قص حواف الصور بنسبة مئوية',
    'Join videos → MP4': 'دمج الفيديوهات ← MP4',
    'Videos → MP4': 'الفيديو ← MP4',
    'Extract audio → MP3': 'استخراج الصوت ← MP3',
    'Audio → MP3': 'الصوت ← MP3',
    'Merge audio tracks → MP3': 'دمج المقاطع الصوتية ← MP3',
    'Office documents → PDF': 'مستندات Office ← PDF',
    'Create ZIP archive': 'إنشاء ملف ZIP',
    'Create RAR archive (licensed engine)': 'إنشاء ملف RAR (يحتاج برنامجًا مرخّصًا)',
    'Create TAR.GZ archive': 'إنشاء ملف TAR.GZ',
    'PDF → Extract text (auto OCR)': 'PDF ← استخراج النص (مع OCR تلقائي)',
    'OCR → Text file (Arabic + English)': 'OCR ← ملف نصي (عربي وإنجليزي)',
    'OCR · Make the PDF searchable': 'OCR · جعل ملف PDF قابلًا للبحث',
    'Images → Extract text (Arabic + English OCR)': 'الصور ← استخراج النص (OCR عربي وإنجليزي)',
    'Speech → Text (Arabic / English, offline)': 'تحويل الكلام إلى نص (عربي / إنجليزي، دون إنترنت)',

    # ------------------------------------------------------------------ short hub labels
    'To PNG': 'إلى PNG',
    'To JPG': 'إلى JPG',
    'To WebP': 'إلى WebP',
    'To MP4': 'إلى MP4',
    'To MP3': 'إلى MP3',
    'To PDF': 'إلى PDF',
    'Compress': 'ضغط',
    'Extract range': 'استخراج صفحات',
    'Separate PDF': 'تقسيم PDF',
    'Extract text': 'استخراج النص',
    'Merge + Compress': 'دمج وضغط',
    'Edit PDF': 'تحرير PDF',
    'Crop & rotate': 'قص وتدوير',
    'Make PDF': 'إنشاء PDF',
    'Resize': 'تغيير الحجم',
    'Extract audio': 'استخراج الصوت',
    'Merge videos': 'دمج الفيديو',
    'Merge audio': 'دمج الصوت',
    'ZIP files': 'ضغط ZIP',
    'TAR.GZ': 'TAR.GZ',
    'RAR (licensed)': 'RAR (مرخّص)',
    'OCR': 'OCR',
    'OCR → Text file': 'OCR ← ملف نصي',
    'Speech → Text': 'الكلام ← نص',
    'Convert speech to text': 'تحويل الكلام إلى نص',

    # ------------------------------------------------------------------ file-type profiles
    'One PDF': 'ملف PDF واحد',
    'PDF + Images': 'PDF مع صور',
    'Multiple PDFs': 'عدة ملفات PDF',
    'One image': 'صورة واحدة',
    'Multiple images': 'عدة صور',
    'One video': 'فيديو واحد',
    'Multiple videos': 'عدة فيديوهات',
    'One audio': 'مقطع صوتي واحد',
    'Multiple audio': 'عدة مقاطع صوتية',
    'Office files': 'مستندات Office',
    'Mixed files': 'ملفات متنوعة',

    # ------------------------------------------------------------------ settings window
    'Morphix — Settings': 'Morphix — الإعدادات',
    'File actions': 'أدوات كل نوع ملف',
    'Startup & background': 'التشغيل والعمل في الخلفية',
    'The preview updates as you go. Press Save to apply.': 'تتحدث المعاينة فورًا. اضغط «حفظ» لاعتماد التغييرات.',
    'The Action Hub shows the right tools for the files you select. Choose its shape, where it appears, and whether it stays on screen.':
        'يعرض لك مركز الأدوات الأدوات المناسبة للملفات التي تحددها. اختر شكله، ومكان ظهوره، وهل يبقى ظاهرًا على الشاشة.',
    'SHAPE': 'الشكل',
    'LIVE PREVIEW': 'معاينة مباشرة',
    'Live preview': 'معاينة مباشرة',
    'WHERE IT APPEARS': 'مكان الظهور',
    'WHEN IT IS VISIBLE': 'وقت الظهور',
    'Only when I press the shortcut': 'عند الضغط على الاختصار فقط',
    'Always on screen (it updates when your mouse moves over it)':
        'ظاهر دائمًا على الشاشة (يتحدّث عندما تمرّر الفأرة فوقه)',
    'SIZE': 'الحجم',
    'BACKGROUND OPACITY': 'شفافية الخلفية',
    'EDGE GLOW': 'توهج الحواف',
    'OPENING ANIMATION': 'حركة الظهور',
    'ACCENT COLOR': 'اللون المميز',
    'Choose an accent color': 'اختر اللون المميز',
    'Choose which tools appear for each file type': 'اختر الأدوات التي تظهر لكل نوع من الملفات',
    'For each kind of file, tick the tools you want in the Action Hub and drag them into your preferred order. '
    'The wheel shows up to 6, the other shapes up to 8 or 9; everything else stays under “More tools”.':
        'لكل نوع من الملفات، ضع علامة على الأدوات التي تريدها في مركز الأدوات، ثم اسحبها لترتيبها كما تحب. '
        'تعرض العجلة حتى ٦ أدوات، وبقية الأشكال حتى ٨ أو ٩، وما تبقى تجده في «أدوات أخرى».',
    'FILE TYPE': 'نوع الملف',
    'DRAG TO REORDER · TICK TO SHOW': 'اسحب لتغيير الترتيب · ضع علامة لإظهار الأداة',
    '{n} selected · {shape} shows up to {max}': 'اخترت {n} · شكل «{shape}» يعرض حتى {max}',
    'Morphix lives quietly in the menu bar. Studio opens only when you ask for it.':
        'يعمل Morphix بهدوء من شريط القوائم، ولا يُفتح الاستوديو إلا عندما تطلبه.',
    'Start Morphix automatically when I log in': 'شغّل Morphix تلقائيًا عند تسجيل الدخول',
    'Only the background helper starts — Studio stays closed until you open it.':
        'يبدأ العمل في الخلفية فقط، ويبقى الاستوديو مغلقًا حتى تفتحه بنفسك.',
    'Closing Studio does not stop Morphix. To stop it completely, choose “Quit Morphix” from the blue M menu.':
        'إغلاق الاستوديو لا يوقف Morphix. لإيقافه تمامًا اختر «إنهاء Morphix» من قائمة M الزرقاء.',
    'Choose the language of the whole app. Morphix restarts to apply it.':
        'اختر لغة البرنامج بالكامل. سيعيد Morphix تشغيل نفسه لتطبيقها.',
    'In Arabic the interface is arranged from right to left.': 'في العربية تُرتَّب الواجهة من اليمين إلى اليسار.',
    'Change language': 'تغيير اللغة',
    'Morphix will restart in the new language. Continue?': 'سيُعاد تشغيل Morphix باللغة الجديدة. هل تريد المتابعة؟',

    # ------------------------------------------------------------------ compression
    'Morphix · Compression': 'Morphix · الضغط',
    'Compression': 'ضغط الحجم',
    'Original size:': 'الحجم الأصلي:',
    'Compression strength': 'قوة الضغط',
    'Light · Best quality': 'خفيف · أفضل جودة',
    'Balanced · Recommended': 'متوازن · الخيار المقترح',
    'Strong · Much smaller': 'قوي · حجم أصغر بكثير',
    'Maximum · Very small (quality drops)': 'أقصى · حجم صغير جدًا (تقل الجودة)',
    'Extreme · Smallest possible': 'فائق · أصغر حجم ممكن',
    'Also reduce image dimensions for a smaller file': 'صغّر أبعاد الصور أيضًا للحصول على حجم أقل',
    'Black & white (smaller, good for text documents)': 'أبيض وأسود (حجم أقل، ومناسب للمستندات النصية)',
    'Saved as JPEG at quality {q}/95. Stronger levels look softer; transparent areas become white. Your original is never changed.':
        'تُحفظ الصور بصيغة JPEG بجودة {q} من 95. كلما زاد الضغط قلّت الحدة، وتتحول المناطق الشفافة إلى الأبيض. '
        'ملفك الأصلي لا يتغير أبدًا.',
    'Extreme: every page is redrawn as a compressed image. The file becomes much smaller, but text can no longer be selected or searched — '
    'run OCR on the result if you need that. Your original is never changed.':
        'الضغط الفائق: تتحول كل صفحة إلى صورة مضغوطة، فيصغر الملف كثيرًا، لكن لن تستطيع تحديد النص أو البحث فيه — '
        'وإن احتجت ذلك فشغّل OCR على الملف الناتج. ملفك الأصلي لا يتغير أبدًا.',
    'Images inside the PDF are reduced; text stays sharp and selectable. For an even smaller file, move the slider to the far end. '
    'Your original is never changed.':
        'تُصغَّر الصور داخل ملف PDF، ويبقى النص واضحًا وقابلًا للتحديد. ولحجم أصغر من ذلك، حرّك المؤشر إلى أقصى الطرف. '
        'ملفك الأصلي لا يتغير أبدًا.',
    'Lossless clean-up only: nothing visible changes. Your original is never changed.':
        'تنظيف داخلي فقط دون أي فقد في الجودة، فلا يتغير شيء مما تراه. ملفك الأصلي لا يتغير أبدًا.',
    'The final size is shown when the file is saved.': 'يظهر الحجم النهائي بعد حفظ الملف.',
    'Large image — the exact size appears after saving.': 'الصورة كبيرة — يظهر حجمها الدقيق بعد الحفظ.',
    'First image:': 'الصورة الأولى:',
    'No preview for this image.': 'لا تتوفر معاينة لهذه الصورة.',

    # ------------------------------------------------------------------ page ranges / merge
    'Morphix · Separate PDF': 'Morphix · تقسيم PDF',
    'Morphix · Extract pages': 'Morphix · استخراج صفحات',
    'Extract pages': 'استخراج الصفحات',
    'This PDF has {n} pages. Choose page numbers from 1 to {n}.': 'يحتوي الملف على {n} صفحة. اختر أرقام الصفحات من 1 إلى {n}.',
    '+ Add another part': '+ إضافة جزء آخر',
    'Part {n}': 'الجزء {n}',
    'Remove this part': 'حذف هذا الجزء',
    'No more parts': 'لا يمكن إضافة المزيد',
    'There cannot be more parts than pages.': 'لا يمكن أن يزيد عدد الأجزاء على عدد الصفحات.',
    'Adjust the last part': 'عدّل الجزء الأخير',
    'The last part has only one page. Shorten or remove another part first.':
        'الجزء الأخير صفحة واحدة فقط. قصّر جزءًا آخر أو احذفه أولًا.',
    'Keep one part': 'يجب إبقاء جزء واحد',
    'At least one page range is required.': 'يجب تحديد نطاق صفحات واحد على الأقل.',
    'Check the page ranges': 'راجع نطاقات الصفحات',
    'Select one PDF': 'حدّد ملف PDF واحدًا',
    'Select a single PDF for page tools.': 'أدوات الصفحات تعمل على ملف PDF واحد فقط.',
    'Morphix · Merge order': 'Morphix · ترتيب الدمج',
    'Arrange the files in the final PDF': 'رتّب الملفات في ملف PDF النهائي',
    'The top file comes first. Each PDF adds all of its pages and each image adds one page. '
    'Finder does not always keep the order you clicked in, so please check the list.':
        'الملف الأعلى يأتي أولًا. كل ملف PDF يُضاف بجميع صفحاته، وكل صورة تصبح صفحة واحدة. '
        'لا يحتفظ Finder دائمًا بترتيب نقراتك، لذا راجع القائمة قبل الدمج.',
    'Move up': 'نقل لأعلى',
    'Move down': 'نقل لأسفل',
    'Merge in this order': 'ادمج بهذا الترتيب',

    # ------------------------------------------------------------------ visual editors
    'Password-protected PDF is not supported by the visual editor.': 'المحرر البصري لا يدعم ملفات PDF المحمية بكلمة مرور.',
    'Morphix · PDF Visual Editor': 'Morphix · محرر PDF البصري',
    'Drag pages to reorder · Select a page to preview · Draw a rectangle to crop':
        'اسحب الصفحات لترتيبها · اختر صفحة لمعاينتها · ارسم مستطيلًا للقص',
    'Rotate 90°': 'تدوير ‏90°',
    'Remove page': 'حذف الصفحة',
    'Crop selection': 'قص التحديد',
    'Reset crop': 'إلغاء القص',
    'Save PDF as…': 'حفظ PDF باسم…',
    'Cannot remove': 'لا يمكن الحذف',
    'A PDF must contain at least one page.': 'يجب أن يحتوي ملف PDF على صفحة واحدة على الأقل.',
    'Drag a rectangle over the page preview first.': 'ارسم مستطيلًا فوق معاينة الصفحة أولًا.',
    'Crop set': 'تم تحديد القص',
    'Crop area saved for this page. Click Save PDF as… to export.': 'حُفظت منطقة القص لهذه الصفحة. اضغط «حفظ PDF باسم…» للتصدير.',
    'Save edited PDF': 'حفظ ملف PDF المعدَّل',
    'Choose a new filename': 'اختر اسمًا جديدًا للملف',
    'Do not overwrite the original PDF.': 'لا يمكن الحفظ فوق ملف PDF الأصلي.',
    'Export failed': 'تعذّر التصدير',
    'Morphix · Crop & Straighten': 'Morphix · القص والتعديل',
    'Drag the crop corners or draw a new rectangle · Straighten freely · Original is preserved':
        'اسحب زوايا القص أو ارسم مستطيلًا جديدًا · عدّل الميلان بحرية · يبقى الأصل كما هو',
    'Crop to selected rectangle': 'قص حسب المستطيل المحدد',
    'Clear crop': 'إلغاء القص',
    'Save edited image as…': 'حفظ الصورة المعدّلة باسم…',
    'Save edited image': 'حفظ الصورة المعدّلة',
    'Morphix · Quick Crop & Rotate': 'Morphix · قص وتدوير سريع',
    'Save Copy': 'حفظ نسخة',
    'Save alongside the original without overwriting it': 'تُحفظ بجانب الأصل دون الكتابة فوقه',

    # ------------------------------------------------------------------ speech to text
    'Morphix · Speech → Text': 'Morphix · تحويل الكلام إلى نص',
    'Download a speech model once. After that, Arabic and English transcription works completely offline.':
        'نزّل نموذج الكلام مرة واحدة فقط، وبعدها يعمل تحويل الكلام العربي والإنجليزي إلى نص دون أي اتصال بالإنترنت.',
    'Accuracy': 'الدقة',
    'Detect automatically (Arabic / English)': 'تحديد اللغة تلقائيًا (عربي / إنجليزي)',
    'Fast (small model)': 'سريع (نموذج صغير)',
    'Balanced (large-v3-turbo)': 'متوازن (large-v3-turbo)',
    'Most accurate (large-v3)': 'الأعلى دقة (large-v3)',
    'Text (.txt)': 'نص (.txt)',
    'Text + times': 'نص مع التوقيت',
    'Subtitles (.srt)': 'ترجمة مرئية (.srt)',
    'WebVTT': 'WebVTT',
    'Download this model (one time)': 'تنزيل هذا النموذج (مرة واحدة)',
    'For Arabic, “Most accurate” gives the best results; it is slower and needs about 3 GB. '
    'Clear recordings in Modern Standard Arabic work best — strong dialects and background noise lower accuracy.':
        'للعربية، يعطي خيار «الأعلى دقة» أفضل النتائج، لكنه أبطأ ويحتاج نحو 3 GB. '
        'أفضل النتائج تكون مع التسجيلات الواضحة بالفصحى، أما اللهجات القوية والضوضاء فتقلل الدقة.',
    'Runs 100% on this computer. Long recordings (hours) are processed in parts; if you cancel or the Mac sleeps, '
    'run it again on the same file to continue.':
        'يعمل بالكامل على جهازك. التسجيلات الطويلة (ساعات) تُعالَج على أجزاء؛ وإن ألغيت العملية أو نام الجهاز، '
        'شغّلها مرة أخرى على الملف نفسه وستكمل من حيث توقفت.',
    'The speech engine is not installed. Run Launch_Morphix_Mac.command once while connected to the internet.':
        'محرك تحويل الكلام غير مثبّت. شغّل Launch_Morphix_Mac.command مرة واحدة وأنت متصل بالإنترنت.',
    'Model installed — works offline.': 'النموذج مثبّت — يعمل دون إنترنت.',
    'This model is not downloaded yet ({size}). Internet is needed only for this one-time download.':
        'لم يُنزَّل هذا النموذج بعد (حجمه {size}). تحتاج الإنترنت لهذا التنزيل فقط، ولمرة واحدة.',
    'Download failed': 'تعذّر التنزيل',
    'Downloading the speech model ({size}) — one time only…': 'جارٍ تنزيل نموذج الكلام ({size}) — لمرة واحدة فقط…',
    'The model could not be downloaded. Please check your internet connection and try again.':
        'تعذّر تنزيل النموذج. تأكد من اتصالك بالإنترنت ثم حاول مرة أخرى.',
    'The speech model “{model}” is not downloaded yet.\nOpen Morphix Studio → Speech models → Download (one time, needs internet). '
    'After that, transcription works fully offline.':
        'نموذج الكلام «{model}» لم يُنزَّل بعد.\nافتح استوديو Morphix ← نماذج تحويل الكلام ← تنزيل (مرة واحدة، ويحتاج إنترنت). '
        'بعدها يعمل التحويل دون أي اتصال.',
    'Loading the speech model (offline)…': 'جارٍ تحميل نموذج الكلام (دون إنترنت)…',
    'Analyzing the audio of {name}…': 'جارٍ تحليل صوت الملف {name}…',
    'Continuing {name} — {done} of {total} parts already done': 'متابعة {name} — اكتمل {done} من {total} أجزاء سابقًا',
    '{name}: part {done} of {total} · {pos} of {length} · about {mins} min left':
        '{name}: الجزء {done} من {total} · {pos} من {length} · يتبقى نحو {mins} دقيقة',
    '{name}: finishing…': '{name}: اللمسات الأخيرة…',
    'No audio track found in {name}': 'لا يحتوي الملف {name} على مسار صوتي',
    'Could not read {name}': 'تعذّرت قراءة الملف {name}',
    'No speech was recognized in {name}.': 'لم يُتعرّف على أي كلام في الملف {name}.',

    # ------------------------------------------------------------------ about
    'Morphix was designed and built to save you time and effort: it brings your everyday file tools together in one place, '
    'so the work gets done in a single step — privately, on your own computer, without needing the internet.':
        'صُمِّم Morphix وطُوِّر ليختصر عليك الوقت والجهد؛ فيجمع أدوات ملفاتك اليومية في مكان واحد، '
        'لتُنجز عملك بخطوة واحدة — بخصوصية تامة، على جهازك، ودون حاجة إلى الإنترنت.',
    'Developed by: Yousef bin Abdulaziz Alghamdi': 'تطوير: يوسف بن عبدالعزيز الغامدي',
    'Get in touch': 'للتواصل',
    'Version {v}': 'الإصدار {v}',

    'Maximum accuracy — slowest (large-v3, full precision)': 'أقصى دقة — الأبطأ (large-v3 بدقة كاملة)',
    'Clean up the audio first (evens out quiet voices, removes rumble)':
        'نقِّ الصوت أولًا (يوازن الأصوات المنخفضة ويزيل الطنين)',
    'For Arabic choose “Most accurate”, or “Maximum accuracy” for the very best result (same 3 GB download, about half the speed). '
    'Clear recordings work best — strong dialects and heavy background noise lower accuracy.':
        'للعربية اختر «الأعلى دقة»، أو «أقصى دقة» لأفضل نتيجة ممكنة (التنزيل نفسه بحجم 3 GB، لكن بنصف السرعة تقريبًا). '
        'أفضل النتائج مع التسجيلات الواضحة، أما اللهجات القوية والضوضاء العالية فتقلل الدقة.',

    'Completely free — no subscriptions, no ads, and no account needed.':
        'مجاني بالكامل — بلا اشتراكات، ولا إعلانات، ولا حاجة إلى إنشاء حساب.',

    # ------------------------------------------------------------------ background removal
    'Remove background': 'إزالة الخلفية',
    'Remove the background': 'إزالة خلفية الصورة',
    'Remove the background (keeps full quality)': 'إزالة الخلفية (بنفس جودة الصورة)',
    'Morphix · Remove background': 'Morphix · إزالة الخلفية',
    '{n} image(s). The subject keeps its exact original pixels and full resolution; only the background is removed.':
        '{n} صورة. يبقى العنصر الأساسي بنفس دقته الكاملة ونفس بكسلاته الأصلية تمامًا، وتُزال الخلفية فقط.',
    'Quality': 'الجودة',
    'Background': 'الخلفية',
    'Transparent (PNG)': 'شفافة (PNG)',
    'White': 'بيضاء',
    'Black': 'سوداء',
    'Standard (ISNet) — recommended': 'قياسي (ISNet) — مُوصى به',
    'Finest edges (BiRefNet) — 16 GB RAM': 'أدق الحواف (BiRefNet) — يحتاج ذاكرة 16 GB',
    'Works fully offline. The first time, the model is downloaded once (internet needed). '
    '“Finest edges” is best for hair and fur and needs 16 GB of memory.':
        'تعمل دون إنترنت. في أول مرة فقط يُنزَّل النموذج (يحتاج إنترنت مرة واحدة). '
        'خيار «أدق الحواف» هو الأفضل للشعر والفرو، ويحتاج جهازًا بذاكرة 16 GB.',
    'Downloading the background model ({size}) — one time only…': 'جارٍ تنزيل نموذج إزالة الخلفية ({size}) — لمرة واحدة فقط…',
    'Removing the background: {name} ({i} of {n})…': 'جارٍ إزالة الخلفية: {name} ({i} من {n})…',
    'The background-removal model is not downloaded yet. It downloads automatically the first time (internet needed once).':
        'نموذج إزالة الخلفية لم يُنزَّل بعد. يُنزَّل تلقائيًا في أول استخدام (يحتاج إنترنت مرة واحدة).',
    'This Mac has too little memory for “Finest edges”; using Standard instead.':
        'ذاكرة هذا الجهاز لا تكفي لخيار «أدق الحواف»، لذلك استُخدم الخيار القياسي.',

    # ------------------------------------------------------------------ documents & Excel
    'Merge everything into one PDF': 'دمج كل الملفات في ملف PDF واحد',
    'Convert each file to its own PDF': 'تحويل كل ملف إلى PDF مستقل',
    'Merge into one PDF': 'دمج في PDF واحد',
    'Each to PDF': 'كل ملف إلى PDF',
    'Excel → PDF (each sheet fits one page)': 'Excel ← PDF (كل ورقة في صفحة واحدة)',
    'Excel → CSV (one file per sheet)': 'Excel ← CSV (ملف لكل ورقة)',
    'Split sheets into separate Excel files': 'فصل الأوراق إلى ملفات Excel مستقلة',
    'Merge workbooks into one Excel file': 'دمج ملفات Excel في ملف واحد',
    'CSV → Excel': 'CSV ← Excel',
    'PDF · fit sheets': 'PDF · ورقة بصفحة',
    'To CSV': 'إلى CSV',
    'To Excel': 'إلى Excel',
    'Split sheets': 'فصل الأوراق',
    'Merge workbooks': 'دمج ملفات Excel',
    'Word / PowerPoint files': 'ملفات Word و PowerPoint',
    'One Excel file': 'ملف Excel واحد',
    'Multiple Excel files': 'عدة ملفات Excel',
    'Mixed documents': 'مستندات متنوعة',
    'Unsupported file: {name}': 'نوع الملف غير مدعوم: {name}',
    'The selected files are already PDFs.': 'الملفات المحددة بصيغة PDF أصلًا.',
    '{name} has only one sheet.': 'الملف {name} يحتوي على ورقة واحدة فقط.',
    'Converting Office files needs LibreOffice (free). Install it from libreoffice.org, then try again.':
        'تحويل ملفات Office يحتاج إلى برنامج LibreOffice المجاني. ثبّته من libreoffice.org ثم حاول مرة أخرى.',

    # ------------------------------------------------------------------ add-ons
    'Yousef A.Alghamdi': 'من تطوير: يوسف الغامدي | Yousef A.Alghamdi',
    'Add-ons': 'الإضافات',
    'Add-ons…': 'الإضافات…',
    'Morphix · Add-ons': 'Morphix · الإضافات',
    'Extra tools that are downloaded once. After downloading they work without the internet. Everything else in Morphix is already built in.':
        'أدوات إضافية تُنزَّل مرة واحدة فقط، وبعد تنزيلها تعمل دون إنترنت. أما بقية أدوات Morphix فهي مدمجة فيه أصلًا.',
    'Quick drafts and clear recordings. Lowest accuracy.': 'للمسودات السريعة والتسجيلات الواضحة. دقته الأقل بين النماذج.',
    'Good balance of speed and accuracy for everyday recordings.': 'توازن جيد بين السرعة والدقة للتسجيلات اليومية.',
    'Highest accuracy — recommended for Arabic. Also powers “Maximum accuracy”.':
        'الأعلى دقة — مُوصى به للعربية. ويُستخدم أيضًا في خيار «أقصى دقة».',
    'Clean cut-outs of people, products, animals and objects.': 'قصّ نظيف للأشخاص والمنتجات والحيوانات والأشياء.',
    'Finest hair and fur edges. Needs a Mac with 16 GB of memory.': 'أدق حواف للشعر والفرو. يحتاج جهازًا بذاكرة 16 GB.',
    'Free program that converts Word, PowerPoint and Excel files. Installed separately from its official website.':
        'برنامج مجاني يحوّل ملفات Word وPowerPoint وExcel. يُثبَّت بشكل مستقل من موقعه الرسمي.',
    'This Mac does not have enough memory for this model (16 GB needed).': 'ذاكرة هذا الجهاز لا تكفي لهذا النموذج (يحتاج 16 GB).',
    'Installed — works offline': 'مثبّت — يعمل دون إنترنت',
    'Installed': 'مثبّت',
    'Not installed — needs internet once': 'غير مثبّت — يحتاج إنترنت مرة واحدة',
    'Not installed': 'غير مثبّت',
    'Download': 'تنزيل',
    'Downloading…': 'جارٍ التنزيل…',
    'Open website': 'فتح الموقع',
    'Remove': 'حذف',
    'Remove “{name}” from this computer? You can download it again at any time.':
        'هل تريد حذف «{name}» من جهازك؟ تستطيع تنزيله مرة أخرى في أي وقت.',
    'A download is still running. Cancel it and close?': 'ما زال هناك تنزيل قيد التنفيذ. هل تريد إلغاءه والإغلاق؟',
    'Another program already uses {keys}. Choose a different shortcut in Settings → Keyboard shortcut.':
        'هناك برنامج آخر يستخدم {keys}. اختر اختصارًا آخر من الإعدادات ← اختصار لوحة المفاتيح.',
    'The speech engine could not load on this computer ({error}). If Smart App Control is on, it blocks the engine files.':
        'تعذّر تشغيل محرك تحويل الكلام على هذا الجهاز ({error}). إذا كان «التحكم الذكي في التطبيقات» مفعّلًا فهو يمنع ملفات المحرك.',
    'Add a keyboard shortcut in your system settings that runs: {cmd}':
        'أضف اختصارًا من إعدادات لوحة المفاتيح في النظام يشغّل الأمر: {cmd}',
}
