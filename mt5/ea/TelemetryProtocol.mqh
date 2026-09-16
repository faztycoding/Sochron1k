#ifndef SOCHRON_TELEMETRY_PROTOCOL_MQH
#define SOCHRON_TELEMETRY_PROTOCOL_MQH

// Pure wire helpers. No network, account, file or trading operations here.
#define SC_MAX_SEQUENCE 9007199254740991

string ScQuote(const string value)
  {
   string result="\"";
   for(int i=0;i<StringLen(value);i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(c==34) result+="\\\"";
      else if(c==92) result+="\\\\";
      else if(c<32 || c>126) result+=StringFormat("\\u%04x",(int)c);
      else result+=StringSubstr(value,i,1);
     }
   return result+"\"";
  }

string ScBool(const bool value) { return value ? "true" : "false"; }
string ScDecimal(const double value) { return ScQuote(DoubleToString(value,10)); }

string ScUtc(const datetime value)
  {
   MqlDateTime d;
   if(!TimeToStruct(value,d)) return "";
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",
                       d.year,d.mon,d.day,d.hour,d.min,d.sec);
  }

bool ScTokenValid(const string value)
  {
   int length=StringLen(value);
   if(length<43 || length>128) return false;
   for(int i=0;i<length;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(!((c>=65 && c<=90) || (c>=97 && c<=122) ||
           (c>=48 && c<=57) || c==45 || c==95)) return false;
     }
   return true;
  }

void ScSpace(const string text,int &position)
  {
   while(position<StringLen(text))
     {
      ushort c=StringGetCharacter(text,position);
      if(c!=32 && c!=9 && c!=10 && c!=13) break;
      position++;
     }
  }

bool ScTake(const string text,int &position,const ushort expected)
  {
   ScSpace(text,position);
   if(position>=StringLen(text) || StringGetCharacter(text,position)!=expected) return false;
   position++;
   return true;
  }

// API response strings need only printable ASCII with no escapes.
// Deliberately reject a broader JSON dialect instead of silently misparsing it.
bool ScAsciiString(const string text,int &position,string &value)
  {
   value="";
   if(!ScTake(text,position,34)) return false;
   while(position<StringLen(text))
     {
      ushort c=StringGetCharacter(text,position++);
      if(c==34) return true;
      if(c<32 || c>126 || c==92) return false;
      value+=StringSubstr(text,position-1,1);
     }
   return false;
  }

bool ScPositiveInteger(const string text,long &value)
  {
   int length=StringLen(text);
   if(length<1 || length>16 || StringGetCharacter(text,0)==48) return false;
   for(int i=0;i<length;i++)
     {
      ushort c=StringGetCharacter(text,i);
      if(c<48 || c>57) return false;
     }
   value=StringToInteger(text);
   return value>0 && value<=SC_MAX_SEQUENCE;
  }

// Flat objects only; kinds: 1 string, 2 unsigned integer, 3 boolean.
bool ScFlatObject(const string text,string &keys[],string &values[],int &kinds[])
  {
   ArrayResize(keys,0); ArrayResize(values,0); ArrayResize(kinds,0);
   if(StringLen(text)>2048) return false;
   int position=0;
   if(!ScTake(text,position,123)) return false;
   for(int count=0;count<3;count++)
     {
      string key,value;
      int kind=0;
      if(!ScAsciiString(text,position,key) || !ScTake(text,position,58)) return false;
      for(int j=0;j<count;j++) if(keys[j]==key) return false;
      ScSpace(text,position);
      if(position>=StringLen(text)) return false;
      ushort c=StringGetCharacter(text,position);
      if(c==34)
        {
         if(!ScAsciiString(text,position,value)) return false;
         kind=1;
        }
      else
        {
         int start=position;
         while(position<StringLen(text))
           {
            c=StringGetCharacter(text,position);
            if(c==44 || c==125 || c==32 || c==9 || c==10 || c==13) break;
            position++;
           }
         value=StringSubstr(text,start,position-start);
         long number=0;
         if(value=="true" || value=="false") kind=3;
         else if(ScPositiveInteger(value,number)) kind=2;
         else return false;
        }
      ArrayResize(keys,count+1); ArrayResize(values,count+1); ArrayResize(kinds,count+1);
      keys[count]=key; values[count]=value; kinds[count]=kind;
      ScSpace(text,position);
      if(position>=StringLen(text)) return false;
      if(StringGetCharacter(text,position)==125)
        {
         position++; ScSpace(text,position);
         return position==StringLen(text);
        }
      if(!ScTake(text,position,44)) return false;
     }
   return false;
  }

bool ScUuid(const string value)
  {
   if(StringLen(value)!=36) return false;
   for(int i=0;i<36;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(i==8 || i==13 || i==18 || i==23) { if(c!=45) return false; }
      else if(!((c>=48 && c<=57) || (c>=97 && c<=102))) return false;
     }
   return true;
  }

bool ScChallenge(const string text,string &boot,long &sequence)
  {
   boot=""; sequence=0;
   string keys[],values[]; int kinds[];
   if(!ScFlatObject(text,keys,values,kinds) || ArraySize(keys)!=2) return false;
   for(int i=0;i<2;i++)
     {
      if(keys[i]=="boot_id" && kinds[i]==1) boot=values[i];
      else if(keys[i]=="next_sequence" && kinds[i]==2)
        { if(!ScPositiveInteger(values[i],sequence)) return false; }
      else return false;
     }
   return ScUuid(boot) && sequence>0;
  }

bool ScReceipt(const string text,const long expected_sequence)
  {
   string keys[],values[]; int kinds[];
   if(!ScFlatObject(text,keys,values,kinds) || ArraySize(keys)!=3) return false;
   bool accepted=false,duplicate_seen=false,sequence_seen=false;
   for(int i=0;i<3;i++)
     {
      if(keys[i]=="accepted" && kinds[i]==3) accepted=(values[i]=="true");
      else if(keys[i]=="duplicate" && kinds[i]==3) duplicate_seen=true;
      else if(keys[i]=="sequence" && kinds[i]==2)
        {
         long number=0;
         if(!ScPositiveInteger(values[i],number)) return false;
         sequence_seen=(number==expected_sequence);
        }
      else return false;
     }
   return accepted && duplicate_seen && sequence_seen;
  }

struct ScSample
  {
   string executor_id,account_ref,server,currency,margin_mode,symbol,observed_at;
   long terminal_build,tick_time_server_msc;
   bool account_trade_allowed;
   int broker_utc_offset_seconds,digits,stops,freeze;
   double equity,balance,free_margin,bid,ask,tick_size,volume_min,volume_max,volume_step;
   string filling_modes_json;
  };

string ScSnapshotJson(const ScSample &s,const string boot,const long sequence)
  {
   return "{\"protocol\":\"sochron.telemetry.v1\",\"source\":\"mt5-ea-sampled\","
      "\"boot_id\":"+ScQuote(boot)+",\"sequence\":"+IntegerToString(sequence)+
      ",\"identity\":{\"executor_id\":"+ScQuote(s.executor_id)+
      ",\"account_ref\":"+ScQuote(s.account_ref)+",\"server\":"+ScQuote(s.server)+
      ",\"currency\":"+ScQuote(s.currency)+",\"margin_mode\":"+ScQuote(s.margin_mode)+
      ",\"symbol\":"+ScQuote(s.symbol)+"},\"trade_mode\":\"demo\","
      "\"terminal_build\":"+IntegerToString(s.terminal_build)+
      ",\"terminal_connected\":true,\"account_trade_allowed\":"+ScBool(s.account_trade_allowed)+
      ",\"observed_at\":"+ScQuote(s.observed_at)+
      ",\"tick_time_server_msc\":"+IntegerToString(s.tick_time_server_msc)+
      ",\"broker_utc_offset_seconds\":"+IntegerToString(s.broker_utc_offset_seconds)+
      ",\"equity\":"+ScDecimal(s.equity)+",\"balance\":"+ScDecimal(s.balance)+
      ",\"free_margin\":"+ScDecimal(s.free_margin)+",\"bid\":"+ScDecimal(s.bid)+
      ",\"ask\":"+ScDecimal(s.ask)+",\"contract\":{\"symbol\":"+ScQuote(s.symbol)+
      ",\"digits\":"+IntegerToString(s.digits)+",\"tick_size\":"+ScDecimal(s.tick_size)+
      ",\"volume_min\":"+ScDecimal(s.volume_min)+",\"volume_max\":"+ScDecimal(s.volume_max)+
      ",\"volume_step\":"+ScDecimal(s.volume_step)+
      ",\"stops_level_points\":"+IntegerToString(s.stops)+
      ",\"freeze_level_points\":"+IntegerToString(s.freeze)+
      ",\"filling_modes\":"+s.filling_modes_json+"}}";
  }

#endif
