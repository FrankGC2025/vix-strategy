import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import tqdm
from future_data_loader import FutureDataLoader
from trading_strategy_visualizer import Visualizer
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

class SimpleStrategy:
    def __init__(self, start_date, end_date, ric):
        self.start_date = start_date
        self.end_date = end_date
        self.ric = ric
        self.capital = 100000.00  # 初始资本金
        loader = FutureDataLoader(
            ric=self.ric,
            start_date=self.start_date,
            end_date=self.end_date,
        )
        daily_data = loader.main_contract
        intraday_data = loader.intraday
        self.daily_data = daily_data
        self.intraday_data = intraday_data

    def _generate_position(self):
        data = self.intraday_data.copy()
        # 一直买，买就完啦！
        data['position'] = 1
        return data.reset_index()

    def _calculate_return(self):
        data = self._generate_position()
        data['minute_return'] = data['close'].pct_change() * data['position']
        forced_close = (data['datetime'].dt.hour == 17) & (data['position'] == 0)
        data.loc[forced_close, 'minute_return'] = 0
        return data

    def backtest(self):
        self.intraday_data = self._calculate_return()
        vix_minute = Visualizer(self.intraday_data, self.start_date, self.end_date, self.capital)
        vix_minute.calculate_statistics()

if __name__ == "__main__":
    # 运行策略
    strategy = SimpleStrategy(
        start_date='2022-01-01',  # 回测开始时间
        end_date='2025-05-02',  # 回测结束时间
        ric='VX',  # 交易标的
    )
    # 执行回测
    strategy.backtest()