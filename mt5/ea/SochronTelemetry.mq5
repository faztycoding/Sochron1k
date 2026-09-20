#property strict
#property version "0.12"
#property description "Sochron1k read-only Demo observer; NOT an execution EA"

#include "TelemetryProtocol.mqh"

input bool EnableReadOnlyTelemetry=false;
input bool EnableReadOnlyCharts=false;
input int ChartBars=120;
input long ExpectedLogin=0;
input string ExpectedServer="";
input string ExpectedCurrency="";
input string ExpectedSymbol="";
input string ExecutorId="";
input int ExpectedMarginMode=-1;
input int BrokerUtcOffsetSeconds=2147483647; // Unknown; never infer an offset.

const string SC_API="http://127.0.0.1:8000/bridge/v1";
const string SC_TOKEN_FILE="sochron-telemetry.token";
const int SC_TIMEOUT_MS=500;
string sc_token="",sc_boot="",sc_state="";
long sc_sequence=0;
ulong sc_retry_after=0;
bool sc_latched=false;
int sc_requests_this_timer=0;
string sc_chart_boot="",sc_chart_state="";
long sc_chart_sequence=0;
int sc_chart_index=0;
ulong sc_chart_retry_after=0;
bool sc_chart_due=false,sc_chart_latched=false;

void ScState(const string state)
  {
   if(state==sc_state) return;
   sc_state=state;
   Print("Sochron read-only telemetry: ",state); // Static reason codes only.
  }

void ScChartState(const string state)
  {
   if(state==sc_chart_state) return;
   sc_chart_state=state;
   Print("Sochron read-only chart: ",state); // Static codes, never payloads or identity.
  }

void ScResetChartConnection()
  {
   sc_chart_boot=""; sc_chart_sequence=0; sc_chart_due=false;
   // A validation/history latch survives reconnect; only explicit reinit releases it.
  }

bool ScLoadToken()
  {
   int handle=FileOpen(SC_TOKEN_FILE,FILE_READ|FILE_BIN);
   if(handle==INVALID_HANDLE) return false;
   ulong size=FileSize(handle);
   if(size<43 || size>128) { FileClose(handle); return false; }
   uchar bytes[];
   uint count=FileReadArray(handle,bytes,0,(uint)size);
   FileClose(handle);
   if(count!=size) return false;
   for(uint i=0;i<count;i++)
     {
      uchar c=bytes[i];
      if(!((c>=65 && c<=90) || (c>=97 && c<=122) ||
           (c>=48 && c<=57) || c==45 || c==95))
        { ArrayInitialize(bytes,0); return false; }
     }
   sc_token=CharArrayToString(bytes,0,(int)size,CP_UTF8);
   ArrayInitialize(bytes,0);
   return ScTokenValid(sc_token);
  }

string ScMarginMode(const long mode)
  {
   if(mode==ACCOUNT_MARGIN_MODE_RETAIL_NETTING) return "retail_netting";
   if(mode==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) return "retail_hedging";
   if(mode==ACCOUNT_MARGIN_MODE_EXCHANGE) return "exchange";
   return "";
  }

bool ScAccountInteger(const ENUM_ACCOUNT_INFO_INTEGER property,long &value)
  {
   ResetLastError(); value=AccountInfoInteger(property);
   return GetLastError()==0;
  }

bool ScAccountString(const ENUM_ACCOUNT_INFO_STRING property,string &value)
  {
   ResetLastError(); value=AccountInfoString(property);
   return GetLastError()==0;
  }

bool ScAccountDouble(const ENUM_ACCOUNT_INFO_DOUBLE property,double &value)
  {
   ResetLastError(); value=AccountInfoDouble(property);
   return GetLastError()==0 && MathIsValidNumber(value);
  }

bool ScIdentityMatches()
  {
   // Re-read terminal truth; a configured string saying Demo is insufficient.
   long mode,login,margin;
   string server,currency;
   return ScAccountInteger(ACCOUNT_TRADE_MODE,mode) && mode==ACCOUNT_TRADE_MODE_DEMO &&
      ScAccountInteger(ACCOUNT_LOGIN,login) && login==ExpectedLogin &&
      ScAccountString(ACCOUNT_SERVER,server) && server==ExpectedServer &&
      ScAccountString(ACCOUNT_CURRENCY,currency) && currency==ExpectedCurrency &&
      ScAccountInteger(ACCOUNT_MARGIN_MODE,margin) && margin==ExpectedMarginMode &&
      _Symbol==ExpectedSymbol;
  }

bool ScConfigurationValid()
  {
   return ExpectedLogin>0 && StringLen(ExpectedServer)>0 && StringLen(ExpectedServer)<=128 &&
      StringLen(ExpectedCurrency)>=3 && StringLen(ExpectedCurrency)<=8 &&
      StringLen(ExpectedSymbol)>0 && StringLen(ExpectedSymbol)<=32 &&
      StringLen(ExecutorId)>0 && StringLen(ExecutorId)<=128 &&
      ScMarginMode(ExpectedMarginMode)!="" && BrokerUtcOffsetSeconds>=-50400 &&
      BrokerUtcOffsetSeconds<=50400 && BrokerUtcOffsetSeconds%60==0 &&
      (!EnableReadOnlyCharts || (ChartBars>=2 && ChartBars<=240));
  }

void ScAppendMode(string &modes,const string mode)
  {
   if(modes!="") modes+=",";
   modes+=ScQuote(mode);
  }

bool ScSessionDayOpen(const ENUM_DAY_OF_WEEK day,const int second_of_day,
                      const bool previous_day,bool &open)
  {
   for(uint index=0;index<64;index++)
     {
      datetime from_time,to_time;
      ResetLastError();
      if(!SymbolInfoSessionTrade(ExpectedSymbol,day,index,from_time,to_time))
         return GetLastError()==0; // No further session is normal; a terminal error is not.
      long from_second=(long)from_time,to_second=(long)to_time;
      if(from_second<0 || from_second>=86400 || to_second<0 || to_second>86400 ||
         from_second==to_second) return false;
      if(ScSessionContains(second_of_day,(int)from_second,(int)to_second,previous_day))
         open=true;
     }
   return false; // Refuse an unbounded or malformed broker session table.
  }

bool ScReadMarketOpen(const datetime server_time,bool &open)
  {
   open=false;
   long trade_mode;
   if(!SymbolInfoInteger(ExpectedSymbol,SYMBOL_TRADE_MODE,trade_mode)) return false;
   if(trade_mode==SYMBOL_TRADE_MODE_DISABLED || trade_mode==SYMBOL_TRADE_MODE_CLOSEONLY)
      return true;
   if(trade_mode!=SYMBOL_TRADE_MODE_LONGONLY && trade_mode!=SYMBOL_TRADE_MODE_SHORTONLY &&
      trade_mode!=SYMBOL_TRADE_MODE_FULL) return false;
   MqlDateTime value;
   if(!TimeToStruct(server_time,value) || value.day_of_week<0 || value.day_of_week>6) return false;
   int second_of_day=value.hour*3600+value.min*60+value.sec;
   ENUM_DAY_OF_WEEK current=(ENUM_DAY_OF_WEEK)value.day_of_week;
   ENUM_DAY_OF_WEEK previous=(ENUM_DAY_OF_WEEK)((value.day_of_week+6)%7);
   return ScSessionDayOpen(current,second_of_day,false,open) &&
      ScSessionDayOpen(previous,second_of_day,true,open);
  }

bool ScReadSample(ScSample &s)
  {
   if(!TerminalInfoInteger(TERMINAL_CONNECTED) || !ScIdentityMatches()) return false;
   if(!SymbolIsSynchronized(ExpectedSymbol)) return false;
   MqlTick tick;
   if(!SymbolInfoTick(ExpectedSymbol,tick) || tick.time_msc<=0 ||
      !MathIsValidNumber(tick.bid) || !MathIsValidNumber(tick.ask) ||
      tick.bid<=0 || tick.ask<tick.bid) return false;
   long digits,stops,freeze,fill,execution;
   if(!SymbolInfoInteger(ExpectedSymbol,SYMBOL_DIGITS,digits) ||
      !SymbolInfoInteger(ExpectedSymbol,SYMBOL_TRADE_STOPS_LEVEL,stops) ||
      !SymbolInfoInteger(ExpectedSymbol,SYMBOL_TRADE_FREEZE_LEVEL,freeze) ||
      !SymbolInfoInteger(ExpectedSymbol,SYMBOL_FILLING_MODE,fill) ||
      !SymbolInfoInteger(ExpectedSymbol,SYMBOL_TRADE_EXEMODE,execution) ||
      !SymbolInfoDouble(ExpectedSymbol,SYMBOL_TRADE_TICK_SIZE,s.tick_size) ||
      !SymbolInfoDouble(ExpectedSymbol,SYMBOL_VOLUME_MIN,s.volume_min) ||
      !SymbolInfoDouble(ExpectedSymbol,SYMBOL_VOLUME_MAX,s.volume_max) ||
      !SymbolInfoDouble(ExpectedSymbol,SYMBOL_VOLUME_STEP,s.volume_step)) return false;
   if(digits<0 || digits>10 || stops<0 || freeze<0 || stops>2147483647 || freeze>2147483647 ||
      !MathIsValidNumber(s.tick_size) || !MathIsValidNumber(s.volume_min) ||
      !MathIsValidNumber(s.volume_max) || !MathIsValidNumber(s.volume_step) ||
      s.tick_size<=0 || s.volume_min<=0 || s.volume_max<s.volume_min || s.volume_step<=0) return false;

   bool request_or_instant=(execution==SYMBOL_TRADE_EXECUTION_REQUEST ||
                            execution==SYMBOL_TRADE_EXECUTION_INSTANT);
   if(!request_or_instant && execution!=SYMBOL_TRADE_EXECUTION_MARKET &&
      execution!=SYMBOL_TRADE_EXECUTION_EXCHANGE) return false;
   string modes="";
   if(request_or_instant || (fill&SYMBOL_FILLING_FOK)!=0) ScAppendMode(modes,"fok");
   if(request_or_instant || (fill&SYMBOL_FILLING_IOC)!=0) ScAppendMode(modes,"ioc");
   if(execution!=SYMBOL_TRADE_EXECUTION_MARKET) ScAppendMode(modes,"return");
   if((fill&SYMBOL_FILLING_BOC)!=0) ScAppendMode(modes,"boc");
   if(modes=="") return false;
   s.filling_modes_json="["+modes+"]";
   s.executor_id=ExecutorId;
   s.account_ref=IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN));
   s.server=AccountInfoString(ACCOUNT_SERVER);
   s.currency=AccountInfoString(ACCOUNT_CURRENCY);
   s.margin_mode=ScMarginMode(AccountInfoInteger(ACCOUNT_MARGIN_MODE));
   s.symbol=ExpectedSymbol;
   s.terminal_build=TerminalInfoInteger(TERMINAL_BUILD);
   s.account_trade_allowed=(bool)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED);
   if(!ScAccountDouble(ACCOUNT_EQUITY,s.equity) ||
      !ScAccountDouble(ACCOUNT_BALANCE,s.balance) ||
      !ScAccountDouble(ACCOUNT_MARGIN_FREE,s.free_margin)) return false;
   s.bid=tick.bid; s.ask=tick.ask; s.tick_time_server_msc=tick.time_msc;
   if(!ScReadMarketOpen(tick.time,s.market_open)) return false;
   s.digits=(int)digits; s.stops=(int)stops; s.freeze=(int)freeze;
   s.broker_utc_offset_seconds=BrokerUtcOffsetSeconds;
   s.observed_at=ScUtc(TimeGMT());
   // Account switching during collection invalidates the entire observation.
   return s.observed_at!="" && s.terminal_build>0 &&
      TerminalInfoInteger(TERMINAL_CONNECTED) && ScIdentityMatches();
  }

int ScRequest(const string method,const string path,const string body,string &response)
  {
   response="";
   if(sc_latched || !ScIdentityMatches() || !TerminalInfoInteger(TERMINAL_CONNECTED)) return -1;
   if(sc_requests_this_timer>=1)
     { sc_latched=true; ScState("REQUEST_BUDGET_EXCEEDED_REINITIALIZE"); return -1; }
   char data[],result[];
   if(body!="")
     {
      int copied=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);
      int maximum=(method=="POST" && path=="/chart/snapshot") ? 131072 : 16384;
      if(copied<1 || copied-1>maximum) return -1;
      ArrayResize(data,copied-1); // JSON body must NOT include the terminating NUL.
     }
   string headers="Authorization: Bearer "+sc_token+"\r\nContent-Type: application/json\r\n";
   string result_headers;
   ulong started=GetTickCount64();
   sc_requests_this_timer++;
   int status=WebRequest(method,SC_API+path,headers,SC_TIMEOUT_MS,data,result,result_headers);
   headers="";
   if(GetTickCount64()-started>1000)
     {
      sc_latched=true;
      ScState("TRANSPORT_DEADLINE_EXCEEDED_REINITIALIZE");
      return -1;
     }
   // The library owns allocation while receiving; this bounds parsing, not allocation.
   if(ArraySize(result)>2048) return -1;
   response=CharArrayToString(result,0,ArraySize(result),CP_UTF8);
   return status;
  }

void ScReconnectLater()
  {
   sc_boot=""; sc_sequence=0;
   ScResetChartConnection();
   sc_retry_after=GetTickCount64()+10000;
  }

bool ScReadChartPacket(const ENUM_TIMEFRAMES period,const string name,string &packet)
  {
   packet="";
   ScSample before,after;
   if(!ScReadSample(before)) return false;
   long synced,available,last_before,basis,custom;
   if(!SymbolInfoInteger(ExpectedSymbol,SYMBOL_CUSTOM,custom) || custom!=0 ||
      !SymbolInfoInteger(ExpectedSymbol,SYMBOL_CHART_MODE,basis) ||
      (basis!=SYMBOL_CHART_MODE_BID && basis!=SYMBOL_CHART_MODE_LAST) ||
      !SeriesInfoInteger(ExpectedSymbol,period,SERIES_SYNCHRONIZED,synced) || synced!=1 ||
      !SeriesInfoInteger(ExpectedSymbol,period,SERIES_BARS_COUNT,available) || available<ChartBars ||
      !SeriesInfoInteger(ExpectedSymbol,period,SERIES_LASTBAR_DATE,last_before)) return false;
   // Fixed non-series array: CopyRates places the oldest copied bar at index zero.
   MqlRates rates[240];
   int copied=CopyRates(ExpectedSymbol,period,0,ChartBars,rates);
   if(copied!=ChartBars) return false;
   long last_after,basis_after;
   if(!SeriesInfoInteger(ExpectedSymbol,period,SERIES_SYNCHRONIZED,synced) || synced!=1 ||
      !SeriesInfoInteger(ExpectedSymbol,period,SERIES_LASTBAR_DATE,last_after) ||
      last_after!=last_before || last_after!=(long)rates[copied-1].time ||
      !SymbolInfoInteger(ExpectedSymbol,SYMBOL_CHART_MODE,basis_after) || basis_after!=basis ||
      !ScReadSample(after) || before.digits!=after.digits || before.tick_size!=after.tick_size ||
      before.terminal_build!=after.terminal_build) return false;
   // A clock/offset mismatch must not manufacture a future candle.
   if(last_after>(long)TimeGMT()+BrokerUtcOffsetSeconds) return false;
   return ScChartJson(after,sc_chart_boot,sc_chart_sequence,name,
                      basis==SYMBOL_CHART_MODE_BID ? "bid" : "last",rates,copied,packet);
  }

void ScChartUnconfirmed(const int status,const string response)
  {
   if(status==409 && ScErrorIs(response,"BOOT_MISMATCH"))
     { ScReconnectLater(); ScChartState("API_RESTART_RECONNECTING"); return; }
   if(status>=400 && status<500 && status!=408 && status!=429)
     {
      sc_chart_latched=true;
      ScResetChartConnection();
      ScChartState("CHART_REJECTED_REVIEW_BEFORE_REINITIALIZE");
      return;
     }
   ScResetChartConnection();
   sc_chart_retry_after=GetTickCount64()+10000;
   ScChartState("CHART_UNCONFIRMED_BACKOFF");
  }

void ScChartTimer()
  {
   sc_chart_due=false; // The next timer belongs to telemetry, including on failure.
   string response;
   if(sc_chart_boot=="")
     {
      string boot; long sequence;
      int status=ScRequest("GET","/chart/challenge","",response);
      if(sc_latched) return;
      if(status!=200 || !ScChallenge(response,boot,sequence))
        { ScChartUnconfirmed(status,response); return; }
      if(boot!=sc_boot)
        { ScReconnectLater(); ScChartState("API_RESTART_RECONNECTING"); return; }
      sc_chart_boot=boot; sc_chart_sequence=sequence;
      ScChartState("CHART_CHALLENGE_RECEIVED");
      return;
     }
   ENUM_TIMEFRAMES periods[4]={PERIOD_M1,PERIOD_M5,PERIOD_M15,PERIOD_H1};
   string names[4]={"M1","M5","M15","H1"};
   int index=sc_chart_index;
   sc_chart_index=(sc_chart_index+1)%4; // An unavailable timeframe cannot starve others.
   string packet;
   ulong started=GetTickCount64();
   bool collected=ScReadChartPacket(periods[index],names[index],packet);
   if(GetTickCount64()-started>250)
     {
      sc_chart_latched=true; ScResetChartConnection();
      ScChartState("HISTORY_BUDGET_EXCEEDED_REVIEW_BEFORE_REINITIALIZE");
      return; // After-the-fact detection, not a preemptive CopyRates deadline.
     }
   if(!ScIdentityMatches())
     { sc_latched=true; ScState("IDENTITY_CHANGED_REINITIALIZE"); return; }
   if(!collected) { ScChartState("SYNCHRONIZED_HISTORY_UNAVAILABLE"); return; }
   int status=ScRequest("POST","/chart/snapshot",packet,response);
   if(sc_latched) return;
   if(status!=200 || !ScReceipt(response,sc_chart_sequence))
     { ScChartUnconfirmed(status,response); return; }
   if(sc_chart_sequence==SC_MAX_SEQUENCE)
     { sc_chart_latched=true; ScChartState("CHART_SEQUENCE_EXHAUSTED_REINITIALIZE_API"); return; }
   sc_chart_sequence++;
   ScChartState("CHART_RECEIVED_NOT_TRADE_READY");
  }

int OnInit()
  {
   sc_latched=false; sc_boot=""; sc_sequence=0; sc_retry_after=0; sc_token=""; sc_state="";
   ScResetChartConnection(); sc_chart_index=0; sc_chart_retry_after=0;
   sc_chart_latched=false; sc_chart_state="";
   if(EnableReadOnlyCharts && !EnableReadOnlyTelemetry)
     { ScState("CHART_REQUIRES_READ_ONLY_TELEMETRY"); return INIT_PARAMETERS_INCORRECT; }
   if(!EnableReadOnlyTelemetry) { ScState("DISABLED"); return INIT_SUCCEEDED; }
   if(MQLInfoInteger(MQL_TESTER)) { ScState("TESTER_NETWORK_UNSUPPORTED"); return INIT_FAILED; }
   if(!ScConfigurationValid() || !ScIdentityMatches())
     { ScState("DEMO_IDENTITY_OR_CONFIG_INVALID"); return INIT_PARAMETERS_INCORRECT; }
   if(!ScLoadToken()) { ScState("PRIVATE_TOKEN_FILE_INVALID"); return INIT_FAILED; }
   if(!EventSetTimer(1)) { ScState("TIMER_UNAVAILABLE"); return INIT_FAILED; }
   ScState("READ_ONLY_STARTING");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   sc_token=""; sc_boot=""; sc_sequence=0;
   ScResetChartConnection();
  }

void OnTimer()
  {
   sc_requests_this_timer=0;
   if(!EnableReadOnlyTelemetry || sc_latched) return;
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
     { sc_boot=""; sc_sequence=0; ScResetChartConnection(); ScState("DISCONNECTED"); return; }
   if(!ScIdentityMatches())
     { sc_latched=true; ScState("IDENTITY_CHANGED_REINITIALIZE"); return; }
   if(GetTickCount64()<sc_retry_after) return;
   string response;
   if(sc_boot=="")
     {
      int status=ScRequest("GET","/challenge","",response);
      if(sc_latched) return;
      if(status!=200 || !ScChallenge(response,sc_boot,sc_sequence))
        { ScReconnectLater(); ScState("CHALLENGE_UNAVAILABLE"); }
      else ScState("READ_ONLY_SAMPLING");
      return; // At most one WebRequest per timer.
     }
   if(EnableReadOnlyCharts && !sc_chart_latched && sc_chart_due &&
      GetTickCount64()>=sc_chart_retry_after)
     { ScChartTimer(); return; } // This branch never also sends telemetry.
   ScSample sample;
   if(!ScReadSample(sample)) { ScState("OBSERVATION_UNAVAILABLE"); return; }
   string packet=ScSnapshotJson(sample,sc_boot,sc_sequence);
   int status=ScRequest("POST","/snapshot",packet,response);
   if(sc_latched) return;
   if(status!=200 || !ScReceipt(response,sc_sequence))
     { ScReconnectLater(); ScState("OBSERVATION_UNCONFIRMED"); return; }
   if(sc_sequence==SC_MAX_SEQUENCE)
     { sc_latched=true; ScState("SEQUENCE_EXHAUSTED_REINITIALIZE_API"); return; }
   sc_sequence++;
   sc_chart_due=EnableReadOnlyCharts && !sc_chart_latched;
   ScState("READ_ONLY_SAMPLE_RECEIVED_NOT_TRADE_READY");
  }
