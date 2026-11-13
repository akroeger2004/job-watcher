"""Is a posting located in the United States?

The history keeps only US-based postings. The raw files keep everything each board returned,
so this rule can be changed and the history rebuilt without refetching anything.

The decision is made from the location text, in this order:
  1. an explicit "United States" means US;
  2. a country name, or a Canadian province abbreviation, rules a place out;
  3. a US state (abbreviation or name) means US, even for towns that share a foreign
     name ("London, KY");
  4. a well-known foreign city rules a place out;
  5. a well-known US city written without a state means US.
Anything left over (empty, "Multiple locations", an unknown place) is not counted as US.
"""
import re

US_ABBR = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR".split()

# case-sensitive on purpose: "In" is not Indiana
_ABBR = re.compile(r"(?:^|[\s,/(-])(" + "|".join(US_ABBR) + r")(?=$|[\s,/)-])")
_PROVINCE = re.compile(r"(?:^|[\s,;/(-])(ON|BC|QC|AB|NS|NB|MB|SK|PE|NL)(?=$|[\s,;/)-])")
_MORE = re.compile(r"\(\+\d+ more\)")
_US_STATE = re.compile(r'''\b(alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware|florida|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont|virginia|washington|west virginia|wisconsin|wyoming|puerto rico|district of columbia|georgia)\b''', re.I)
_US_WORD = re.compile(r'''\b(united states|usa|u\.s\.a?\.?)(?!\w)''', re.I)
_COUNTRY = re.compile(r'''\b(united kingdom|uk|england|scotland|wales|ireland|india|china|hong kong|japan|singapore|philippines|poland|germany|france|netherlands|spain|switzerland|luxembourg|canada|quebec|british columbia|alberta|brazil|argentina|colombia|chile|peru|australia|new zealand|israel|emirates|uae|korea|taiwan|malaysia|thailand|vietnam|indonesia|italy|belgium|sweden|norway|denmark|finland|austria|czech|romania|hungary|portugal|greece|turkey(?! plant)|egypt|south africa|nigeria|kenya|saudi arabia|qatar|bahrain|costa rica|panama|prince edward island|nova scotia|new brunswick|manitoba|saskatchewan|newfoundland)\b|(?<!new )\bmexico\b|\bontario\b(?!,?\s*CA\b)''', re.I)
_FOREIGN_CITY = re.compile(r'''\b(london|mumbai|bangalore|bengaluru|hyderabad|gurugram|gurgaon|chennai|pune|noida|tokyo|manila|cluj|edinburgh|glasgow|krakow|warsaw|warszawa|gdansk|toronto|nottingham|bournemouth|dublin|kilkenny|sydney|melbourne|frankfurt|paris|geneve|geneva|zurich|shanghai|beijing|shenzhen|hangzhou|seoul|taipei|kuala lumpur|buenos aires|sao paulo|alabang|tbilisi|eng)\b''', re.I)
_US_CITY = re.compile(r'''\b(arlington|pnc plaza|tysons corner|boston|dallas|fort worth|new york|nyc|chicago|tempe|charlotte|fort mill(?:charlotte)?|san francisco|houston|austin|atlanta|denver|seattle|los angeles|philadelphia|pittsburgh|minneapolis|miami|phoenix|irving|plano|columbus|cleveland|princeton|wilmington|jersey city|newark|mclean|richmond|nashville|san antonio|san diego|san jose|baltimore|washington|detroit|st\.? louis|kansas city|salt lake city|las vegas|portland|raleigh|tampa|orlando|jacksonville|indianapolis|cincinnati|milwaukee|omaha|little rock|bentonville|springdale|rogers|fayetteville)\b''', re.I)


def is_us(location):
    """True when the location text says the posting is in the United States."""
    text = _MORE.sub("", location or "").strip()
    if not text:
        return False
    if _US_WORD.search(text):
        return True
    if re.search(r"\btbilisi\b", text, re.I):  # Georgia the country
        return False
    if _COUNTRY.search(text) or _PROVINCE.search(text):
        return False
    if _ABBR.search(text) or _US_STATE.search(text):
        return True
    if _FOREIGN_CITY.search(text):
        return False
    return bool(_US_CITY.search(text))
