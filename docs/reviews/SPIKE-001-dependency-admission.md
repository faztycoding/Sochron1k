# SPIKE-001 dependency admission — proposed

Reviewer: Codex, dependency-admission role. Date: 2026-10-21 Asia/Bangkok.
Repository snapshot: `0916776c58b78c34677ffb4ba73a7a0f789ca8ae`, branch `spike/SPIKE-001-mt5-time`.
Target: CPython 3.12, Windows x64, temporary `uv run --with` environment, no extras.
Procedure: `.agents/skills/dependency-admission/SKILL.md`; contract: `docs/contracts/SPIKE-001-mt5-connectivity-time.md` v1.

## สรุปสำหรับเจ้าของ

**pin `MetaTrader5==5.0.6231` ใน contract ถูกต้องและยังเป็นรุ่นล่าสุดที่ PyPI รายงาน ณ เวลาตรวจ** มี wheel ตรง Python 3.12 / Windows x64 จึงไม่ต้องเปลี่ยน pin นี้ แต่ `numpy>=1.7` ที่ package ประกาศเปิดช่วงกว้าง ควร pin `numpy==2.5.4` เพิ่มแล้วพิสูจน์ native ABI และการเชื่อม Demo ใน SPIKE-001 ก่อนรับเป็น stack ของโปรเจกต์ หลักฐาน: [latest JSON](https://pypi.org/pypi/MetaTrader5/json), [version JSON](https://pypi.org/pypi/MetaTrader5/5.0.6231/json), [NumPy JSON](https://pypi.org/pypi/numpy/2.5.4/json).

| Package | ข้อเสนอ | Exact pin | เหตุผลหลัก |
|---|---|---|---|
| MetaTrader5 | **SPIKE FIRST** | `MetaTrader5==5.0.6231` | official vendor, wheel ตรงเป้าหมาย; native binary/NumPy ABI และ terminal จริงยังไม่ทดสอบ |
| tzdata | **ADMIT** เฉพาะ spike | `tzdata==2026.5` | ข้อมูล IANA ให้ stdlib `zoneinfo` บน Windows; ไม่มี runtime dependency เพิ่ม |
| pytest | **ADMIT** เฉพาะ spike tests | `pytest==9.1.1` | ตรงเครื่องมือใน contract; universal wheel; pin transitives อีก 5 ตัวด้านล่าง |

ทั้งหมดเป็น **ข้อเสนอ ไม่ใช่ owner approval**. SPIKE FIRST หมายถึงเสนอให้เจ้าของอนุมัติทดลองคู่ MetaTrader5/NumPy ตาม contract นี้เพื่อเก็บหลักฐานก่อนตัดสินรับใช้ต่อ ไม่ได้หมายความว่าต้องสร้าง spike อีกงานหนึ่ง รายงานนี้ไม่ได้อนุมัติ D-001 หรือการเชื่อม terminal และไม่ได้ติดตั้ง/import/รัน package ใด

ชุดรวมมี **3 direct + 6 transitive = 9 packages**. OSV exact-version queries ของทั้ง 9 ตัวไม่พบ advisory ที่ match ณ เวลาตรวจ; ผลนี้ไม่พิสูจน์ว่าไม่มีช่องโหว่หรือ malicious code. ได้ตรวจประวัติ advisory ของ pytest/Pygments และพบว่า pin ที่เลือกพ้นช่วงที่ได้รับผลกระทบ รายละเอียดและข้อจำกัดอยู่ด้านล่าง

## Scope and evidence method

- Initial successful registry/advisory queries were captured on **2026-10-20 19:39–19:41 UTC** (2026-10-21 02:39–02:41 +07); all nine report wheel names/hashes were cross-checked again against exact-release JSON at **19:44:42 UTC**. Version-specific URLs preserve the selected release identity; latest endpoints are time-dependent.
- Used existing Node.js `v26.12.0` built-in `fetch` for PyPI JSON GET and OSV read-only POST queries, plus registry/vendor/advisory pages. No dependency artifact was downloaded, installed, imported, or executed. No `uv` resolver was run.
- Evaluated `Requires-Python`, `Requires-Dist`, platform markers, wheel names, yanked flags, release dates, registry hashes, declared licenses and publisher evidence. This is metadata screening, not a wheel-content, signature, source-code or binary audit.
- Dependency closure below assumes a clean environment, public PyPI, normal latest-compatible stable selection, no extras, no additional constraints or index overrides. Actual `uv` resolution can differ with local configuration; explicitly pin the full applicable set for the later approved run.
- Repository search found no tracked `src/`, `spikes/`, `pyproject.toml`, `uv.lock` or requirements files providing an existing implementation/dependency to reuse. The contract remains draft. The owner's instruction authorizes this report only; no other file, staging, commit or push is part of this run.

## MetaTrader5 — SPIKE FIRST, candidate pin 5.0.6231

**Identity and maintenance.** Registry canonical name is `metatrader5`; `MetaTrader5` is the vendor's documented distribution/import spelling, not a different package. PyPI identifies MetaQuotes Ltd. as author/maintainer and `metaquotes` as its PyPI maintainer. The vendor links to this Python integration, and the registry links back to MetaTrader/MQL5 documentation. Latest release is 5.0.6231, uploaded 2026-09-27; preceding releases include 5.0.6180 on September 5, 5.0.6162 on September 3 and 5.0.6147 on August 27. [Registry JSON](https://pypi.org/pypi/MetaTrader5/json), [publisher/files](https://pypi.org/project/MetaTrader5/), [vendor documentation](https://www.mql5.com/en/docs/python_metatrader5).

**License.** PyPI declares MIT, compatible at the metadata-screening level with the intended private spike. Preserve applicable license/copyright notices for redistribution. The wheel's license text was not extracted; this statement does not grant rights to redistribute the MT5 terminal, broker software or market data. [Pinned metadata](https://pypi.org/pypi/MetaTrader5/5.0.6231/json).

**Compatibility and size.** `Requires-Python: <4,>=3.6`; the actual wheel list, rather than that broad range, establishes availability. All nine release files are non-yanked Windows x64 wheels; no sdist exists for this release. Target wheel: `metatrader5-5.0.6231-cp312-cp312-win_amd64.whl`, **47,968 bytes**, uploaded `2026-09-27T12:22:35.219917Z`. Exact published tags:

```text
cp36-cp36m-win_amd64
cp37-cp37m-win_amd64
cp38-cp38-win_amd64
cp39-cp39-win_amd64
cp310-cp310-win_amd64
cp311-cp311-win_amd64
cp312-cp312-win_amd64
cp313-cp313-win_amd64
cp314-cp314-win_amd64
```

There is no cp315, win32, win_arm64, Linux or macOS wheel in this release. The repository's abbreviated cp310–cp314 description is not the complete release list. [Exact release JSON](https://pypi.org/pypi/MetaTrader5/5.0.6231/json).

**Security and runtime surface.** The exact-version OSV query and a normalized-name package-wide query returned no records; PyPI reports `vulnerabilities: []`. PyPI reports no Trusted Publishing/provenance for these wheels. A platform-specific native wheel will load executable code with the Python process's permissions. Vendor documentation describes local terminal IPC; initialization can start the terminal and use its saved account/session, with the terminal communicating with the broker. The API also exposes account/order-changing operations even though SPIKE-001 forbids them. A temporary environment is dependency isolation, not a broker/network sandbox. [PyPI file details](https://pypi.org/project/MetaTrader5/), [initialize behavior](https://www.mql5.com/en/docs/python_metatrader5/mt5initialize_py), [API surface](https://www.mql5.com/en/docs/python_metatrader5).

**Fit and decision.** No stdlib equivalent provides the official MT5 IPC/data interface; replacing it would introduce substantial implementation and validation work. It declares exactly `numpy>=1.7`, with no upper bound. Select **`numpy==2.5.4` as the explicit candidate**: current, non-yanked, Python 3.12-compatible and no matching OSV advisory. Neither metadata nor a matching wheel tag proves the MetaTrader5/NumPy ABI pair works. NumPy documents downstream C-ABI incompatibilities across major versions. Therefore **SPIKE FIRST** for the pair: after owner authorization, verify import and record both versions, then use only the authorized Demo read path and record the terminal build. If import fails, retain the actual error and re-review a specific alternative; do not silently downgrade or loosen pins. [NumPy metadata](https://pypi.org/pypi/numpy/2.5.4/json), [NumPy ABI guidance](https://numpy.org/doc/stable/user/troubleshooting-importerror.html).

## tzdata — ADMIT for this spike, pin 2026.5

**Identity and maintenance.** Exact distribution `tzdata`, author Python Software Foundation, PyPI owner `Python`; maintainers `belopolsky`, `pganssle`, `stanfromireland`. Latest 2026.5 wheel was uploaded `2026-10-03T09:23:12.535688Z`; preceding 2026.4/2026.3 releases were September 12/July 10. PyPI shows Trusted Publishing from `python/tzdata`, source commit `9493aaba724e991b239647cb7bfe977d019ce1b9`; this review did not independently verify an attestation. [Registry/publisher](https://pypi.org/project/tzdata/), [exact JSON](https://pypi.org/pypi/tzdata/2026.5/json), [vendor docs](https://tzdata.python.org/).

**Compatibility/dependencies.** `Requires-Python: >=2`; `Requires-Dist: null`, hence zero declared runtime dependencies. One universal wheel, `tzdata-2026.5-py2.py3-none-any.whl`, **347,996 bytes**, non-yanked. Its exact compressed tag `py2.py3-none-any` expands to `py2-none-any` and `py3-none-any`; the latter matches CPython 3.12 Windows x64. An sdist is also published but unnecessary here. [Exact release metadata](https://pypi.org/pypi/tzdata/2026.5/json).

**License/security/runtime.** Package license Apache-2.0; upstream IANA timezone data is public domain except specified portions. Preserve applicable license/notices on redistribution; do not infer that every bundled source file is public domain. Vendor describes compiled TZif data resources, not CPU-native extension binaries. Expected runtime is local resource reads by `zoneinfo`, with no vendor-documented broker/network requirement. OSV exact query returned `{}` and PyPI vulnerabilities is empty. Archive content/install behavior was not inspected. [Pinned vendor license](https://github.com/python/tzdata/blob/9493aaba724e991b239647cb7bfe977d019ce1b9/LICENSE), [IANA license](https://data.iana.org/time-zones/tzdb/LICENSE), [vendor documentation](https://tzdata.python.org/).

**Fit.** Python 3.12 already provides `zoneinfo`, but Windows normally lacks an IANA timezone database. This package supplies the data, so another timezone engine is unnecessary. It supports named zones/DST checks; it does not establish whether raw MT5 timestamps mean UTC or broker-server time. AC-04 still determines that rule. Pinning tzdata makes the database version reproducible; record the actual data source used because `zoneinfo` searches system paths before its package fallback. [Python 3.12 zoneinfo documentation](https://docs.python.org/3.12/library/zoneinfo.html).

## pytest — ADMIT for spike tests, pin 9.1.1

**Identity and maintenance.** Official pytest-dev package `pytest`; PyPI maintainers include `anatoly`, `flub`, `hpk`, `nicoddemus`, `pfctdayelise`, `ronny`, `The_Compiler`. Latest release 9.1.1 was uploaded 2026-06-19, following 9.1.0 on June 13 and 9.0.3 on April 7. License MIT. PyPI reports Trusted Publishing for the current release; no independent attestation validation was performed. [Version JSON](https://pypi.org/pypi/pytest/9.1.1/json), [publisher](https://pypi.org/project/pytest/9.1.1/), [official docs](https://docs.pytest.org/en/stable/how-to/plugins.html).

**Compatibility.** `Requires-Python: >=3.10`; sole wheel `pytest-9.1.1-py3-none-any.whl`, **386,536 bytes**, non-yanked; exact tag `py3-none-any`. An sdist is available but is unnecessary for this target. Five mandatory runtime transitives apply on Windows/Python 3.12; all have compatible universal wheels. Pin them as below. [Exact metadata](https://pypi.org/pypi/pytest/9.1.1/json).

**Security.** Exact-version OSV query returned `{}`; PyPI vulnerabilities is empty. A package-wide lookup found **CVE-2025-71176 / GHSA-6w46-j5rx-g56g**, concerning UNIX temporary-directory handling through 9.0.2, fixed in **9.0.3**. Selected 9.1.1 is outside that range. This is not an unresolved vulnerability in the selected pin. [Advisory](https://osv.dev/vulnerability/GHSA-6w46-j5rx-g56g).

**Execution surface and fit.** pytest executes tests, `conftest.py` and plugins; writes cache/temp files and possibly bytecode. Plugin code has the process's filesystem/network permissions. For the later approved run, use the isolated spike environment and disable unsolicited plugin autoload (`--disable-plugin-autoload`); this does not prevent explicitly selected/local test code from executing. No setting was changed here. The contract explicitly uses pytest for negative-case tests. Stdlib `unittest` is an alternative but would change the prescribed test workflow without reducing the need to review test code. Keep pytest out of the probe environment unless tests require it. [Plugin behavior](https://docs.pytest.org/en/stable/how-to/plugins.html), [cache behavior](https://docs.pytest.org/en/stable/how-to/cache.html).

## Transitive admission, lighter-depth review

All pins below are the latest stable versions returned by their PyPI project JSON at review time, have non-yanked target-compatible wheels, and returned no exact-version OSV matches. “ADMIT” remains a proposal restricted to this spike. Python requirements and identities are registry evidence; runtime behavior is documented purpose/inference, not an executed test.

| Package/pin and metadata source | Proposal | Publisher; license | Release UTC date; Python | Target wheel tag; bytes | Fit and remaining risk |
|---|---|---|---|---|---|
| [numpy==2.5.4](https://pypi.org/pypi/numpy/2.5.4/json) | **SPIKE FIRST** with MetaTrader5 | NumPy Developers; PyPI `charlesr.harris`, `mattip`; `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0` | 2026-10-10; `>=3.12` | `cp312-cp312-win_amd64`; 12,573,091 | Required arrays/native ABI; no declared Python runtime deps; native/bundled libraries remain uninspected |
| [colorama==0.4.6](https://pypi.org/pypi/colorama/0.4.6/json) | **ADMIT** | Jonathan Hartley/Arnon Yaari; PyPI `tartley`, `wiggin15`; BSD-3-Clause | 2022-10-25; `>=2.7`, excludes 3.0–3.6 | `py2.py3-none-any`; 25,335 | Required by pytest on Windows; console/stdout wrapping; old release cadence, metadata admits 3.12 but description's tested-version list ends at 3.10 |
| [iniconfig==2.3.1](https://pypi.org/pypi/iniconfig/2.3.1/json) | **ADMIT** | pytest-dev; PyPI `hpk`, `ronny`; MIT | 2026-10-06; `>=3.10` | `py3-none-any`; 7,552 | INI configuration parsing; recent patch after 2.3.0 in October 2025 |
| [packaging==26.3](https://pypi.org/pypi/packaging/26.3/json) | **ADMIT** | PyPA; PyPI `brettcannon`, `dstufft`, `pf_moore`, `pradyunsg`; Apache-2.0 OR BSD-2-Clause | 2026-08-04; `>=3.9` | `py3-none-any`; 129,956 | Version/requirement parsing; follows 26.1/26.2 in April 2026 |
| [pluggy==1.7.0](https://pypi.org/pypi/pluggy/1.7.0/json) | **ADMIT** | pytest-dev/Holger Krekel; PyPI `flub`, `goodboy`, `hpk`, `nicoddemus`, `ronny`, `The_Compiler`; MIT | 2026-10-15; `>=3.10` | `py3-none-any`; 27,082 | Runs registered hooks; recent release after 1.6.0 in May 2025; test integration still unverified |
| [Pygments==2.21.0](https://pypi.org/pypi/Pygments/2.21.0/json) | **ADMIT** | Pygments team; PyPI `Anteru`, `gbrandl`, `mitsuhiko`; BSD-2-Clause | 2026-08-17; `>=3.9` | `py3-none-any`; 1,250,147 | Syntax highlighting/parsing; no default runtime deps; fixed-version security evidence below |

Publisher cross-checks: [NumPy](https://pypi.org/project/numpy/2.5.4/), [colorama](https://pypi.org/project/colorama/0.4.6/), [iniconfig](https://pypi.org/project/iniconfig/), [packaging](https://pypi.org/project/packaging/), [pluggy](https://pypi.org/project/pluggy/), [Pygments](https://pypi.org/project/Pygments/). These licenses are permissive for the proposed private use; redistribution must retain the applicable notices/conditions. For NumPy, its composite expression and bundled-library notices matter, not just the main project's BSD license. [NumPy license](https://numpy.org/doc/stable/license.html).

NumPy 2.5.4 follows 2.5.3 (September 6) and 2.5.2 (August 9). PyPI reports provenance for its release artifacts. Vendor documentation notes that PyPI wheels contain OpenBLAS code; bundled native libraries are **not additional pip distributions**, and their exact versions/SBOM were not inspected. Package-level OSV results do not independently audit those libraries. NumPy has file serialization/loading functionality; no untrusted serialized arrays are needed for this spike. [Registry](https://pypi.org/pypi/numpy/json), [native-runtime documentation](https://numpy.org/doc/stable/user/troubleshooting-importerror.html).

Pygments 2.21.0 follows 2.20.0 (March 29). Package-wide OSV lookup found **CVE-2026-4539 / GHSA-5239-wwwm-4pmq**, a regex denial of service fixed in **2.20.0**; selected 2.21.0 is outside that range. Its exact-version OSV query covers other indexed records as well. PyPI reports no Trusted Publishing for 2.21.0. [Advisory](https://osv.dev/vulnerability/GHSA-5239-wwwm-4pmq), [release metadata](https://pypi.org/project/Pygments/).

### Exact closure for the target

```text
MetaTrader5==5.0.6231
  numpy>=1.7                                  => numpy==2.5.4
tzdata==2026.5                                 => no runtime deps
pytest==9.1.1
  colorama>=0.4; sys_platform == "win32"        => colorama==0.4.6
  iniconfig>=1.0.1                            => iniconfig==2.3.1
  packaging>=22                              => packaging==26.3
  pluggy<2,>=1.5                              => pluggy==1.7.0
  pygments>=2.7.2                             => Pygments==2.21.0
```

`sys_platform == "win32"` is true on Windows x64 too. `exceptiongroup>=1` and `tomli>=1` both have `python_version < "3.11"`, so are excluded. pytest's `dev` extra is not selected: no argcomplete, attrs, hypothesis, mock, requests, setuptools or xmlschema. Pygments declares `colorama>=0.4.6; extra == "windows-terminal"`; that extra is not selected (colorama is already required by pytest). NumPy, tzdata, colorama, iniconfig, packaging and pluggy declare no further mandatory runtime dependencies in these versions.

Thus the contract's probe environment needs **3 distributions** (MetaTrader5, NumPy, tzdata); its pytest-only command needs **6** (pytest and five transitives). Tests importing the probe may need their **9-package union**; that is a later test-design/runtime question. pandas, matplotlib and pytz in vendor examples are not declared dependencies and are not admitted here. No build dependencies are needed if the published wheels are used; a source-build fallback would be outside this review. Interpreter/tool/cache/terminal software is not counted as a PyPI transitive.

### Exact wheel identities and registry SHA-256

These are **registry-reported hashes**, not hashes independently computed from downloaded artifacts. All three direct packages' complete wheel-tag sets are documented above. For NumPy the table lists the exact target wheel, not its unrelated Linux/macOS/other-interpreter variants. The other five transitives each publish the single universal wheel shown; colorama's compressed tag expands to `py2-none-any` and `py3-none-any`.

| Wheel filename | Registry SHA-256 |
|---|---|
| `metatrader5-5.0.6231-cp312-cp312-win_amd64.whl` | `b94b1f8f52087ae36dfac5f352a96f5d04fe308704d9515f82cf5d1470bc31d4` |
| `tzdata-2026.5-py2.py3-none-any.whl` | `b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac` |
| `pytest-9.1.1-py3-none-any.whl` | `37a86b45efb9a47a61a36449063e8e18d0cab3161329fc099eb21783169c4f0c` |
| `numpy-2.5.4-cp312-cp312-win_amd64.whl` | `a7b1b6353e36a7e50de2973a38d705c88ee93adcf120673cee7f45a4a3fa223a` |
| `colorama-0.4.6-py2.py3-none-any.whl` | `4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6` |
| `iniconfig-2.3.1-py3-none-any.whl` | `9121e2c1fdb355232495be3194c8dfe87ccc2d5dee45947b78e68f499790d7a7` |
| `packaging-26.3-py3-none-any.whl` | `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c` |
| `pluggy-1.7.0-py3-none-any.whl` | `7dd7b0d8832ba3cb632c306926ded123429211b83641b35dc5c41ad2d34f9bec` |
| `pygments-2.21.0-py3-none-any.whl` | `2363c69b61c4a97c838da3b130dcd6468f4848992b21a82f2a63ec34377137d9` |

Total compressed size of these nine wheels: **14,795,663 bytes**; this excludes Python, uv, MT5, extracted files and caches. Installing a wheel avoids executing its sdist build backend, but wheel tags/JSON cannot establish the absence of startup hooks, unexpected files or malicious runtime code. Install scripts, archive entry points and native imports remain uninspected; no claim of “no install scripts” is made.

## Advisory query record

Read-only lookup endpoint: [OSV query API](https://api.osv.dev/v1/query). Each request used `Content-Type: application/json` and the following shape, with the package/version in the table. POST is the query API's read operation, not a publication or modification.

```json
{"package":{"name":"numpy","ecosystem":"PyPI"},"version":"2.5.4"}
```

| Query package | Version | Observed UTC, 2026-10-20 | HTTP / body | Meaning |
|---|---|---|---|---|
| MetaTrader5 | 5.0.6231 | 19:39:35.944 | 200 / `{}` | No indexed matching advisory |
| numpy | 2.5.4 | 19:39:36.282 | 200 / `{}` | No indexed matching advisory |
| tzdata | 2026.5 | 19:40:02.828 | 200 / `{}` | No indexed matching advisory |
| pytest | 9.1.1 | 19:39:30.360–19:39:30.477 | 200 / `{}` | No indexed matching advisory |
| colorama | 0.4.6 | same six-package batch | 200 / `{}` | No indexed matching advisory |
| iniconfig | 2.3.1 | same six-package batch | 200 / `{}` | No indexed matching advisory |
| packaging | 26.3 | same six-package batch | 200 / `{}` | No indexed matching advisory |
| pluggy | 1.7.0 | same six-package batch | 200 / `{}` | No indexed matching advisory |
| pygments | 2.21.0 | same six-package batch | 200 / `{}` | No indexed matching advisory |

PyPI version metadata also returned empty vulnerability lists. Package-wide queries (omitting `version`) checked historical records for MetaTrader5, NumPy, pytest and its five transitives. Normalized `metatrader5` returned zero records at 19:40:05.171 UTC; NumPy returned 16 records, including duplicate ecosystem/advisory representations, with no pagination token. Those records must not be called 16 currently applicable vulnerabilities: the exact 2.5.4 query returned none. pytest/Pygments relevant fixed-version records are cited above; colorama/iniconfig/packaging/pluggy package-wide queries returned none. No exhaustive open-issue or undisclosed-vulnerability search was possible within registry/advisory/vendor scope.

## Draft DECISIONS entries — proposed only

These entries are proposed text inside this report. `D-0xx` is an unassigned placeholder for the owner/implementer to replace with free IDs when authorized. `DECISIONS.md` was not edited. Transitive pins are included in their parent's decision so approval cannot silently omit them.

### D-0xx Add MetaTrader5 5.0.6231 and NumPy 2.5.4 — 2026-10-21 — proposed

เสนอ **SPIKE FIRST** สำหรับ `MetaTrader5==5.0.6231` พร้อม `numpy==2.5.4` เฉพาะ temporary `uv run --with` environment ของ SPIKE-001 บน Python 3.12 / Windows x64 โดยไม่เพิ่ม project dependency หรือ lockfile

เหตุผล: MetaQuotes official package และ pin ปัจจุบันมี `cp312-cp312-win_amd64`; NumPy pin นี้ตรง requirement และมี wheel เป้าหมาย; OSV ไม่พบ matching advisory ทั้งคู่ ณ เวลาตรวจ แต่ binary ABI และ terminal compatibility ยัง UNKNOWN จึงต้องพิสูจน์ import/version และการอ่าน Demo ตาม contract ก่อนใช้ผลไปตัดสิน D-001 ไม่ fallback เป็นรุ่นอื่นโดยอัตโนมัติ เจ้าของต้องอนุมัติทั้ง dependency proposal, contract และขอบเขต terminal ก่อน execution

หลักฐาน: รายงานนี้, [MetaTrader5 metadata](https://pypi.org/pypi/MetaTrader5/5.0.6231/json), [NumPy metadata](https://pypi.org/pypi/numpy/2.5.4/json). ข้อเสนอนี้ไม่รับ D-001 และไม่อนุญาตการเปลี่ยนสถานะบัญชี

### D-0xx Add tzdata 2026.5 — 2026-10-21 — proposed

เสนอ **ADMIT `tzdata==2026.5`** เฉพาะ environment ชั่วคราวของ SPIKE-001 เพื่อให้ stdlib `zoneinfo` ใช้ IANA timezone data บน Windows มี universal wheel และไม่มี runtime transitives; metadata ระบุ Apache-2.0 และ OSV ไม่พบ matching advisory การใช้ timezone data ไม่ตัดสินความหมายของ raw MT5 timestamp แทน AC-04

เจ้าของเป็นผู้อนุมัติ; ไม่เพิ่ม dependency/lockfile ให้โปรเจกต์ และไม่อนุมานว่า D-001 accepted หลักฐาน: รายงานนี้และ [tzdata metadata](https://pypi.org/pypi/tzdata/2026.5/json)

### D-0xx Add pytest 9.1.1 and its five transitives — 2026-10-21 — proposed

เสนอ **ADMIT `pytest==9.1.1`** สำหรับ tests ของ SPIKE-001 เท่านั้น พร้อม **ADMIT** pins `colorama==0.4.6`, `iniconfig==2.3.1`, `packaging==26.3`, `pluggy==1.7.0`, `Pygments==2.21.0` โดยไม่เลือก extras และไม่เพิ่ม project dependency/lockfile

เหตุผล: ตรง contract, wheel/Python metadata รองรับเป้าหมาย, licenses รองรับ private test use ตาม metadata และ OSV ไม่พบ matching advisory; pytest 9.1.1 พ้น fixed version 9.0.3 ของ CVE-2025-71176, Pygments 2.21.0 พ้น fixed version 2.20.0 ของ CVE-2026-4539 บันทึกความเสี่ยง colorama release เก่าและ pluggy release ใหม่ไว้แล้ว

เมื่อเจ้าของอนุมัติ execution ให้เลือก wheels และ environment แยก ตรวจ version จริง และปิด unsolicited plugin autoload การ review นี้ยังไม่พิสูจน์ runtime และไม่รับ D-001 หลักฐาน: รายงานนี้, [pytest metadata](https://pypi.org/pypi/pytest/9.1.1/json) และ exact-version links ของ transitives ในตาราง

## Checks, limitations and handoff

All checks refer to HEAD `0916776c58b78c34677ffb4ba73a7a0f789ca8ae`; this report is an uncommitted working-tree addition. Times are 2026-10-21 Asia/Bangkok unless explicitly UTC.

| Command/procedure | Result | Commit | Time/evidence |
|---|---|---|---|
| `git status --short`; `git branch --show-current`; `git rev-parse HEAD` | PASS: initially clean, expected task branch | `0916776` | Session start, before report creation |
| `git ls-files 'src/*' 'spikes/*' 'pyproject.toml' 'uv.lock' '*requirements*'` | PASS: no existing tracked code/dependency files returned | `0916776` | 02:40:04 |
| Existing Node `fetch`: GET PyPI latest and exact-release JSON; inspect metadata/markers/files | PASS: 9 selected versions and dependency closure recorded | `0916776` | 02:39–02:41; exact JSON links above |
| Existing Node `fetch`: POST OSV exact-version query for all 9 pins | PASS: HTTP 200 `{}` for each; limited to known indexed matches | `0916776` | Exact UTC query times above |
| Read registry publisher/file pages, vendor docs and cited advisory records | PASS for cited evidence | `0916776` | This session; no package execution |
| `bash scripts/controls/red-flags.sh main` | PASS command exit 0; **6 hit groups**, not a clean scan | `0916776` | Baseline 02:40–02:41 and final 02:44:42; local `main`/merge-base `951ee98`; final run lists this report as untracked/not scanned |
| `node scripts/controls/check-locked-paths.mjs main` | **FAIL**, exit 1: 42 inherited control changes require owner label | `0916776` | Same baseline check; 70 changed paths / 58 commits since `951ee98` |
| `git diff --no-index --check -- /dev/null docs/reviews/SPIKE-001-dependency-admission.md` | UNKNOWN as a standalone pass signal: exit 1, empty output; new-file comparison, no whitespace diagnostics | `0916776` + report | 02:43:59; explicit content checks below provide the whitespace result |
| Node stdin document checks: UTF-8, trailing whitespace, final newline, Markdown fences, hash/draft counts | PASS, exit 0: no replacement characters/trailing whitespace; 9 hashes and 3 decision drafts | `0916776` + report | 02:43:41 |
| Node stdin supplemental report-text pattern screen | PASS, exit 0: 0 secret/control-bypass/test-disable pattern hits | `0916776` + report | 02:43:59; supplemental screen, not the repository scanner |
| Read-only document consistency QA | PASS: closure, markers, pins, hashes' format, size sum, proposal/AC boundaries | `0916776` + report | This session; metadata not independently re-fetched by this QA |
| Node stdin: parse the report's 9 wheel/hash rows; GET each exact PyPI release JSON; compare filename, SHA-256, non-yanked flag and size sum | PASS, exit 0: 9/9 exact matches; 14,795,663 bytes | `0916776` + report | 02:44:42.153; registry metadata only, no artifacts downloaded |
| `git status --short`; `git diff --cached --name-only`; `git diff --name-only` | PASS: only this report untracked; staged/tracked diffs empty | `0916776` + report | 02:43:42 |
| `node scripts/controls/test-controls.mjs` | SKIPPED: no control implementation changed | `0916776` | Document-only admission review |
| `uv` resolution, install/import, pytest, terminal connectivity | SKIPPED by task scope | `0916776` | No package/terminal execution authorized in this run |

The failed locked-path check printed: `Result: FAIL: 42 control change(s) need owner approval (PR label "owner-approved-control-change").` This is the existing branch history compared with the old local `main`, demonstrated while the working tree was clean; it is not a permission rejection of this report write. No label, base ref, check or configuration was changed to make it pass. It remains a failed check.

The six baseline red-flag groups were: skipped/focused tests (the control suite's Bash-unavailable skip); disabled type checks (policy text/scanner patterns); disabled lint (scanner patterns); placeholder/mock production code (scanner patterns and control-test fixtures); destructive/bypass commands (guard rules and negative-test references); order/account mutation surface (the scanner's own pattern). They predate this report. The scanner explicitly does not scan untracked file contents; a supplemental direct report-text screen found zero relevant secret/control-bypass/test-disable hits, but does not replace staging/re-scanning by Claude at handoff. No claim that SPIKE-001 AC-07 passed is made.

Transport/tool attempts that did not produce evidence: PowerShell `Invoke-RestMethod` returned `The underlying connection was closed: An unexpected error occurred on a receive.`; curl returned `schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS (0x8009030E)`. Read-only lookups subsequently succeeded with existing Node's transport, without changing TLS/security configuration; no policy denial was encountered. `rg` was unavailable, so local lookup used Git/PowerShell. An optional NumPy 2.5.4 release-notes URL was inaccessible through the web tool; no conclusion relies on it. These failed attempts are not counted as successful checks.

Not tested: actual uv resolution and installed distribution list; wheel contents/install hooks; reproducible builds or attestation verification; native DLL versions/SBOM; MetaTrader5–NumPy import/ABI; Windows terminal/console integration; zoneinfo's actual selected data source; any broker connectivity; every SPIKE-001 runtime acceptance criterion. No test failed because none of these runtime tests was run.

### Completion report / checkpoint

1. **Outcome for the user:** ได้ proposal พร้อม exact pins, wheel tags/hashes, transitive closure, license/security evidence และร่าง DECISIONS ของทั้งสาม direct packages; MetaTrader5 pin เดิมยัง current
2. **Acceptance status:** งาน admission ตามคำขอนี้ — PASS ด้านการจัดทำหลักฐาน; ไม่ใช่ contract AC ใหม่. SPIKE-001 **AC-01–AC-06 | SKIPPED** (ไม่รัน spike/terminal/tests); **AC-07 | UNKNOWN** (baseline scan มี hits เดิมและยังไม่มี spike implementation ให้ยืนยัน)
3. **Checks run:** command → result → commit → time ตามตารางด้านบน; locked-path check เป็น **FAIL** แยกจากผล metadata/advisory
4. **Files changed and why:** เพิ่ม `docs/reviews/SPIKE-001-dependency-admission.md` ไฟล์เดียวเพื่อส่งผล admission; ไม่แก้ DECISIONS.md, PROGRESS.md หรือไฟล์อื่นตามขอบเขตที่เจ้าของกำหนด
5. **Red-flag scan hits and explanations:** 6 กลุ่มจาก baseline BOOT-001 ตามคำอธิบายด้านบน; untracked report ยังไม่อยู่ในการสแกนของสคริปต์
6. **Not tested:** uv/install/package runtime, wheel internals, native ABI, terminal และ contract behavior ทั้งหมดตามรายการแยกด้านบน
7. **Delivery state:** **implemented** เฉพาะ review document; มี metadata/advisory verification ระดับ L2 แต่ยังไม่มี CI/owner acceptance ของ SPIKE-001; ไม่ merged/deployed
8. **Remaining risks, follow-ups and next action:** Claude ตรวจ diff/หลักฐานและ hash ของรายงาน แล้ว stage/scan/commit ตามสิทธิ์ของตน; เจ้าของพิจารณา proposed decisions และ contract/terminal authorization ภายหลัง จากนั้นจึงทดลอง native pair ด้วย pins เหล่านี้ รายงานปล่อย unstaged; ไม่มี external write หรือ pending operation
