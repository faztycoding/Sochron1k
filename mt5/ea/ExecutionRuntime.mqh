#ifndef SOCHRON_EXECUTION_RUNTIME_MQH
#define SOCHRON_EXECUTION_RUNTIME_MQH

#include "ExecutionLedger.mqh"

#define SCXE_MAX_CURRENT_ITEMS 32
#define SCXE_MAX_HISTORY_ITEMS 256
#define SCXE_MAX_RISK_FRACTION 0.0025

struct ScxeContract
  {
   int digits,currency_digits;
   long trade_mode,order_mode,filling_mode,execution_mode;
   long stops_level,freeze_level;
   double point,tick_size,volume_min,volume_max,volume_step;
   ENUM_ORDER_TYPE_FILLING filling;
  };

struct ScxeCurrentScan
  {
   long foreign_orders,foreign_positions,owned_orders,owned_positions;
   ulong owned_order_ticket,owned_position_ticket;
   long owned_position_id;
   string fingerprint;
  };

string ScxeMarginMode(const long mode)
  {
   if(mode==ACCOUNT_MARGIN_MODE_RETAIL_NETTING) return "retail_netting";
   if(mode==ACCOUNT_MARGIN_MODE_RETAIL_HEDGING) return "retail_hedging";
   if(mode==ACCOUNT_MARGIN_MODE_EXCHANGE) return "exchange";
   return "";
  }

bool ScxeAccountInteger(const ENUM_ACCOUNT_INFO_INTEGER property,long &value)
  {
   ResetLastError(); value=AccountInfoInteger(property);
   return GetLastError()==0;
  }

bool ScxeAccountString(const ENUM_ACCOUNT_INFO_STRING property,string &value)
  {
   ResetLastError(); value=AccountInfoString(property);
   return GetLastError()==0;
  }

bool ScxeAccountDouble(const ENUM_ACCOUNT_INFO_DOUBLE property,double &value)
  {
   ResetLastError(); value=AccountInfoDouble(property);
   return GetLastError()==0 && MathIsValidNumber(value);
  }

bool ScxeSymbolInteger(const string symbol,const ENUM_SYMBOL_INFO_INTEGER property,
                       long &value)
  {
   ResetLastError(); value=SymbolInfoInteger(symbol,property);
   return GetLastError()==0;
  }

bool ScxeSymbolDouble(const string symbol,const ENUM_SYMBOL_INFO_DOUBLE property,
                      double &value)
  {
   ResetLastError(); value=SymbolInfoDouble(symbol,property);
   return GetLastError()==0 && MathIsValidNumber(value);
  }

bool ScxeConfigurationValid(const long login,const string server,const string currency,
                            const string symbol,const string executor_id,
                            const int margin_mode,const long magic,
                            const int spread_points,const int deviation_points,
                            const int quote_age_seconds)
  {
   return login>0 && ScxSafeIdentifier(server,128) && ScxCurrency(currency) &&
      ScxSafeIdentifier(symbol,32) && ScxSafeIdentifier(executor_id,128) &&
      ScxeMarginMode(margin_mode)!="" && magic>0 && magic<=2147483647 &&
      spread_points>0 && spread_points<=100000 && deviation_points>=0 &&
      deviation_points<=100000 && quote_age_seconds>=1 && quote_age_seconds<=5;
  }

bool ScxeIdentityMatches(const long login,const string server,const string currency,
                         const string symbol,const int margin_mode)
  {
   long actual_mode,actual_login,actual_margin;
   string actual_server,actual_currency;
   return TerminalInfoInteger(TERMINAL_CONNECTED) && _Symbol==symbol &&
      ScxeAccountInteger(ACCOUNT_TRADE_MODE,actual_mode) &&
      actual_mode==ACCOUNT_TRADE_MODE_DEMO &&
      ScxeAccountInteger(ACCOUNT_LOGIN,actual_login) && actual_login==login &&
      ScxeAccountString(ACCOUNT_SERVER,actual_server) && actual_server==server &&
      ScxeAccountString(ACCOUNT_CURRENCY,actual_currency) && actual_currency==currency &&
      ScxeAccountInteger(ACCOUNT_MARGIN_MODE,actual_margin) &&
      actual_margin==margin_mode;
  }

bool ScxeTradingAllowed()
  {
   long account_allowed,expert_allowed;
   return TerminalInfoInteger(TERMINAL_CONNECTED) &&
      TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) &&
      MQLInfoInteger(MQL_TRADE_ALLOWED) &&
      ScxeAccountInteger(ACCOUNT_TRADE_ALLOWED,account_allowed) && account_allowed &&
      ScxeAccountInteger(ACCOUNT_TRADE_EXPERT,expert_allowed) && expert_allowed;
  }

bool ScxeReadContract(const string symbol,ScxeContract &contract)
  {
   ZeroMemory(contract);
   long digits,currency_digits;
   if(!ScxeSymbolInteger(symbol,SYMBOL_DIGITS,digits) || digits<0 || digits>10 ||
      !ScxeAccountInteger(ACCOUNT_CURRENCY_DIGITS,currency_digits) ||
      currency_digits<0 || currency_digits>10 ||
      !ScxeSymbolInteger(symbol,SYMBOL_TRADE_MODE,contract.trade_mode) ||
      !ScxeSymbolInteger(symbol,SYMBOL_ORDER_MODE,contract.order_mode) ||
      !ScxeSymbolInteger(symbol,SYMBOL_FILLING_MODE,contract.filling_mode) ||
      !ScxeSymbolInteger(symbol,SYMBOL_TRADE_EXEMODE,contract.execution_mode) ||
      !ScxeSymbolInteger(symbol,SYMBOL_TRADE_STOPS_LEVEL,contract.stops_level) ||
      !ScxeSymbolInteger(symbol,SYMBOL_TRADE_FREEZE_LEVEL,contract.freeze_level) ||
      !ScxeSymbolDouble(symbol,SYMBOL_POINT,contract.point) ||
      !ScxeSymbolDouble(symbol,SYMBOL_TRADE_TICK_SIZE,contract.tick_size) ||
      !ScxeSymbolDouble(symbol,SYMBOL_VOLUME_MIN,contract.volume_min) ||
      !ScxeSymbolDouble(symbol,SYMBOL_VOLUME_MAX,contract.volume_max) ||
      !ScxeSymbolDouble(symbol,SYMBOL_VOLUME_STEP,contract.volume_step)) return false;
   contract.digits=(int)digits; contract.currency_digits=(int)currency_digits;
   if(contract.trade_mode!=SYMBOL_TRADE_MODE_FULL ||
      (contract.order_mode&SYMBOL_ORDER_MARKET)!=SYMBOL_ORDER_MARKET ||
      (contract.order_mode&SYMBOL_ORDER_SL)!=SYMBOL_ORDER_SL ||
      contract.point<=0 || contract.tick_size<=0 || contract.volume_min<=0 ||
      contract.volume_max<contract.volume_min || contract.volume_step<=0 ||
      contract.stops_level<0 || contract.freeze_level<0) return false;
   if((contract.filling_mode&SYMBOL_FILLING_FOK)==SYMBOL_FILLING_FOK)
      contract.filling=ORDER_FILLING_FOK;
   else if((contract.filling_mode&SYMBOL_FILLING_IOC)==SYMBOL_FILLING_IOC)
      contract.filling=ORDER_FILLING_IOC;
   else if(contract.execution_mode!=SYMBOL_TRADE_EXECUTION_MARKET)
      contract.filling=ORDER_FILLING_RETURN;
   else return false;
   return true;
  }

bool ScxeGridValue(const double value,const double step)
  {
   if(!MathIsValidNumber(value) || !MathIsValidNumber(step) || value<=0 || step<=0)
      return false;
   double units=value/step,nearest=MathRound(units);
   return MathIsValidNumber(units) && MathIsValidNumber(nearest) &&
      MathAbs(units-nearest)<=0.0000001;
  }

bool ScxeSessionOpen(const string symbol,const datetime server_time)
  {
   MqlDateTime now;
   if(!TimeToStruct(server_time,now)) return false;
   int current=now.hour*3600+now.min*60+now.sec;
   for(uint index=0;index<32;index++)
     {
      datetime from,to;
      ResetLastError();
      if(!SymbolInfoSessionTrade(symbol,(ENUM_DAY_OF_WEEK)now.day_of_week,index,from,to))
        {
         if(GetLastError()!=0) return false;
         break;
        }
      MqlDateTime start,finish;
      if(!TimeToStruct(from,start) || !TimeToStruct(to,finish)) return false;
      int a=start.hour*3600+start.min*60+start.sec;
      int b=finish.hour*3600+finish.min*60+finish.sec;
      if(a==b || (a<b && current>=a && current<b) ||
         (a>b && (current>=a || current<b))) return true;
     }
   return false;
  }

bool ScxeFreshTick(const string symbol,const int maximum_age_seconds,
                   MqlTick &tick,datetime &server_time)
  {
   ResetLastError();
   if(!SymbolInfoTick(symbol,tick) || GetLastError()!=0 || tick.time_msc<=0 ||
      !MathIsValidNumber(tick.bid) || !MathIsValidNumber(tick.ask) ||
      tick.bid<=0 || tick.ask<=tick.bid) return false;
   server_time=TimeTradeServer();
   if(server_time<=0) return false;
   long age=(long)server_time*1000-tick.time_msc;
   return age>=0 && age<=(long)maximum_age_seconds*1000 &&
      ScxeSessionOpen(symbol,server_time);
  }

bool ScxeAppendFingerprint(string &fingerprint,const string kind,const ulong ticket,
                           const string symbol,const long magic,const string detail)
  {
   if(ticket==0 || StringLen(symbol)<1 || StringLen(symbol)>64 ||
      StringLen(detail)>512 || StringLen(fingerprint)>8192) return false;
   fingerprint+=kind+":"+StringFormat("%I64u",ticket)+":"+
      IntegerToString(magic)+":"+symbol+":"+detail+"|";
   return StringLen(fingerprint)<=16384;
  }

bool ScxeReadCurrent(const string symbol,const long magic,ScxeCurrentScan &scan)
  {
   ZeroMemory(scan);
   int orders=OrdersTotal(),positions=PositionsTotal();
   if(orders<0 || positions<0 || orders+positions>SCXE_MAX_CURRENT_ITEMS) return false;
   scan.fingerprint="orders:"+IntegerToString(orders)+"|positions:"+
      IntegerToString(positions)+"|";
   for(int i=0;i<orders;i++)
     {
      ulong ticket=OrderGetTicket(i);
      if(ticket==0) return false;
      string item_symbol=OrderGetString(ORDER_SYMBOL);
      long item_magic=OrderGetInteger(ORDER_MAGIC);
      double initial=OrderGetDouble(ORDER_VOLUME_INITIAL);
      double current=OrderGetDouble(ORDER_VOLUME_CURRENT);
      double price=OrderGetDouble(ORDER_PRICE_OPEN);
      double stop=OrderGetDouble(ORDER_SL);
      if(!MathIsValidNumber(initial) || !MathIsValidNumber(current) ||
         !MathIsValidNumber(price) || !MathIsValidNumber(stop) ||
         !ScxeAppendFingerprint(scan.fingerprint,"order",ticket,item_symbol,item_magic,
            IntegerToString(OrderGetInteger(ORDER_TYPE))+":"+
            IntegerToString(OrderGetInteger(ORDER_STATE))+":"+
            DoubleToString(initial,16)+":"+DoubleToString(current,16)+":"+
            DoubleToString(price,16)+":"+DoubleToString(stop,16)))
         return false;
      if(item_symbol==symbol && item_magic==magic)
        {
         scan.owned_orders++;
         if(scan.owned_orders==1) scan.owned_order_ticket=ticket;
        }
      else scan.foreign_orders++;
     }
   for(int i=0;i<positions;i++)
     {
      ulong ticket=PositionGetTicket(i);
      if(ticket==0) return false;
      string item_symbol=PositionGetString(POSITION_SYMBOL);
      long item_magic=PositionGetInteger(POSITION_MAGIC);
      double volume=PositionGetDouble(POSITION_VOLUME);
      double stop=PositionGetDouble(POSITION_SL);
      long position_id=PositionGetInteger(POSITION_IDENTIFIER);
      if(!MathIsValidNumber(volume) || !MathIsValidNumber(stop) ||
         !ScxeAppendFingerprint(scan.fingerprint,"position",ticket,item_symbol,item_magic,
            IntegerToString(PositionGetInteger(POSITION_TYPE))+":"+
            IntegerToString(position_id)+":"+DoubleToString(volume,16)+":"+
            DoubleToString(stop,16)))
         return false;
      if(item_symbol==symbol && item_magic==magic)
        {
         scan.owned_positions++;
         if(scan.owned_positions==1)
           {
            scan.owned_position_ticket=ticket;
            scan.owned_position_id=position_id;
           }
        }
      else scan.foreign_positions++;
     }
   return scan.owned_orders<=1 && scan.owned_positions<=1;
  }

bool ScxeStableCurrent(const string symbol,const long magic,ScxeCurrentScan &scan)
  {
   ScxeCurrentScan first,second;
   if(!ScxeReadCurrent(symbol,magic,first) || !ScxeReadCurrent(symbol,magic,second) ||
      first.fingerprint!=second.fingerprint ||
      first.foreign_orders!=second.foreign_orders ||
      first.foreign_positions!=second.foreign_positions ||
      first.owned_orders!=second.owned_orders ||
      first.owned_positions!=second.owned_positions) return false;
   scan=second;
   return true;
  }

bool ScxePreflightOpen(const ScxCommand &command,const string symbol,
                       const int spread_points,const int deviation_points,
                       const int quote_age_seconds,ScxeContract &contract,
                       MqlTick &tick,MqlTradeRequest &request,double &loss,
                       double &margin)
  {
   ZeroMemory(request); loss=0; margin=0;
   datetime server_time;
   ScxeCurrentScan current;
   if(command.operation!="open" || !ScxeTradingAllowed() ||
      !ScxeStableCurrent(symbol,command.magic_number,current) ||
      current.foreign_orders!=0 || current.foreign_positions!=0 ||
      current.owned_orders!=0 || current.owned_positions!=0 ||
      !ScxeReadContract(symbol,contract) ||
      !ScxeFreshTick(symbol,quote_age_seconds,tick,server_time) ||
      !ScxeGridValue(command.volume,contract.volume_step) ||
      command.volume<contract.volume_min || command.volume>contract.volume_max ||
      !ScxeGridValue(command.requested_entry,contract.tick_size) ||
      !ScxeGridValue(command.stop_loss,contract.tick_size) ||
      (command.has_take_profit && !ScxeGridValue(command.take_profit,contract.tick_size)))
      return false;
   double spread=(tick.ask-tick.bid)/contract.point;
   if(!MathIsValidNumber(spread) || spread<0 || spread>spread_points) return false;
   bool buy=(command.side=="buy");
   double entry=buy ? tick.ask : tick.bid;
   if(!ScxeGridValue(entry,contract.tick_size) ||
      MathAbs(entry-command.requested_entry)>
      (double)deviation_points*contract.point+contract.tick_size*0.0000001)
      return false;
   double minimum=(double)MathMax(contract.stops_level,contract.freeze_level)*contract.point;
   if((buy && (command.stop_loss>=entry ||
               entry-command.stop_loss<minimum ||
               (command.has_take_profit &&
                (command.take_profit<=entry ||
                 command.take_profit-entry<minimum)))) ||
      (!buy && (command.stop_loss<=entry ||
                command.stop_loss-entry<minimum ||
                (command.has_take_profit &&
                 (command.take_profit>=entry ||
                  entry-command.take_profit<minimum))))) return false;
   ENUM_ORDER_TYPE type=buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   double risk_entry=buy ? entry+(double)deviation_points*contract.point :
      entry-(double)deviation_points*contract.point;
   if(!MathIsValidNumber(risk_entry) || risk_entry<=0) return false;
   double risk_units=risk_entry/contract.tick_size;
   if(!MathIsValidNumber(risk_units)) return false;
   risk_entry=(buy ? MathCeil(risk_units) : MathFloor(risk_units))*contract.tick_size;
   if(!MathIsValidNumber(risk_entry) || risk_entry<=0) return false;
   ResetLastError();
   double profit=0;
   if(!OrderCalcProfit(type,symbol,command.volume,risk_entry,command.stop_loss,profit) ||
      GetLastError()!=0 || !MathIsValidNumber(profit) || profit>=0) return false;
   double scale=MathPow(10.0,contract.currency_digits);
   if(!MathIsValidNumber(scale) || scale<1) return false;
   loss=MathCeil((-profit)*scale)/scale;
   double equity;
   if(!ScxeAccountDouble(ACCOUNT_EQUITY,equity) || equity<=0) return false;
   double hard_risk=MathFloor(equity*SCXE_MAX_RISK_FRACTION*scale)/scale;
   double total_risk=loss+command.cost_budget;
   if(!MathIsValidNumber(loss) || loss<=0 || !MathIsValidNumber(hard_risk) ||
      hard_risk<=0 || !MathIsValidNumber(total_risk) ||
      total_risk>command.risk_limit || total_risk>hard_risk) return false;
   ResetLastError();
   if(!OrderCalcMargin(type,symbol,command.volume,risk_entry,margin) ||
      GetLastError()!=0 || !MathIsValidNumber(margin) || margin<=0) return false;
   double free_margin;
   if(!ScxeAccountDouble(ACCOUNT_MARGIN_FREE,free_margin) ||
      free_margin<=0 || margin>free_margin) return false;
   request.action=TRADE_ACTION_DEAL; request.magic=(ulong)command.magic_number;
   request.symbol=symbol; request.volume=command.volume; request.type=type;
   request.price=entry; request.sl=command.stop_loss;
   request.tp=command.has_take_profit ? command.take_profit : 0;
   request.deviation=(ulong)deviation_points; request.type_filling=contract.filling;
   request.type_time=ORDER_TIME_GTC;
   request.comment="scx:"+StringSubstr(command.command_id,0,20);
   return true;
  }

bool ScxePreflightCancel(const ScxCommand &command,const string symbol,const long magic,
                         MqlTradeRequest &request)
  {
   ZeroMemory(request);
   ScxeCurrentScan current;
   if(command.operation!="cancel" || !command.has_broker_order_ticket ||
      !ScxeTradingAllowed() || !ScxeStableCurrent(symbol,magic,current) ||
      current.foreign_orders!=0 || current.foreign_positions!=0 ||
      current.owned_orders!=1) return false;
   ulong ticket=(ulong)StringToInteger(command.broker_order_ticket);
   if(ticket==0 || current.owned_order_ticket!=ticket || !OrderSelect(ticket) ||
      OrderGetString(ORDER_SYMBOL)!=symbol ||
      OrderGetInteger(ORDER_MAGIC)!=magic ||
      !ScxDecimalEqual(OrderGetDouble(ORDER_VOLUME_CURRENT),command.volume)) return false;
   request.action=TRADE_ACTION_REMOVE; request.magic=(ulong)magic;
   request.order=ticket; request.symbol=symbol;
   request.comment="scx:"+StringSubstr(command.command_id,0,20);
   return true;
  }

bool ScxeFindPosition(const string symbol,const long magic,const string identifier,
                      ulong &ticket,long &position_id,long &position_type,
                      double &volume)
  {
   int total=PositionsTotal(),matches=0;
   ticket=0; position_id=0; position_type=-1; volume=0;
   if(total<0 || total>SCXE_MAX_CURRENT_ITEMS) return false;
   for(int i=0;i<total;i++)
     {
      ulong candidate=PositionGetTicket(i);
      if(candidate==0 || PositionGetString(POSITION_SYMBOL)!=symbol ||
         PositionGetInteger(POSITION_MAGIC)!=magic) continue;
      long id=PositionGetInteger(POSITION_IDENTIFIER);
      if(IntegerToString(id)!=identifier) continue;
      matches++; ticket=candidate; position_id=id;
      position_type=PositionGetInteger(POSITION_TYPE);
      volume=PositionGetDouble(POSITION_VOLUME);
     }
   return matches==1 && ticket>0 && position_id>0 &&
      (position_type==POSITION_TYPE_BUY || position_type==POSITION_TYPE_SELL) &&
      MathIsValidNumber(volume) && volume>0;
  }

bool ScxePreflightClose(const ScxCommand &command,const string symbol,const long magic,
                        const int deviation_points,const int quote_age_seconds,
                        MqlTradeRequest &request)
  {
   ZeroMemory(request);
   if(command.operation!="close" || !command.has_position_id ||
      !ScxeTradingAllowed()) return false;
   ulong position_ticket;
   long position_id,position_type;
   double current_volume;
   ScxeCurrentScan current;
   if(!ScxeStableCurrent(symbol,magic,current) || current.foreign_orders!=0 ||
      current.foreign_positions!=0 || current.owned_orders!=0 ||
      current.owned_positions!=1 ||
      !ScxeFindPosition(symbol,magic,command.position_id,position_ticket,position_id,
      position_type,current_volume) || !ScxDecimalEqual(command.volume,current_volume))
      return false;
   ScxeContract contract;
   MqlTick tick;
   datetime server_time;
   if(!ScxeReadContract(symbol,contract) ||
      !ScxeFreshTick(symbol,quote_age_seconds,tick,server_time) ||
      !ScxeGridValue(command.volume,contract.volume_step)) return false;
   bool close_buy=(position_type==POSITION_TYPE_SELL);
   request.action=TRADE_ACTION_DEAL; request.magic=(ulong)magic;
   request.position=position_ticket; request.symbol=symbol; request.volume=command.volume;
   request.type=close_buy ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   request.price=close_buy ? tick.ask : tick.bid;
   request.deviation=(ulong)deviation_points; request.type_filling=contract.filling;
   request.type_time=ORDER_TIME_GTC;
   request.comment="scx:"+StringSubstr(command.command_id,0,20);
   return true;
  }

bool ScxeTicketText(const ulong ticket,string &value)
  {
   if(ticket==0 || ticket>9223372036854775807) return false;
   value=StringFormat("%I64u",ticket);
   return ScxSafeIdentifier(value,128);
  }

bool ScxeHistoryFingerprint(const string symbol,const long magic,const datetime since,
                            string &fingerprint)
  {
   fingerprint="";
   datetime until=TimeTradeServer()+60;
   if(since<=0 || until<=since || !HistorySelect(since,until)) return false;
   int orders=HistoryOrdersTotal(),deals=HistoryDealsTotal();
   if(orders<0 || deals<0 || orders>SCXE_MAX_HISTORY_ITEMS ||
      deals>SCXE_MAX_HISTORY_ITEMS) return false;
   fingerprint="orders:"+IntegerToString(orders)+"|deals:"+
      IntegerToString(deals)+"|";
   for(int i=0;i<orders;i++)
     {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket==0) return false;
      string item_symbol=HistoryOrderGetString(ticket,ORDER_SYMBOL);
      long item_magic=HistoryOrderGetInteger(ticket,ORDER_MAGIC);
      if(item_symbol!=symbol || item_magic!=magic) continue;
      double initial=HistoryOrderGetDouble(ticket,ORDER_VOLUME_INITIAL);
      double current=HistoryOrderGetDouble(ticket,ORDER_VOLUME_CURRENT);
      if(!MathIsValidNumber(initial) || !MathIsValidNumber(current) ||
         !ScxeAppendFingerprint(fingerprint,"history-order",ticket,item_symbol,item_magic,
            IntegerToString(HistoryOrderGetInteger(ticket,ORDER_TYPE))+":"+
            IntegerToString(HistoryOrderGetInteger(ticket,ORDER_STATE))+":"+
            IntegerToString(HistoryOrderGetInteger(ticket,ORDER_TIME_SETUP_MSC))+":"+
            IntegerToString(HistoryOrderGetInteger(ticket,ORDER_TIME_DONE_MSC))+":"+
            DoubleToString(initial,16)+":"+DoubleToString(current,16))) return false;
     }
   for(int i=0;i<deals;i++)
     {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0) return false;
      string item_symbol=HistoryDealGetString(ticket,DEAL_SYMBOL);
      long item_magic=HistoryDealGetInteger(ticket,DEAL_MAGIC);
      if(item_symbol!=symbol || item_magic!=magic) continue;
      double volume=HistoryDealGetDouble(ticket,DEAL_VOLUME);
      double price=HistoryDealGetDouble(ticket,DEAL_PRICE);
      double profit=HistoryDealGetDouble(ticket,DEAL_PROFIT);
      double commission=HistoryDealGetDouble(ticket,DEAL_COMMISSION);
      double swap=HistoryDealGetDouble(ticket,DEAL_SWAP);
      double fee=HistoryDealGetDouble(ticket,DEAL_FEE);
      if(!MathIsValidNumber(volume) || !MathIsValidNumber(price) ||
         !MathIsValidNumber(profit) || !MathIsValidNumber(commission) ||
         !MathIsValidNumber(swap) || !MathIsValidNumber(fee) ||
         !ScxeAppendFingerprint(fingerprint,"history-deal",ticket,item_symbol,item_magic,
            IntegerToString(HistoryDealGetInteger(ticket,DEAL_ORDER))+":"+
            IntegerToString(HistoryDealGetInteger(ticket,DEAL_POSITION_ID))+":"+
            IntegerToString(HistoryDealGetInteger(ticket,DEAL_ENTRY))+":"+
            IntegerToString(HistoryDealGetInteger(ticket,DEAL_TIME_MSC))+":"+
            DoubleToString(volume,16)+":"+DoubleToString(price,16)+":"+
            DoubleToString(profit,16)+":"+DoubleToString(commission,16)+":"+
            DoubleToString(swap,16)+":"+DoubleToString(fee,16))) return false;
     }
   return StringLen(fingerprint)<=16384;
  }

bool ScxeStableHistory(const string symbol,const long magic,const datetime since)
  {
   string first,second;
   return ScxeHistoryFingerprint(symbol,magic,since,first) &&
      ScxeHistoryFingerprint(symbol,magic,since,second) && first==second;
  }

bool ScxeCollectDeals(const string symbol,const long magic,const ulong order_ticket,
                      const long position_id,const bool entries,const datetime since,
                      ScxDealEvidence &deals[],double &volume)
  {
   ArrayResize(deals,0); volume=0;
   datetime until=TimeTradeServer()+60;
   if(since<=0 || until<=since || !HistorySelect(since,until)) return false;
   int total=HistoryDealsTotal();
   if(total<0 || total>SCXE_MAX_HISTORY_ITEMS) return false;
   for(int i=0;i<total;i++)
     {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket==0 || HistoryDealGetString(ticket,DEAL_SYMBOL)!=symbol ||
         HistoryDealGetInteger(ticket,DEAL_MAGIC)!=magic) continue;
      long entry=HistoryDealGetInteger(ticket,DEAL_ENTRY);
      bool direction=entries ? (entry==DEAL_ENTRY_IN) :
         (entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY);
      if(!direction) continue;
      if(order_ticket>0 && (ulong)HistoryDealGetInteger(ticket,DEAL_ORDER)!=order_ticket)
         continue;
      if(position_id>0 && HistoryDealGetInteger(ticket,DEAL_POSITION_ID)!=position_id)
         continue;
      int next=ArraySize(deals);
      if(next>=SCX_MAX_DEALS) return false;
      ArrayResize(deals,next+1);
      string ticket_text;
      if(!ScxeTicketText(ticket,ticket_text)) return false;
      deals[next].deal_ticket=ticket_text;
      deals[next].volume=HistoryDealGetDouble(ticket,DEAL_VOLUME);
      deals[next].price=HistoryDealGetDouble(ticket,DEAL_PRICE);
      deals[next].profit=HistoryDealGetDouble(ticket,DEAL_PROFIT);
      deals[next].commission=HistoryDealGetDouble(ticket,DEAL_COMMISSION);
      deals[next].swap=HistoryDealGetDouble(ticket,DEAL_SWAP);
      deals[next].fee=HistoryDealGetDouble(ticket,DEAL_FEE);
      long time_msc=HistoryDealGetInteger(ticket,DEAL_TIME_MSC);
      deals[next].has_occurred_at=(time_msc>0);
      deals[next].occurred_at=deals[next].has_occurred_at ?
         ScUtc((datetime)(time_msc/1000)) : "";
      string validation;
      if(!ScxDealEvidenceJson(deals[next],validation)) return false;
      volume+=deals[next].volume;
      if(!MathIsValidNumber(volume)) return false;
     }
   return true;
  }

bool ScxeResolveEntryOrder(const ScxeLedgerRecord &record,const string symbol,
                           const long magic,const ScxeCurrentScan &scan,
                           ulong &order_ticket)
  {
   order_ticket=0;
   long expected_type=(record.command.side=="buy" ? ORDER_TYPE_BUY : ORDER_TYPE_SELL);
   if(record.order_ticket!="") order_ticket=(ulong)StringToInteger(record.order_ticket);
   if(order_ticket==0 && record.deal_ticket!="")
     {
      ulong deal_ticket=(ulong)StringToInteger(record.deal_ticket);
      if(HistoryDealSelect(deal_ticket) &&
         HistoryDealGetString(deal_ticket,DEAL_SYMBOL)==symbol &&
         HistoryDealGetInteger(deal_ticket,DEAL_MAGIC)==magic &&
         HistoryDealGetInteger(deal_ticket,DEAL_ENTRY)==DEAL_ENTRY_IN)
         order_ticket=(ulong)HistoryDealGetInteger(deal_ticket,DEAL_ORDER);
     }
   if(order_ticket==0 && scan.owned_order_ticket>0) order_ticket=scan.owned_order_ticket;
   if(order_ticket>0)
     {
      if(OrderSelect(order_ticket))
         return OrderGetString(ORDER_SYMBOL)==symbol &&
            OrderGetInteger(ORDER_MAGIC)==magic &&
            OrderGetInteger(ORDER_TYPE)==expected_type;
      if(!HistoryOrderSelect(order_ticket)) return false;
      return HistoryOrderGetString(order_ticket,ORDER_SYMBOL)==symbol &&
         HistoryOrderGetInteger(order_ticket,ORDER_MAGIC)==magic &&
         HistoryOrderGetInteger(order_ticket,ORDER_TYPE)==expected_type;
     }
   datetime since=(datetime)record.history_from;
   if(since<=0 || !HistorySelect(since-60,TimeTradeServer()+60)) return false;
   int total=HistoryOrdersTotal(),matches=0;
   if(total<0 || total>SCXE_MAX_HISTORY_ITEMS) return false;
   for(int i=0;i<total;i++)
     {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket==0 || HistoryOrderGetString(ticket,ORDER_SYMBOL)!=symbol ||
         HistoryOrderGetInteger(ticket,ORDER_MAGIC)!=magic ||
         HistoryOrderGetInteger(ticket,ORDER_TYPE)!=expected_type) continue;
      long setup_msc=HistoryOrderGetInteger(ticket,ORDER_TIME_SETUP_MSC);
      if(setup_msc<(long)(since-60)*1000) continue;
      matches++; order_ticket=ticket;
     }
   return matches==1 && order_ticket>0;
  }

bool ScxeBuildEntryEvidence(const ScxeLedgerRecord &record,const string symbol,
                            const long magic,const ScxeCurrentScan &scan,
                            ScxBrokerEvidence &snapshot)
  {
   ZeroMemory(snapshot);
   if(!record.present || record.command.operation!="open") return false;
   datetime since=(datetime)record.history_from;
   if(since<=0 || !ScxeStableHistory(symbol,magic,since-60)) return false;
   ulong order_ticket;
   if(!ScxeResolveEntryOrder(record,symbol,magic,scan,order_ticket) ||
      !ScxeTicketText(order_ticket,snapshot.order_ticket)) return false;
   long position_id=scan.owned_position_id;
   ScxDealEvidence entry_deals[];
   double filled=0;
   if(!ScxeCollectDeals(symbol,magic,order_ticket,0,true,since-60,entry_deals,filled))
      return false;
   long deal_position_id=0;
   for(int i=0;i<ArraySize(entry_deals);i++)
     {
      ulong deal_ticket=(ulong)StringToInteger(entry_deals[i].deal_ticket);
      long candidate=HistoryDealGetInteger(deal_ticket,DEAL_POSITION_ID);
      if(candidate<=0 || (deal_position_id>0 && candidate!=deal_position_id)) return false;
      deal_position_id=candidate;
     }
   if(position_id<=0 && ArraySize(entry_deals)>0)
      position_id=deal_position_id;
   if(position_id>0 && deal_position_id>0 && position_id!=deal_position_id) return false;
   ScxDealEvidence exit_deals[];
   double closed=0;
   if(position_id>0 &&
      !ScxeCollectDeals(symbol,magic,0,position_id,false,since-60,exit_deals,closed))
      return false;
   double remaining=0;
   bool active=(scan.owned_order_ticket==order_ticket && OrderSelect(order_ticket));
   if(active) remaining=OrderGetDouble(ORDER_VOLUME_CURRENT);
   else
     {
      if(!HistoryOrderSelect(order_ticket)) return false;
      long state=HistoryOrderGetInteger(order_ticket,ORDER_STATE);
      bool terminal_cancel=state==ORDER_STATE_CANCELED || state==ORDER_STATE_REJECTED ||
         state==ORDER_STATE_EXPIRED;
      if(!terminal_cancel && state!=ORDER_STATE_FILLED) return false;
      if(state==ORDER_STATE_FILLED && !ScxDecimalEqual(filled,record.command.volume))
         return false;
     }
   if(!MathIsValidNumber(remaining) || remaining<0) return false;
   double cancelled=record.command.volume-filled-remaining;
   if(cancelled<0 && MathAbs(cancelled)<=0.00000000005) cancelled=0;
   snapshot.command_id=record.command.command_id;
   snapshot.requested_volume=record.command.volume;
   snapshot.filled_volume=filled; snapshot.remaining_volume=remaining;
   snapshot.cancelled_volume=cancelled; snapshot.closed_volume=closed;
   ArrayResize(snapshot.deals,ArraySize(entry_deals));
   for(int i=0;i<ArraySize(entry_deals);i++) snapshot.deals[i]=entry_deals[i];
   snapshot.has_position_id=(position_id>0);
   snapshot.position_id=snapshot.has_position_id ? IntegerToString(position_id) : "";
   snapshot.stop_loss_confirmed=false;
   if(scan.owned_position_ticket>0 && PositionSelectByTicket(scan.owned_position_ticket))
     {
      double actual_sl=PositionGetDouble(POSITION_SL);
      snapshot.stop_loss_confirmed=actual_sl>0 &&
         ScxDecimalEqual(actual_sl,record.command.stop_loss);
     }
   snapshot.has_terminal_state=false; snapshot.terminal_state="";
   if(ScxDecimalEqual(filled,0) && ScxDecimalEqual(remaining,0) && cancelled>0)
     { snapshot.has_terminal_state=true; snapshot.terminal_state="cancelled"; }
   else if(filled>0 && ScxDecimalEqual(closed,filled) && ScxDecimalEqual(remaining,0))
     { snapshot.has_terminal_state=true; snapshot.terminal_state="closed";
       snapshot.stop_loss_confirmed=false; }
   string validation;
   return ScxBrokerEvidenceJson(snapshot,validation);
  }

bool ScxeResolveExitOrder(const ScxeLedgerRecord &record,const string symbol,
                          const long magic,const datetime since,ulong &order_ticket)
  {
   order_ticket=(record.order_ticket=="" ? 0 :
      (ulong)StringToInteger(record.order_ticket));
   long position_id=StringToInteger(record.command.position_id);
   if(order_ticket==0 && record.deal_ticket!="")
     {
      ulong deal_ticket=(ulong)StringToInteger(record.deal_ticket);
      long entry=HistoryDealSelect(deal_ticket) ?
         HistoryDealGetInteger(deal_ticket,DEAL_ENTRY) : -1;
      if((entry==DEAL_ENTRY_OUT || entry==DEAL_ENTRY_OUT_BY) &&
         HistoryDealGetString(deal_ticket,DEAL_SYMBOL)==symbol &&
         HistoryDealGetInteger(deal_ticket,DEAL_MAGIC)==magic &&
         HistoryDealGetInteger(deal_ticket,DEAL_POSITION_ID)==position_id)
         order_ticket=(ulong)HistoryDealGetInteger(deal_ticket,DEAL_ORDER);
     }
   if(order_ticket==0)
     {
      if(!HistorySelect(since-60,TimeTradeServer()+60)) return false;
      int total=HistoryDealsTotal();
      if(total<0 || total>SCXE_MAX_HISTORY_ITEMS) return false;
      for(int i=0;i<total;i++)
        {
         ulong deal_ticket=HistoryDealGetTicket(i);
         if(deal_ticket==0 || HistoryDealGetString(deal_ticket,DEAL_SYMBOL)!=symbol ||
            HistoryDealGetInteger(deal_ticket,DEAL_MAGIC)!=magic ||
            HistoryDealGetInteger(deal_ticket,DEAL_POSITION_ID)!=position_id) continue;
         long entry=HistoryDealGetInteger(deal_ticket,DEAL_ENTRY);
         if(entry!=DEAL_ENTRY_OUT && entry!=DEAL_ENTRY_OUT_BY) continue;
         ulong candidate=(ulong)HistoryDealGetInteger(deal_ticket,DEAL_ORDER);
         if(candidate==0 || (order_ticket>0 && order_ticket!=candidate)) return false;
         order_ticket=candidate;
        }
     }
   if(order_ticket==0) return false;
   if(OrderSelect(order_ticket))
      return OrderGetString(ORDER_SYMBOL)==symbol &&
         OrderGetInteger(ORDER_MAGIC)==magic &&
         OrderGetInteger(ORDER_POSITION_ID)==position_id;
   if(!HistoryOrderSelect(order_ticket)) return false;
   return HistoryOrderGetString(order_ticket,ORDER_SYMBOL)==symbol &&
      HistoryOrderGetInteger(order_ticket,ORDER_MAGIC)==magic &&
      HistoryOrderGetInteger(order_ticket,ORDER_POSITION_ID)==position_id;
  }

bool ScxeBuildManagementEvidence(const ScxeLedgerRecord &record,
                                 const ScxBrokerEvidence &target,
                                 const string symbol,const long magic,
                                 ScxManagementEvidence &snapshot)
  {
   ZeroMemory(snapshot);
   if(!record.present || record.command.operation=="open") return false;
   datetime since=(datetime)record.history_from;
   if(since<=0 || !ScxeStableHistory(symbol,magic,since-60)) return false;
   snapshot.command_id=record.command.command_id;
   snapshot.target_command_id=record.command.target_command_id;
   snapshot.operation=record.command.operation;
   snapshot.position_id=record.command.has_position_id ? record.command.position_id : "";
   snapshot.has_position_id=record.command.has_position_id;
   snapshot.requested_volume=record.command.volume;
   snapshot.observed_at=ScUtc(TimeGMT());
   if(record.command.operation=="cancel")
     {
      snapshot.broker_order_ticket=record.command.broker_order_ticket;
      snapshot.completed_volume=record.command.volume-target.remaining_volume;
      snapshot.remaining_volume=target.remaining_volume;
      ArrayResize(snapshot.deals,0);
      snapshot.has_terminal_state=ScxDecimalEqual(snapshot.remaining_volume,0);
      snapshot.terminal_state=snapshot.has_terminal_state ? "cancelled" : "";
     }
   else
     {
      ulong exit_order;
      if(!ScxeResolveExitOrder(record,symbol,magic,since,exit_order) ||
         !ScxeTicketText(exit_order,snapshot.broker_order_ticket))
         return false;
      long position_id=StringToInteger(record.command.position_id);
      ScxDealEvidence exits[];
      double completed=0;
      if(!ScxeCollectDeals(symbol,magic,exit_order,position_id,false,since-60,
         exits,completed)) return false;
      snapshot.completed_volume=completed;
      snapshot.remaining_volume=record.command.volume-completed;
      if(snapshot.remaining_volume<0 && MathAbs(snapshot.remaining_volume)<=0.00000000005)
         snapshot.remaining_volume=0;
      ArrayResize(snapshot.deals,ArraySize(exits));
      for(int i=0;i<ArraySize(exits);i++) snapshot.deals[i]=exits[i];
      snapshot.has_terminal_state=ScxDecimalEqual(snapshot.remaining_volume,0);
      snapshot.terminal_state=snapshot.has_terminal_state ? "closed" : "";
     }
   snapshot.target=target;
   string validation;
   return ScxManagementEvidenceJson(snapshot,validation);
  }

bool ScxeNoEffectSince(const string symbol,const long magic,const string operation,
                       const datetime since)
  {
   ScxeCurrentScan scan;
   if(!ScxeStableCurrent(symbol,magic,scan) ||
      (operation=="open" && (scan.owned_orders!=0 || scan.owned_positions!=0)) ||
      !ScxeStableHistory(symbol,magic,since) ||
      !HistorySelect(since,TimeTradeServer()+60)) return false;
   int orders=HistoryOrdersTotal(),deals=HistoryDealsTotal();
   if(orders<0 || deals<0 || orders>SCXE_MAX_HISTORY_ITEMS ||
      deals>SCXE_MAX_HISTORY_ITEMS) return false;
   for(int i=0;i<orders;i++)
     {
      ulong ticket=HistoryOrderGetTicket(i);
      if(ticket>0 && HistoryOrderGetString(ticket,ORDER_SYMBOL)==symbol &&
         HistoryOrderGetInteger(ticket,ORDER_MAGIC)==magic &&
         HistoryOrderGetInteger(ticket,ORDER_TIME_SETUP)>=since) return false;
     }
   for(int i=0;i<deals;i++)
     {
      ulong ticket=HistoryDealGetTicket(i);
      if(ticket>0 && HistoryDealGetString(ticket,DEAL_SYMBOL)==symbol &&
         HistoryDealGetInteger(ticket,DEAL_MAGIC)==magic &&
         HistoryDealGetInteger(ticket,DEAL_TIME)>=since) return false;
     }
   return true;
  }

bool ScxeBuildRejectionEvidence(const ScxeLedgerRecord &record,const string symbol,
                                const long magic,ScxRejectionEvidence &rejection)
  {
   ZeroMemory(rejection);
   if(!record.present || !record.has_retcode ||
      !ScxNoEffectRetcode(record.retcode) ||
      record.history_from<=0 || !ScxeNoEffectSince(symbol,magic,
         record.command.operation,(datetime)record.history_from)) return false;
   rejection.command_id=record.command.command_id;
   rejection.has_target=record.command.has_target;
   rejection.target_command_id=record.command.target_command_id;
   rejection.operation=record.command.operation;
   rejection.retcode=record.retcode;
   rejection.retcode_external=record.retcode_external;
   rejection.request_id=record.has_request_id ? record.request_id : 0;
   rejection.observed_at=ScUtc(TimeGMT());
   string validation;
   return ScxRejectionEvidenceJson(rejection,validation);
  }

#endif
