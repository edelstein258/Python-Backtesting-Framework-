# -*- coding: utf-8 -*-
"""
Created on Thu Sep 13 13:01:45 2021
@author: Rathan
"""
import logging
import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

class Order():
    def __init__(self, ins, qty, side, price, time, remark, exchange='NSE'):
        self.ins = ins
        self.qty = qty
        self.side = side
        self.price = price
        self.time = time
        self.remark = remark
        self.exchange = exchange
        
trade_hist = list()

class Trade():
    def __init__(self):
        self.ins = ''
        self.qty = 0
        self.side = 0
        self.exchange = ''
        self.entry_price = -1
        self.entry_time = -1
        self.entry_remark = ''
        self.exit_price = -1
        self.exit_time = ''
        self.exit_remark = ''
        self.holding_period = 0
        self.cum_pnl = 0
    
    def to_dict(self):
        return {
            'ins': self.ins,
            'qty': self.qty,
            'side': self.side,
            'exchange': self.exchange,
            'entry_price': self.entry_price,
            'entry_time': self.entry_time,
            'entry_remark': self.entry_remark,
            'exit_price': self.exit_price,
            'exit_time': self.exit_time,
            'exit_remark': self.exit_remark,
            'holding_period': self.holding_period,
            'pnl': self.pnl,
            'pnl_prct': self.pnl_prct,
            'cum_pnl': self.cum_pnl,
            'cost': self.cost,
        }

    def entry_trade(self, order):
        self.ins = order.ins
        self.qty = order.qty
        if order.side == 'BUY':
            self.side = 'LONG'
        else:
            self.side = 'SHORT'
        self.exchange = order.exchange
        self.entry_price = order.price
        self.entry_time = order.time
        self.entry_remark = order.remark
        self.compute_cost()

    def compute_cost(self):
        self.cost = (self.qty * self.price) * 0.0002
    
    def calc_pnl(self):
        if self.side == 'LONG':
            self.pnl = (self.entry_price - self.exit_price) * self.qty
        else:
            self.pnl = -(self.entry_price - self.exit_price) * self.qty
        self.pnl_prct = self.pnl/self.entry_price*100
    
    def exit_trade(self, order):
        if (order.ins != self.ins) or (order.qty != self.qty):
            return False
        if (((self.side == 'LONG') and (order.side != 'SELL')) or ((self.side == 'SHORT') and (order.side != 'BUY'))):
            return False
        self.exit_price = order.price
        self.exit_time = order.time
        self.exit_remark = order.remark
        self.calc_pnl()
        return True


class Position():
    def __init__(self, ins, **kwargs):
        self.ins = ins
        self.cost = 0
        self.last_traded_price = 0
        self.last_traded_time = 0
        self.trade_count = 0
        self.pnl = 0
        self.current_trade = Trade()
        global trade_hist
        # self.trade_list = list()

    def place_order(self, order):
        self.trade_count += 1
        if order.ins == self.ins:
            if self.current_trade.qty == 0:
                self.current_trade.entry_trade(order)
            else:
                if self.current_trade.exit_trade(order):
                    self.cost += self.current_trade.cost
                    self.pnl += self.current_trade.pnl
                    self.current_trade.pnl = self.pnl
                    # self.trade_list.append(self.current_trade)
                    trade_hist.append(self.current_trade)
                    self.current_trade = Trade()
            log.info('Taking %s Trade in %s of %s at %s', order.side, order.ins, order.qty, order.price)
            
            self.last_traded_price = order.price
            self.last_traded_time = order.time

        else:
            print('Cant update since order_ins: %s pos_ins: %s'%(order.ins, self.ins))


class Portfolio():
    def __init__(self):
        self.pos_map = dict()

    @property
    def instrument_list(self):
        return list(self.pos_map.keys())

    def update_position(self, position):
        self.pos_map[position.ins] = position

    def place_order(self, order):
        if not order.ins in self.instrument_list:
            self.pos_map[order.ins] = Position(order.ins)

        self.pos_map[order.ins].place_order(order)

    @property
    def trade_list(self):
        all_trades = list()
        for ins, pos in self.pos_map.items():
            all_trades.extend(pos.trade_list)
        return all_trades

    @property
    def cost(self):
        cost = 0
        for ins, pos in self.pos_map.items():
            cost += pos.cost
        return cost

    @property
    def pnl(self):
        pnl = 0
        for ins, pos in self.pos_map.items():
            pnl += pos.pnl
        return pnl


class BackTestSummary():
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.risk_free_rate = 0.06
        self.trading_days_in_year = 252
        self.trade_pnl = pd.DataFrame()
        self.description = None
        self.states = dict()

    def set_capital(self, cap):
        self.capital = cap

    def set_description(self, _description):
        self.description = _description

    def record_pnl(self, ts):
        # for ins, pos in self.portfolio.pos_map.items():
        self.pnl_series.loc[ts, 'total'] = self.portfolio.pnl

    def record_state(self, ts, _state):
        self.states[ts] = _state


class DataSet():
    def __init__(self):
        self.data = dict()

    def add_data(self, ins, df):
        self.data[ins] = df

    @property
    def instrument_list(self):
        return list(self.data.keys())
    
    def get_data(self, ins):
        return self.data.get(ins)




def gen_trade_report():
    trades_df = pd.DataFrame.from_records([t.to_dict() for t in trade_hist]).T

def gen_full_data_entry_report():
    pass

def calc_rsi(close, window):
    delta = close.diff()
    up_days = delta.copy()
    up_days[delta<=0]=0.0
    down_days = abs(delta.copy())
    down_days[delta>0]=0.0
    RS_up = up_days.rolling(window).mean()
    RS_down = down_days.rolling(window).mean()
    rsi= 100-100/(1+RS_up/RS_down)
    return rsi

def prep_data(dataset, ema1_span, ema2_span, rsi1_window):
    # make the correct data format
    # dataset = pd.read_excel('dataset.xlsx', sheet_name=None)
    cols = ['Ticker', 'Date/Time', 'Open', 'High', 'Low', 'Close','Volume']
    # TODO
    # sort the data on timestamp
    for key in dataset.keys():
        df = dataset[key]
        df = df[cols]
        df = df.rename(columns={'Date/Time':'DateTime'})
        df.set_index(df['DateTime'])
        df.sort_index()
        # calc_ema()
        df['EMA1'] = df['Close'].ewm(span=ema1_span, adjust=False).mean()
        df['EMA1_prev'] = df['EMA1'].shift(1)
        df['EMA2'] = df['Close'].ewm(span=ema2_span, adjust=False).mean()
        df['EMA2_prev'] = df['EMA2'].shift(1)
        # calc_rsi()
        df['RSI'] = calc_rsi(df.Close, rsi1_window)
        df['RSI_prev'] = df['RSI'].shift(1)
        dataset[key] = df
        del df
        # shift prev_value
    #combine data

def gen_signal(row):
  # crosserver
  if (row['EMA1_prev'] < row['EMA2_prev']) and (row['EMA1'] > row['EMA2']):
    return 'LONG'
  elif (row['EMA1_prev'] > row['EMA2_prev']) and (row['EMA1'] < row['EMA2']):
    return 'SHORT'
  return -1


def trade_logic(dataset):
    timestamp = ''
    ins_list = []
    trade_cap = 500000
    for t in timestamp:
        for inst in ins_list:
            df = dataset[inst]
            entry_cond1 = True
            entry_cond2 = True
            entry_cond3 = True
            exit_cond1 = True
            exit_cond2 = True
            exit_cond3 = True
            sl_cond = False
            tgt_cond = False
            tsl_cond = False
            if (entry_cond1) and (entry_cond2):
                qty = int(trade_cap//curr_price)
                if entry_cond3:
                    ord = Order(inst, qty, 'BUY', curr_price, t, '')

# def summarize_trades():
#     gen_trade_report()
#     gen_full_data_entry_report()

def gen_summary1():
    pass

def gen_summary2():
    pass


# Trade Summary Metrics to be Calculated
'''
Full data Entry Format
    data + calculated metrics and perform outer join with trade df
'''

'''
Trade Report
SYMBOL	TRADE	
DATE IN	    TIME IN	    PRICE IN	
DATE OUT	TIME OUT	PRICE OUT 
CHNG%	PL	PL%	
ENTRY REMARK	
EXIT REMARK	
QTY	
TURNOVER
NBARS	mfe%	mae%	Ccum pl	HighValue	Drawdown	MaxDD

Calculate Row specific data
Combime all trades
Calculate other metrics
'''

'''
Summary 1
Parameter 1, Parameter 2, Data in year, No. of Trades, Winning Trades, Losing Trades, Max DD, PNL/No. of Trades, RRR
'''

'''
Summary 2
Have to Calculate for different Combination of Parameters
Symbol, PNL, ata in year, No. of Trades, Winning Trades, Losing Trades, Max DD, PNL/No. of Trades, RRR
'''