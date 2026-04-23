//+------------------------------------------------------------------+
//| ClaudeBridge.mq5 - File-based bridge entre Claude y MT5          |
//| Escribe/lee JSON en MQL5/Files/ para integración con Claude Code  |
//| Autor: Trading Project                                            |
//| Versión: 1.00                                                     |
//+------------------------------------------------------------------+
#property copyright "Trading Project"
#property version   "1.00"
#property strict

//=== INPUTS ===
input int    HeartbeatSec   = 5;                          // Timer interval en segundos
input long   Magic          = 77777;                       // Magic number para filtrar nuestras posiciones
input string CommandsFile   = "claude_mt5_commands.json"; // Archivo de comandos (en MQL5/Files/)
input string StateFile      = "claude_mt5_state.json";    // Archivo de estado que escribimos
input bool   AllowExecution = true;                       // Kill-switch: false = solo monitoreo, no ejecuta órdenes

//=== GLOBALS ===
string VERSION = "1.00";
string TMP_SUFFIX = ".tmp";

//+------------------------------------------------------------------+
//|                     STRUCT: Parsed Command                       |
//+------------------------------------------------------------------+
struct CmdData {
   string id;
   string type;        // place_order | modify_order | cancel_order | close_position
   string symbol;
   string side;        // BUY | SELL | BUY_LIMIT | SELL_LIMIT | BUY_STOP | SELL_STOP
   double lots;
   double entry;
   double sl;
   double tp;
   string comment;
   int    expiry_minutes;
   long   ticket;      // para cancel/modify/close
   double new_sl;      // para modify
   double new_tp;      // para modify
   bool   processed;
};

//+------------------------------------------------------------------+
//=== JSON HELPER FUNCTIONS ===
//+------------------------------------------------------------------+

// Extrae el valor string de una clave en un objeto JSON plano.
// Busca: "key":"value" o "key": "value"
// Retorna "" si no encontrado.
string JsonGetString(const string json, const string key)
{
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if(pos < 0) return "";

   // Avanzar hasta ':'
   int colon = StringFind(json, ":", pos + StringLen(search));
   if(colon < 0) return "";

   // Buscar comilla de apertura del valor
   int q1 = StringFind(json, "\"", colon + 1);
   if(q1 < 0) return "";

   // Buscar comilla de cierre (escapeadas son \" — no las buscamos por simplicidad;
   // nuestros valores son controlados por Claude, nunca contienen \" escapados)
   int q2 = StringFind(json, "\"", q1 + 1);
   if(q2 < 0) return "";

   return StringSubstr(json, q1 + 1, q2 - q1 - 1);
}

// Extrae el valor numérico (double) de una clave en un objeto JSON plano.
// Busca: "key":number (sin comillas alrededor del valor)
// Retorna 0.0 si no encontrado o si el valor está entre comillas.
double JsonGetDouble(const string json, const string key)
{
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if(pos < 0) return 0.0;

   int colon = StringFind(json, ":", pos + StringLen(search));
   if(colon < 0) return 0.0;

   // Saltar espacios
   int start = colon + 1;
   while(start < StringLen(json) && StringSubstr(json, start, 1) == " ") start++;

   // Si el siguiente char es comilla, es string → no es número
   string firstChar = StringSubstr(json, start, 1);
   if(firstChar == "\"") return 0.0;

   // Leer hasta separador (coma, }, espacio, newline)
   int end = start;
   while(end < StringLen(json))
   {
      string c = StringSubstr(json, end, 1);
      if(c == "," || c == "}" || c == " " || c == "\n" || c == "\r" || c == "]") break;
      end++;
   }
   if(end == start) return 0.0;

   string numStr = StringSubstr(json, start, end - start);
   return StringToDouble(numStr);
}

// Extrae valor long (entero) de una clave
long JsonGetLong(const string json, const string key)
{
   return (long)JsonGetDouble(json, key);
}

// Extrae valor bool ("true"/"false") de una clave
bool JsonGetBool(const string json, const string key)
{
   string search = "\"" + key + "\"";
   int pos = StringFind(json, search);
   if(pos < 0) return false;
   int colon = StringFind(json, ":", pos + StringLen(search));
   if(colon < 0) return false;
   int start = colon + 1;
   while(start < StringLen(json) && StringSubstr(json, start, 1) == " ") start++;
   return (StringSubstr(json, start, 4) == "true");
}

// Formatea datetime como ISO 8601 UTC: "2026-04-23T08:45:12Z"
string FormatISO8601(datetime t)
{
   MqlDateTime dt;
   TimeToStruct(t, dt);
   return StringFormat("%04d-%02d-%02dT%02d:%02d:%02dZ",
                       dt.year, dt.mon, dt.day, dt.hour, dt.min, dt.sec);
}

// Escapa string para embeber en JSON (solo escapa comillas y backslash)
string JsonEscapeString(const string s)
{
   string out = s;
   StringReplace(out, "\\", "\\\\");
   StringReplace(out, "\"", "\\\"");
   return out;
}

//+------------------------------------------------------------------+
//=== PARSEO DE COMMANDS FILE ===
//+------------------------------------------------------------------+

// Lee el archivo de comandos y retorna array de CmdData no procesados.
// Retorna la cantidad de comandos parseados.
int ReadCommands(CmdData &cmds[], string &rawJson)
{
   rawJson = "";
   ArrayResize(cmds, 0);

   int fh = FileOpen(CommandsFile, FILE_READ | FILE_ANSI | FILE_TXT | FILE_COMMON);
   if(fh == INVALID_HANDLE)
   {
      Print("ClaudeBridge: commands file not found yet (", CommandsFile, ") — waiting");
      return 0;
   }

   while(!FileIsEnding(fh))
      rawJson += FileReadString(fh);
   FileClose(fh);

   // Parsear array de objetos: {"commands":[{...},{...}]}
   // Encontrar el array entre [ y ]
   int arrStart = StringFind(rawJson, "[");
   int arrEnd   = StringFind(rawJson, "]", arrStart);
   if(arrStart < 0 || arrEnd < 0) return 0;

   string arrStr = StringSubstr(rawJson, arrStart + 1, arrEnd - arrStart - 1);

   // Iterar objetos { ... } dentro del array
   int cursor = 0;
   int count  = 0;
   while(true)
   {
      int objStart = StringFind(arrStr, "{", cursor);
      if(objStart < 0) break;

      // Buscar cierre de objeto: encontrar } balanceado
      int depth  = 0;
      int objEnd = objStart;
      while(objEnd < StringLen(arrStr))
      {
         string c = StringSubstr(arrStr, objEnd, 1);
         if(c == "{") depth++;
         else if(c == "}") { depth--; if(depth == 0) break; }
         objEnd++;
      }

      string obj = StringSubstr(arrStr, objStart, objEnd - objStart + 1);
      cursor = objEnd + 1;

      // Extraer campos
      CmdData cmd;
      cmd.id             = JsonGetString(obj, "id");
      cmd.type           = JsonGetString(obj, "type");
      cmd.symbol         = JsonGetString(obj, "symbol");
      cmd.side           = JsonGetString(obj, "side");
      cmd.lots           = JsonGetDouble(obj, "lots");
      cmd.entry          = JsonGetDouble(obj, "entry");
      cmd.sl             = JsonGetDouble(obj, "sl");
      cmd.tp             = JsonGetDouble(obj, "tp");
      cmd.comment        = JsonGetString(obj, "comment");
      cmd.expiry_minutes = (int)JsonGetDouble(obj, "expiry_minutes");
      cmd.ticket         = JsonGetLong(obj, "ticket");
      cmd.new_sl         = JsonGetDouble(obj, "new_sl");
      cmd.new_tp         = JsonGetDouble(obj, "new_tp");
      cmd.processed      = JsonGetBool(obj, "processed");

      ArrayResize(cmds, count + 1);
      cmds[count] = cmd;
      count++;
   }

   return count;
}

// Escribe el JSON de commands con el campo "processed" y "result" actualizados.
// Hace atomic write: escribe a .tmp, luego FileMove.
void WriteCommandsResult(const string rawJson, const string cmdId,
                         bool ok, long ticket, double fillPrice,
                         const string execAt, const string errMsg)
{
   // Construir bloque result para este command
   string resultBlock = StringFormat(
      "\"processed\":true,\"result\":{\"ok\":%s,\"ticket\":%I64d,\"fill_price\":%.5f,\"executed_at\":\"%s\",\"error\":\"%s\"}",
      ok ? "true" : "false",
      ticket,
      fillPrice,
      JsonEscapeString(execAt),
      JsonEscapeString(errMsg)
   );

   // Reemplazar el bloque del command con id==cmdId
   // Estrategia: encontrar "id":"<cmdId>" dentro del JSON, luego reemplazar "processed":false por el bloque
   string updated = rawJson;

   // Insertar result: buscar la posición de "id":"cmdId" y dentro de ese objeto reemplazar "processed":false
   string searchId = "\"id\":\"" + cmdId + "\"";
   int idPos = StringFind(updated, searchId);
   if(idPos >= 0)
   {
      // Encontrar cierre de ese objeto (siguiente } no balanceado)
      int objEnd = StringFind(updated, "}", idPos);
      if(objEnd >= 0)
      {
         // Buscar "processed":false dentro de este objeto
         string beforeClose = StringSubstr(updated, 0, objEnd);
         int procPos = StringFind(beforeClose, "\"processed\":false", idPos);
         if(procPos >= 0)
         {
            string left  = StringSubstr(updated, 0, procPos);
            string right = StringSubstr(updated, procPos + StringLen("\"processed\":false"));
            updated = left + resultBlock + right;
         }
      }
   }

   // Atomic write: tmp → rename
   string tmpFile = CommandsFile + TMP_SUFFIX;
   int fh = FileOpen(tmpFile, FILE_WRITE | FILE_ANSI | FILE_TXT | FILE_COMMON);
   if(fh == INVALID_HANDLE)
   {
      Print("ClaudeBridge: cannot write tmp commands file: ", GetLastError());
      return;
   }
   FileWriteString(fh, updated);
   FileClose(fh);
   FileMove(tmpFile, FILE_COMMON, CommandsFile, FILE_REWRITE | FILE_COMMON);
}

//+------------------------------------------------------------------+
//=== COMMAND EXECUTION ===
//+------------------------------------------------------------------+

// Convierte string de side a ENUM_ORDER_TYPE
ENUM_ORDER_TYPE ParseOrderType(const string side)
{
   if(side == "BUY")        return ORDER_TYPE_BUY;
   if(side == "SELL")       return ORDER_TYPE_SELL;
   if(side == "BUY_LIMIT")  return ORDER_TYPE_BUY_LIMIT;
   if(side == "SELL_LIMIT") return ORDER_TYPE_SELL_LIMIT;
   if(side == "BUY_STOP")   return ORDER_TYPE_BUY_STOP;
   if(side == "SELL_STOP")  return ORDER_TYPE_SELL_STOP;
   return ORDER_TYPE_BUY; // default
}

// Ejecuta place_order: market o pending según side
bool ExecutePlaceOrder(const CmdData &cmd, long &outTicket, double &outFillPrice, string &outError)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   ENUM_ORDER_TYPE otype = ParseOrderType(cmd.side);

   bool isMarket = (otype == ORDER_TYPE_BUY || otype == ORDER_TYPE_SELL);

   req.action   = isMarket ? TRADE_ACTION_DEAL : TRADE_ACTION_PENDING;
   req.symbol   = cmd.symbol;
   req.volume   = cmd.lots;
   req.type     = otype;
   req.price    = isMarket ? SymbolInfoDouble(cmd.symbol, SYMBOL_ASK) : cmd.entry;
   req.sl       = cmd.sl;
   req.tp       = cmd.tp;
   req.magic    = Magic;
   req.comment  = cmd.comment;

   if(!isMarket && cmd.expiry_minutes > 0)
   {
      req.expiration = TimeCurrent() + cmd.expiry_minutes * 60;
      req.type_time  = ORDER_TIME_SPECIFIED;
   }
   else
   {
      req.type_time = ORDER_TIME_GTC;
   }

   if(isMarket) req.type_filling = ORDER_FILLING_IOC;

   bool sent = OrderSend(req, res);

   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      outTicket    = (long)res.order;
      outFillPrice = res.price;
      outError     = "";
      return true;
   }

   outTicket    = 0;
   outFillPrice = 0;
   outError     = StringFormat("retcode=%d deal=%I64u order=%I64u comment=%s",
                               res.retcode, res.deal, res.order, res.comment);
   return false;
}

// Ejecuta modify_order: modifica SL/TP de una orden pendiente
bool ExecuteModifyOrder(const CmdData &cmd, string &outError)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action = TRADE_ACTION_MODIFY;
   req.order  = (ulong)cmd.ticket;
   req.sl     = cmd.new_sl;
   req.tp     = cmd.new_tp;
   req.price  = OrderGetDouble(ORDER_PRICE_OPEN); // mantener precio de apertura

   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      outError = "";
      return true;
   }
   outError = StringFormat("modify retcode=%d", res.retcode);
   return false;
}

// Ejecuta cancel_order: elimina una orden pendiente por ticket
bool ExecuteCancelOrder(const CmdData &cmd, string &outError)
{
   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   req.action = TRADE_ACTION_REMOVE;
   req.order  = (ulong)cmd.ticket;

   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      outError = "";
      return true;
   }
   outError = StringFormat("cancel retcode=%d", res.retcode);
   return false;
}

// Ejecuta close_position: cierra posición abierta por ticket
bool ExecuteClosePosition(const CmdData &cmd, long &outTicket, double &outFillPrice, string &outError)
{
   // Buscar la posición por ticket
   if(!PositionSelectByTicket((ulong)cmd.ticket))
   {
      outError = StringFormat("position ticket=%I64d not found", cmd.ticket);
      return false;
   }

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};

   ENUM_POSITION_TYPE posType = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double vol    = PositionGetDouble(POSITION_VOLUME);
   string symbol = PositionGetString(POSITION_SYMBOL);

   req.action   = TRADE_ACTION_DEAL;
   req.symbol   = symbol;
   req.volume   = vol;
   req.type     = (posType == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
   req.price    = (posType == POSITION_TYPE_BUY)
                  ? SymbolInfoDouble(symbol, SYMBOL_BID)
                  : SymbolInfoDouble(symbol, SYMBOL_ASK);
   req.position = (ulong)cmd.ticket;
   req.magic    = Magic;
   req.comment  = "ClaudeBridge close";
   req.type_filling = ORDER_FILLING_IOC;

   bool sent = OrderSend(req, res);
   if(sent && res.retcode == TRADE_RETCODE_DONE)
   {
      outTicket    = (long)res.deal;
      outFillPrice = res.price;
      outError     = "";
      return true;
   }
   outError = StringFormat("close retcode=%d", res.retcode);
   return false;
}

// Despacha un CmdData al handler correcto y escribe resultado al JSON
void DispatchCommand(const CmdData &cmd, const string rawJson)
{
   if(cmd.processed)
   {
      // Ya procesado — skip (idempotencia)
      return;
   }

   if(!AllowExecution)
   {
      Print("ClaudeBridge: AllowExecution=false — skipping command ", cmd.id, " type=", cmd.type);
      WriteCommandsResult(rawJson, cmd.id, false, 0, 0,
                          FormatISO8601(TimeGMT()), "AllowExecution=false (kill-switch activo)");
      return;
   }

   Print("ClaudeBridge: executing command id=", cmd.id, " type=", cmd.type, " symbol=", cmd.symbol);

   long   outTicket    = 0;
   double outFillPrice = 0.0;
   string outError     = "";
   bool   ok           = false;
   string execAt       = FormatISO8601(TimeGMT());

   if(cmd.type == "place_order")
   {
      ok = ExecutePlaceOrder(cmd, outTicket, outFillPrice, outError);
   }
   else if(cmd.type == "modify_order")
   {
      ok = ExecuteModifyOrder(cmd, outError);
   }
   else if(cmd.type == "cancel_order")
   {
      ok = ExecuteCancelOrder(cmd, outError);
   }
   else if(cmd.type == "close_position")
   {
      ok = ExecuteClosePosition(cmd, outTicket, outFillPrice, outError);
   }
   else
   {
      outError = "unknown command type: " + cmd.type;
      ok = false;
   }

   if(ok)
      Print("ClaudeBridge: command OK id=", cmd.id, " ticket=", outTicket, " fill=", outFillPrice);
   else
      Print("ClaudeBridge: command FAILED id=", cmd.id, " error=", outError);

   WriteCommandsResult(rawJson, cmd.id, ok, outTicket, outFillPrice, execAt, outError);
}

//+------------------------------------------------------------------+
//=== STATE SERIALIZATION ===
//+------------------------------------------------------------------+

// Construye el JSON de estado y lo escribe atómicamente.
void WriteState()
{
   string now = FormatISO8601(TimeGMT());

   // --- Account ---
   long   login      = AccountInfoInteger(ACCOUNT_LOGIN);
   string server     = AccountInfoString(ACCOUNT_SERVER);
   string currency   = AccountInfoString(ACCOUNT_CURRENCY);
   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity     = AccountInfoDouble(ACCOUNT_EQUITY);
   double margin     = AccountInfoDouble(ACCOUNT_MARGIN);
   double freeMargin = AccountInfoDouble(ACCOUNT_FREEMARGIN);

   string accountJson = StringFormat(
      "{\"login\":%I64d,\"server\":\"%s\",\"balance\":%.2f,\"equity\":%.2f,"
      "\"margin\":%.2f,\"free_margin\":%.2f,\"currency\":\"%s\"}",
      login, JsonEscapeString(server), balance, equity, margin, freeMargin,
      JsonEscapeString(currency)
   );

   // --- Positions (filtradas por magic) ---
   string posArr = "[";
   int    posTotal = PositionsTotal();
   bool   firstPos = true;
   for(int i = 0; i < posTotal; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != Magic) continue;

      string sym       = PositionGetString(POSITION_SYMBOL);
      double vol       = PositionGetDouble(POSITION_VOLUME);
      double openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      double curPrice  = PositionGetDouble(POSITION_PRICE_CURRENT);
      double sl        = PositionGetDouble(POSITION_SL);
      double tp        = PositionGetDouble(POSITION_TP);
      double pnl       = PositionGetDouble(POSITION_PROFIT);
      string posType   = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      datetime openTime = (datetime)PositionGetInteger(POSITION_TIME);
      string comment   = PositionGetString(POSITION_COMMENT);

      if(!firstPos) posArr += ",";
      posArr += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\",\"lots\":%.2f,"
         "\"open_price\":%.5f,\"current_price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,"
         "\"pnl\":%.2f,\"open_time\":\"%s\",\"comment\":\"%s\"}",
         ticket, JsonEscapeString(sym), posType, vol,
         openPrice, curPrice, sl, tp, pnl,
         FormatISO8601(openTime), JsonEscapeString(comment)
      );
      firstPos = false;
   }
   posArr += "]";

   // --- Pending Orders (filtradas por magic) ---
   string ordArr  = "[";
   int    ordTotal = OrdersTotal();
   bool   firstOrd = true;
   for(int i = 0; i < ordTotal; i++)
   {
      ulong ticket = OrderGetTicket(i);
      if(!OrderSelect(ticket)) continue;
      if(OrderGetInteger(ORDER_MAGIC) != Magic) continue;

      string sym      = OrderGetString(ORDER_SYMBOL);
      double vol      = OrderGetDouble(ORDER_VOLUME_CURRENT);
      double price    = OrderGetDouble(ORDER_PRICE_OPEN);
      double sl       = OrderGetDouble(ORDER_SL);
      double tp       = OrderGetDouble(ORDER_TP);
      datetime expiry = (datetime)OrderGetInteger(ORDER_TIME_EXPIRATION);
      ENUM_ORDER_TYPE otype = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      string typeStr;
      switch(otype)
      {
         case ORDER_TYPE_BUY_LIMIT:  typeStr = "BUY_LIMIT";  break;
         case ORDER_TYPE_SELL_LIMIT: typeStr = "SELL_LIMIT"; break;
         case ORDER_TYPE_BUY_STOP:   typeStr = "BUY_STOP";   break;
         case ORDER_TYPE_SELL_STOP:  typeStr = "SELL_STOP";  break;
         default:                    typeStr = "MARKET";      break;
      }

      if(!firstOrd) ordArr += ",";
      ordArr += StringFormat(
         "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\",\"lots\":%.2f,"
         "\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,\"expiry\":\"%s\"}",
         ticket, JsonEscapeString(sym), typeStr, vol,
         price, sl, tp, FormatISO8601(expiry)
      );
      firstOrd = false;
   }
   ordArr += "]";

   // --- Closed Today (HistorySelect rango hoy 00:00 UTC a ahora) ---
   MqlDateTime todayDt;
   TimeToStruct(TimeGMT(), todayDt);
   todayDt.hour = 0; todayDt.min = 0; todayDt.sec = 0;
   datetime dayStart = StructToTime(todayDt);

   HistorySelect(dayStart, TimeGMT() + 1);

   string closedArr = "[";
   bool   firstClosed = true;

   // Iterar deals para encontrar los nuestros
   int dealsTotal = HistoryDealsTotal();
   for(int i = 0; i < dealsTotal; i++)
   {
      ulong dealTicket = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(dealTicket, DEAL_MAGIC) != Magic) continue;

      // Solo deals de salida (DEAL_ENTRY_OUT) representan cierres
      ENUM_DEAL_ENTRY entry = (ENUM_DEAL_ENTRY)HistoryDealGetInteger(dealTicket, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT) continue;

      string sym      = HistoryDealGetString(dealTicket, DEAL_SYMBOL);
      double vol      = HistoryDealGetDouble(dealTicket, DEAL_VOLUME);
      double price    = HistoryDealGetDouble(dealTicket, DEAL_PRICE);
      double profit   = HistoryDealGetDouble(dealTicket, DEAL_PROFIT);
      double swap     = HistoryDealGetDouble(dealTicket, DEAL_SWAP);
      double commission = HistoryDealGetDouble(dealTicket, DEAL_COMMISSION);
      datetime closeTime = (datetime)HistoryDealGetInteger(dealTicket, DEAL_TIME);
      long   posTicket = HistoryDealGetInteger(dealTicket, DEAL_POSITION_ID);
      ENUM_DEAL_TYPE dtype = (ENUM_DEAL_TYPE)HistoryDealGetInteger(dealTicket, DEAL_TYPE);
      string typeStr = (dtype == DEAL_TYPE_BUY) ? "BUY" : "SELL";

      if(!firstClosed) closedArr += ",";
      closedArr += StringFormat(
         "{\"deal\":%I64u,\"position_ticket\":%I64d,\"symbol\":\"%s\",\"type\":\"%s\","
         "\"lots\":%.2f,\"close_price\":%.5f,\"profit\":%.2f,\"swap\":%.2f,"
         "\"commission\":%.2f,\"close_time\":\"%s\"}",
         dealTicket, posTicket, JsonEscapeString(sym), typeStr,
         vol, price, profit, swap, commission, FormatISO8601(closeTime)
      );
      firstClosed = false;
   }
   closedArr += "]";

   // --- Armar JSON completo ---
   string stateJson = StringFormat(
      "{\"last_update\":\"%s\",\"account\":%s,"
      "\"positions\":%s,\"pending_orders\":%s,\"closed_today\":%s}",
      now, accountJson, posArr, ordArr, closedArr
   );

   // Atomic write: tmp → rename
   string tmpFile = StateFile + TMP_SUFFIX;
   int fh = FileOpen(tmpFile, FILE_WRITE | FILE_ANSI | FILE_TXT | FILE_COMMON);
   if(fh == INVALID_HANDLE)
   {
      Print("ClaudeBridge: cannot open state tmp file for write: ", GetLastError());
      return;
   }
   FileWriteString(fh, stateJson);
   FileClose(fh);
   FileMove(tmpFile, FILE_COMMON, StateFile, FILE_REWRITE | FILE_COMMON);
}

//+------------------------------------------------------------------+
//=== PROCESS COMMANDS PIPELINE ===
//+------------------------------------------------------------------+

void ProcessCommands()
{
   string rawJson;
   CmdData cmds[];
   int count = ReadCommands(cmds, rawJson);
   if(count == 0) return;

   for(int i = 0; i < count; i++)
   {
      if(!cmds[i].processed)
         DispatchCommand(cmds[i], rawJson);
   }
}

//+------------------------------------------------------------------+
//=== EVENT HANDLERS ===
//+------------------------------------------------------------------+

int OnInit()
{
   EventSetTimer(HeartbeatSec);
   PrintFormat("ClaudeBridge EA v%s starting magic=%I64d heartbeat=%ds AllowExecution=%s",
               VERSION, Magic, HeartbeatSec, AllowExecution ? "true" : "false");
   // Escribir estado inicial
   WriteState();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   PrintFormat("ClaudeBridge EA stopping. Reason code: %d", reason);
}

void OnTimer()
{
   ProcessCommands();
   WriteState();
}

// OnTick requerido aunque no lo usemos (compilación limpia)
void OnTick() {}
