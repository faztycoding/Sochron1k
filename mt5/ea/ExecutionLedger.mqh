#ifndef SOCHRON_EXECUTION_LEDGER_MQH
#define SOCHRON_EXECUTION_LEDGER_MQH

// Terminal-local append-only executor ledger. The selected MT5 build must still
// prove lock sharing and flush durability; this source never claims power-loss fsync.
#include "ExecutionProtocol.mqh"

#define SCXE_MAX_LEDGER_BYTES 262144
#define SCXE_MAX_LEDGER_RECORDS 128

struct ScxeLedgerRecord
  {
   bool present,send_attempted,has_retcode,has_request_id;
   long sequence,history_from,retcode,retcode_external,request_id;
   string stage,observed_at,command_json,outcome_json;
   string order_ticket,deal_ticket;
   ScxCommand command;
  };

struct ScxeLedgerBook
  {
   long sequence;
   bool has_entry,has_management;
   ScxeLedgerRecord entry,management;
  };

bool ScxeAsciiLine(const string value,const int maximum)
  {
   int length=StringLen(value);
   if(length<1 || length>maximum) return false;
   for(int i=0;i<length;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(c<32 || c>126 || c==9 || c==10 || c==13) return false;
     }
   return true;
  }

ulong ScxeChecksum(const string value)
  {
   uchar bytes[];
   int count=StringToCharArray(value,bytes,0,WHOLE_ARRAY,CP_UTF8);
   if(count<1) return 0;
   ArrayResize(bytes,count-1);
   ulong hash=1469598103934665603;
   for(int i=0;i<ArraySize(bytes);i++)
     {
      hash^=(ulong)bytes[i];
      hash*=1099511628211;
     }
   ArrayInitialize(bytes,0);
   return hash;
  }

string ScxeChecksumText(const string value)
  { return StringFormat("%016I64X",ScxeChecksum(value)); }

bool ScxeHexChecksum(const string value,ulong &result)
  {
   if(StringLen(value)!=16) return false;
   result=0;
   for(int i=0;i<16;i++)
     {
      ushort c=StringGetCharacter(value,i);
      int digit=-1;
      if(c>=48 && c<=57) digit=(int)c-48;
      else if(c>=65 && c<=70) digit=(int)c-55;
      else return false;
      result=(result<<4)|(ulong)digit;
     }
   return true;
  }

bool ScxeSignedLong(const string value,long &result)
  {
   int length=StringLen(value),start=0;
   if(length<1 || length>20) return false;
   if(StringGetCharacter(value,0)==45)
     {
      if(length==1) return false;
      start=1;
     }
   if(length-start>1 && StringGetCharacter(value,start)==48) return false;
   for(int i=start;i<length;i++)
     {
      ushort c=StringGetCharacter(value,i);
      if(c<48 || c>57) return false;
     }
   result=StringToInteger(value);
   return IntegerToString(result)==value;
  }

bool ScxeStage(const string value)
  {
   return value=="PREPARED" || value=="SEND_STARTED" ||
      value=="SEND_RETURN" || value=="OUTCOME_READY" ||
      value=="OUTCOME_ACKED" || value=="RECOVERED_INVENTORY";
  }

bool ScxeUnresolvedStage(const string value)
  {
   return value=="PREPARED" || value=="SEND_STARTED" ||
      value=="SEND_RETURN" || value=="OUTCOME_READY";
  }

bool ScxeRecordStageShape(const ScxeLedgerRecord &record)
  {
   if((!record.has_retcode && record.retcode!=0) ||
      (!record.has_request_id && record.request_id!=0)) return false;
   if(record.stage=="PREPARED")
      return !record.send_attempted && !record.has_retcode &&
         !record.has_request_id && record.order_ticket=="" &&
         record.deal_ticket=="" && record.outcome_json=="";
   if(record.stage=="SEND_STARTED")
      return record.send_attempted && !record.has_retcode &&
         !record.has_request_id && record.order_ticket=="" &&
         record.deal_ticket=="" && record.outcome_json=="";
   if(record.stage=="SEND_RETURN")
      return record.send_attempted && record.has_retcode &&
         record.outcome_json=="";
   if(record.stage=="OUTCOME_READY" || record.stage=="OUTCOME_ACKED")
      return record.outcome_json!="";
   return record.stage=="RECOVERED_INVENTORY" && record.outcome_json=="";
  }

bool ScxeTransition(const string previous,const string next)
  {
   if(previous=="") return next=="PREPARED";
   if(previous=="PREPARED")
      return next=="SEND_STARTED" || next=="OUTCOME_READY";
   if(previous=="SEND_STARTED")
      return next=="SEND_RETURN" || next=="OUTCOME_READY" ||
         next=="RECOVERED_INVENTORY";
   if(previous=="SEND_RETURN")
      return next=="OUTCOME_READY" || next=="RECOVERED_INVENTORY";
   if(previous=="OUTCOME_READY")
      return next=="OUTCOME_ACKED" || next=="RECOVERED_INVENTORY";
   return false;
  }

bool ScxeSameCommand(const ScxCommand &left,const ScxCommand &right)
  {
   return left.command_id==right.command_id &&
      left.attempt_id==right.attempt_id && left.fingerprint==right.fingerprint &&
      left.generation==right.generation && left.operation==right.operation &&
      left.boot_id==right.boot_id && left.dispatch_sequence==right.dispatch_sequence;
  }

bool ScxeRecordLine(const ScxeLedgerRecord &record,string &payload,string &line)
  {
   payload=""; line="";
   datetime observed;
   ScxCommand parsed;
   if(!record.present || record.sequence<1 || record.history_from<=0 ||
      !ScxeStage(record.stage) ||
      !ScxeRecordStageShape(record) ||
      !ScxUtcTimestamp(record.observed_at,observed) ||
      !ScxeAsciiLine(record.command_json,SCX_MAX_COMMAND_BYTES) ||
      (record.outcome_json!="" && !ScxeAsciiLine(record.outcome_json,262144)) ||
      (record.order_ticket!="" && !ScxSafeIdentifier(record.order_ticket,128)) ||
      (record.deal_ticket!="" && !ScxSafeIdentifier(record.deal_ticket,128)) ||
      !ScxCommandJson(record.command_json,parsed) ||
      !ScxeSameCommand(parsed,record.command)) return false;
   payload="SCXL1\t"+IntegerToString(record.sequence)+"\t"+record.stage+"\t"+
      record.observed_at+"\t"+IntegerToString(record.history_from)+"\t"+
      (record.send_attempted ? "1" : "0")+"\t"+
      (record.has_retcode ? IntegerToString(record.retcode) : "-")+"\t"+
      IntegerToString(record.retcode_external)+"\t"+
      (record.has_request_id ? IntegerToString(record.request_id) : "-")+"\t"+
      (record.order_ticket=="" ? "-" : record.order_ticket)+"\t"+
      (record.deal_ticket=="" ? "-" : record.deal_ticket)+"\t"+
      record.command_json+"\t"+(record.outcome_json=="" ? "-" : record.outcome_json);
   line=payload+"\t"+ScxeChecksumText(payload)+"\n";
   return StringLen(line)<=262144;
  }

bool ScxeParseRecord(const string line,ScxeLedgerRecord &record)
  {
   ZeroMemory(record);
   string fields[];
   int count=StringSplit(line,9,fields);
   if(count!=14 || fields[0]!="SCXL1") return false;
   string payload=fields[0];
   for(int i=1;i<13;i++) payload+="\t"+fields[i];
   ulong supplied=0;
   if(!ScxeHexChecksum(fields[13],supplied) || supplied!=ScxeChecksum(payload)) return false;
   long sequence=0,history_from=0,retcode=0,external=0,request=0;
   if(!ScxeSignedLong(fields[1],sequence) || sequence<1 || !ScxeStage(fields[2]) ||
      !ScxeSignedLong(fields[4],history_from) || history_from<=0 ||
      !ScxeSignedLong(fields[7],external) || external<-2147483648 ||
      external>2147483647) return false;
   datetime observed;
   if(!ScxUtcTimestamp(fields[3],observed) ||
      (fields[5]!="0" && fields[5]!="1")) return false;
   bool has_retcode=(fields[6]!="-"),has_request=(fields[8]!="-");
   if((has_retcode && (!ScxeSignedLong(fields[6],retcode) || retcode<0)) ||
      (has_request && (!ScxeSignedLong(fields[8],request) || request<0 ||
                       request>4294967295))) return false;
   string order=(fields[9]=="-" ? "" : fields[9]);
   string deal=(fields[10]=="-" ? "" : fields[10]);
   string outcome=(fields[12]=="-" ? "" : fields[12]);
   if((order!="" && !ScxSafeIdentifier(order,128)) ||
      (deal!="" && !ScxSafeIdentifier(deal,128)) ||
      !ScxeAsciiLine(fields[11],SCX_MAX_COMMAND_BYTES) ||
      (outcome!="" && !ScxeAsciiLine(outcome,262144))) return false;
   ScxCommand command;
   if(!ScxCommandJson(fields[11],command)) return false;
   record.present=true; record.sequence=sequence; record.stage=fields[2];
   record.observed_at=fields[3]; record.history_from=history_from;
   record.send_attempted=(fields[5]=="1");
   record.has_retcode=has_retcode; record.retcode=retcode;
   record.retcode_external=external; record.has_request_id=has_request;
   record.request_id=request; record.order_ticket=order; record.deal_ticket=deal;
   record.command_json=fields[11]; record.outcome_json=outcome; record.command=command;
   return ScxeRecordStageShape(record);
  }

void ScxeApplyRecord(ScxeLedgerBook &book,const ScxeLedgerRecord &next,bool &valid)
  {
   if(!valid || next.sequence!=book.sequence+1) { valid=false; return; }
   ScxeLedgerRecord previous;
   bool has_previous=false;
   if(next.command.operation=="open")
     {
      if(book.has_entry &&
         book.entry.command.command_id==next.command.command_id)
        { previous=book.entry; has_previous=true; }
      else
        {
         if(next.stage!="PREPARED" ||
            (book.has_entry && ScxeUnresolvedStage(book.entry.stage)) ||
            (book.has_management && ScxeUnresolvedStage(book.management.stage)))
           { valid=false; return; }
         book.has_management=false;
        }
      if(has_previous &&
         (!ScxeSameCommand(previous.command,next.command) ||
          previous.command_json!=next.command_json ||
          previous.observed_at!=next.observed_at ||
          previous.history_from!=next.history_from ||
          (next.stage=="OUTCOME_ACKED" &&
           previous.outcome_json!=next.outcome_json) ||
          !ScxeTransition(previous.stage,next.stage))) { valid=false; return; }
      if(!has_previous && !ScxeTransition("",next.stage)) { valid=false; return; }
      book.entry=next; book.has_entry=true;
     }
   else
     {
      if(!book.has_entry ||
         next.command.target_command_id!=book.entry.command.command_id)
        { valid=false; return; }
      if(book.has_management &&
         book.management.command.command_id==next.command.command_id)
        { previous=book.management; has_previous=true; }
      else if(book.has_management && ScxeUnresolvedStage(book.management.stage))
        { valid=false; return; }
      if(has_previous &&
         (!ScxeSameCommand(previous.command,next.command) ||
          previous.command_json!=next.command_json ||
          previous.observed_at!=next.observed_at ||
          previous.history_from!=next.history_from ||
          (next.stage=="OUTCOME_ACKED" &&
           previous.outcome_json!=next.outcome_json) ||
          !ScxeTransition(previous.stage,next.stage))) { valid=false; return; }
      if(!has_previous && !ScxeTransition("",next.stage)) { valid=false; return; }
      book.management=next; book.has_management=true;
     }
   book.sequence=next.sequence;
  }

bool ScxeLedgerLoad(const int handle,ScxeLedgerBook &book)
  {
   ZeroMemory(book);
   if(handle==INVALID_HANDLE) return false;
   ResetLastError(); FileFlush(handle);
   if(GetLastError()!=0 || !FileSeek(handle,0,SEEK_SET)) return false;
   ulong size=FileSize(handle);
   if(size>SCXE_MAX_LEDGER_BYTES) return false;
   if(size==0) return true;
   uchar bytes[];
   uint read=FileReadArray(handle,bytes,0,(uint)size);
   if(read!=size) return false;
   string text=CharArrayToString(bytes,0,(int)size,CP_UTF8);
   ArrayInitialize(bytes,0);
   if(StringLen(text)<1 || StringGetCharacter(text,StringLen(text)-1)!=10) return false;
   string lines[];
   int count=StringSplit(text,10,lines);
   if(count<2 || count-1>SCXE_MAX_LEDGER_RECORDS || lines[count-1]!="") return false;
   bool valid=true;
   for(int i=0;i<count-1;i++)
     {
      ScxeLedgerRecord record;
      if(!ScxeParseRecord(lines[i],record)) return false;
      ScxeApplyRecord(book,record,valid);
      if(!valid) return false;
     }
   return FileSeek(handle,0,SEEK_END);
  }

bool ScxeLedgerAppend(const int handle,ScxeLedgerBook &book,
                      const string stage,const string observed_at,
                      const long history_from,
                      const string command_json,const bool send_attempted,
                      const bool has_retcode,const long retcode,
                      const long retcode_external,const bool has_request_id,
                      const long request_id,const string order_ticket,
                      const string deal_ticket,const string outcome_json)
  {
   if(handle==INVALID_HANDLE || book.sequence>=SCXE_MAX_LEDGER_RECORDS) return false;
   ScxeLedgerRecord record;
   ZeroMemory(record);
   record.present=true; record.sequence=book.sequence+1; record.stage=stage;
   record.observed_at=observed_at; record.history_from=history_from;
   record.command_json=command_json;
   record.send_attempted=send_attempted; record.has_retcode=has_retcode;
   record.retcode=retcode; record.retcode_external=retcode_external;
   record.has_request_id=has_request_id; record.request_id=request_id;
   record.order_ticket=order_ticket; record.deal_ticket=deal_ticket;
   record.outcome_json=outcome_json;
   if(!ScxCommandJson(command_json,record.command)) return false;
   string payload,line;
   if(!ScxeRecordLine(record,payload,line)) return false;
   bool valid=true;
   ScxeLedgerBook candidate=book;
   ScxeApplyRecord(candidate,record,valid);
   if(!valid || !FileSeek(handle,0,SEEK_END) ||
      FileSize(handle)+(ulong)StringLen(line)>SCXE_MAX_LEDGER_BYTES) return false;
   ulong before=FileTell(handle);
   ResetLastError();
   uint written=FileWriteString(handle,line);
   FileFlush(handle);
   ulong after=FileTell(handle);
   if(GetLastError()!=0 || written!=(uint)StringLen(line) ||
      after<=before || after-before!=(ulong)StringLen(line)) return false;
   if(!FileSeek(handle,(long)before,SEEK_SET)) return false;
   uchar verification[];
   uint read=FileReadArray(handle,verification,0,written);
   string stored=CharArrayToString(verification,0,(int)read,CP_UTF8);
   ArrayInitialize(verification,0);
   ResetLastError(); FileFlush(handle);
   if(read!=written || stored!=line || GetLastError()!=0 ||
      !FileSeek(handle,0,SEEK_END)) return false;
   book=candidate;
   return true;
  }

#endif
