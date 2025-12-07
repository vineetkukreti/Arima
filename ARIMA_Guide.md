# ARIMA Models — A Complete Beginner's Guide

## Table of Contents
1. [Introduction](#introduction)
2. [Time Series Fundamentals](#time-series-fundamentals)
3. [The Three Components of ARIMA](#the-three-components-of-arima)
4. [Understanding ARIMA Parameters (p, d, q)](#understanding-arima-parameters)
5. [Stationarity — The Foundation](#stationarity)
6. [How ARIMA Works — Step by Step](#how-arima-works)
7. [Identifying ARIMA Parameters](#identifying-parameters)
8. [Model Fitting and Forecasting](#model-fitting-and-forecasting)
9. [Practical Example](#practical-example)
10. [Common Pitfalls and Best Practices](#common-pitfalls)

---

## Introduction

### What is ARIMA?

**ARIMA** stands for **AutoRegressive Integrated Moving Average**. It's one of the most popular statistical methods for forecasting time series data.

**In Simple Terms**: ARIMA is a mathematical model that looks at patterns in historical data (what happened in the past) to predict what will happen in the future.

**Use Cases**:
- Sales forecasting
- Stock price prediction
- Weather forecasting
- Demand planning
- Economic indicators

### Why ARIMA?

✅ **Proven and Reliable**: Used since the 1970s  
✅ **Handles Trends**: Can model data that increases/decreases over time  
✅ **Flexible**: Works with many different patterns  
✅ **Interpretable**: You can understand what the model is doing  
✅ **No External Data Needed**: Only requires historical values of the variable you're forecasting

---

## Time Series Fundamentals

Before understanding ARIMA, you need to understand **time series** data.

### What is a Time Series?

A **time series** is data collected at regular intervals over time.

**Examples**:
- Daily temperature readings
- Monthly sales figures
- Hourly stock prices
- Yearly GDP

**Key Characteristic**: The **order matters**! Unlike regular data where you can shuffle rows, time series data must stay in chronological order.

### Components of Time Series

Time series data typically has four components:

#### 1. **Trend** (T)
The long-term direction of the data.

```
Examples:
- Upward trend: Sales increasing year after year
- Downward trend: Print newspaper readership declining
- No trend: Data stays around the same level
```

**Visual**: Imagine a line that shows the general direction — uphill, downhill, or flat.

#### 2. **Seasonality** (S)
Regular, repeating patterns at fixed intervals.

```
Examples:
- Ice cream sales peak every summer (yearly pattern)
- Electricity usage spikes every evening (daily pattern)
- Tourism increases during holidays (seasonal pattern)
```

**Visual**: Think of waves that repeat at regular intervals.

#### 3. **Cyclic Patterns** (C)
Long-term fluctuations without fixed periods.

```
Examples:
- Economic cycles (boom and recession)
- Business cycles
```

**Different from Seasonality**: Cycles don't have fixed periods (might be 3 years, then 5 years, etc.)

#### 4. **Irregular/Random** (I)
Unpredictable, random fluctuations (noise).

```
Examples:
- Sudden events (pandemic, natural disaster)
- Random daily variations
- Measurement errors
```

---

## The Three Components of ARIMA

ARIMA = **AR** + **I** + **MA**

Let's break down each component:

### 1. AR — AutoRegressive

**"Auto" = Self, "Regressive" = Using past values**

The AR component says: **"The current value depends on previous values"**

#### Intuitive Example

Imagine predicting tomorrow's temperature:
- If today is 25°C, tomorrow is likely to be around 24-26°C (not suddenly 40°C)
- The current temperature is **correlated** with recent temperatures

#### Mathematical Representation

AR(p) model:
```
Y_t = c + φ₁·Y_{t-1} + φ₂·Y_{t-2} + ... + φₚ·Y_{t-p} + ε_t
```

**Translation**:
- `Y_t` = Value at time t (today)
- `Y_{t-1}` = Value at time t-1 (yesterday)
- `Y_{t-2}` = Value at time t-2 (day before yesterday)
- `φ₁, φ₂, ...` = Coefficients (weights) that the model learns
- `p` = Number of past values to use (the "order")
- `ε_t` = Random error

#### Real-World Analogy

**Stock Prices**: If a stock closed at $100 yesterday, it's more likely to open around $98-$102 today than at $50 or $200. The past influences the present.

#### AR Order (p)

- **AR(1)**: Uses only the immediately previous value
- **AR(2)**: Uses the last 2 values
- **AR(p)**: Uses the last p values

---

### 2. I — Integrated (Differencing)

**"Integrated" = Making the data stationary**

The I component says: **"Remove trends by taking differences"**

#### Why Do We Need This?

ARIMA requires **stationary** data (more on this later). Many real-world time series have trends, which we need to remove.

#### What is Differencing?

Instead of looking at the raw values, we look at the **differences** between consecutive values.

#### Example

**Original Data** (has upward trend):
```
Month:  Jan  Feb  Mar  Apr  May
Sales:  100  110  120  130  140
```

**First Difference** (trend removed):
```
Month:     Feb  Mar  Apr  May
Difference: 10   10   10   10
```

**Formula**: `Difference = Y_t - Y_{t-1}`

#### Differencing Order (d)

- **d = 0**: No differencing (data already stationary)
- **d = 1**: First-order differencing (most common)
- **d = 2**: Second-order differencing (difference of differences — rare)

#### Visual Understanding

**Original**: ↗️ (Going up)  
**After Differencing**: → (Flat, stationary)

---

### 3. MA — Moving Average

**NOT the simple moving average you might know!**

The MA component says: **"The current value depends on past forecast errors"**

#### Intuitive Explanation

Imagine you're forecasting sales:
- If you **over-predicted** yesterday (forecast was too high), you might adjust today's forecast **down**
- If you **under-predicted** yesterday, you might adjust today's forecast **up**

The MA part learns from past mistakes!

#### Mathematical Representation

MA(q) model:
```
Y_t = μ + ε_t + θ₁·ε_{t-1} + θ₂·ε_{t-2} + ... + θ_q·ε_{t-q}
```

**Translation**:
- `ε_t` = Today's error (random shock)
- `ε_{t-1}` = Yesterday's error
- `θ₁, θ₂, ...` = Coefficients for past errors
- `q` = Number of past errors to use

#### Real-World Analogy

**Weather Forecasting**: If yesterday's forecast was wrong (error), today's forecast is adjusted based on how wrong it was.

#### MA Order (q)

- **MA(1)**: Uses the last error term
- **MA(2)**: Uses the last 2 error terms
- **MA(q)**: Uses the last q error terms

---

## Understanding ARIMA Parameters

### The Notation: ARIMA(p, d, q)

Every ARIMA model is specified by three numbers:

| Parameter | Name | Meaning |
|-----------|------|---------|
| **p** | AR order | Number of past values to use |
| **d** | Differencing order | Number of times to difference the data |
| **q** | MA order | Number of past errors to use |

### Common ARIMA Models

#### ARIMA(1, 0, 0) = AR(1)
- Uses 1 past value
- No differencing (data already stationary)
- No moving average
- **Example**: Tomorrow's temperature depends on today's temperature

#### ARIMA(0, 1, 1)
- No autoregressive component
- First differencing applied
- Uses 1 past error
- **Common for**: Random walk with noise

#### ARIMA(1, 1, 0)
- Uses 1 past value
- First differencing
- No moving average
- **Your model's configuration!** (from the forecast system)

#### ARIMA(2, 1, 2)
- Uses 2 past values
- First differencing
- Uses 2 past errors
- **Common for**: Complex patterns with both AR and MA components

---

## Stationarity — The Foundation

### What is Stationarity?

**Stationary** = Statistical properties (mean, variance) don't change over time

#### Visual Examples

**Stationary** ✅:
```
   •  •
  •    •  •
 •       •  •
•          •
──────────────────► Time
(Fluctuates around a constant mean)
```

**Non-Stationary** ❌:
```
              •
          •  •
       •
    •
 •
──────────────────► Time
(Has an upward trend — mean is changing)
```

### Why Does ARIMA Need Stationarity?

ARIMA's math assumes the future will behave like the past. If data has a trend:
- The mean is constantly changing
- Past patterns won't help predict the future
- Model assumptions are violated

**Solution**: Use differencing (the "I" in ARIMA) to remove trends!

### Testing for Stationarity

**Augmented Dickey-Fuller (ADF) Test** is the most common test.

**How to interpret**:
- **p-value < 0.05** → Stationary ✅
- **p-value > 0.05** → Non-stationary ❌

**Your model's result**:
```
ADF p-value: 0.0031
✓ Series is STATIONARY
```

---

## How ARIMA Works — Step by Step

### The Complete ARIMA Process

#### Step 1: Check Stationarity
```
1. Run ADF test on original data
2. If p-value > 0.05 → Non-stationary
3. Apply differencing (d = 1)
4. Re-test
5. Repeat until stationary
```

#### Step 2: Identify Parameters (p, q)

Use **ACF** and **PACF** plots:

**ACF (Autocorrelation Function)**:
- Shows how current values correlate with past values
- Helps determine **q** (MA order)

**PACF (Partial Autocorrelation Function)**:
- Shows direct correlation (removing indirect effects)
- Helps determine **p** (AR order)

**Rules of Thumb**:

| Plot | Pattern | Suggested Model |
|------|---------|----------------|
| ACF cuts off after lag q | MA(q) | Use MA model |
| PACF cuts off after lag p | AR(p) | Use AR model |
| Both decay gradually | ARMA(p,q) | Use both AR and MA |

#### Step 3: Fit the Model

The ARIMA algorithm:
1. Takes your data and parameters (p, d, q)
2. Applies differencing d times
3. Estimates coefficients (φ and θ values) using **Maximum Likelihood Estimation**
4. Minimizes prediction errors

**Math Behind the Scenes** (simplified):
```
The algorithm finds the φ and θ values that make
the model's predictions closest to actual values
```

#### Step 4: Validate the Model

**Check Residuals** (prediction errors):

Good model residuals should be:
- ✅ **Normally distributed** (Q-Q plot should be a straight line)
- ✅ **No autocorrelation** (ACF plot should show no patterns)
- ✅ **Zero mean** (errors average to zero)
- ✅ **Constant variance** (no increasing/decreasing spread)

**Statistical Tests**:
- **Ljung-Box Test**: Tests if residuals are random
  - p-value > 0.05 → Good! ✅
  - p-value < 0.05 → Bad, residuals have patterns ❌

#### Step 5: Forecast

Once validated:
1. Model uses the last p values and q errors
2. Generates predictions for future time points
3. Calculates confidence intervals
4. Further into the future → wider confidence intervals (more uncertainty)

---

## Identifying ARIMA Parameters

### Method 1: Auto ARIMA (Automated)

**Easiest approach** — let the algorithm find the best (p, d, q).

```python
from pmdarima import auto_arima

model = auto_arima(data,
                   start_p=0, start_q=0,
                   max_p=5, max_q=5,
                   d=None,  # Auto-detect
                   seasonal=False,
                   stepwise=True)
                   
print(model.order)  # Best (p, d, q)
```

**How it works**:
1. Tries many combinations of (p, d, q)
2. Compares models using **AIC** or **BIC** (lower is better)
3. Returns the best model

**Your model** used this and found: ARIMA(1, 1, 0)

### Method 2: ACF/PACF Plots (Manual)

**For learning** — understand patterns yourself.

#### Reading ACF Plot

**ACF measures**: Correlation between Y_t and Y_{t-k} for different lags k

**Patterns**:
- **Sharp cutoff at lag q**: Suggests MA(q)
- **Gradual decay**: Suggests AR component

#### Reading PACF Plot

**PACF measures**: Direct correlation at each lag (removing intermediate effects)

**Patterns**:
- **Sharp cutoff at lag p**: Suggests AR(p)
- **Gradual decay**: Suggests MA component

### Method 3: Information Criteria

**AIC (Akaike Information Criterion)**:
```
AIC = 2k - 2·ln(L)
```
- k = number of parameters
- L = likelihood

**Lower AIC = Better model**

**BIC (Bayesian Information Criterion)**: Similar but penalizes complexity more

---

## Model Fitting and Forecasting

### The Fitting Process

#### 1. Data Preparation
```python
# Your time series
data = [100, 110, 120, 130, 140, ...]

# Apply differencing if d > 0
if d == 1:
    diff_data = data[1:] - data[:-1]
```

#### 2. Estimate Coefficients

The model estimates:
- **φ (phi)**: AR coefficients
- **θ (theta)**: MA coefficients

Using **Maximum Likelihood Estimation**:
- Finds parameters that maximize the probability of observing the given data

#### 3. Make Predictions

**One-step ahead**:
```
Forecast_t+1 = φ₁·Y_t + φ₂·Y_{t-1} + ... + θ₁·ε_t + ...
```

**Multi-step ahead**:
- Use previous forecasts as "actual" values
- Uncertainty increases with each step

### Confidence Intervals

**95% Confidence Interval** means:
- 95% chance the true value will fall in this range
- 5% chance it will be outside

**Why they widen over time**:
- More steps ahead = more uncertainty
- Errors compound over multiple predictions

**Your model's example**:
```
Jan 2030: Forecast = 3,491 [3,015 - 3,967]  (narrow)
Dec 2034: Forecast = 3,484 [1,956 - 5,012]  (wide)
```

---

## Practical Example

Let's walk through a complete example with your data!

### Your Data Characteristics

**Original Data**:
- 62 monthly observations (2024-11 to 2029-12)
- Product demand aggregated across customers/products

### Step-by-Step Analysis

#### 1. Stationarity Check
```
ADF Test Result:
- Test Statistic: -3.78
- p-value: 0.0031 < 0.05
✓ Data is STATIONARY
```

**Interpretation**: Your data doesn't have a strong trend. It fluctuates around a stable mean.

#### 2. Parameter Selection

**Auto ARIMA found**: ARIMA(1, 1, 0)

**What this means**:
- **p = 1**: Current value depends on 1 previous value
  - `Y_t = φ₁·Y_{t-1}`
- **d = 1**: Data is differenced once
  - Makes it even more stationary
- **q = 0**: No moving average component
  - Past errors don't significantly affect predictions

**In Plain English**:
"This month's demand can be predicted by looking at the change from last month"

#### 3. Model Equation

Your ARIMA(1, 1, 0) model is:
```
ΔY_t = φ₁·ΔY_{t-1} + ε_t

Where ΔY_t = Y_t - Y_{t-1} (first difference)
```

#### 4. Performance

**MAPE: 3.39%**

This means on average, predictions are within **3.39%** of actual values — **excellent!**

**Why it's good**:
- < 10% → Excellent
- 10-20% → Good
- 20-50% → Acceptable
- \> 50% → Poor

#### 5. Forecast

**Pattern detected**: Stable demand around 3,484 units/month

**Why stable**?
- Data doesn't have strong trend
- ARIMA(1,1,0) captures short-term fluctuations
- Forecast converges to a long-term mean

---

## Common Pitfalls and Best Practices

### Common Mistakes

❌ **Ignoring Stationarity**
- ARIMA assumes stationarity
- Always test and apply differencing if needed

❌ **Overfitting**
- Using too many parameters (high p, q)
- Model memorizes noise instead of patterns
- **Solution**: Use AIC/BIC to balance fit vs complexity

❌ **Not Checking Residuals**
- Residuals should be random
- Patterns in residuals = model missed something
- **Solution**: Always plot and test residuals

❌ **Extrapolating Too Far**
- Confidence intervals widen over time
- Long-term forecasts become very uncertain
- **Solution**: Re-train model regularly with new data

❌ **Ignoring Seasonality**
- ARIMA can't handle seasonal patterns well
- **Solution**: Use SARIMA (Seasonal ARIMA) for seasonal data

### Best Practices

✅ **Always Visualize Data First**
- Plot your time series
- Look for trends, seasonality, outliers

✅ **Split Data for Validation**
- Train on 80%, test on 20%
- Ensures model generalizes well

✅ **Use Auto ARIMA for Initial Exploration**
- Quick and reliable
- Good starting point

✅ **Validate with Multiple Metrics**
- Don't rely on just one metric
- Use RMSE, MAE, MAPE together

✅ **Check Residuals**
- Q-Q plot for normality
- ACF plot for autocorrelation
- Ljung-Box test

✅ **Retrain Regularly**
- Update model with new data
- Quarterly or monthly retraining
- Keeps model current

✅ **Use Confidence Intervals**
- Don't just look at point forecasts
- Plan for best/worst case scenarios

---

## Summary

### Key Takeaways

1. **ARIMA = AR + I + MA**
   - AR: Uses past values
   - I: Differences to remove trends
   - MA: Uses past errors

2. **Three Parameters (p, d, q)**
   - p: Number of past values (AR order)
   - d: Differencing order
   - q: Number of past errors (MA order)

3. **Stationarity is Critical**
   - Test with ADF
   - Apply differencing if needed

4. **Model Selection**
   - Auto ARIMA for automation
   - ACF/PACF for understanding
   - AIC/BIC for comparison

5. **Validation Matters**
   - Check residuals
   - Use train-test split
   - Multiple performance metrics

### When to Use ARIMA

**Good for**:
✅ Univariate time series (one variable)
✅ Data with trends
✅ Short to medium-term forecasts
✅ Regular interval data

**Not ideal for**:
❌ Strong seasonal patterns (use SARIMA)
❌ Multiple variables (use VAR)
❌ Very long-term forecasts
❌ Data with structural breaks

### Next Steps

1. **Run the notebooks** to see ARIMA in action
2. **Experiment** with different (p, d, q) values
3. **Try seasonal data** with SARIMA
4. **Read model diagnostics** carefully
5. **Practice** with different datasets

---

## Glossary

| Term | Definition |
|------|------------|
| **Autocorrelation** | Correlation of a variable with itself at different time lags |
| **Stationarity** | Statistical properties don't change over time |
| **ADF Test** | Statistical test for stationarity |
| **Differencing** | Subtracting consecutive values to remove trends |
| **Lag** | Time delay (lag 1 = previous period) |
| **Residuals** | Prediction errors (actual - forecast) |
| **AIC/BIC** | Information criteria for model selection (lower is better) |
| **MAPE** | Mean Absolute Percentage Error (accuracy metric) |
| **Confidence Interval** | Range where true value likely falls |

---

## Further Reading

**Books**:
- "Time Series Analysis" by Box & Jenkins (classic)
- "Forecasting: Principles and Practice" by Hyndman & Athanasopoulos (free online)

**Online Resources**:
- [statsmodels documentation](https://www.statsmodels.org/)
- [pmdarima documentation](http://alkaline-ml.com/pmdarima/)

**Your Project Files**:
- `notebooks/01_data_exploration.ipynb` - See EDA in practice
- `notebooks/02_arima_modeling.ipynb` - Complete ARIMA workflow
- `README.md` - Technical documentation

---

**You now understand ARIMA!** 🎉

The best way to learn is to run the notebooks and see how each step works with real data. Start with the data exploration notebook, then move to the modeling notebook. Don't hesitate to experiment!
