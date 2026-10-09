# Open data for the newborn-service prototype

Run `python3 scripts/import_open_data.py` from the repository root. Python 3 and network access are the only requirements. The importer gets current catalog metadata, checks the declared license against the two reviewed licenses, downloads selected resources and license legal-code pages, validates the files, and generates JSON.

## Imported sources

1. **Valsts adrešu reģistra atvērtie dati — Valsts zemes dienests.** Full current CSV resources for municipalities, cities, parishes, villages, streets, and building/land addresses. Used for address selection and municipality lookup. License: CC BY 4.0.
2. **Pašvaldības pakalpojumu apraksti — Rīgas dome.** Original CSV and JSON records for service discovery. Riga only; publisher warns of incomplete data. The imported snapshot has five records, including a preschool service marked suspended; it must not be presented as a current newborn-service catalog. License: CC0 1.0.
3. **Ģimenes valsts pabalsta saņēmēji — publisher recorded in manifest.** Latest appended XLSX resource, preserved unchanged for optional statistical context. These are counts of recipients, not benefit rules. License: CC0 1.0.
4. **VSAA administrēto pakalpojumu saņēmēju skaits — publisher recorded in manifest.** Latest appended XLSX resource, preserved unchanged for optional statistical context. These are recipient statistics, not applications or eligibility decisions. License: CC0 1.0.

5. **Vakances — Nodarbinātības valsts aģentūra.** Daily CSV of vacancies registered with NVA. Aggregated on 2026-10-09 to counts per municipality and category with up to three sample vacancies each (`public/data/nva-vacancies.json`); the full list stays on the NVA CV and vacancy portal. License: CC0 1.0.

The two VSAA/LM workbooks (sources 3 and 4) were additionally converted on 2026-10-09 to `public/data/vsaa-statistics.json` and `public/data/gimenes-valsts-pabalsts.json` (row arrays with named columns, values unchanged) so the dashboard can show municipality-level context. These three JSON files are manual conversions; the importer does not regenerate them yet.

## Where files live

- `data/manifest.json`: sources, resource URLs and IDs, retrieval time, licenses, SHA-256 checksums, transformations, coverage and unresolved addresses.
- `data/metadata/`: original catalog metadata snapshots.
- `data/licenses/`: saved English legal-code HTML from Creative Commons.
- `data/raw/`: original downloaded files. Excluded from Git and Docker images; reproducible with the importer.
- `public/data/municipalities.json`: municipality index with address counts and relative JSON paths.
- `public/data/addresses/<municipality-code>.json`: all resolved active building/land addresses for that municipality. Excluded from Git due to size; included in Docker builds after import.
- `public/data/addresses.json`: five representative addresses per municipality, kept in Git for a small demo.
- `public/data/riga-services.json`: converted service catalog.
- `public/data/sources.json`: source manifest for the website.
- `public/data-licenses.html`: visible attribution and source links.

JSON derivations remove deleted records and unused fields. Municipality resolution follows parent codes, not name matching. Buildings whose parent municipality cannot be resolved are excluded and reported explicitly. The importer does not include apartment/unit addresses; building selection is not sufficient for a real declaration.

This is a snapshot, not a live API. Check the manifest's retrieval time and resource period. Generated bulk address files and raw CSV files must be re-imported on another checkout before using nationwide search.

## License handling

CC BY 4.0 requires appropriate attribution, a license link and indication of changes. Keep the attribution page accessible wherever this data is shown, and preserve the saved notices when sharing snapshots. The attribution names the dataset and publisher, links the source and license, and explains the CSV-to-JSON transformations. It does not imply publisher endorsement.

CC0 datasets can be reused without an attribution condition under that dedication. We retain source references and the CC0 legal code for provenance.

The project code's licensing is separate. These data licenses do not license Latvija.gov.lv logos, visual assets, personal records, authentication or government integrations. No legal outcome is guaranteed by saving license files.

## Still needed before benefit recommendations

This import does not supply current benefit amounts, deadlines, eligibility rules or every municipality's newborn grant rules. Those require separately verified official VSAA and municipality sources. Do not treat recipient counts or service names as those rules. Do not invent amounts or claim a family is eligible based on address alone.

## Demo profile addresses

The people seeder randomly assigns addresses from the tracked `public/data/addresses.json` snapshot using a deterministic seed. These are real public addresses, but the people and their association with those addresses are fictional. Names remain generated from the existing name lists; imported datasets contain no personal name lists. Email addresses use example.com and phone numbers are generated. Profile address attribution links to the existing source and license page. Existing placeholder addresses are upgraded without resetting users, identifiers or sessions. Docker mounts the tracked address snapshot read-only into the API container.
