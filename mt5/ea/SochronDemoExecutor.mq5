#property strict
#property version "0.10"
#property description "Sochron1k default-off single-account MT5 Demo executor"

#include "ExecutionRuntime.mqh"

input bool EnableDemoExecution=false;
input long ExpectedLogin=0;
input string ExpectedServer="";
input string ExpectedCurrency="";
input string ExpectedSymbol="";
input string ExecutorId="";
input int ExpectedMarginMode=-1;
input long ExpectedMagicNumber=0;
input int MaxSpreadPoints=0;
input int MaxDeviationPoints=0;
input int MaxQuoteAgeSeconds=5;

const string SCXE_API="http://127.0.0.1:8000/executor/v1";
const string SCXE_TOKEN_FILE="sochron-execution.token";
const string SCXE_LOCK_FILE="sochron-execution.lock";
const string SCXE_LEDGER_FILE="sochron-execution-ledger.v1";
const int SCXE_TIMEOUT_MS=500;

string scxe_token="",scxe_boot="",scxe_generation="",scxe_state="";
long scxe_inventory_sequence=0;
ulong scxe_retry_after=0;
bool scxe_latched=false,scxe_inventory_turn=true,scxe_inventory_admitted=false;
bool scxe_reconcile_needed=true;
ulong scxe_reconcile_deadline=0;
int scxe_requests_this_timer=0,scxe_lock_handle=INVALID_HANDLE;
int scxe_ledger_handle=INVALID_HANDLE;
ScxeLedgerBook scxe_book;

void ScxeState(const string state)
  {
   if(state==scxe_state) return;
   scxe_state=state;
   Print("Sochron Demo executor: ",state);
  }

void ScxeLatch(const string state)
  {
   scxe_latched=true;
   ScxeState(state);
  }

bool ScxeLoadToken()
  {
   int handle=FileOpen(SCXE_TOKEN_FILE,FILE_READ|FILE_BIN);
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
   scxe_token=CharArrayToString(bytes,0,(int)size,CP_UTF8);
   ArrayInitialize(bytes,0);
   return ScTokenValid(scxe_token);
  }

bool ScxeOpenPrivateState()
  {
   // No FILE_SHARE flags: the selected MT5 build must prove the second EA is denied.
   scxe_lock_handle=FileOpen(SCXE_LOCK_FILE,FILE_READ|FILE_WRITE|FILE_BIN);
   if(scxe_lock_handle==INVALID_HANDLE) return false;
   // ASCII-only records plus FILE_ANSI keep one character equal to one byte.
   scxe_ledger_handle=FileOpen(SCXE_LEDGER_FILE,
      FILE_READ|FILE_WRITE|FILE_BIN|FILE_ANSI);
   if(scxe_ledger_handle==INVALID_HANDLE)
     { FileClose(scxe_lock_handle); scxe_lock_handle=INVALID_HANDLE; return false; }
   if(!ScxeLedgerLoad(scxe_ledger_handle,scxe_book))
     {
      FileClose(scxe_ledger_handle); FileClose(scxe_lock_handle);
      scxe_ledger_handle=INVALID_HANDLE; scxe_lock_handle=INVALID_HANDLE;
      return false;
     }
   return true;
  }

bool ScxePendingRecord(ScxeLedgerRecord &record)
  {
   ZeroMemory(record);
   if(scxe_book.has_management && ScxeUnresolvedStage(scxe_book.management.stage))
     {
      record=scxe_book.management;
      return true;
     }
   if(scxe_book.has_entry && ScxeUnresolvedStage(scxe_book.entry.stage))
     {
      record=scxe_book.entry;
      return true;
     }
   return false;
  }

bool ScxeAppendRecord(const ScxeLedgerRecord &record,const string stage,
                      const string outcome_json)
  {
   return ScxeLedgerAppend(scxe_ledger_handle,scxe_book,stage,record.observed_at,
      record.history_from,record.command_json,record.send_attempted,
      record.has_retcode,record.retcode,
      record.retcode_external,record.has_request_id,record.request_id,
      record.order_ticket,record.deal_ticket,outcome_json);
  }

int ScxeRequest(const string method,const string path,const string body,string &response)
  {
   response="";
   if(scxe_latched || !ScxeIdentityMatches(ExpectedLogin,ExpectedServer,
      ExpectedCurrency,ExpectedSymbol,ExpectedMarginMode)) return -1;
   if(scxe_requests_this_timer>=1)
     { ScxeLatch("REQUEST_BUDGET_EXCEEDED_REINITIALIZE"); return -1; }
   char data[],result[];
   if(body!="")
     {
      int copied=StringToCharArray(body,data,0,WHOLE_ARRAY,CP_UTF8);
      if(copied<1 || copied-1>262144) return -1;
      ArrayResize(data,copied-1);
     }
   string headers="Authorization: Bearer "+scxe_token+
      "\r\nContent-Type: application/json\r\n";
   string result_headers;
   ulong started=GetTickCount64();
   scxe_requests_this_timer++;
   int status=WebRequest(method,SCXE_API+path,headers,SCXE_TIMEOUT_MS,
                         data,result,result_headers);
   headers="";
   if(GetTickCount64()-started>1000)
     { ScxeLatch("TRANSPORT_DEADLINE_EXCEEDED_REINITIALIZE"); return -1; }
   if(ArraySize(result)>SCX_MAX_COMMAND_BYTES) return -1;
   response=CharArrayToString(result,0,ArraySize(result),CP_UTF8);
   return status;
  }

void ScxeReconnectLater()
  {
   scxe_boot=""; scxe_inventory_sequence=0;
   scxe_inventory_admitted=false;
   scxe_retry_after=GetTickCount64()+10000;
  }

bool ScxeBuildSample(ScxInventorySample &sample,ScxeCurrentScan &scan)
  {
   if(!ScxeIdentityMatches(ExpectedLogin,ExpectedServer,ExpectedCurrency,
      ExpectedSymbol,ExpectedMarginMode) ||
      !ScxeStableCurrent(ExpectedSymbol,ExpectedMagicNumber,scan)) return false;
   long build,account_allowed;
   double equity;
   ResetLastError(); build=TerminalInfoInteger(TERMINAL_BUILD);
   if(GetLastError()!=0 || build<1 ||
      !ScxeAccountInteger(ACCOUNT_TRADE_ALLOWED,account_allowed) ||
      !ScxeAccountDouble(ACCOUNT_EQUITY,equity) || equity<=0) return false;
   sample.executor_id=ExecutorId;
   sample.account_ref=IntegerToString(ExpectedLogin);
   sample.server=ExpectedServer; sample.currency=ExpectedCurrency;
   sample.margin_mode=ScxeMarginMode(ExpectedMarginMode);
   sample.symbol=ExpectedSymbol; sample.generation=scxe_generation;
   sample.observed_at=ScUtc(TimeGMT()); sample.terminal_build=build;
   sample.magic_number=ExpectedMagicNumber;
   sample.foreign_orders=scan.foreign_orders;
   sample.foreign_positions=scan.foreign_positions;
   sample.terminal_connected=true;
   sample.account_trade_allowed=(bool)account_allowed;
   sample.algo_trading_allowed=ScxeTradingAllowed();
   sample.complete=false; sample.equity=equity;
   return sample.observed_at!="" &&
      ScxeIdentityMatches(ExpectedLogin,ExpectedServer,ExpectedCurrency,
                          ExpectedSymbol,ExpectedMarginMode);
  }

bool ScxeBuildInventory(string &packet,bool &recovers_pending,bool &complete)
  {
   packet=""; recovers_pending=false; complete=false;
   ScxInventorySample sample;
   ScxeCurrentScan scan;
   if(!ScxeBuildSample(sample,scan)) return false;
   ScxBrokerEvidence entry;
   ScxManagementEvidence management;
   ScxRejectionEvidence rejection;
   bool has_entry=false,has_management=false,has_rejection=false;
   complete=(scan.foreign_orders==0 && scan.foreign_positions==0);
   if(scxe_book.has_entry)
     {
      if(ScxeBuildRejectionEvidence(scxe_book.entry,ExpectedSymbol,
                                    ExpectedMagicNumber,rejection))
         has_rejection=true;
      else if(ScxeBuildEntryEvidence(scxe_book.entry,ExpectedSymbol,
                                     ExpectedMagicNumber,scan,entry)) has_entry=true;
      else complete=false;
     }
   else if(scan.owned_orders>0 || scan.owned_positions>0) complete=false;
   if(scxe_book.has_management)
     {
      ScxRejectionEvidence management_rejection;
      if(has_entry && ScxeBuildManagementEvidence(scxe_book.management,entry,
         ExpectedSymbol,ExpectedMagicNumber,management)) has_management=true;
      else if(has_entry && ScxeBuildRejectionEvidence(scxe_book.management,
         ExpectedSymbol,ExpectedMagicNumber,management_rejection))
        {
         if(has_rejection) complete=false;
         else { rejection=management_rejection; has_rejection=true; }
        }
      else complete=false;
     }
   sample.complete=complete;
   if(!ScxInventoryEvidenceJson(sample,scxe_boot,scxe_inventory_sequence,
      has_entry,entry,has_management,management,has_rejection,rejection,packet))
      return false;
   ScxeLedgerRecord pending;
   if(ScxePendingRecord(pending) && pending.command.boot_id!=scxe_boot && complete)
     {
      if(pending.command.operation=="open")
         recovers_pending=(has_entry ||
            (has_rejection && rejection.command_id==pending.command.command_id));
      else recovers_pending=(has_management ||
         (has_rejection && rejection.command_id==pending.command.command_id));
     }
   return true;
  }

bool ScxeUploadInventory()
  {
   string packet,response;
   bool recovers_pending=false,complete=false;
   scxe_inventory_admitted=false;
   if(!ScxeBuildInventory(packet,recovers_pending,complete))
     { ScxeState("INVENTORY_RECONCILIATION_INCOMPLETE"); return false; }
   int status=ScxeRequest("POST","/inventory",packet,response);
   if(scxe_latched) return false;
   if(status!=200 || !ScReceipt(response,scxe_inventory_sequence))
     {
      if(status==409 && ScErrorIs(response,"BOOT_MISMATCH"))
        { ScxeReconnectLater(); ScxeState("API_RESTART_RECONNECTING"); return false; }
      if(status>=400 && status<500 && status!=408 && status!=429)
        { ScxeLatch("INVENTORY_REJECTED_REINITIALIZE"); return false; }
      ScxeReconnectLater();
      ScxeState("INVENTORY_UNCONFIRMED_RECHALLENGE_PENDING");
      return false;
     }
   if(recovers_pending)
     {
      ScxeLedgerRecord pending;
      if(!ScxePendingRecord(pending) ||
         !ScxeAppendRecord(pending,"RECOVERED_INVENTORY",""))
        { ScxeLatch("LEDGER_RECOVERY_COMMIT_FAILED"); return false; }
     }
   if(scxe_inventory_sequence==SC_MAX_SEQUENCE)
     { ScxeLatch("SEQUENCE_EXHAUSTED_REINITIALIZE_API"); return false; }
   scxe_inventory_sequence++;
   scxe_inventory_admitted=complete;
   if(complete) ScxeState("INVENTORY_CONFIRMED");
   else
     {
      scxe_retry_after=GetTickCount64()+2000;
      ScxeState("INVENTORY_INCOMPLETE_COMMAND_POLL_QUARANTINED");
     }
   return true;
  }

bool ScxeOutcomeFor(const ScxeLedgerRecord &record,string &outcome)
  {
   outcome="";
   ScxeCurrentScan scan;
   if(!ScxeStableCurrent(ExpectedSymbol,ExpectedMagicNumber,scan)) return false;
   if(record.command.operation=="open")
     {
      ScxRejectionEvidence rejection;
      if(ScxeBuildRejectionEvidence(record,ExpectedSymbol,ExpectedMagicNumber,rejection))
         return ScxRejectionJson(record.command,rejection.observed_at,rejection.retcode,
            rejection.retcode_external,rejection.request_id,outcome);
      ScxBrokerEvidence entry;
      if(ScxeBuildEntryEvidence(record,ExpectedSymbol,ExpectedMagicNumber,scan,entry))
         return ScxEntrySnapshotOutcomeJson(record.command,ScUtc(TimeGMT()),entry,outcome);
     }
   else if(scxe_book.has_entry)
     {
      ScxBrokerEvidence target;
      ScxManagementEvidence management;
      if(ScxeBuildEntryEvidence(scxe_book.entry,ExpectedSymbol,ExpectedMagicNumber,
         scan,target) && ScxeBuildManagementEvidence(record,target,ExpectedSymbol,
         ExpectedMagicNumber,management))
         return ScxManagementSnapshotOutcomeJson(record.command,
            management.observed_at,management,outcome);
     }
   ScxRejectionEvidence rejection;
   if(ScxeBuildRejectionEvidence(record,ExpectedSymbol,ExpectedMagicNumber,rejection))
      return ScxRejectionJson(record.command,rejection.observed_at,rejection.retcode,
         rejection.retcode_external,rejection.request_id,outcome);
   return ScxUncertainJson(record.command,ScUtc(TimeGMT()),record.has_retcode,
      record.retcode,record.retcode_external,record.has_request_id,
      record.request_id,outcome);
  }

bool ScxePrepareOutcome()
  {
   ScxeLedgerRecord pending;
   if(!ScxePendingRecord(pending)) return false;
   if(pending.stage=="OUTCOME_READY") return true;
   string outcome;
   if(!ScxeOutcomeFor(pending,outcome) ||
      !ScxeAppendRecord(pending,"OUTCOME_READY",outcome))
     { ScxeLatch("OUTCOME_JOURNAL_FAILED"); return false; }
   scxe_reconcile_needed=false;
   scxe_reconcile_deadline=0;
   ScxeState("OUTCOME_DURABLE");
   return true;
  }

bool ScxePostOutcome()
  {
   ScxeLedgerRecord pending;
   if(!ScxePendingRecord(pending) || pending.stage!="OUTCOME_READY" ||
      pending.outcome_json=="") return false;
   string response;
   int status=ScxeRequest("POST","/outcomes",pending.outcome_json,response);
   if(scxe_latched) return false;
   if(status==200 && ScReceipt(response,pending.command.dispatch_sequence))
     {
      if(!ScxeAppendRecord(pending,"OUTCOME_ACKED",pending.outcome_json))
        { ScxeLatch("OUTCOME_ACK_JOURNAL_FAILED"); return false; }
      scxe_inventory_turn=true;
      scxe_inventory_admitted=false;
      ScxeState("OUTCOME_CONFIRMED");
      return true;
     }
   if(status==409 && ScErrorIs(response,"BOOT_MISMATCH"))
     { ScxeReconnectLater(); ScxeState("API_RESTART_RECONNECTING"); return false; }
   if(status>=400 && status<500 && status!=408 && status!=429)
     { ScxeLatch("OUTCOME_REJECTED_REINITIALIZE"); return false; }
   scxe_retry_after=GetTickCount64()+2000;
   ScxeState("OUTCOME_UNCONFIRMED_REPLAY_PENDING");
   return false;
  }

bool ScxeJournalPrepared(const string command_json)
  {
   long history_from=(long)TimeTradeServer();
   return history_from>0 &&
      ScxeLedgerAppend(scxe_ledger_handle,scxe_book,"PREPARED",ScUtc(TimeGMT()),
         history_from,command_json,false,false,0,0,false,0,"","","");
  }

bool ScxeJournalDenied(const ScxeLedgerRecord &record,const long retcode,
                       const long external,const long request_id)
  {
   string outcome;
   bool confirmed=ScxNoEffectRetcode(retcode);
   if(confirmed)
      confirmed=ScxeNoEffectSince(ExpectedSymbol,ExpectedMagicNumber,
         record.command.operation,(datetime)record.history_from);
   if(confirmed)
      confirmed=ScxRejectionJson(record.command,ScUtc(TimeGMT()),retcode,external,
                                 request_id,outcome);
   if(!confirmed && !ScxUncertainJson(record.command,ScUtc(TimeGMT()),retcode>0,
      retcode,external,request_id>0,request_id,outcome)) return false;
   return ScxeLedgerAppend(scxe_ledger_handle,scxe_book,"OUTCOME_READY",record.observed_at,
      record.history_from,record.command_json,false,retcode>0,retcode,external,
      request_id>0,request_id,
      "","",outcome);
  }

bool ScxeProcessCommand(const string command_json)
  {
   ScxCommand command;
   if(!ScxeAsciiLine(command_json,SCX_MAX_COMMAND_BYTES) ||
      !ScxCommandJson(command_json,command) ||
      !ScxCommandBinding(command,scxe_boot,scxe_generation,ExpectedMagicNumber,
                         IntegerToString(ExpectedLogin),ExpectedSymbol) ||
      command.expires_at<=TimeGMT())
     { ScxeLatch("COMMAND_BINDING_REJECTED_REINITIALIZE"); return false; }
   ScxeLedgerRecord unresolved;
   if(ScxePendingRecord(unresolved))
     {
      if(ScxeSameCommand(unresolved.command,command)) return true;
      ScxeLatch("COMMAND_CONFLICT_REINITIALIZE"); return false;
     }
   if(command.operation=="open")
     {
      ScxeCurrentScan before_prepare;
      if(!ScxeStableCurrent(ExpectedSymbol,ExpectedMagicNumber,before_prepare) ||
         before_prepare.foreign_orders!=0 || before_prepare.foreign_positions!=0 ||
         before_prepare.owned_orders!=0 || before_prepare.owned_positions!=0)
        { ScxeLatch("ENTRY_EXPOSURE_CONFLICT_REINITIALIZE"); return false; }
     }
   if(!ScxeJournalPrepared(command_json))
     { ScxeLatch("COMMAND_PREPARE_JOURNAL_FAILED"); return false; }
   ScxeLedgerRecord prepared;
   if(!ScxePendingRecord(prepared) ||
      !ScxeSameCommand(prepared.command,command))
     { ScxeLatch("PREPARED_COMMAND_UNAVAILABLE"); return false; }
   MqlTradeRequest request;
   bool ready=false;
   if(command.operation=="open")
     {
      ScxeContract contract;
      MqlTick tick;
      double loss,margin;
      ready=ScxePreflightOpen(command,ExpectedSymbol,MaxSpreadPoints,
         MaxDeviationPoints,MaxQuoteAgeSeconds,contract,tick,request,loss,margin);
     }
   else if(command.operation=="cancel")
      ready=ScxePreflightCancel(command,ExpectedSymbol,ExpectedMagicNumber,request);
   else ready=ScxePreflightClose(command,ExpectedSymbol,ExpectedMagicNumber,
      MaxDeviationPoints,MaxQuoteAgeSeconds,request);
   if(!ready)
     {
      if(!ScxeJournalDenied(prepared,0,0,0))
         ScxeLatch("PREFLIGHT_DENIAL_JOURNAL_FAILED");
      else ScxeState("PREFLIGHT_DENIED_NO_BROKER_WRITE");
      return false;
     }
   MqlTradeCheckResult checked;
   ZeroMemory(checked); ResetLastError();
   bool check_ok=OrderCheck(request,checked);
   if(!check_ok || checked.retcode!=0)
     {
      if(!ScxeJournalDenied(prepared,(long)checked.retcode,0,0))
         ScxeLatch("ORDER_CHECK_DENIAL_JOURNAL_FAILED");
      else ScxeState("ORDER_CHECK_DENIED_NO_BROKER_WRITE");
      return false;
     }
   if(!ScxeLedgerAppend(scxe_ledger_handle,scxe_book,"SEND_STARTED",prepared.observed_at,
      prepared.history_from,command_json,true,false,0,0,false,0,"","",""))
     { ScxeLatch("SEND_INTENT_JOURNAL_FAILED"); return false; }
   if(!ScxeIdentityMatches(ExpectedLogin,ExpectedServer,ExpectedCurrency,
      ExpectedSymbol,ExpectedMarginMode) || !ScxeTradingAllowed() ||
      command.expires_at<=TimeGMT())
     { ScxeState("MUTATION_FENCE_CHANGED_RECONCILIATION_REQUIRED"); return false; }
   MqlTradeResult result;
   ZeroMemory(result); ResetLastError();
   scxe_reconcile_needed=false;
   scxe_reconcile_deadline=GetTickCount64()+2000;
   bool sent=OrderSend(request,result);
   string order_ticket="",deal_ticket="";
   if(result.order>0 && !ScxeTicketText(result.order,order_ticket))
     { ScxeLatch("UNSUPPORTED_ORDER_IDENTIFIER"); return false; }
   if(result.deal>0 && !ScxeTicketText(result.deal,deal_ticket))
     { ScxeLatch("UNSUPPORTED_DEAL_IDENTIFIER"); return false; }
   if(!ScxeLedgerAppend(scxe_ledger_handle,scxe_book,"SEND_RETURN",prepared.observed_at,
      prepared.history_from,command_json,true,true,(long)result.retcode,
      (long)result.retcode_external,
      result.request_id>0,(long)result.request_id,order_ticket,deal_ticket,""))
     { ScxeLatch("SEND_RETURN_JOURNAL_FAILED_RECONCILE_EXTERNALLY"); return false; }
   if(!sent) scxe_reconcile_needed=true;
   ScxeState(sent ? "BROKER_WRITE_RECONCILIATION_REQUIRED" :
                    "BROKER_WRITE_UNCONFIRMED_RECONCILIATION_REQUIRED");
   return true;
  }

bool ScxePollCommand()
  {
   string response;
   int status=ScxeRequest("GET","/commands/next","",response);
   if(scxe_latched) return false;
   if(status==204) { ScxeState("READY_NO_COMMAND"); return true; }
   if(status!=200)
     {
      if(status==409 && ScErrorIs(response,"BOOT_MISMATCH"))
        { ScxeReconnectLater(); ScxeState("API_RESTART_RECONNECTING"); }
      else if(status>=400 && status<500 && status!=408 && status!=429)
         ScxeLatch("COMMAND_CHANNEL_REJECTED_REINITIALIZE");
      else ScxeState("COMMAND_CHANNEL_UNAVAILABLE");
      return false;
     }
   return ScxeProcessCommand(response);
  }

int OnInit()
  {
   if(!EnableDemoExecution)
     { ScxeState("DISABLED"); return INIT_SUCCEEDED; }
   if(!ScxeConfigurationValid(ExpectedLogin,ExpectedServer,ExpectedCurrency,
      ExpectedSymbol,ExecutorId,ExpectedMarginMode,ExpectedMagicNumber,
      MaxSpreadPoints,MaxDeviationPoints,MaxQuoteAgeSeconds))
     { ScxeState("INVALID_CONFIGURATION"); return INIT_FAILED; }
   if(!ScxeIdentityMatches(ExpectedLogin,ExpectedServer,ExpectedCurrency,
      ExpectedSymbol,ExpectedMarginMode))
     { ScxeState("DEMO_IDENTITY_MISMATCH"); return INIT_FAILED; }
   if(!ScxeOpenPrivateState())
     { ScxeState("EXECUTOR_LOCK_OR_LEDGER_UNAVAILABLE"); return INIT_FAILED; }
   if(!ScxeLoadToken())
     { ScxeState("PRIVATE_TOKEN_UNAVAILABLE"); return INIT_FAILED; }
   if(scxe_book.has_entry) scxe_generation=scxe_book.entry.command.generation;
   else scxe_generation=StringFormat("executor-%I64d-%I64u",(long)TimeGMT(),
                                     GetMicrosecondCount());
   if(!ScxSafeIdentifier(scxe_generation,128) || !EventSetTimer(1))
     { ScxeState("INITIALIZATION_FAILED"); return INIT_FAILED; }
   ScxeState("STARTUP_RECONCILIATION_REQUIRED");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   if(!EnableDemoExecution) return;
   EventKillTimer();
   if(scxe_ledger_handle!=INVALID_HANDLE)
     { FileFlush(scxe_ledger_handle); FileClose(scxe_ledger_handle); }
   if(scxe_lock_handle!=INVALID_HANDLE) FileClose(scxe_lock_handle);
   scxe_ledger_handle=INVALID_HANDLE; scxe_lock_handle=INVALID_HANDLE;
   scxe_token=""; scxe_boot=""; scxe_generation="";
  }

void OnTradeTransaction(const MqlTradeTransaction &trans,
                        const MqlTradeRequest &request,
                        const MqlTradeResult &result)
  {
   scxe_reconcile_needed=true;
  }

void OnTimer()
  {
   scxe_requests_this_timer=0;
   if(!EnableDemoExecution || scxe_latched) return;
   if(!ScxeIdentityMatches(ExpectedLogin,ExpectedServer,ExpectedCurrency,
      ExpectedSymbol,ExpectedMarginMode))
     { ScxeLatch("IDENTITY_CHANGED_REINITIALIZE"); return; }
   if(GetTickCount64()<scxe_retry_after) return;
   string response;
   if(scxe_boot=="")
     {
      int status=ScxeRequest("GET","/challenge","",response);
      if(scxe_latched) return;
      if(status==200 && !ScxChallenge(response,scxe_boot,scxe_inventory_sequence))
        { ScxeLatch("CHALLENGE_INVALID_REINITIALIZE"); return; }
      if(status>=400 && status<500 && status!=408 && status!=429)
        { ScxeLatch("CHALLENGE_REJECTED_REINITIALIZE"); return; }
      if(status!=200)
        { ScxeReconnectLater(); ScxeState("CHALLENGE_UNAVAILABLE"); }
      else ScxeState("STARTUP_INVENTORY_REQUIRED");
      return;
     }
   ScxeLedgerRecord pending;
   if(ScxePendingRecord(pending))
     {
      if(pending.command.boot_id!=scxe_boot)
        { ScxeUploadInventory(); return; }
      if(pending.stage!="OUTCOME_READY")
        {
         if(!scxe_reconcile_needed && scxe_reconcile_deadline>GetTickCount64())
           { ScxeState("WAITING_FOR_BROKER_RECONCILIATION"); return; }
         scxe_reconcile_needed=true;
         ScxePrepareOutcome();
         return;
        }
      ScxePostOutcome();
      return;
     }
   if(scxe_inventory_turn)
     {
      if(ScxeUploadInventory()) scxe_inventory_turn=false;
      return;
     }
   if(!scxe_inventory_admitted)
     {
      scxe_inventory_turn=true;
      ScxeState("INVENTORY_NOT_ADMITTED_NO_COMMAND_POLL");
      return;
     }
   if(!ScxeTradingAllowed())
     {
      scxe_inventory_turn=true;
      ScxeState("TRADING_PERMISSION_UNAVAILABLE_NO_COMMAND_POLL");
      return;
     }
   scxe_inventory_turn=true;
   ScxePollCommand();
  }
