#property strict
#property script_show_inputs
#property description "Pure SCN-013 execution protocol tests; no terminal, account or network access"

#include "ExecutionProtocol.mqh"

int scx_failures=0,scx_checks=0;
void ScxCheck(const bool condition,const string name)
  {
   scx_checks++;
   if(!condition) { scx_failures++; Print("FAIL execution protocol case: ",name); }
  }

string ScxChanged(const string source,const string before,const string after)
  {
   string result=source;
   if(StringReplace(result,before,after)!=1) return "";
   return result;
  }

string ScxOpenCommandFixture()
  {
   return "{\"protocol\":\"sochron.execution.command.v1\","+
      "\"boot_id\":\"11111111-2222-4333-8444-555555555555\","+
      "\"dispatch_sequence\":7,\"attempt_id\":\"synthetic-attempt-1\","+
      "\"generation\":\"synthetic-generation-1\",\"magic_number\":910001,"+
      "\"command_id\":\"synthetic-command-1\",\"target_command_id\":null,"+
      "\"fingerprint\":\"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\","+
      "\"account_ref\":\"123456789\",\"experiment_id\":\"synthetic-experiment\","+
      "\"symbol\":\"XAUUSD.fixture\",\"operation\":\"open\",\"volume\":\"0.10\","+
      "\"risk_limit\":\"100.00\",\"cost_budget\":\"1.00\","+
      "\"expires_at\":\"2026-09-20T00:00:30Z\",\"side\":\"buy\","+
      "\"requested_entry\":\"2500.20\",\"stop_loss\":\"2495.20\","+
      "\"take_profit\":\"2510.20\",\"broker_order_ticket\":null,"+
      "\"position_id\":null,\"reason\":null}";
  }

string ScxCloseCommandFixture()
  {
   return "{\"protocol\":\"sochron.execution.command.v1\","+
      "\"boot_id\":\"11111111-2222-4333-8444-555555555555\","+
      "\"dispatch_sequence\":8,\"attempt_id\":\"synthetic-attempt-2\","+
      "\"generation\":\"synthetic-generation-1\",\"magic_number\":910001,"+
      "\"command_id\":\"synthetic-close-1\","+
      "\"target_command_id\":\"synthetic-command-1\","+
      "\"fingerprint\":\"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb\","+
      "\"account_ref\":\"123456789\",\"experiment_id\":\"synthetic-experiment\","+
      "\"symbol\":\"XAUUSD.fixture\",\"operation\":\"close\",\"volume\":\"0.10\","+
      "\"risk_limit\":null,\"cost_budget\":null,"+
      "\"expires_at\":\"2026-09-20T00:01:00.123456Z\",\"side\":null,"+
      "\"requested_entry\":null,\"stop_loss\":null,\"take_profit\":null,"+
      "\"broker_order_ticket\":\"7001\",\"position_id\":\"8001\","+
      "\"reason\":\"owner_request\"}";
  }

void ScxEntryEvidenceFixture(ScxBrokerEvidence &entry,const bool closed)
  {
   ZeroMemory(entry);
   entry.command_id="synthetic-command-1";
   entry.order_ticket="7001";
   entry.position_id="8001";
   entry.has_position_id=true;
   entry.requested_volume=0.10;
   entry.filled_volume=0.10;
   entry.remaining_volume=0;
   entry.cancelled_volume=0;
   entry.closed_volume=closed ? 0.10 : 0;
   entry.stop_loss_confirmed=!closed;
   entry.has_terminal_state=closed;
   entry.terminal_state=closed ? "closed" : "";
   ArrayResize(entry.deals,1);
   entry.deals[0].deal_ticket="7101";
   entry.deals[0].volume=0.10;
   entry.deals[0].price=2500.20;
   entry.deals[0].profit=0;
   entry.deals[0].commission=-0.25;
   entry.deals[0].swap=0;
   entry.deals[0].fee=0;
   entry.deals[0].occurred_at="2026-09-20T00:00:01Z";
   entry.deals[0].has_occurred_at=true;
  }

void ScxManagementEvidenceFixture(ScxManagementEvidence &management)
  {
   ZeroMemory(management);
   management.command_id="synthetic-close-1";
   management.target_command_id="synthetic-command-1";
   management.operation="close";
   management.broker_order_ticket="7001";
   management.position_id="8001";
   management.has_position_id=true;
   management.requested_volume=0.10;
   management.completed_volume=0.10;
   management.remaining_volume=0;
   management.terminal_state="closed";
   management.has_terminal_state=true;
   management.observed_at="2026-09-20T00:01:01Z";
   ArrayResize(management.deals,1);
   management.deals[0].deal_ticket="7201";
   management.deals[0].volume=0.10;
   management.deals[0].price=2501.20;
   management.deals[0].profit=10;
   management.deals[0].commission=-0.25;
   management.deals[0].swap=0;
   management.deals[0].fee=0;
   management.deals[0].occurred_at=management.observed_at;
   management.deals[0].has_occurred_at=true;
   ScxEntryEvidenceFixture(management.target,true);
  }

void OnStart()
  {
   string boot="11111111-2222-4333-8444-555555555555",response;
   long sequence;
   ScxCheck(ScxChallenge("{\"boot_id\":"+ScQuote(boot)+
      ",\"next_inventory_sequence\":1}",response,sequence) &&
      response==boot && sequence==1,"execution challenge");
   ScxCheck(!ScxChallenge("{\"boot_id\":"+ScQuote(boot)+
      ",\"next_sequence\":1}",response,sequence),"telemetry sequence key denied");
   ScxCheck(ScReceipt("{\"accepted\":true,\"duplicate\":false,\"sequence\":1}",1),
      "common exact receipt");

   ScxCommand command,close;
   string good=ScxOpenCommandFixture();
   ScxCheck(ScxCommandJson(good,command),"open command");
   ScxCheck(command.operation=="open" && command.side=="buy" &&
      command.volume_text=="0.10" && command.volume==0.10 &&
      command.risk_limit==100.00 && command.cost_budget==1.00,"open values");
   ScxCheck(ScxCommandBinding(command,boot,"synthetic-generation-1",910001,
      "123456789","XAUUSD.fixture"),"command identity binding");
   ScxCheck(!ScxCommandBinding(command,boot,"synthetic-generation-1",910001,
      "123456789","XAUUSD.other"),"wrong symbol binding denied");
   ScxCheck(ScxCommandJson(ScxCloseCommandFixture(),close) && close.operation=="close" &&
      close.has_target && close.has_position_id && !close.has_side,"close command");
   ScxCheck(!ScxCommandJson(good+" trailing",command),"trailing command bytes");
   ScxCheck(!ScxCommandJson(StringSubstr(good,0,StringLen(good)-1)+
      ",\"operation\":\"open\"}",command),"duplicate command key");
   ScxCheck(!ScxCommandJson(StringSubstr(good,0,StringLen(good)-1)+
      ",\"extra\":1}",command),"extra command key");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"\"side\":\"buy\"","\"side\":null"),command),
      "entry side required");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"\"target_command_id\":null",
      "\"target_command_id\":\"synthetic-command-1\""),command),"self target denied");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"\"volume\":\"0.10\"",
      "\"volume\":\"1e-1\""),command),"exponent decimal denied");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"2026-09-20T00:00:30Z",
      "2026-09-20T00:00:30+07:00"),command),"non UTC expiry denied");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"+
      "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","ABC"),command),"fingerprint denied");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"synthetic-experiment",
      "synthetic experiment"),command),"unsafe identifier denied");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"\"broker_order_ticket\":null",
      "\"broker_order_ticket\":\"7001\""),command),"entry broker ticket denied");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"\"risk_limit\":\"100.00\"",
      "\"risk_limit\":null"),command),"entry risk limit required");
   ScxCheck(!ScxCommandJson(ScxChanged(good,"\"cost_budget\":\"1.00\"",
      "\"cost_budget\":\"100.00\""),command),"cost below risk required");
   ScxCheck(ScxNonNegativeDecimalText("0",command.cost_budget),"zero cost allowed");
   ScxCheck(ScxDecimalText("0.0000000001",command.volume),"ten decimal places");
   ScxCheck(!ScxDecimalText("0.00000000001",command.volume),"decimal precision bound");
   ScxCheck(!ScxDecimalText("01.00",command.volume),"leading decimal zero");
   ScxCheck(!ScxDecimalText("0",command.volume),"zero decimal denied");
   ScxCheck(ScxCurrency("USD") && !ScxCurrency("usd"),"currency alphabet");
   ScxCheck(ScxReason("owner_request") && !ScxReason("Owner Request"),"reason alphabet");
   datetime stamp;
   ScxCheck(ScxUtcTimestamp("2026-09-20T00:00:00Z",stamp),"UTC timestamp");
   ScxCheck(ScxUtcTimestamp("2026-09-20T00:00:00.123456Z",stamp),"UTC microseconds");
   ScxCheck(!ScxUtcTimestamp("2026-09-20T00:00:00.Z",stamp),"empty fraction denied");
   ScxCheck(!ScxUtcTimestamp("2026-02-30T00:00:00Z",stamp),"invalid calendar day");
   ScxCheck(ScxNoEffectRetcode(10006) && ScxNoEffectRetcode(10046),"no-effect limits");
   ScxCheck(!ScxNoEffectRetcode(10009) && !ScxNoEffectRetcode(10012) &&
      !ScxNoEffectRetcode(10036) && !ScxNoEffectRetcode(10039),"ambiguous codes denied");

   ScxBrokerEvidence entry;
   ScxEntryEvidenceFixture(entry,false);
   string entry_json;
   ScxCheck(ScxBrokerEvidenceJson(entry,entry_json) &&
      StringFind(entry_json,"\"stop_loss_confirmed\":true")>=0,
      "cumulative entry evidence");
   entry.remaining_volume=0.01;
   ScxCheck(!ScxBrokerEvidenceJson(entry,entry_json),"entry volume conservation");
   entry.remaining_volume=0;
   entry.deals[0].occurred_at="2026-09-20T00:00:01+07:00";
   ScxCheck(!ScxBrokerEvidenceJson(entry,entry_json),"entry deal UTC required");
   entry.deals[0].occurred_at="2026-09-20T00:00:01Z";
   ScxManagementEvidence management;
   ScxManagementEvidenceFixture(management);
   string management_json;
   ScxCheck(ScxManagementEvidenceJson(management,management_json) &&
      StringFind(management_json,"\"terminal_state\":\"closed\"")>=0,
      "cumulative management evidence");
   management.remaining_volume=0.01;
   ScxCheck(!ScxManagementEvidenceJson(management,management_json),
      "management volume conservation");
   management.remaining_volume=0;

   ScxInventorySample inventory;
   inventory.executor_id="synthetic-executor"; inventory.account_ref="123456789";
   inventory.server="Synthetic-Demo"; inventory.currency="USD";
   inventory.margin_mode="retail_hedging"; inventory.symbol="XAUUSD.fixture";
   inventory.generation="synthetic-generation-1";
   inventory.observed_at="2026-09-20T00:01:01Z";
   inventory.terminal_build=1; inventory.magic_number=910001;
   inventory.foreign_orders=0; inventory.foreign_positions=0;
   inventory.terminal_connected=true; inventory.account_trade_allowed=false;
   inventory.algo_trading_allowed=false; inventory.complete=true; inventory.equity=1000;
   ScxRejectionEvidence no_rejection,prior_rejection;
   prior_rejection.command_id="synthetic-command-3";
   prior_rejection.target_command_id="synthetic-command-1";
   prior_rejection.operation="close";
   prior_rejection.observed_at="2026-09-20T00:01:01Z";
   prior_rejection.retcode=10006; prior_rejection.retcode_external=0;
   prior_rejection.request_id=9; prior_rejection.has_target=true;
   string inventory_packet,outcome_packet,rejection_packet,uncertain;
   ScxCheck(ScxInventoryEvidenceJson(inventory,boot,1,true,management.target,true,management,
      true,prior_rejection,uncertain),"cumulative inventory evidence categories");
   prior_rejection.command_id=management.command_id;
   ScxCheck(!ScxInventoryEvidenceJson(inventory,boot,1,true,management.target,true,management,
      true,prior_rejection,uncertain),"inventory command namespace collision");
   ScxCheck(ScxInventoryEvidenceJson(inventory,boot,1,true,management.target,true,management,
      false,no_rejection,inventory_packet),"inventory evidence fixture");
   ScxCheck(StringFind(inventory_packet,"\"trade_mode\":\"demo\"")>=0,
      "inventory Demo only");
   ScxCheck(StringFind(inventory_packet,"\"algo_trading_allowed\":false")>=0,
      "fixture trading disabled");

   ScxCheck(ScxCommandJson(good,command),"reload command");
   ScxCheck(ScxEntrySnapshotOutcomeJson(command,"2026-09-20T00:00:01Z",entry,
      outcome_packet),"entry snapshot outcome fixture");
   ScxCheck(ScxManagementSnapshotOutcomeJson(close,management.observed_at,management,
      uncertain),"management snapshot outcome");
   entry.command_id="another-command";
   ScxCheck(!ScxEntrySnapshotOutcomeJson(command,"2026-09-20T00:00:01Z",entry,
      uncertain),"snapshot command binding");
   entry.command_id="synthetic-command-1";
   ScxCheck(ScxRejectionJson(command,"2026-09-20T00:00:01Z",10006,0,7,
      rejection_packet),"rejection fixture");
   ScxCheck(!ScxRejectionJson(command,"2026-09-20T00:00:01Z",10012,0,7,
      uncertain),"timeout is not rejection");
   ScxCheck(!ScxRejectionJson(command,"2026-09-20T00:00:01Z",10006,
      2147483648,7,uncertain),"external retcode bound");
   ScxCheck(ScxUncertainJson(command,"2026-09-20T00:00:01Z",true,10012,0,true,7,
      uncertain),"uncertain outcome");
   ScxCheck(StringFind(uncertain,"\"status\":\"uncertain\"")>=0,
      "uncertain remains distinct");
   if(scx_failures!=0)
     { Print("FAIL Sochron execution protocol self-test: ",scx_failures," of ",scx_checks); return; }

   char bytes[];
   int count=StringToCharArray(inventory_packet,bytes,0,WHOLE_ARRAY,CP_UTF8);
   if(count<2) { Print("FAIL execution inventory fixture encoding"); return; }
   ArrayResize(bytes,count-1);
   int output=FileOpen("SochronExecutionInventorySelfTest.json",FILE_WRITE|FILE_BIN);
   if(output==INVALID_HANDLE) { Print("FAIL execution inventory fixture output"); return; }
   uint written=FileWriteArray(output,bytes,0,ArraySize(bytes));
   FileClose(output);
   if(written!=ArraySize(bytes)) { Print("FAIL execution inventory fixture incomplete"); return; }

   count=StringToCharArray(outcome_packet,bytes,0,WHOLE_ARRAY,CP_UTF8);
   if(count<2) { Print("FAIL execution outcome fixture encoding"); return; }
   ArrayResize(bytes,count-1);
   output=FileOpen("SochronExecutionOutcomeSelfTest.json",FILE_WRITE|FILE_BIN);
   if(output==INVALID_HANDLE) { Print("FAIL execution outcome fixture output"); return; }
   written=FileWriteArray(output,bytes,0,ArraySize(bytes));
   FileClose(output);
   if(written!=ArraySize(bytes)) { Print("FAIL execution outcome fixture incomplete"); return; }
   Print("PASS Sochron execution protocol self-test: ",scx_checks,
         " cases; two synthetic fixtures generated");
  }
