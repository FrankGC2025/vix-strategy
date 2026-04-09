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
        self.capital = 100000.00
        self.stop_loss = 0.015
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
        return (dt + pd.Timedelta(hours=6)).date()

    def _close_position(self, data, dt, trade_state):
        if trade_state['position'] == 0:
            return
        exit_price = data.at[dt, 'close']
        trade_state['position'] = 0
        trade_state['entry_price'] = None
        data.at[dt, 'position'] = 0
        data.at[dt, 'exit_price'] = exit_price

    def _open_position(self, data, dt, row, trade_state, position):
        entry_price = row['open']
        trade_state['position'] = position
        trade_state['entry_price'] = entry_price
        trade_state['daily_trades'] += 1
        data.at[dt, 'position'] = position
        data.at[dt, 'entry_price'] = entry_price

    def _check_stop_loss(self, data, dt, row, trade_state):
        if trade_state['position'] == 0:
            return

        current_price = row['open']
        entry_price = trade_state['entry_price']
        position = trade_state['position']
        pnl_pct = (current_price - entry_price) / entry_price * position

        if pnl_pct <= -self.stop_loss:
            self._close_position(data, dt, trade_state)
            if trade_state['daily_trades'] == 1:
                self._open_position(data, dt, row, trade_state, position=-position)

    def _generate_position(self):
        data = self.intraday_data.copy()
        trade_state = {
            'position': 0,
            'daily_trades': 0,
            'current_trading_day': None,
            'entry_price': None,
            'last_data_time': None,
        }

        data['trading_day'] = data.index.map(self._get_trading_day)

        for trading_day, group in tqdm.tqdm(data.groupby('trading_day'), desc='Processing Days...'):
            if trade_state['current_trading_day'] != trading_day:
                trade_state['daily_trades'] = 0
                trade_state['current_trading_day'] = trading_day
                first_idx = group.index[0]
                self._open_position(data, first_idx, group.loc[first_idx], trade_state, position=-1)

            for dt, row in group.iterrows():
                if trade_state['position'] != 0:
                    self._check_stop_loss(data, dt, row, trade_state)
                data.at[dt, 'position'] = trade_state['position']
                data.at[dt, 'entry_price'] = trade_state['entry_price']
                trade_state['last_data_time'] = dt

        if trade_state['position'] != 0:
            self._close_position(data, trade_state['last_data_time'], trade_state)

        return data

    def _calculate_return(self):
        data = self._generate_position()
        data['minute_return'] = 0.0

        # 保持为Series类型以使用shift方法
        positions = data['position']
        entry_prices = data['entry_price']
        opens = data['open']
        closes = data['close']

        # 计算持仓期间的收益率
        holding_mask = (positions != 0)
        data.loc[holding_mask, 'minute_return'] = (opens[holding_mask] - entry_prices[holding_mask]) / entry_prices[
            holding_mask] * positions[holding_mask]

        # 计算平仓时的收益率
        exit_mask = (positions.shift(1) != 0) & (positions == 0)
        data.loc[exit_mask, 'minute_return'] = (closes[exit_mask] - entry_prices.shift(1)[exit_mask]) / \
                                               entry_prices.shift(1)[exit_mask] * positions.shift(1)[exit_mask]

        # 交易日结束时强制平仓
        forced_close = (data.index.hour == 17) & (data['position'] == 0)
        data.loc[forced_close, 'minute_return'] = 0

        return data

    def backtest(self):
        self.intraday_data = self._calculate_return()
        print("===== 收益分布验证 =====")
        minute_returns = self.intraday_data['minute_return']
        print(f"分钟收益率均值: {minute_returns.mean():.6f}")
        print(f"分钟收益率标准差: {minute_returns.std():.6f}")
        print(f"最大分钟收益: {minute_returns.max():.6f}")
        print(f"最大分钟亏损: {minute_returns.min():.6f}")
        vix_minute = Visualizer(self.intraday_data, self.start_date, self.end_date, self.capital)
        vix_minute.calculate_statistics()


if __name__ == "__main__":
    strategy = VIXShortStrategy(
        start_date='2019-07-01',
        end_date='2020-01-01',
        ric='VX',
    )
    strategy.backtest()
