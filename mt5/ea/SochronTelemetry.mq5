#property strict
#property version "0.10"
#property description "Sochron1k read-only Demo observer; NOT an execution EA"

#include "TelemetryProtocol.mqh"

input bool EnableReadOnlyTelemetry=false;
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

void ScState(const string state)
  {
   if(state==sc_state) return;
   sc_state=state;
   Print("Sochron read-only telemetry: ",state); // Static reason codes only.
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
      BrokerUtcOffsetSeconds<=50400 && BrokerUtcOffsetSeconds%60==0;
  }

void ScAppendMode(string &modes,const string mode)
  {
   if(modes!="") modes+=",";
   modes+=ScQuote(mode);
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
   char data[],result[];
   if(body!="")
     {
      int copied=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);
      if(copied<1 || copied-1>16384) return -1;
      ArrayResize(data,copied-1); // JSON body must NOT include the terminating NUL.
     }
   string headers="Authorization: Bearer "+sc_token+"\r\nContent-Type: application/json\r\n";
   string result_headers;
   ulong started=GetTickCount64();
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
   sc_retry_after=GetTickCount64()+10000;
  }

int OnInit()
  {
   sc_latched=false; sc_boot=""; sc_sequence=0; sc_retry_after=0; sc_token=""; sc_state="";
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
  }

void OnTimer()
  {
   if(!EnableReadOnlyTelemetry || sc_latched) return;
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
     { sc_boot=""; sc_sequence=0; ScState("DISCONNECTED"); return; }
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
   ScState("READ_ONLY_SAMPLE_RECEIVED_NOT_TRADE_READY");
  }
