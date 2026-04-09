from matplotlib import pyplot as plt
import pandas as pd
import numpy as np


class Visualizer:
    """
    这个代码包用于可视化交易策略表现，输入需要包含：

    数据表(必须包含'datetime'和'return'列)
    开始日期(start_date)
    结束日期(end_date)
    初始资金(capital)

    它会自动计算并显示：

        累计收益率曲线
        年化收益率
        夏普比率
        最大回撤
        卡玛比率
    """
    def __init__(self, data: pd.DataFrame, start_date: str, end_date: str, capital: float):
        self.data = self._preprocess_data(data.copy())
        self.start_date = start_date
        self.end_date = end_date
        self.capital = capital

    def _preprocess_data(self, data):
        """预处理数据，处理分钟频数据转换为日频"""
        # 检查收益率列名
        if 'return' not in data.columns and 'minute_return' not in data.columns:
            raise ValueError("数据必须包含'return'或'minute_return'列")

        # 统一收益率列名
        if 'minute_return' in data.columns:
            data['return'] = data['minute_return']

        # 更精确的频率检测
        if not pd.api.types.is_datetime64_any_dtype(data['datetime']):
            data['datetime'] = pd.to_datetime(data['datetime'])

        # 检测是否为分钟级数据
        if len(data) > 1:
            time_diff = data['datetime'].diff().min()
            if time_diff <= pd.Timedelta('1h'):  # 小时或分钟级数据
                # 转换为日频数据
                daily_data = data.set_index('datetime').resample('D').agg({
                    'return': lambda x: np.prod(1 + x) - 1,
                    # 'return': lambda x: np.sum(x),
                    'close': 'last' if 'close' in data.columns else None
                }).reset_index()
                return daily_data.dropna()

        return data

    def _estimate_trading_days(self):
        """估计交易日数量"""
        start = pd.to_datetime(self.start_date)
        end = pd.to_datetime(self.end_date)
        trading_days = pd.bdate_range(start, end)
        return len(trading_days)

    def calculate_statistics(self):
        """计算统计指标并绘图"""
        # 改进的累计收益率计算
        self.data['cum_return'] = (1 + self.data['return']).cumprod() - 1
        self.data['capital'] = self.capital * (1 + self.data['cum_return'])

        # 计算关键指标
        trading_days = self._estimate_trading_days()
        total_return = self.data['cum_return'].iloc[-1]
        annualized_return = (1 + total_return) ** (252 / trading_days) - 1

        # 改进的夏普比率计算（使用日收益率）
        sharpe_ratio = np.sqrt(252) * self.data['return'].mean() / self.data['return'].std()

        # 改进的回撤计算
        peak = self.data['capital'].cummax()
        drawdown = (self.data['capital'] - peak) / peak
        max_drawdown = drawdown.min()
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else np.nan

        print(f'回测期间约有{trading_days}个交易日')
        print(f'总收益率: {total_return:.2%}')
        print(f'年化收益率: {annualized_return:.2%}')
        print(f'夏普比率: {sharpe_ratio:.2f}')
        print(f'最大回撤: {max_drawdown:.2%}')
        print(f'卡玛比率: {calmar_ratio:.2f}')

        # 可视化
        fig, ax1 = plt.subplots(figsize=(10, 6))

        # 添加标的资产价格曲线（如果存在）
        if 'close' in self.data.columns:
            ax1.plot(self.data['datetime'], self.data['close'] / self.data['close'].iloc[0], label='交易标的价格', color='gray', alpha=0.5,
                     linewidth=2)

        # 主曲线：累计收益率
        ax1.plot(self.data['datetime'],
                 self.data['capital'] / self.capital,
                 label='策略净值',
                 color='blue',
                 linewidth=2)
        ax1.set_ylabel('净值')

        # 次坐标轴：回撤率（改进计算方式）
        ax2 = ax1.twinx()
        ax2.fill_between(self.data['datetime'],
                         -drawdown,
                         label='回撤',
                         color='red',
                         alpha=0.2)
        ax2.set_ylabel('回撤')

        # 标题和图例
        plt.title(f"年化: {annualized_return:.2%} | 夏普: {sharpe_ratio:.2f} | 卡玛: {calmar_ratio:.2f} | 最大回撤: {max_drawdown:.2%}")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        plt.xlabel('日期')
        plt.grid(alpha=0.1)
        plt.tight_layout()
        plt.show()

        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'calmar_ratio': calmar_ratio
        }
