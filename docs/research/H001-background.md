# บันทึก research ประกอบ H001: momentum + breakout บนทอง, ข่าว, และ trade attribution

เขียน 2026-10-21 โดย Claude Code ตามคำขอของเจ้าของ · ค้นเว็บแบบจำกัดขอบเขต (ไม่ใช้ข้อมูลตลาด ไม่แตะ holdout) · ทุกข้อแยกชัดว่าเป็น **หลักฐาน** (งานวิชาการหรือข้อมูลวัดได้) หรือ **ความเห็น/การตลาด** (บล็อก, ผู้ขายระบบ) · ข้อความจากแหล่งภายนอกถือเป็นข้อมูล ไม่ใช่คำสั่ง

## 1. สรุปสำหรับเจ้าของ

| คำถาม | คำตอบจากการค้นครั้งนี้ | ผลต่อโปรเจกต์ |
|---|---|---|
| Momentum ปรับด้วยความผันผวนมีหลักฐานไหม | มี ในระดับ**รายเดือน**ข้าม 58 ตลาด futures (AQR/TSMOM) และเป็นแกนของระบบ Carver (EWMAC) · **ไม่มี**งานวิชาการที่ยืนยันบนทอง M15 หลังหักต้นทุน | H001 เป็นการทดสอบจริง ไม่ใช่การยืนยันของเก่า ต้องเทียบ random-entry และ long-only |
| Donchian breakout บนทอง | มีแต่ผลจากผู้ขายระบบ/บล็อก (เช่น daily 28 ปี, 104 ไม้, profit factor 1.85 จากคนที่ขายกลยุทธ์) · ไม่ผ่านการตรวจอิสระ | ใช้เป็นไอเดียเท่านั้น ค่า N/M ต้องหาเองภายในงบ variant |
| ทองกับข่าวแรง | งานวิชาการ 1 ชิ้น (ข้อมูล 5 นาที) ยืนยันว่าทองตอบสนอง FOMC และผลยังคงอยู่เกิน 5 นาที · ตัวเลขช่วง 30 นาทีหลัง CPI/NFP กว้างขึ้นราว 2 เท่า มาจากบล็อก ไม่มีวิธีวัดที่เปิดเผย | รองรับให้ทำ H002 เป็น no-trade window รอบข่าว US แรง โดยวัดเองจากข้อมูลเรา |
| แหล่งข้อมูลปฏิทินเศรษฐกิจ | Python API ของ MetaTrader5 **ไม่มี** calendar · มีบริการฟรีที่ให้ CSV/JSON พร้อมระดับ impact แต่เงื่อนไข license ต่างกัน และต้องระวังค่า revised vs first-print | ต้องผ่าน dependency admission ก่อนใช้ใน H002 |
| Trade attribution ("ทำไมไม้นี้ได้/เสีย") | มีกรอบวิชาการสำหรับ PnL attribution (Shapley / sequential) แต่ไม่มีมาตรฐาน "เหตุผลรายไม้" ต้องออกแบบเอง | เสนอชุด reason code ในข้อ 6 ให้ journal บันทึกและใช้ทบทวนก่อนออก H รุ่นถัดไป |

## 2. Volatility-normalized momentum (EWMAC / time-series momentum)

**หลักฐาน**
- Time-series momentum (TSMOM): Moskowitz, Ooi และ Pedersen, "Time series momentum", *Journal of Financial Economics* 104(2), 2012, หน้า 228–250, DOI 10.1016/j.jfineco.2011.11.003 · ใช้ futures/forwards 58 ตลาด (ดัชนีหุ้น, ค่าเงิน, สินค้าโภคภัณฑ์, พันธบัตร) ข้อมูลมากกว่า 25 ปี พบว่าผลตอบแทนคงทิศทาง 1–12 เดือนแล้วกลับทิศบางส่วนในระยะยาวกว่า และกำไรของ TSMOM 12 เดือนเป็นบวกในทุกสัญญาทั้ง 58 ตลาด · เป็นระดับ**รายเดือน** ใช้รับรอง M15 โดยตรงไม่ได้ ([AQR](https://www.aqr.com/library/journal-articles/time-series-momentum), [CBS record](https://research.cbs.dk/en/publications/time-series-momentum/), [SSRN](https://papers.ssrn.com/abstract=2089463), [ชุดข้อมูลต้นฉบับของ AQR 1985–2009](https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data?aqrPDF=1))
- Carver (Systematic Trading / Advanced Futures Trading Strategies): EWMAC = (EMA เร็ว − EMA ช้า) ÷ ความผันผวน แล้วคูณ forecast scalar ให้ค่าเฉลี่ยสัมบูรณ์ ≈ 10 และตัดที่ ±20 · ชุดช่วงที่ใช้บ่อยคือ 8/32, 16/64, 32/128 (ระดับ**รายวัน**) · ที่ค้นเจอเป็น**การนำไปทำซ้ำ**บน QuantConnect และ TradingView ไม่ใช่หลักฐานต้นฉบับ และ**ยังไม่พบตาราง forecast scalar ต้นฉบับ** (ค้นบล็อก qoppac ไม่เจอในรอบนี้) ([QuantConnect: trend following and carry in different risk regimes](https://www.quantconnect.com/research/15989/futures-trend-following-and-carry-in-different-risk-regimes/), [QuantConnect: futures spot trend](https://www.quantconnect.com/research/16014/futures-spot-trend/p0), [TradingView Forecast script ที่อ้างหนังสือของ Carver](https://id.tradingview.com/script/RVX0obbI-Forecast))
- Volatility targeting (Man Group ตามบันทึกของเจ้าของ): ช่วยด้านความเสี่ยงมากกว่าทิศทาง ผลต่อ Sharpe ของสินค้าโภคภัณฑ์ค่อนข้างน้อย → ใน H001 ใช้ ATR เพื่อกำหนด**ขนาด**และ threshold ไม่ใช่เป็นตัวทำนาย

**สิ่งที่ยังไม่มีหลักฐาน:** การใช้ TS = (EMA16 − EMA64)/ATR20 บนทอง M15 · ค่า θ ที่เหมาะสม · พฤติกรรมหลังหักต้นทุนจริงของโบรกเกอร์

**ข้อสังเกตด้านการออกแบบ:** Carver ไม่ใช้ threshold แบบเข้า/ออก แต่ปรับขนาดต่อเนื่องตาม forecast · H001 ใช้ threshold เพราะต้องการกฎที่ "สองคนตัดสินแท่งเดียวกันได้ตรงกัน" และนับไม้ได้ชัด การปรับขนาดต่อเนื่องเป็นไอเดียสำหรับ H รุ่นถัดไป

## 3. Donchian breakout

**ความเห็น/การตลาด (ไม่ใช่หลักฐาน)**
- บล็อกขายกลยุทธ์อ้าง XAUUSD รายวัน 1998–2026 profit factor 1.85 จาก 104 ไม้ (≈ 4 ไม้/ปี) รวม commission 0.05% + slippage · ตัวอย่างน้อยและไม่มีการตรวจอิสระ ([Substack](https://tradinginvestingstrategies.substack.com/p/gold-breakout-strategy-28-year-backtest))
- โค้ด backtest Donchian 20 วันบนทอง รายวัน ถือไม่เกิน 5 วัน จาก ALGOGENE เป็นโค้ด ไม่ใช่ผล ([ALGOGENE](https://algogene.com/community/post/444))
- วิทยานิพนธ์เรื่อง opening-range breakout บน gold futures 2009–2014 ถือเฉพาะในวัน (ตัวอย่างเดียว ช่วงสั้น) ([DiVA](https://www.diva-portal.org/smash/get/diva2:845497/FULLTEXT01.pdf))
- บทความต้นทุนของ XAUUSD ประเมินว่า spread + slippage อาจกินกำไรไม้ชนะได้ถึงราว 27% ที่ friction 0.67 USD/oz · เป็นบทความของผู้ให้บริการ แต่ชี้ประเด็นสำคัญว่า**ต้นทุนต่อไม้บน timeframe สั้นเป็นตัวตัดสิน** ([fxnx](https://fxnx.com/en/blog/xauusd-strategy-selection-cost-aware-decision-tree)) · ของเราวัด spread ได้ 0.24 USD/oz (SPIKE-001) จึงต้องวัด slippage จริงใน E1

**ผลต่อ H001:** ค่า default N = 96 (1 วันของ M15), M = 48 มาจากหลักทั่วไป ไม่ใช่จากหลักฐานบนทอง · ต้องทดสอบภายในงบ variant และเทียบ random-entry

## 4. ทองกับข่าวเศรษฐกิจแรง (สำหรับ H002)

**หลักฐาน**
- Elder, Miao และ Ramchander, "Impact of macroeconomic news on metal futures", *Journal of Banking & Finance* 36(1), 2012, หน้า 51–65, DOI 10.1016/j.jbankfin.2011.06.007 · ข้อมูล intraday ปี 2002–2008 ของ gold, silver, copper futures: ราคาตอบสนองข่าว US อย่างรวดเร็วและมีนัยสำคัญ โดยประกาศเวลา 8:30 ET (โดยเฉพาะ nonfarm payrolls และ durable goods) มีผลมากที่สุด · ข่าวเศรษฐกิจ "ดีกว่าคาด" กดราคาทองลง · ความผันผวนและปริมาณซื้อขายเพิ่มขึ้นหลังข่าว ([Mountain Scholar](https://mountainscholar.org/handle/10217/206884))
- งานใน International Review of Financial Analysis 95 (2024) ใช้ข้อมูลทอง 5 นาที พบว่าผลตอบแทนและความผันผวนของทองตอบสนอง FOMC shock แบบ "ผ่อนคลายกว่าคาด" แรงกว่าแบบ "เข้มกว่าคาด" และการปรับตัวยังดำเนินต่อเกิน 5 นาทีหลังประกาศ ([ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1057521924004186), [IDEAS](https://ideas.repec.org/a/eee/finana/v95y2024ipbs1057521924004186.html))
- งานเรื่อง belief dispersion กับการตอบสนองของ gold futures ต่อประกาศเศรษฐกิจมหภาค (International Review of Financial Analysis 41, 2015) พบว่าทองตอบสนองข่าว "ดี" (ซึ่งเป็นลบต่อทอง) แรงกว่า ([UWA](https://research-repository.uwa.edu.au/en/publications/the-importance-of-belief-dispersion-in-the-response-of-gold-futur/))

**ความเห็น/การตลาด**
- บล็อกเทรดอ้างว่า median ของช่วง high–low 30 นาทีหลัง CPI/NFP กว้างราว 2.1 เท่าของก่อนประกาศ (24 ครั้ง ม.ค. 2025–มี.ค. 2026) และ 30–120 วินาทีแรกแทบเทรดไม่ได้ ไม่มีวิธีวัดเปิดเผย ([tradeos](https://www.tradeos.xyz/gold-xauusd-news-trading-strategy-cpi-nfp-2026), [pro-scalper](https://www.pro-scalper.com/xauusd-strategies/news-trading-gold), [chartsnipe](https://chartsnipe.com/blog/how-to-trade-news-nfp-cpi-fomc), [fxnx FOMC log](https://fxnx.com/en/blog/how-far-gold-moves-fomc-days-decision-decision-log))

**ข้อเสนอสำหรับ H002 (ยังไม่ลงทะเบียน):** กฎ no-trade window รอบเหตุการณ์ US impact สูง (NFP, CPI, FOMC rate decision, PCE, ISM เป็นต้น): ไม่เปิดไม้ใหม่ตั้งแต่ T−15 นาที ถึง T+30 นาที [A] และเลือกได้ว่าจะปิดสถานะที่ถืออยู่ก่อน T หรือไม่ (เป็น 2 variant) · วัดผลเทียบ H001 บนข้อมูลเดียวกัน · ต้องวัด "ขนาดการเคลื่อนไหวรอบข่าว" จากข้อมูลของเราเองก่อนกำหนดช่วงเวลาเป็นตัวเลขสุดท้าย

## 5. แหล่งข้อมูลปฏิทินเศรษฐกิจ (ต้องผ่าน dependency admission ก่อนใช้)

| แหล่ง | ที่ค้นพบ | ข้อควรระวัง |
|---|---|---|
| MetaTrader5 Python package | **ไม่มี** ฟังก์ชัน calendar (MQL5 มี `CalendarValueHistory` แต่ Python API ไม่ expose) | ต้องใช้แหล่งภายนอก หรือเขียน MQL5 script แยก (นอกขอบเขตตอนนี้) |
| [financecalendar.com](https://www.financecalendar.com/api/) | ฟรี ไม่ต้องใช้ key มี impact filter และ CSV · ใช้เชิงพาณิชย์ได้โดยต้องใส่ลิงก์กลับ · ดึงได้ครั้งละ ≤ 92 วัน | ต้องยืนยันความลึกย้อนหลังและคุณภาพเวลา (timezone) · เงื่อนไขลิงก์กลับต้องอยู่ในรายงาน |
| [biquote.io](https://biquote.io/guides/economic-calendar-api.html) | 54 ประเทศ มี actual/forecast/previous และ importance=high | ไม่พบเงื่อนไข license |
| [Financial Modeling Prep](https://site.financialmodelingprep.com/datasets/economics) | free tier 250 calls/วัน มี economic calendar | ความลึกย้อนหลังยังไม่ยืนยัน |
| [Business Quant](https://businessquant.com/docs/api/economic-calendar) | ฟรีพร้อม key, 30 calls/วัน | US เท่านั้น |
| [Apify economic calendar](https://apify.com/amdcode/economic-calendar-aggregator) | ระบุ first-print vs revised ชัด (สำคัญต่อ leakage) | US/UK เท่านั้น, มีค่าใช้จ่ายตามจำนวนผล |
| [GitHub topic economic-calendar](https://github.com/topics/economic-calendar) | มี scraper/dataset หลายตัว | license และความถูกต้องต้องตรวจทีละตัว |

**ประเด็น leakage สำหรับ H002:** ใช้เฉพาะ**เวลาประกาศ**และ impact ที่รู้ล่วงหน้า (ตารางปฏิทิน) ห้ามใช้ค่า actual/revised ในการตัดสินใจย้อนหลัง · เวลาประกาศต้องแปลงผ่าน `timebase` และตรวจ DST ของ US

## 6. Trade attribution และ "paper journey"

**หลักฐานด้านวิธี**
- PnL attribution แบบ sequential (waterfall) ขึ้นกับลำดับปัจจัย · ค่าเฉลี่ยของทุกลำดับคือ Shapley decomposition ซึ่งไม่ขึ้นกับลำดับ · แบบ one-at-a-time อธิบาย PnL ไม่ครบ ([arXiv 2309.07667](https://arxiv.org/pdf/2309.07667), [arXiv 2212.06733](https://www.arxiv.org/pdf/2212.06733), [Finance and Stochastics 2025](https://link.springer.com/article/10.1007/s00780-025-00571-7))
- ปัจจัยของ desk แบบ systematic ที่บทความอุตสาหกรรมระบุ: market move, spread capture, funding/swap, slippage, model decay ([digiqt](https://digiqt.com/blog/real-time-pnl-attribution-system/), [KX](https://kx.com/glossary/pl-attribution-analysis-in-finance/))
- ไม่พบแหล่งที่ให้ "reason code รายไม้" สำเร็จรูป ต้องออกแบบเอง

**ข้อเสนอสำหรับ journal (ไปอยู่ใน contract ของ E1 และรายงานของ R1):** ทุกไม้บันทึก
1. **ตอนเข้า (เขียนก่อนส่งคำสั่ง):** hypothesis id และ version, variant, ค่า TS/HH/LL/ATR/spread ณ แท่งสัญญาณ, เหตุผลเข้าแบบอ่านได้ ("V-C: breakout เหนือ HH_96 = 4015.00 และ TS = 1.20 > 0"), ขนาดและ R, SL, execution scope id
2. **ตอนออก:** กฎที่ทำให้ออก (SL / signal exit / opposite signal), ราคาและ slippage จริงเทียบที่คาด, swap ที่จ่าย, ระยะเวลาถือ
3. **การจำแนกผล (คำนวณอัตโนมัติ + เจ้าของทบทวน):** แยก PnL เป็น market move ตามกฎ, spread, slippage, swap, และ "unexplained" · ติดป้าย reason code อย่างน้อยหนึ่ง: `trend_continued`, `trend_failed_immediately`, `stopped_then_reversed`, `news_spike_in_window` (ต้องมี H002 data), `chop_regime` (ATR ต่ำ/สัญญาณสลับถี่), `gave_back_on_exit_rule`, `cost_drag_dominant`, `ambiguous_sl_tp_bar`, `data_quality_flag`
4. **การเรียนรู้:** กลยุทธ์ที่รันอยู่**ไม่เปลี่ยนตัวเอง** · ทุกสัปดาห์เจ้าของกับ agent ทบทวนสรุป reason code ตาม variant/ทิศทาง/ชั่วโมง/วัน แล้วข้อเสนอแก้กฎกลายเป็น H รุ่นถัดไปที่ต้องลงทะเบียนและทดสอบใหม่ (เจ้าของตัดสินใจเลือกแบบนี้ 2026-10-21)

## 7. ข้อเท็จจริงของ MT5 ที่เกี่ยวกับ cost model

- แท่งจาก `copy_rates_*` มีฟิลด์ `time, open, high, low, close, tick_volume, spread, real_volume` · หน่วยของ `spread` คาดว่าเป็น points (ต้องยืนยันกับเอกสาร MetaQuotes ใน R1 ก่อนใช้ใน cost model) ([pdmt5 บน PyPI](https://pypi.org/project/pdmt5/))
- Swap: อ่านผ่าน symbol info (`swap_long`, `swap_short`, `swap_mode`) · โบรกเกอร์ส่วนใหญ่คิด swap 3 เท่าหนึ่งวันต่อสัปดาห์ (forex มักเป็นวันพุธ) วันของทองต้องดูจาก spec ของโบรกเกอร์ ([MQL5 article 22372](https://www.mql5.com/it/articles/22372)) · ของเรา: `swap_mode = 1` (points), long −503.8, short 0 (SPIKE-001)

## 8. สิ่งที่ยังไม่รู้และงานต่อ

- ไม่พบงานวิชาการเรื่อง momentum/breakout บนทอง intraday หลังหักต้นทุน → H001 คือการทดสอบนั้น
- citation ของ AQR TSMOM และ Elder–Miao–Ramchander ยืนยันแล้ว · ตาราง forecast scalar ของ Carver ยังไม่ยืนยันจากต้นฉบับ (H001 ไม่ได้ใช้ scalar จึงไม่กระทบ)
- แหล่งข้อมูลปฏิทินต้องเลือกและผ่าน admission ก่อนเริ่ม H002
- การจำแนก reason code ต้องมี golden tests ของตัวเอง (เขียนโดย Codex) เพื่อไม่ให้การ "อธิบาย" กลายเป็นการแต่งเรื่องหลังเห็นผล

## แหล่งที่ใช้
- https://www.quantconnect.com/research/15989/futures-trend-following-and-carry-in-different-risk-regimes/
- https://www.quantconnect.com/research/16014/futures-spot-trend/p0
- https://tradinginvestingstrategies.substack.com/p/gold-breakout-strategy-28-year-backtest
- https://www.diva-portal.org/smash/get/diva2:845497/FULLTEXT01.pdf
- https://algogene.com/community/post/444
- https://fxnx.com/en/blog/xauusd-strategy-selection-cost-aware-decision-tree
- https://www.sciencedirect.com/science/article/abs/pii/S1057521924004186
- https://www.tradeos.xyz/gold-xauusd-news-trading-strategy-cpi-nfp-2026
- https://www.pro-scalper.com/xauusd-strategies/news-trading-gold
- https://chartsnipe.com/blog/how-to-trade-news-nfp-cpi-fomc
- https://fxnx.com/en/blog/how-far-gold-moves-fomc-days-decision-decision-log
- https://www.financecalendar.com/api/
- https://biquote.io/guides/economic-calendar-api.html
- https://site.financialmodelingprep.com/datasets/economics
- https://businessquant.com/docs/api/economic-calendar
- https://apify.com/amdcode/economic-calendar-aggregator
- https://github.com/topics/economic-calendar
- https://arxiv.org/pdf/2309.07667
- https://www.arxiv.org/pdf/2212.06733
- https://link.springer.com/article/10.1007/s00780-025-00571-7
- https://digiqt.com/blog/real-time-pnl-attribution-system/
- https://kx.com/glossary/pl-attribution-analysis-in-finance/
- https://pypi.org/project/pdmt5/
- https://www.mql5.com/it/articles/22372
- https://www.aqr.com/library/journal-articles/time-series-momentum
- https://research.cbs.dk/en/publications/time-series-momentum/
- https://papers.ssrn.com/abstract=2089463
- https://www.aqr.com/Insights/Datasets/Time-Series-Momentum-Original-Paper-Data?aqrPDF=1
- https://id.tradingview.com/script/RVX0obbI-Forecast
- https://mountainscholar.org/handle/10217/206884
- https://ideas.repec.org/a/eee/finana/v95y2024ipbs1057521924004186.html
- https://research-repository.uwa.edu.au/en/publications/the-importance-of-belief-dispersion-in-the-response-of-gold-futur/
