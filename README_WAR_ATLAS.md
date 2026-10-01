# War Atlas

Mobile-first interactive map of wars from 2500 BCE to the present.

## Architecture
- Wikipedia `List of wars` pages define the corpus.
- Wikidata enriches entries with coordinates (P625), dates (P580/P582/P585), and number of deaths (P1120) where available.
- `scripts/build_data.py` produces a compact static GeoJSON.
- GitHub Actions refreshes the dataset every Monday and can also be run manually.
- The browser only renders the prepared dataset; it does not crawl Wikimedia.

## Historical-data caveat
This is a visualization of conflicts represented in the selected Wikipedia lists, not a claim to enumerate every conflict that occurred in human history. Missing casualty data remains unknown rather than zero.

## Mobile
The UI is designed around touch, portrait screens, clustering, and a year slider. It can be installed as a PWA once served over HTTPS.
