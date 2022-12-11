QUERY_PARAMETERS = [
    {
        "name": "css",
        "type": "integer",
        "description": "Styles the embed's theme according to the unique custom CSS ID. Custom CSS may be managed from the user dashboard page.",
        "example": "1",
    },
    {
        "name": "defaultchannel",
        "type": "snowflake",
        "description": 'Instead of having the top channel as the first channel your users see, you may change it. Enable Discord\'s Developer mode in the Appearances tab of the User Settings and copy the channel ID. Here is a <a href="https://support.discordapp.com/hc/en-us/articles/206346498-Where-can-I-find-my-server-ID-" target="_blank">tutorial</a> on obtaining the channel ID.',
        "example": "1234567890",
    },
    {
        "name": "fixedsidenav",
        "type": "boolean",
        "description": "Always show the left server navigation sidebar on large screens.",
        "example": "true",
        "options": [
            {
                "name": "true",
                "default": False,
            },
            {
                "name": "false",
                "default": True,
            },
        ],
    },
    {
        "name": "lang",
        "type": "language",
        "description": 'Are your users multilingual? No worries, Titan can speak multiple languages! Check the about page for a list of all language parameters Titan can support. <br> Wish Titan supported your language? Consider contributing to <a href="http://translate.titanembeds.com/" target="_blank">our CrowdIn project</a>!',
        "example": "nl_NL",
        "input": "text",
    },
    {
        "name": "noscroll",
        "type": "boolean",
        "description": "Prevents the embed from scrolling down on first load. Useful for those who wants to set #info -typed channels as their default channel. Gotta have those good reads!",
        "example": "true",
        "options": [
            {
                "name": "true",
                "default": False,
            },
            {
                "name": "false",
                "default": True,
            },
        ],
    },
    {
        "name": "sametarget",
        "type": "boolean",
        "description": "For those who don't want the Discord Login to open in a new tab/window... (<em>Does not work for iframe loaded embeds!!!</em> This is a direct link option only.)",
        "example": "true",
        "options": [
            {
                "name": "true",
                "default": False,
            },
            {
                "name": "false",
                "default": True,
            },
        ],
    },
    {
        "name": "scrollbartheme",
        "type": "string",
        "description": 'Sets the scrollbar theme. View the demo of all themes <a href="http://manos.malihu.gr/repository/custom-scrollbar/demo/examples/scrollbar_themes_demo.html" target="_blank">here</a>. Or create your own theme by overriding <a href="https://i.imgur.com/SZPL0ag.png" target="_blank">these classes</a> and following at <a href="https://github.com/malihu/malihu-custom-scrollbar-plugin/blob/master/jquery.mCustomScrollbar.css" target="_blank">these examples</a>!',
        "example": "3d-dark",
        "options": [
            {
                "name": "light",
                "default": False,
            },
            {
                "name": "dark",
                "default": False,
            },
            {
                "name": "minimal",
                "default": False,
            },
            {
                "name": "minimal-dark",
                "default": False,
            },
            {
                "name": "light-2",
                "default": False,
            },
            {
                "name": "dark-2",
                "default": False,
            },
            {
                "name": "light-3",
                "default": False,
            },
            {
                "name": "dark-3",
                "default": False,
            },
            {
                "name": "light-thick",
                "default": False,
            },
            {
                "name": "dark-thick",
                "default": False,
            },
            {
                "name": "light-thin",
                "default": False,
            },
            {
                "name": "dark-thin",
                "default": False,
            },
            {
                "name": "inset",
                "default": False,
            },
            {
                "name": "inset-dark",
                "default": False,
            },
            {
                "name": "inset-2",
                "default": False,
            },
            {
                "name": "inset-2-dark",
                "default": False,
            },
            {
                "name": "inset-3",
                "default": False,
            },
            {
                "name": "inset-3-dark",
                "default": False,
            },
            {
                "name": "rounded",
                "default": False,
            },
            {
                "name": "rounded-dark",
                "default": False,
            },
            {
                "name": "rounded-dots",
                "default": False,
            },
            {
                "name": "rounded-dots-dark",
                "default": False,
            },
            {
                "name": "3d",
                "default": False,
            },
            {
                "name": "3d-dark",
                "default": False,
            },
            {
                "name": "3d-thick",
                "default": False,
            },
            {
                "name": "3d-thick-dark",
                "default": False,
            },
            {
                "name": "custom",
                "default": False,
            },
        ],
    },
    {
        "name": "lockscrollbar",
        "type": "boolean",
        "description": "Shows the scrollbar permanently without autohiding. (Requires the scrollbar theme param to be set for scrollbar to be themed)",
        "example": "true",
        "options": [
            {
                "name": "true",
                "default": False,
            },
            {
                "name": "false",
                "default": True,
            },
        ],
    },
    {
        "name": "theme",
        "type": "string",
        "description": "Want your embed to use one of our premade themes? Look no further!",
        "example": "DiscordDark",
        "options": [
            {
                "name": "BetterTitan",
                "default": False,
            },
            {
                "name": "DiscordDark",
                "default": False,
            },
            {
                "name": "FireWyvern",
                "default": False,
            },
            {
                "name": "IceWyvern",
                "default": True,
            },
            {
                "name": "MetroEdge",
                "default": False,
            },
        ],
    },
    {
        "name": "username",
        "type": "string",
        "description": "Prefills the guest username field with the given username. If the guest captcha is disabled and that the user has not been logged in yet, it automatically logs the user in with the specified username.",
        "example": "Rainbow%20Dash",
    },
    {
        "name": "userscalable",
        "type": "boolean",
        "description": "Enables pinch-to-zoom and auto zoom on input fields for most mobile browsers on touch-enabled devices. Disabling this will give your embed a more app-like experience. Keep in mind that disabling this might prevent accessibility features disabled people rely on from functioning.",
        "example": "false",
        "options": [
            {
                "name": "true",
                "default": True,
            },
            {
                "name": "false",
                "default": False,
            },
        ],
    },
]

LANGUAGES = [
    {
        "code": "az_AZ",
        "name_en": "Azerbaijani",
        "name": "Azərbaycan",
        "translators": [
            {
                "name": "Shahin Farzaliyev",
                "crowdin_profile": "Khan27",
            },
        ],
    },
    {
        "code": "bg_BG",
        "name_en": "Bulgarian",
        "name": "български",
        "translators": [
            {
                "name": "kr3t3n",
                "crowdin_profile": "kr3t3n",
            },
            {
                "name": "Dremski",
                "crowdin_profile": "Dremski",
            },
        ],
    },
    {
        "code": "ca_ES",
        "name_en": "Catalan",
        "name": "Català",
        "translators": [
            {
                "name": "jan",
                "crowdin_profile": "test83318",
            },
            {
                "name": "Jaime Muñoz Martín",
                "crowdin_profile": "jmmartin_5",
            },
        ],
    },
    {
        "code": "cs_CZ",
        "name_en": "Czech",
        "name": "čeština",
        "translators": [
            {
                "name": "Roman Hejč",
                "crowdin_profile": "romanhejc",
            },
            {
                "name": "Tom Silvestr",
                "crowdin_profile": "rescool",
            },
        ],
    },
    {
        "code": "da_DK",
        "name_en": "Danish",
        "name": "Dansk",
        "translators": [
            {
                "name": "Victor Fisker",
                "crowdin_profile": "victorfrb",
            },
            {
                "name": 'Brian "Ztyle" Aagesen',
                "crowdin_profile": "b-l",
            },
            {
                "name": "Lucas Gundelach",
                "crowdin_profile": "lucas.g",
            },
        ],
    },
    {
        "code": "de_DE",
        "name_en": "German",
        "name": "Deutsch",
        "translators": [
            {
                "name": "futureyess22",
                "crowdin_profile": "futureyess22",
            },
            {
                "name": "Sascha Greuel",
                "crowdin_profile": "SoftCreatR",
            },
            {
                "name": "Markus Heinz",
                "crowdin_profile": "nanzowatz",
            },
        ],
    },
    {
        "code": "en_US",
        "name_en": "English",
        "name": "English",
        "translators": [
            {
                "name": "Tornado1878",
                "crowdin_profile": "Tornado1878",
            },
        ],
    },
    {
        "code": "es_ES",
        "name_en": "Spanish",
        "name": "Español",
        "translators": [
            {
                "name": "jmromero",
                "crowdin_profile": "jmromero",
            },
            {
                "name": "NeHoMaR",
                "crowdin_profile": "NeHoMaR",
            },
            {
                "name": "Jaime Muñoz Martín",
                "crowdin_profile": "jmmartin_5",
            },
            {
                "name": "Amy Y",
                "crowdin_profile": "amytheacmaster",
            },
            {
                "name": "NicholasG04",
                "crowdin_profile": "NicholasG04",
            },
        ],
    },
    {
        "code": "fr_FR",
        "name_en": "French",
        "name": "français",
        "translators": [
            {
                "name": "𝔻𝕣.𝕄𝕦𝕣𝕠𝕨",
                "crowdin_profile": "drmurow",
            },
            {
                "name": "SytheS Boi",
                "crowdin_profile": "clawschaospsn",
            },
            {
                "name": "MVP_54",
                "crowdin_profile": "54Mvp",
            },
            {
                "name": "Serveur gta",
                "crowdin_profile": "givemefive.serveur",
            },
        ],
    },
    {
        "code": "hi_IN",
        "name_en": "Hindi",
        "name": "हिंदी",
        "translators": [
            {
                "name": "jznsamuel",
                "crowdin_profile": "jasonsamuel88",
            },
        ],
    },
    {
        "code": "hu_HU",
        "name_en": "Hungarian",
        "name": "Magyar",
        "translators": [
            {
                "name": "János Erkli",
                "crowdin_profile": "erklijani0521",
            },
            {
                "name": "csongorhunt",
                "crowdin_profile": "csongorhunt",
            },
            {
                "name": "Amy Y",
                "crowdin_profile": "amytheacmaster",
            },
        ],
    },
    {
        "code": "id_ID",
        "name_en": "Indonesian",
        "name": "bahasa Indonesia",
        "translators": [
            {
                "name": "isaideureka",
                "crowdin_profile": "isaideureka",
            },
            {
                "name": "riesky",
                "crowdin_profile": "riesky",
            },
            {
                "name": "Qodam",
                "crowdin_profile": "Qodam",
            },
        ],
    },
    {
        "code": "it_IT",
        "name_en": "Italian",
        "name": "Italiano",
        "translators": [
            {
                "name": "dotJS",
                "crowdin_profile": "justdotJS",
            },
            {
                "name": "Amy Y",
                "crowdin_profile": "amytheacmaster",
            },
            {
                "name": "BlackHawk94",
                "crowdin_profile": "BlackHawk94",
            },
        ],
    },
    {
        "code": "ja_JP",
        "name_en": "Japanese",
        "name": "日本語",
        "translators": [
            {
                "name": "Jacob Ayeni",
                "crowdin_profile": "MehItsJacob",
            },
        ],
    },
    {
        "code": "nl_NL",
        "name_en": "Dutch",
        "name": "Nederlands",
        "translators": [
            {
                "name": "jelle619",
                "crowdin_profile": "jelle619",
            },
            {
                "name": "Reeskikker",
                "crowdin_profile": "Reeskikker",
            },
            {
                "name": "SuperVK",
                "crowdin_profile": "SuperVK",
            },
        ],
    },
    {
        "code": "pl_PL",
        "name_en": "Polish",
        "name": "Polski",
        "translators": [
            {
                "name": "That Guy",
                "crowdin_profile": "maksinibob",
            },
            {
                "name": "Ukas9",
                "crowdin_profile": "Ukas9",
            },
            {
                "name": "Krzysztof Kurzawa",
                "crowdin_profile": "Crisu192",
            },
        ],
    },
    {
        "code": "pt_PT",
        "name_en": "Portuguese",
        "name": "Português",
        "translators": [
            {
                "name": "Miguel Dos Reis",
                "crowdin_profile": "siersod",
            },
            {
                "name": "Ivo Pereira",
                "crowdin_profile": "ivo-pereira",
            },
            {
                "name": "DJ MARCIO EXTREME",
                "crowdin_profile": "krsolucoesweb",
            },
            {
                "name": "André Gama",
                "crowdin_profile": "ToeOficial",
            },
        ],
    },
    {
        "code": "pt_BR",
        "name_en": "Portuguese, Brazilian",
        "name": "Português do Brasil",
        "translators": [
            {
                "name": "DannielMM",
                "crowdin_profile": "DannielMM",
            },
        ],
    },
    {
        "code": "ro_RO",
        "name_en": "Romanian",
        "name": "Română",
        "translators": [
            {
                "name": "Andra",
                "crowdin_profile": "sarmizegetusa",
            },
            {
                "name": "Florin Andrei",
                "crowdin_profile": "florinandrei344",
            },
        ],
    },
    {
        "code": "ru_RU",
        "name_en": "Russian",
        "name": "русский",
        "translators": [
            {
                "name": "haha_yes",
                "crowdin_profile": "haha_yes",
            },
            {
                "name": "Влад Гаврилович",
                "crowdin_profile": "vladik0701",
            },
        ],
    },
    {
        "code": "sl_SI",
        "name_en": "Slovenian",
        "name": "Slovenščina",
        "translators": [
            {
                "name": "Obrazci Mail",
                "crowdin_profile": "spamamail64",
            },
        ],
    },
    {
        "code": "sr_Cyrl",
        "name_en": "Serbian (Cyrillic)",
        "name": "Српски",
        "translators": [
            {
                "name": '"adriatic" Miguel Dos Reis',
                "crowdin_profile": "siersod",
            },
            {
                "name": "Ciker",
                "crowdin_profile": "CikerDeveloper",
            },
        ],
    },
    {
        "code": "sr_Latn",
        "name_en": "Serbian (Latin)",
        "name": "Српски",
        "translators": [
            {
                "name": "Ciker",
                "crowdin_profile": "CikerDeveloper",
            },
            {
                "name": "shame741",
                "crowdin_profile": "shame741",
            },
        ],
    },
    {
        "code": "sv_SE",
        "name_en": "Swedish",
        "name": "svenska",
        "translators": [
            {
                "name": "Samuel Sandstrom",
                "crowdin_profile": "ssandstrom95",
            },
            {
                "name": "_CatInATopHat",
                "crowdin_profile": "_CatInATopHat",
            },
        ],
    },
    {
        "code": "th_TH",
        "name_en": "Thai",
        "name": "ไทย",
        "translators": [
            {
                "name": "Pantakarn Toopprateep",
                "crowdin_profile": "CardKunG",
            },
            {
                "name": "Jay Kh.",
                "crowdin_profile": "ds-al-coda",
            },
            {
                "name": "Apinat Yodprasit",
                "crowdin_profile": "apinatyodprasit",
            },
        ],
    },
    {
        "code": "tr_TR",
        "name_en": "Turkish",
        "name": "Türk",
        "translators": [
            {
                "name": "monomyth",
                "crowdin_profile": "monomyth",
            },
            {
                "name": "erdogdu96",
                "crowdin_profile": "erdogdu96",
            },
        ],
    },
    {
        "code": "zh_Hans_CN",
        "name_en": "Chinese Simplified",
        "name": "简体中文",
        "translators": [
            {
                "name": "dotJS",
                "crowdin_profile": "justdotJS",
            },
            {
                "name": "myjourney in Steemit",
                "crowdin_profile": "myjourney",
            },
            {
                "name": "Jack Mao",
                "crowdin_profile": "mrjacksonvillecc",
            },
        ],
    },
    {
        "code": "zh_Hant_TW",
        "name_en": "Chinese Traditional",
        "name": "中国传统的",
        "translators": [
            {
                "name": "myjourney in Steemit",
                "crowdin_profile": "myjourney",
            },
        ],
    },
]

# Original list adopted from https://github.com/areebbeigh/profanityfilter/blob/master/profanityfilter/data/badwords.txt
GLOBAL_BANNED_WORDS = [
    "@$$",
    "ahole",
    "amcik",
    "andskota",
    "anus",
    "arschloch",
    "arse",
    "ash0le",
    "ash0les",
    "asholes",
    "ass",
    "assface",
    "assh0le",
    "assh0lez",
    "asshole",
    "assholes",
    "assholz",
    "assmonkey",
    "assrammer",
    "asswipe",
    "ayir",
    "azzhole",
    "b00bs",
    "b17ch",
    "b1tch",
    "bassterds",
    "bastard",
    "bastards",
    "bastardz",
    "basterds",
    "basterdz",
    "bch",
    "bi7ch",
    "biatch",
    "bich",
    "bitch",
    "bitches",
    "blowjob",
    "boffing",
    "boiolas",
    "bollock",
    "boobs",
    "breasts",
    "btch",
    "buceta",
    "bullshit",
    "butthole",
    "buttpirate",
    "buttwipe",
    "c0ck",
    "c0cks",
    "c0k",
    "cabron",
    "carpetmuncher",
    "cawk",
    "cawks",
    "cazzo",
    "chink",
    "chraa",
    "chuj",
    "cipa",
    "clit",
    "clits",
    "cnts",
    "cntz",
    "cock",
    "cockhead",
    "cocks",
    "cocksucker",
    "crap",
    "cum",
    "cunt",
    "cunts",
    "cuntz",
    "d4mn",
    "damn",
    "daygo",
    "dego",
    "dick",
    "dike",
    "dild0",
    "dild0s",
    "dildo",
    "dildos",
    "dilld0",
    "dilld0s",
    "dirsa",
    "dominatricks",
    "dominatrics",
    "dominatrix",
    "dupa",
    "dyke",
    "dziwka",
    "ejackulate",
    "ejakulate",
    "ekrem",
    "ekto",
    "enculer",
    "enema",
    "faen",
    "fag",
    "fag1t",
    "faget",
    "fagg1t",
    "faggit",
    "faggot",
    "fagit",
    "fags",
    "fagz",
    "faig",
    "faigs",
    "fanculo",
    "fanny",
    "fart",
    "fatass",
    "fcuk",
    "feces",
    "feg",
    "felcher",
    "ficken",
    "fitt",
    "flikker",
    "flipping",
    "foreskin",
    "fotze",
    "fu",
    "fuchah",
    "fuck",
    "fucka",
    "fucker",
    "fuckin",
    "fucking",
    "fucks",
    "fudgepacker",
    "fuk",
    "fukah",
    "fuken",
    "fuker",
    "fukin",
    "fukk",
    "fukka",
    "fukkah",
    "fukken",
    "fukker",
    "fukkin",
    "futkretzn",
    "fux0r",
    "g00k",
    "gay",
    "gaybor",
    "gayboy",
    "gaygirl",
    "gays",
    "gayz",
    "goddamned",
    "gook",
    "guiena",
    "h00r",
    "h0ar",
    "h0r",
    "h0re",
    "h4x0r",
    "hell",
    "hells",
    "helvete",
    "hoar",
    "hoer",
    "honkey",
    "hoor",
    "hoore",
    "hore",
    "huevon",
    "hui",
    "injun",
    "jackoff",
    "jap",
    "japs",
    "jerkoff",
    "jisim",
    "jism",
    "jiss",
    "jizm",
    "jizz",
    "kanker",
    "kawk",
    "kike",
    "klootzak",
    "knob",
    "knobs",
    "knobz",
    "knulle",
    "kraut",
    "kuk",
    "kuksuger",
    "kunt",
    "kunts",
    "kuntz",
    "kurac",
    "kurwa",
    "kusi",
    "kyrpa",
    "l3i+ch",
    "l3itch",
    "lesbian",
    "lesbo",
    "lezzian",
    "lipshits",
    "lipshitz",
    "mamhoon",
    "masochist",
    "masokist",
    "massterbait",
    "masstrbait",
    "masstrbate",
    "masterbaiter",
    "masterbat",
    "masterbat3",
    "masterbate",
    "masterbates",
    "masturbat",
    "masturbate",
    "merd",
    "mibun",
    "mofo",
    "monkleigh",
    "motha",
    "mothafucker",
    "mothafuker",
    "mothafukkah",
    "mothafukker",
    "motherfucker",
    "motherfukah",
    "motherfuker",
    "motherfukkah",
    "motherfukker",
    "mouliewop",
    "muie",
    "mulkku",
    "muschi",
    "mutha",
    "muthafucker",
    "muthafukah",
    "muthafuker",
    "muthafukkah",
    "muthafukker",
    "n1gr",
    "nastt",
    "nasty",
    "nazi",
    "nazis",
    "nepesaurio",
    "nigga",
    "niggas",
    "nigger",
    "nigur",
    "niiger",
    "niigr",
    "nutsack",
    "orafis",
    "orgasim",
    "orgasm",
    "orgasum",
    "oriface",
    "orifice",
    "orifiss",
    "orospu",
    "p0rn",
    "packi",
    "packie",
    "packy",
    "paki",
    "pakie",
    "paky",
    "paska",
    "pecker",
    "peeenus",
    "peeenusss",
    "peenus",
    "peinus",
    "pen1s",
    "penas",
    "penis",
    "penisbreath",
    "penus",
    "penuus",
    "perse",
    "phuc",
    "phuck",
    "phuk",
    "phuker",
    "phukker",
    "picka",
    "pierdol",
    "pillu",
    "pimmel",
    "pimpis",
    "piss",
    "pizda",
    "polac",
    "polack",
    "polak",
    "poonani",
    "poontsee",
    "poop",
    "porn",
    "pr0n",
    "pr1c",
    "pr1ck",
    "pr1k",
    "preteen",
    "pula",
    "pule",
    "pusse",
    "pussee",
    "pussy",
    "puta",
    "puto",
    "puuke",
    "puuker",
    "qahbeh",
    "queef",
    "queer",
    "queers",
    "queerz",
    "qweers",
    "qweerz",
    "qweir",
    "rautenberg",
    "recktum",
    "rectum",
    "retard",
    "s.o.b.",
    "sadist",
    "scank",
    "schaffer",
    "scheiss",
    "schlampe",
    "schlong",
    "schmuck",
    "screw",
    "screwing",
    "scrotum",
    "semen",
    "sex",
    "sexx",
    "sexxx",
    "sexy",
    "sh1t",
    "sh1ter",
    "sh1ts",
    "sh1tter",
    "sh1tz",
    "sharmuta",
    "sharmute",
    "shemale",
    "shi+",
    "shipal",
    "shit",
    "shits",
    "shitt",
    "shitter",
    "shitty",
    "shity",
    "shitz",
    "shiz",
    "sht",
    "shyt",
    "shyte",
    "shytty",
    "skanck",
    "skank",
    "skankee",
    "skankey",
    "skanks",
    "skanky",
    "skrib",
    "slut",
    "sluts",
    "slutty",
    "slutz",
    "smut",
    "sonofabitch",
    "sx",
    "teets",
    "teez",
    "testical",
    "testicle",
    "tit",
    "tits",
    "titt",
    "turd",
    "va1jina",
    "vag1na",
    "vagiina",
    "vagina",
    "vaj1na",
    "vajina",
    "vullva",
    "vulva",
    "w00se",
    "w0p",
    "wank",
    "wh00r",
    "wh0re",
    "whoar",
    "whore",
    "xrated",
    "xxx",
]


LANGUAGE_CODE_LIST = [lang["code"] for lang in LANGUAGES]
