//+------------------------------------------------------------------+
//|                                   BTC_Swing_Sentinel_v100.mq5   |
//|                        Copyright 2026, BTC Prudential Signal Team |
//|                                      https://github.com/giuse2003 |
//+------------------------------------------------------------------+
#property copyright   "BTC Prudential Signal Team"
#property link        "https://github.com/giuse2003/BTC_Prudential_Signal"
#property version     "1.00"
#property description "Quantitative Bitcoin Long-Only Swing Strategy."
#property description "Combines Golden Regime (SMA50/SMA200) with Parabolic Chandelier Trailing Exit"
#property description "and Coinbase Spot fee-drag emulation (0.60% per leg)."

#include <Trade\Trade.mqh>

//====================================================================
// ENUMS
//====================================================================
enum ENUM_LOT_MODE
{
   LOT_FIXED         = 0, // Fixed Lots (InpFixedLot)
   LOT_PCT_EQUITY    = 1  // Spot Emulation: % of Equity (Unleveraged Spot Hold)
};

//====================================================================
// INPUTS
//====================================================================
input group "===== 1. Strategy Parameters ====="
input ulong          InpMagic                = 20261122;     // Magic Number
input string         InpTradeComment         = "BTC_Swing_Sentinel"; // Trade Comment
input double         InpRsiThreshold         = 40.0;         // RSI(14) Min Threshold (>= 40)
input int            InpMomentumDays         = 7;            // Momentum Lookback (Days)
input bool           InpUseVolumeFilter      = true;         // Require Volume > Volume SMA20
input int            InpVolumeMaPeriod       = 20;           // Volume SMA Period

input group "===== 2. Dynamic Parabolic Chandelier Exit ====="
input bool           InpUseChandelier        = true;         // Enable Parabolic Chandelier Trailing Exit
input double         InpStretchRatio         = 1.50;         // Stretch Threshold (Price > X * SMA50)
input double         InpTrailK               = 2.50;         // Trailing Factor (K * ATR(14))
input int            InpConsecBelowSMA50     = 2;            // Closes below SMA50 for macro exit

input group "===== 3. Money Management & Spot Emulation ====="
input ENUM_LOT_MODE  InpLotMode              = LOT_PCT_EQUITY; // Position Sizing Mode
input double         InpFixedLot             = 0.10;         // Fixed Lot Size (if LOT_FIXED)
input double         InpEquityPct            = 95.0;         // % of Free Margin used (Spot 1.0x allocation)
input double         InpCoinbaseFeePct       = 0.60;         // Coinbase Spot Fee per transaction (0.60%)

input group "===== 4. Visual HUD & Logging ====="
input bool           InpShowHUD              = true;         // Show Chart Telemetry HUD
input color          InpHUDColor             = clrGold;      // HUD Text Color

//====================================================================
// GLOBAL VARIABLES
//====================================================================
CTrade         g_trade;
int            g_h_sma50      = INVALID_HANDLE;
int            g_h_sma200     = INVALID_HANDLE;
int            g_h_rsi        = INVALID_HANDLE;
int            g_h_atr        = INVALID_HANDLE;

datetime       g_last_d1_time = 0;
double         g_peak_price   = 0.0;
double         g_entry_price  = 0.0;
datetime       g_entry_time   = 0;
int            g_consec_below = 0;

// Synthetic Coinbase Spot Tracking
double         g_spot_starting_capital = 10000.0;
double         g_spot_equity           = 10000.0;
double         g_spot_units            = 0.0;
bool           g_spot_in_trade         = false;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetMarginMode();
   g_trade.SetTypeFillingBySymbol(_Symbol);

   // Initialize Indicator Handles on PERIOD_D1
   g_h_sma50 = iMA(_Symbol, PERIOD_D1, 50, 0, MODE_SMA, PRICE_CLOSE);
   if(g_h_sma50 == INVALID_HANDLE)
   {
      PrintFormat("[INIT ERROR] Failed to create SMA50 handle: %d", GetLastError());
      return INIT_FAILED;
   }

   g_h_sma200 = iMA(_Symbol, PERIOD_D1, 200, 0, MODE_SMA, PRICE_CLOSE);
   if(g_h_sma200 == INVALID_HANDLE)
   {
      PrintFormat("[INIT ERROR] Failed to create SMA200 handle: %d", GetLastError());
      return INIT_FAILED;
   }

   g_h_rsi = iRSI(_Symbol, PERIOD_D1, 14, PRICE_CLOSE);
   if(g_h_rsi == INVALID_HANDLE)
   {
      PrintFormat("[INIT ERROR] Failed to create RSI handle: %d", GetLastError());
      return INIT_FAILED;
   }

   g_h_atr = iATR(_Symbol, PERIOD_D1, 14);
   if(g_h_atr == INVALID_HANDLE)
   {
      PrintFormat("[INIT ERROR] Failed to create ATR handle: %d", GetLastError());
      return INIT_FAILED;
   }

   g_spot_starting_capital = AccountInfoDouble(ACCOUNT_BALANCE);
   if(g_spot_starting_capital <= 0) g_spot_starting_capital = 10000.0;
   g_spot_equity = g_spot_starting_capital;

   PrintFormat("[INIT] BTC_Swing_Sentinel_v100 Initialized successfully on %s. Balance: %.2f", 
               _Symbol, g_spot_starting_capital);

   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   IndicatorRelease(g_h_sma50);
   IndicatorRelease(g_h_sma200);
   IndicatorRelease(g_h_rsi);
   IndicatorRelease(g_h_atr);

   if(InpShowHUD)
   {
      ObjectsDeleteAll(0, "BTC_SWING_");
      Comment("");
   }
}

//+------------------------------------------------------------------+
//| Check if position currently open for our Magic                   |
//+------------------------------------------------------------------+
bool HasOpenPosition(ulong &ticket, double &open_price, double &volume)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetSymbol(i) == _Symbol)
      {
         if(PositionGetInteger(POSITION_MAGIC) == InpMagic)
         {
            ticket     = PositionGetInteger(POSITION_TICKET);
            open_price = PositionGetDouble(POSITION_PRICE_OPEN);
            volume     = PositionGetDouble(POSITION_VOLUME);
            return true;
         }
      }
   }
   return false;
}

//+------------------------------------------------------------------+
//| Calculate Lot Size                                               |
//+------------------------------------------------------------------+
double CalculateLots(double price)
{
   if(InpLotMode == LOT_FIXED)
      return InpFixedLot;

   double free_margin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double contract_size = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_CONTRACT_SIZE);
   if(contract_size <= 0) contract_size = 1.0;

   double target_value = free_margin * (InpEquityPct / 100.0);
   double raw_lots = target_value / (price * contract_size);

   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double min_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   double lots = MathFloor(raw_lots / lot_step) * lot_step;
   if(lots < min_lot) lots = min_lot;
   if(lots > max_lot) lots = max_lot;

   return NormalizeDouble(lots, 2);
}

//+------------------------------------------------------------------+
//| Get Indicator Value from Handle                                  |
//+------------------------------------------------------------------+
double ReadIndicator(int handle, int shift)
{
   double buf[1];
   if(CopyBuffer(handle, 0, shift, 1, buf) <= 0)
      return 0.0;
   return buf[0];
}

//+------------------------------------------------------------------+
//| Get D1 Close                                                     |
//+------------------------------------------------------------------+
double GetD1Close(int shift)
{
   MqlRates rates[1];
   if(CopyRates(_Symbol, PERIOD_D1, shift, 1, rates) <= 0)
      return 0.0;
   return rates[0].close;
}

//+------------------------------------------------------------------+
//| Get 20-day Volume SMA                                            |
//+------------------------------------------------------------------+
bool GetVolumeCondition(long &curr_vol, double &avg_vol)
{
   MqlRates rates[21];
   int copied = CopyRates(_Symbol, PERIOD_D1, 1, InpVolumeMaPeriod + 1, rates);
   if(copied < InpVolumeMaPeriod) return true; // fail-open if not enough bars

   curr_vol = (long)rates[copied - 1].tick_volume; // bar 1
   long sum = 0;
   for(int i = 0; i < copied - 1; i++)
   {
      sum += (long)rates[i].tick_volume;
   }
   avg_vol = (double)sum / (double)(copied - 1);
   return (curr_vol > avg_vol);
}

//+------------------------------------------------------------------+
//| Update On-Screen HUD                                             |
//+------------------------------------------------------------------+
void UpdateHUD(bool in_pos, double close1, double sma50, double sma200, 
               double rsi14, double atr14, double chandelier_stop)
{
   if(!InpShowHUD) return;

   string hud = "";
   hud += "========================================\n";
   hud += "  BTC SWING SENTINEL - MQL5 v1.00       \n";
   hud += "  Engine: D1 Golden Regime + Chandelier \n";
   hud += "========================================\n";
   hud += StringFormat("Symbol: %s | Time: %s\n", _Symbol, TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES));
   hud += StringFormat("Status: %s\n", in_pos ? ">>> IN POSITION (LONG) <<<" : "FLAT (WAITING FOR SIGNAL)");
   hud += StringFormat("BTC Close (D1): %.2f\n", close1);
   hud += StringFormat("SMA50: %.2f | SMA200: %.2f\n", sma50, sma200);
   hud += StringFormat("Regime: %s\n", (close1 > sma200) ? "BULLISH (Close > SMA200)" : "BEARISH / CAUTION");
   hud += StringFormat("RSI(14): %.1f (Min: %.1f)\n", rsi14, InpRsiThreshold);
   hud += StringFormat("ATR(14): %.2f\n", atr14);

   if(in_pos)
   {
      double stretch = (sma50 > 0) ? (g_peak_price / sma50) : 0.0;
      hud += "----------------------------------------\n";
      hud += StringFormat("Entry Price: %.2f\n", g_entry_price);
      hud += StringFormat("Peak Price:  %.2f (Stretch: %.2fx SMA50)\n", g_peak_price, stretch);
      if(stretch >= InpStretchRatio)
      {
         hud += StringFormat("CHANDELIER ACTIVE: Trailing Stop @ %.2f\n", chandelier_stop);
         hud += StringFormat("Distance to Chandelier Stop: %.2f USD\n", close1 - chandelier_stop);
      }
      else
      {
         hud += StringFormat("Chandelier Inactive (Stretch %.2fx < Target %.2fx)\n", stretch, InpStretchRatio);
         hud += StringFormat("Active Exit: 2 closes below SMA50 (Current: %d)\n", g_consec_below);
      }
   }

   Comment(hud);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Check if new daily bar (D1) has formed
   datetime d1_time = iTime(_Symbol, PERIOD_D1, 0);
   bool is_new_d1 = (d1_time != g_last_d1_time);

   // Tracking position
   ulong  pos_ticket = 0;
   double open_price = 0.0;
   double pos_volume = 0.0;
   bool   in_position = HasOpenPosition(pos_ticket, open_price, pos_volume);

   // Update peak price continuously on ticks if in position
   double current_bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(in_position)
   {
      if(current_bid > g_peak_price)
         g_peak_price = current_bid;
   }

   // Read indicator values on bar 1 (last closed daily bar)
   double close1 = GetD1Close(1);
   double close2 = GetD1Close(2);
   double close_mom = GetD1Close(1 + InpMomentumDays);

   double sma50_1  = ReadIndicator(g_h_sma50, 1);
   double sma50_2  = ReadIndicator(g_h_sma50, 2);
   double sma200_1 = ReadIndicator(g_h_sma200, 1);
   double rsi_1    = ReadIndicator(g_h_rsi, 1);
   double atr_1    = ReadIndicator(g_h_atr, 1);

   long   cur_vol = 0;
   double avg_vol = 0.0;
   bool   vol_ok  = !InpUseVolumeFilter || GetVolumeCondition(cur_vol, avg_vol);

   // Chandelier Trailing Stop calculation
   double chandelier_stop = 0.0;
   bool chandelier_active = false;
   if(in_position && g_peak_price > InpStretchRatio * sma50_1)
   {
      chandelier_active = true;
      chandelier_stop   = g_peak_price - (InpTrailK * atr_1);
   }

   // Process Daily Bar Close logic
   if(is_new_d1 && close1 > 0 && sma50_1 > 0 && sma200_1 > 0)
   {
      g_last_d1_time = d1_time;

      // Update consecutive closes below SMA50
      if(close1 < sma50_1)
         g_consec_below++;
      else
         g_consec_below = 0;

      // -------------------------------------------------------------
      // EXIT CHECK
      // -------------------------------------------------------------
      if(in_position)
      {
         bool exit_triggered = false;
         string exit_reason = "";

         // Condition A: Macro Breakdown (2 closes below SMA50)
         if(g_consec_below >= InpConsecBelowSMA50)
         {
            exit_triggered = true;
            exit_reason = StringFormat("2_CLOSES_BELOW_SMA50 (C1=%.2f < SMA50=%.2f)", close1, sma50_1);
         }
         // Condition B: Parabolic Chandelier Trailing Exit
         else if(InpUseChandelier && chandelier_active && close1 < chandelier_stop)
         {
            exit_triggered = true;
            exit_reason = StringFormat("CHANDELIER_TRAIL_HIT (C1=%.2f < Stop=%.2f, Peak=%.2f)", 
                                       close1, chandelier_stop, g_peak_price);
         }

         if(exit_triggered)
         {
            PrintFormat("[EXIT] Closing Ticket #%I64u | Reason: %s | PnL: %.2f USD", 
                        pos_ticket, exit_reason, (close1 - g_entry_price) * pos_volume);
            
            if(g_trade.PositionClose(pos_ticket))
            {
               // Coinbase spot fee emulation
               double exit_fee = (g_spot_equity * (InpCoinbaseFeePct / 100.0));
               double trade_gain = (close1 / g_entry_price - 1.0);
               g_spot_equity = g_spot_equity * (1.0 + trade_gain) - exit_fee;
               
               PrintFormat("[SPOT EMULATION] Trade completed. Net Spot Gain: %.2f%% | Synthetic Equity: %.2f USD", 
                           trade_gain * 100.0, g_spot_equity);

               in_position  = false;
               g_peak_price = 0.0;
               g_entry_price = 0.0;
               g_consec_below = 0;
            }
         }
      }

      // -------------------------------------------------------------
      // ENTRY CHECK (Long-Only)
      // -------------------------------------------------------------
      if(!in_position)
      {
         bool cond_regime   = (close1 > sma200_1);
         bool cond_rsi      = (rsi_1 >= InpRsiThreshold);
         bool cond_momentum = (close1 > close_mom);
         bool cond_volume   = vol_ok;

         if(cond_regime && cond_rsi && cond_momentum && cond_volume)
         {
            double lots = CalculateLots(current_bid);
            PrintFormat("[ENTRY] Signal ACQUISTA Triggered: Close=%.2f > SMA200=%.2f, RSI=%.1f, Mom=%.2f, Vol=OK. Lots: %.2f",
                        close1, sma200_1, rsi_1, close_mom, lots);

            if(g_trade.Buy(lots, _Symbol, 0, 0, 0, InpTradeComment))
            {
               g_entry_price = current_bid;
               g_peak_price  = current_bid;
               g_entry_time  = TimeCurrent();
               g_consec_below = 0;
               in_position   = true;

               // Emulate Coinbase 0.60% entry fee
               double entry_fee = g_spot_equity * (InpCoinbaseFeePct / 100.0);
               g_spot_equity -= entry_fee;
               PrintFormat("[SPOT EMULATION] Entry executed. Fee paid: %.2f USD | Capital: %.2f USD", 
                           entry_fee, g_spot_equity);
            }
            else
            {
               PrintFormat("[ERROR] Trade Buy failed: %d", GetLastError());
            }
         }
      }
   }

   // Update visual HUD
   UpdateHUD(in_position, close1, sma50_1, sma200_1, rsi_1, atr_1, chandelier_stop);
}
//+------------------------------------------------------------------+
