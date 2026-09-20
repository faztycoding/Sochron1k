#property strict
#property script_show_inputs
#property description "Pure telemetry/chart protocol tests; no account or network access"

#include "TelemetryProtocol.mqh"

int sc_failures=0,sc_checks=0;
void ScCheck(const bool condition,const string name)
  {
   sc_checks++;
   if(!condition) { sc_failures++; Print("FAIL protocol case: ",name); }
  }

void OnStart()
  {
   string boot;
   long sequence;
   string id="11111111-2222-4333-8444-555555555555";
   string good="{\"boot_id\":"+ScQuote(id)+",\"next_sequence\":1}";
   ScCheck(ScChallenge(good,boot,sequence) && boot==id && sequence==1,"challenge");
   ScCheck(ScChallenge(" { \"next_sequence\": 12, \"boot_id\": "+ScQuote(id)+" } ",
                       boot,sequence) && sequence==12,"reordered whitespace");
   ScCheck(!ScChallenge(good+" trailing",boot,sequence),"trailing data");
   ScCheck(!ScChallenge("{\"boot_id\":\"invalid\",\"next_sequence\":1}",boot,sequence),"uuid");
   ScCheck(!ScChallenge("{\"boot_id\":"+ScQuote(id)+",\"next_sequence\":0}",boot,sequence),"zero");
   ScCheck(!ScChallenge("{\"boot_id\":"+ScQuote(id)+",\"next_sequence\":01}",boot,sequence),"leading zero");
   ScCheck(!ScChallenge("{\"boot_id\":"+ScQuote(id)+",\"next_sequence\":1.0}",boot,sequence),"float");
   ScCheck(!ScChallenge("{\"boot_id\":"+ScQuote(id)+",\"next_sequence\":true}",boot,sequence),"bool sequence");
   ScCheck(!ScChallenge("{\"boot_id\":"+ScQuote(id)+",\"boot_id\":"+ScQuote(id)+"}",
                        boot,sequence),"duplicate key");
   ScCheck(!ScChallenge("{\"boot_id\":"+ScQuote(id)+",\"next_sequence\":9007199254740992}",
                        boot,sequence),"overflow");
   ScCheck(ScPositiveInteger("9007199254740991",sequence) && sequence==SC_MAX_SEQUENCE,"max sequence");
   ScCheck(!ScPositiveInteger("-1",sequence),"negative sequence");
   ScCheck(ScReceipt("{\"accepted\":true,\"duplicate\":false,\"sequence\":7}",7),"receipt");
   ScCheck(ScReceipt("{\"sequence\":7,\"duplicate\":true,\"accepted\":true}",7),"duplicate receipt");
   ScCheck(!ScReceipt("{\"accepted\":true,\"duplicate\":false,\"sequence\":8}",7),"wrong sequence");
   ScCheck(!ScReceipt("{\"accepted\":false,\"duplicate\":false,\"sequence\":7}",7),"not accepted");
   ScCheck(!ScReceipt("{\"accepted\":true,\"duplicate\":false,\"sequence\":7,\"extra\":1}",7),"extra key");
   ScCheck(ScQuote("a\"b\\c\n")=="\"a\\\"b\\\\c\\u000a\"","JSON escape");
   ScCheck(ScDecimal(0.01)=="\"0.0100000000\"","decimal precision");
   ScCheck(ScUtc(D'2026.09.17 00:00:00')=="2026-09-17T00:00:00Z","UTC formatting");
   ScCheck(!ScTokenValid(""),"empty token");
   ScCheck(!ScTokenValid("fixture-not-a-credential"),"short token");

   ScSample s;
   s.executor_id="synthetic-ea"; s.account_ref="123456789";
   s.server="Synthetic-Demo"; s.currency="USD"; s.margin_mode="retail_hedging";
   s.symbol="XAUUSD.fixture"; s.observed_at="2026-09-17T00:00:00Z";
   s.terminal_build=1; s.tick_time_server_msc=((long)D'2026.09.17 00:00:00')*1000+7200000;
   s.account_trade_allowed=false; s.market_open=true; s.broker_utc_offset_seconds=7200;
   s.digits=2; s.stops=10; s.freeze=0;
   s.equity=1000; s.balance=1000; s.free_margin=1000;
   s.bid=2500; s.ask=2500.2; s.tick_size=0.01;
   s.volume_min=0.01; s.volume_max=100; s.volume_step=0.01;
   s.filling_modes_json="[\"fok\",\"ioc\"]";
   string packet=ScSnapshotJson(s,id,1);
   char bytes[];
   int count=StringToCharArray(packet,bytes,0,WHOLE_ARRAY,CP_UTF8);
   ScCheck(count>1 && bytes[count-1]==0,"UTF8 terminator");
   ArrayResize(bytes,count-1);
   ScCheck(ArraySize(bytes)==StringLen(packet),"ASCII fixture byte length excludes NUL");
   ScCheck(ScSessionContains(3600,0,7200,false),"ordinary session inside");
   ScCheck(!ScSessionContains(7200,0,7200,false),"ordinary session end exclusive");
   ScCheck(ScSessionContains(23*3600,22*3600,2*3600,false),"overnight start day");
   ScCheck(ScSessionContains(3600,22*3600,2*3600,true),"overnight carry day");
   ScCheck(!ScSessionContains(12*3600,22*3600,2*3600,false),"overnight outside");
   ScCheck(!ScSessionContains(0,0,0,false),"ambiguous zero session refused");

   MqlRates rates[2];
   for(int i=0;i<2;i++)
     {
      rates[i].time=D'2026.09.17 01:55:00'+i*300;
      rates[i].open=2500; rates[i].high=2501; rates[i].low=2499;
      rates[i].close=(i==0 ? 2500.5 : 2500.25);
      rates[i].tick_volume=10; rates[i].spread=20; rates[i].real_volume=0;
     }
   string chart,invalid;
   ScCheck(ScChartJson(s,id,1,"M5","bid",rates,2,chart),"chart fixture");
   ScCheck(ScChartJson(s,id,1,"M5","last",rates,2,invalid),"explicit Last basis");
   ScCheck(ScChartSeconds("M1")==60 && ScChartSeconds("M5")==300 &&
           ScChartSeconds("M15")==900 && ScChartSeconds("H1")==3600,"four periods");
   ScCheck(!ScChartJson(s,id,1,"M2","bid",rates,2,invalid),"unsupported period");
   ScCheck(!ScChartJson(s,id,1,"M5","ask",rates,2,invalid),"unsupported price basis");
   ScCheck(!ScChartJson(s,"bad",1,"M5","bid",rates,2,invalid),"chart boot");
   ScCheck(!ScChartJson(s,id,0,"M5","bid",rates,2,invalid),"chart sequence");
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,1,invalid),"chart count low");
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,241,invalid),"chart count high");
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,3,invalid),"array shorter than count");
   rates[1].time=rates[0].time;
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,2,invalid),"duplicate bar");
   rates[1].time=D'2026.09.17 02:00:01';
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,2,invalid),"misaligned bar");
   rates[1].time=D'2026.09.17 02:00:00';
   rates[1].low=2500.5;
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,2,invalid),"invalid OHLC");
   rates[1].low=2499; rates[1].tick_volume=0;
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,2,invalid),"empty tick volume");
   rates[1].tick_volume=10; rates[1].spread=-1;
   ScCheck(!ScChartJson(s,id,1,"M5","bid",rates,2,invalid),"negative spread");
   rates[1].spread=20;
   ScCheck(!ScChartPrice(2500.001,2,0.01),"refuse decimal rounding");
   ScCheck(!ScChartPrice(2500.1,2,0.25),"refuse off-grid price");
   ScCheck(ScChartPrice(2500.25,2,0.25),"quarter tick grid");
   ScCheck(!ScChartPrice(1e14,10,0.01),"scaled integer precision limit");
   ScCheck(!ScChartPrice(-1,2,0.01),"negative price");
   ScCheck(!ScChartPrice(2500,2,0),"invalid tick size");
   ScCheck(!ScChartPrice(2500,11,0.01),"invalid digits");
   ScCheck(ScErrorIs("{\"detail\":\"BOOT_MISMATCH\"}","BOOT_MISMATCH"),"boot error");
   ScCheck(!ScErrorIs("{\"detail\":\"CLOSED_BAR_CHANGED\"}","BOOT_MISMATCH"),"correction is not restart");
   ScCheck(!ScErrorIs("{\"detail\":\"BOOT_MISMATCH\",\"extra\":1}","BOOT_MISMATCH"),"invalid error envelope");
   ScCheck(ScChartJson(s,id,1,"M5","bid",rates,2,invalid) && invalid==chart,"fixture unchanged");
   if(sc_failures!=0)
     { Print("FAIL Sochron protocol self-test: ",sc_failures," of ",sc_checks); return; }

   // Synthetic output only. Never substitute a real account snapshot for this fixture.
   // This script deliberately overwrites its own generated fixture on a new test run.
   int output=FileOpen("SochronTelemetrySelfTest.json",FILE_WRITE|FILE_BIN);
   if(output==INVALID_HANDLE) { Print("FAIL self-test fixture output"); return; }
   uint written=FileWriteArray(output,bytes,0,ArraySize(bytes));
   FileClose(output);
   if(written!=ArraySize(bytes)) { Print("FAIL self-test fixture incomplete"); return; }
   count=StringToCharArray(chart,bytes,0,WHOLE_ARRAY,CP_UTF8);
   if(count<2) { Print("FAIL chart fixture encoding"); return; }
   ArrayResize(bytes,count-1);
   output=FileOpen("SochronChartSelfTest.json",FILE_WRITE|FILE_BIN);
   if(output==INVALID_HANDLE) { Print("FAIL chart self-test fixture output"); return; }
   written=FileWriteArray(output,bytes,0,ArraySize(bytes));
   FileClose(output);
   if(written!=ArraySize(bytes)) { Print("FAIL chart self-test fixture incomplete"); return; }
   Print("PASS Sochron protocol self-test: ",sc_checks," cases; two synthetic fixtures generated");
  }
