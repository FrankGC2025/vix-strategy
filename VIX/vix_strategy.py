import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import tqdm
from future_data_loader import FutureDataLoader
from trading_strategy_visualizer import Visualizer
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class VIXShortStrategy:
    def __init__(self, start_date = '2010-01-01', end_date = '2025-05-02', ric='VX'):
        self.start_date = start_date
        self.end_date = end_date
        self.ric = ric # 交易标的
        self.capital = 100000.00 # 初始资本金
        self.stop_loss_pct = 0.005 # 0.5%止损比例
        self.commission = 0.005 # 每一个合约交易的手续费
        self.trade_times = 0 # 计算累计交易次数
        self.log_file = open('../VIX/trading_record.txt', 'w')
        self.log_file.write("交易日志\n")
        self.log_file.write("=" * 50 + "\n")
        loader = FutureDataLoader(
            ric = self.ric,
            start_date = self.start_date,
            end_date = self.end_date,
        )
        daily_data = loader.main_contract
        intraday_data = loader.intraday
        self.daily_data = daily_data
        self.intraday_data = intraday_data

    def _generate_position(self):
        # 初始化日志文件
        log_file = open('../VIX/trading_log.txt', 'w')
        log_file.write("交易日志开始\n")
        log_file.write("=" * 50 + "\n")

        data = self.intraday_data.copy()
        data['position'] = 0
        data['entry_price'] = np.nan
        data['capital'] = self.capital
        data['num_contract'] = 0

        trade_state = {
            'position': 0,
            'entry_price': None,
            'contracts': 0,
            'daily_trades': 0,
            'current_trading_day': None,
            'last_data_time': None
        }

        current_capital = self.capital
        prev_dt = None  # 记录前一个时间点

        for idx, (dt, row) in enumerate(tqdm.tqdm(data.iterrows(), total=len(data), desc='Generating Positions...')):
            # 先处理前一个交易日结束的情况（如果有）
            if prev_dt is not None:
                prev_trading_day = self._get_trading_day(prev_dt)
                current_trading_day = self._get_trading_day(dt)

                # 如果交易日发生变化且还有持仓
                if prev_trading_day != current_trading_day and trade_state['position'] != 0:
                    self.log_file.write(f'交易日结束时间 {prev_dt}，执行平仓\n')
                    current_capital = self._close_position(data, prev_dt, trade_state, data.loc[prev_dt]['close'],current_capital)

            # 更新当前数据点的资本金
            data.at[dt, 'capital'] = current_capital

            trading_day = self._get_trading_day(dt)

            # 检查是否是新交易日开始
            if trade_state['current_trading_day'] != trading_day:
                self.log_file.write(f'今天是{trading_day}\n')
                trade_state['daily_trades'] = 0
                trade_state['current_trading_day'] = trading_day
                current_capital = self._open_position(data, dt, row, trade_state, direction=-1,
                                                      current_capital=current_capital)
            trade_state['last_data_time'] = dt
            prev_dt = dt  # 更新前一个时间点
            # 止损检查
            if trade_state['position'] != 0:
                current_capital = self._check_stop_loss(data, dt, row, trade_state, current_capital)
            # 更新持仓数据
            data.at[dt, 'position'] = trade_state['position']
            data.at[dt, 'entry_price'] = trade_state['entry_price']
            data.at[dt, 'num_contract'] = trade_state['contracts']
        # 处理最后一个交易日可能未平仓的情况
        if trade_state['position'] != 0:
            last_dt = trade_state['last_data_time']
            last_row = data.loc[last_dt]
            current_capital = self._close_position(data, last_dt, trade_state, last_row['close'], current_capital)
            data.at[last_dt, 'capital'] = current_capital
        # 关闭日志文件
        self.log_file.write("=" * 50 + "\n")
        self.log_file.write(f"交易结束，累计交易次数: {self.trade_times}\n")
        self.log_file.close()
        return data.reset_index()

    def _open_position(self, data, dt, row, trade_state, direction, current_capital):
        entry_price = row['close']
        contracts = int(np.floor(current_capital / entry_price))
        # 计算开仓成本
        cost = contracts * entry_price
        commission = contracts * self.commission
        # 更新交易状态
        trade_state['position'] = direction
        trade_state['entry_price'] = entry_price
        trade_state['contracts'] = contracts
        trade_state['daily_trades'] += 1
        # 更新数据
        data.at[dt, 'position'] = direction
        data.at[dt, 'entry_price'] = entry_price
        data.at[dt, 'num_contract'] = contracts
        # 更新资本金（减去佣金）
        new_capital = current_capital - commission
        data.at[dt, 'capital'] = new_capital
        self.trade_times += 1
        action = "买入" if direction == 1 else "卖出"
        self.log_file.write(f'交易日志：{dt} 当前本金{current_capital}, {action}了 {contracts} 手，价格 {entry_price}，佣金 {commission}\n，剩余本金{new_capital}')
        self.log_file.write(f'已累计交易 {self.trade_times} 次\n')
        # if direction == 1:
        #     print(f'交易日志：{dt} 买入了 {contracts} 手，价格 {entry_price}，佣金 {commission}')
        # elif direction == -1:
        #     print(f'交易日志：{dt} 卖出了 {contracts} 手，价格 {entry_price}，佣金 {commission}')
        # print(f'已累计交易 {self.trade_times} 次')
        return new_capital

    def _close_position(self, data, dt, trade_state, current_price, current_capital):
        if trade_state['position'] == 0:
            return current_capital
        # 计算平仓盈亏
        entry_price = trade_state['entry_price']
        contracts = trade_state['contracts']
        position = trade_state['position']
        pnl = round((current_price - entry_price) * position * contracts, 2)
        commission = contracts * self.commission
        new_capital = current_capital + pnl - commission # 更新资本金
        # 重置交易状态
        trade_state['position'] = 0
        trade_state['entry_price'] = None
        trade_state['contracts'] = 0
        # 更新数据
        data.at[dt, 'position'] = 0
        data.at[dt, 'num_contract'] = 0
        data.at[dt, 'capital'] = new_capital

        self.log_file.write(f'交易日志：{dt} 平仓，价格 {current_price}，盈亏 {pnl}，佣金 {commission}\n')
        # print(f'交易日志：{dt} 平仓，价格 {current_price}，盈亏 {pnl}，佣金 {commission}')
        return new_capital

    def _check_stop_loss(self, data, dt, row, trade_state, current_capital):
        current_price = row['close']
        entry_price = trade_state['entry_price']
        position = trade_state['position']
        pnl_pct = (current_price - entry_price) / entry_price * position
        if pnl_pct <= -self.stop_loss_pct:
            self.log_file.write(f'触发止损：当前亏损 {pnl_pct * 100:.2f}%\n')
            # print(f'触发止损：当前亏损 {pnl_pct * 100:.2f}%')
            current_capital = self._close_position(data, dt, trade_state, current_price, current_capital)
            if trade_state['daily_trades'] == 1:
                current_capital = self._open_position(
                    data, dt, row, trade_state,
                    direction=-position,
                    current_capital=current_capital
                )
        return current_capital

    def _get_trading_day(self, dt):
        if dt.hour >= 18:  # 18:00-23:59 属于明天的交易日
            return (dt + pd.Timedelta(days=1)).date()
        else:  # 00:00-17:59 属于今天的交易日
            return dt.date()

    def _calculate_return(self):
        data = self._generate_position()
        price_change = data['close'].diff().fillna(0)
        data['pnl'] = data['position'] * data['num_contract'] * price_change
        prev_capital = data['capital'].shift(1).fillna(self.capital)
        data['minute_return'] = data['pnl'] / prev_capital
        forced_close = (data['datetime'].dt.hour == 17) & (data['position'] == 0)
        data.loc[forced_close, 'minute_return'] = 0
        data['capital'] = self.capital * (1 + data['minute_return']).cumprod()
        data['cum_return'] = data['capital'] / self.capital
        data.to_csv('../VIX/tradeflow_data.csv', index=False)
        return data

    def backtest(self):
        self.intraday_data = self._calculate_return()
        vix_minute = Visualizer(self.intraday_data, self.start_date, self.end_date, self.capital)
        vix_minute.calculate_statistics()

if __name__ == "__main__":

    # 运行策略
    strategy = VIXShortStrategy(
        start_date = '2025-01-01', # 回测开始时间
        end_date = '2025-05-02', # 回测结束时间
        ric = 'VX', # 交易标的
    )
    # 执行回测
    strategy.backtest()