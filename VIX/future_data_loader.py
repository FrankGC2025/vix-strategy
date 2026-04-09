import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import tqdm
os.chdir('C:/Users/new00/Documents/Frank/Intern/cta') # 更改工作路径

class FutureDataLoader:
    '''
    这个代码包用于加载期货数据，输入期货代码(ric)、开始日期(start_date)
    和结束日期(end_date)
    后，会返回两个数据表：
    main_contract: 包含主力合约的日线数据(开盘价、收盘价、成交量等)
    intraday: 包含对应主力合约的分钟级交易数据
    '''
    def __init__(self, ric, start_date, end_date='2025-05-02'):
        self.ric = ric
        self.start_date = start_date
        self.end_date = end_date
        self.main_contract = self.load_main_contract()
        self.intraday = self.load_intraday()

    def load_main_contract(self):
        # 读取每日主力合约
        contract_list = os.listdir(f'data/XXLP/futures/{self.ric}_day_allcontract')
        result = []
        for contract in tqdm.tqdm(contract_list, desc='Loading Main Contract...'):
            tmp = pd.read_csv(f'data/XXLP/futures/{self.ric}_day_allcontract/' + contract)
            tmp['contract'] = contract[:-8]  # 合约的选择上可能随着字符串长度不相等出现bug需要注意，这里是hard code
            result.append(tmp)
        result = pd.concat(result)
        result['datetime'] = pd.to_datetime(result['datetime'])
        result = result.sort_values(by=['datetime', 'volume'], ascending=[True, True]).drop_duplicates(subset=['datetime'], keep='last')
        result['date'] = result['datetime'].dt.normalize()
        result = result.set_index('datetime')
        result = result.loc[result.index >= self.start_date]
        result = result.loc[result.index <= self.end_date]
        result = result.reset_index(drop=False)
        return result

    def load_intraday(self):
        all_intraday = []  # 根据主力合约读取期货分钟频数据
        for contract, tmp in tqdm.tqdm(self.main_contract.groupby('contract'), desc='Loading Intraday Data...'):
            dates = tmp['date'].unique()
            intraday = pd.read_csv(f'data/XXLP/futures/{self.ric}_1min_allcontract/{contract}_1min.csv')  # 读取单个合约的数据
            intraday['datetime'] = pd.to_datetime(intraday['datetime'])  # 处理时间字段
            intraday['date'] = intraday['datetime'].dt.normalize()
            intraday['contract'] = contract
            intraday_filtered = intraday[intraday['date'].isin(dates)]  # 过滤符合条件的日期
            all_intraday.append(intraday_filtered)  # 将过滤后的数据添加到列表
        final_intraday = pd.concat(all_intraday, axis=0).sort_values(by=['datetime'], ascending=[True]).reset_index(drop=True)
        final_intraday.set_index('datetime', inplace=True, drop = False)
        final_intraday = final_intraday[
            (final_intraday['date'] >= self.start_date) & (final_intraday['date'] <= self.end_date)]
        intraday = final_intraday.between_time('00:00', '23:59')
        # intraday.to_csv('../VIX/intraday_data.csv')
        return intraday

if __name__ == '__main__':
    loader = FutureDataLoader(ric = 'VX', start_date = '2025-01-01', end_date = '2025-05-01')
    print(loader.main_contract.head(20))
    print(loader.intraday.head(20))
    # plt.plot(loader.main_contract['close'])
    # plt.tight_layout()
    # plt.show()
    plt.scatter(loader.intraday.index, loader.intraday['close'], size = 0.5)
    plt.tight_layout()
    plt.show()
    # plt.figure(figsize=(12, 6))
    # plt.plot(loader.intraday.index, loader.intraday['close'], label='Intraday Close Price')
    # plt.title('Intraday Close Price (Only Trading Hours)')
    # plt.xlabel('Time')
    # plt.ylabel('Price')
    # plt.xticks(rotation=45)
    # plt.grid(True)
    # plt.tight_layout()
    # plt.show()