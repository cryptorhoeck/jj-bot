"""
Technical Indicators Module

Provides a comprehensive set of technical analysis indicators:
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- Fibonacci Retracement Levels
- Enhanced RSI, SMA, EMA, ATR
- Volume indicators
"""

import math
from typing import List, Dict, Tuple, Optional


class TechnicalIndicators:
    """Calculate technical indicators from OHLCV data"""

    @staticmethod
    def sma(data: List[float], period: int) -> List[Optional[float]]:
        """
        Simple Moving Average

        Args:
            data: List of prices
            period: Period for the moving average

        Returns:
            List of SMA values (None for insufficient data points)
        """
        sma = []
        for i in range(len(data)):
            if i < period - 1:
                sma.append(None)
            else:
                avg = sum(data[i - period + 1:i + 1]) / period
                sma.append(avg)
        return sma

    @staticmethod
    def ema(data: List[float], period: int) -> List[Optional[float]]:
        """
        Exponential Moving Average

        Args:
            data: List of prices
            period: Period for the moving average

        Returns:
            List of EMA values
        """
        ema = []
        multiplier = 2 / (period + 1)

        # First EMA is SMA
        sma_val = sum(data[:period]) / period
        ema.append(sma_val)

        # Calculate EMA for remaining periods
        for i in range(1, len(data)):
            if i < period - 1:
                ema.insert(0, None)
            else:
                ema_val = (data[i] - ema[-1]) * multiplier + ema[-1]
                ema.append(ema_val)

        # Adjust for initial None values
        ema = [None] * (period - 1) + ema[period - 1:]
        return ema

    @staticmethod
    def macd(
        data: List[float],
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9
    ) -> Dict[str, List[Optional[float]]]:
        """
        MACD (Moving Average Convergence Divergence)

        Args:
            data: List of closing prices
            fast_period: Fast EMA period (default 12)
            slow_period: Slow EMA period (default 26)
            signal_period: Signal line period (default 9)

        Returns:
            Dict with macd_line, signal_line, and histogram
        """
        # Calculate fast and slow EMAs
        fast_ema = TechnicalIndicators.ema(data, fast_period)
        slow_ema = TechnicalIndicators.ema(data, slow_period)

        # Calculate MACD line (fast EMA - slow EMA)
        macd_line = []
        for i in range(len(data)):
            if fast_ema[i] is None or slow_ema[i] is None:
                macd_line.append(None)
            else:
                macd_line.append(fast_ema[i] - slow_ema[i])

        # Calculate signal line (EMA of MACD line)
        macd_values = [v for v in macd_line if v is not None]
        if len(macd_values) >= signal_period:
            signal_ema = TechnicalIndicators.ema(macd_values, signal_period)

            # Align signal line with macd line
            signal_line = [None] * (len(macd_line) - len(signal_ema)) + signal_ema
        else:
            signal_line = [None] * len(macd_line)

        # Calculate histogram (MACD line - signal line)
        histogram = []
        for i in range(len(macd_line)):
            if macd_line[i] is None or signal_line[i] is None:
                histogram.append(None)
            else:
                histogram.append(macd_line[i] - signal_line[i])

        return {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": histogram
        }

    @staticmethod
    def bollinger_bands(
        data: List[float],
        period: int = 20,
        std_dev: float = 2.0
    ) -> Dict[str, List[Optional[float]]]:
        """
        Bollinger Bands

        Args:
            data: List of closing prices
            period: Period for the moving average (default 20)
            std_dev: Number of standard deviations (default 2.0)

        Returns:
            Dict with upper_band, middle_band (SMA), and lower_band
        """
        middle_band = TechnicalIndicators.sma(data, period)
        upper_band = []
        lower_band = []

        for i in range(len(data)):
            if i < period - 1:
                upper_band.append(None)
                lower_band.append(None)
            else:
                # Calculate standard deviation for the period
                period_data = data[i - period + 1:i + 1]
                mean = middle_band[i]
                variance = sum((x - mean) ** 2 for x in period_data) / period
                std = math.sqrt(variance)

                upper_band.append(mean + (std_dev * std))
                lower_band.append(mean - (std_dev * std))

        return {
            "upper_band": upper_band,
            "middle_band": middle_band,
            "lower_band": lower_band,
            "bandwidth": [
                (upper_band[i] - lower_band[i]) / middle_band[i] * 100
                if all(x is not None for x in [upper_band[i], lower_band[i], middle_band[i]]) and middle_band[i] != 0
                else None
                for i in range(len(data))
            ]
        }

    @staticmethod
    def fibonacci_retracement(
        high: float,
        low: float,
        trend: str = "uptrend"
    ) -> Dict[str, float]:
        """
        Fibonacci Retracement Levels

        Args:
            high: Highest price in the range
            low: Lowest price in the range
            trend: "uptrend" or "downtrend"

        Returns:
            Dict with Fibonacci levels (0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%)
        """
        diff = high - low
        levels = {}

        if trend == "uptrend":
            levels = {
                "level_0": high,                      # 0%
                "level_236": high - (0.236 * diff),   # 23.6%
                "level_382": high - (0.382 * diff),   # 38.2%
                "level_50": high - (0.5 * diff),      # 50%
                "level_618": high - (0.618 * diff),   # 61.8%
                "level_786": high - (0.786 * diff),   # 78.6%
                "level_100": low                      # 100%
            }
        else:  # downtrend
            levels = {
                "level_0": low,                       # 0%
                "level_236": low + (0.236 * diff),    # 23.6%
                "level_382": low + (0.382 * diff),    # 38.2%
                "level_50": low + (0.5 * diff),       # 50%
                "level_618": low + (0.618 * diff),    # 61.8%
                "level_786": low + (0.786 * diff),    # 78.6%
                "level_100": high                     # 100%
            }

        return levels

    @staticmethod
    def fibonacci_extension(
        start: float,
        high: float,
        low: float
    ) -> Dict[str, float]:
        """
        Fibonacci Extension Levels (for price targets)

        Args:
            start: Starting price
            high: Swing high
            low: Swing low

        Returns:
            Dict with Fibonacci extension levels
        """
        diff = high - low

        return {
            "level_0": start,
            "level_618": start + (0.618 * diff),
            "level_100": start + diff,
            "level_1618": start + (1.618 * diff),
            "level_2618": start + (2.618 * diff),
            "level_4236": start + (4.236 * diff)
        }

    @staticmethod
    def rsi(data: List[float], period: int = 14) -> List[Optional[float]]:
        """
        Relative Strength Index

        Args:
            data: List of closing prices
            period: Period for RSI calculation (default 14)

        Returns:
            List of RSI values (0-100)
        """
        if len(data) < period + 1:
            return [None] * len(data)

        rsi_values = [None]  # First value is None (no change to calculate)

        # Calculate price changes
        changes = [data[i] - data[i - 1] for i in range(1, len(data))]

        # Calculate initial average gain and loss
        gains = [max(change, 0) for change in changes[:period]]
        losses = [abs(min(change, 0)) for change in changes[:period]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        # Calculate first RSI
        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

        # Calculate subsequent RSI values using Wilder's smoothing
        for i in range(period, len(changes)):
            change = changes[i]
            gain = max(change, 0)
            loss = abs(min(change, 0))

            avg_gain = (avg_gain * (period - 1) + gain) / period
            avg_loss = (avg_loss * (period - 1) + loss) / period

            if avg_loss == 0:
                rsi_values.append(100)
            else:
                rs = avg_gain / avg_loss
                rsi_values.append(100 - (100 / (1 + rs)))

        # Pad beginning with None values
        rsi_values = [None] * (period - 1) + rsi_values[period - 1:]

        return rsi_values

    @staticmethod
    def atr(
        high: List[float],
        low: List[float],
        close: List[float],
        period: int = 14
    ) -> List[Optional[float]]:
        """
        Average True Range (volatility indicator)

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            period: Period for ATR calculation (default 14)

        Returns:
            List of ATR values
        """
        if len(high) != len(low) or len(high) != len(close):
            raise ValueError("high, low, and close lists must have the same length")

        true_ranges = []

        for i in range(len(high)):
            if i == 0:
                # First TR is just high - low
                tr = high[i] - low[i]
            else:
                # TR = max(high - low, abs(high - prev_close), abs(low - prev_close))
                hl = high[i] - low[i]
                hc = abs(high[i] - close[i - 1])
                lc = abs(low[i] - close[i - 1])
                tr = max(hl, hc, lc)

            true_ranges.append(tr)

        # Calculate ATR using Wilder's smoothing
        atr_values = []

        for i in range(len(true_ranges)):
            if i < period - 1:
                atr_values.append(None)
            elif i == period - 1:
                # First ATR is simple average
                atr_values.append(sum(true_ranges[:period]) / period)
            else:
                # Subsequent ATRs use Wilder's smoothing
                prev_atr = atr_values[-1]
                current_atr = (prev_atr * (period - 1) + true_ranges[i]) / period
                atr_values.append(current_atr)

        return atr_values

    @staticmethod
    def stochastic_oscillator(
        high: List[float],
        low: List[float],
        close: List[float],
        period: int = 14,
        smooth_k: int = 3,
        smooth_d: int = 3
    ) -> Dict[str, List[Optional[float]]]:
        """
        Stochastic Oscillator (%K and %D)

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            period: Period for stochastic calculation (default 14)
            smooth_k: Smoothing period for %K (default 3)
            smooth_d: Smoothing period for %D (default 3)

        Returns:
            Dict with k_values and d_values
        """
        k_raw = []

        for i in range(len(close)):
            if i < period - 1:
                k_raw.append(None)
            else:
                period_high = max(high[i - period + 1:i + 1])
                period_low = min(low[i - period + 1:i + 1])

                if period_high == period_low:
                    k_raw.append(50)  # Avoid division by zero
                else:
                    k = ((close[i] - period_low) / (period_high - period_low)) * 100
                    k_raw.append(k)

        # Smooth %K
        k_values = TechnicalIndicators.sma([v for v in k_raw if v is not None], smooth_k)
        k_values = [None] * (len(k_raw) - len(k_values)) + k_values

        # Calculate %D (SMA of %K)
        d_values = TechnicalIndicators.sma([v for v in k_values if v is not None], smooth_d)
        d_values = [None] * (len(k_values) - len(d_values)) + d_values

        return {
            "k_values": k_values,
            "d_values": d_values
        }

    @staticmethod
    def obv(close: List[float], volume: List[float]) -> List[float]:
        """
        On-Balance Volume (volume indicator)

        Args:
            close: List of closing prices
            volume: List of volume values

        Returns:
            List of OBV values
        """
        obv_values = [0]  # Start at 0

        for i in range(1, len(close)):
            if close[i] > close[i - 1]:
                # Price up: add volume
                obv_values.append(obv_values[-1] + volume[i])
            elif close[i] < close[i - 1]:
                # Price down: subtract volume
                obv_values.append(obv_values[-1] - volume[i])
            else:
                # Price unchanged: keep same OBV
                obv_values.append(obv_values[-1])

        return obv_values

    @staticmethod
    def vwap(high: List[float], low: List[float], close: List[float], volume: List[float]) -> List[float]:
        """
        Volume Weighted Average Price

        Args:
            high: List of high prices
            low: List of low prices
            close: List of closing prices
            volume: List of volume values

        Returns:
            List of VWAP values
        """
        vwap_values = []
        cumulative_tpv = 0  # Typical Price * Volume
        cumulative_volume = 0

        for i in range(len(close)):
            # Typical Price = (High + Low + Close) / 3
            typical_price = (high[i] + low[i] + close[i]) / 3

            # Add to cumulatives
            cumulative_tpv += typical_price * volume[i]
            cumulative_volume += volume[i]

            # Calculate VWAP
            if cumulative_volume > 0:
                vwap_values.append(cumulative_tpv / cumulative_volume)
            else:
                vwap_values.append(typical_price)

        return vwap_values


# Create singleton instance for easy import
indicators = TechnicalIndicators()
