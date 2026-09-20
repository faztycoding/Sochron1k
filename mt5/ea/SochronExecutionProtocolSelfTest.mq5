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

   ScxInventorySample inventory;
   inventory.executor_id="synthetic-executor"; inventory.account_ref="123456789";
   inventory.server="Synthetic-Demo"; inventory.currency="USD";
   inventory.margin_mode="retail_hedging"; inventory.symbol="XAUUSD.fixture";
   inventory.generation="synthetic-generation-1";
   inventory.observed_at="2026-09-20T00:00:00Z";
   inventory.terminal_build=1; inventory.magic_number=910001;
   inventory.foreign_orders=0; inventory.foreign_positions=0;
   inventory.terminal_connected=true; inventory.account_trade_allowed=false;
   inventory.algo_trading_allowed=false; inventory.complete=true; inventory.equity=1000;
   string inventory_packet,outcome_packet,uncertain;
   ScxCheck(ScxInventoryJson(inventory,boot,1,inventory_packet),"inventory fixture");
   ScxCheck(StringFind(inventory_packet,"\"trade_mode\":\"demo\"")>=0,
      "inventory Demo only");
   ScxCheck(StringFind(inventory_packet,"\"algo_trading_allowed\":false")>=0,
      "fixture trading disabled");

   ScxCheck(ScxCommandJson(good,command),"reload command");
   ScxCheck(ScxRejectionJson(command,"2026-09-20T00:00:01Z",10006,0,7,
      outcome_packet),"rejection fixture");
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
