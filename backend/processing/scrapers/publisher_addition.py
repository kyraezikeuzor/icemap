import csv
import re
from urllib.parse import urlparse

CSV_PATH = '/Users/jackvu/Desktop/latex_projects/icemap/data/distilled_data/aggregated_incidents.csv'

# Top 3 newspapers from the top 50 US cities (by population, 2024)
# This is a non-exhaustive, editable list. Add more as needed.
DOMAIN_TO_PUBLISHER = {
    # New York
    r'nytimes\.com': 'New York Times',
    r'nypost\.com': 'New York Post',
    r'nydailynews\.com': 'New York Daily News',
    # Los Angeles
    r'latimes\.com': 'Los Angeles Times',
    r'dailynews\.com': 'Los Angeles Daily News',
    r'labusinessjournal\.com': 'Los Angeles Business Journal',
    # Chicago
    r'chicagotribune\.com': 'Chicago Tribune',
    r'suntimes\.com': 'Chicago Sun-Times',
    r'dailyherald\.com': 'Daily Herald',
    # Houston
    r'houstonchronicle\.com': 'Houston Chronicle',
    r'chron\.com': 'Houston Chronicle',
    r'houstonpress\.com': 'Houston Press',
    # Phoenix
    r'azcentral\.com': 'The Arizona Republic',
    r'phoenixnewtimes\.com': 'Phoenix New Times',
    r'eastvalleytribune\.com': 'East Valley Tribune',
    # Philadelphia
    r'inquirer\.com': 'Philadelphia Inquirer',
    r'phillytrib\.com': 'Philadelphia Tribune',
    r'phillyvoice\.com': 'PhillyVoice',
    # San Antonio
    r'expressnews\.com': 'San Antonio Express-News',
    r'sanantoniomag\.com': 'San Antonio Magazine',
    r'sacurrent\.com': 'San Antonio Current',
    # San Diego
    r'sandiegouniontribune\.com': 'San Diego Union-Tribune',
    r'voiceofsandiego\.org': 'Voice of San Diego',
    r'timesofsandiego\.com': 'Times of San Diego',
    # Dallas
    r'dallasnews\.com': 'Dallas Morning News',
    r'dallasobserver\.com': 'Dallas Observer',
    r'nbcdfw\.com': 'NBC DFW',
    # San Jose
    r'mercurynews\.com': 'The Mercury News',
    r'thesixfifty\.com': 'The Six Fifty',
    r'sanjoseinside\.com': 'San Jose Inside',
    # Austin
    r'statesman\.com': 'Austin American-Statesman',
    r'austinchronicle\.com': 'The Austin Chronicle',
    r'kut\.org': 'KUT News',
    # Jacksonville
    r'jacksonville\.com': 'The Florida Times-Union',
    r'jaxdailyrecord\.com': 'Jacksonville Daily Record',
    r'firstcoastnews\.com': 'First Coast News',
    # San Francisco
    r'sfchronicle\.com': 'San Francisco Chronicle',
    r'sfexaminer\.com': 'San Francisco Examiner',
    r'sfgate\.com': 'SFGate',
    # Columbus
    r'dispatch\.com': 'The Columbus Dispatch',
    r'columbusalive\.com': 'Columbus Alive',
    r'thisweeknews\.com': 'ThisWeek Community News',
    # Fort Worth
    r'star-telegram\.com': 'Fort Worth Star-Telegram',
    r'fwweekly\.com': 'Fort Worth Weekly',
    r'fortworthbusiness\.com': 'Fort Worth Business Press',
    # Indianapolis
    r'indystar\.com': 'The Indianapolis Star',
    r'nuvo\.net': 'NUVO',
    r'indianapolisrecorder\.com': 'Indianapolis Recorder',
    # Charlotte
    r'charlotteobserver\.com': 'The Charlotte Observer',
    r'charlottepost\.com': 'The Charlotte Post',
    r'qcnerve\.com': 'Queen City Nerve',
    # Seattle
    r'seattletimes\.com': 'The Seattle Times',
    r'seattlepi\.com': 'Seattle Post-Intelligencer',
    r'theseattlemedium\.com': 'The Seattle Medium',
    # Denver
    r'denverpost\.com': 'The Denver Post',
    r'westword\.com': 'Westword',
    r'coloradopolitics\.com': 'Colorado Politics',
    # Washington
    r'washingtonpost\.com': 'Washington Post',
    r'washingtontimes\.com': 'Washington Times',
    r'dcist\.com': 'DCist',
    # Boston
    r'bostonglobe\.com': 'The Boston Globe',
    r'bostonherald\.com': 'Boston Herald',
    r'baystatebanner\.com': 'Bay State Banner',
    # El Paso
    r'elpasotimes\.com': 'El Paso Times',
    r'kfoxtv\.com': 'KFOX14',
    r'cbs4local\.com': 'CBS4 Local',
    # Nashville
    r'tennessean\.com': 'The Tennessean',
    r'nashvillescene\.com': 'Nashville Scene',
    r'williamsonherald\.com': 'Williamson Herald',
    # Detroit
    r'detroitnews\.com': 'The Detroit News',
    r'detroitfreepress\.com': 'Detroit Free Press',
    r'metrotimes\.com': 'Detroit Metro Times',
    # Oklahoma City
    r'oklahoman\.com': 'The Oklahoman',
    r'journalrecord\.com': 'The Journal Record',
    r'nondoc\.com': 'NonDoc',
    # Portland
    r'oregonlive\.com': 'The Oregonian',
    r'portlandtribune\.com': 'Portland Tribune',
    r'willametteweek\.com': 'Willamette Week',
    # Las Vegas
    r'reviewjournal\.com': 'Las Vegas Review-Journal',
    r'lasvegassun\.com': 'Las Vegas Sun',
    r'lasvegasweekly\.com': 'Las Vegas Weekly',
    # Memphis
    r'commercialappeal\.com': 'The Commercial Appeal',
    r'dailymemphian\.com': 'Daily Memphian',
    r'memphisflyer\.com': 'Memphis Flyer',
    # Louisville
    r'courier-journal\.com': 'The Courier-Journal',
    r'leoweekly\.com': 'LEO Weekly',
    r'voice-tribune\.com': 'The Voice-Tribune',
    # Baltimore
    r'baltimoresun\.com': 'The Baltimore Sun',
    r'baltimorebrew\.com': 'Baltimore Brew',
    r'baltimorefishbowl\.com': 'Baltimore Fishbowl',
    # Milwaukee
    r'jsonline\.com': 'Milwaukee Journal Sentinel',
    r'shepherdexpress\.com': 'Shepherd Express',
    r'urbanmilwaukee\.com': 'Urban Milwaukee',
    # Albuquerque
    r'abqjournal\.com': 'Albuquerque Journal',
    r'krqe\.com': 'KRQE News',
    r'kob\.com': 'KOB 4',
    # Tucson
    r'tucson\.com': 'Arizona Daily Star',
    r'tucsonweekly\.com': 'Tucson Weekly',
    r'azpm\.org': 'Arizona Public Media',
    # Fresno
    r'fresnobee\.com': 'The Fresno Bee',
    r'thebusinessjournal\.com': 'The Business Journal',
    r'gvwire\.com': 'GV Wire',
    # Mesa
    r'eastvalleytribune\.com': 'East Valley Tribune',
    r'azcentral\.com': 'The Arizona Republic',
    r'ktar\.com': 'KTAR News',
    # Sacramento
    r'sacbee\.com': 'The Sacramento Bee',
    r'sacobserver\.com': 'The Sacramento Observer',
    r'newsreview\.com': 'Sacramento News & Review',
    # Atlanta
    r'ajc\.com': 'The Atlanta Journal-Constitution',
    r'atlantamagazine\.com': 'Atlanta Magazine',
    r'creativeloafing\.com': 'Creative Loafing',
    # Kansas City
    r'kansascity\.com': 'The Kansas City Star',
    r'kcbeacon\.org': 'The Beacon',
    r'kcur\.org': 'KCUR 89.3',
    # Colorado Springs
    r'gazette\.com': 'The Gazette',
    r'csindy\.com': 'Colorado Springs Independent',
    r'coloradospringsbusinessjournal\.com': 'Colorado Springs Business Journal',
    # Miami
    r'miamiherald\.com': 'Miami Herald',
    r'miaminewtimes\.com': 'Miami New Times',
    r'southfloridatimes\.com': 'South Florida Times',
    # Raleigh
    r'newsobserver\.com': 'The News & Observer',
    r'indyweek\.com': 'Indy Week',
    r'triangletribune\.com': 'The Triangle Tribune',
    # Omaha
    r'omaha\.com': 'Omaha World-Herald',
    r'thereader\.com': 'The Reader',
    r'leavenworthtimes\.com': 'Leavenworth Times',
    # Long Beach
    r'presstelegram\.com': 'Long Beach Press-Telegram',
    r'lbpost\.com': 'Long Beach Post',
    r'gazettes\.com': 'Gazettes',
    # Virginia Beach
    r'pilotonline\.com': 'The Virginian-Pilot',
    r'dailypress\.com': 'Daily Press',
    r'virginiabusiness\.com': 'Virginia Business',
    # Oakland
    r'eastbaytimes\.com': 'East Bay Times',
    r'oaklandpost\.org': 'Oakland Post',
    r'oaklandside\.org': 'The Oaklandside',
    # Minneapolis
    r'startribune\.com': 'Star Tribune',
    r'minnpost\.com': 'MinnPost',
    r'southwestjournal\.com': 'Southwest Journal',
    # Tulsa
    r'tulsaworld\.com': 'Tulsa World',
    r'tulsapeople\.com': 'TulsaPeople',
    r'urbantulsa\.com': 'Urban Tulsa',
    # Arlington
    r'star-telegram\.com': 'Fort Worth Star-Telegram',
    r'arlnow\.com': 'ARLnow',
    r'insidenova\.com': 'InsideNoVa',
    # Tampa
    r'tampabay\.com': 'Tampa Bay Times',
    r'tampamagazines\.com': 'Tampa Magazines',
    r'cltampa\.com': 'Creative Loafing Tampa',
    # New Orleans
    r'nola\.com': 'The Times-Picayune',
    r'theadvocate\.com': 'The Advocate',
    r'gambitweekly\.com': 'Gambit',
    # Wichita
    r'kansas\.com': 'The Wichita Eagle',
    r'wichitamag\.com': 'Wichita Magazine',
    r'kansasreflector\.com': 'Kansas Reflector',
    # Cleveland
    r'cleveland\.com': 'The Plain Dealer',
    r'crainscleveland\.com': "Crain's Cleveland Business",
    r'scene\.com': 'Cleveland Scene',
    # Bakersfield
    r'bakersfield\.com': 'The Bakersfield Californian',
    r'kget\.com': 'KGET 17',
    r'bakersfieldlife\.com': 'Bakersfield Life',
    # Aurora
    r'aurorasentinel\.com': 'Aurora Sentinel',
    r'auroragov\.org': 'AuroraGov',
    r'coloradopolitics\.com': 'Colorado Politics',
    # National/Other
    r'ice\.gov': 'ICE.gov',
    r'reuters\.com': 'Reuters',
    r'apnews\.com': 'Associated Press',
    r'cnn\.com': 'CNN',
    r'foxnews\.com': 'Fox News',
    r'nbcnews\.com': 'NBC News',
    r'abcnews\.go\.com': 'ABC News',
    r'cbsnews\.com': 'CBS News',
    r'wsj\.com': 'Wall Street Journal',
}

def extract_publisher_from_url(url):
    try:
        domain = urlparse(url).netloc.lower()
        for pattern, publisher in DOMAIN_TO_PUBLISHER.items():
            if re.search(pattern, domain):
                return publisher
        return "Other"
    except Exception:
        return "Other"

def main():
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
        fieldnames = rows[0].keys()
        # Add publisher_name if not present
        if 'publisher_name' not in fieldnames:
            fieldnames = list(fieldnames) + ['publisher_name']

    for row in rows:
        url = row.get('url', '')
        row['publisher_name'] = extract_publisher_from_url(url)

    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

if __name__ == '__main__':
    main()
