#property strict
#property version "0.10"
#property description "Sochron1k read-only Demo execution inventory; never polls commands"

#include "ExecutionProtocol.mqh"

input bool EnableReadOnlyExecutionInventory=false;
input long ExpectedLogin=0;
input string ExpectedServer="";
input string ExpectedCurrency="";
input string ExpectedSymbol="";
input string ExecutorId="";
input int ExpectedMarginMode=-1;
input long ExpectedMagicNumber=0;

const string SCXI_API="http://127.0.0.1:8000/executor/v1";
const string SCXI_TOKEN_FILE="sochron-execution.token";
const int SCXI_TIMEOUT_MS=500;
const int SCXI_MAX_CURRENT_ITEMS=32;
string scxi_token="",scxi_boot="",scxi_generation="",scxi_state="";
long scxi_sequence=0;
ulong scxi_retry_after=0;
bool scxi_latched=false;
int scxi_requests_this_timer=0;

struct ScxiScan
  {
   long foreign_orders,foreign_positions,owned_orders,owned_positions;
   string fingerprint;
  };

void ScxiState(const string state)
  {
   if(state==scxi_state) return;
   scxi_state=state;
   Print("Sochron read-only execution inventory: ",state);
  }

string ScxiMarginMode(const long mode)
  {
   if(mode==ACCOUNT_MARGIN_MODE_RETAIL_NETTING) return "retail_netting";
   if(mode==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) return "retail_hedging";
   if(mode==ACCOUNT_MARGIN_MODE_EXCHANGE) return "exchange";
   return "";
  }

bool ScxiAccountInteger(const ENUM_ACCOUNT_INFO_INTEGER property,long &value)
  {
   ResetLastError(); value=AccountInfoInteger(property);
   return GetLastError()==0;
  }

bool ScxiAccountString(const ENUM_ACCOUNT_INFO_STRING property,string &value)
  {
   ResetLastError(); value=AccountInfoString(property);
   return GetLastError()==0;
  }

bool ScxiAccountDouble(const ENUM_ACCOUNT_INFO_DOUBLE property,double &value)
  {
   ResetLastError(); value=AccountInfoDouble(property);
   return GetLastError()==0 && MathIsValidNumber(value);
  }

bool ScxiIdentityMatches()
  {
   long mode,login,margin;
   string server,currency;
   return TerminalInfoInteger(TERMINAL_CONNECTED) &&
      ScxiAccountInteger(ACCOUNT_TRADE_MODE,mode) && mode==ACCOUNT_TRADE_MODE_DEMO &&
      ScxiAccountInteger(ACCOUNT_LOGIN,login) && login==ExpectedLogin &&
      ScxiAccountString(ACCOUNT_SERVER,server) && server==ExpectedServer &&
      ScxiAccountString(ACCOUNT_CURRENCY,currency) && currency==ExpectedCurrency &&
      ScxiAccountInteger(ACCOUNT_MARGIN_MODE,margin) && margin==ExpectedMarginMode &&
      _Symbol==ExpectedSymbol;
  }

bool ScxiConfigurationValid()
  {
   return ExpectedLogin>0 && StringLen(ExpectedServer)>0 && StringLen(ExpectedServer)<=128 &&
      StringLen(ExpectedCurrency)>=3 && StringLen(ExpectedCurrency)<=8 &&
      StringLen(ExpectedSymbol)>0 && StringLen(ExpectedSymbol)<=32 &&
      StringLen(ExecutorId)>0 && StringLen(ExecutorId)<=128 &&
      ScxSafeIdentifier(ExecutorId,128) && ScxSafeIdentifier(ExpectedServer,128) &&
      ScxCurrency(ExpectedCurrency) && ScxSafeIdentifier(ExpectedSymbol,32) &&
      ScxiMarginMode(ExpectedMarginMode)!="" && ExpectedMagicNumber>0 &&
      ExpectedMagicNumber<=2147483647;
  }

bool ScxiLoadToken()
  {
   int handle=FileOpen(SCXI_TOKEN_FILE,FILE_READ|FILE_BIN);
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
   scxi_token=CharArrayToString(bytes,0,(int)size,CP_UTF8);
   ArrayInitialize(bytes,0);
   return ScTokenValid(scxi_token);
  }

bool ScxiAppend(string &fingerprint,const string kind,const ulong ticket,
                 const string symbol,const long magic)
  {
   if(ticket==0 || StringLen(symbol)<1 || StringLen(symbol)>64 ||
      StringLen(fingerprint)>4096) return false;
   fingerprint+=kind+":"+StringFormat("%I64u",ticket)+":"+
      IntegerToString(magic)+":"+symbol+"|";
   return StringLen(fingerprint)<=8192;
  }

bool ScxiReadCurrent(ScxiScan &scan)
  {
   ZeroMemory(scan);
   int orders=OrdersTotal(),positions=PositionsTotal();
   if(orders<0 || positions<0 || orders+positions>SCXI_MAX_CURRENT_ITEMS) return false;
   scan.fingerprint="orders:"+IntegerToString(orders)+"|positions:"+
      IntegerToString(positions)+"|";
   for(int i=0;i<orders;i++)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) return false;
      string symbol=OrderGetString(ORDER_SYMBOL);
      long magic=OrderGetInteger(ORDER_MAGIC);
      if(!ScxiAppend(scan.fingerprint,"order",ticket,symbol,magic)) return false;
      if(symbol==ExpectedSymbol && magic==ExpectedMagicNumber) scan.owned_orders++;
      else scan.foreign_orders++;
     }
   for(int i=0;i<positions;i++)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) return false;
      string symbol=PositionGetString(POSITION_SYMBOL);
      long magic=PositionGetInteger(POSITION_MAGIC);
      if(!ScxiAppend(scan.fingerprint,"position",ticket,symbol,magic)) return false;
      if(symbol==ExpectedSymbol && magic==ExpectedMagicNumber) scan.owned_positions++;
      else scan.foreign_positions++;
     }
   return scan.foreign_orders+scan.owned_orders==orders &&
      scan.foreign_positions+scan.owned_positions==positions;
  }

bool ScxiReadSample(ScxInventorySample &sample)
  {
   if(!ScxiIdentityMatches()) return false;
   ScxiScan before,after;
   if(!ScxiReadCurrent(before) || !ScxiReadCurrent(after) ||
      before.fingerprint!=after.fingerprint ||
      before.foreign_orders!=after.foreign_orders ||
      before.foreign_positions!=after.foreign_positions ||
      before.owned_orders!=after.owned_orders ||
      before.owned_positions!=after.owned_positions) return false;
   long build,allowed;
   double equity;
   ResetLastError(); build=TerminalInfoInteger(TERMINAL_BUILD);
   if(GetLastError()!=0 || build<1 ||
      !ScxiAccountInteger(ACCOUNT_TRADE_ALLOWED,allowed) ||
      !ScxiAccountDouble(ACCOUNT_EQUITY,equity) || equity<=0) return false;
   sample.executor_id=ExecutorId;
   sample.account_ref=IntegerToString(ExpectedLogin);
   sample.server=ExpectedServer;
   sample.currency=ExpectedCurrency;
   sample.margin_mode=ScxiMarginMode(ExpectedMarginMode);
   sample.symbol=ExpectedSymbol;
   sample.generation=scxi_generation;
   sample.observed_at=ScUtc(TimeGMT());
   sample.terminal_build=build;
   sample.magic_number=ExpectedMagicNumber;
   sample.foreign_orders=after.foreign_orders;
   sample.foreign_positions=after.foreign_positions;
   sample.terminal_connected=true;
   sample.account_trade_allowed=(bool)allowed;
   sample.algo_trading_allowed=false; // Policy observation only; never executor admission.
   sample.complete=(after.owned_orders==0 && after.owned_positions==0);
   sample.equity=equity;
   return sample.observed_at!="" && ScxiIdentityMatches();
  }

int ScxiRequest(const string method,const string path,const string body,string &response)
  {
   response="";
   if(scxi_latched || !ScxiIdentityMatches()) return -1;
   if(scxi_requests_this_timer>=1)
     { scxi_latched=true; ScxiState("REQUEST_BUDGET_EXCEEDED_REINITIALIZE"); return -1; }
   char data[],result[];
   if(body!="")
     {
      int copied=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);
      if(copied<1 || copied-1>262144) return -1;
      ArrayResize(data,copied-1);
     }
   string headers="Authorization: Bearer "+scxi_token+
      "\r\nContent-Type: application/json\r\n";
   string result_headers;
   ulong started=GetTickCount64();
   scxi_requests_this_timer++;
   int status=WebRequest(method,SCXI_API+path,headers,SCXI_TIMEOUT_MS,
                         data,result,result_headers);
   headers="";
   if(GetTickCount64()-started>1000)
     {
      scxi_latched=true;
      ScxiState("TRANSPORT_DEADLINE_EXCEEDED_REINITIALIZE");
      return -1;
     }
   if(ArraySize(result)>2048) return -1;
   response=CharArrayToString(result,0,ArraySize(result),CP_UTF8);
   return status;
  }

void ScxiReconnectLater()
  {
   scxi_boot=""; scxi_sequence=0;
   scxi_retry_after=GetTickCount64()+10000;
  }

int OnInit()
  {
   if(!EnableReadOnlyExecutionInventory)
     { ScxiState("DISABLED"); return INIT_SUCCEEDED; }
   if(!ScxiConfigurationValid())
     { ScxiState("INVALID_CONFIGURATION"); return INIT_FAILED; }
   if(!ScxiIdentityMatches())
     { ScxiState("DEMO_IDENTITY_MISMATCH"); return INIT_FAILED; }
   if(!ScxiLoadToken())
     { ScxiState("PRIVATE_TOKEN_UNAVAILABLE"); return INIT_FAILED; }
   scxi_generation=StringFormat("observer-%I64d-%I64u",(long)TimeGMT(),GetMicrosecondCount());
   if(!ScxSafeIdentifier(scxi_generation,128) || !EventSetTimer(1))
     { scxi_token=""; ScxiState("INITIALIZATION_FAILED"); return INIT_FAILED; }
   ScxiState("READ_ONLY_INVENTORY_STARTING");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   scxi_token=""; scxi_boot=""; scxi_generation=""; scxi_sequence=0;
  }

void OnTimer()
  {
   scxi_requests_this_timer=0;
   if(!EnableReadOnlyExecutionInventory || scxi_latched) return;
   if(!TerminalInfoInteger(TERMINAL_CONNECTED))
     { ScxiReconnectLater(); ScxiState("DISCONNECTED"); return; }
   if(!ScxiIdentityMatches())
     { scxi_latched=true; ScxiState("IDENTITY_CHANGED_REINITIALIZE"); return; }
   if(GetTickCount64()<scxi_retry_after) return;
   string response;
   if(scxi_boot=="")
     {
      int status=ScxiRequest("GET","/challenge","",response);
      if(scxi_latched) return;
      if(status!=200 || !ScxChallenge(response,scxi_boot,scxi_sequence))
        { ScxiReconnectLater(); ScxiState("CHALLENGE_UNAVAILABLE"); }
      else ScxiState("READ_ONLY_INVENTORY_SCANNING");
      return;
     }
   ScxInventorySample sample;
   string packet;
   if(!ScxiReadSample(sample) || !ScxInventoryJson(sample,scxi_boot,scxi_sequence,packet))
     { ScxiState("INVENTORY_UNAVAILABLE"); return; }
   int status=ScxiRequest("POST","/inventory",packet,response);
   if(scxi_latched) return;
   if(status!=200 || !ScReceipt(response,scxi_sequence))
     {
      if(status==409 && ScErrorIs(response,"BOOT_MISMATCH"))
        { ScxiReconnectLater(); ScxiState("API_RESTART_RECONNECTING"); return; }
      if(status>=400 && status<500 && status!=408 && status!=429)
        { scxi_latched=true; ScxiState("INVENTORY_REJECTED_REINITIALIZE"); return; }
      ScxiReconnectLater(); ScxiState("INVENTORY_UNCONFIRMED"); return;
     }
   if(scxi_sequence==SC_MAX_SEQUENCE)
     { scxi_latched=true; ScxiState("SEQUENCE_EXHAUSTED_REINITIALIZE_API"); return; }
   scxi_sequence++;
   ScxiState(sample.complete ? "EMPTY_INVENTORY_CONFIRMED_POLICY_ONLY" :
      "OWNED_EFFECT_REQUIRES_FULL_EXECUTOR");
  }
