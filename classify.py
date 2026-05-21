import pandas as pd
import re
from pathlib import Path

# Keywords für Geschlechterklassifizierung
MALE_KEYWORDS = {
    # Pronomen und Endungen
    'er', 'herr', 'herren',
    # Berufe und Rollen (männlich)
    'pfarrer', 'bürgermeister', 'dichter', 'komponist', 'dirigent', 'bauer',
    'fischer', 'müller', 'schuster', 'schmied', 'maler', 'bildhauer',
    'schriftsteller', 'journalist', 'kaufmann', 'händler', 'krämer',
    'meister', 'zunftmeister', 'zunftherr', 'hofmeister', 'schulmeister',
    # Familiäre Begriffe
    'bruder', 'sohn', 'vater', 'großvater', 'onkel', 'ehemann',
    'mann', 'prince', 'könig', 'kaiser', 'graf', 'freiherr', 'herzog',
    # Deutsche Vornamen (männlich)
    'hans', 'peter', 'johannes', 'jakob', 'friedrich', 'georg', 'wilhelm',
    'ernst', 'heinrich', 'karl', 'kurt', 'otto', 'franz', 'josef', 'paul',
    'martin', 'thomas', 'ludwig', 'franz', 'rudolf', 'theodor', 'Frizz',
}

FEMALE_KEYWORDS = {
    # Pronomen und Bezeichnungen
    'frau', 'fräulein',
    # Berufe und Rollen (weiblich)
    'ärztin', 'lehrerin', 'schriftstellerin', 'künstlerin', 'malerin',
    'bildhauerin', 'dichterin', 'komponistin', 'sängerin', 'musikerin',
    'tänzerin', 'schauspielerin', 'autorin', 'journalistin', 'hebamme',
    # Familiäre Begriffe
    'schwester', 'tochter', 'mutter', 'großmutter', 'tante', 'ehefrau',
    'princess', 'königin', 'kaiserin', 'gräfin', 'herzogin',
    # Deutsche Vornamen (weiblich)
    'anna', 'maria', 'marie', 'hannah', 'elisabet', 'sophie', 'clara',
    'ida', 'rosa', 'bertha', 'louise', 'käthe', 'martha',
    'helene', 'pauline', 'caroline', 'josephine', 'christine', 'margarete',
    'barbara', 'helena', 'angela', 'brunhilde', 'gerda', 'ingrid', 'dora',
    'meret', 'gretel', 'emilie', 'julia', 'trudi', 'urbana', 'Dora', 
    # Endungen (mindestens 4 Buchstaben für sicheres Matching)
    '-erin',
}

# Kategorien Keywords (Berufsgruppen, Gebäude, Epochen)
PROFESSIONS = {
    'wissenschaft': {
        'professor', 'doktor', 'physiker', 'mathematiker', 'chemiker',
        'biologe', 'naturwissenschaft', 'gelehrte', 'forscher', 'wissenschaftler',
        'astronome', 'geologe', 'botaniker', 'zoolog', 'arzt', 'ärztin',
        'medizin', 'pharmazie', 'universität', 'akademie',
    },
    'kunst': {
        'maler', 'bildhauer', 'künstler', 'kunstgewerbe', 'kunsthandwerker',
        'kunstmaler', 'kunstbildner', 'kunstschule', 'kunstweg',
        'kunsthalle', 'galerie', 'kunstmuseum', 'kunstsammler',
        'dichter', 'schriftsteller', 'schriftstellerei', 'literatur',
        'komponist', 'musiker', 'musikant', 'sänger', 'gesang',
        'tänzer', 'schauspiel', 'theater', 'bühne', 'opernhaus',
    },
    'handwerk': {
        'bauer', 'fischer', 'müller', 'schuster', 'schmied', 'zimmer',
        'zimmermann', 'maurer', 'steinmetz', 'tischler', 'schreiner',
        'schlosser', 'schmiede', 'werkstatt', 'handwerk', 'handwerker',
        'gewerbetreiber', 'weber', 'leineweber', 'schneider',
    },
    'handel': {
        'kaufmann', 'händler', 'krämer', 'verkäufer', 'kramerstoffe',
        'handel', 'markt', 'messe', 'mustermesse', 'waren', 'gewandhaus',
    },
    'religion': {
        'pfarrer', 'priester', 'dompfarrer', 'kirche', 'dom', 'kapelle',
        'kloster', 'münster', 'jesuitenweg', 'johanneskirche', 'pauluskirche',
        'martinskirche', 'theodor', 'martin', 'johannes', 'jacob', 'jakob',
        'elisabet', 'felix', 'nikolaus', 'franziskanerplatz',
    },
    'politik': {
        'bürgermeister', 'zunftmeister', 'rat', 'rathaus', 'ratsherr',
        'zunftherr', 'bürger', 'meister', 'präsident', 'kanzler',
    },
    'adel': {
        'könig', 'königin', 'kaiser', 'kaiserin', 'prinz', 'prinzessin',
        'graf', 'gräfin', 'freiherr', 'freifrau', 'baron', 'baronin',
        'herzog', 'herzogin', 'führer', 'fürstin', 'burgunder', 'österreich',
    },
    'militär': {
        'general', 'oberst', 'major', 'hauptmann', 'leutnant', 'soldat',
        'kriegrat', 'feldherr', 'festung', 'krieg', 'fort', 'Stadtbefestigung', 
    },
    'Ortschaft': {
        'basel', 'bern', 'zürich', 'luzern', 'st.gallen', 'appenzell',
        'wallis', 'graubünden', 'tessin', 'jura', 'fribourg',
        'biel', 'solothurn', 'aarau', 'liestal', 'bellinzona',
        'deutsches', 'belgien', 'holland', 'frankreich', 'italien',
        'schwarzwald', 'vogesen', 'jura', 'alpen', 'berg', 'tal', 'wiese',
 },
    'Geografie': {
         'vogesen', 'jura', 'alpen', 'berg', 'tal', 'wiese',
    
    },
    'gebäude': {
        'schloss', 'burg', 'festung', 'turm', 'brücke', 'rathaus',
        'kirche', 'dom', 'kapelle', 'kloster', 'münster', 'opernhaus',
        'theater', 'galerie', 'museum', 'bibliothek', 'archiv',
        'arsenalstrasse', 'arsenal', 'zeughaus', 'kaserne',
        'spital', 'spitalgasse', 'wasenplatz', 'waaghaus',
        'zunfthaus', 'gildenhaus', 'gilde', 'gewandhaus',
        'marktplatz', 'markthalle', 'stall', 'magazin',
        'mühle', 'darre', 'backhaus', 'brauerei', 'brennerei',
        'färberei', 'tuchhandel', 'tuchschau', 'walke',
    },
    'epoche': {
        # Mittelalter / Frühmittelalter
        'mittelalter', 'gotik', 'romanik', '1100', '1200', '1300',
        '1400', 'mittelalterlich', 'gotisch', 'romanisch',
        # Renaissance
        'renaissance', '1500', '1550',
        # Barock
        'barock', '1600', '1650', '1700', 'barocke',
        # Klassizismus / Aufklärung
        'klassizismus', 'aufklärung', '1750', '1800',
        # 19. Jahrhundert
        'neogotik', 'historismus', '1850', '1900', 'biedermeier',
        # 20. Jahrhundert
        'moderne', 'jugendstil', 'art deco', 'gründerzeit',
        '1920', '1930', '1950', '1960', '1970',
        # Zeitliche Marker
        'antike', 'römisch', 'helvetier', 'kelten',
    },
    'tiere': {
        'wolf', 'hirsch', 'fuchs', 'löwe',
        'eichhorn', 'wild', 'pferd', 'ross', 'hund',
        'vogel', 'adler', 'falke', 'ente',
        'fisch', 'forelle',
    },
    'pflanzen': {
        'eiche', 'eich', 'linde', 'birke', 'erle', 'erlen',
        'tanne', 'buche', 'kastanie', 'ahorn', 'ulme',
        'rose', 'weide', 'busch',
        'rebe', 'wein', 'Baum', 'Pflanze'
        'baum', 'wald', 'gras', 'wiese', 'feld', 'garten',
    },
    'gewässer': {
        # Flüsse in Basel
        'rhein', 'birs', 'birsig', 'wiese',

        'bach', 'fluss', 'teich', 'quelle', 'brunnen',
        'wasser', 'zufluss',
    },
}

def _count_keyword_matches(keywords: set, text: str) -> int:
    """Zähle Keyword-Matches.

    - Endung-Keywords (mit '-' prefix): nur am Wort-ENDE matchen
    - Kurze Keywords (< 4 Buchstaben): exakte Wort-Grenzen
    - Längere Keywords (>= 4 Buchstaben): Wort-Anfang matching (für Compound-Wörter)
    """
    count = 0
    for kw in keywords:
        kw_str = kw.lower()
        if kw_str.startswith('-'):
            # Endung-Keyword: muss am Wortende stehen
            ending = kw_str.lstrip('-')
            pattern = re.escape(ending) + r'\b'
        elif len(kw_str) < 4:
            # Kurze Keywords nur als ganze Wörter
            pattern = r'\b' + re.escape(kw_str) + r'\b'
        else:
            # Längere Keywords ab Wort-Anfang (für Compound-Wörter)
            pattern = r'\b' + re.escape(kw_str)
        if re.search(pattern, text):
            count += 1
    return count

def classify_gender(street_name: str, explanation: str) -> str:
    """Klassifiziere Strasse als männlich, weiblich oder neutral (nicht zuordenbar)."""
    combined_text = f"{street_name} {explanation}".lower()

    male_score = _count_keyword_matches(MALE_KEYWORDS, combined_text)
    female_score = _count_keyword_matches(FEMALE_KEYWORDS, combined_text)

    # Bonus für -in Endung in Strasse (typisch weiblich)
    if re.search(r'-in(nen)?$', street_name.lower()):
        female_score += 2

    # Nur klare Zuordnungen - sonst "neutral"
    if male_score > 0 and male_score > female_score:
        return 'männlich'
    elif female_score > 0 and female_score > male_score:
        return 'weiblich'
    else:
        return 'neutral'

def classify_profession(street_name: str, explanation: str) -> str:
    """Klassifiziere Strasse in Kategorie (Berufsgruppe, Gebäude, etc.)."""
    combined_text = f"{street_name} {explanation}".lower()

    profession_scores = {}
    for profession, keywords in PROFESSIONS.items():
        if profession != 'epoche':  # Epoche separat
            score = _count_keyword_matches(keywords, combined_text)
            if score > 0:
                profession_scores[profession] = score

    if profession_scores:
        return max(profession_scores, key=profession_scores.get)
    return 'keine Kategorie'

def year_to_epoch(year) -> str:
    """Wandle eine Jahreszahl in eine Epoche um."""
    if pd.isna(year):
        return None
    try:
        y = int(year)
    except (ValueError, TypeError):
        return None

    if y < 1500:
        return 'Mittelalter'
    elif y < 1600:
        return 'Renaissance'
    elif y < 1750:
        return 'Barock'
    elif y < 1830:
        return 'Klassizismus'
    elif y < 1900:
        return '19. Jahrhundert'
    elif y < 1945:
        return 'Moderne'
    else:
        return 'Zeitgenössisch'

def classify_epoch(street_name: str, explanation: str,
                   erstmals_erwaehnt=None, amtlich_benannt=None) -> str:
    """Klassifiziere Strasse in Epoche.

    Priorität:
    1. Jahreszahl aus 'Erstmals erwähnt' (historischer Ursprung)
    2. Jahreszahl aus 'Amtlich benannt' (Fallback)
    3. Keyword-Matching aus Text
    """
    # Erst Jahre prüfen
    epoch_from_year = year_to_epoch(erstmals_erwaehnt)
    if epoch_from_year:
        return epoch_from_year

    epoch_from_year = year_to_epoch(amtlich_benannt)
    if epoch_from_year:
        return epoch_from_year

    # Fallback: Keyword-Matching
    combined_text = f"{street_name} {explanation}".lower()
    epoch_keywords = PROFESSIONS.get('epoche', {})
    score = _count_keyword_matches(epoch_keywords, combined_text)

    if score > 0:
        if 'mittelalter' in combined_text or 'gotik' in combined_text:
            return 'Mittelalter'
        elif 'renaissance' in combined_text:
            return 'Renaissance'
        elif 'barock' in combined_text:
            return 'Barock'
        elif 'klassizismus' in combined_text or 'aufklärung' in combined_text:
            return 'Klassizismus'
        elif 'jugendstil' in combined_text or 'historismus' in combined_text:
            return '19. Jahrhundert'
        elif 'moderne' in combined_text:
            return 'Moderne'

    return 'keine Angabe'

def process_data():
    """Hauptpipeline: CSV einlesen, klassifizieren, speichern."""
    csv_path = Path(__file__).parent / '100189_raw.csv'

    # CSV einlesen (Delimiter ist ;)
    df = pd.read_csv(csv_path, delimiter=';', encoding='utf-8')

    print(f"CSV geladen: {len(df)} Strassen")

    # Beide Erklärungszeilen kombinieren
    def get_explanation(row):
        z1 = '' if pd.isna(row['Erklärung erste Zeile']) else str(row['Erklärung erste Zeile'])
        z2 = '' if pd.isna(row['Erklärung zweite Zeile']) else str(row['Erklärung zweite Zeile'])
        return f"{z1} {z2}".strip()

    df['_explanation'] = df.apply(get_explanation, axis=1)

    # Klassifizierungen hinzufügen
    df['Geschlecht'] = df.apply(
        lambda row: classify_gender(row['Strassenname'], row['_explanation']),
        axis=1
    )

    df['Kategorie'] = df.apply(
        lambda row: classify_profession(row['Strassenname'], row['_explanation']),
        axis=1
    )

    df['Epoche'] = df.apply(
        lambda row: classify_epoch(
            row['Strassenname'],
            row['_explanation'],
            erstmals_erwaehnt=row.get('Erstmals erwähnt'),
            amtlich_benannt=row.get('Amtlich benannt'),
        ),
        axis=1
    )

    # Temporäre Spalte entfernen
    df = df.drop(columns=['_explanation'])

    # Ausgabe
    output_path = Path(__file__).parent / '100189_classified.csv'
    df.to_csv(output_path, sep=';', encoding='utf-8', index=False)

    print(f"Klassifiziert und gespeichert: {output_path}")

    # Statistiken
    print("\n=== Geschlechterverteilung ===")
    print(df['Geschlecht'].value_counts())

    print("\n=== Kategorien ===")
    print(df['Kategorie'].value_counts())

    print("\n=== Epochen ===")
    print(df['Epoche'].value_counts())

    # Beispiele
    print("\n=== Beispiele ===")
    print(df[['Strassenname', 'Geschlecht', 'Kategorie', 'Epoche']].head(20))

if __name__ == '__main__':
    process_data()
