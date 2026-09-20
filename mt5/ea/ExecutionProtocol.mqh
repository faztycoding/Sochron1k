#ifndef SOCHRON_EXECUTION_PROTOCOL_MQH
#define SOCHRON_EXECUTION_PROTOCOL_MQH

// Pure SCN-013 wire helpers. No network, account, file or trading operations.
#include "TelemetryProtocol.mqh"

#define SCX_MAX_COMMAND_BYTES 16384
#define SCX_ALL_COMMAND_FIELDS 16777215
#define SCX_MAX_DEALS 32

struct ScxCommand
  {
   string protocol,boot_id,attempt_id,generation,command_id,target_command_id;
   string fingerprint,account_ref,experiment_id,symbol,operation,side;
   string volume_text,risk_limit_text,cost_budget_text;
   string requested_entry_text,stop_loss_text,take_profit_text;
   string broker_order_ticket,position_id,reason,expires_at_text;
   long dispatch_sequence,magic_number;
   double volume,risk_limit,cost_budget,requested_entry,stop_loss,take_profit;
   datetime expires_at;
   bool has_target,has_risk_limit,has_cost_budget,has_side;
   bool has_requested_entry,has_stop_loss,has_take_profit;
   bool has_broker_order_ticket,has_position_id,has_reason;
  };

struct ScxInventorySample
  {
   string executor_id,account_ref,server,currency,margin_mode,symbol;
   string generation,observed_at;
   long terminal_build,magic_number,foreign_orders,foreign_positions;
   bool terminal_connected,account_trade_allowed,algo_trading_allowed,complete;
   double equity;
  };

struct ScxDealEvidence
  {
   string deal_ticket,occurred_at;
   double volume,price,profit,commission,swap,fee;
   bool has_occurred_at;
  };

struct ScxBrokerEvidence
  {
   string command_id,order_ticket,position_id,terminal_state;
   double requested_volume,filled_volume,remaining_volume;
   double cancelled_volume,closed_volume;
   bool has_position_id,stop_loss_confirmed,has_terminal_state;
   ScxDealEvidence deals[];
  };

struct ScxManagementEvidence
  {
   string command_id,target_command_id,operation,broker_order_ticket;
   string position_id,terminal_state,observed_at;
   double requested_volume,completed_volume,remaining_volume;
   bool has_position_id,has_terminal_state;
   ScxDealEvidence deals[];
   ScxBrokerEvidence target;
  };

struct ScxRejectionEvidence
  {
   string command_id,target_command_id,operation,observed_at;
   long retcode,retcode_external,request_id;
   bool has_target;
  };

bool ScxSafeIdentifier(const string value,const int maximum)
  {
   int length=StringLen(value);
   if(length<1 || length>maximum) return false;
   for(int i=0;i<length;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(!((c>=65 && c<=90) || (c>=97 && c<=122) || (c>=48 && c<=57) ||
           c==45 || c==46 || c==58 || c==95)) return false;
     }
   return true;
  }

bool ScxHex64(const string value)
  {
   if(StringLen(value)!=64) return false;
   for(int i=0;i<64;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(!((c>=48 && c<=57) || (c>=97 && c<=102))) return false;
     }
   return true;
  }

bool ScxCurrency(const string value)
  {
   int length=StringLen(value);
   if(length<3 || length>8) return false;
   for(int i=0;i<length;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(c<65 || c>90) return false;
     }
   return true;
  }

bool ScxReason(const string value)
  {
   int length=StringLen(value);
   if(length<1 || length>64) return false;
   for(int i=0;i<length;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(!((c>=97 && c<=122) || (c>=48 && c<=57) || c==95)) return false;
     }
   return true;
  }

bool ScxLiteral(const string text,int &position,const string literal)
  {
   ScSpace(text,position);
   int length=StringLen(literal);
   if(StringSubstr(text,position,length)!=literal) return false;
   position+=length;
   return true;
  }

bool ScxStringOrNull(const string text,int &position,string &value,bool &present)
  {
   ScSpace(text,position);
   if(StringSubstr(text,position,4)=="null")
     { position+=4; value=""; present=false; return true; }
   present=ScAsciiString(text,position,value);
   return present;
  }

bool ScxIntegerToken(const string text,int &position,long &value)
  {
   ScSpace(text,position);
   int start=position;
   while(position<StringLen(text))
     {
      ushort c=StringGetCharacter(text,position);
      if(c<48 || c>57) break;
      position++;
     }
   return ScPositiveInteger(StringSubstr(text,start,position-start),value);
  }

bool ScxBoundedDecimalText(const string raw,double &value,const bool allow_zero)
  {
   int length=StringLen(raw),point=-1,digits=0,fraction=0;
   if(length<1 || length>40) return false;
   for(int i=0;i<length;i++)
     {
      ushort c=StringGetCharacter(raw,i);
      if(c==46)
        {
         if(point>=0 || i==0 || i==length-1) return false;
         point=i;
        }
      else
        {
         if(c<48 || c>57) return false;
         digits++;
         if(point>=0) fraction++;
        }
     }
   if(digits<1 || digits>24 || fraction>10) return false;
   int integer_length=(point<0 ? length : point);
   if(integer_length>1 && StringGetCharacter(raw,0)==48) return false;
   value=StringToDouble(raw);
   return MathIsValidNumber(value) && (value>0 || (allow_zero && value==0));
  }

bool ScxDecimalText(const string raw,double &value)
  { return ScxBoundedDecimalText(raw,value,false); }

bool ScxNonNegativeDecimalText(const string raw,double &value)
  { return ScxBoundedDecimalText(raw,value,true); }

bool ScxDecimalValue(const string text,int &position,string &raw,double &value)
  {
   if(!ScAsciiString(text,position,raw)) return false;
   return ScxDecimalText(raw,value);
  }

bool ScxDecimalOrNull(const string text,int &position,string &raw,double &value,bool &present)
  {
   ScSpace(text,position);
   if(StringSubstr(text,position,4)=="null")
     { position+=4; raw=""; value=0; present=false; return true; }
   present=true;
   return ScxDecimalValue(text,position,raw,value);
  }

bool ScxNonNegativeDecimalOrNull(const string text,int &position,string &raw,
                                 double &value,bool &present)
  {
   ScSpace(text,position);
   if(StringSubstr(text,position,4)=="null")
     { position+=4; raw=""; value=0; present=false; return true; }
   present=true;
   if(!ScAsciiString(text,position,raw)) return false;
   return ScxNonNegativeDecimalText(raw,value);
  }

bool ScxDigits(const string text,const int start,const int count,int &value)
  {
   if(start<0 || count<1 || start+count>StringLen(text)) return false;
   value=0;
   for(int i=0;i<count;i++)
     {
      ushort c=StringGetCharacter(text,start+i);
      if(c<48 || c>57) return false;
      value=value*10+(int)c-48;
     }
   return true;
  }

bool ScxUtcTimestamp(const string value,datetime &stamp)
  {
   int length=StringLen(value);
   if(length<20 || length>27 || StringGetCharacter(value,length-1)!=90 ||
      StringGetCharacter(value,4)!=45 || StringGetCharacter(value,7)!=45 ||
      StringGetCharacter(value,10)!=84 || StringGetCharacter(value,13)!=58 ||
      StringGetCharacter(value,16)!=58) return false;
   if(length>20)
     {
      if(length<22 || StringGetCharacter(value,19)!=46) return false;
      for(int i=20;i<length-1;i++)
        {
         ushort c=StringGetCharacter(value,i);
         if(c<48 || c>57) return false;
        }
     }
   int year,month,day,hour,minute,second;
   if(!ScxDigits(value,0,4,year) || !ScxDigits(value,5,2,month) ||
      !ScxDigits(value,8,2,day) || !ScxDigits(value,11,2,hour) ||
      !ScxDigits(value,14,2,minute) || !ScxDigits(value,17,2,second) ||
      year<2020 || year>2100 || month<1 || month>12 || day<1 || day>31 ||
      hour>23 || minute>59 || second>59) return false;
   MqlDateTime fields={};
   fields.year=year; fields.mon=month; fields.day=day;
   fields.hour=hour; fields.min=minute; fields.sec=second;
   stamp=StructToTime(fields);
   MqlDateTime check={};
   if(stamp<=0 || !TimeToStruct(stamp,check)) return false;
   return check.year==year && check.mon==month && check.day==day &&
      check.hour==hour && check.min==minute && check.sec==second;
  }

bool ScxCommandValid(const ScxCommand &command)
  {
   if(command.protocol!="sochron.execution.command.v1" || !ScUuid(command.boot_id) ||
      command.dispatch_sequence<1 || command.dispatch_sequence>SC_MAX_SEQUENCE ||
      command.magic_number<1 || command.magic_number>2147483647 ||
      !ScxSafeIdentifier(command.attempt_id,128) ||
      !ScxSafeIdentifier(command.generation,128) ||
      !ScxSafeIdentifier(command.command_id,128) || !ScxHex64(command.fingerprint) ||
      !ScxSafeIdentifier(command.account_ref,128) ||
      !ScxSafeIdentifier(command.experiment_id,128) ||
      !ScxSafeIdentifier(command.symbol,32) || command.volume<=0 ||
      command.expires_at<=0) return false;
   if(command.has_target && (!ScxSafeIdentifier(command.target_command_id,128) ||
      command.target_command_id==command.command_id)) return false;
   if(command.operation=="open")
     return !command.has_target && command.has_side &&
        (command.side=="buy" || command.side=="sell") &&
        command.has_risk_limit && command.has_cost_budget &&
        command.risk_limit>0 && command.cost_budget>=0 &&
        command.cost_budget<command.risk_limit &&
        command.has_requested_entry && command.has_stop_loss && command.has_take_profit &&
        !command.has_broker_order_ticket && !command.has_position_id && !command.has_reason;
   if(command.operation!="cancel" && command.operation!="close") return false;
   return command.has_target && !command.has_side && !command.has_requested_entry &&
      !command.has_stop_loss && !command.has_take_profit &&
      !command.has_risk_limit && !command.has_cost_budget &&
      command.has_broker_order_ticket && ScxSafeIdentifier(command.broker_order_ticket,128) &&
      (command.operation!="close" || (command.has_position_id &&
       ScxSafeIdentifier(command.position_id,128))) &&
      (!command.has_position_id || ScxSafeIdentifier(command.position_id,128)) &&
      command.has_reason && ScxReason(command.reason);
  }

bool ScxCommandBinding(const ScxCommand &command,const string expected_boot,
                       const string expected_generation,const long expected_magic,
                       const string expected_account,const string expected_symbol)
  {
   return ScxCommandValid(command) && ScUuid(expected_boot) &&
      ScxSafeIdentifier(expected_generation,128) && expected_magic>0 &&
      expected_magic<=2147483647 && ScxSafeIdentifier(expected_account,128) &&
      ScxSafeIdentifier(expected_symbol,32) && command.boot_id==expected_boot &&
      command.generation==expected_generation && command.magic_number==expected_magic &&
      command.account_ref==expected_account && command.symbol==expected_symbol;
  }

bool ScxCommandJson(const string text,ScxCommand &command)
  {
   ZeroMemory(command);
   if(StringLen(text)<2 || StringLen(text)>SCX_MAX_COMMAND_BYTES) return false;
   int position=0,fields=0;
   string seen="|";
   if(!ScTake(text,position,123)) return false;
   for(int count=0;count<24;count++)
     {
      string key;
      if(!ScAsciiString(text,position,key) || StringFind(seen,"|"+key+"|")>=0 ||
         !ScTake(text,position,58)) return false;
      seen+=key+"|";
      if(key=="protocol")
        { if(!ScAsciiString(text,position,command.protocol)) return false; fields|=1; }
      else if(key=="boot_id")
        { if(!ScAsciiString(text,position,command.boot_id)) return false; fields|=2; }
      else if(key=="dispatch_sequence")
        { if(!ScxIntegerToken(text,position,command.dispatch_sequence)) return false; fields|=4; }
      else if(key=="attempt_id")
        { if(!ScAsciiString(text,position,command.attempt_id)) return false; fields|=8; }
      else if(key=="generation")
        { if(!ScAsciiString(text,position,command.generation)) return false; fields|=16; }
      else if(key=="magic_number")
        { if(!ScxIntegerToken(text,position,command.magic_number)) return false; fields|=32; }
      else if(key=="command_id")
        { if(!ScAsciiString(text,position,command.command_id)) return false; fields|=64; }
      else if(key=="target_command_id")
        {
         if(!ScxStringOrNull(text,position,command.target_command_id,command.has_target))
            return false;
         fields|=128;
        }
      else if(key=="fingerprint")
        { if(!ScAsciiString(text,position,command.fingerprint)) return false; fields|=256; }
      else if(key=="account_ref")
        { if(!ScAsciiString(text,position,command.account_ref)) return false; fields|=512; }
      else if(key=="experiment_id")
        { if(!ScAsciiString(text,position,command.experiment_id)) return false; fields|=1024; }
      else if(key=="symbol")
        { if(!ScAsciiString(text,position,command.symbol)) return false; fields|=2048; }
      else if(key=="operation")
        { if(!ScAsciiString(text,position,command.operation)) return false; fields|=4096; }
      else if(key=="volume")
        {
         if(!ScxDecimalValue(text,position,command.volume_text,command.volume)) return false;
         fields|=8192;
        }
      else if(key=="risk_limit")
        {
         if(!ScxDecimalOrNull(text,position,command.risk_limit_text,
            command.risk_limit,command.has_risk_limit)) return false;
         fields|=4194304;
        }
      else if(key=="cost_budget")
        {
         if(!ScxNonNegativeDecimalOrNull(text,position,command.cost_budget_text,
            command.cost_budget,command.has_cost_budget)) return false;
         fields|=8388608;
        }
      else if(key=="expires_at")
        {
         if(!ScAsciiString(text,position,command.expires_at_text) ||
            !ScxUtcTimestamp(command.expires_at_text,command.expires_at)) return false;
         fields|=16384;
        }
      else if(key=="side")
        {
         if(!ScxStringOrNull(text,position,command.side,command.has_side)) return false;
         fields|=32768;
        }
      else if(key=="requested_entry")
        {
         if(!ScxDecimalOrNull(text,position,command.requested_entry_text,
            command.requested_entry,command.has_requested_entry)) return false;
         fields|=65536;
        }
      else if(key=="stop_loss")
        {
         if(!ScxDecimalOrNull(text,position,command.stop_loss_text,
            command.stop_loss,command.has_stop_loss)) return false;
         fields|=131072;
        }
      else if(key=="take_profit")
        {
         if(!ScxDecimalOrNull(text,position,command.take_profit_text,
            command.take_profit,command.has_take_profit)) return false;
         fields|=262144;
        }
      else if(key=="broker_order_ticket")
        {
         if(!ScxStringOrNull(text,position,command.broker_order_ticket,
            command.has_broker_order_ticket)) return false;
         fields|=524288;
        }
      else if(key=="position_id")
        {
         if(!ScxStringOrNull(text,position,command.position_id,
            command.has_position_id)) return false;
         fields|=1048576;
        }
      else if(key=="reason")
        {
         if(!ScxStringOrNull(text,position,command.reason,command.has_reason)) return false;
         fields|=2097152;
        }
      else return false;
      ScSpace(text,position);
      if(position>=StringLen(text)) return false;
      if(StringGetCharacter(text,position)==125)
        {
         position++; ScSpace(text,position);
         return position==StringLen(text) && fields==SCX_ALL_COMMAND_FIELDS &&
            ScxCommandValid(command);
        }
      if(!ScTake(text,position,44)) return false;
     }
   return false;
  }

bool ScxChallenge(const string text,string &boot,long &sequence)
  {
   boot=""; sequence=0;
   string keys[],values[]; int kinds[];
   if(!ScFlatObject(text,keys,values,kinds) || ArraySize(keys)!=2) return false;
   for(int i=0;i<2;i++)
     {
      if(keys[i]=="boot_id" && kinds[i]==1) boot=values[i];
      else if(keys[i]=="next_inventory_sequence" && kinds[i]==2)
        { if(!ScPositiveInteger(values[i],sequence)) return false; }
      else return false;
     }
   return ScUuid(boot) && sequence>0;
  }

bool ScxInventoryJson(const ScxInventorySample &s,const string boot,const long sequence,
                      string &packet)
  {
   packet="";
   datetime observed;
   if(!ScUuid(boot) || sequence<1 || sequence>SC_MAX_SEQUENCE ||
      !ScxSafeIdentifier(s.executor_id,128) || !ScxSafeIdentifier(s.account_ref,128) ||
      !ScxSafeIdentifier(s.server,128) || !ScxCurrency(s.currency) ||
      (s.margin_mode!="retail_netting" && s.margin_mode!="retail_hedging" &&
       s.margin_mode!="exchange") || !ScxSafeIdentifier(s.symbol,32) ||
      !ScxSafeIdentifier(s.generation,128) || !ScxUtcTimestamp(s.observed_at,observed) ||
      s.terminal_build<1 || s.magic_number<1 || s.magic_number>2147483647 ||
      s.foreign_orders<0 || s.foreign_orders>100000 ||
      s.foreign_positions<0 || s.foreign_positions>100000 ||
      !MathIsValidNumber(s.equity) ||
      s.equity<=0) return false;
   packet="{\"protocol\":\"sochron.execution.inventory.v1\",\"boot_id\":"+
      ScQuote(boot)+",\"sequence\":"+IntegerToString(sequence)+
      ",\"identity\":{\"executor_id\":"+ScQuote(s.executor_id)+
      ",\"account_ref\":"+ScQuote(s.account_ref)+",\"server\":"+ScQuote(s.server)+
      ",\"currency\":"+ScQuote(s.currency)+",\"margin_mode\":"+ScQuote(s.margin_mode)+
      ",\"symbol\":"+ScQuote(s.symbol)+"},\"trade_mode\":\"demo\","+
      "\"terminal_build\":"+IntegerToString(s.terminal_build)+
      ",\"terminal_connected\":"+ScBool(s.terminal_connected)+
      ",\"account_trade_allowed\":"+ScBool(s.account_trade_allowed)+
      ",\"algo_trading_allowed\":"+ScBool(s.algo_trading_allowed)+
      ",\"magic_number\":"+IntegerToString(s.magic_number)+
      ",\"observed_at\":"+ScQuote(s.observed_at)+",\"inventory\":{\"executor_id\":"+
      ScQuote(s.executor_id)+",\"generation\":"+ScQuote(s.generation)+
      ",\"account\":{\"account_ref\":"+ScQuote(s.account_ref)+
      ",\"server\":"+ScQuote(s.server)+",\"currency\":"+ScQuote(s.currency)+
      ",\"margin_mode\":"+ScQuote(s.margin_mode)+",\"trade_mode\":\"demo\","+
      "\"can_trade\":"+ScBool(s.account_trade_allowed)+",\"equity\":"+
      ScDecimal(s.equity)+",\"checked_at\":"+ScQuote(s.observed_at)+"},\"symbol\":"+
      ScQuote(s.symbol)+",\"observed_at\":"+ScQuote(s.observed_at)+
      ",\"complete\":"+ScBool(s.complete)+",\"foreign_orders\":"+
      IntegerToString(s.foreign_orders)+",\"foreign_positions\":"+
      IntegerToString(s.foreign_positions)+
      ",\"snapshots\":[],\"management_snapshots\":[],\"rejections\":[]}}";
   return StringLen(packet)<=262144;
  }

bool ScxNoEffectRetcode(const long retcode)
  {
   long allowed[27]={10004,10006,10007,10013,10014,10015,10016,10017,10018,
                     10019,10020,10021,10022,10024,10026,10027,10029,10030,
                     10032,10033,10034,10035,10040,10042,10043,10044,10045};
   for(int i=0;i<ArraySize(allowed);i++) if(retcode==allowed[i]) return true;
   return retcode==10046;
  }

string ScxNullableString(const bool present,const string value)
  { return present ? ScQuote(value) : "null"; }

bool ScxDecimalEqual(const double left,const double right)
  {
   if(!MathIsValidNumber(left) || !MathIsValidNumber(right)) return false;
   return MathAbs(left-right)<=0.00000000005;
  }

bool ScxEntryTerminalState(const string value)
  {
   return value=="rejected" || value=="cancelled" || value=="closed" ||
      value=="expired";
  }

bool ScxManagementTerminalState(const string value)
  { return value=="rejected" || value=="cancelled" || value=="closed"; }

bool ScxDealEvidenceJson(const ScxDealEvidence &deal,string &packet)
  {
   packet="";
   datetime occurred;
   if(!ScxSafeIdentifier(deal.deal_ticket,128) ||
      !MathIsValidNumber(deal.volume) || deal.volume<=0 ||
      !MathIsValidNumber(deal.price) || deal.price<=0 ||
      !MathIsValidNumber(deal.profit) || !MathIsValidNumber(deal.commission) ||
      !MathIsValidNumber(deal.swap) || !MathIsValidNumber(deal.fee) ||
      (deal.has_occurred_at && !ScxUtcTimestamp(deal.occurred_at,occurred)) ||
      (!deal.has_occurred_at && deal.occurred_at!="")) return false;
   packet="{\"deal_ticket\":"+ScQuote(deal.deal_ticket)+
      ",\"volume\":"+ScDecimal(deal.volume)+",\"price\":"+
      ScDecimal(deal.price)+",\"profit\":"+ScDecimal(deal.profit)+
      ",\"commission\":"+ScDecimal(deal.commission)+",\"swap\":"+
      ScDecimal(deal.swap)+",\"fee\":"+ScDecimal(deal.fee)+
      ",\"occurred_at\":"+ScxNullableString(deal.has_occurred_at,deal.occurred_at)+"}";
   return StringLen(packet)<=2048;
  }

bool ScxDealsJson(const ScxDealEvidence &deals[],string &packet,double &total)
  {
   packet="["; total=0;
   int count=ArraySize(deals);
   if(count<0 || count>SCX_MAX_DEALS) return false;
   for(int i=0;i<count;i++)
     {
      for(int j=0;j<i;j++) if(deals[j].deal_ticket==deals[i].deal_ticket) return false;
      string item;
      if(!ScxDealEvidenceJson(deals[i],item)) return false;
      if(i>0) packet+=",";
      packet+=item;
      total+=deals[i].volume;
      if(!MathIsValidNumber(total) || StringLen(packet)>131072) return false;
     }
   packet+="]";
   return true;
  }

bool ScxBrokerEvidenceJson(const ScxBrokerEvidence &snapshot,string &packet)
  {
   packet="";
   if(!ScxSafeIdentifier(snapshot.command_id,128) ||
      !ScxSafeIdentifier(snapshot.order_ticket,128) ||
      (snapshot.has_position_id && !ScxSafeIdentifier(snapshot.position_id,128)) ||
      (!snapshot.has_position_id && snapshot.position_id!="") ||
      (snapshot.has_terminal_state && !ScxEntryTerminalState(snapshot.terminal_state)) ||
      (!snapshot.has_terminal_state && snapshot.terminal_state!="")) return false;
   double values[5]={snapshot.requested_volume,snapshot.filled_volume,
      snapshot.remaining_volume,snapshot.cancelled_volume,snapshot.closed_volume};
   if(!MathIsValidNumber(values[0]) || values[0]<=0) return false;
   for(int i=1;i<5;i++) if(!MathIsValidNumber(values[i]) || values[i]<0) return false;
   if(!ScxDecimalEqual(snapshot.filled_volume+snapshot.remaining_volume+
      snapshot.cancelled_volume,snapshot.requested_volume) ||
      snapshot.closed_volume>snapshot.filled_volume ||
      (snapshot.filled_volume>0 && !snapshot.has_position_id) ||
      (snapshot.stop_loss_confirmed &&
       snapshot.filled_volume-snapshot.closed_volume<=0)) return false;
   string deals;
   double dealt=0;
   if(!ScxDealsJson(snapshot.deals,deals,dealt) ||
      !ScxDecimalEqual(dealt,snapshot.filled_volume)) return false;
   if(snapshot.has_terminal_state)
     {
      if(snapshot.terminal_state=="rejected" &&
         (!ScxDecimalEqual(snapshot.filled_volume,0) ||
          !ScxDecimalEqual(snapshot.cancelled_volume,0) ||
          !ScxDecimalEqual(snapshot.closed_volume,0) ||
          !ScxDecimalEqual(snapshot.remaining_volume,snapshot.requested_volume) ||
          ArraySize(snapshot.deals)!=0 || snapshot.has_position_id)) return false;
      if((snapshot.terminal_state=="cancelled" || snapshot.terminal_state=="expired") &&
         (!ScxDecimalEqual(snapshot.filled_volume,0) ||
          !ScxDecimalEqual(snapshot.closed_volume,0) ||
          !ScxDecimalEqual(snapshot.remaining_volume,0) ||
          !ScxDecimalEqual(snapshot.cancelled_volume,snapshot.requested_volume) ||
          ArraySize(snapshot.deals)!=0 || snapshot.has_position_id)) return false;
      if(snapshot.terminal_state=="closed" &&
         (snapshot.filled_volume<=0 ||
          !ScxDecimalEqual(snapshot.closed_volume,snapshot.filled_volume) ||
          !ScxDecimalEqual(snapshot.remaining_volume,0) ||
          snapshot.stop_loss_confirmed)) return false;
     }
   else if(snapshot.remaining_volume<=0 &&
           snapshot.filled_volume-snapshot.closed_volume<=0) return false;
   packet="{\"command_id\":"+ScQuote(snapshot.command_id)+
      ",\"order_ticket\":"+ScQuote(snapshot.order_ticket)+
      ",\"position_id\":"+ScxNullableString(snapshot.has_position_id,snapshot.position_id)+
      ",\"requested_volume\":"+ScDecimal(snapshot.requested_volume)+
      ",\"filled_volume\":"+ScDecimal(snapshot.filled_volume)+
      ",\"remaining_volume\":"+ScDecimal(snapshot.remaining_volume)+
      ",\"cancelled_volume\":"+ScDecimal(snapshot.cancelled_volume)+
      ",\"closed_volume\":"+ScDecimal(snapshot.closed_volume)+
      ",\"deals\":"+deals+",\"stop_loss_confirmed\":"+
      ScBool(snapshot.stop_loss_confirmed)+",\"terminal_state\":"+
      ScxNullableString(snapshot.has_terminal_state,snapshot.terminal_state)+"}";
   return StringLen(packet)<=196608;
  }

bool ScxManagementEvidenceJson(const ScxManagementEvidence &snapshot,string &packet)
  {
   packet="";
   datetime observed;
   if(!ScxSafeIdentifier(snapshot.command_id,128) ||
      !ScxSafeIdentifier(snapshot.target_command_id,128) ||
      snapshot.command_id==snapshot.target_command_id ||
      (snapshot.operation!="cancel" && snapshot.operation!="close") ||
      !ScxSafeIdentifier(snapshot.broker_order_ticket,128) ||
      (snapshot.has_position_id && !ScxSafeIdentifier(snapshot.position_id,128)) ||
      (!snapshot.has_position_id && snapshot.position_id!="") ||
      (snapshot.operation=="close" && !snapshot.has_position_id) ||
      (snapshot.has_terminal_state &&
       !ScxManagementTerminalState(snapshot.terminal_state)) ||
      (!snapshot.has_terminal_state && snapshot.terminal_state!="") ||
      !ScxUtcTimestamp(snapshot.observed_at,observed) ||
      !MathIsValidNumber(snapshot.requested_volume) || snapshot.requested_volume<=0 ||
      !MathIsValidNumber(snapshot.completed_volume) || snapshot.completed_volume<0 ||
      !MathIsValidNumber(snapshot.remaining_volume) || snapshot.remaining_volume<0 ||
      !ScxDecimalEqual(snapshot.completed_volume+snapshot.remaining_volume,
                       snapshot.requested_volume)) return false;
   string deals,target;
   double dealt=0;
   if(!ScxDealsJson(snapshot.deals,deals,dealt) ||
      !ScxBrokerEvidenceJson(snapshot.target,target) ||
      snapshot.target.command_id!=snapshot.target_command_id) return false;
   if(snapshot.operation=="cancel")
     {
      if(ArraySize(snapshot.deals)!=0 || !snapshot.has_terminal_state ||
         (snapshot.terminal_state!="cancelled" && snapshot.terminal_state!="rejected"))
         return false;
     }
   else if(!ScxDecimalEqual(dealt,snapshot.completed_volume)) return false;
   if(snapshot.has_terminal_state && snapshot.terminal_state=="rejected" &&
      (!ScxDecimalEqual(snapshot.completed_volume,0) ||
       !ScxDecimalEqual(snapshot.remaining_volume,snapshot.requested_volume) ||
       ArraySize(snapshot.deals)!=0)) return false;
   if(snapshot.has_terminal_state &&
      (snapshot.terminal_state=="closed" || snapshot.terminal_state=="cancelled") &&
      (!ScxDecimalEqual(snapshot.completed_volume,snapshot.requested_volume) ||
       !ScxDecimalEqual(snapshot.remaining_volume,0))) return false;
   if(!snapshot.has_terminal_state &&
      (snapshot.operation!="close" || snapshot.completed_volume<=0 ||
       snapshot.remaining_volume<=0)) return false;
   packet="{\"command_id\":"+ScQuote(snapshot.command_id)+
      ",\"target_command_id\":"+ScQuote(snapshot.target_command_id)+
      ",\"operation\":"+ScQuote(snapshot.operation)+
      ",\"broker_order_ticket\":"+ScQuote(snapshot.broker_order_ticket)+
      ",\"position_id\":"+ScxNullableString(snapshot.has_position_id,snapshot.position_id)+
      ",\"requested_volume\":"+ScDecimal(snapshot.requested_volume)+
      ",\"completed_volume\":"+ScDecimal(snapshot.completed_volume)+
      ",\"remaining_volume\":"+ScDecimal(snapshot.remaining_volume)+
      ",\"deals\":"+deals+",\"terminal_state\":"+
      ScxNullableString(snapshot.has_terminal_state,snapshot.terminal_state)+
      ",\"target\":"+target+",\"observed_at\":"+
      ScQuote(snapshot.observed_at)+"}";
   return StringLen(packet)<=245760;
  }

bool ScxRejectionEvidenceJson(const ScxRejectionEvidence &rejection,string &packet)
  {
   packet="";
   datetime observed;
   if(!ScxSafeIdentifier(rejection.command_id,128) ||
      (rejection.has_target &&
       (!ScxSafeIdentifier(rejection.target_command_id,128) ||
        rejection.target_command_id==rejection.command_id)) ||
      (!rejection.has_target && rejection.target_command_id!="") ||
      ((rejection.operation=="open")==rejection.has_target) ||
      (rejection.operation!="open" && rejection.operation!="cancel" &&
       rejection.operation!="close") || !ScxUtcTimestamp(rejection.observed_at,observed) ||
      !ScxNoEffectRetcode(rejection.retcode) ||
      rejection.retcode_external<-2147483648 ||
      rejection.retcode_external>2147483647 || rejection.request_id<0 ||
      rejection.request_id>4294967295) return false;
   packet="{\"command_id\":"+ScQuote(rejection.command_id)+
      ",\"target_command_id\":"+
      ScxNullableString(rejection.has_target,rejection.target_command_id)+
      ",\"operation\":"+ScQuote(rejection.operation)+",\"retcode\":"+
      IntegerToString(rejection.retcode)+",\"retcode_external\":"+
      IntegerToString(rejection.retcode_external)+",\"request_id\":"+
      IntegerToString(rejection.request_id)+",\"observed_at\":"+
      ScQuote(rejection.observed_at)+"}";
   return StringLen(packet)<=4096;
  }

bool ScxInventoryEvidenceJson(const ScxInventorySample &sample,const string boot,
                              const long sequence,const bool has_entry,
                              const ScxBrokerEvidence &entry,const bool has_management,
                              const ScxManagementEvidence &management,
                              const bool has_rejection,
                              const ScxRejectionEvidence &rejection,string &packet)
  {
   if(!ScxInventoryJson(sample,boot,sequence,packet)) return false;
   string entry_json="",management_json="",rejection_json="";
   if(has_entry && !ScxBrokerEvidenceJson(entry,entry_json)) return false;
   if(has_management)
     {
      if(!has_entry || !ScxManagementEvidenceJson(management,management_json) ||
         management.target_command_id!=entry.command_id ||
         management.target.command_id!=entry.command_id) return false;
     }
   if(has_rejection)
     {
      if(!ScxRejectionEvidenceJson(rejection,rejection_json) ||
         (rejection.operation=="open" && has_entry) ||
         (rejection.operation!="open" &&
          (!has_entry || rejection.target_command_id!=entry.command_id))) return false;
     }
   if(has_entry && has_management && entry.command_id==management.command_id) return false;
   if(has_entry && has_rejection && entry.command_id==rejection.command_id) return false;
   if(has_management && has_rejection &&
      management.command_id==rejection.command_id) return false;
   string entries=has_entry ? "["+entry_json+"]" : "[]";
   string managements=has_management ? "["+management_json+"]" : "[]";
   string rejections=has_rejection ? "["+rejection_json+"]" : "[]";
   if(StringReplace(packet,"\"snapshots\":[]","\"snapshots\":"+entries)!=1 ||
      StringReplace(packet,"\"management_snapshots\":[]",
                    "\"management_snapshots\":"+managements)!=1 ||
      StringReplace(packet,"\"rejections\":[]","\"rejections\":"+rejections)!=1)
      return false;
   return StringLen(packet)<=262144;
  }

bool ScxEntrySnapshotOutcomeJson(const ScxCommand &command,const string observed_at,
                                 const ScxBrokerEvidence &snapshot,string &packet)
  {
   packet="";
   datetime observed;
   string body;
   if(!ScxCommandValid(command) || command.operation!="open" ||
      snapshot.command_id!=command.command_id ||
      !ScxUtcTimestamp(observed_at,observed) ||
      !ScxBrokerEvidenceJson(snapshot,body)) return false;
   packet="{\"protocol\":\"sochron.execution.outcome.v1\",\"boot_id\":"+
      ScQuote(command.boot_id)+",\"dispatch_sequence\":"+
      IntegerToString(command.dispatch_sequence)+",\"attempt_id\":"+
      ScQuote(command.attempt_id)+",\"generation\":"+ScQuote(command.generation)+
      ",\"command_id\":"+ScQuote(command.command_id)+
      ",\"target_command_id\":null,\"operation\":\"open\",\"observed_at\":"+
      ScQuote(observed_at)+",\"status\":\"snapshot\",\"snapshot\":"+body+
      ",\"management_snapshot\":null,\"rejection\":null,\"uncertain\":null}";
   return StringLen(packet)<=262144;
  }

bool ScxManagementSnapshotOutcomeJson(const ScxCommand &command,const string observed_at,
                                      const ScxManagementEvidence &snapshot,string &packet)
  {
   packet="";
   datetime observed;
   string body;
   if(!ScxCommandValid(command) || command.operation=="open" ||
      snapshot.command_id!=command.command_id ||
      snapshot.target_command_id!=command.target_command_id ||
      snapshot.operation!=command.operation || !ScxUtcTimestamp(observed_at,observed) ||
      !ScxManagementEvidenceJson(snapshot,body) || snapshot.observed_at!=observed_at)
      return false;
   packet="{\"protocol\":\"sochron.execution.outcome.v1\",\"boot_id\":"+
      ScQuote(command.boot_id)+",\"dispatch_sequence\":"+
      IntegerToString(command.dispatch_sequence)+",\"attempt_id\":"+
      ScQuote(command.attempt_id)+",\"generation\":"+ScQuote(command.generation)+
      ",\"command_id\":"+ScQuote(command.command_id)+",\"target_command_id\":"+
      ScQuote(command.target_command_id)+",\"operation\":"+ScQuote(command.operation)+
      ",\"observed_at\":"+ScQuote(observed_at)+
      ",\"status\":\"snapshot\",\"snapshot\":null,\"management_snapshot\":"+
      body+",\"rejection\":null,\"uncertain\":null}";
   return StringLen(packet)<=262144;
  }

bool ScxRejectionJson(const ScxCommand &command,const string observed_at,const long retcode,
                      const long retcode_external,const long request_id,string &packet)
  {
   packet="";
   datetime observed;
   if(!ScxCommandValid(command) || !ScxUtcTimestamp(observed_at,observed) ||
      !ScxNoEffectRetcode(retcode) || retcode_external<-2147483648 ||
      retcode_external>2147483647 || request_id<0 || request_id>4294967295) return false;
   string target=ScxNullableString(command.has_target,command.target_command_id);
   packet="{\"protocol\":\"sochron.execution.outcome.v1\",\"boot_id\":"+
      ScQuote(command.boot_id)+",\"dispatch_sequence\":"+
      IntegerToString(command.dispatch_sequence)+",\"attempt_id\":"+
      ScQuote(command.attempt_id)+",\"generation\":"+ScQuote(command.generation)+
      ",\"command_id\":"+ScQuote(command.command_id)+",\"target_command_id\":"+
      target+",\"operation\":"+ScQuote(command.operation)+",\"observed_at\":"+
      ScQuote(observed_at)+",\"status\":\"rejected\",\"snapshot\":null,"+
      "\"management_snapshot\":null,\"rejection\":{\"command_id\":"+
      ScQuote(command.command_id)+",\"target_command_id\":"+target+
      ",\"operation\":"+ScQuote(command.operation)+",\"retcode\":"+
      IntegerToString(retcode)+",\"retcode_external\":"+
      IntegerToString(retcode_external)+",\"request_id\":"+
      IntegerToString(request_id)+",\"observed_at\":"+ScQuote(observed_at)+
      "},\"uncertain\":null}";
   return StringLen(packet)<=262144;
  }

bool ScxUncertainJson(const ScxCommand &command,const string observed_at,
                      const bool has_retcode,const long retcode,
                      const long retcode_external,const bool has_request_id,
                      const long request_id,string &packet)
  {
   packet="";
   datetime observed;
   if(!ScxCommandValid(command) || !ScxUtcTimestamp(observed_at,observed) ||
      (has_retcode && (retcode<0 || retcode>4294967295)) ||
      retcode_external<-2147483648 || retcode_external>2147483647 ||
      (has_request_id && (request_id<0 || request_id>4294967295))) return false;
   string target=ScxNullableString(command.has_target,command.target_command_id);
   string code=has_retcode ? IntegerToString(retcode) : "null";
   string request=has_request_id ? IntegerToString(request_id) : "null";
   packet="{\"protocol\":\"sochron.execution.outcome.v1\",\"boot_id\":"+
      ScQuote(command.boot_id)+",\"dispatch_sequence\":"+
      IntegerToString(command.dispatch_sequence)+",\"attempt_id\":"+
      ScQuote(command.attempt_id)+",\"generation\":"+ScQuote(command.generation)+
      ",\"command_id\":"+ScQuote(command.command_id)+",\"target_command_id\":"+
      target+",\"operation\":"+ScQuote(command.operation)+",\"observed_at\":"+
      ScQuote(observed_at)+",\"status\":\"uncertain\",\"snapshot\":null,"+
      "\"management_snapshot\":null,\"rejection\":null,\"uncertain\":{"+
      "\"retcode\":"+code+",\"retcode_external\":"+
      IntegerToString(retcode_external)+",\"request_id\":"+request+"}}";
   return StringLen(packet)<=262144;
  }

#endif
