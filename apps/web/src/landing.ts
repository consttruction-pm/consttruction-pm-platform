type LandingLocale = string;
type Feature = { icon: string; title: string; body: string; assistantAvatar?: boolean };
type LandingCopy = {
  nav: string[]; eyebrow: string; title: string; accent: string; subtitle: string; body: string;
  primary: string; secondary: string; featuresEyebrow: string; featuresTitle: string; featuresBody: string; features: Feature[];
  techEyebrow: string; techTitle: string; techBody: string; techLink: string; techNodes: string[];
  industriesEyebrow: string; industriesTitle: string; industriesBody: string;
  ctaTitle: string; ctaBody: string; signIn: string; start: string; language: string;
  footerColumns: Array<{ title: string; links: string[] }>; footerNote: string;
  assistantTitle: string; assistantSubtitle: string; assistantDescription: string;
  assistantWorkspaceAction: string; assistantClose: string;
};
const copy: Partial<Record<LandingLocale, LandingCopy>> = {
  en: {
    nav: ["Home", "Platform", "Solutions", "Resources", "About Us", "Contact"],
    eyebrow: "CONSTRUCTION & BUILDING INTELLIGENCE",
    title: "Control every detail.", accent: "Build with confidence.",
    subtitle: "Plan. Control. Build Smarter.",
    body: "From buildings and infrastructure to oil, gas, petrochemical, energy and complex industrial facilities, CUBI connects project scope, schedules, progress, resources, cost and evidence in one disciplined project-controls environment. Give planners, cost engineers, site leaders and executives a clearer basis for the ne¶»§q«^vóŸ–6S–7_ûg‰ô(€€€t°(€€€Ñ•¡å•‰É½Üè‹¢’¦nG«_·
ã
Ÿ
¿#»
¬ˆ±Ñ•¡Q¥Ñ±”è‹
#
+¢&¿š?šwšÆë–ºk
KšR¿#
/ÖÇ–B#–~ënˆ°(€€€Ñ•¡	½‘äè‰U	$ƒ¿_·
ã
Ÿ
¿#–ºkú§]	O
‹
¿
O
7#¿ó
¿
¯³Ïógó
ç§
“Ï¦Ëš6_«
÷ó
çï
Ï
ç#š–‚Çº‡BšZšnã³wó#
K¦šBë_ûg¢¢#º_£–Ş—¢/ÖCšzs¿š¶–ò?«_·
ã
Ÿ
¿#
×óO
ç
Kš‚çš.ƒ£_
‹
ß
ç
ÿÏ#»š:£šâ³¯¿’úw–¶c_ûo
Oˆ°(€€€Ñ•¡1¥¹¬è‹_§#W
§óƒš¦¢÷
K¢š/
,ƒŠHˆ±Ñ•¡9½‘•Ìél‹_·
ã
Ÿ
¿#º‡Bˆ°‹š*¢†O
³
“$ˆ°‹¦šBëó
üˆ°‹ÖÇ–"ÛW
3š–·–.d‰t°(€€€¥¹‘ÕÍÑÉ¥•Íå•‰É½Üè‹–ršr£–Ş—’ê//
'¢’¦nG«_·
ï
ç¢¢·–
gûœˆ±¥¹‘ÕÍÑÉ¥•ÍQ¥Ñ±”è‹’â“»_·
ã
Ÿ
¿#º‡B–~ën“
K–’kšc«Rš–·ãˆ°(€€€¥¹‘ÕÍÑÉ¥•Í	½‘äè‰U	$ƒ¿–îë¾'ï
“ÏW§~ÏšÊçï
³
ç¦Z/fëG
“_§
“Ï¢÷šÊçš&~ÏšÊç–2[–¶›¢¢·–
gfë¦nïï–³n+’ê/š–·Rš–·_§Ï#Aƒ_·
ã
Ÿ
¿#
KšÏ–ºk_›ûgš/¦ƒ
¯³Ïó–öç–&Ë³wó#
K–º¦jo»š–·–.g¯–B#
?o›¢¢·–ºkŸ7ûgˆ°(€€€Ñ…Q¥Ñ±”è‹š²‡»_·
ã
Ÿ
¿#–"“šZ·
K
#
+šb;Šë«š–‚ÇŸˆ±Ñ…	½‘äè‹¢¢#Rï’êëšVÃ–“¢¢ó¢Ş‡
K_·
ã
Ÿ
¿#§
“W
×
“
¿¯–£’öOŸ“«;ûgˆ°(€€€…ÍÍ¥ÍÑ…¹ÑQ¥Ñ±”è‰U	$ƒ
£Ï
ã/
‹«Ï
Ãï
“Ï«
ã
ŸÏ
çï
‹
ß
ç
ÿÏ ˆ±…ÍÍ¥ÍÑ…¹ÑMÕ‰Ñ¥Ñ±”è‹_·
ã
Ÿ
¿#šR¿š>Ó
KÚîÆ­y×÷'BgVæ7F–öâ&W6öÇfTÆæF–ætÆæwVvT‡&Vb€¢F&vWDÆö6ÆS¢ÆæF–ætÆö6ÆRÀ¢F†æÖS¢7G&–ærÀ¢FVfVÇDÆö6ÆS¢ÆæF–ætÆö6ÆRÒDTdTÅEôÄäD”äuôÄô4ÄRÀ¢“¢7G&–ær°¢6öç7B&÷WFUF‚ÒG·F†æÖRç&WÆ6R‚ö–æFW…Âæ‡FÖÂBòÂ""’ç&WÆ6R‚õÂò²BòÂ""—Òö°¢6öç7BF„Æö6ÆRÒ&W6öÇfTÆæF–ætÆö6ÆTg&öÕF‚‡F†æÖR“°¢6öç7B&6RÒF„Æö6ÆP¢ò&÷WFUF‚ç6Æ–6RƒÂ&÷WFUF‚æÆVæwF‚ÒG·F„Æö6ÆWÒöæÆVæwF‚¢¢&÷WFUFƒ°¢–b‡F&vWDÆö6ÆRÓÓÒFVfVÇDÆö6ÆR’&WGW&â&6S°¢&WGW&âG¶&6WÒG·F&vWDÆö6ÆWÒö°§Ğ ¦gVæ7F–öâ&W7F÷&TÆæF–ætÆö6ÆR‚“¢7G&–ærÂçVÆÂ°¢6öç7B&÷WFTÆö6ÆRÒ&W6öÇfTÆæF–ætÆö6ÆTg&öÕF‚‡v–æF÷ræÆö6F–öâçF†æÖR“°¢6öç7B6fVBÒ&VE6fVDÆæF–ætÆö6ÆR‚“°¢–b‡&÷WFTÆö6ÆR’°¢Æö6ÆRÒ&÷WFTÆö6ÆS°¢–b‡6fVBÓÒ&÷WFTÆö6ÆR’W'6—7DÆæF–ætÆö6ÆR‚“°¢&WGW&âçVÆÃ°¢Ğ¢òò†öÖWvRÖöæÇ’Æö6ÆW2&R&VæFW&VB–âÆ6RæB&Ræ÷BGfW'F—6VB0¢òòG&ç6ÆFVBÂ–æFW†&ÆR7V'vR&÷WFW2âF†RFö7VÖVçBÆæröF—"—2WFFV@¢òòFövWF†W"v—F‚F†R6VÆV7FVB†öÖWvR6÷’à¢Æö6ÆRÒ6fVBóòDTdTÅEôÄäD”äuôÄô4ÄS°¢–b‡6fVBbbvWDÆæF–ætÆæwVvU&÷WFW2‚’æ–æ6ÇVFW2‡6fVB’’°¢&WGW&â&W6öÇfTÆæF–ætÆæwVvT‡&Vb‡6fVBÂv–æF÷ræÆö6F–öâçF†æÖR“°¢Ğ¢&WGW&âçVÆÃ°§Ğ¦gVæ7F–öâ&VE6fVDÆæF–ætÆö6ÆR‚“¢ÆæF–ætÆö6ÆRÂçVÆÂ°¢G'’°¢6öç7B6fVBÒv–æF÷ræÆö6Å7F÷&vRævWD—FVÒ„ÄäD”äuôÄô4ÄUõ5Dõ$tUô´U’“°¢&WGW&â6fVBbbvWDÆæF–æt†öÖWvTÆö6ÆW2‚’æ–æ6ÇVFW2‡6fVB’ò6fVB¢çVÆÃ°¢Ò6F6‚°¢òò7F÷&vRÖ’&RF—6&ÆVC²F†R†öÖWvR&VÖ–ç2W6&ÆRv—F†÷WB7Kkºwµç