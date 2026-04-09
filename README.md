# 📊 VIX期货做空策略（VX Futures Short Strategy）

## 📌 项目简介

本项目实现了一个基于 **VIX期货（VX）** 的量化交易策略，重点研究波动率风险溢价（Volatility Risk Premium）在期货市场中的表现。

策略核心思想：

* VIX期货通常存在 **期限结构（Term Structure）贴水/升水**
* 波动率具有一定的 **均值回归特性**
* 因此尝试构建 **做空VIX期货的策略**

---

## 🧠 项目结构说明

本项目包含两个版本的策略实现：

### 1️⃣ Research版本（研究原型）

* 仅关注：**信号与收益**
* 使用简化收益计算方式（position × return）
* 不考虑：

  * 资金管理
  * 手续费
  * 合约数量

👉 用于：验证策略是否有 alpha

---

### 2️⃣ Execution版本（交易模拟）

* 包含完整交易逻辑：

  * 资金（capital）
  * 合约数量（contracts）
  * 手续费（commission）
  * 止损机制（stop loss）
* 更接近真实交易环境

👉 用于：评估策略在现实中的表现

---

## ⚙️ 环境安装

建议使用虚拟环境：

### 1. 克隆仓库

```bash
git clone https://github.com/FrankGC2025/vix-strategy
cd vix-strategy
```

### 2. 创建虚拟环境

```bash
python -m venv venv
```

### 3. 激活环境

* Mac / Linux:

```bash
source venv/bin/activate
```

* Windows:

```bash
venv\Scripts\activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

---

## 📂 数据说明（重要）

⚠️ 本项目 **不包含任何数据文件**

原因：

* 数据体积较大（超过GitHub限制）
* 数据可能涉及授权或版权问题

---

### 如果你想运行策略：

你需要自行准备数据，并满足以下格式：

#### 必需字段（intraday）：

* `datetime`
* `close`
* `contract`（用于主力合约切换）

建议数据路径：

```bash
/data/
```

---

## ▶️ 运行方式

```bash
python your_strategy_file.py
```

---

## 📊 策略逻辑

策略核心规则：

* 每个交易日开始：

  * 默认做空 VIX期货
* 日内：

  * 若触发止损 → 平仓 / 反手
* 收盘：

  * 强制平仓
* 合约切换：

  * 自动平仓避免跨合约风险

---

## 📈 回测输出

策略运行后将输出：

* 每分钟收益（minute return）
* 收益分布统计：

  * 平均收益
  * 波动率
  * 最大收益 / 最大亏损
* 资金曲线（通过可视化模块）

---

## 🧩 项目结构

```bash
vix-strategy/
│── strategy.py                  # 策略核心逻辑
│── future_data_loader.py        # 数据加载
│── trading_strategy_visualizer.py # 可视化与统计
│── requirements.txt
│── README.md
│── data/                        # （不包含）
```

---

## ⚠️ 注意事项

* 本项目仅用于：

  * 学术研究
  * 策略原型验证
* 不构成任何投资建议
* 实盘交易需考虑：

  * 滑点
  * 流动性
  * 杠杆风险

---

## 🚀 后续优化方向

* 引入更合理的 **交易信号（alpha）**
* 使用 VIX 期限结构（Term Structure）
* 引入波动率因子
* 优化止损与仓位管理
* 构建完整回测框架（Backtesting Engine）
