"""
RSS Feed Configuration with Categories and Subcategories

This module defines the RSS feeds organized by categories to improve
article classification and clustering accuracy.

# TEST: Volume mounting is working if you can see this comment in the container
# UPDATED: Testing live mount at 2025-08-20 16:09
"""

from typing import Dict, List

# RSS Feed Configuration organized by categories
# Define the desired category order
CATEGORY_ORDER = [
    "World News",
    "Politics & Government", 
    "Business",
    "Technology",
    "Science & Environment",
    "Sports", 
    "Arts & Culture",
    "Health",
    "Lifestyle"
]

RSS_FEEDS_CONFIG = {
    "World News": {
        "subcategories": ["Africa", "Asia", "Europe", "Middle East", "North America", "South America", "Oceania"],
        "feeds": [
            "https://www.abc.net.au/news/feed/51120/rss.xml",  # ABC News (Australia)
            "https://www.africanews.com/feed/rss",  # Africa News
            "https://www.aljazeera.com/xml/rss/all.xml?sec=Asia",  # Al Jazeera – Asia
            "https://www.aljazeera.com/xml/rss/all.xml?sec=latin-america",  # Al Jazeera – Latin America
            "https://www.aljazeera.com/xml/rss/all.xml?sec=Middle%20East",  # Al Jazeera – Middle East
            "https://asiatimes.com/feed/",  # Asia Times
            "https://feeds.bbci.co.uk/news/world/africa/rss.xml",  # BBC News – Africa
            "https://feeds.bbci.co.uk/news/world/asia/rss.xml",  # BBC News – Asia
            "https://feeds.bbci.co.uk/news/world/australia/rss.xml",  # BBC News – Australia
            "https://feeds.bbci.co.uk/news/world/europe/rss.xml",  # BBC News – Europe
            "https://feeds.bbci.co.uk/news/world/latin_america/rss.xml",  # BBC News – Latin America
            "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml",  # BBC News – Middle East
            "https://feeds.bbci.co.uk/news/world/rss.xml",  # BBC News – World
            "https://feeds.bbci.co.uk/news/world/us_and_canada/rss.xml",  # BBC News – US & Canada
            "https://feeds.bbci.co.uk/news/rss.xml",  # BBC News
            "http://rss.cnn.com/rss/cnn_topstories.rss",  # CNN Top Stories
            "http://rss.cnn.com/rss/cnn_world.rss",  # CNN World
            "https://rss.dw.com/rdf/rss-en-africa",  # DW (Deutsche Welle) Africa
            "https://rss.dw.com/rdf/rss-en-asia",  # DW – Asia
            "https://www.euronews.com/rss?level=theme&name=news",  # Euronews
            "https://foreignpolicy.com/feed/",  # Foreign Policy Magazine
            "https://moxie.foxnews.com/google-publisher/latest.xml",  # Fox News
            "https://www.france24.com/en/europe/rss",  # France 24 – Europe
            "https://www.theguardian.com/world/africa/rss",  # The Guardian – Africa
            "https://www.theguardian.com/australia-news/rss",  # The Guardian – Australia
            "https://www.theguardian.com/world/middleeast/rss",  # The Guardian – Middle East
            "https://www.theguardian.com/world/rss",  # The Guardian World Politics
            "https://www.japantimes.co.jp/news/feed/",  # Japan Times News
            "https://mondediplo.com/spip.php?page=backend",  # Le Monde Diplomatique (English)
            "https://mg.co.za/feeds/",  # Mail & Guardian (South Africa)
            "https://www.middleeasteye.net/rss",  # Middle East Eye
            "https://www.middleeastmonitor.com/feed/",  # Middle East Monitor
            "https://www.9news.com.au/rss",  # 9News
            "https://feeds.npr.org/1001/rss.xml",  # NPR News
            "https://www.rnz.co.nz/rss/national.xml",  # Radio New Zealand News
            "https://www.sbs.com.au/news/feed",  # SBS News
            "https://www.smh.com.au/rss/feed.xml",  # Sydney Morning Herald
            "https://thediplomat.com/feed/",  # The Diplomat
            "https://news.un.org/feed/subscribe/en/news/all/rss.xml",  # UN News
            "https://www.yahoo.com/news/rss",  # Yahoo News
            "https://www.worldpoliticsreview.com/feed/",  # World Politics Review
        ]
    },
    
    "Politics & Government": {
        "subcategories": ["US Politics", "International Politics", "Elections", "Policy & Legislation", "Government Affairs"],
        "feeds": [
            "https://www.aljazeera.com/xml/rss/all.xml?sec=politics",  # Al Jazeera Politics
            "https://feeds.bbci.co.uk/news/politics/rss.xml",  # BBC World Politics
            "https://www.cbsnews.com/latest/rss/politics",  # CBS News Politics
            "http://rss.cnn.com/rss/cnn_allpolitics.rss",  # CNN Politics
            "https://fivethirtyeight.com/feed/",  # FiveThirtyEight
            "https://fivethirtyeight.com/politics/feed/",  # FiveThirtyEight – Elections
            "https://moxie.foxnews.com/google-publisher/politics.xml",  # Fox News Politics
            "https://feeds.npr.org/1014/rss.xml",  # NPR Politics
            "https://www.politico.eu/feed/",  # Politico Europe
            "https://thehill.com/feed/",  # The Hill
            "https://news.un.org/feed/subscribe/en/news/topic/law-and-crime-prevention/feed/rss.xml",  # UN News – Policy & Law
            "https://feeds.washingtonpost.com/rss/national",  # Washington Post – National
            "https://feeds.washingtonpost.com/rss/politics",  # Washington Post Politics
        ]
    },
    
    "Business": {
        "subcategories": ["Markets", "Corporations & Earnings", "Startups & Entrepreneurship", "Economy and Policy"],
        "feeds": [
            "https://feeds.bbci.co.uk/news/business/rss.xml",  # BBC Business
            "https://www.cnbc.com/id/10001147/device/rss/rss.html",  # CNBC Business
            "https://www.cnbc.com/id/15839135/device/rss/rss.html",  # CNBC Markets
            "https://www.forbes.com/business/feed/",  # Forbes Business
            "https://fortune.com/feed/",  # Fortune
            "https://marketrealist.com/feed/",  # Market Realist
            "https://www.marketwatch.com/rss/",  # MarketWatch
            "https://www.nasdaq.com/feed/rssoutbound?category=Stocks",  # Nasdaq News
            "https://finance.yahoo.com/news/rssindex",  # Yahoo Finance News
        ]
    },
    
    "Technology": {
        "subcategories": ["AI & Machine Learning", "Gadgets & Consumer Tech", "Software & Apps", "Cybersecurity", "Hardware & Infrastructure"],
        "feeds": [
            "https://www.aitrends.com/feed/",  # AI Trends
            "https://www.androidauthority.com/feed/",  # Android Authority
            "https://www.androidpolice.com/feed/",  # Android Police
            "https://feeds.arstechnica.com/arstechnica/gadgets",  # Ars Technica – Gear
            "https://feeds.bbci.co.uk/news/technology/rss.xml",  # BBC Technology
            "https://betakit.com/feed/",  # BetaKit
            "https://betanews.com/feed/",  # BetaNews
            "https://www.bleepingcomputer.com/feed/",  # Bleeping Computer
            "https://www.cbinsights.com/research/feed/",  # CB Insights Research
            "https://www.cnet.com/rss/news/",  # CNET
            "http://rss.cnn.com/rss/cnn_tech.rss",  # CNN Tech
            "https://deepmind.google/blog/rss.xml",  # DeepMind Blog
            "https://www.engadget.com/rss.xml",  # Engadget
            "https://feeds.foxnews.com/foxnews/tech",  # Fox News Tech
            "https://github.blog/feed/",  # GitHub Blog
            "https://security.googleblog.com/feeds/posts/default",  # Google Security Blog
            "https://www.hardwarecanucks.com/feed/",  # Hardware Canucks
            "https://news.ycombinator.com/rss",  # Hacker News
            "https://www.imore.com/rss",  # iMore
            "https://krebsonsecurity.com/feed/",  # Krebs on Security
            "https://www.macstories.net/feed/",  # MacStories
            "https://www.microsoft.com/en-us/research/feed/",  # Microsoft Research Blog – AI
            "https://www.microsoft.com/security/blog/feed/",  # Microsoft Security Blog
            "https://9to5mac.com/feed/",  # 9to5Mac
            "https://www.servethehome.com/feed/",  # ServeTheHome
            "https://www.smashingmagazine.com/feed/",  # Smashing Magazine
            "https://softwareengineeringdaily.com/feed/",  # Software Engineering Daily
            "https://stackoverflow.blog/feed/",  # Stack Overflow Blog
            "https://syncedreview.com/feed/",  # Synced Review
            "https://techcrunch.com/apps/feed/",  # TechCrunch – Apps
            "https://techcrunch.com/tag/artificial-intelligence/feed/",  # TechCrunch – Artificial Intelligence
            "https://techcrunch.com/category/startups/feed/",  # TechCrunch Startups
            "https://www.techradar.com/rss",  # TechRadar
            "https://www.technologyreview.com/topic/artificial-intelligence/feed/",  # MIT Technology Review – AI
            "https://feeds.feedburner.com/TheHackersNews",  # The Hacker News
            "https://thenextweb.com/topic/startups/feed/",  # The Next Web – Startups
            "https://www.theregister.com/hardware/headlines.atom",  # The Register – Hardware
            "https://www.theregister.com/software/headlines.atom",  # The Register – Software
            "https://www.theverge.com/rss/index.xml",  # The Verge
            "https://threatpost.com/feed/",  # Threatpost
            "https://towardsdatascience.com/feed",  # Towards Data Science
            "https://www.tomsguide.com/feeds/all",  # Tom's Guide
            "https://www.tomshardware.com/feeds/all",  # Tom's Hardware
            "https://www.cisa.gov/uscert/ncas/alerts.xml",  # US‑CERT Alerts
            "https://www.zdnet.com/topic/security/rss.xml",  # ZDNet – Security
            "https://www.zdnet.com/topic/software/rss.xml",  # ZDNet – Software
        ]
    },
    
    "Science & Environment": {
        "subcategories": ["Space & Astronomy", "Biology", "Physics & Chemistry", "Research & Academia", "Climate & Weather", "Sustainability", "Conservation & Wildlife"],
        "feeds": [
            "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",  # BBC Science & Environment
            "https://www.carbonbrief.org/feed/",  # Carbon Brief
            "https://cleantechnica.com/feed/",  # CleanTechnica
            "https://www.climate.gov/news-features/feed",  # Climate.gov
            "https://www.esa.int/rssfeed/Our_Activities/Space_News",  # ESA – European Space Agency
            "https://moxie.foxnews.com/google-publisher/science.xml",  # Fox News Science
            "http://www.genestogenomes.org/feed/",  # Genetics Society of America
            "https://www.greenpeace.org/international/feed/",  # Greenpeace – News
            "https://www.janegoodall.org/feed/",  # Jane Goodall Institute
            "https://www.nasa.gov/rss/dyn/breaking_news.rss",  # NASA Breaking News
            "https://www.nature.com/subjects/chemistry.rss",  # Nature – Chemistry
            "https://www.nature.com/ncomms.rss",  # Nature Communications
            "https://www.nature.com/subjects/physics.rss",  # Nature – Physics
            "https://feeds.npr.org/1026/rss.xml",  # NPR Science
            "https://feeds.npr.org/1167/rss.xml",  # NPR Environment
            "https://journals.plos.org/plosbiology/feed/atom",  # PLOS Biology
            "https://www.sciencedaily.com/rss/health_medicine.xml",  # Science Daily – Medicine
            "https://www.space.com/feeds/all",  # Space.com
            "https://spaceflightnow.com/feed/",  # Spaceflight Now
            "https://news.stanford.edu/feed/",  # Stanford News – Science & Technology
            "https://sustainablebrands.com/feed",  # Sustainable Brands
            "https://www.universetoday.com/feed/",  # Universe Today
            "https://yaleclimateconnections.org/feed/",  # Yale Climate Connections
        ]
    },
    
    "Sports": {
        "subcategories": [
            "Football (Soccer)", "American Football", "Basketball", "Baseball", "Cricket",
            "Tennis", "F1", "Boxing", "MMA", "Golf", "Ice hockey", "Rugby",
            "Volleyball", "Table Tennis (Ping Pong)", "Athletics"
        ],
        "feeds": [
            "https://athleticsweekly.com/feed/",  # Athletics Weekly
            "https://www.baseballprospectus.com/feed/",  # Baseball Prospectus
            "https://feeds.bbci.co.uk/sport/athletics/rss.xml",  # BBC Sport – Athletics
            "https://feeds.bbci.co.uk/sport/boxing/rss.xml",  # BBC Sport – Boxing
            "https://feeds.bbci.co.uk/sport/cricket/rss.xml",  # BBC Sport – Cricket
            "https://feeds.bbci.co.uk/sport/formula1/rss.xml",  # BBC Sport – F1
            "https://feeds.bbci.co.uk/sport/football/rss.xml",  # BBC Sport – Football
            "https://feeds.bbci.co.uk/sport/golf/rss.xml",  # BBC Sport – Golf
            "https://feeds.bbci.co.uk/sport/rugby-union/rss.xml",  # BBC Sport – Rugby Union
            "https://feeds.bbci.co.uk/sport/rss.xml",  # BBC Sport
            "https://feeds.bbci.co.uk/sport/tennis/rss.xml",  # BBC Sport – Tennis
            "https://www.boxingnewsonline.net/feed/",  # Boxing News Online
            "https://www.bundesliga.com/en/bundesliga/news/rss",  # Bundesliga – News
            "https://cagesidepress.com/feed/",  # Cageside Press
            "https://www.cbssports.com/rss/headlines/mlb/",  # CBS Sports – MLB
            "https://www.cbssports.com/rss/headlines/nba/",  # CBS Sports – NBA
            "https://www.cbssports.com/rss/headlines/nfl/",  # CBS Sports – NFL
            "https://www.cbssports.com/rss/headlines/nhl/",  # CBS Sports – NHL
            "https://combatpress.com/feed/",  # Combat Press
            "https://www.cricket.co.za/feed/",  # Cricket South Africa
            "https://www.crictracker.com/feed/",  # CricTracker
            "https://www.espn.com/espn/rss/boxing/news",  # ESPN – Boxing
            "https://www.espn.com/espn/rss/rpm/news",  # ESPN – F1
            "https://www.espn.com/espn/rss/mlb/news",  # ESPN – MLB
            "https://www.espn.com/espn/rss/mma/news",  # ESPN – MMA
            "https://www.espn.com/espn/rss/nba/news",  # ESPN – NBA
            "https://www.espn.com/espn/rss/news",  # ESPN
            "https://www.espn.com/espn/rss/nfl/news",  # ESPN – NFL
            "https://www.espn.com/espn/rss/nhl/news",  # ESPN – NHL
            "https://www.espn.com/espn/rss/rugby/news",  # ESPN – Rugby
            "https://www.espn.com/espn/rss/soccer/news",  # ESPN FC
            "https://www.espn.com/espn/rss/tennis/news",  # ESPN – Tennis
            "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",  # ESPNcricinfo
            "https://www.fightnews.com/feed",  # Fightnews.com
            "https://www.formula1.com/content/fom-website/en/latest/all.xml",  # Formula1.com – News
            "https://moxie.foxnews.com/google-publisher/sports.xml",  # Fox News Sports
            "https://www.golfmonthly.com/feed",  # Golf Monthly
            "https://www.golfwrx.com/feed/",  # GolfWRX
            "https://www.theguardian.com/football/rss",  # The Guardian – Football
            "https://www.theguardian.com/sport/formulaone/rss",  # The Guardian – F1
            "https://www.theguardian.com/sport/rugby-union/rss",  # The Guardian – Rugby
            "https://www.theguardian.com/sport/tennis/rss",  # The Guardian – Tennis
            "https://www.ittf.com/feed/",  # ITTF – News
            "https://www.mlbtraderumors.com/feed",  # MLB Trade Rumors
            "https://www.motorsportweek.com/feed/",  # Motorsport Week – F1
            "https://profootballtalk.nbcsports.com/feed/",  # NBC Sports – Pro Football Talk
            "https://www.onefc.com/feed/",  # ONE Championship
            "https://www.racefans.net/feed/",  # RaceFans
            "https://www.sherdog.com/rss/news.xml",  # Sherdog
            "https://www.skysports.com/rss/12040",  # Sky Sports – Football
            "https://tabletenniscoach.me.uk/feed/",  # Table Tennis Coach
            "https://www.ttcanada.ca/feed/",  # Table Tennis Canada
            "https://the-race.com/feed/",  # The Race – F1
            "https://trackandfieldnews.com/feed/",  # Track & Field News
            "https://volleymob.com/feed/",  # Volley Mob
            "https://www.wbaboxing.com/feed",  # WBA – News
            "https://www.worldathletics.org/rss",  # World Athletics – News
            "https://sports.yahoo.com/boxing/news/rss/",  # Yahoo Sports – Boxing
            "https://sports.yahoo.com/golf/news/rss/",  # Yahoo Sports – Golf
            "https://sports.yahoo.com/mlb/rss.xml",  # Yahoo Sports – MLB
            "https://sports.yahoo.com/mma/news/rss/",  # Yahoo Sports – MMA
            "https://sports.yahoo.com/nba/rss.xml",  # Yahoo Sports – NBA
            "https://sports.yahoo.com/nfl/rss.xml",  # Yahoo Sports – NFL
            "https://sports.yahoo.com/nhl/rss.xml",  # Yahoo Sports – NHL
            "https://sports.yahoo.com/soccer/news/rss/",  # Yahoo Sports – Soccer
            "https://sports.yahoo.com/tennis/news/rss/",  # Yahoo Sports – Tennis
        ]
    },
    
    "Arts & Culture": {
        "subcategories": ["Celebrity News", "Gaming", "Film & TV", "Music", "Literature", "Art & Design", "Fashion"],
        "feeds": [
            "https://www.artnews.com/feed/",  # ARTnews
            "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",  # BBC Entertainment & Arts
            "https://www.bbc.com/culture/feed.rss",  # BBC Culture
            "https://www.billboard.com/feed/",  # Billboard – News
            "https://bookriot.com/feed/",  # Book Riot
            "https://consequence.net/feed/",  # Consequence of Sound – News
            "https://www.creativereview.co.uk/feed/",  # Creative Review
            "https://deadline.com/feed/",  # Deadline Hollywood
            "https://www.designboom.com/feed/",  # Designboom
            "https://www.dezeen.com/feed/",  # Dezeen
            "https://www.elle.com/rss/all.xml",  # Elle
            "https://www.elle.com/rss/fashion.xml",  # Elle – Fashion
            "https://www.gamespot.com/feeds/news/",  # GameSpot
            "https://www.giantbomb.com/feeds/news/",  # Giant Bomb
            "https://www.theguardian.com/artanddesign/rss",  # The Guardian – Art and Design
            "https://www.theguardian.com/books/rss",  # The Guardian – Books
            "https://www.theguardian.com/film/rss",  # The Guardian – Film
            "https://www.theguardian.com/music/rss",  # The Guardian – Music
            "https://www.hellomagazine.com/rss/",  # Hello Magazine
            "https://www.highsnobiety.com/feed/",  # Highsnobiety
            "https://www.hollywoodreporter.com/c/movies/feed/",  # The Hollywood Reporter – Film
            "https://www.hollywoodreporter.com/feed/",  # The Hollywood Reporter
            "https://lithub.com/feed/",  # Literary Hub
            "https://www.nintendolife.com/feeds/latest",  # Nintendo Life
            "https://www.nme.com/news/music/feed",  # NME – Music News
            "https://feeds.npr.org/1008/rss.xml",  # NPR Music
            "https://feeds.npr.org/1032/rss.xml",  # NPR – Books
            "https://feeds.npr.org/1039/rss.xml",  # NPR Movies
            "https://feeds.npr.org/1045/rss.xml",  # NPR Pop Culture
            "https://feeds.npr.org/1048/rss.xml",  # NPR Arts & Life
            "https://feeds.npr.org/1128/rss.xml",  # NPR Music News
            "https://feeds.npr.org/1138/rss.xml",  # NPR Arts
            "https://pagesix.com/feed/",  # Page Six
            "https://blog.playstation.com/feed/",  # PlayStation Blog
            "https://www.polygon.com/rss/index.xml",  # Polygon – News
            "https://www.rockpapershotgun.com/feed/news",  # Rock Paper Shotgun
            "https://www.rollingstone.com/culture/feed/",  # Rolling Stone – Culture
            "https://www.rollingstone.com/music/feed/",  # Rolling Stone – Music
            "https://www.rollingstone.com/tv-movies/feed/",  # Rolling Stone – Film & TV
            "https://screenrant.com/feed/",  # Screen Rant
            "https://www.stereogum.com/feed/",  # Stereogum
            "https://www.tmz.com/rss.xml",  # TMZ
            "https://www.usmagazine.com/feed/",  # Us Weekly
            "https://variety.com/v/film/feed/",  # Variety – Film & TV
            "https://www.vogue.com/feed/rss",  # Vogue
            "https://news.xbox.com/feed/",  # Xbox Wire
        ]
    },
    
    "Health": {
        "subcategories": ["Public Health", "Medicine & Healthcare", "Fitness & Wellness", "Mental Health"],
        "feeds": [
            "https://feeds.bbci.co.uk/news/health/rss.xml",  # BBC Health
            "https://www.theguardian.com/society/health/rss",  # The Guardian – Health
            "https://www.theguardian.com/society/mental-health/rss",  # The Guardian – Mental Health
            "https://www.gottman.com/blog/feed/",  # The Gottman Institute
            "https://www.menshealth.com/rss/all.xml/",  # Men's Health
            "https://www.mhanational.org/blog/feed",  # Mental Health America
            "https://www.nhs.uk/feeds/news.xml",  # NHS – News
            "https://feeds.npr.org/1128/rss.xml",  # NPR Health
            "https://www.gov.uk/government/organisations/public-health-england.atom",  # Public Health England
            "https://news.un.org/feed/subscribe/en/news/topic/health/feed/rss.xml",  # UN News – Health
            "https://www.womenshealthmag.com/rss/all.xml/",  # Women's Health
            "https://news.yahoo.com/rss/health",  # Yahoo Health
            "https://www.yogajournal.com/feed/",  # Yoga Journal
        ]
    },
    
    "Lifestyle": {
        "subcategories": ["Travel", "Food & Dining", "Home & Garden", "Relationships & Family", "Hobbies"],
        "feeds": [
            "https://www.apartmenttherapy.com/main.rss",  # Apartment Therapy
            "https://www.backpacker.com/feed/",  # Backpacker Magazine
            "https://www.bbcgoodfood.com/rss",  # BBC Good Food
            "https://www.bbc.com/travel/feed.rss",  # BBC Travel
            "https://www.cntraveler.com/feed/rss",  # Condé Nast Traveler
            "https://www.countryliving.com/rss/all.xml/",  # Country Living
            "https://www.eater.com/rss/index.xml",  # Eater
            "https://www.fatherly.com/feed",  # Fatherly – Parenting
            "https://www.finegardening.com/feed",  # Fine Gardening
            "https://www.finewoodworking.com/feed",  # Fine Woodworking
            "https://moxie.foxnews.com/google-publisher/travel.xml",  # Fox News Travel
            "https://www.gardenersworld.com/feed/",  # Gardeners' World
            "https://www.greenhousegrower.com/feed/",  # Greenhouse Grower
            "https://www.theguardian.com/lifeandstyle/family/rss",  # The Guardian – Family
            "https://www.houseplantjournal.com/feed/",  # Houseplant Journal
            "https://www.mother.ly/feed/",  # Motherly – Parenting
            "https://feeds.npr.org/1053/rss.xml",  # NPR Food
            "https://cooking.nytimes.com/rss/recipelists",  # The New York Times – Cooking
            "https://photographylife.com/feed",  # Photography Life
            "https://www.scarymommy.com/feed/",  # Scary Mommy
            "https://www.tastingtable.com/feed/",  # Tasting Table
            "https://www.yahoo.com/lifestyle/rss",  # Yahoo Lifestyle
        ]
    }
}

def get_all_feeds() -> List[str]:
    """Get all RSS feed URLs as a flat list"""
    all_feeds = []
    for category_data in RSS_FEEDS_CONFIG.values():
        all_feeds.extend(category_data["feeds"])
    return all_feeds

def get_feed_category(feed_url: str) -> str:
    """Get the category for a specific feed URL"""
    for category, category_data in RSS_FEEDS_CONFIG.items():
        if feed_url in category_data["feeds"]:
            return category
    return "General"

def get_category_subcategories(category: str) -> List[str]:
    """Get subcategories for a specific category"""
    if category in RSS_FEEDS_CONFIG:
        return RSS_FEEDS_CONFIG[category]["subcategories"]
    return []

def get_categories() -> List[str]:
    """Get all available categories"""
    return list(RSS_FEEDS_CONFIG.keys())
