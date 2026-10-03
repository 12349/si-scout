# Third-Party Notices and Licenses

This project incorporates and depends upon open-source software and public research datasets.
Below are the attributions, licenses, and compatibility notices for each component.

---

## 1. Python Software Dependencies

| Component | Code License | Authors / Maintainers |
| :--- | :--- | :--- |
| **Flask** | BSD-3-Clause | Pallets Projects |
| **Pandas** | BSD-3-Clause | NumFOCUS / PyData Development Team |
| **PyYAML** | MIT | Kirill Simonov |
| **Requests** | Apache-2.0 | Kenneth Reitz and Requests Contributors |
| **Pytest** | MIT | Holger Krekel and pytest-dev |
| **Wordfreq (Code)** | Apache-2.0 | Robyn Speer & Luminoso Technologies, Inc. |

---

## 2. Wordfreq Data Licenses and Attribution Notice

Per installed package metadata (`wordfreq 3.1.1`, License: `Apache-2.0`) and documentation:
- **Code License**: Apache License, Version 2.0 (confirmed via pip metadata).
- **Data Licenses**: The word frequency lists compiled by `wordfreq` are derived from multiple sources distributed under Creative Commons Attribution-ShareAlike 4.0 International (**CC BY-SA 4.0**), with specific data source attributions:
  - **Google Books Ngram Corpus**: Used in accordance with Google Books terms of use (attribution required).
  - **SUBTLEX**: Subtitle word frequency data (Brysbaert, New, Keuleers et al.) used under scientific research and CC terms.
  - **Wikipedia & Wiktionary**: Used under CC BY-SA 4.0.
  - **OpenSubtitles & Leeds Internet Corpora**: Used under respective CC and research attribution terms.
- **Data Files Not Bundled**: **No wordfreq data files or frequency tables are bundled in the SI Scout repository.** SI Scout interacts strictly with the `wordfreq` Python package installed via `pip`, and downloads/manages no proprietary wordfreq data binaries in version control.

---

## 3. External Research Datasets & Registry Services

### Tranco Top Sites List
- **Provider**: Tranco Research Team (Victor Le Pochat, Tom Van Goethem, Samaneh Tajalizadehkhoob, Maciej Korczyński, Wouter Joosen).
- **Website**: https://tranco-list.eu/
- **License**: **Verify at tranco-list.eu** (licensing terms and citation conditions should be verified directly at the official project site prior to distribution or commercial use).
- **Attribution**: Victor Le Pochat, Tom Van Goethem, Samaneh Tajalizadehkhoob, Maciej Korczyński, Wouter Joosen. *An Evaluated Research Dataset of Top Sites on the Web*. In Proceedings of the 2019 Network and Distributed System Security Symposium (NDSS 2019).
- **Data Files Not Bundled**: Raw Tranco CSV/JSON files are excluded via `.gitignore`. The repository includes only a lightweight bootstrapping script (`scripts/bootstrap_data.py`).

### Register.si Public Registry Service
- **Provider**: Academic and Research Network of Slovenia (ARNES) / Register.si.
- **Website**: https://www.register.si/
- **Terms & Etiquette**: RDAP endpoints and registry status information (`https://www.register.si/statusi-domen/`) are queried using rate-limited, read-only HTTP GET requests. The scanner is designed to be polite (enforcing &ge;1.0s spacing); users must independently check the registry's terms and policies before querying live endpoints.
- **Notice**: SI Scout is an independent project and is not sponsored, affiliated with, or approved by ARNES or Register.si.

---

## 4. Software License Texts

### BSD-3-Clause License (Flask, Pandas)
Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

### Apache License, Version 2.0 (Requests, Wordfreq code)
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.


## 5. UI Frontend & Visualization Architecture
The SI Scout dashboard frontend is constructed using 100% vanilla ECMAScript modules, CSS Custom Properties, and native Scalable Vector Graphics (SVG).
- Zero external runtime JavaScript libraries (e.g. Chart.js, React, jQuery) are vendored or bundled.
- Zero external Content Delivery Networks (CDNs), web fonts, or analytics endpoints are requested at runtime.
