import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tqdm
from future_data_loader import FutureDataLoader
from trading_strategy_visualizer import Visualizer
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class VIXShortStrategy:
    def __init__(self, start_date, end_date, ric):
        self.start_date = start_date
        self.end_date = end_date
        self.ric = ric
        self.capital = 100000.00  # 初始资本金
        self.stop_loss = 0.00
        loader = FutureDataLoader(
            ric=self.ric,
            start_date=self.start_date,
            end_date=self.end_date,
        )
        daily_data = loader.main_contract
        intraday_data = loader.intraday
        self.daily_data = daily_data
        self.intraday_data = intraday_data

    def _get_trading_day(self, dt):
        if dt.hour >= 18:  # 18:00-23:59 属于明天的交易日
            return (dt + pd.Timedelta(days=1)).date()
        else:  # 00:00-17:59 属于今天的交易日
            return dt.date()

    def _close_position(self, data, dt, trade_state):
        if trade_state['position'] == 0:
            return
        # 重置交易状态
        trade_state['position'] = 0
        trade_state['entry_price'] = None
        # 更新数据
        data.at[dt, 'position'] = 0
        # print(f'{dt}平仓')
        return

    def _open_position(self, data, dt, row, trade_state, position):
        entry_price = row['close']
        # 更新交易状态
        trade_state['position'] = position
        trade_state['entry_price'] = entry_price
        trade_state['daily_trades'] += 1
        # 更新数据
        data.at[dt, 'position'] = position
        data.at[dt, 'entry_price'] = entry_price
        # 显示输出
        # action = '开多' if position == 1 else '开空'
        # print(f'{dt}{action}')
        return

    def _check_stop_loss(self, data, dt, row, trade_state):
        current_price = row['close']
        entry_price = trade_state['entry_price']
        position = trade_state['position']
        pnl_pct = (current_price - entry_price) / entry_price * position
        if pnl_pct <= -self.stop_loss:
            # print(f'触发止损：当前亏损 {pnl_pct * 100:.2f}%')
            self._close_position(data, dt, trade_state)
            if trade_state['daily_trades'] == 1:
                self._open_position(data, dt, row, trade_state, position=-position)
        return

    def _generate_position(self):
        data = self.intraday_data.copy()
        trade_state = {
            'position': 0, # 持仓方向
            'daily_trades': 0, # 交易日已交易次数
            'current_trading_day': None, # 当前交易日
            'entry_price' : None,
            'last_data_time': None,
        }
        prev_dt = None
        for idx, (dt, row) in enumerate(tqdm.tqdm(data.iterrows(), total=len(data), desc='Generating Position...')):
            if prev_dt is not None: # 如果交易日发生变化且还有持仓，先平仓
                prev_trading_day = self._get_trading_day(prev_dt)
                current_trading_day = self._get_trading_day(dt)
                if prev_trading_day != current_trading_day and data.loc[prev_dt, 'position'] != 0:
                    self._close_position(data, prev_dt, trade_state)
                if prev_dt in data.index and data.loc[prev_dt, 'contract'] != data.loc[dt, 'contract']:
                    self._close_position(data, prev_dt, trade_state)
            trading_day = self._get_trading_day(dt)
            # 检查是否是新交易日开始
            if trade_state['current_trading_day'] != trading_day:
                trade_state['daily_trades'] = 0
                trade_state['current_trading_day'] = trading_day
                self._open_position(data, dt, row, trade_state, position=-1)
            trade_state['last_data_time'] = dt
            prev_dt = dt  # 更新前一个时间点
            # 止损检查
            if trade_state['position'] != 0:
                self._check_stop_loss(data, dt, row, trade_state)
            # 更新持仓数据
            data.at[dt, 'position'] = trade_state['position']
            data.at[dt, 'entry_price'] = trade_state['entry_price']
        # 处理最后一个交易日可能未平仓的情况
        if trade_state['position'] != 0:
            last_dt = trade_state['last_data_time']
            self._close_position(data, last_dt, trade_state)
            data.to_csv('../VIX/tradeflow_data.csv', index=False)
        return data

    def _calculate_return(self):
        data = self._generate_position()
        data['minute_return'] = data['close'].pct_change() * data['position'].shift(1)
        forced_close = (data['datetime'].dt.hour == 17) & (data['position'] == 0)
        data.loc[forced_close, 'minute_return'] = 0
        return data

    def backtest(self):
        self.intraday_data = self._calculate_return()
        self.intraday_data.to_csv('../VIX/tradeflow.csv')
        print("===== 收益分布验证 =====")
        minute_returns = self.intraday_data['minute_return']
        print(f"分钟收益率均值: {minute_returns.mean():.6f}")
        print(f"分钟收益率标准差: {minute_returns.std():.6f}")
        print(f"最大分钟收益: {minute_returns.max():.6f}")
        print(f"最大分钟亏损: {minute_returns.min():.6f}")
        vix_minute = Visualizer(self.intraday_data, self.start_date, self.end_date, self.capital)
        vix_minute.calculate_statistics()

if __name__ == "__main__":
    # 运行策略
    strategy = VIXShortStrategy(
        start_date='2020-01-01',  # 回测开始时间
        end_date='2021-01-01',  # 回测结束时间
        ric='VX',  # 交易标的
    )
    # 执行回测
    strategy.backtest()