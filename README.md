# GAM Bakker Portbase import

Functioneel en technisch ontwerp | Versie 1.2 | 7 oktober 2026

## Functioneel ontwerp

De applicatie helpt medewerkers om klant-PDF’s om te zetten naar het Portbase-importbestand. Uploaden, controleren en aanvullen gebeurt op één pagina. Dit ontwerp beschrijft de huidige lokale versie en de voorwaarden voor een volgende online proef.

### Gebruik in vier stappen

1. Upload één of meer PDF’s via slepen of Bestanden kiezen. Een verkeerd bestand kan afzonderlijk worden verwijderd.

2. Controleer het gevonden MRN, bestemmingsland, documenttype en trucknummer. MRN en land zijn aanpasbaar. Trucknummers staan numeriek op volgorde; klik op de kolomkop om de volgorde om te draaien.

3. Koppel via het trucknummer de rit aan het later aangeleverde bookingnummer en het kenteken van de eigen GAM Bakker-wagen. Vul deze gegevens per document in. De applicatie toont of de regel compleet is.

4. Download Portbase-import.xls zodra alle documenten compleet en zonder dubbele MRN’s zijn. Importeer dit bestand zelf in Portbase.

### Gegevens en regels

| Gegeven | Herkomst of invulling | Gebruik |
| --- | --- | --- |
| Documentnummer | MRN bij de barcode rechtsboven | XLS kolom DOCNR |
| Documenttype | Bestemming GB geeft EU; ander land TT2 | XLS kolom DOCTYPE |
| Truck nummer | PDF en aanlevering per mail op trucknummer | Ritreferentie en sortering |
| Kenteken | Eigen wagen, gekoppeld via het trucknummer | XLS kolom TRANSPORTEQUIPMENTID |
| Bookingnummer | Later aangeleverd en handmatig gekoppeld | XLS kolom BOOKINGREF |

Het trucknummer is de ritreferentie: de documenten worden ook per mail op trucknummer aangeleverd. Bij meerdere documenten voor dezelfde rit vult de medewerker hetzelfde bijbehorende bookingnummer en kenteken in. Het trucknummer is niet het kenteken van de eigen wagen.

### Afbakening en open punten

Geen accounts, importgeschiedenis of documentopslag. Scans worden nog niet herkend. Ontbrekende gegevens moeten worden aangevuld; onleesbare bestanden moeten worden verwijderd. Vernieuwen van de pagina wist de invoer.

Nog te bevestigen met een praktijkproef: de bedrijfsregel GB → EU en overige landen → TT2, en acceptatie van het XLS-bestand door Excel en Portbase. Het bookingnummer en kenteken blijven per rit aan te vullen gegevens.

## Technisch ontwerp

De huidige oplossing bestaat uit een HTML/CSS/JavaScript-webpagina en een Python-server op dezelfde computer. De server leest PDF’s uit en vult een kopie van NEDTemplate.xls. Er is geen database of cloudverbinding.

### Verwerking

Browser → Python API → PDF uitlezen → controletabel → XLS genereren → download

| Onderdeel | Techniek | Verantwoordelijkheid |
| --- | --- | --- |
| Webpagina | HTML, CSS en JavaScript | Uploaden, corrigeren, sorteren en export aanvragen |
| Server | Flask en Waitress | API, controles en tijdelijke download afhandelen |
| PDF uitlezen | pdfplumber | Tekst en veldposities herkennen |
| XLS export | xlrd, xlutils en xlwt | Template kopiëren en vier kolommen vullen |

### Herkenning en export

De eerste pagina levert het MRN en Country of destination. Vervolgpagina’s worden gecontroleerd op afwijkende MRN’s. Het MRN wordt uit de leesbare tekst bij de barcode gehaald; de barcode zelf wordt niet gedecodeerd.

Voor Truck nummer zoekt de server eerst in vertrekveld [19 05], daarna in grensvelden [19 04] en [19 08]. Een gevonden genummerde TRUCK-waarde krijgt voorrang op alleen TRUCK. De getoonde bron maakt controle mogelijk. De sortering gebruikt het getal na TRUCK; waarden zonder dit getal komen onderaan.

Het veld truck dient als ritreferentie voor de handmatige koppeling met booking en plate. De medewerker gebruikt hiervoor de aanlevering per mail. De huidige versie vult bookingnummer en kenteken per document in; automatisch overnemen naar andere regels met hetzelfde trucknummer en het uitlezen van e-mail zijn niet geïmplementeerd.

De export vult DOCNR, DOCTYPE, TRANSPORTEQUIPMENTID en BOOKINGREF vanaf Excel-rij 4. De tabelvolgorde wordt overgenomen. Beide tabbladen en de kolomnamen blijven behouden; overige gegevenskolommen blijven leeg. Het ingebedde logo van het XLS-template wordt niet meegenomen.

### Controles en grenzen

Maximaal 20 MB en 50 pagina’s per PDF, en 200 documenten per export. Het MRN moet de verwachte schrijfwijze van 18 tekens hebben; de landcode telt twee letters. Dit is geen douanevalidatie. Dubbele MRN’s en ontbrekende verplichte invoer blokkeren de export. De server bepaalt het documenttype opnieuw bij export.

### Gegevens en toegang

PDF’s worden op de lokale server in het geheugen verwerkt. De exportdownload is eenmalig en 60 seconden geldig. Verlopen exports worden bij een volgende aanvraag opgeruimd. Het gedownloade bestand wordt wel op de computer van de gebruiker opgeslagen.

De server luistert op 127.0.0.1:8766 en accepteert alleen lokale hosts. Herkomstcontrole, een aanvraagheader en browserbeveiligingsheaders zijn aanwezig. Voor online gebruik moeten de host- en serverinstellingen worden aangepast en HTTPS worden ingericht. Zonder accounts is een openbare versie voor iedere bezoeker bereikbaar.

## Lokaal starten

Gebruik Python 3.12. Op Windows kun je `Start-lokaal.cmd` openen. De eerste start installeert de afhankelijkheden en vereist internet. Houd het servervenster open.

Handmatig starten op Windows:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:8766/ in de browser. De huidige versie is ingericht voor lokaal gebruik.

Tests uitvoeren:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

De repository bevat alleen tests met fictieve invoer. Klant-PDF’s, klantreferenties en gegenereerde exports worden niet meegeleverd.

Het bewerkbare Word-document staat in [docs/Portbase-functioneel-en-technisch-ontwerp.docx](docs/Portbase-functioneel-en-technisch-ontwerp.docx).
